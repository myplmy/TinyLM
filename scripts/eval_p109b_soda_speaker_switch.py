"""Probe grounded question switching on unseen candidate groups using the frozen P109B arm."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
import json
from pathlib import Path
from unittest.mock import patch

from scripts import diag_p106b_soda_speaker_switch as source
from scripts import eval_p109b_first_use as first_use
from scripts import run_p109c_scratch330 as supervisor
from tinylm.infer.generate import sample


ROOT = first_use.pair.ROOT
OUT = source.OUT.parent / "p109b_soda_speaker_switch_gpu_v1_20261121"
POLICY = "uniform_r2"
END = datetime.fromisoformat("2026-11-22T13:00:00+09:00")
MAX_NEW = 20


def inputs():
    from tokenizers import Tokenizer

    pins = first_use.previous.frozen.audit.Inputs()
    manifest = source.OUT / "candidate_shards_manifest.json"
    paths = (Path(__file__), Path(source.__file__), Path(first_use.__file__), Path(first_use.previous.__file__),
             Path(supervisor.__file__), source.OUT / "report.json", manifest,
             ROOT / "tinylm/infer/generate.py", ROOT / "tinylm/model/transformer.py",
             ROOT / "tinylm/model/modules.py", ROOT / "tinylm/model/ternary.py")
    for path in paths:
        pins.add(path)
    pins.add(first_use.pair.TOKENIZER, first_use.previous.TOKENIZER_SHA)
    readback = first_use.pair.OUT / "readback.json"
    pins.add(readback)
    arm = first_use.previous.read(readback)["arms"][POLICY]
    if (arm["tag"] != first_use.pair.ARMS[POLICY] or arm["updates"] != first_use.pair.STEPS
            or arm["draw_tokens"] != first_use.pair.STEPS * first_use.pair.MICRO * first_use.pair.ACCUM * first_use.pair.SEQ):
        raise ValueError("requires the completed uniform R2 arm")
    pins.add(ROOT / arm["checkpoint"], arm["checkpoint_sha256"])
    tokenizer = Tokenizer.from_file(str(first_use.pair.TOKENIZER))

    def message(messages, index):
        return messages[index]["content"][0]["text"]

    data = json.loads(manifest.read_bytes())
    source.exact.previous.verify(source.OUT, data)
    cases = []
    for shard in data["shards"]:
        shard_file = source.OUT / shard["path"]
        pins.add(shard_file)
        for line in shard_file.read_bytes().splitlines():
            row = json.loads(line)
            meta, messages = row["meta"], row["messages"]
            if meta["independent_candidate_split"] != "heldout":
                continue
            split = message(messages, 0).rsplit("\n\nWho says this exact utterance? ", 1)
            if len(split) != 2:
                raise ValueError("the held-out dialogue requires its exact first question")
            a, b = meta["target_labels"]
            second = message(messages, 2).removeprefix("Refer to the same dialogue for a different speaker. ")
            second_only = split[0] + "\n\n" + second
            cases.append(dict(root=meta["source_group_id"], first=message(messages, 0), second=second,
                              second_only=second_only, expected=[a, b]))
    report = first_use.previous.read(source.OUT / "report.json")
    if len({case["root"] for case in cases}) != len(cases) or len(cases) != report["inventory"]["heldout"]["groups"]:
        raise ValueError("the held-out source-group count differs")
    return pins, tokenizer, cases


def generate(model, tokenizer, prompt, expected):
    ids = tokenizer.encode(prompt).ids
    if len(ids) > first_use.INPUT or len(ids) + MAX_NEW > model.cfg.max_seq_len:
        raise ValueError("the held-out request exceeds the existing input budget")
    capture = first_use.DecodeSuffix(tokenizer, ids)
    answer, receipt = sample(model, model.cfg, capture, prompt, max_new=MAX_NEW, temperature=0., top_k=0,
                             device="cuda", eos_id=2, stop_token_sequences=[[4]], logits_last_only=True,
                             return_metadata=True)
    correct = first_use.strict(answer) == first_use.strict(expected)
    complete = receipt["finish_reason"] in {"EOS", "STOP_SEQUENCE"}
    return dict(answer=answer, ids=capture.ids, finish=receipt["finish_reason"], exact=correct,
                exact_with_end=correct and complete, input_tokens=len(ids))


def worker(path, checksum, _resume, record, cutoff):
    import time

    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel

    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        source_receipt = json.loads(supervisor.manifest_bytes(path, checksum))
        pins, tokenizer, cases = inputs()
        if source_receipt != dict(cases=cases, pins=pins.files, policy=POLICY, max_new=MAX_NEW):
            raise ValueError("the prepared holdout or runtime source differs")
        torch.set_num_threads(2)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        model, _ = first_use.previous.load_model(torch, pins, POLICY)
        rows = []
        with sdpa_kernel(SDPBackend.MATH):
            for item in cases:
                if time.time() >= cutoff:
                    raise TimeoutError("evaluation reached its cutoff")
                expectation_a, expectation_b = item["expected"]
                first_prompt = first_use.dialog(item["first"])
                first = generate(model, tokenizer, first_prompt, expectation_a)
                # A terminated answer is inserted as text, so emitted structural IDs cannot open a turn.
                continuation = first_prompt + first["answer"] + "<|im_end|>\n" + first_use.dialog(item["second"])
                second = generate(model, tokenizer, continuation, expectation_b)
                single = generate(model, tokenizer, first_use.dialog(item["second_only"]), expectation_b)
                rows.append(dict(root=item["root"], expected=item["expected"], first=first, switched=second,
                                 second_only=single, copied_previous=bool(first["answer"].strip()) and
                                 first_use.strict(first["answer"]) == first_use.strict(second["answer"])))
        pins.unchanged()
        supervisor.publish(record / "report.json", dict(policy=POLICY, groups=len(rows), rows=rows,
            first_exact=sum(row["first"]["exact"] for row in rows),
            switched_exact=sum(row["switched"]["exact"] for row in rows),
            second_only_exact=sum(row["second_only"]["exact"] for row in rows),
            both_exact_with_end=sum(row["first"]["exact_with_end"] and row["switched"]["exact_with_end"] for row in rows),
            copied_previous=sum(row["copied_previous"] for row in rows),
            peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
            peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    args = parser.parse_args()
    pins, tokenizer, cases = inputs()
    if max(len(tokenizer.encode(first_use.dialog(case["first"])).ids) for case in cases) > 896:
        raise ValueError("prompt length exceeds the chosen budget")
    if args.mode == "check":
        print(f"SODA_SWITCH_CHECK groups={len(cases)} prompts={3 * len(cases)}")
        return 0
    from tempfile import TemporaryDirectory

    stop_by = min(END, datetime.now().astimezone() + timedelta(minutes=8))
    with TemporaryDirectory(prefix="p109b_soda_switch_input_") as directory:
        path = Path(directory) / "profile.json"
        supervisor.publish(path, dict(cases=cases, pins=pins.files, policy=POLICY, max_new=MAX_NEW))
        with patch.object(supervisor, "gpu_worker", worker):
            return supervisor.supervise(path, supervisor.file_sha(path), False, OUT, stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
