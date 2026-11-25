"""Compare equal-token observed-value and arithmetic answer supervision."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
from random import Random
from time import monotonic, time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_single_numeric_cpu as numeric


diagnostic = numeric.prior
training = diagnostic.prior
reference = diagnostic.reference
OUT = reference.EVIDENCE / "p109c_arithmetic_target_cpu_20261126"
ARMS = ("observed_ce", "computed_ce")
FAMILIES = ("dispatch", "relay")
LANGUAGES = ("ko", "en")
TRAIN_SEED = 26112026
SURFACES = {
    ("ko", "dispatch"): (
        "물류 장부에 도자기 판 {seen}장이 기록되어 있습니다. 검사에 {operand}장을 빼고, 나머지가 {threshold}장 이상이어야 출고합니다.",
        "검사에 빼기 전 몇 장이 있었나요?", "검사용으로 뺀 뒤에는 몇 장이 남나요?", "지금 출고합니까?"),
    ("en", "dispatch"): (
        "A ceramic tile shipment starts with {seen} tiles. Withhold {operand} for inspection. The shipment leaves only if at least {threshold} tiles are left.",
        "What is the initial number of tiles?", "How many tiles remain after withholding the inspection tiles?", "May the shipment leave?"),
    ("ko", "relay"): (
        "수위계의 눈금이 {seen}입니다. 제어기는 이 눈금에 2를 곱한 값이 {threshold}보다 클 때만 수문을 엽니다.",
        "수위계에 표시된 눈금은 얼마입니까?", "그 눈금에 2를 곱한 값은 얼마입니까?", "수문을 엽니까?"),
    ("en", "relay"): (
        "A reservoir gauge shows {seen}. Its gate opens only when twice that reading is strictly higher than {threshold}.",
        "What reading appears on the gauge?", "What is the gauge reading multiplied by two?", "Should the gate open?"),
}
INTEGER = {"ko": "정수 하나만 쓰세요.", "en": "Write just one integer."}
DECISION = {"ko": "예 또는 아니요만 쓰세요.", "en": "Answer only Yes or No."}


def make_values(random, family):
    offset = (random.randint(1, 20), random.randint(1, 20))
    if family == "dispatch":
        threshold, operand = random.randint(310, 590), random.randint(15, 83)
        results = (threshold + offset[0], threshold - offset[1])
        seen = tuple(value + operand for value in results)
    else:
        threshold, operand = random.randint(520, 1700), 2
        seen = (threshold // 2 + offset[0], threshold // 2 - offset[1])
        results = tuple(value * operand for value in seen)
    return threshold, operand, seen, results


def encode_numeric(tokenizer, prompt, number):
    prefix, (tokens,) = numeric.scoring.continuations(tokenizer, numeric.scoring.chat(prompt), [str(number)])
    return (prefix + tokens + [training.EOT], len(prefix) - 1, len(tokens), False)


def compile_pair(tokenizer, random, language, family, occupied):
    template, observed_q, computed_q, decision_q = SURFACES[language, family]
    for _ in range(512):
        threshold, operand, seen, results = make_values(random, family)
        keys = {(family, value, operand) for value in seen}
        if keys & occupied:
            continue
        facts = [template.format(seen=value, operand=operand, threshold=threshold) for value in seen]
        numeric_rows, integer_prompts = [], []
        for fact, before, after in zip(facts, seen, results, strict=True):
            requests = [fact + "\n" + question + "\n" + INTEGER[language] for question in (observed_q, computed_q)]
            pair = [encode_numeric(tokenizer, text, value) for text, value in zip(requests, (before, after), strict=True)]
            numeric_rows.extend(pair)
            integer_prompts.append(requests)
        if any(numeric_rows[index][2] != numeric_rows[index+1][2] for index in (0, 2)):
            continue
        final = [fact + "\n" + decision_q + "\n" + DECISION[language] for fact in facts]
        decision_rows = training.encoded_pair(tokenizer, dict(language=language, prompts=final))
        occupied.update(keys)
        return dict(language=language, family=family, operand=operand, threshold=threshold, observed=seen,
                    values=results, integer_prompts=integer_prompts, decision_prompts=final,
                    numeric_rows=numeric_rows, decision_rows=decision_rows)
    raise ValueError("no disjoint arithmetic pair with a matched answer token count")


def scheduled_rows(case, arm, shared_decision):
    if shared_decision:
        return case["decision_rows"]
    offset = ARMS.index(arm)
    return [(tokens, start, width, index % 2 == offset)
            for index, (tokens, start, width, _) in enumerate(case["numeric_rows"])]


def expected_exposure(panel, arm):
    totals = dict(inputs=0, answer_targets=0, replay_targets=0)
    for index, case in enumerate(panel):
        rows = scheduled_rows(case, arm, index // 4 % 4 == 3)
        totals["inputs"] += sum(len(row[0]) - 1 for row in rows) + training.REPLAY_WIDTH
        totals["answer_targets"] += sum(row[2] + 1 for row in rows if row[3])
        totals["replay_targets"] += training.REPLAY_WIDTH
    return totals


def prepare():
    profile, tokenizer, checkpoint, _, previous, _, replay, validation = training.prepare()
    if profile != reference.completed.read_json(training.PROFILE):
        raise ValueError("the approved replay and raw VAL inputs differ from their previous profile")
    verified = diagnostic.pinned(diagnostic.VERIFIED, diagnostic.VERIFIED_SHA)
    source = diagnostic.pinned(reference.completed.ROOT / verified["source_path"], verified["source_sha256"])
    excluded = {
        (case["family"], fact["fields"]["observed"], fact["fields"]["reserved" if case["family"] == "dispatch" else "factor"])
        for case in verified["cases"] if case["family"] in FAMILIES for fact in case["facts"]
    }
    held_rules = [case for case in source["evaluation"] if case["family"] in FAMILIES]
    held_numbers = [case for case in numeric.cases() if case["family"] in FAMILIES]
    if len(held_numbers) != 24 or [case["id"] for case in held_numbers] != [case["id"] for case in held_rules]:
        raise ValueError("the frozen arithmetic holdout denominators differ")
    random = Random(TRAIN_SEED)
    occupied = set(excluded)
    panel = [compile_pair(tokenizer, random, language, family, occupied)
             for _ in range(training.STEPS) for language in LANGUAGES for family in FAMILIES]
    if len(panel) != len(replay) or expected_exposure(panel, ARMS[0]) != expected_exposure(panel, ARMS[1]):
        raise ValueError("the curriculum arms must have equal measured target budgets")
    numeric.prepare_scores(held_numbers, tokenizer)
    return profile, tokenizer, checkpoint, panel, replay, validation, previous, held_rules, held_numbers


def tune(model, arm, profile, panel, replay, check):
    model.clear_quant()
    model.cfg.infer_repeat = 1.
    model.train()
    if len(model.visit_schedule()) != 28:
        raise ValueError("training must retain the v3 R2 route")
    optimizer = torch.optim.AdamW(model.parameters(), lr=profile["lr"], weight_decay=0., foreach=False)
    totals = dict(inputs=0, answer_targets=0, replay_targets=0)
    start = monotonic()
    with (OUT / f"{arm}_updates.jsonl").open("x", encoding="utf-8", buffering=1) as stream:
        for step in range(training.STEPS):
            check()
            optimizer.zero_grad(set_to_none=True)
            for micro in range(training.ACCUM):
                index = 2 * (step * training.ACCUM + micro)
                rows = [row for case in panel[index:index+2] for row in scheduled_rows(case, arm, step % 4 == 3)]
                ce, raw, _, exposure = training.update_batch(model, rows, replay[index:index+2])
                ((ce + profile["replay_weight"] * raw) / training.ACCUM).backward()
                for key in totals:
                    totals[key] += exposure[key]
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            row = dict(step=step+1, seconds=monotonic()-start, targets=totals, gradient=float(norm))
            print(json.dumps(row), file=stream)
            if step == 0 or (step+1) % 8 == 0:
                print(arm, json.dumps(row), flush=True)
    if totals != expected_exposure(panel, arm):
        raise ValueError("the actual supervised and replay targets differ from the seal")
    model.eval()
    model.cfg.infer_repeat = 2.
    with torch.no_grad():
        model.freeze_quant()
    return totals


def assess_numbers(model, tokenizer, held_numbers, check):
    values = []
    for case in held_numbers:
        check()
        row = {key: case[key] for key in ("id", "family", "language")}
        row["facts"] = [{field: numeric.assess(model, tokenizer, case["language"], request)
                         for field, request in fact.items()} for fact in case["facts"]]
        values.append(row)
    return values


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= diagnostic.END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14, hide CUDA and provide a deadline in the November 26 authorization")
    cutoff = args.stop_by.timestamp()

    def check():
        if time() >= cutoff:
            raise TimeoutError("the arithmetic training stopped at the approved cutoff")

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile, tokenizer, checkpoint, panel, replay, validation, previous, held_rules, held_numbers = prepare()
    old = diagnostic.pinned(diagnostic.operator_trial.RECORD / "ce_assessment.json", diagnostic.ASSESSMENT_SHA["ce"])
    parent = old["training"]["body_sha256"]
    check()
    OUT.mkdir(exist_ok=False)
    publish = reference.native.publish
    inputs = OUT / "inputs.json"
    exposure = expected_exposure(panel, ARMS[0])
    publish(inputs, dict(train=panel, held_numbers=held_numbers, held_decisions=held_rules,
                         source_sha256=reference.file_sha(Path(__file__)), ce_parent_sha256=parent,
                         replay_sha256=profile["replay_sha256"], raw_val_sha256=profile["val_sha256"],
                         lr=profile["lr"], replay_weight=profile["replay_weight"], train_seed=TRAIN_SEED,
                         steps=training.STEPS, reserved=profile["reserved"], exposure=exposure,
                         gates=dict(arithmetic_delta=8, arithmetic_language_delta=3, decision_delta=4,
                                    decision_language_delta=2, raw_nll_delta=.005)))
    summaries = {}
    with sdpa_kernel(SDPBackend.MATH):
        for arm in ARMS:
            check()
            torch.manual_seed(1337)
            model, body = diagnostic.load_body("ce", parent, checkpoint)
            start = monotonic()
            totals = tune(model, arm, profile, panel, replay, check)
            checkpoint_out = OUT / f"{arm}_body.pt"
            with checkpoint_out.open("xb") as stream:
                torch.save(dict(schema="P109C_ARITHMETIC_TARGET_V1", model=model.state_dict(),
                                parent_sha256=parent, arm=arm, post_updates=training.STEPS), stream)
            comparison = training.assess(model, tokenizer, held_rules, previous, validation, cutoff)
            with torch.inference_mode():
                numbers = assess_numbers(model, tokenizer, held_numbers, check)
            if reference.file_sha(body) != parent or reference.file_sha(checkpoint) != reference.CHECKPOINT_SHA256:
                raise ValueError("a frozen parent changed")
            report = dict(numbers=numbers, assessment=comparison, exposure=totals, elapsed_seconds=monotonic()-start,
                          body_sha256=reference.file_sha(checkpoint_out))
            publish(OUT / f"{arm}_assessment.json", report)
            summaries[arm] = dict(numbers=numeric.summary(numbers), decisions=comparison["new_rules"]["counts"],
                                  previous_decisions=comparison["previous_dev"]["counts"],
                                  raw_val_nll=comparison["raw_val_nll"], body_sha256=report["body_sha256"])
            print(arm, json.dumps(summaries[arm]), flush=True)
            del model
    publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=reference.file_sha(inputs), summary=summaries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
