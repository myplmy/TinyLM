"""Expand only the development cohort for the protected periodic head edit."""

import argparse
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from random import Random
import sys

import torch

from scripts import run_p108_periodic_tied_head as prior


trial = prior.trial
data = prior.foundation.data
authored = data.authored
TAG = "p108_periodic_tied_head_gpu_v2_20261121"
OUT = trial.DATA.parent / TAG
SIZE = 64
SEED = 824753


def development_rows(tokenizer, special, cases):
    used = data.source_keys(tokenizer, cases)
    rng = Random(data.PROFILE_SEED)
    data.eval_pairs(tokenizer, rng, 11, 100, used)
    data.eval_pairs(tokenizer, rng, 11, 9980, used)
    digest = sha256()
    for _, low, high, count in data.STAGES:
        for index in range(count):
            values, *_ = data.draw(rng, index, low, high, used)
            key = authored.digest(["table_values", sorted(values)])
            digest.update(bytes.fromhex(key))
    if digest.hexdigest() != trial.read_json(data.DATA / "preflight.json")["train_values_sha256"]:
        raise ValueError("the foundation training source exclusion differs")

    rng = Random(SEED)
    rows = {}
    for index in range(SIZE):
        values, order, field, other, language = data.draw(rng, index, 11, 9980, used)
        root = authored.digest(["table", values])
        single, gold = data.form(values, order, field, language, 1)
        question = single["messages"][0]["content"][0]["text"]
        foil = str(values[other])
        reminder = "앞의 작업표에서 항목을 다시 확인해 주세요. " if language == "ko" else "Check the original work log again. "
        correction = authored.row(root, "correction", language, [
            ("user", question), ("assistant", foil),
            ("user", reminder + authored.field_question(language, field, 1)), ("assistant", gold),
        ], view="correction")["record"]
        texts = {"single": single, "correction": correction}
        records = {v: data.encode_record(row, tokenizer, context=trial.WIDTH) for v, row in texts.items()}
        prompts = {v: data.generation_prompt(tokenizer, row) for v, row in texts.items()}
        labels = {v: [token for token in row.y if token != data.IGNORE] for v, row in records.items()}
        if (labels["single"] != labels["correction"] or labels["single"][-1] != special["<|im_end|>"]
                or tokenizer.decode(labels["single"][:-1]) != gold
                or any(records[v].x[:len(p)] != p for v, p in prompts.items())):
            raise ValueError("a development record did not preserve the same scored answer")
        rows[root] = dict(records=records, prompts=prompts, gold=gold, foil=foil, language=language)
    if len(rows) != SIZE or any(rows.keys() & split.keys() for split in cases.values()):
        raise ValueError("the development cohort overlaps another split")
    return rows, digest.hexdigest()


def prepare():
    plan = prior.prepare()
    report_path = prior.OUT / "report.json"
    report = trial.read_json(report_path)
    terminal = trial.read_json(prior.OUT / "supervisor.json")
    if (report["preflight"] != plan or terminal["returncode"] or terminal["stop_reason"]
            or any(event["applied"] for event in report["events"])):
        raise ValueError("requires the completed first search with no changes")
    tokenizer, special, cases, orders, profiles = trial.load_cases()
    dev, excluded = development_rows(tokenizer, special, cases)
    for epoch in prior.SITES:
        event = trial.read_json(prior.OUT / f"edit_{epoch}.json")
        if event["attempts"] or any(not prior.correct(event["before"]["rows"][root], "correction") for root in plan["fit"]):
            raise ValueError("the first search did not exhaust its candidate coverage")
    path = Path(__file__)
    identity = {root: {k: row[k] for k in ("prompts", "gold", "foil", "language")} for root, row in dev.items()}
    plan.update(tag=TAG, fit=sorted(dev), seed=SEED, development_sha256=authored.digest(identity),
                exclusion_sha256=excluded, implementation_sha256=trial.file_sha(path),
                first_report_sha256=trial.file_sha(report_path))
    return plan, (tokenizer, special, cases, orders, profiles, dev)


def save_branch(name, model, tokenizer, special, cases, plan, dev, events):
    model.eval()
    model.clear_quant()
    digest = trial.state_sha(model.state_dict())
    control = trial.read_json(prior.CONTROL)
    identical = control["state_sha256"] == digest
    results = ({key: control[key] for key in ("validation", "test")} if identical else
               {key: trial.evaluate(model, tokenizer, special, cases[key]) for key in ("validation", "test")})
    targets = {event["target"]: dev[event["target"]] for event in events if event["applied"]}
    final_targets = trial.evaluate(model, tokenizer, special, targets) if targets else None
    audit = {root: results["validation"]["rows"][root] for root in plan["audit"]}
    trial.publish(OUT / f"{name}.json", dict(state_sha256=digest, reused_archived_responses=identical,
                  independent_audit_correct=len(prior.existing_answers(dict(rows=audit))), final_targets=final_targets, **results))
    return digest


def worker(plan, fraction):
    torch.set_num_threads(1)
    checked, (tokenizer, special, cases, orders, profiles, dev) = prepare()
    if checked != plan:
        raise ValueError("the frozen follow-up inputs changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(prior.foundation.OUT / "foundation.pt", weights_only=True, map_location="cpu")
    if trial.state_sha(state["model"]) != plan["base"]["state_sha256"]:
        raise ValueError("unexpected common initial weights")
    model = prior.TiedMLPTransformer(prior.TMTConfig(**state["config"])).to("cuda")
    model.load_state_dict(state["model"])
    torch.manual_seed(prior.reference.data.SEED)
    optimizer = torch.optim.AdamW(model.parameters(), lr=prior.reference.LR, weight_decay=.01, fused=True)
    steps = profiles["CORRECTION_ONLY"]["updates"]
    epochs = orders["CORRECTION_ONLY"] * trial.CYCLES
    schedule = [[cases["train"][entry["case_id"]]["records"][entry["view"]] for entry in epoch] for epoch in epochs]
    selection_and_guard = {**dev, **{root: cases["validation"][root] for root in plan["guard"]}}
    reference = trial.read_json(prior.CONTROL)["epochs"]
    step, events, history = 0, [], []
    print(f"START {TAG}", flush=True)
    for epoch, ordered in enumerate(schedule[:prior.SITES[-1]], 1):
        step, train = prior.train_epoch(model, optimizer, ordered, special, step, steps)
        history.append(dict(epoch=epoch, **train))
        if not any(event["applied"] for event in events) and train["ce"] != reference[epoch-1]["ce"]:
            raise RuntimeError("the common prefix drifted before any edit")
        if epoch not in prior.SITES:
            continue
        if epoch == prior.SITES[-1]:
            snapshot = {name: weight.detach().cpu().clone() for name, weight in model.state_dict().items()}
            moments = deepcopy(optimizer.state_dict())
            cpu_rng, cuda_rng = torch.get_rng_state(), torch.cuda.get_rng_state()
        edit = prior.attempt_edit(model, optimizer, tokenizer, special, selection_and_guard, plan)
        rejected = sum(not prior.correct(edit["before"]["rows"][root], "correction") for root in plan["fit"])
        target = edit["accepted"]["target"] if edit["applied"] else None
        observed = dict(epoch=epoch, step=step, wrong_candidates=rejected, attempts=len(edit.get("attempts", [])),
                        applied=edit["applied"], target=target)
        events.append(observed)
        trial.publish(OUT / f"edit_{epoch}.json", edit)
        print(observed, flush=True)
    boundary = step
    branches = {}
    for arm in (("periodic", "first_only") if events[-1]["applied"] else ("shared",)):
        if arm == "first_only":
            model.load_state_dict(snapshot)
            optimizer.load_state_dict(moments)
            torch.set_rng_state(cpu_rng)
            torch.cuda.set_rng_state(cuda_rng)
        step = boundary
        for epoch, ordered in enumerate(schedule[prior.SITES[-1]:], prior.SITES[-1]+1):
            step, train = prior.train_epoch(model, optimizer, ordered, special, step, steps)
            history.append(dict(arm=arm, epoch=epoch, **train))
        if step != steps:
            raise RuntimeError("an edit arm did not finish its planned updates")
        branches[arm] = save_branch(arm, model, tokenizer, special, cases, plan, dev, events)
    trial.publish(OUT / "report.json", dict(tag=TAG, preflight=plan, events=events, branches=branches, history=history,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan, _ = prepare()
    if args.mode == "check":
        print(trial.json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("run requires the matching receipt and stop time")
    return prior.owner.supervise(worker, (plan,), OUT, args.stop_by, authorization_end=trial.CUTOFF, min_seconds=300)


if __name__ == "__main__":
    sys.exit(main())
