"""Compare CE, paired movement and a separate decision margin for each rule fact."""

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
from time import monotonic, time

import torch
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_rule_counterfactual_training_cpu as prior
from scripts import diag_p109c_rule_margin_readback_cpu as margins


REF = prior.reference
TAG = "p109c_conditional_margin_cpu_20261126"
PROFILE = REF.EVIDENCE / f"{TAG}_profile_v2.json"
OUT = REF.EVIDENCE / TAG
END = datetime.fromisoformat("2026-11-26T06:45:00+09:00")
ARMS = ("ce", "paired", "per_fact")
NORMAL_STOP = ("STOP_SEQUENCE", "EOS")


def prepare():
    old, tokenizer, checkpoint, train, heldout, original, replay, val = prior.prepare()
    if old != REF.completed.read_json(prior.PROFILE):
        raise ValueError("the original exercise, replay or validation panel changed")
    baseline = REF.completed.read_json(prior.RECORD / "baseline.json")
    if len(baseline["raw_val_windows"]) * (len(val[0]) - 1) != old["val_tokens"]:
        raise ValueError("the parent raw validation denominator changed")
    encoded = [prior.encoded_pair(tokenizer, case) for case in train]
    pairs = [pair for pair in encoded if len(pair) == 4 and [row[3] for row in pair] == [True, False, False, True]]
    if len(pairs) != len(encoded) or len(encoded) != prior.STEPS * prior.ACCUM * 2:
        raise ValueError("each training rule needs the same four ordered candidates")
    expected = dict(inputs=sum(len(row[0]) - 1 for pair in encoded for row in pair) + len(replay) * prior.REPLAY_WIDTH,
                    answer_targets=sum(length + 1 for pair in encoded for _, _, length, gold in pair if gold),
                    replay_targets=len(replay) * prior.REPLAY_WIDTH)
    paths = [Path(__file__), Path(prior.__file__), Path(margins.__file__), Path(margins.scoring.__file__),
             prior.PROFILE, prior.RECORD / "baseline.json"]
    profile = dict(tag=TAG, parent_sha256=old["parent_sha256"], tokenizer_sha256=old["tokenizer_sha256"],
                   sources={path.name: REF.file_sha(path) for path in paths}, steps=prior.STEPS,
                   cpu_affinity=[14], threads=1, arms=list(ARMS), accum=prior.ACCUM, reserved=old["reserved"],
                   encoded_sha256=prior.json_digest(encoded), train_sha256=old["train_sha256"],
                   holdout_sha256=old["holdout_sha256"], original_sha256=old["original_sha256"],
                   replay_sha256=old["replay_sha256"], val_sha256=old["val_sha256"],
                   expected_exposure=expected, seed=1337, raw_val_tokens=old["val_tokens"],
                   lr=old["lr"], replay_weight=old["replay_weight"], rank_weight=old["arms"]["paired"],
                   paired_margin=1., per_fact_margin=.5, archived_parent_raw_nll=baseline["raw_val_nll"],
                   gates=dict(free_vs_ce=8, free_language_vs_ce=3, free_vs_paired=4,
                              scored_vs_paired=4, raw_nll_delta=.005))
    return profile, tokenizer, checkpoint, encoded, heldout, original, replay, val


def update_batch(model, candidate_rows, replay):
    rows = [*candidate_rows, *((row.tolist(), 0, 0, False) for row in replay)]
    width = max(len(tokens) - 1 for tokens, *_ in rows)
    if len(rows) != prior.ROWS or not 1 <= width <= prior.WIDTH:
        raise ValueError("the actual candidates and replay exceed the frozen batch")
    wire = torch.zeros((prior.ROWS, width), dtype=torch.long)
    indices, positions, targets, use_ce, in_answer = [], [], [], [], []
    for index, (tokens, start, length, gold) in enumerate(rows):
        wire[index, :len(tokens) - 1] = torch.tensor(tokens[:-1])
        for position in range(start, len(tokens) - 1):
            indices.append(index)
            positions.append(position)
            targets.append(tokens[position + 1])
            use_ce.append(gold)
            in_answer.append(position < start + length)
    hidden = model(wire, return_hidden=True)
    index = torch.tensor(indices)
    logits = model._head_logits(hidden[index, positions]).float()
    logp = logits.log_softmax(-1).gather(1, torch.tensor(targets)[:, None]).flatten()
    body = logp.new_zeros(prior.ROWS).index_add(0, index, logp * torch.tensor(in_answer))[:8].reshape(2, 4)
    yes = body[:, 0] - body[:, 1]
    no = body[:, 2] - body[:, 3]
    paired = body[:, 0] - body[:, 1] - body[:, 2] + body[:, 3]
    totals = dict(inputs=sum(len(tokens) - 1 for tokens, *_ in rows), answer_targets=sum(use_ce),
                  replay_targets=len(replay) * prior.REPLAY_WIDTH)
    return -logp[torch.tensor(use_ce)].mean(), -logp[index >= 8].mean(), yes, no, paired, totals


def check(deadline):
    if time() >= deadline or (OUT / "STOP").exists():
        raise TimeoutError("the conditional objective reached its approved end")


def train_arm(model, arm, profile, encoded, replay, deadline):
    model.clear_quant()
    model.cfg.infer_repeat = 1.
    model.train()
    if len(model.visit_schedule()) != 28:
        raise ValueError("the fixed training R2 visit count differs")
    optimizer = torch.optim.AdamW(model.parameters(), lr=profile["lr"], weight_decay=0., foreach=False)
    totals = dict.fromkeys(profile["expected_exposure"], 0)
    start = monotonic()
    with (OUT / f"{arm}_updates.jsonl").open("x", encoding="utf-8", buffering=1) as stream:
        for step in range(prior.STEPS):
            check(deadline)
            optimizer.zero_grad(set_to_none=True)
            losses = []
            for micro in range(prior.ACCUM):
                index = 2 * (step * prior.ACCUM + micro)
                rows = encoded[index] + encoded[index + 1]
                ce, raw, yes, no, paired, counts = update_batch(model, rows, replay[index:index + 2])
                pair_loss = F.softplus(profile["paired_margin"] - paired).mean()
                fact_margin = profile["per_fact_margin"]
                fact_loss = .5 * (F.softplus(fact_margin - yes) + F.softplus(fact_margin + no)).mean()
                rank = {"ce": 0. * pair_loss, "paired": pair_loss, "per_fact": fact_loss}[arm]
                ((ce + profile["replay_weight"] * raw + profile["rank_weight"] * rank) / prior.ACCUM).backward()
                for key, value in counts.items():
                    totals[key] += value
                losses.append([float(value.detach()) for value in (ce, raw, pair_loss, fact_loss, yes.mean(), no.mean())])
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            row = dict(arm=arm, step=step + 1, seconds=monotonic() - start, totals=totals, losses=losses,
                       grad_norm=float(norm))
            print(json.dumps(row), file=stream)
            if step == 0 or (step + 1) % 8 == 0:
                print(json.dumps(row), flush=True)
    if totals != profile["expected_exposure"]:
        raise ValueError("the actual update tokens differ from the sealed totals")
    model.eval()
    model.cfg.infer_repeat = 2.
    with torch.no_grad():
        model.freeze_quant()
    if len(model.visit_schedule()) != 28:
        raise ValueError("the fixed evaluation R2 visit count differs")
    return dict(totals=totals, seconds=monotonic() - start)


def generation_counts(rows):
    counts = {}
    for language in ("all", "ko", "en"):
        subset = [row for row in rows if language == "all" or row["language"] == language]
        answers = [(row["language"], row[key]) for row in subset for key in ("yes", "no")]
        counts[language] = dict(pairs=len(subset), both_correct=sum(row["correct"] and all(
            row[key]["stopped"] in NORMAL_STOP for key in ("yes", "no")) for row in subset),
            both_correct_eot=sum(row["correct"] and all(row[key]["stopped"] == "STOP_SEQUENCE"
                                 for key in ("yes", "no")) for row in subset),
            length_bound=sum(answer["stopped"] in ("MAX_NEW", "MAX_NEW_EOS_DISABLED") for _, answer in answers),
            eos=sum(answer["stopped"] == "EOS" for _, answer in answers),
            non_eot=sum(answer["stopped"] != "STOP_SEQUENCE" for _, answer in answers),
            empty=sum(not answer["answer"].strip() for _, answer in answers),
            repeat_tail=sum(prior.decode.repeat_tail(answer["ids"]) for _, answer in answers),
            accepted_alias=sum(answer["label"] is not None and answer["answer"].strip().casefold().strip(".!?。！？")
                               not in {label.casefold() for label in REF.LABELS[lang]} for lang, answer in answers),
            same_answer=sum(row["yes"]["label"] == row["no"]["label"] and row["yes"]["label"] in ("yes", "no")
                            for row in subset))
    return counts


def candidate_measurement(model, tokenizer, prompt, language):
    scoring = margins.scoring
    prefix, answer_tokens = scoring.continuations(tokenizer, scoring.chat(prompt), REF.LABELS[language])
    yes, no = [scoring.scores(model, prefix, tokens, prior.EOT) for tokens in answer_tokens]
    ended = [tokens + [prior.EOT] for tokens in answer_tokens]
    branch = next((index for index, (a, b) in enumerate(zip(*ended)) if a != b), None)
    if branch is None:
        raise ValueError("the two candidate token paths never separate")
    wire = torch.tensor([prefix + ended[0][:branch]], dtype=torch.long)
    hidden = model(wire, return_hidden=True)[0, -1:]
    logits = model._head_logits(hidden).float().flatten()
    a, b = (tokens[branch] for tokens in ended)
    body = yes["body"] - no["body"]
    return dict(body=body, body_mean=yes["body_mean"] - no["body_mean"], with_eot=body + yes["eot"] - no["eot"],
                candidates={"yes": yes, "no": no}, branch=dict(index=branch, token_ids=[a, b], margin=float(logits[a] - logits[b])))


@torch.inference_mode()
def read_margins(model, tokenizer, heldout, deadline):
    rows = []
    for case in heldout:
        check(deadline)
        yes, no = [candidate_measurement(model, tokenizer, prompt, case["language"]) for prompt in case["prompts"]]
        rows.append({key: case[key] for key in ("id", "family", "language")} | {"yes": yes, "no": no})
    return dict(rows=rows, summary=margins.summarize(rows))


def compare(profile, summaries, parent_nll):
    ce, pair, fact = (summaries[arm] for arm in ARMS)
    gates = profile["gates"]
    free_delta = {lang: fact["generated"][lang]["both_correct"] - ce["generated"][lang]["both_correct"]
                  for lang in ("all", "ko", "en")}
    relative_free = {lang: fact["generated"][lang]["both_correct"] - pair["generated"][lang]["both_correct"]
                     for lang in free_delta}
    relative_score = {lang: fact["scores"][lang]["body"]["both_correct"] - pair["scores"][lang]["body"]["both_correct"]
                      for lang in free_delta}
    raw_deltas = {"ce": fact["raw_nll"] - ce["raw_nll"], "parent": fact["raw_nll"] - parent_nll}
    return dict(free_vs_ce=free_delta, free_vs_paired=relative_free, scored_vs_paired=relative_score,
                raw_nll_delta=raw_deltas, gates_passed=dict(
                    scored=relative_score["all"] >= gates["scored_vs_paired"],
                    generated=(free_delta["all"] >= gates["free_vs_ce"] and relative_free["all"] >= gates["free_vs_paired"]
                               and all(free_delta[lang] >= gates["free_language_vs_ce"] and relative_free[lang] >= 0
                                       for lang in ("ko", "en"))),
                    raw_vs_ce=raw_deltas["ce"] <= gates["raw_nll_delta"],
                    raw_vs_parent=raw_deltas["parent"] <= gates["raw_nll_delta"]))


def run(profile, tokenizer, checkpoint, encoded, heldout, original, replay, val, deadline):
    OUT.mkdir(exist_ok=False)
    summaries = {}
    with sdpa_kernel(SDPBackend.MATH):
        parent = REF.completed.load_model(checkpoint, 2942, "cpu")
        parent_raw = prior.assess(parent, tokenizer, [], [], val, deadline)
        REF.native.publish(OUT / "parent_raw.json", {key: value for key, value in parent_raw.items() if key.startswith("raw_val")})
        del parent
        for arm in ARMS:
            check(deadline)
            torch.manual_seed(profile["seed"])
            model = REF.completed.load_model(checkpoint, 2942, "cpu")
            training = train_arm(model, arm, profile, encoded, replay, deadline)
            body = OUT / f"{arm}_body.pt"
            with body.open("xb") as stream:
                torch.save(dict(schema="P109C_CONDITIONAL_MARGIN_V1", model=model.state_dict(), arm=arm,
                                parent_sha256=profile["parent_sha256"], post_updates=prior.STEPS), stream)
            training["body_sha256"] = REF.file_sha(body)
            assessment = prior.assess(model, tokenizer, heldout, original, val, deadline)
            scored = read_margins(model, tokenizer, heldout, deadline)
            summary = dict(training=training, generated=generation_counts(assessment["new_rules"]["rows"]),
                           previous=generation_counts(assessment["previous_dev"]["rows"]), scores=scored["summary"],
                           raw_nll=assessment["raw_val_nll"])
            REF.native.publish(OUT / f"{arm}_assessment.json", dict(summary=summary, assessment=assessment,
                                                                     margins=scored["rows"]))
            summaries[arm] = summary
            print(arm, json.dumps(summary, ensure_ascii=False), flush=True)
            del model
    if REF.file_sha(checkpoint) != profile["parent_sha256"]:
        raise ValueError("the original v3 body changed")
    parent_nll = parent_raw["raw_val_nll"]
    decision = compare(profile, summaries, parent_nll)
    REF.native.publish(OUT / "report.json", dict(status="COMPLETE", profile_sha256=REF.file_sha(PROFILE),
                                                 arms=summaries, parent_raw_nll=parent_nll, comparison=decision))
    print(json.dumps(decision, ensure_ascii=False), flush=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seal", "run"))
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    parser.add_argument("--profile-sha256")
    args = parser.parse_args()
    if (args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= END
            or os.sched_getaffinity(0) != {14} or os.environ.get("CUDA_VISIBLE_DEVICES") != ""):
        parser.error("use CPU 14 with CUDA hidden before the reserved return time")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    profile, *assets = prepare()
    if args.action == "seal":
        REF.native.publish(PROFILE, profile)
        print(REF.file_sha(PROFILE), flush=True)
    elif profile != REF.completed.read_json(PROFILE) or args.profile_sha256 != REF.file_sha(PROFILE):
        parser.error("the frozen objective profile and exact input digest must match")
    else:
        run(profile, *assets, args.stop_by.timestamp())


if __name__ == "__main__":
    main()
