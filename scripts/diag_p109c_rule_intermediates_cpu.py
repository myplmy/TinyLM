"""Separate numeric intermediates from final decisions on the frozen P109C rule pairs."""

from argparse import ArgumentParser
from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import re
from time import time
from unicodedata import normalize

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_rule_operator_cpu as operator_trial


prior = operator_trial.prior
reference = prior.reference
END = datetime.fromisoformat("2026-11-26T15:00:00+09:00")
OUT = reference.EVIDENCE / "p109c_rule_intermediates_cpu_20261126"
VERIFIED = reference.EVIDENCE / "p109c_rule_operator_intermediates_readback_20261125.json"
VERIFIED_SHA = "6BE651219BE30B9B666D08B8F62F15044405848B3706578B18341B2132B38737"
ASSESSMENT_SHA = {
    "ce": "B7938590584FDC8291ECC06C0C9C7FB090BA78B9BB97FF8269CAD2395B441F51",
    "actual_relation": "6DC7F3B57CFDAAF8F0548B0180DFF1C9DD5F13D2584ADA4D99A2498A24C2111E",
}
FIELD_ORDER = {
    "dispatch": ("observed", "reserved", "minimum", "after_reservation"),
    "relay": ("observed", "factor", "threshold", "doubled"),
    "orchard": ("observed", "lower", "upper"),
    "permit_desk": ("observed", "minimum", "excluded"),
}
TERMS = {
    "ko": dict(observed="문장에 적힌 실제 수치", reserved="따로 뺄 수량", minimum="최소값", factor="곱하는 수",
               threshold="기준값", lower="하한", upper="상한", excluded="제외값",
               after_reservation="따로 뺀 뒤 남은 수량", doubled="곱한 뒤의 값"),
    "en": dict(observed="stated observed value", reserved="reserved amount", minimum="minimum", factor="multiplier",
               threshold="threshold", lower="lower bound", upper="upper bound", excluded="excluded value",
               after_reservation="amount remaining after reservation", doubled="value after multiplication"),
}


def pinned(path, checksum):
    return json.loads(reference.native.manifest_bytes(path, checksum))


def request_set(prompt, language, family, fact):
    lines = prompt.splitlines()
    if lines[-1] != {"ko": "예 또는 아니요만 쓰세요.", "en": "Answer only Yes or No."}[language]:
        raise ValueError("the existing answer instruction differs")
    fields = fact["fields"]
    order = FIELD_ORDER[family]
    if set(order) != fields.keys():
        raise ValueError("the verified numeric fields differ from the rule family")
    computed = order[-1:] if family in ("dispatch", "relay") else ()
    operands = order[:-1] if computed else order
    names = TERMS[language]
    ordered = ", ".join(names[key] for key in order)
    comparisons = ", ".join(f"{names[computed[0] if computed else 'observed']} / {names[key]}"
                            for key in operands[1:] if key != "reserved" and key != "factor")
    if language == "ko":
        probe = (f"이 순서의 숫자만 쉼표로 적으세요. {ordered}. 그 뒤 |를 쓰고 "
                 f"다음 왼쪽과 오른쪽을 비교한 기호를 순서대로 쉼표로 적으세요. {comparisons}. "
                 "비교 기호는 <, =, > 중 하나입니다.")
        label = f"검산 메모 ({names[computed[0] if computed else 'observed']})"
    else:
        probe = (f"List only these numbers in order, separated by commas: {ordered}. Then write | and "
                 f"list the comparison signs for these left/right pairs in order: {comparisons}. "
                 "Each sign is <, =, or >.")
        label = f"Verification note ({names[computed[0] if computed else 'observed']})"
    numeric = fields[computed[0] if computed else "observed"]
    return dict(probe="\n".join([*lines[:-2], probe]),
                blank="\n".join([*lines[:-2], f"{label}: ?", *lines[-2:]]),
                value="\n".join([*lines[:-2], f"{label}: {numeric}", *lines[-2:]]),
                operands=[fields[key] for key in operands], computed=[fields[key] for key in computed],
                relations=[row["relation"] for row in fact["comparisons"]])


def score_probe(answer, expected):
    numeric_part, sep, relation_part = normalize("NFKC", answer).strip().partition("|")
    numbers = [part.strip() for part in numeric_part.split(",")]
    expected_count = len(expected["operands"]) + len(expected["computed"])
    has_numbers = len(numbers) == expected_count and all(re.fullmatch(r"-?\d+", word) for word in numbers)
    integers = [int(value) for value in numbers] if has_numbers else None
    relations = [part.strip() for part in relation_part.split(",")]
    has_relations = bool(sep) and len(relations) == len(expected["relations"]) and set(relations) <= {"<", "=", ">"}
    boundary = len(expected["operands"])
    return dict(numbers_parsed=has_numbers, relations_parsed=has_relations,
                operands_correct=has_numbers and integers[:boundary] == expected["operands"],
                computed_correct=(has_numbers and integers[boundary:] == expected["computed"]
                                  if expected["computed"] else None),
                relations_correct=has_relations and relations == expected["relations"])


def sealed_panel():
    derivation = pinned(VERIFIED, VERIFIED_SHA)
    source = pinned(reference.completed.ROOT / derivation["source_path"], derivation["source_sha256"])
    panel = []
    for item, verified in zip(source["evaluation"], derivation["cases"], strict=True):
        if any(item[key] != verified[key] for key in ("id", "family", "language")):
            raise ValueError("the verified facts belong to different cases")
        if [fact["decision"] for fact in verified["facts"]] != [True, False]:
            raise ValueError("the verified pair no longer matches the existing answer order")
        requests = [request_set(prompt, item["language"], item["family"], fact)
                    for prompt, fact in zip(item["prompts"], verified["facts"], strict=True)]
        panel.append(dict(id=item["id"], family=item["family"], language=item["language"], requests=requests))
    if len(panel) != 48 or len({case["id"] for case in panel}) != 48:
        raise ValueError("the full frozen evaluation needs 48 distinct pairs")
    return panel


def load_body(name, expected, parent):
    path = reference.completed.regular_file(operator_trial.RECORD / f"{name}_body.pt")
    if reference.file_sha(path) != expected:
        raise ValueError("the trained body differs from its prior assessment")
    payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if (payload["schema"] != "P109C_CPU_RELATION_DIAGNOSTIC" or payload["arm"] != name
            or payload["post_updates"] != 64 or payload["parent_sha256"] != reference.CHECKPOINT_SHA256):
        raise ValueError("the trained body header differs")
    model = reference.completed.load_model(parent, 2942, "cpu")
    model.clear_quant()
    model.load_state_dict(payload["model"], strict=True)
    model.freeze_quant()
    return model, path


def summarize(rows):
    totals = Counter()
    for row in rows:
        for group in ("all", row["language"], row["family"]):
            totals[group, "pairs"] += 1
            for mode in ("original", "blank", "value"):
                totals[group, mode + "_pair_correct"] += row[mode + "_pair_correct"]
                totals[group, mode + "_pair_ended"] += row[mode + "_pair_ended"]
            for answer in row["facts"]:
                for key, value in answer["probe_score"].items():
                    if value is not None:
                        totals[group, key] += bool(value)
                        totals[group, key + "_denominator"] += 1
    return {group: {key: value for (name, key), value in totals.items() if name == group}
            for group in dict.fromkeys(name for name, _ in totals)}


def assess(case, original, model, tokenizer, check):
    facts = []
    expected_labels = ("yes", "no")
    for request, label in zip(case["requests"], expected_labels, strict=True):
        check()
        replies = {mode: prior.greedy(model, tokenizer, case["language"], request[mode])
                   for mode in ("probe", "blank", "value")}
        facts.append(dict(**replies, original=original[label], probe_score=score_probe(replies["probe"]["answer"], request)))
    row = {key: case[key] for key in ("id", "language", "family")}
    row["facts"] = facts
    for mode in ("original", "blank", "value"):
        row[mode + "_pair_correct"] = tuple(fact[mode]["label"] for fact in facts) == expected_labels
        row[mode + "_pair_ended"] = all(fact[mode]["stopped"] in ("EOS", "STOP_SEQUENCE") for fact in facts)
    return row


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or os.sched_getaffinity(0) != {14}
            or args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END):
        parser.error("use CPU 14, hide CUDA and provide a deadline inside the November 26 authorization")
    cutoff = args.stop_by.timestamp()

    def check():
        if time() >= cutoff:
            raise TimeoutError("the frozen numeric diagnostics reached the approved cutoff")

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    parent = reference.checkpoint()
    tokenizer = reference.completed.load_tokenizer()
    panel = sealed_panel()
    assessments = {name: pinned(operator_trial.RECORD / f"{name}_assessment.json", sha)
                   for name, sha in ASSESSMENT_SHA.items()}
    pins = {name: value["training"]["body_sha256"] for name, value in assessments.items()}
    for case in panel:
        if any(len(tokenizer.encode(prior.rule.chat(request[mode])).ids) + 32 > 1024
               for request in case["requests"] for mode in ("probe", "blank", "value")):
            raise ValueError("a diagnostic input would clip the frozen generation budget")
    check()
    OUT.mkdir(exist_ok=False)
    publish = reference.native.publish
    seal = OUT / "inputs.json"
    publish(seal, dict(cases=panel, source_sha256=reference.file_sha(Path(__file__)),
                       verified_values_sha256=VERIFIED_SHA, models=pins, assessment_sha256=ASSESSMENT_SHA,
                       stop_by=args.stop_by.isoformat(), context=1024, max_new=32, threads=1))
    summaries = {}
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for name, old in assessments.items():
            check()
            originals = {row["id"]: row for row in old["assessment"]["new_rules"]["rows"]}
            if originals.keys() != {row["id"] for row in panel}:
                raise ValueError("the archived free-answer panel does not match")
            model, path = load_body(name, pins[name], parent)
            with (OUT / f"{name}.jsonl").open("x", encoding="utf-8", buffering=1) as stream:
                rows = []
                for case in panel:
                    row = assess(case, originals[case["id"]], model, tokenizer, check)
                    print(json.dumps(row, ensure_ascii=False), file=stream)
                    rows.append(row)
            if reference.file_sha(path) != pins[name] or reference.file_sha(parent) != reference.CHECKPOINT_SHA256:
                raise ValueError("an assessed model changed")
            summaries[name] = summarize(rows)
            print(name, json.dumps(summaries[name]["all"]), flush=True)
            del model
    publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=reference.file_sha(seal), summary=summaries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
