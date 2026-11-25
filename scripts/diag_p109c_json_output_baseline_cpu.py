"""Check whether v3 can produce correct multi-value output on a short input."""

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
from time import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_kv_length_cpu as baseline
from tinylm.infer.generate import sample


END = datetime.fromisoformat("2026-11-26T15:00:00+09:00")
OUT = baseline.RECORD.with_name("p109c_json_output_baseline_cpu_20261126")
SIZE = (3, 5)
PROMPTS = {
    "ko": "답에 넣을 색 이름의 순서는 {values}입니다. answer 하나를 키로 갖는 JSON 객체만 쓰세요. 값은 색 이름을 주어진 순서로 한 칸씩 띄워 넣은 문자열입니다.",
    "en": "The colors for the answer, in order, are {values}. Output only a JSON object with one key, answer. Its string value must contain the colors in the stated order, separated by single spaces.",
}
VERBATIM = {
    "ko": "답 내용은 {values}입니다. answer 하나를 키로 갖고 답 내용 전체를 문자열 값으로 넣은 JSON 객체만 쓰세요.",
    "en": "The answer content is {values}. Output only a JSON object with one key, answer, whose string value is that entire content.",
}


def panel(tokenizer, verbatim=False):
    manifest = baseline.completed.read_json(baseline.MANIFEST)
    audit = baseline.completed.read_json(baseline.AUDIT)
    if (manifest["rows"] != 200 or manifest["concat_sha256"] != baseline.ARCHIVE_SHA
            or audit["source_sha256"] != baseline.ARCHIVE_SHA):
        raise ValueError("the original answer bytes and semantic assessment disagree")
    baseline.p106b_shards.verify(baseline.ARCHIVE, manifest)
    positives = defaultdict(list)
    for part in manifest["shards"]:
        for line in (baseline.ARCHIVE / part["path"]).read_bytes().splitlines():
            row = json.loads(line)
            language = row["language"]
            if (row["id"].startswith(f"final_{language}_format_") and row["reference_match"] is True
                    and row["id"] in audit["semantic_true_ids"][language]["usable"]):
                positives[language].append((row["id"], row["reference"]["answer"]))
    requests = []
    for language in PROMPTS:
        sequence = sorted(positives[language])
        if len(sequence) != 5 or len({value for _, value in sequence}) != 5:
            raise ValueError("the panel requires five distinct previously correct JSON values per language")
        repeated = sequence + sequence
        for count in SIZE:
            for offset in range(len(sequence)):
                items = repeated[offset:offset+count]
                values = [value for _, value in items]
                template = VERBATIM[language] if verbatim else PROMPTS[language]
                text = template.format(values=(" " if verbatim else ", ").join(values))
                prompt = baseline.serialize({"messages": baseline.manual.prompt_messages(text)}, "chatml",
                                            add_generation_prompt=True)
                ids = tokenizer.encode(prompt).ids
                if len(ids) + baseline.MAX_NEW > 1024:
                    raise ValueError("the composed answer requests must fit the short model setting")
                requests.append(dict(id=f"{language}_{count}_{offset}", language=language, count=count, text=text,
                                     prompt=prompt, ids=ids, originals=[identifier for identifier, _ in items],
                                     expected=" ".join(values)))
    return requests


def score(answer, expected):
    try:
        value = json.loads(answer, object_pairs_hook=list)
    except ValueError:
        return False
    return value == [("answer", expected)]


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    parser.add_argument("--verbatim", action="store_true", help="present the same answer string already joined")
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14, hide CUDA and provide a November 26 cutoff")
    cutoff = args.stop_by.timestamp()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    checkpoint = baseline.reference.checkpoint()
    tokenizer = baseline.completed.load_tokenizer()
    cases = panel(tokenizer, args.verbatim)
    output = OUT.with_name("p109c_json_output_verbatim_cpu_20261126") if args.verbatim else OUT
    earlier_sha = None
    if args.verbatim:
        previous = OUT / "inputs.json"
        old = baseline.completed.read_json(previous)["cases"]
        identity = lambda case: (case["id"], case["originals"], case["expected"])
        if [identity(case) for case in cases] != [identity(case) for case in old]:
            raise ValueError("verbatim controls must use the same twenty composed answers")
        earlier_sha = baseline.reference.file_sha(previous)
    output.mkdir(exist_ok=False)
    publish = baseline.native.publish
    inputs = output / "inputs.json"
    publish(inputs, dict(cases=cases, source_sha256=baseline.reference.file_sha(Path(__file__)),
                         model_sha256=baseline.reference.CHECKPOINT_SHA256, previous_answers_sha256=baseline.ARCHIVE_SHA,
                         previous_composition_input_sha256=earlier_sha, verbatim=args.verbatim,
                         max_new=baseline.MAX_NEW, cutoff=args.stop_by.isoformat()))
    model = baseline.completed.load_model(checkpoint, 2942, "cpu")
    model.cfg.kv_dtype = "fp32"
    rows = []
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for case in cases:
            if time() >= cutoff:
                raise TimeoutError("the JSON output baseline reached the approved cutoff")
            capture = baseline.first.DecodeSuffix(tokenizer, case["ids"])
            _, meta = sample(model, model.cfg, capture, case["prompt"], max_new=baseline.MAX_NEW,
                             temperature=0., top_k=1, device="cpu", eos_id=2, use_cache=True,
                             logits_last_only=True, return_metadata=True, stop_token_sequences=[[4]])
            answer, meta = baseline.manual.answer_from_tokens(tokenizer, case["ids"], case["ids"] + capture.ids,
                                                              meta, baseline.MAX_NEW)
            exact = score(answer, case["expected"])
            usable = exact and meta["content_tokens"] >= 12 and meta["finish_reason"] in ("STOP_SEQUENCE", "EOS")
            rows.append(dict(id=case["id"], language=case["language"], count=case["count"], answer=answer,
                             metadata=meta, exact=exact, usable=usable))
    if baseline.reference.file_sha(checkpoint) != baseline.reference.CHECKPOINT_SHA256:
        raise ValueError("the v3 weight bytes changed")
    publish(output / "report.json", dict(status="COMPLETE", input_sha256=baseline.reference.file_sha(inputs), rows=rows,
                                        correct=sum(row["exact"] for row in rows), usable=sum(row["usable"] for row in rows)))
    print("P109C_JSON_OUTPUT", len(rows), sum(row["exact"] for row in rows), sum(row["usable"] for row in rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
