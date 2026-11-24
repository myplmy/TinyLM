"""Check the three completed range-training policies on new source tables."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import re

import numpy as np
import torch

from scripts import run_p109c_bilingual_range_replay as replay
from tinylm.config import TMTConfig


paired, data, trial, baseline = replay.paired, replay.data, replay.trial, replay.baseline
readout = replay.widened.holdout.readout
TAG = "p109c_bilingual_range_confirmation_gpu_v1_20261121"
OUT = replay.OUT.with_name(TAG)
SEED = 2026112129
QUESTIONS = {
    "ko": "이 기록의 {field} 칸에 실제로 적힌 번호는 무엇입니까? 번호만 적으세요.",
    "en": "In this record, which digits are written in the {field} entry? Give only the number.",
}


def freeze_weights():
    models = {
        "original": (paired.OUT, paired.OUT / "transfer" / "foundation.pt"),
        "extended": (replay.widened.OUT, replay.widened.OUT / "foundation.pt"),
        "replay": (replay.OUT, replay.OUT / "foundation.pt"),
    }
    proofs = {}
    for name, (folder, checkpoint) in models.items():
        terminal = folder / "supervisor.json"
        end = trial.read_json(terminal)
        report_path = folder / "report.json"
        report = trial.read_json(report_path)
        arm = report["arms"]["transfer"] if name == "original" else report
        proof = trial.file_sha(checkpoint)
        if end["returncode"] or end["stop_reason"] or proof != arm["checkpoint"]:
            raise ValueError(f"requires a successfully completed frozen model for {name}")
        proofs[name] = dict(report=trial.file_sha(report_path), terminal=trial.file_sha(terminal),
                            weights=proof)
    return models, proofs


def build_cases():
    tok, special, original, _, _ = trial.load_cases()
    known = data.source_keys(tok, original)
    prior = Random(data.PROFILE_SEED)
    data.eval_pairs(tok, prior, 11, 100, known)
    data.eval_pairs(tok, prior, 11, 9980, known)
    training_digest = sha256()
    for _, lo, hi, count in data.STAGES:
        for i in range(count):
            values, *_ = data.draw(prior, i, lo, hi, known)
            fingerprint = data.authored.digest(["table_values", sorted(values)])
            training_digest.update(bytes.fromhex(fingerprint))
    if training_digest.hexdigest() != trial.read_json(data.DATA / "preflight.json")["train_values_sha256"]:
        raise ValueError("the original training group sequence changed")
    earlier = trial.read_json(readout.OUT / "report.json")["answers"]
    used_digits = set()
    for panel in earlier.values():
        for row in panel:
            values = tuple(sorted(map(int, row["values"])))
            known.add(values)
            used_digits.update(v for v in values if 10000 <= v < 99999)
    with np.load(replay.widened.PAYLOAD, allow_pickle=False) as training:
        used_digits.update(map(int, training["values"].flat))
    allowed = sorted(set(range(10000, 99999)) - used_digits)
    rng = Random(SEED)
    groups = {}
    for name, pool in (("known_range", range(11, 9980)), ("five_digit", allowed)):
        cases = []
        for i in range(64):
            while True:
                values = rng.sample(pool, 4)
                key = tuple(sorted(values))
                if key not in known:
                    known.add(key)
                    break
            lang = data.authored.LANGUAGES[i % 2]
            field = (i // 2) % 4
            other = (field + rng.randrange(1, 4)) % 4
            order = rng.sample(range(4), 4)
            swapped = values.copy()
            swapped[field], swapped[other] = swapped[other], swapped[field]
            prompts, gold, slots = [], [], []
            for entries in (values, swapped):
                question = QUESTIONS[lang].format(field=data.authored.FIELDS[lang][field])
                text = data.authored.values_text(lang, entries, order) + " " + question
                answer = str(entries[field])
                source_key = data.authored.digest([name, key])
                record = data.authored.row(source_key, "table_lookup", lang,
                                           [("user", text), ("assistant", answer)], view="single")["record"]
                prompt = data.generation_prompt(tok, record)
                positions, read = readout.extract_sites(tok, prompt)
                if read != [str(entries[j]) for j in order]:
                    raise ValueError("the exact input does not contain the authored values")
                prompts.append(prompt)
                gold.append(answer)
                slots.append([*positions, read.index(answer)])
            cases.append(dict(root=source_key, language=lang, prompts=prompts, gold=gold, slots=slots))
        groups[name] = cases
    return (tok, special, groups), len(used_digits)


def prepare():
    models, proofs = freeze_weights()
    cases, excluded = build_cases()
    digests = dict(tag=TAG, source=trial.file_sha(Path(__file__)), cases=data.authored.digest(cases[-1]),
                   seed=SEED, excluded_five_digit_values=excluded, models=proofs,
                   pairs_per_range=64, augmentation=trial.file_sha(replay.widened.PAYLOAD),
                   prior_requests=trial.file_sha(readout.OUT / "report.json"))
    return digests, models, cases


def worker(plan, fraction):
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    checked, models, (tok, special, cases) = prepare()
    if checked != plan:
        raise ValueError("a test panel or model changed after preflight")
    results = {}
    for name, (_, checkpoint) in models.items():
        weights = torch.load(checkpoint, weights_only=True, map_location="cpu")
        model = baseline.TiedMLPTransformer(TMTConfig(**weights["config"])).to("cuda").eval()
        model.load_state_dict(weights["model"])
        selector = baseline.ValueLink(model.cfg.dim).to("cuda").eval()
        selector.load_state_dict(weights["train_head"])
        arms = {}
        for panel, rows in cases.items():
            generated = data.evaluate(model, tok, special, rows, paired=True)
            selected = baseline.evaluate_slots(model, selector, rows, special["<pad>"])
            by_language = {}
            five_digit_counts = {}
            for language in data.authored.LANGUAGES:
                matches = [(item, target) for row in generated["rows"] if row["language"] == language
                           for item, target in zip(row["outputs"], row["gold"], strict=True)]
                by_language[language] = sum(item["answer"] == target and item["eot"] for item, target in matches)
                five_digit_counts[language] = sum(bool(re.fullmatch("[0-9]{5}", item["answer"])) and item["eot"]
                                                   for item, _ in matches)
            arms[panel] = dict(individual=sum(by_language.values()), individual_language=by_language,
                               pairs=generated["both_correct"], pair_language=generated["by_language"],
                               selected=selected["individual"], five_digit_counts=five_digit_counts)
            trial.publish(OUT / f"{name}-{panel}.json", dict(generated=generated, selected=selected))
        results[name] = arms
        del model, selector
    trial.publish(OUT / "report.json", dict(plan=plan, results=results))
    print(json.dumps(results, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "run"))
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    plan, _, _ = prepare()
    if args.mode == "check":
        print(json.dumps(plan, indent=2))
        return 0
    if args.receipt is None or args.stop_by is None or trial.read_json(args.receipt) != plan:
        parser.error("requires the sealed independent panels and cutoff")
    return baseline.owner.supervise(worker, (plan,), OUT, args.stop_by,
                                    authorization_end=paired.bridge.AUTHORIZATION_END, min_seconds=120)


if __name__ == "__main__":
    raise SystemExit(main())
