"""Ask for one observed or computed integer without a multi-field response format."""

from argparse import ArgumentParser
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from time import time
from unicodedata import normalize

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_rule_intermediates_cpu as prior
from scripts import diag_p109c_rule_label_position_cpu as scoring


OUT = prior.OUT.with_name("p109c_single_numeric_cpu_20261126")
SOURCE_PROMPTS = {
    "dispatch": {"ko": ("따로 빼기 전 상자는 몇 개입니까?", "상자를 따로 빼고 나면 몇 개가 남습니까?"),
                 "en": ("How many crates are there before reserving any?", "How many crates remain after reserving the stated amount?")},
    "relay": {"ko": ("기록된 전류는 몇 단위입니까?", "기록된 전류의 두 배는 몇 단위입니까?"),
              "en": ("What is the recorded current in units?", "What is twice the recorded current in units?")},
    "orchard": {"ko": ("오늘 측정값은 얼마입니까?",), "en": ("What is today's reading?",)},
    "permit_desk": {"ko": ("신청자의 점수는 몇 점입니까?",), "en": ("What score did the applicant receive?",)},
}


def cases():
    verified = prior.pinned(prior.VERIFIED, prior.VERIFIED_SHA)
    source = prior.pinned(prior.reference.completed.ROOT / verified["source_path"], verified["source_sha256"])
    prepared = []
    for item, derivation in zip(source["evaluation"], verified["cases"], strict=True):
        if any(item[key] != derivation[key] for key in ("id", "language", "family")):
            raise ValueError("a verified fact does not match its question")
        family, lang = item["family"], item["language"]
        prompts = SOURCE_PROMPTS[family][lang]
        fields = ("observed", prior.FIELD_ORDER[family][-1]) if len(prompts) == 2 else ("observed",)
        instruction = "정수 하나만 쓰세요." if lang == "ko" else "Write just one integer."
        facts = []
        for side, text in enumerate(item["prompts"]):
            original = text.splitlines()[:-2]
            facts.append({field: dict(text="\n".join([*original, query, instruction]),
                                  right=derivation["facts"][side]["fields"][field],
                                  other=derivation["facts"][1-side]["fields"][field])
                          for field, query in zip(fields, prompts, strict=True)})
        prepared.append(dict(id=item["id"], family=family, language=lang, facts=facts))
    if len(prepared) != 48 or sum(len(fact) for row in prepared for fact in row["facts"]) != 144:
        raise ValueError("the single-number panel does not close at the frozen denominator")
    return prepared


def prepare_scores(panel, tokenizer):
    for row in panel:
        for fact in row["facts"]:
            for request in fact.values():
                prompt = scoring.chat(request["text"])
                prefix, candidates = scoring.continuations(tokenizer, prompt, [str(request["right"]), str(request["other"])])
                if len(prefix) + 32 > 1024:
                    raise ValueError("the integer request exceeds the generation budget")
                request.update(prefix=prefix, candidates=candidates)


def assess(model, tokenizer, language, request):
    response = prior.prior.greedy(model, tokenizer, language, request["text"])
    content = normalize("NFKC", response["answer"]).strip()
    match = re.fullmatch(r"[+-]?\d+", content)
    integer = int(match.group()) if match else None
    expected = request["right"]
    exact = integer == expected
    valid_ends = ("EOS", "STOP_SEQUENCE")
    equal_length = len({len(tokens) for tokens in request["candidates"]}) == 1
    scores = [scoring.scores(model, request["prefix"], tokens, 4) for tokens in request["candidates"]]
    margin = scores[0]["body"] - scores[1]["body"]
    eligible = equal_length and expected != request["other"]
    return dict(response=response, parsed=integer, correct=exact, correct_end=exact and response["stopped"] in valid_ends,
                matched_candidates=eligible, body_margin=margin, body_mean_margin=scores[0]["body_mean"]-scores[1]["body_mean"],
                scores=scores)


def summary(rows):
    groups = {}
    for row in rows:
        for language in ("all", row["language"]):
            left, right = row["facts"]
            for field in left:
                role = "observed" if field == "observed" else "computed"
                key = f"{language}_{role}"
                count = groups.setdefault(key, Counter())
                measurements = (left[field], right[field])
                count["pairs"] += 1
                count["exact_and_ended"] += sum(item["correct_end"] for item in measurements)
                count["integer_parsed"] += sum(item["parsed"] is not None for item in measurements)
                count["exact_pair"] += all(item["correct_end"] for item in measurements)
                matched = all(item["matched_candidates"] for item in measurements)
                count["matched_candidate_pairs"] += matched
                count["positive_margin_both"] += matched and all(item["body_margin"] > 0 for item in measurements)
    return groups


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or os.sched_getaffinity(0) != {14}
            or args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= prior.END):
        parser.error("use CPU 14 with CUDA hidden and a November 26 cutoff")

    def check():
        if time() >= args.stop_by.timestamp():
            raise TimeoutError("the single-number diagnostic reached its authorized cutoff")

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    tokenizer = prior.reference.completed.load_tokenizer()
    parent = prior.reference.checkpoint()
    panel = cases()
    prepare_scores(panel, tokenizer)
    digest = prior.reference.file_sha
    pins = {name: prior.pinned(prior.operator_trial.RECORD / f"{name}_assessment.json", checksum)["training"]["body_sha256"]
            for name, checksum in prior.ASSESSMENT_SHA.items()}
    OUT.mkdir(exist_ok=False)
    publish = prior.reference.native.publish
    seal = OUT / "inputs.json"
    source_sha = sha256(Path(__file__).read_bytes()).hexdigest().upper()
    publish(seal, dict(cases=panel, source_sha256=source_sha, body_sha256=pins,
                      verified_sha256=prior.VERIFIED_SHA, stop_by=args.stop_by.isoformat(), max_new=32))
    totals = {}
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for name, checksum in pins.items():
            check()
            model, path = prior.load_body(name, checksum, parent)
            rows = []
            with (OUT / f"{name}.jsonl").open("x", encoding="utf-8", buffering=1) as stream:
                for case in panel:
                    check()
                    row = {key: case[key] for key in ("id", "family", "language")}
                    row["facts"] = [{field: assess(model, tokenizer, case["language"], request)
                                     for field, request in fact.items()} for fact in case["facts"]]
                    rows.append(row)
                    print(json.dumps(row, ensure_ascii=False), file=stream)
            if digest(path) != checksum or digest(parent) != prior.reference.CHECKPOINT_SHA256:
                raise ValueError("the assessed model changed")
            totals[name] = summary(rows)
            print(name, json.dumps(totals[name]), flush=True)
            del model
    publish(OUT / "report.json", dict(status="COMPLETE", input_sha256=digest(seal), summary=totals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
