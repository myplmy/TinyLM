"""Localize carry prediction to operand, digit, or sum evidence on the recovery DEV cases."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
from time import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_arithmetic_recovery_cpu as prior


CALC, REF = prior.calc, prior.REF
TAG = "p109c_carry_evidence_cpu_20261126"
PROFILE = REF.EVIDENCE / f"{TAG}_profile.json"
OUT = REF.EVIDENCE / TAG
MAX_NEW = 8
END = datetime.fromisoformat("2026-11-26T14:00:00+09:00")
ARMS = ("operands", "digits", "true_sum", "wrong_sum")


def request(case, arm):
    a, b = (case["task"][name] for name in ("a", "b"))
    left, right = a % 10, b % 10
    total = left + right
    carried = total >= 10
    if int(carried) != case["carry"]:
        raise ValueError("the original case and the local carry disagree")
    changed = total - 10 if carried else total + 10
    if case["language"] == "ko":
        notes = dict(operands="", digits=f"메모에 적힌 일의 자리: {left}와 {right}.\n",
                     true_sum=f"메모에 적힌 일의 자리 합: {total}.\n",
                     wrong_sum=f"메모에 적힌 일의 자리 합: {changed}.\n")
        prompt = (f"두 수: {a}와 {b}.\n" + notes[arm] +
                  "두 수의 일의 자리 합이 10 이상이면 1, 10 미만이면 0입니다. "
                  "메모가 있어도 두 수를 기준으로 검산하세요. 받아올림 숫자 하나만 쓰세요.")
    else:
        notes = dict(operands="", digits=f"Ones digits in the note: {left} and {right}.\n",
                     true_sum=f"Ones sum in the note: {total}.\n", wrong_sum=f"Ones sum in the note: {changed}.\n")
        prompt = (f"Two numbers: {a} and {b}.\n" + notes[arm] +
                  "The carry is 1 if the ones sum is at least 10, or 0 if it is less than 10. "
                  "Use the two numbers to check any note. Reply with the single carry digit.")
    return CALC.BASE.serialize({"messages": [{"role": "user", "content": prompt}]}, "chatml", add_generation_prompt=True)


def prepare():
    input_path, report_path = (prior.OUT / name for name in ("inputs.json", "report.json"))
    source, resolved = map(REF.completed.read_json, (input_path, report_path))
    if (resolved["status"] != "COMPLETE" or resolved["input_sha256"] != REF.file_sha(input_path)
            or source["parent_sha256"] != REF.CHECKPOINT_SHA256 or resolved["comparison"]["gates"]["recovery"]):
        raise ValueError("the targeted diagnostic follows the verified failed recovery comparison")
    tokenizer = REF.completed.load_tokenizer()
    cases = []
    for case in source["held_cases"]:
        arms = {}
        for arm in ARMS:
            prompt = request(case, arm)
            ids = tokenizer.encode(prompt).ids
            continuations = [tokenizer.encode(prompt + label).ids for label in ("0", "1")]
            if any(seq[:-1] != ids for seq in continuations) or continuations[0][-1] == continuations[1][-1]:
                raise ValueError("0 and 1 must each append one distinct token to exactly the same prompt")
            arms[arm] = dict(prompt=prompt, ids=ids, choices=[seq[-1] for seq in continuations])
        cases.append(dict(id=case["id"], language=case["language"], gold=case["carry"], arms=arms,
                          same_note_arm_length=len(arms["true_sum"]["ids"]) == len(arms["wrong_sum"]["ids"])))
    if (len(cases) != 32 or len({case["id"] for case in cases}) != 16
            or any(sum(case["language"] == lang and case["gold"] == gold for case in cases) != 8
                   for lang in ("ko", "en") for gold in (0, 1))):
        raise ValueError("the same language and target-balanced 16 DEV facts are required")
    return dict(cases=cases, parent_sha256=REF.CHECKPOINT_SHA256, recovery_inputs_sha256=REF.file_sha(input_path),
                recovery_report_sha256=REF.file_sha(report_path), max_new=MAX_NEW,
                source_sha256=REF.file_sha(Path(__file__))), tokenizer


def score(model, tokenizer, case, arm):
    choice = case["arms"][arm]
    ids = choice["ids"]
    hidden = model(torch.tensor([ids], dtype=torch.long), return_hidden=True)
    logits = model._head_logits(hidden[:, -1]).float()[0].log_softmax(-1)[choice["choices"]]
    if not torch.isfinite(logits).all():
        raise ValueError("the first token score must be finite")
    capture = CALC.frozen.FrozenPrefix(tokenizer, ids)
    _, meta = CALC.frozen.sample(model, model.cfg, capture, choice["prompt"], max_new=MAX_NEW, temperature=0.,
                                 top_k=1, device="cpu", eos_id=2, use_cache=True, logits_last_only=True,
                                 return_metadata=True, stop_token_sequences=[[4]])
    answer, meta = CALC.BASE.manual.answer_from_tokens(tokenizer, ids, ids + capture.ids, meta, MAX_NEW)
    ended = meta["finish_reason"] in ("STOP_SEQUENCE", "EOS")
    stripped = answer.strip()
    digit = int(stripped) if stripped in ("0", "1") else None
    left, right = logits.tolist()
    pick = int(right > left) if right != left else None
    return dict(id=case["id"], language=case["language"], gold=case["gold"], arm=arm, answer=answer, metadata=meta,
                digit=digit, ended=ended, exact_and_ended=ended and digit == case["gold"],
                choice_logp=[left, right], choice_prediction=pick, both_note_lengths_equal=case["same_note_arm_length"])


def summarize(rows):
    result = {}
    for language in ("all", "ko", "en"):
        group = [row for row in rows if language in ("all", row["language"])]
        arms = {arm: [row for row in group if row["arm"] == arm] for arm in ARMS}
        result[language] = {arm: dict(rows=len(values), ends=sum(row["ended"] for row in values),
                                      exact=sum(row["exact_and_ended"] for row in values),
                                      first_token=sum(row["choice_prediction"] == row["gold"] for row in values))
                            for arm, values in arms.items()}
        pairs = list(zip(arms["true_sum"], arms["wrong_sum"], strict=True))
        if any((left["id"], left["language"]) != (right["id"], right["language"]) for left, right in pairs):
            raise ValueError("same facts must be compared under the opposite note")
        equal = [(left, right) for left, right in pairs if left["both_note_lengths_equal"]]
        result[language]["paired_notes"] = dict(rows=len(pairs), equal_length=len(equal),
            same_carry=sum(left["ended"] and right["ended"] and left["digit"] is not None and left["digit"] == right["digit"]
                           for left, right in pairs),
            follows_both_sums=sum(left["exact_and_ended"] and right["ended"] and right["digit"] == 1 - right["gold"]
                                  for left, right in pairs),
            equal_length_follows_both_sums=sum(left["exact_and_ended"] and right["ended"] and right["digit"] == 1 - right["gold"]
                                               for left, right in equal))
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("keep the final GPU comparison independent and use CPU 14 only")
    if args.mode == "prepare":
        if args.profile_sha256 or args.stop_by or PROFILE.exists() or OUT.exists():
            parser.error("prepare needs a model-free new profile")
        profile, _ = prepare()
        REF.native.publish(PROFILE, profile)
        print(PROFILE, REF.file_sha(PROFILE), sum(case["same_note_arm_length"] for case in profile["cases"]), flush=True)
        return
    if (not args.profile_sha256 or args.stop_by is None or args.stop_by.tzinfo is None
            or not datetime.now().astimezone() < args.stop_by <= END or OUT.exists()):
        parser.error("use the pending source seal and a future CPU cutoff")
    profile, tokenizer = prepare()
    if profile != json.loads(REF.native.manifest_bytes(PROFILE, args.profile_sha256)):
        raise ValueError("the frozen carry comparison changed")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    checkpoint = REF.checkpoint()
    model = REF.completed.load_model(checkpoint, 2942, "cpu")
    if len(model.visit_schedule()) != 28:
        raise ValueError("the model must run the same native R2 evaluation route")
    OUT.mkdir(exist_ok=False)
    rows = []
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for case in profile["cases"]:
            for arm in ARMS:
                if time() >= args.stop_by.timestamp():
                    raise TimeoutError("the carry evidence comparison reached its cutoff")
                rows.append(score(model, tokenizer, case, arm))
    if REF.file_sha(checkpoint) != REF.CHECKPOINT_SHA256:
        raise ValueError("the frozen base checkpoint changed")
    summary = summarize(rows)
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", profile_sha256=args.profile_sha256.upper(),
                                                rows=rows, summary=summary))
    print("P109C_CARRY_EVIDENCE", json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
