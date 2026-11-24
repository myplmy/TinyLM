"""Measure the protected edit at the first actual greedy divergence."""

import argparse
from datetime import datetime
from itertools import zip_longest
import json
from pathlib import Path
import sys

import torch

from scripts import run_p108_periodic_tied_head_followup as followup


prior = followup.prior
trial = prior.trial
TAG = "p108_tied_head_first_margin_gpu_v1_20261121"
OUT = trial.DATA.parent / TAG
CHECKPOINT = prior.CONTROL.with_suffix(".pt")


def prepare():
    plan, data = followup.prepare()
    report = trial.read_json(followup.OUT / "report.json")
    terminal = trial.read_json(followup.OUT / "supervisor.json")
    control = trial.read_json(prior.CONTROL)
    if (report["preflight"] != plan or terminal["returncode"] or terminal["stop_reason"]
            or report["branches"] != {"shared": control["state_sha256"]}
            or trial.file_sha(CHECKPOINT) != control["checkpoint_sha256"]):
        raise ValueError("requires the verified unedited correction run")
    event_path = followup.OUT / "edit_12.json"
    last = trial.read_json(event_path)["before"]["rows"]
    selected = [root for root in plan["fit"] if not prior.correct(last[root], "correction")]
    if len(selected) != report["events"][-1]["wrong_candidates"]:
        raise ValueError("wrong first-divergence cohort")
    return dict(tag=TAG, setup=plan, targets=selected, edit_log_sha256=trial.file_sha(event_path),
                source_sha256=trial.file_sha(Path(__file__)), checkpoint_sha256=control["checkpoint_sha256"],
                state_sha256=control["state_sha256"]), data


def margin(scores, target):
    other = scores.clone()
    other[target] = -torch.inf
    return float(scores[target] - other.max())


def probe(model, tokenizer, special, cases, dev, plan):
    guard = {root: cases["validation"][root] for root in plan["setup"]["guard"]}
    panel = dict(dev, **guard)
    before = trial.evaluate(model, tokenizer, special, panel)
    correct = prior.existing_answers(before)
    anchors = [(root, view) for root in guard for view in prior.VIEWS if (root, view) in correct][:12]
    fixed = torch.cat([prior.projected(model, guard[root]["records"][view])[0] for root, view in anchors]).cpu()
    table = model.emb.weight
    end = special["<|im_end|>"]
    comparisons = []
    for root in plan["targets"]:
        example = dev[root]["records"]["correction"]
        keys, scores, labels = prior.projected(model, example)
        answer = before["rows"][root]["correction"]
        generated = answer["ids"] + ([end] if answer["eot"] else [])
        mismatch = next((i for i, (a, b) in enumerate(zip_longest(labels.tolist(), generated)) if a != b), None)
        if mismatch is None:
            comparisons.append(dict(root=root, before=answer, reason="already correct at completion"))
            continue
        if mismatch >= min(len(labels), len(generated)) or int(scores[mismatch].argmax()) != generated[mismatch]:
            comparisons.append(dict(root=root, before=answer, reason="generation and projected position are not aligned"))
            continue
        wanted, rival = int(labels[mismatch]), generated[mismatch]
        original_gap = margin(scores[mismatch], wanted)
        target_signal = -original_gap + .2
        reference = rival if wanted == end else wanted
        cap = .3 * float(table[reference].detach().double().norm())
        methods = []
        if wanted != end:
            methods.append(("raise_answer", [wanted], [target_signal]))
        if wanted == end:
            methods.append(("lower_extra_token", [rival], [-target_signal]))
        elif rival != end:
            methods.append(("raise_answer_and_lower_rival", [wanted, rival], [target_signal/2, -target_signal/2]))
        for method, ids, requested in methods:
            trial_info = dict(root=root, method=method, before=answer, gold=dev[root]["gold"], position=mismatch,
                              wanted=wanted, rival=rival, budget=cap, before_margin=original_gap)
            try:
                factors, stats = prior.protection.existing.constrained_factors(
                    keys[mismatch:mismatch+1].cpu(), torch.tensor([requested], dtype=torch.float64), fixed)
            except ValueError as error:
                comparisons.append(dict(trial_info, reason=str(error)))
                continue
            delta = prior.protection.existing.dense_delta(factors)
            required = float(delta.double().norm())
            pristine = table[ids].detach().clone()
            try:
                with torch.no_grad():
                    table[ids] = pristine + delta.to(pristine) * min(1., cap/required)
                model.clear_quant()
                _, new_scores, _ = prior.projected(model, example)
                actual = trial.evaluate(model, tokenizer, special, {root: dev[root]})["rows"][root]
                trial_info.update(required_norm=required, after_margin=margin(new_scores[mismatch], wanted),
                                  after=actual["correction"], target_correct=prior.correct(actual, "correction"), stats=stats)
                if trial_info["target_correct"]:
                    measured = trial.evaluate(model, tokenizer, special, panel)
                    trial_info["protected_lost"] = sorted(correct - prior.existing_answers(measured))
                    if not trial_info["protected_lost"]:
                        trial_info["independent_test"] = trial.evaluate(model, tokenizer, special, cases["test"])
                comparisons.append(trial_info)
            finally:
                with torch.no_grad():
                    table[ids] = pristine
                model.clear_quant()
    return comparisons


def worker(plan, memory_fraction):
    torch.set_num_threads(1)
    checked, (tokenizer, special, cases, _, _, dev) = prepare()
    if plan != checked:
        raise ValueError("first-margin evidence changed")
    torch.cuda.set_per_process_memory_fraction(memory_fraction)
    state = torch.load(CHECKPOINT, weights_only=True, map_location="cpu")
    model = prior.TiedMLPTransformer(prior.TMTConfig(**state["config"])).to("cuda")
    model.load_state_dict(state["model"])
    model.eval()
    if trial.state_sha(model.state_dict()) != plan["state_sha256"]:
        raise ValueError("wrong completed control state")
    rows = probe(model, tokenizer, special, cases, dev, plan)
    if trial.state_sha(model.state_dict()) != plan["state_sha256"]:
        raise RuntimeError("a temporary edit was not restored")
    trial.publish(OUT / "report.json", dict(plan=plan, comparisons=rows, weights_restored=True))
    print(json.dumps([dict(root=row["root"], method=row.get("method"), correct=row.get("target_correct"),
                           before=row.get("before_margin"), after=row.get("after_margin")) for row in rows]), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan, _ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("run requires the matching receipt and stop time")
    return prior.owner.supervise(worker, (plan,), OUT, args.stop_by, authorization_end=trial.CUTOFF, min_seconds=90)


if __name__ == "__main__":
    sys.exit(main())
