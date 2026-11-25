"""Separate a preceding chat turn from its token length on reused answer controls."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_long_arithmetic_retention_cpu as previous
from scripts import p106b_verified_trace_data as verifier


REF, BASE = previous.REF, previous.bare.BASE
OUT = REF.EVIDENCE / "p109c_context_turn_length_cpu_20261126"
END = datetime.fromisoformat("2026-11-26T06:48:00+09:00")
LENGTHS = (128, 256, 512)


def prepare(tokenizer):
    old_inputs, old_report = (previous.OUT / item for item in ("inputs.json", "report.json"))
    inputs, report = map(REF.completed.read_json, (old_inputs, old_report))
    if (report["status"] != "COMPLETE" or report["input_sha256"] != REF.file_sha(old_inputs)
            or inputs["model_sha256"] != REF.CHECKPOINT_SHA256
            or inputs["source_sha256"] != REF.file_sha(Path(previous.__file__))
            or report["summary"]["cases"] != 6):
        raise ValueError("the six positive context controls must match the completed comparison")
    head = tokenizer.encode("<|im_start|>user\n", add_special_tokens=False).ids
    cases = []
    for case in inputs["cases"]:
        lang = case["language"]
        medium = case["input_variants"]["medium"]
        confirmation = "확인했습니다." if lang == "ko" else "Acknowledged."
        tail_text = previous.BACKGROUND[lang][-1] + f"\n<|im_end|>\n<|im_start|>assistant\n{confirmation}<|im_end|>\n"
        sentence, end = tail_text.split("<|im_end|>", 1)
        tail = (tokenizer.encode(sentence, add_special_tokens=False).ids
                + tokenizer.encode("<|im_end|>" + end, add_special_tokens=False).ids + case["ids"])
        if medium[:len(head)] != head or medium[-len(tail):] != tail or len(head)+len(tail) >= min(LENGTHS):
            raise ValueError("the shortest turn may only remove earlier background tokens")
        new = {"one_sentence": head + tail}
        for length in LENGTHS:
            new[str(length)] = head + medium[-(length-len(head)):]
        cases.append(dict(case, input_variants=new))
    return cases, REF.file_sha(old_report)


def score(model, tokenizer, cases, deadline):
    rows = []
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for case in cases:
            expected = verifier.parse_final_line(case["expected"], case["language"])
            if not expected["ok"]:
                raise ValueError("the original case lacks an independently parsable final value")
            for arm, ids in case["input_variants"].items():
                wrapped = previous.ChunkedCalls(model, model.cfg, deadline)
                row = previous.bare.score(wrapped, tokenizer, dict(case, ids=ids))
                final = verifier.parse_final_line(row["answer"], case["language"])
                final_agrees = final["ok"] and final["value"] == expected["value"]
                ended = row["metadata"]["finish_reason"] in ("STOP_SEQUENCE", "EOS")
                rows.append(dict(row, arm=arm, final_agrees_and_ended=final_agrees and ended))
    return rows


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 before the fixed raw validation phase")
    tokenizer = REF.completed.load_tokenizer()
    cases, previous_root = prepare(tokenizer)
    body = REF.checkpoint()
    OUT.mkdir(exist_ok=False)
    inputs = OUT / "inputs.json"
    REF.native.publish(inputs, dict(cases=cases, previous_report_sha256=previous_root, model_sha256=REF.CHECKPOINT_SHA256,
                                    source_sha256=REF.file_sha(Path(__file__)), max_new=BASE.MAX_NEW))
    model = previous.streaming.model_for("short_fp32")
    model.cfg.kv_dtype = "fp32"
    rows = score(model, tokenizer, cases, args.stop_by.timestamp())
    if REF.file_sha(body) != REF.CHECKPOINT_SHA256:
        raise ValueError("the frozen v3 checkpoint changed")
    summary = {}
    for arm in cases[0]["input_variants"]:
        group = [row for row in rows if row["arm"] == arm]
        summary[arm] = dict(requests=len(group), usable=sum(row["usable"] for row in group),
                            final_agrees_and_ended=sum(row["final_agrees_and_ended"] for row in group),
                            prompt_tokens=[row["metadata"]["prompt_tokens"] for row in group])
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=REF.file_sha(inputs),
                                                rows=rows, summary=summary))
    print("P109C_CONTEXT_TURN_LENGTH", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
