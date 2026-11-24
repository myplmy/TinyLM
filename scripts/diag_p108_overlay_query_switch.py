"""Test a frozen output correction when a follow-up asks about a different field."""

import argparse
from contextlib import nullcontext
from datetime import datetime
import json
from pathlib import Path
import re

import torch

from scripts import train_p108_guarded_output_sidecar as trained


TAG = "p108_overlay_query_switch_gpu_v1_20261121"
OUT = trained.OUT.with_name(TAG)
trial, prior, composition = trained.trial, trained.prior, trained.composition
TEMPLATES = {
    "en": (
        "Switch to the {field} entry. What number is on that line?",
        "That was about a different entry. Give the number for {field} now.",
        "Please report the value attached to {field} from the same log.",
    ),
    "ko": (
        "이번에는 {field} 항목으로 바꿉니다. 그 항목에는 무슨 번호가 있나요?",
        "그 답은 다른 항목에 관한 것이었습니다. 이제 {field} 번호를 적으세요.",
        "같은 작업표에서 {field}에 해당하는 번호를 알려 주세요.",
    ),
}


def prepare():
    recipe, (tok, special, _, dev, previous, _) = trained.prepare()
    stored = trained.OUT / "report.json"
    terminal = trained.OUT / "supervisor.json"
    learned = trained.OUT / "trained_overlay.pt"
    report = trial.read_json(stored)
    end = trial.read_json(terminal)
    checkpoint = trained.solver.first.CHECKPOINT
    if (recipe != report["plan"] or report["requests"] != previous or end["returncode"] or end["stop_reason"]
            or trial.file_sha(learned) != report["new_expressions"]["saved_sha256"]
            or trial.read_json(prior.CONTROL)["checkpoint_sha256"] != trial.file_sha(checkpoint)):
        raise ValueError("requires the unchanged completed sidecar and reference checkpoint")
    rows = []
    for root in recipe["targets"]:
        entry = dev[root]
        lang, gold, foil = entry["language"], entry["gold"], entry["foil"]
        raw = tok.decode(entry["prompts"]["correction"], skip_special_tokens=False)
        prefix, _ = raw.rsplit(composition.TURN, 1)
        values = {}
        for field in composition.AUTHOR.FIELDS[lang]:
            matches = re.findall(re.escape(field) + r": ([0-9]+)", prefix)
            if len(matches) != 1:
                raise ValueError("a table field did not have one explicit value")
            values[field] = matches[0]
        if len(set(values.values())) != 4 or gold not in values.values() or foil not in values.values():
            raise ValueError("the table and preceding foil are inconsistent")
        for field, value in values.items():
            if value in (gold, foil):
                continue

            def swap(match):
                old = match[1]
                replacement = {gold: value, value: gold}.get(old, old)
                return f": {replacement}"

            reordered = composition.VALUE.sub(swap, prefix)
            for style, template in enumerate(TEMPLATES[lang]):
                turn = composition.TURN + template.format(field=field) + composition.ENDING
                for family, table, wanted in (("different", prefix, value), ("swapped", reordered, gold)):
                    prompt = table + turn
                    ids = tok.encode(prompt, add_special_tokens=False).ids
                    if len(ids) + trial.GENERATION > trial.WIDTH:
                        raise ValueError("the follow-up exceeded the evaluation window")
                    rows.append(dict(root=root, language=lang, field=field, style=style, family=family,
                                     wanted=wanted, original_target=gold, foil=foil, prompt=prompt, ids=ids))
    inputs = {tuple(row["ids"]) for row in rows}
    old = {tuple(row["ids"]) for row in previous}
    if len(rows) != 24 or len(inputs) != 24 or inputs & old:
        raise ValueError("the question changes did not form a distinct paired panel")
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), prior_report=trial.file_sha(stored),
                prior_terminal=trial.file_sha(terminal), trained=trial.file_sha(learned),
                composed=recipe["start_overlay_sha256"], checkpoint=trial.file_sha(checkpoint),
                body=recipe["body_state_sha256"], requests=composition.AUTHOR.digest(rows), count=len(rows))
    return plan, (tok, special, rows, checkpoint, learned)


def evaluate(plan, fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    checked, (tok, special, rows, checkpoint, learned) = prepare()
    if checked != plan:
        raise ValueError("the sealed query-switch comparison changed")
    state = torch.load(checkpoint, weights_only=True, map_location="cpu")
    model = prior.TiedMLPTransformer(prior.TMTConfig(**state["config"])).to("cuda").eval().requires_grad_(False)
    model.load_state_dict(state["model"])
    if trial.state_sha(model.state_dict()) != plan["body"]:
        raise ValueError("the output corrections were attached to the wrong body")
    arms = {"clean": nullcontext()}
    for arm, path in (("composed", trained.INITIAL), ("trained", learned)):
        if trial.file_sha(path) != plan[arm]:
            raise ValueError("a sidecar does not match the sealed comparison")
        overlay = torch.load(path, weights_only=True, map_location="cpu")
        if overlay["body_sha256"] != plan["body"]:
            raise ValueError("a sidecar belongs to a different frozen body")
        arms[arm] = trained.solver.overlay(model, overlay["ids"], overlay["delta"].float())
    results = {}
    for arm, context in arms.items():
        with context:
            results[arm] = composition.run_wording(model, tok, special, rows)
    summaries = {}
    for arm, answers in results.items():
        different = [i for i, row in enumerate(rows) if row["family"] == "different"]
        summaries[arm] = dict(
            exact=sum(row["exact"] for row in answers),
            paired_both=sum(answers[i]["exact"] and answers[i + 1]["exact"] for i in different),
            different_exact=sum(answers[i]["exact"] for i in different),
            original_target_intrusion=sum(answers[i]["answer"] == rows[i]["original_target"] for i in different),
            prior_foil_copy=sum(answer["answer"] == row["foil"] for row, answer in zip(rows, answers, strict=True)),
            lost_clean_exact=sum(a["exact"] and not b["exact"] for a, b in zip(results["clean"], answers, strict=True)),
        )
    if trial.state_sha(model.state_dict()) != plan["body"]:
        raise ValueError("the query-switch comparison mutated the frozen model")
    trial.publish(OUT / "report.json", dict(plan=plan, requests=rows, outputs=results, summary=summaries))
    print(json.dumps(summaries), flush=True)


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
        parser.error("requires a sealed evaluation panel and authorized cutoff")
    return prior.owner.supervise(evaluate, (plan,), OUT, args.stop_by,
                                 authorization_end=trained.solver.AUTHORIZATION_END, min_seconds=120)


if __name__ == "__main__":
    raise SystemExit(main())
