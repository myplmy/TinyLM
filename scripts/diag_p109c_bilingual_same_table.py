"""Isolate the question language on the same held-out tables and value swaps."""

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

import torch

from scripts import run_p109c_first_answer_value_bridge as bridge
from tinylm.config import TMTConfig


TAG = "p109c_bilingual_same_table_gpu_v1_20261121"
OUT = bridge.OUT.with_name(TAG)
trial, data, baseline = bridge.trial, bridge.data, bridge.baseline
MODELS = {"location":baseline.OUT, "first_value":bridge.OUT}


def prepare():
    tok, special, _, _, _ = trial.load_cases()
    bases = {}
    archived = {}
    for name, directory in MODELS.items():
        report, terminal = (trial.read_json(directory/f"{key}.json") for key in ("report", "supervisor"))
        model = directory/"foundation.pt"
        if terminal["returncode"] or terminal["stop_reason"] or trial.file_sha(model) != report["checkpoint_sha256"]:
            raise ValueError("requires the two verified completed unparented models")
        bases[name] = dict(checkpoint=report["checkpoint_sha256"], state=report["state_sha256"],
                           prior=trial.file_sha(directory/"wide_eval.json"))
        archived[name] = trial.read_json(directory/"wide_eval.json")["rows"]
    rows = archived["location"]
    if len(rows) != 64 or len(archived["first_value"]) != 64:
        raise ValueError("the archived mixed-language control must have 64 roots in each arm")
    requests = []
    for row, peer in zip(rows, archived["first_value"], strict=True):
        fields = ("root", "values", "order", "field", "other", "language", "prompts", "gold")
        if any(row[key] != peer[key] for key in fields):
            raise ValueError("the archived model comparisons used different prompts")
        language = {"ko":"en","en":"ko"}[row["language"]]
        swap = list(row["values"])
        swap[row["field"]], swap[row["other"]] = swap[row["other"]], swap[row["field"]]
        prompts, positions = [], []
        for values, gold in zip((row["values"],swap), row["gold"], strict=True):
            record, expected = data.form(values, row["order"], row["field"], language, 2)
            if expected != gold:
                raise ValueError("the translated question changed the target value")
            prompt = data.generation_prompt(tok, record)
            prompts.append(prompt)
            positions.append(baseline.sites_from_prompt(tok,prompt,gold))
        requests.append(dict(root=row["root"], language=language, gold=row["gold"], prompts=prompts, slots=positions))
    old = {tuple(p) for row in rows for p in row["prompts"]}
    new = {tuple(p) for row in requests for p in row["prompts"]}
    if new & old or len(new) != 128 or Counter(row["language"] for row in requests) != {"ko":32,"en":32}:
        raise ValueError("the translated panel must contain 128 new, balanced prompts")
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), bases=bases,
                requests=data.authored.digest(requests), new_prompts=len(new))
    return plan, (tok, special, archived, requests)


def compare(original, translated):
    languages = {language:dict(individual=0, joint=0, original=0, translated=0) for language in ("ko","en")}
    disagreements = dict(both=0, ko_only=0, en_only=0, neither=0)
    for before, after in zip(original, translated, strict=True):
        if before["root"] != after["root"] or before["gold"] != after["gold"]:
            raise ValueError("paired roots shifted")
        for origin, row in (("original",before),("translated",after)):
            item = languages[row["language"]]
            item["individual"] += sum(answer["answer"] == gold and answer["eot"]
                                      for answer, gold in zip(row["outputs"], row["gold"], strict=True))
            item["joint"] += row["both_correct"]
            item[origin] += row["both_correct"]
        success = {side["language"]:side["both_correct"] for side in (before,after)}
        if success["ko"] and success["en"]:
            disagreements["both"] += 1
        elif success["ko"]:
            disagreements["ko_only"] += 1
        elif success["en"]:
            disagreements["en_only"] += 1
        else:
            disagreements["neither"] += 1
    return dict(languages=languages, matched=disagreements)


def evaluate(plan, fraction):
    checked,(tok,special,archived,requests) = prepare()
    if checked != plan:
        raise ValueError("the sealed panel changed")
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    outputs, summaries = {}, {}
    for name, folder in MODELS.items():
        stored = torch.load(folder/"foundation.pt", weights_only=True, map_location="cpu")
        if trial.state_sha(stored["model"]) != plan["bases"][name]["state"]:
            raise ValueError("the model body does not match the earlier evaluation")
        model = baseline.TiedMLPTransformer(TMTConfig(**stored["config"])).to("cuda").eval()
        model.load_state_dict(stored["model"])
        selector = baseline.ValueLink(model.cfg.dim).to("cuda").eval()
        selector.load_state_dict(stored["train_head"])
        converted = data.evaluate(model, tok, special, requests, paired=True)
        slots = baseline.evaluate_slots(model, selector, requests, special["<pad>"])
        summaries[name] = dict(compare(archived[name],converted["rows"]), new_selection=slots["individual"])
        outputs[name] = dict(translated=converted, slots=slots)
        del model, selector
    trial.publish(OUT/"report.json",dict(plan=plan, result=summaries, outputs=outputs))
    print(json.dumps(summaries), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan,_ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires an exact sealed test and deadline")
    return baseline.owner.supervise(evaluate, (plan,), OUT, args.stop_by,
                                    authorization_end=bridge.AUTHORIZATION_END, min_seconds=180)


if __name__ == "__main__":
    raise SystemExit(main())
