"""Cross answer-token identity with display position on frozen v3 rule pairs."""

import argparse
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import resource
from statistics import median
import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_v3_rule_flip as previous


TAG = "p109c_rule_label_position_cpu_20261125"
PROFILE = previous.EVIDENCE / f"{TAG}_profile.json"
RECORD = previous.EVIDENCE / TAG
CPUS = set(range(14))
THREADS = 6
CELLS = ((True, True), (True, False), (False, True), (False, False))
AUTHORIZATION_END = datetime.fromisoformat("2026-11-25T13:00:00+09:00")


def instructions(language):
    if language == "en":
        return "Write only A or B.", "Answer only Yes or No."
    return "A 또는 B만 쓰세요.", "예 또는 아니요만 쓰세요."


def chat(text):
    return previous.serialize({"messages": [{"role": "user", "content": text}]}, "chatml",
                              add_generation_prompt=True)


def continuations(tokenizer, prompt, labels):
    prefix = tokenizer.encode(prompt).ids
    values = [tokenizer.encode(prompt + label).ids for label in labels]
    if any(tokens[:len(prefix)] != prefix or not len(prefix) < len(tokens) < 1024 for tokens in values):
        raise ValueError("a target continuation changed the prefix or exceeded the model context")
    return prefix, [tokens[len(prefix):] for tokens in values]


def prepare():
    tokenizer = previous.completed.load_tokenizer()
    old = previous.completed.read_json(previous.PROFILE)
    if previous.file_sha(previous.INPUT) != old["input_sha256"] or old["checkpoint_sha256"] != previous.CHECKPOINT_SHA256:
        raise ValueError("the previous frozen question panel or model identity changed")
    checkpoint = previous.checkpoint()
    cases = []
    for row in previous.panel():
        names = dict(zip(("yes", "no"), previous.LABELS[row["language"]], strict=True))
        choice_instruction, direct_instruction = instructions(row["language"])
        for gold in ("yes", "no"):
            evidence = row["evidence"].format(value=row[gold])
            text = evidence + "\n\n" + row["question"] + "\n"
            options = []
            for yes_first, yes_a in CELLS:
                yes_label, no_label = ("A", "B") if yes_a else ("B", "A")
                yes = f"{yes_label}. {names['yes']}"
                no = f"{no_label}. {names['no']}"
                first, second = (yes, no) if yes_first else (no, yes)
                prompt = chat(text + f"{first}\n{second}\n" + choice_instruction)
                prefix, tokens = continuations(tokenizer, prompt, (yes_label, no_label))
                if any(len(value) != 1 for value in tokens) or tokens[0] == tokens[1]:
                    raise ValueError("A and B must be distinct one-token continuations")
                options.append(dict(prompt=prompt, prefix=prefix, yes_first=yes_first, yes_a=yes_a,
                                    labels=[tokens[0][0], tokens[1][0]]))
            direct_prompt = chat(text + direct_instruction)
            prefix, tokens = continuations(tokenizer, direct_prompt, tuple(names.values()))
            cases.append(dict(id=row["id"], language=row["language"], gold=gold, options=options,
                              direct=dict(prompt=direct_prompt, prefix=prefix, continuations=tokens)))
    pins = previous.pins()
    for path in (Path(__file__).resolve(), previous.PROFILE):
        pins[path.relative_to(previous.completed.ROOT).as_posix()] = previous.file_sha(path)
    profile = dict(tag=TAG, checkpoint_sha256=old["checkpoint_sha256"], pinned_sources=pins,
                   cases_sha256=sha256(json.dumps(cases, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                   cases=len(cases), cpu_affinity=sorted(CPUS), threads=THREADS, precision="CPU_FP32_MATH",
                   eot_id=tokenizer.token_to_id("<|im_end|>"), factors=[list(cell) for cell in CELLS])
    if profile["eot_id"] != 4:
        raise ValueError("the original ChatML termination token changed")
    return profile, checkpoint, cases


def scores(model, prefix, tokens, eot):
    input_ids = torch.tensor([prefix + tokens], dtype=torch.long)
    hidden = model(input_ids, return_hidden=True)[0, len(prefix) - 1:]
    next_tokens = torch.tensor(tokens + [eot])
    values = model._head_logits(hidden).float().log_softmax(-1).gather(1, next_tokens[:, None]).flatten().tolist()
    if not all(math.isfinite(value) for value in values):
        raise ValueError("a direct answer score is nonfinite")
    return dict(body=sum(values[:-1]), body_mean=sum(values[:-1]) / len(tokens), eot=values[-1], tokens=tokens)


def measure(model, case, eot):
    cells = []
    for option in case["options"]:
        hidden = model(torch.tensor([option["prefix"]]), return_hidden=True)
        probabilities = model._head_logits(hidden[:, -1]).float()[0].log_softmax(-1)[option["labels"]].tolist()
        if not all(math.isfinite(value) for value in probabilities):
            raise ValueError("an option score is nonfinite")
        cells.append(dict(logp=probabilities, margin=probabilities[0] - probabilities[1],
                          yes_first=option["yes_first"], yes_a=option["yes_a"], prompt=option["prompt"],
                          token_ids=option["labels"]))
    first_a, first_b, second_a, second_b = (cell["margin"] for cell in cells)
    contrasts = dict(mean=sum(cell["margin"] for cell in cells) / 4,
                     position=(first_a + first_b - second_a - second_b) / 2,
                     label=(first_a + second_a - first_b - second_b) / 2,
                     position_label=first_a - first_b - second_a + second_b)
    direct = case["direct"]
    yes, no = [scores(model, direct["prefix"], tokens, eot) for tokens in direct["continuations"]]
    return dict(id=case["id"], language=case["language"], gold=case["gold"], cells=cells, effects=contrasts,
                direct=dict(prompt=direct["prompt"], yes=yes, no=no, body=yes["body"] - no["body"],
                            body_mean=yes["body_mean"] - no["body_mean"],
                            with_eot=yes["body"] + yes["eot"] - no["body"] - no["eot"]))


def summarize(rows):
    by_case = defaultdict(dict)
    for row in rows:
        by_case[row["id"]][row["gold"]] = row
    metrics = {"four_cell_mean": lambda row: row["effects"]["mean"],
               **{f"cell_{i}": lambda row, index=i: row["cells"][index]["margin"] for i in range(len(CELLS))},
               **{mode: lambda row, key=mode: row["direct"][key] for mode in ("body", "body_mean", "with_eot")}}
    result = {}
    for name, cases in (("all", by_case), ("excluding_ko04", {k: v for k, v in by_case.items() if k != "ko04"}),
                        *((lang, {k: v for k, v in by_case.items() if v["yes"]["language"] == lang})
                          for lang in ("en", "ko"))):
        flattened = [row for pair in cases.values() for row in pair.values()]
        scores_by_metric = {}
        for key, get in metrics.items():
            pairs = [(get(pair["yes"]), get(pair["no"])) for pair in cases.values()]
            scores_by_metric[key] = dict(both_correct=sum(a > 0 > b for a, b in pairs),
                                        direction=sum(a > b for a, b in pairs),
                                        median_fact_shift=median(a - b for a, b in pairs))
        effects = {effect: dict(signed_median=median(row["effects"][effect] for row in flattened),
                                absolute_median=median(abs(row["effects"][effect]) for row in flattened))
                   for effect in ("position", "label", "position_label")}
        result[name] = dict(pairs=len(cases), metrics=scores_by_metric, effects=effects)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--profile-sha256")
    args = parser.parse_args()
    if os.sched_getaffinity(0) != CPUS or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("buffer CPU 14 for independent work and run this diagnostic with CUDA hidden")
    current, checkpoint, cases = prepare()
    if args.action == "prepare":
        previous.native.publish(PROFILE, current)
        print(previous.file_sha(PROFILE), flush=True)
        return 0
    if (args.stop_by is None or args.stop_by.tzinfo is None or args.stop_by > AUTHORIZATION_END
            or time.time() >= args.stop_by.timestamp() or args.profile_sha256 != previous.file_sha(PROFILE)
            or current != previous.completed.read_json(PROFILE)):
        parser.error("run the frozen profile inside the allowed CPU interval")
    RECORD.mkdir(exist_ok=False)
    torch.set_num_threads(THREADS)
    torch.set_num_interop_threads(1)
    start = time.monotonic()
    model = previous.completed.load_model(checkpoint, 2942, "cpu")
    rows = []
    with (torch.inference_mode(), sdpa_kernel(SDPBackend.MATH),
          (RECORD / "rows.jsonl").open("x", encoding="utf-8", buffering=1) as output):
        for case in cases:
            if time.time() >= args.stop_by.timestamp():
                raise TimeoutError("the CPU diagnosis reached its stop time")
            outcome = measure(model, case, current["eot_id"])
            print(json.dumps(outcome, ensure_ascii=False), file=output)
            rows.append(outcome)
    if previous.file_sha(checkpoint) != current["checkpoint_sha256"]:
        raise ValueError("the original checkpoint changed")
    result = dict(tag=TAG, status="COMPLETE", profile_sha256=args.profile_sha256,
                  rows_sha256=previous.file_sha(RECORD / "rows.jsonl"), duration_s=time.monotonic()-start,
                  process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, summary=summarize(rows))
    previous.native.publish(RECORD / "report.json", result)
    print(json.dumps(result["summary"]["all"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
