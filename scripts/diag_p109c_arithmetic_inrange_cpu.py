"""Separate learned calculations from transfer to unseen numbers in the same range."""

from argparse import ArgumentParser
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
from random import Random
from time import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_arithmetic_target_cpu as original


OUT = original.OUT.with_name("p109c_arithmetic_inrange_cpu_20261126")
END = datetime.fromisoformat("2026-11-26T06:42:00+09:00")
SEED = 261126014
FAMILIES = {"dispatch": "after_reservation", "relay": "doubled"}
TRAINED_ROUNDS = (0, 12, 24, 36)


def graded_case(identifier, case):
    rows = []
    for side, prompts in enumerate(case["integer_prompts"]):
        rows.append({key: dict(text=prompt, right=case[values][side], other=case[values][1-side])
                     for key, prompt, values in zip(("observed", FAMILIES[case["family"]]), prompts,
                                                     ("observed", "values"), strict=True)})
    return dict(id=identifier, language=case["language"], family=case["family"], facts=rows)


def panel(tokenizer, previous):
    train = previous["train"]
    exposed = [row for index, row in enumerate(train) if index // 4 % 4 != 3]
    if len(exposed) != 192:
        raise ValueError("the admitted run needs 192 rule pairs with direct numeric supervision")
    ranges = {}
    used = {(row["family"], value, row["operand"]) for row in train for value in row["observed"]}
    for family in FAMILIES:
        values = [n for row in exposed if row["family"] == family for n in row["values"]]
        ranges[family] = (min(values), max(values))
    seen = [graded_case(f"seen-{index}", train[index]) for group in TRAINED_ROUNDS for index in range(group * 4, group * 4 + 4)]
    random = Random(SEED)
    fresh = []
    for _ in TRAINED_ROUNDS:
        for language in original.LANGUAGES:
            for family in FAMILIES:
                low, high = ranges[family]
                for _ in range(512):
                    case = original.compile_pair(tokenizer, random, language, family, used)
                    if all(low <= value <= high for value in case["values"]):
                        fresh.append(graded_case(f"fresh-{len(fresh)}", case))
                        break
                else:
                    raise ValueError("unable to seal a disjoint same-range arithmetic pair")
    old_text = {question for row in train for pair in row["integer_prompts"] for question in pair}
    old_text.update(request["text"] for case in previous["held_numbers"] for fact in case["facts"] for request in fact.values())
    new_text = {request["text"] for case in fresh for fact in case["facts"] for request in fact.values()}
    counts = lambda cases: Counter((row["family"], row["language"]) for row in cases)
    if (len(seen) != 16 or len(fresh) != 16 or counts(seen) != counts(fresh)
            or len(new_text) != 64 or old_text & new_text):
        raise ValueError("the old and new numeric cohorts have changed identities or overlap")
    panels = dict(trained=seen, unseen_same_range=fresh)
    for cases in panels.values():
        original.numeric.prepare_scores(cases, tokenizer)
    return panels, ranges


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 and the small diagnostic return window")
    deadline = args.stop_by.timestamp()

    def check():
        if time() >= deadline:
            raise TimeoutError("the same-range diagnostic reached its cutoff")

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    ref = original.reference
    parent_path = ref.checkpoint()
    tokenizer = ref.completed.load_tokenizer()
    inputs, report = (original.OUT / name for name in ("inputs.json", "report.json"))
    previous, completed = map(ref.completed.read_json, (inputs, report))
    if (completed["status"] != "COMPLETE" or completed["input_sha256"] != ref.file_sha(inputs)
            or previous["source_sha256"] != ref.file_sha(Path(original.__file__))):
        raise ValueError("the completed training and archived inputs must agree")
    panels, ranges = panel(tokenizer, previous)
    pins = {"parent": previous["ce_parent_sha256"],
            **{arm: completed["summary"][arm]["body_sha256"] for arm in original.ARMS}}
    OUT.mkdir(exist_ok=False)
    sealed = OUT / "inputs.json"
    ref.native.publish(sealed, dict(panels=panels, ranges=ranges, seed=SEED, checkpoint_sha256=pins,
                                   training_input_sha256=ref.file_sha(inputs), training_report_sha256=ref.file_sha(report),
                                   source_sha256=ref.file_sha(Path(__file__)),
                                   selection="Four actual numeric rounds and four new pairs per family and language"))
    results = {}
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for arm, stamp in pins.items():
            check()
            model, shared = original.diagnostic.load_body("ce", pins["parent"], parent_path)
            if arm == "parent":
                path = shared
            else:
                path = original.OUT / f"{arm}_body.pt"
                if ref.file_sha(path) != stamp:
                    raise ValueError("a trained arithmetic checkpoint changed")
                body = torch.load(path, map_location="cpu", mmap=True, weights_only=True)
                if (body["schema"] != "P109C_ARITHMETIC_TARGET_V1" or body["parent_sha256"] != pins["parent"]
                        or body["arm"] != arm or body["post_updates"] != previous["steps"]):
                    raise ValueError("the delivered arithmetic body has a different training history")
                model.clear_quant()
                model.load_state_dict(body["model"], strict=True)
                model.freeze_quant()
            arm_rows = {name: original.assess_numbers(model, tokenizer, cases, check) for name, cases in panels.items()}
            summaries = {name: original.numeric.summary(rows) for name, rows in arm_rows.items()}
            if ref.file_sha(path) != stamp or ref.file_sha(parent_path) != ref.CHECKPOINT_SHA256:
                raise ValueError("a frozen source body changed during the diagnostic")
            ref.native.publish(OUT / f"{arm}.json", dict(rows=arm_rows, summary=summaries, checkpoint_sha256=stamp))
            results[arm] = summaries
            print(arm, json.dumps(summaries, ensure_ascii=False), flush=True)
            del model
    ref.native.publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=ref.file_sha(sealed), summary=results,
                                                reuse_small_range=completed["summary"]))


if __name__ == "__main__":
    main()
