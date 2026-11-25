"""Test whether worked examples recover a short correct long-answer baseline."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
from time import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_json_output_baseline_cpu as prior
from tinylm.infer.generate import sample


BASE = prior.baseline
REF = BASE.reference
VERBATIM = prior.OUT.with_name("p109c_json_output_verbatim_cpu_20261126")
OUT = prior.OUT.with_name("p109c_json_output_demonstrations_cpu_20261126")
END = datetime.fromisoformat("2026-11-26T06:48:00+09:00")
ARMS = ("format_examples", "sequence_examples")
EXAMPLES = {
    "ko": {"format_examples": ("달력", "부채"), "sequence_examples": ("달력 부채 서랍", "수건 접시 주전자 천 책상")},
    "en": {"format_examples": ("calendar", "fan"), "sequence_examples": ("calendar fan drawer", "towel plate kettle cloth desk")},
}


def compile_panel(tokenizer):
    inputs, report = (VERBATIM / name for name in ("inputs.json", "report.json"))
    frozen = BASE.completed.read_json(inputs)
    previous = BASE.completed.read_json(report)
    if (previous["status"] != "COMPLETE" or previous["input_sha256"] != REF.file_sha(inputs)
            or frozen["cases"] != prior.panel(tokenizer, verbatim=True) or previous["correct"] or previous["usable"]):
        raise ValueError("the fixed no-demonstration source must match the completed zero-hit baseline")
    panel = []
    for case in frozen["cases"]:
        language, text = case["language"], case["text"]
        user = BASE.manual.prompt_messages(text)
        if user[-1] != {"role": "user", "content": text}:
            raise ValueError("the frozen user request changed")
        conditions = {}
        for arm, contents in EXAMPLES[language].items():
            examples = []
            for value in contents:
                if set(value.split()) & set(case["expected"].split()):
                    raise ValueError("an example discloses part of a test answer")
                examples.extend((dict(role="user", content=prior.VERBATIM[language].format(values=value)),
                                 dict(role="assistant", content=json.dumps({"answer": value}, ensure_ascii=False))))
            prompt = BASE.serialize({"messages": [*user[:-1], *examples, user[-1]]}, "chatml",
                                    add_generation_prompt=True)
            ids = tokenizer.encode(prompt).ids
            if not len(case["ids"]) < len(ids) <= 1024 - BASE.MAX_NEW:
                raise ValueError("a demonstration request is outside the original model context")
            conditions[arm] = dict(prompt=prompt, ids=ids)
        panel.append(dict(id=case["id"], language=language, expected=case["expected"], requests=conditions))
    return panel, inputs, report


def measure(model, tokenizer, case, arm):
    request = case["requests"][arm]
    capture = BASE.first.DecodeSuffix(tokenizer, request["ids"])
    _, meta = sample(model, model.cfg, capture, request["prompt"], max_new=BASE.MAX_NEW,
                     temperature=0., top_k=1, device="cpu", eos_id=2, use_cache=True,
                     logits_last_only=True, return_metadata=True, stop_token_sequences=[[4]])
    answer, meta = BASE.manual.answer_from_tokens(tokenizer, request["ids"], request["ids"] + capture.ids, meta,
                                                  BASE.MAX_NEW)
    exact = prior.score(answer, case["expected"])
    return dict(id=case["id"], language=case["language"], arm=arm, answer=answer, metadata=meta, exact=exact,
                usable=exact and meta["content_tokens"] >= 12 and meta["finish_reason"] in ("STOP_SEQUENCE", "EOS"))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("pin the small CPU diagnostic to logical CPU 14")
    cutoff = args.stop_by.timestamp()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    checkpoint = REF.checkpoint()
    tokenizer = BASE.completed.load_tokenizer()
    cases, old_input, old_report = compile_panel(tokenizer)
    publish = BASE.native.publish
    OUT.mkdir(exist_ok=False)
    inputs = OUT / "inputs.json"
    publish(inputs, dict(cases=cases, old_input_sha256=REF.file_sha(old_input), old_report_sha256=REF.file_sha(old_report),
                         model_sha256=REF.CHECKPOINT_SHA256, source_sha256=REF.file_sha(Path(__file__)),
                         max_new=BASE.MAX_NEW, useful_by_language=2))
    rows = []
    model = BASE.completed.load_model(checkpoint, 2942, "cpu")
    model.cfg.kv_dtype = "fp32"
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for index, case in enumerate(cases):
            for arm in ARMS if index % 2 == 0 else reversed(ARMS):
                if time() >= cutoff:
                    raise TimeoutError("the demonstration comparator reached its stop time")
                rows.append(measure(model, tokenizer, case, arm))
    if REF.file_sha(checkpoint) != REF.CHECKPOINT_SHA256:
        raise ValueError("the original v3 body changed")
    counts = {arm: {language: dict(exact=sum(row["exact"] for row in rows if row["arm"] == arm and row["language"] == language),
                                  usable=sum(row["usable"] for row in rows if row["arm"] == arm and row["language"] == language))
                    for language in EXAMPLES} for arm in ARMS}
    gate = all(row["usable"] >= 2 for row in counts["sequence_examples"].values())
    publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=REF.file_sha(inputs), rows=rows,
                                      counts=counts, eligible_for_long_context_probe=gate))
    print("P109C_COPY_DEMONSTRATIONS", json.dumps(counts), gate, flush=True)


if __name__ == "__main__":
    main()
