"""Test train-only numeric relation supervision with two matched CPU controls."""

from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
from random import Random
import re
from time import monotonic, time

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_rule_counterfactual_training_cpu as prior
from scripts.p109c_rule_counterfactual_cases import Family, make_cases


TAG = "p109c_rule_operator_20261125"
PROFILE = prior.reference.EVIDENCE / f"{TAG}_profile.json"
RECORD = prior.reference.EVIDENCE / TAG
END = datetime.fromisoformat("2026-11-25T12:00:00+09:00")
ARMS = ("ce", "shuffled_relation", "actual_relation")
MISSING = -100
SEED = 1337

INDEPENDENT = (
    Family("dispatch", ("Send the shipment if at least {limit} crates remain after reserving {extra} crates.",
                        "상자 {extra}개를 따로 빼고 {limit}개 이상이 남았을 때만 발송합니다."),
           ("There are {value} crates before reserving any.", "따로 빼기 전 상자가 {value}개 있습니다."),
           ("Should the shipment be sent?", "지금 화물을 발송해야 하나요?"),
           lambda value, limit, extra: value - extra >= limit),
    Family("orchard", ("Water outside the open interval from {limit} to {upper}, including both endpoints.",
                       "수치가 {limit}와 {upper} 사이의 열린 구간 밖일 때 물을 줍니다. 양 끝값도 포함합니다."),
           ("Today's reading is {value}.", "오늘 측정값은 {value}입니다."),
           ("Should the orchard be watered?", "과수원에 물을 줘야 하나요?"),
           lambda value, limit, extra: value <= limit or value >= limit + extra),
    Family("relay", ("Enable the relay only if doubling its recorded current gives more than {double} units.",
                     "기록 전류를 두 배로 한 값이 {double}단위를 초과할 때만 계전기를 켭니다."),
           ("The recorded current was {value} units.", "기록 전류는 {value}단위였습니다."),
           ("Should the relay be enabled?", "계전기를 켜야 하나요?"),
           lambda value, limit, extra: 2 * value > 2 * limit),
    Family("permit_desk", ("Issue a permit for scores of {limit} or higher. The score {upper} is disqualified.",
                           "점수가 {limit}점 이상이면 허가증을 발급합니다. 단, {upper}점은 제외합니다."),
           ("The applicant scored {value}.", "신청자의 점수는 {value}점입니다."),
           ("Should the desk issue a permit?", "허가증을 발급해야 하나요?"),
           lambda value, limit, extra: value >= limit and value != limit + extra),
)


def relation(left, right):
    return int(left >= right) + int(left > right)


def case_targets(case):
    family = case["family"]
    numbers = [int(value) for value in re.findall(r"[0-9]+", case["rule"])]
    targets = []
    for outcome, prompt in enumerate(case["prompts"]):
        values = re.findall(r"[0-9]+", prompt.splitlines()[2])
        if len(values) != 1:
            raise ValueError(f"{case['id']}: expected one observed number")
        value = int(values[0])
        if family in ("greenhouse", "tickets"):
            lower, upper = numbers
            label = (relation(value, lower), relation(value, upper))
            passes = label[0] >= 1 and label[1] <= 1 if family == "greenhouse" else 1 in label
        else:
            if family == "stock":
                extra, limit = numbers
                value += extra
            elif family == "calibration":
                limit, = numbers[-1:]
                if numbers[:-1] != ([2] if case["language"] == "ko" else []):
                    raise ValueError(f"{case['id']}: unexpected factor")
                value *= 2
            else:
                limit, = numbers
            comparison = relation(value, limit)
            label = (comparison, MISSING)
            decisive = {"museum": (1, 2), "shelf": (0, 1), "badge": (1,), "stock": (1, 2),
                        "calibration": (0,), "bridge": (0,)}
            passes = comparison in decisive[family]
        if passes != (outcome == 0):
            raise ValueError(f"{case['id']}: parsed relation disagrees with the sealed answer")
        targets.append(label)
    return targets


def shuffle_targets(cases, labels):
    bins = defaultdict(list)
    for case_i, (case, pair) in enumerate(zip(cases, labels, strict=True)):
        for fact_i, row in enumerate(pair):
            for slot, label in enumerate(row):
                if label != MISSING:
                    bins[case["family"], case["language"], slot].append((case_i, fact_i, slot))
    rng = Random(1762293)
    result = [[list(row) for row in pair] for pair in labels]
    for positions in bins.values():
        values = [labels[case_i][fact_i][slot] for case_i, fact_i, slot in positions]
        rng.shuffle(values)
        for (case_i, fact_i, slot), label in zip(positions, values, strict=True):
            result[case_i][fact_i][slot] = label
    return result


def check(cutoff):
    if time() >= cutoff or (RECORD / "STOP").exists():
        raise TimeoutError("numeric relation CPU diagnostic reached its authorized stop")


def prepare(cutoff):
    prior_profile, tokenizer, checkpoint, train, previous_holdout, _, replay, validation = prior.prepare()
    if prior_profile != prior.reference.completed.read_json(prior.PROFILE):
        raise ValueError("the previous training inputs no longer match")
    evaluation = make_cases(INDEPENDENT, 6, 1762291)
    seen = train + previous_holdout + prior.reference.panel()
    if (len(evaluation) != 48 or len({row["id"] for row in evaluation}) != 48
            or {row["question"] for row in evaluation} & {row["question"] for row in seen}):
        raise ValueError("independent questions overlap existing questions")
    actual = [case_targets(case) for case in train]
    shuffled = shuffle_targets(train, actual)
    real = torch.tensor(actual)
    control = torch.tensor(shuffled)
    changed = int(real.ne(control).sum())
    label_count = int(real.ne(MISSING).sum())
    if not torch.equal(real.eq(MISSING), control.eq(MISSING)) or changed < label_count / 4:
        raise ValueError("shuffled supervision is not adequately distinct")
    profile = dict(
        tag=TAG, source_sha256=prior.reference.file_sha(Path(__file__)),
        prior_profile_sha256=prior.reference.file_sha(prior.PROFILE), prior_train=prior_profile,
        torch_version=str(torch.__version__), cpu_affinity=[14], threads=1, stop_by=cutoff.isoformat(),
        arms=list(ARMS), seed=SEED, relation_weight=.15, head_lr=.0003, evaluation_pairs=len(evaluation),
        evaluation_sha256=prior.json_digest(evaluation), previous_holdout_sha256=prior.json_digest(previous_holdout),
        actual_labels_sha256=prior.json_digest(actual), shuffled_labels_sha256=prior.json_digest(shuffled),
        shuffled_labels_changed=changed, relation_targets=label_count,
        followup=dict(min_pair_delta=8, min_language_delta=3, max_previous_pair_loss=2, max_raw_nll_delta=.005),
    )
    return profile, tokenizer, checkpoint, train, previous_holdout, evaluation, replay, validation, real, control


def supervised_batch(model, paired_rows, replay_rows, head, labels, verify_prefix):
    even = torch.arange(0, 8, 2)
    positions = [row[1] for row in paired_rows[::2]]
    if positions != [row[1] for row in paired_rows[1::2]]:
        raise ValueError("the two answer rows have different prefix boundaries")
    features = []

    def capture(_, inputs, hidden):
        selected = hidden[even, positions]
        if verify_prefix and not torch.equal(selected, hidden[even + 1, positions]):
            raise ValueError("a supervised feature differs across the two answer continuations")
        features.append(selected)

    with model.register_forward_hook(capture):
        ce, raw, _, observed = prior.update_batch(model, paired_rows, replay_rows)
    features, = features
    targets = labels.flatten()
    scores = head(features.float()).view(-1, 3)
    relation_ce = F.cross_entropy(scores, targets, ignore_index=MISSING)
    observed["relation_targets"] = int(targets.ne(MISSING).sum())
    observed["relation_correct"] = int(scores.detach().argmax(dim=-1).eq(targets).sum())
    return ce, raw, relation_ce, observed


def train_arm(model, arm, profile, encoded, replay, labels, cutoff):
    model.clear_quant()
    model.cfg.infer_repeat = 1.
    model.train()
    if len(model.visit_schedule()) != 28:
        raise ValueError("the source R2 route differs")
    body = torch.optim.AdamW(model.parameters(), lr=profile["prior_train"]["lr"], weight_decay=0., foreach=False)
    head = head_optimizer = None
    if arm != "ce":
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(1762295)
            head = torch.nn.Linear(model.cfg.dim, 6)
        head_optimizer = torch.optim.AdamW(head.parameters(), lr=profile["head_lr"], weight_decay=0., foreach=False)
    counts = dict(inputs=0, answer_targets=0, replay_targets=0, relation_targets=0, relation_correct=0)
    started = monotonic()
    with (RECORD / f"{arm}_updates.jsonl").open("x", encoding="utf-8", buffering=1) as log:
        for step in range(prior.STEPS):
            check(cutoff)
            body.zero_grad(set_to_none=True)
            if head_optimizer is not None:
                head_optimizer.zero_grad(set_to_none=True)
            measurements = []
            for micro in range(prior.ACCUM):
                i = 2 * (step * prior.ACCUM + micro)
                pair = encoded[i] + encoded[i + 1]
                if head is None:
                    ce, raw, _, observed = prior.update_batch(model, pair, replay[i:i+2])
                    auxiliary_loss = ce.new_zeros(())
                else:
                    ce, raw, auxiliary_loss, observed = supervised_batch(
                        model, pair, replay[i:i+2], head, labels[i:i+2], step == micro == 0)
                loss = ce + profile["prior_train"]["replay_weight"] * raw
                ((loss + profile["relation_weight"] * auxiliary_loss) / prior.ACCUM).backward()
                for key in counts:
                    counts[key] += observed.get(key, 0)
                measurements.append([float(value.detach()) for value in (ce, raw, auxiliary_loss)])
            norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True))
            body.step()
            if head is not None:
                torch.nn.utils.clip_grad_norm_(head.parameters(), 1., error_if_nonfinite=True)
                head_optimizer.step()
            row = dict(arm=arm, step=step+1, elapsed_seconds=monotonic()-started, body_grad_norm=norm,
                       losses=measurements, cumulative=counts)
            print(json.dumps(row), file=log)
            if step == 0 or (step+1) % 8 == 0:
                print(json.dumps(row), flush=True)
    last = dict(counts=counts, elapsed_seconds=monotonic()-started)
    expected = (91320, 1280, 24576, profile["relation_targets"] if head is not None else 0)
    actual = tuple(counts[key] for key in ("inputs", "answer_targets", "replay_targets", "relation_targets"))
    if actual != expected:
        raise ValueError(f"training exposure {actual} differs from expected {expected}")
    model.eval()
    model.cfg.infer_repeat = 2.
    with torch.no_grad():
        model.freeze_quant()
    destination = RECORD / f"{arm}_body.pt"
    with destination.open("xb") as stream:
        torch.save(dict(schema="P109C_CPU_RELATION_DIAGNOSTIC", arm=arm,
                        parent_sha256=profile["prior_train"]["parent_sha256"], post_updates=prior.STEPS,
                        model=model.state_dict()), stream)
    return dict(**last, body_sha256=prior.reference.file_sha(destination))


def compare(arms, limits):
    candidate = arms["actual_relation"]
    comparisons = {}
    for name in ("ce", "shuffled_relation"):
        control = arms[name]
        new = candidate["new_rules"]["counts"]
        before = control["new_rules"]["counts"]
        differences = {lang: new[lang] - before[lang] for lang in ("all", "ko", "en")}
        previous = candidate["previous_dev"]["counts"]["all"] - control["previous_dev"]["counts"]["all"]
        raw_delta = candidate["raw_val_nll"] - control["raw_val_nll"]
        comparisons[name] = dict(new_pairs_delta=differences, prior_pairs_delta=previous, raw_val_nll_delta=raw_delta)
    qualifies = all(row["new_pairs_delta"]["all"] >= limits["min_pair_delta"]
                    and all(row["new_pairs_delta"][lang] >= limits["min_language_delta"] for lang in ("ko", "en"))
                    for row in comparisons.values())
    ce = comparisons["ce"]
    return dict(versus=comparisons, qualifies_for_common_evaluation=qualifies
                and ce["prior_pairs_delta"] >= -limits["max_previous_pair_loss"]
                and ce["raw_val_nll_delta"] <= limits["max_raw_nll_delta"])


def run(profile, tokenizer, checkpoint, train, prior_holdout, evaluation, replay, validation, real, control, stamp, cutoff):
    RECORD.mkdir(exist_ok=False)
    publish = prior.reference.native.publish
    publish(RECORD / "inputs.json", dict(evaluation=evaluation, previous_holdout=prior_holdout))
    encoded = [prior.encoded_pair(tokenizer, case) for case in train]
    results = {}
    with sdpa_kernel(SDPBackend.MATH):
        for arm in ("v3", *ARMS):
            check(cutoff)
            torch.manual_seed(SEED)
            model = prior.reference.completed.load_model(checkpoint, 2942, "cpu")
            training = None
            if arm != "v3":
                labels = real if arm == "actual_relation" else control
                training = train_arm(model, arm, profile, encoded, replay, labels, cutoff)
            check(cutoff)
            results[arm] = prior.assess(model, tokenizer, evaluation, prior_holdout, validation, cutoff)
            publish(RECORD / f"{arm}_assessment.json", dict(training=training, assessment=results[arm]))
            del model
    if prior.reference.file_sha(checkpoint) != profile["prior_train"]["parent_sha256"]:
        raise ValueError("the parent model changed during the run")
    decision = compare(results, profile["followup"])
    summary = {name: dict(new_rules=arm["new_rules"]["counts"], previous_rules=arm["previous_dev"]["counts"],
                          raw_val_nll=arm["raw_val_nll"]) for name, arm in results.items()}
    publish(RECORD / "report.json", dict(status="COMPLETE", profile_sha256=stamp, summary=summary, decision=decision))
    print(json.dumps(dict(summary=summary, decision=decision)), flush=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("use the single-core CPU-only path")
    if args.stop_by.tzinfo is None or not time() < args.stop_by.timestamp() <= END.timestamp():
        parser.error("the fixed cutoff must be within the authorized interval")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile, *assets = prepare(args.stop_by)
    if args.action == "seal":
        if PROFILE.exists() or RECORD.exists():
            parser.error("the evidence path must be new")
        prior.reference.native.publish(PROFILE, profile)
        print(prior.reference.file_sha(PROFILE), flush=True)
        return
    if (args.profile_sha256 != prior.reference.file_sha(PROFILE)
            or profile != prior.reference.completed.read_json(PROFILE) or RECORD.exists()):
        parser.error("run requires unchanged sealed inputs and a new result directory")
    run(profile, *assets, args.profile_sha256, args.stop_by.timestamp())


if __name__ == "__main__":
    main()
