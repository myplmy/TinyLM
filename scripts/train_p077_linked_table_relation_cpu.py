"""Add explicit first-table to second-table supervision and test on a fresh panel."""

import argparse
from dataclasses import replace
from datetime import datetime
import os
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import torch
from torch.nn import functional as F

from scripts import train_p077_linked_table_supervision_cpu as core


trial = core.trial
TAG = "p077_linked_table_relation_cpu_v1_20261124"
OUT = core.OUT.with_name(TAG)
TEST_SEED = 223714
LINK_WEIGHT = .5
TEST = {
    "ko": (("산호", "백일", "은하", "참새", "물결", "두레", "늘봄", "동백", "잔디", "먼들", "포도", "우물"),
           ("{name} 몫으로 배정된 업무의 번호를 두 기록에서 확인해 주세요.",
            "담당 항목을 먼저 찾고, {name} 쪽의 코드만 적어주세요.")),
    "en": (("Briar", "Wren", "Juniper", "Rowan", "Drift", "Harbor", "Vale", "Tern", "Saffron", "Vireo", "Dove", "Grove"),
           ("Give the number associated with the assignment recorded for {name}.",
            "Read the records and return the numeric code for what {name} has been assigned.")),
}


def observed_labels(tokenizer, row):
    title_a, title_b = core.SCHEMA[row["language"]][:2]
    text = tokenizer.decode(row["tokens"], skip_special_tokens=False)

    def table_data(title):
        marker = f"[table {title}]\n"
        if text.count(marker) != 1:
            raise ValueError("both original source spans must be present")
        section = text.split(marker, 1)[1].split("\n[/table]", 1)[0]
        return [line.split(": ", 1) for line in section.splitlines()]

    links = table_data(title_a)
    numbers = table_data(title_b)
    fields = {field: i for i, (field, _) in enumerate(numbers)}
    route = [fields[field] for _, field in links]
    if (sorted(route) != list(range(4)) or [text for _, text in numbers] != row["values"]
            or route[row["source"]] != row["value"]):
        raise ValueError("the left and right source labels must agree with the actual held-out task")
    return route


def prepare():
    previous, (tokenizer, symbols, training, old_test) = core.prepare()
    archive = core.OUT / "report.json"
    proof = trial.read_json(archive)
    if proof["profile"] != previous:
        raise ValueError("requires the completed matched CPU arms")
    schemas = {}
    for language, shape in core.SCHEMA.items():
        names, questions = TEST[language]
        if set(names) & set(shape[2] + shape[3]):
            raise ValueError("the prior training and first readback names must stay outside this test")
        schemas[language] = (*shape[:3], names, shape[4], questions)
    with patch.multiple(core, SCHEMA=schemas, SEED=TEST_SEED):
        test = core.panel(tokenizer, "test")
    old_prompts = {tuple(row["tokens"]) for row in training + old_test}
    if any(tuple(row["tokens"]) in old_prompts for row in test):
        raise ValueError("the adapted supervision requires new held-out prompts")
    relation = [observed_labels(tokenizer, row) for row in training]
    prior_weights = {name: proof["arms"][name]["weights_sha256"] for name in core.ARMS}
    if any(trial.file_sha(core.OUT / f"{name}.pt") != stamp for name, stamp in prior_weights.items()):
        raise ValueError("reuse exactly the two trained control heads")
    profile = dict(tag=TAG, previous=previous, previous_report=trial.file_sha(archive),
                   previous_weights=prior_weights, source=trial.file_sha(Path(__file__)),
                   relation_labels=core.authored.digest(relation), test=core.authored.digest(test),
                   fixture_seed=TEST_SEED, sizes=[len(training), len(test)], relation_weight=LINK_WEIGHT)
    return profile, (tokenizer, symbols, training, test, relation)


def second_hop(head, features):
    n, _, dim = features.shape
    first_fields = features[:, 1:5, None, :]
    value_cells = features[:, None, 5:, :].expand(-1, 4, -1, -1)
    every_row = torch.cat((first_fields, value_cells), dim=2).reshape(n * 4, 5, dim)
    return head.second(every_row, torch.arange(5).expand(n * 4, -1)).reshape(n, 4, 4)


@torch.no_grad()
def judge(head, hidden, rows, tok, end):
    result = core.judge(head, hidden, rows, tok, end)
    possible = second_hop(head, hidden).argmax(2)
    picked = possible[torch.arange(len(rows)), torch.tensor([r["source"] for r in rows])].tolist()
    for language in core.SCHEMA:
        result["summaries"][language]["value_with_true_first_row"] = sum(
            row["language"] == language and pos == row["value"] for row, pos in zip(rows, picked, strict=True))
    return result


def run(receipt, deadline):
    checked, (tokenizer, symbols, train, test, relation) = prepare()
    if (checked != receipt or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or deadline.tzinfo is None or deadline > core.linked.files.AUTHORIZATION_END
            or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 480):
        raise ValueError("the altered training requires the existing sealed CPU interval")
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    torch.manual_seed(core.SEED)
    asset = torch.load(core.BODY, map_location="cpu", weights_only=True)
    stored = asset["model"]
    frozen = checked["previous"]["state_sha256"]
    if trial.state_sha(stored) != frozen:
        raise ValueError("use the same immutable G4 body checkpoint")
    cfg = replace(core.TMTConfig(**asset["config"]), max_seq_len=1024)
    body = core.TiedMLPTransformer(cfg).eval().requires_grad_(False)
    body.load_state_dict(stored, strict=True)
    body.freeze_quant()
    OUT.mkdir()
    started = perf_counter()
    pad, end = symbols["<pad>"], symbols["<|im_end|>"]
    fit, valid = (core.features(body, rows, pad, deadline) for rows in (train, test))
    head = core.LinkedValueHeads(cfg.dim)
    phase = torch.Generator().manual_seed(core.SEED + 1)
    optimizer = torch.optim.AdamW(head.parameters(), lr=.004, weight_decay=.01)
    first, targets, links = (torch.tensor(data) for data in ([r["source"] for r in train],
                                [r["value"] for r in train], relation))
    steps, history = 0, []
    for epoch in range(core.EPOCHS):
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("the relation experiment reached its cutoff")
        total = 0.
        for batch in torch.randperm(len(train), generator=phase).split(core.BATCH):
            batch_features = fit[batch]
            a, b = head(batch_features)
            matches = second_hop(head, batch_features).reshape(-1, 4)
            loss = F.nll_loss(b, targets[batch]) + core.ARMS["final_and_assignment"] * F.cross_entropy(a, first[batch])
            loss += LINK_WEIGHT * F.cross_entropy(matches, links[batch].flatten())
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            steps += 1
            total += float(loss.detach())
        history.append(total / (len(train) // core.BATCH))
    results = {"final_assignment_and_relation": judge(head, valid, test, tokenizer, end)}
    candidate = OUT / "relational_head.pt"
    with candidate.open("xb") as stream:
        torch.save(dict(body_sha256=frozen, head=head.state_dict()), stream)
    for mode in core.ARMS:
        old = torch.load(core.OUT / f"{mode}.pt", map_location="cpu", weights_only=True)
        if old["body_sha256"] != frozen:
            raise ValueError("the existing heads must share this body")
        control = core.LinkedValueHeads(cfg.dim)
        control.load_state_dict(old["head"], strict=True)
        results[mode] = judge(control, valid, test, tokenizer, end)
    if trial.state_sha(body.state_dict()) != frozen:
        raise ValueError("body state must remain frozen for the entire comparison")
    trial.publish(OUT / "report.json", dict(profile=receipt, updates=steps, training_loss=history,
                  elapsed_seconds=perf_counter() - started, checkpoint_sha256=trial.file_sha(candidate), arms=results))
    for name, arm in results.items():
        print(name, arm["summaries"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        profile, _ = prepare()
        trial.publish(args.receipt, profile)
        print(trial.file_sha(args.receipt), profile["sizes"], flush=True)
        return 0
    if args.stop_by is None:
        parser.error("a user-authorized time cutoff is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
