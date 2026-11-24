"""Fit when to return a value chosen by the existing frozen value-link head."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from random import Random
import re

import torch
from torch import nn
from torch.nn import functional as F

from scripts import run_p109c_table_value_link as baseline
from tinylm.config import TMTConfig


TAG = "p109c_selected_value_readout_gpu_v1_20261121"
OUT = baseline.OUT.with_name(TAG)
trial, data = baseline.trial, baseline.data
CHECKPOINT = baseline.OUT / "foundation.pt"
AUTHORIZATION_END = datetime.fromisoformat("2026-11-21T17:00:00+09:00")
SEED, STEPS, BATCH = 202611213, 128, 32
VALUES = re.compile(r": ([0-9]+)")
QUESTIONS = {
    "ko": (
        (
            "이 표에서 {a}에 부여된 번호를 하나만 알려 주세요.",
            "{a}와 {b}의 번호를 순서대로 알려 주세요.",
            "{a} 번호가 7000 이상인가요? 예 또는 아니오로 답하세요.",
            "보증 항목의 번호는 무엇인가요?",
        ),
        (
            "{a} 항목 옆에 적힌 숫자만 그대로 옮겨 주세요.",
            "두 항목을 나란히 보여 주세요. {a}, {b} 순서입니다.",
            "{a} 값과 {b} 값 중 어느 쪽이 더 큰가요?",
            "승인 담당자에게 매긴 번호를 찾아 주세요.",
        ),
    ),
    "en": (
        (
            "Return the one number assigned to {a} in this log.",
            "Give the two numbers for {a} and {b}, in that order.",
            "Is the {a} number at least 7000? Answer yes or no.",
            "What is the number assigned to warranty?",
        ),
        (
            "Transcribe only the digits written by the {a} entry.",
            "Show both {a} and {b} as a numbered pair in that order.",
            "Which has the larger value, {a} or {b}?",
            "Find the number assigned to the approver.",
        ),
    ),
}


def extract_sites(tokenizer, ids):
    text = tokenizer.decode(ids, skip_special_tokens=False)
    encoded = tokenizer.encode(text)
    matches = list(VALUES.finditer(text))
    contents = [match[1] for match in matches]
    if encoded.ids != ids or len(contents) != 4 or len(set(contents)) != 4:
        raise ValueError("the exact input must contain four distinct numeric entries")
    positions = []
    for match in matches:
        last_digit = match.end(1) - 1
        hits = [i for i, (start, end) in enumerate(encoded.offsets) if start <= last_digit < end]
        if len(hits) != 1:
            raise ValueError("the final digit needs exactly one visible source position")
        positions.append(hits[0])
    if positions != sorted(set(positions)) or positions[-1] >= len(ids) - 1:
        raise ValueError("the complete table must precede the prediction site")
    return [len(ids) - 1, *positions], contents


def materialize(tokenizer, cases):
    used = data.source_keys(tokenizer, cases)
    foundation = Random(data.PROFILE_SEED)
    data.eval_pairs(tokenizer, foundation, 11, 100, used)
    data.eval_pairs(tokenizer, foundation, 11, 9980, used)
    digest = sha256()
    for _, low, high, count in data.STAGES:
        for index in range(count):
            values, *_ = data.draw(foundation, index, low, high, used)
            digest.update(bytes.fromhex(data.authored.digest(["table_values", sorted(values)])))
    if digest.hexdigest() != trial.read_json(data.DATA / "preflight.json")["train_values_sha256"]:
        raise ValueError("the foundation number groups could not be recovered")
    rng = Random(SEED)
    cohorts = {}
    splits = (("train", 48, 2000, 7000), ("calibration", 24, 7000, 9980),
              ("test_known_range", 32, 11, 2000), ("test_new_range", 32, 10000, 99999))
    for split, count, low, high in splits:
        rows = []
        new_templates = split.startswith("test")
        for index in range(count):
            values, order, field, other, language = data.draw(rng, index, low, high, used)
            root = data.authored.digest(["readout", values])
            head = "작업표에는 다음과 같이 적혀 있습니다. " if language == "ko" else "The work log has these entries. "
            names = data.authored.FIELDS[language]
            crossed = list(values)
            crossed[field], crossed[other] = crossed[other], crossed[field]
            variants = ((0, "single", values), (0, "swapped", crossed), (1, "two_values", values),
                        (2, "comparison", values), (3, "missing", values))
            for question, kind, numbers in variants:
                request = QUESTIONS[language][int(new_templates)][question].format(a=names[field], b=names[other])
                user = head + data.authored.values_text(language, numbers, order) + " " + request
                writable = question == 0
                target = str(numbers[field]) if writable else None
                record = data.authored.row(root, "table_lookup", language,
                                           [("user", user), ("assistant", target or "0")], view="single")["record"]
                ids = data.generation_prompt(tokenizer, record)
                sites, entries = extract_sites(tokenizer, ids)
                if entries != [str(numbers[i]) for i in order] or len(ids) + trial.GENERATION > trial.WIDTH:
                    raise ValueError("the authored entries or context differ from the encoded table")
                rows.append(dict(root=root, language=language, kind=kind, target=target,
                                 ids=ids, sites=sites, values=entries))
        cohorts[split] = rows
    prompts = [tuple(row["ids"]) for rows in cohorts.values() for row in rows]
    if len(set(prompts)) != len(prompts):
        raise ValueError("a generated request appears in more than one case")
    return cohorts


def prepare():
    reference = baseline.OUT / "report.json"
    terminal = baseline.OUT / "supervisor.json"
    report, end = trial.read_json(reference), trial.read_json(terminal)
    if (report["tag"] != baseline.TAG or report["parent"] is not None or end["returncode"] or end["stop_reason"]
            or trial.file_sha(CHECKPOINT) != report["checkpoint_sha256"]):
        raise ValueError("requires the verified first-token value-link canonical checkpoint")
    tok, special, cases, _, _ = trial.load_cases()
    cohorts = materialize(tok, cases)
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), checkpoint=report["checkpoint_sha256"],
                body=report["state_sha256"], baseline=trial.file_sha(reference), terminal=trial.file_sha(terminal),
                cohorts={key: dict(rows=len(rows), sha256=data.authored.digest(rows)) for key, rows in cohorts.items()},
                seed=SEED, updates=STEPS, batch=BATCH)
    return plan, (tok, special, cohorts)


@torch.inference_mode()
def project(model, selector, special, rows):
    features = []
    selected = []
    for start in range(0, len(rows), BATCH):
        batch = rows[start:start+BATCH]
        size = max(len(row["ids"]) for row in batch)
        tokens = torch.tensor([row["ids"] + [special["<pad>"]] * (size - len(row["ids"])) for row in batch],
                              device="cuda")
        tokens_at = torch.tensor([row["sites"] for row in batch], device="cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            hidden = model(tokens, return_hidden=True)
            options = selector(hidden, tokens_at)
        indices = torch.arange(len(batch), device="cuda")
        sorted_scores = options.float().topk(2, dim=-1).values
        margin = (sorted_scores[:, 0] - sorted_scores[:, 1]).unsqueeze(1)
        transformed = F.layer_norm(hidden[indices, tokens_at[:, 0]].float(), (model.cfg.dim,))
        features.append(torch.cat((transformed, torch.log1p(margin)), dim=1))
        selected.extend(options.argmax(dim=1).tolist())
    return torch.cat(features), selected


def fit_gate(projected, cohorts):
    torch.manual_seed(SEED)
    x, guesses = projected["train"]
    x = x.clone()
    train = cohorts["train"]
    labels = torch.tensor([row["target"] == row["values"][i] for row, i in zip(train, guesses, strict=True)],
                          dtype=torch.float32, device=x.device)
    if not 0 < labels.sum().item() < len(labels):
        raise ValueError("both runtime route cases must occur in the training fit")
    gate = nn.Linear(x.shape[1], 1).to(x.device)
    opt = torch.optim.AdamW(gate.parameters(), lr=.012, weight_decay=.01)
    for _ in range(STEPS):
        batch = torch.randperm(len(x), device=x.device)[:BATCH]
        opt.zero_grad(set_to_none=True)
        loss = F.binary_cross_entropy_with_logits(gate(x[batch]).flatten(), labels[batch])
        loss.backward()
        opt.step()
    gate.eval()
    with torch.no_grad():
        for param in gate.parameters():
            param.copy_(param.half())
        holdout, picks = projected["calibration"]
        calibration = cohorts["calibration"]
        bad = torch.tensor([row["target"] != row["values"][i] for row, i in zip(calibration, picks, strict=True)],
                           device=x.device)
        values = gate(holdout).flatten()
        threshold = max(0., values[bad].max().item())
        accepted = int((values > threshold).sum().item())
    return gate, threshold, dict(positive_labels=int(labels.sum().item()), accepted=accepted,
                                  calibration_negative=int(bad.sum().item()))


def evaluate(model, tokenizer, special, rows, projection, gate, cut):
    features, guesses = projection
    with torch.no_grad():
        scores = gate(features).flatten().tolist()
    before = []
    for index in range(0, len(rows), BATCH):
        before.extend(trial.generate(model, tokenizer, special, [r["ids"] for r in rows[index:index+BATCH]]))
    results = []
    for row, old, guess, score in zip(rows, before, guesses, scores, strict=True):
        value = row["values"][guess]
        copy = dict(answer=value, ids=tokenizer.encode(value, add_special_tokens=False).ids, eot=True)
        final = copy if score > cut else old
        results.append(dict(row, raw=old, copy=copy, selected=guess, score=score, routed=score > cut, final=final))
    positive = [row for row in results if row["target"] is not None]
    negative = [row for row in results if row["target"] is None]

    def exact(row, arm):
        return row[arm]["answer"] == row["target"] and row[arm]["eot"]

    summary = dict(positive=len(positive), negative=len(negative),
                   raw=sum(exact(r,"raw") for r in positive), copy=sum(exact(r,"copy") for r in positive),
                   gated=sum(exact(r,"final") for r in positive),
                   raw_lost=sum(exact(r,"raw") and not exact(r,"final") for r in positive),
                   positive_routed=sum(r["routed"] for r in positive),
                   negative_routed=sum(r["routed"] for r in negative))
    for arm in ("raw", "copy", "final"):
        views = {}
        for r in positive:
            views.setdefault(r["root"], []).append(exact(r, arm))
        summary[f"{arm}_pairs"] = sum(len(rs) == 2 and all(rs) for rs in views.values())
    return summary, results


def worker(plan, fraction):
    checked, (tok, special, cohorts) = prepare()
    if checked != plan:
        raise ValueError("the sealed input changed")
    torch.set_num_threads(1)
    torch.cuda.set_per_process_memory_fraction(fraction)
    state = torch.load(CHECKPOINT, weights_only=True, map_location="cpu")
    if trial.state_sha(state["model"]) != plan["body"]:
        raise ValueError("the selected body differs")
    model = baseline.TiedMLPTransformer(TMTConfig(**state["config"])).to("cuda").eval().requires_grad_(False)
    model.load_state_dict(state["model"])
    selector = baseline.ValueLink(model.cfg.dim).to("cuda").eval().requires_grad_(False)
    selector.load_state_dict(state["train_head"])
    projected = {key: project(model, selector, special, rows) for key, rows in cohorts.items()}
    gate, cut, diagnostics = fit_gate(projected, cohorts)
    reports, answers = {}, {}
    for key in ("test_known_range", "test_new_range"):
        reports[key], answers[key] = evaluate(model, tok, special, cohorts[key], projected[key], gate, cut)
    release = (all(not row["negative_routed"] and not row["raw_lost"] for row in reports.values())
               and sum(row["gated"] - row["raw"] for row in reports.values()) > 0)
    if release:
        with (OUT / "readout_gate.pt").open("xb") as out:
            torch.save(dict(state={k:v.half().cpu() for k,v in gate.state_dict().items()},
                            threshold=cut, body=plan["body"]), out)
    if trial.state_sha(model.state_dict()) != plan["body"]:
        raise ValueError("this experiment must keep the body fixed")
    trial.publish(OUT / "report.json", dict(plan=plan, threshold=cut, diagnostics=diagnostics,
                                          summary=reports, accepted_candidate=release,
                                          weights=sum(p.numel() for p in gate.parameters()), answers=answers))
    print(json.dumps(dict(calibration=diagnostics, gates=reports, accepted_candidate=release)), flush=True)


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
        parser.error("requires a sealed experiment and authorized cutoff")
    return baseline.owner.supervise(worker, (plan,), OUT, args.stop_by,
                                    authorization_end=AUTHORIZATION_END, min_seconds=180)


if __name__ == "__main__":
    raise SystemExit(main())
