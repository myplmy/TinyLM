"""Test first-row selection while holding the trained second hop fixed."""

import argparse
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
import os
from pathlib import Path
import re
from time import perf_counter
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel
from torch.nn import functional as F

from scripts import train_p077_linked_table_relation_cpu as relation


core, trial = relation.core, relation.trial
TAG = "p077_linked_first_row_span_cpu_v1_20261124"
OUT = core.OUT.with_name(TAG)
TEST_SEED = 229134
TEST = {
    "ko": (("샘", "샘물", "매화", "해뜰", "포구", "함박", "자갈", "반딧불", "낙엽", "초롱", "이슬", "꽃길"),
           ("두 기록에서 {name}의 업무 번호만 확인해 주세요.",
            "배정받은 일의 번호를 두 표에서 찾아 {name}에게 알려주세요."),
           ("{other} 대신 {name}에게 배정된 업무의 번호를 적어주세요.",
            "{name}의 업무 번호를 알려주세요. {other}의 번호는 빼주세요.")),
    "en": (("Ash", "Ashby", "Reef", "Linden", "Bramble", "Coast", "Fennel", "Elm", "Piper", "Osprey", "Alder", "Crane"),
           ("Consult both tables and identify the assigned work number for {name}.",
            "Write the single code from the two records that belongs to {name}."),
           ("Instead of {other}, give the assigned work number for {name}.",
            "Give the code for {name}. Omit the number assigned to {other}.")),
}


def source_text(tokenizer, row):
    text = tokenizer.decode(row["tokens"], skip_special_tokens=False)
    sections = []
    for title in core.SCHEMA[row["language"]][:2]:
        marker = f"[table {title}]\n"
        if text.count(marker) != 1:
            raise ValueError("both source tables must appear once")
        start = text.index(marker) + len(marker)
        end = text.index("\n[/table]", start)
        sections.append((start, text[start:end].splitlines()))
    start = text.rindex("[/table]\n\n") + len("[/table]\n\n")
    if not text.endswith(core.linked.TAIL):
        raise ValueError("the query must end at the original turn boundary")
    return text, sections, start, len(text) - len(core.linked.TAIL)


def matched_queries(tokenizer, rows):
    modified = []
    for row in rows:
        _, sections, _, _ = source_text(tokenizer, row)
        names = [line.split(": ", 1)[0] for line in sections[0][1]]
        root = int(row["root"].split("-")[1])
        target = row["source"]
        other = (target + 1 + root % 3) % 4
        templates = TEST[row["language"]][2]
        question = templates[(root // 8) % len(templates)].format(name=names[target], other=names[other])
        titles = core.SCHEMA[row["language"]][:2]
        left, right = [core.table(title, section[1]) for title, section in zip(titles, sections, strict=True)]
        tokens, sites = core.request(tokenizer, left, right, question, row["order"])
        modified.append(dict(row, tokens=tokens, sites=sites))
    return modified


def prepare():
    previous, (tokenizer, symbols, train, prior_test, _) = relation.prepare()
    report = relation.OUT / "report.json"
    checkpoint = relation.OUT / "relational_head.pt"
    proof = trial.read_json(report)
    if (proof["profile"] != previous or proof["updates"] != core.EPOCHS * len(train) // core.BATCH
            or trial.file_sha(checkpoint) != proof["checkpoint_sha256"]):
        raise ValueError("a completed matching second-hop checkpoint is required")
    initial_test = core.panel(tokenizer, "test")
    schemas = {}
    for language, schema in core.SCHEMA.items():
        names, questions, _ = TEST[language]
        if set(names) & set((*schema[2], *schema[3], *relation.TEST[language][0])):
            raise ValueError("held-out names must differ from both earlier panels")
        schemas[language] = (*schema[:3], names, schema[4], questions)
    with patch.multiple(core, SCHEMA=schemas, SEED=TEST_SEED):
        single = core.panel(tokenizer, "test")
    competing = matched_queries(tokenizer, single)
    old = {tuple(row["tokens"]) for row in train + initial_test + prior_test}
    new = {tuple(row["tokens"]) for row in single + competing}
    if len(new) != len(single) + len(competing) or old & new:
        raise ValueError("all new queries must be distinct from the earlier inputs")
    data = dict(train=train, single_mention=single, competing_mention=competing)
    profile = dict(tag=TAG, frozen_body=previous["previous"]["state_sha256"],
                   second_checkpoint=proof["checkpoint_sha256"], second_report=trial.file_sha(report),
                   training=previous, source=trial.file_sha(Path(__file__)), seed=TEST_SEED,
                   sizes={name: len(rows) for name, rows in data.items()},
                   inputs={name: core.authored.digest(rows) for name, rows in data.items()},
                   learning_rate=.004, weight_decay=.01)
    return profile, tokenizer, symbols, data


def spans(tokenizer, row):
    text, sections, ask_start, ask_stop = source_text(tokenizer, row)
    encoding = tokenizer.encode(text, add_special_tokens=False)
    if encoding.ids != row["tokens"]:
        raise ValueError("input and observed spans must use identical tokenization")

    def tokens_at(start, stop):
        selected = [index for index, (a, b) in enumerate(encoding.offsets) if a < stop and start < b]
        if not selected:
            raise ValueError("each name or question must contain visible input tokens")
        return selected

    names, name_spans = [], []
    cursor, lines = sections[0]
    for line in lines:
        name = line.split(": ", 1)[0]
        names.append(name)
        name_spans.append(tokens_at(cursor, cursor + len(name)))
        cursor += len(line) + 1
    question = text[ask_start:ask_stop].casefold()
    candidates = []
    for index, name in enumerate(names):
        literal = re.escape(name.casefold())
        if row["language"] == "en":
            literal = rf"(?<!\w){literal}(?!\w)"
        if re.search(literal, question):
            candidates.append(index)
    unique = candidates[0] if len(candidates) == 1 else -1
    return name_spans, tokens_at(ask_start, ask_stop), unique


@dataclass
class Features:
    joint: torch.Tensor
    names: torch.Tensor
    questions: torch.Tensor
    question_mask: torch.Tensor
    literal: torch.Tensor


@torch.no_grad()
def extract(body, tokenizer, rows, pad, deadline):
    locations = [spans(tokenizer, row) for row in rows]
    question_width = max(len(points) for _, points, _ in locations)
    name_width = max(len(points) for names, _, _ in locations for points in names)
    joint, names, questions, mask = [], [], [], []
    for offset in range(0, len(rows), 16):
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("CPU feature extraction reached its authorization cutoff")
        items = rows[offset:offset + 16]
        batch = locations[offset:offset + 16]
        width = max(len(row["tokens"]) for row in items)
        x = torch.tensor([row["tokens"] + [pad] * (width - len(row["tokens"])) for row in items])
        with sdpa_kernel(SDPBackend.MATH):
            hidden = body(x, return_hidden=True)
        row_id = torch.arange(len(items))
        joint.append(hidden[row_id[:, None], torch.tensor([row["sites"] for row in items])])
        names_at = torch.tensor([[points + [-1] * (name_width - len(points)) for points in four]
                                 for four, _, _ in batch])
        valid = names_at >= 0
        name_hidden = hidden[row_id[:, None, None], names_at.clamp_min(0)]
        names.append((name_hidden * valid[..., None]).sum(2) / valid.sum(2)[..., None])
        questions_at = torch.tensor([points + [-1] * (question_width - len(points)) for _, points, _ in batch])
        questions.append(hidden[row_id[:, None], questions_at.clamp_min(0)])
        mask.append(questions_at >= 0)
    return Features(*(torch.cat(blocks) for blocks in (joint, names, questions, mask)),
                    torch.tensor([picked for _, _, picked in locations]))


def scores(head, inputs, rows, mode):
    if mode == "last":
        return head(inputs.joint[rows, :5], torch.arange(5).expand(len(rows), -1))
    keys = head.key(inputs.names[rows])
    query = head.query(inputs.questions[rows])
    raw = keys @ query.transpose(1, 2) / keys.shape[-1] ** .5
    return raw.masked_fill(~inputs.question_mask[rows, None, :], -torch.inf).amax(2)


def fit(head, features, targets, mode, profile, deadline):
    optimizer = torch.optim.AdamW(head.parameters(), lr=profile["learning_rate"], weight_decay=profile["weight_decay"])
    shuffle = torch.Generator().manual_seed(core.SEED + 1)
    losses, updates = [], 0
    for _ in range(core.EPOCHS):
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("first-row learning reached its authorization cutoff")
        epoch_loss = 0.
        for index in torch.randperm(len(targets), generator=shuffle).split(core.BATCH):
            loss = F.cross_entropy(scores(head, features, index, mode), targets[index])
            if not loss.isfinite():
                raise ValueError("nonfinite first-row training loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.detach())
            updates += 1
        losses.append(epoch_loss / (len(targets) // core.BATCH))
    return dict(updates=updates, loss_by_epoch=losses)


def judge(selected, possible, rows):
    picks, stats = [], {}
    for first, options, row in zip(selected.tolist(), possible.tolist(), rows, strict=True):
        value = options[first] if first >= 0 else -1
        picks.append(dict(root=row["root"], language=row["language"], order=row["order"],
                          assignment=row["assignment"], inventory=row["inventory"],
                          first=first, gold_first=row["source"], value=value, gold_value=row["value"],
                          true_row_value=options[row["source"]]))
    for language in ("ko", "en", "all"):
        subset = [result for result in picks if language in ("all", result["language"])]
        by_root = {}
        for result in subset:
            by_root.setdefault(result["root"], []).append(result["value"] == result["gold_value"])
        if any(len(group) != 8 for group in by_root.values()):
            raise ValueError("each root needs both table orders and four states")
        stats[language] = dict(rows=len(subset), first_correct=sum(r["first"] == r["gold_first"] for r in subset),
                               number_correct=sum(r["value"] == r["gold_value"] for r in subset),
                               abstained=sum(r["first"] < 0 for r in subset), groups=len(by_root),
                               groups_all_correct=sum(all(group) for group in by_root.values()),
                               number_if_true_row=sum(r["true_row_value"] == r["gold_value"] for r in subset))
    return dict(summaries=stats, decisions=picks)


def run(profile, deadline):
    checked, tokenizer, symbols, data = prepare()
    if (checked != profile or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or deadline.tzinfo is None or deadline > core.linked.files.AUTHORIZATION_END
            or datetime.now(deadline.tzinfo) >= deadline):
        raise ValueError("the run requires the matching receipt and a valid CPU authorization cutoff")
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    torch.manual_seed(core.SEED)
    asset = torch.load(core.BODY, map_location="cpu", weights_only=True)
    frozen = profile["frozen_body"]
    cfg = replace(core.TMTConfig(**asset["config"]), max_seq_len=1024)
    body = core.TiedMLPTransformer(cfg).eval().requires_grad_(False)
    body.load_state_dict(asset["model"], strict=True)
    body.freeze_quant()
    previous = torch.load(relation.OUT / "relational_head.pt", map_location="cpu", weights_only=True)
    if trial.state_sha(body.state_dict()) != frozen or previous["body_sha256"] != frozen:
        raise ValueError("first- and second-stage features must share the frozen G4 body")
    linked = core.LinkedValueHeads(cfg.dim).eval().requires_grad_(False)
    linked.load_state_dict(previous["head"], strict=True)
    original = trial.state_sha(linked.state_dict())
    trainable = {mode: deepcopy(linked.first).train().requires_grad_(True) for mode in ("last", "span")}
    OUT.mkdir()
    started = perf_counter()
    features = {name: extract(body, tokenizer, rows, symbols["<pad>"], deadline) for name, rows in data.items()}
    targets = torch.tensor([row["source"] for row in data["train"]])
    history = {mode: fit(head, features["train"], targets, mode, profile, deadline) for mode, head in trainable.items()}
    results = {}
    with torch.no_grad():
        for name in ("single_mention", "competing_mention"):
            inputs, rows = features[name], data[name]
            index = torch.arange(len(rows))
            possible = relation.second_hop(linked, inputs.joint).argmax(2)
            first = dict(frozen_last=scores(linked.first, inputs, index, "last").argmax(1), literal=inputs.literal)
            first.update({mode: scores(head, inputs, index, mode).argmax(1) for mode, head in trainable.items()})
            results[name] = {mode: judge(selected, possible, rows) for mode, selected in first.items()}
    if trial.state_sha(body.state_dict()) != frozen or trial.state_sha(linked.state_dict()) != original:
        raise ValueError("neither the body nor the archived second hop may change")
    output = OUT / "first_row_heads.pt"
    with output.open("xb") as stream:
        torch.save({mode: head.state_dict() for mode, head in trainable.items()}, stream)
    trial.publish(OUT / "report.json", dict(profile=profile, history=history, frozen_link_state_sha256=original,
                  elapsed_seconds=perf_counter() - started, checkpoint_sha256=trial.file_sha(output), panels=results))
    for name, panel in results.items():
        print(name, {mode: arm["summaries"]["all"] for mode, arm in panel.items()}, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        profile, *_ = prepare()
        trial.publish(args.receipt, profile)
        print(trial.file_sha(args.receipt), profile["sizes"], flush=True)
        return 0
    if args.stop_by is None:
        parser.error("a user-authorized time cutoff is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
