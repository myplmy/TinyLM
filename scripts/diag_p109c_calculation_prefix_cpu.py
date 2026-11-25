"""Compare free, partial, verified and wrong calculation prefixes in frozen v3."""

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
from time import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_seen_long_answers_cpu as frozen
from scripts import p106b_verified_trace_data as verifier


REF = frozen.REF
BASE = frozen.BASE
SOURCE = REF.EVIDENCE / "p101a_sft_mtp_verified_trace_v3_s1337/first_answer_parent_ntp"
SOURCE_SHA = "5E68158B2F0D71B5954086122835DE36F8C797FA7A9DCBBA74537A018650AFD0"
OUT = REF.EVIDENCE / "p109c_calculation_prefix_cpu_20261126"
END = datetime.fromisoformat("2026-11-26T06:48:00+09:00")
ARMS = ("free", "first_step", "verified_steps", "wrong_carry")
PER_STRATUM = 8


def variants(tokenizer, source):
    sample = source["meta"]
    task = sample["task"]
    question, gold = (message["content"][0]["text"] for message in source["messages"])
    steps = verifier.build_steps(task)
    true_value = verifier.validate_steps(task, steps)
    if (true_value != sample["gold_value"] or not verifier.score_response(task, gold, sample["language"], "trace")["final_correct"]
            or sample["root"] != verifier.canonical_root(task)):
        raise ValueError("a source question no longer carries the verified arithmetic answer")
    off = [dict(step) for step in steps]
    delta = 10 if steps[0]["carry_out"] == 0 else -10
    off[0]["total"] += delta
    off[0]["carry_out"] ^= 1
    off[1]["carry_in"] ^= 1
    off[1]["total"] += delta // 10
    off[1]["digit"], off[1]["carry_out"] = off[1]["total"] % 10, off[1]["total"] // 10
    wrong = off[1]["carry_out"] * 100 + off[1]["digit"] * 10 + off[0]["digit"]
    if wrong != true_value + delta or len(str(wrong)) != len(str(true_value)):
        return None
    if [(s["position"], s["a"], s["b"]) for s in off] != [(s["position"], s["a"], s["b"]) for s in steps]:
        raise ValueError("the failed carry must leave the source operands unchanged")
    prompt = BASE.serialize({"messages": [{"role": "user", "content": question}]},
                            "chatml", add_generation_prompt=True)
    prefixes = dict(free="", first_step=verifier.step_text(steps[0]) + "\n",
                    verified_steps="".join(verifier.step_text(step) + "\n" for step in steps),
                    wrong_carry="".join(verifier.step_text(step) + "\n" for step in off))
    inputs = {name: tokenizer.encode(prompt + value).ids for name, value in prefixes.items()}
    if len(inputs["verified_steps"]) != len(inputs["wrong_carry"]):
        return None
    if any(ids[:len(inputs["free"])] != inputs["free"] for ids in inputs.values()):
        raise ValueError("the source user prompt changed when supplying an assistant prefix")
    if any(len(ids) + BASE.MAX_NEW > 1024 for ids in inputs.values()):
        raise ValueError("the bounded request would displace a supplied trace")
    return dict(id=sample["root"], language=sample["language"], view=sample["view"], task=task, question=question,
                expected=true_value, wrong_value=wrong, carry=steps[0]["carry_out"], prefixes=prefixes, inputs=inputs)


def prepare(tokenizer):
    manifest = REF.completed.read_json(SOURCE / "first_answers_shards_manifest.json")
    if (manifest["concat_sha256"] != SOURCE_SHA or manifest["rows"] != 1024
            or manifest["lineage"]["split"] != "test" or manifest["lineage"]["family"] != "trace"):
        raise ValueError("the original held-out source changed")
    BASE.p106b_shards.verify(SOURCE, manifest)
    potential = defaultdict(dict)
    for item in manifest["shards"]:
        for line in (SOURCE / item["path"]).read_text().splitlines():
            source = json.loads(line)["source"]
            meta = source["meta"]
            if meta["family"] != "addition" or min(meta["task"]["a"], meta["task"]["b"]) < 10:
                continue
            root = meta["root"]
            if meta["view"] != 2 * (int(root[-1], 16) % 2):
                continue
            row = variants(tokenizer, source)
            if row is not None:
                potential[root][row["language"]] = row
    selected = {0: [], 1: []}
    for root in sorted(potential):
        bucket = potential[root]
        if set(bucket) != {"ko", "en"}:
            continue
        if bucket["ko"]["carry"] != bucket["en"]["carry"]:
            raise ValueError("both languages must share the same root and carry")
        group = selected[bucket["ko"]["carry"]]
        if len(group) < PER_STRATUM:
            group.append(bucket)
    if any(len(group) != PER_STRATUM for group in selected.values()):
        raise ValueError(f"insufficient equal-token pairs: { {carry: len(group) for carry, group in selected.items()} }")
    return [bucket[language] for group in selected.values() for bucket in group for language in ("ko", "en")]


def generate(model, tokenizer, case, arm):
    ids = case["inputs"][arm]
    capture = frozen.FrozenPrefix(tokenizer, ids)
    _, metadata = frozen.sample(model, model.cfg, capture, case["question"], max_new=BASE.MAX_NEW,
                                temperature=0., top_k=1, device="cpu", eos_id=2, use_cache=True,
                                logits_last_only=True, return_metadata=True, stop_token_sequences=[[4]])
    answer, metadata = BASE.manual.answer_from_tokens(tokenizer, ids, ids+capture.ids, metadata, BASE.MAX_NEW)
    score = verifier.score_response(case["task"], case["prefixes"][arm] + answer, case["language"])
    ended = metadata["finish_reason"] in ("STOP_SEQUENCE", "EOS")
    final = score["final_value"]
    return dict(id=case["id"], language=case["language"], carry=case["carry"], arm=arm, output=answer,
                metadata=metadata, **score, ended=ended, correct_end=ended and final == case["expected"],
                follows_wrong=ended and final == case["wrong_value"])


def summarize(rows):
    return {arm: {language: dict(
        count=len(group), correct_end=sum(row["correct_end"] for row in group), ended=sum(row["ended"] for row in group),
        valid_trace=sum(row["trace_valid"] is True for row in group), follows_wrong=sum(row["follows_wrong"] for row in group),
        final_contract=sum(row["final_contract"] for row in group))
        for language in ("ko", "en", "all")
        for group in ([row for row in rows if row["arm"] == arm and language in ("all", row["language"])],)}
        for arm in ARMS}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 before the fixed raw-validation phase")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    tokenizer = REF.completed.load_tokenizer()
    cases = prepare(tokenizer)
    body = REF.checkpoint()
    OUT.mkdir(exist_ok=False)
    inputs = OUT / "inputs.json"
    REF.native.publish(inputs, dict(cases=cases, mode="only model-side assistant prefix changes", max_new=BASE.MAX_NEW,
                                    source_file_sha=SOURCE_SHA, source_sha256=REF.file_sha(Path(__file__)),
                                    verifier_sha256=REF.file_sha(Path(verifier.__file__)), model_sha256=REF.CHECKPOINT_SHA256))
    model = REF.completed.load_model(body, 2942, "cpu")
    model.cfg.kv_dtype = "fp32"
    cutoff = args.stop_by.timestamp()
    rows = []
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for case in cases:
            for arm in ARMS:
                if time() >= cutoff:
                    raise TimeoutError("the supervised calculation diagnostic reached the approved cutoff")
                rows.append(generate(model, tokenizer, case, arm))
    if REF.file_sha(body) != REF.CHECKPOINT_SHA256:
        raise ValueError("the body bytes changed")
    summary = summarize(rows)
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=REF.file_sha(inputs), rows=rows, summary=summary))
    print("P109C_CALCULATION_PREFIX", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
