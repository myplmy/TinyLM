"""Train matched two-stage value heads with or without first-source supervision."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
import os
from pathlib import Path
from random import Random
from time import perf_counter

import torch
from torch import nn
from torch.nn import functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p077_linked_tables as linked
from scripts import run_p109c_table_value_link as value_link
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer


trial, authored = linked.trial, linked.authored
TAG = "p077_linked_table_supervision_cpu_v1_20261124"
OUT = linked.OUT.with_name(TAG)
EXPORT = linked.native.training.EXPORT_OUT
BODY = EXPORT / "near_only.pt"
SEED, EPOCHS, BATCH = 224901, 8, 32
ARMS = {"final_only": 0., "final_and_assignment": .5}
SCHEMA = {
    "ko": ("배정표", "번호표",
           ("달빛", "나루", "솔밭", "다람", "아침", "별꽃", "돌담", "푸른", "여울", "구름", "조약", "봄비"),
           ("한별", "오름", "가람", "노을", "샛별", "자작", "보름", "해솔", "은빛", "새싹", "겨울", "다온"),
           ("배정표에서 {name}의 항목을 확인하세요. 번호표에서 그 항목의 번호를 답하세요.",
            "{name}에게 배정된 항목의 번호는 무엇인가요? 두 표를 읽고 숫자만 쓰세요."),
           ("두 표를 대조해 {name}이 사용할 번호 하나를 알려주세요.",
            "{name}이 담당하는 업무와 짝이 되는 번호를 찾아 숫자로만 적어주세요.")),
    "en": ("Assignment register", "Number register",
           ("Aster", "Brook", "Rill", "Moss", "Flint", "Pearl", "Spruce", "Iris", "Lark", "Fern", "Dune", "Cedar"),
           ("Thistle", "Reed", "Willow", "Hazel", "Marsh", "Yarrow", "Oriel", "Sorrel", "Fleck", "Ember", "Fjord", "Vine"),
           ("Find the field assigned to {name} in the assignment register. Give its number from the number register.",
            "Use both registers to find the number for the field assigned to {name}. Write only the number."),
           ("Which number should {name} use? Cross-check the two records before answering.",
            "Return the numeric code linked to the responsibility given to {name}.")),
}


def table(title, lines):
    text = f"[table {title}]\n"
    spots = []
    for line in lines:
        text += line + "\n"
        spots.append(len(text) - 2)
    return text + "[/table]", spots


def request(tokenizer, assignment, listing, ask, order):
    combined = linked.HEADER
    spots = [None, None]
    sources = (assignment, listing)
    for section in (order, 1 - order):
        text, local = sources[section]
        spots[section] = [len(combined) + position for position in local]
        combined += text + "\n\n"
    combined += ask + linked.TAIL
    encoding = tokenizer.encode(combined, add_special_tokens=False)
    if len(encoding.ids) > 256 or tokenizer.decode(encoding.ids, skip_special_tokens=False) != combined:
        raise ValueError("the compact source and query must preserve one bounded input")
    positions = []
    for offset in (*spots[0], *spots[1]):
        hits = [i for i, (start, stop) in enumerate(encoding.offsets) if start <= offset < stop]
        if not hits or hits[-1] >= len(encoding.ids) - 1:
            raise ValueError("an observed source candidate is outside the prompt")
        positions.append(hits[-1])
    if len(set(positions)) != 8:
        raise ValueError("each source candidate must have its own input token position")
    return encoding.ids, [len(encoding.ids) - 1, *positions]


def panel(tokenizer, split):
    test = split == "test"
    rng = Random(SEED + int(test))
    roots, low = (32, 6000) if test else (64, 1000)
    numbers = rng.sample(range(low, low + 3400), roots * 6)
    examples = []
    for root in range(roots):
        language = ("ko", "en")[root % 2]
        name_a, name_b, names_fit, names_test, asks_fit, asks_test = SCHEMA[language]
        names = rng.sample(names_test if test else names_fit, 4)
        position = (root // 2) % 4
        other = (position + rng.randrange(1, 4)) % 4
        ask = (asks_test if test else asks_fit)[(root // 8) % 2].format(name=names[position])
        fields = authored.FIELDS[language]
        a0 = rng.sample(range(4), 4)
        a1 = a0.copy()
        a1[position], a1[other] = a0[other], a0[position]
        b0 = numbers[root * 6 : root * 6 + 4]
        b1 = b0.copy()
        b1[a0[position]], b1[a1[position]] = numbers[root * 6 + 4 : root * 6 + 6]
        cell_order = rng.sample(range(4), 4)
        targets = {b[a[position]] for a in (a0, a1) for b in (b0, b1)}
        if len(targets) != 4:
            raise ValueError("independent assignment and number changes need four unique answers")
        for order in (0, 1):
            for assignment, a in enumerate((a0, a1)):
                left = table(name_a, [f"{entity}: {fields[field]}" for entity, field in zip(names, a, strict=True)])
                for inventory, b in enumerate((b0, b1)):
                    right = table(name_b, [f"{fields[i]}: {b[i]}" for i in cell_order])
                    tokens, sites = request(tokenizer, left, right, ask, order)
                    examples.append(dict(root=f"{split}-{root}", language=language, order=order, assignment=assignment,
                                         inventory=inventory, tokens=tokens, sites=sites, source=position,
                                         value=cell_order.index(a[position]), values=[str(b[i]) for i in cell_order]))
    if len({tuple(r["tokens"]) for r in examples}) != roots * 8:
        raise ValueError("the compact factorial panel needs distinct inputs")
    return examples


def prepare():
    export, terminal = (trial.read_json(EXPORT / name) for name in ("report.json", "supervisor.json"))
    if (trial.file_sha(BODY) != export["checkpoint_sha256"] or terminal["returncode"] != 0
            or terminal["stop_reason"] is not None or terminal["card_after_exit"]["compute_pids"] != []):
        raise ValueError("requires the existing completed and admitted P077 checkpoint")
    tokenizer, symbols, *_ = trial.load_cases()
    train, test = panel(tokenizer, "train"), panel(tokenizer, "test")
    train_values = {s for row in train for s in row["values"]}
    test_values = {s for row in test for s in row["values"]}
    if train_values & test_values or {tuple(r["tokens"]) for r in train} & {tuple(r["tokens"]) for r in test}:
        raise ValueError("the held-out number inventory and prompts must be disjoint from the new training inputs")
    inputs = {name: authored.digest(rows) for name, rows in (("train", train), ("test", test))}
    source = {name: trial.file_sha(path) for name, path in (("runner", Path(__file__)),
              ("readout", Path(value_link.__file__)), ("body_receipt", EXPORT / "report.json"))}
    profile = dict(tag=TAG, state_sha256=export["state_sha256"], checkpoint_sha256=export["checkpoint_sha256"],
                   inputs=inputs, source=source, rows=[len(train), len(test)], max_tokens=max(
                       len(row["tokens"]) for row in train + test), arms=ARMS, seed=SEED, epochs=EPOCHS,
                   batch=BATCH, precision="CPU_FP32_MATH", body_update=False)
    return profile, (tokenizer, symbols, train, test)


class LinkedValueHeads(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.first = value_link.ValueLink(dim)
        self.second = value_link.ValueLink(dim)

    def forward(self, hidden):
        batch, _, dim = hidden.shape
        sites = torch.arange(5).expand(batch, -1)
        first_scores = self.first(hidden[:, :5], sites)
        assignment = hidden[:, 1:5, None, :]
        table_values = hidden[:, None, 5:, :].expand(-1, 4, -1, -1)
        options = torch.cat((assignment, table_values), dim=2).reshape(4 * batch, 5, dim)
        second_scores = self.second(options, torch.arange(5).expand(4 * batch, -1)).reshape(batch, 4, 4)
        joint = first_scores.log_softmax(1)[:, :, None] + second_scores.log_softmax(2)
        return first_scores, joint.logsumexp(1)


@torch.no_grad()
def features(model, rows, pad, deadline):
    result = []
    for offset in range(0, len(rows), 16):
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("the CPU feature extraction reached its authorization cutoff")
        items = rows[offset:offset + 16]
        width = max(len(row["tokens"]) for row in items)
        x = torch.tensor([row["tokens"] + [pad] * (width - len(row["tokens"])) for row in items])
        points = torch.tensor([row["sites"] for row in items])
        with sdpa_kernel(SDPBackend.MATH):
            hidden = model(x, return_hidden=True)
        result.append(hidden[torch.arange(len(x))[:, None], points])
    return torch.cat(result)


@torch.no_grad()
def judge(head, inputs, rows, tokenizer, eot):
    a, b = head(inputs)
    decisions = []
    for row, mark, pos in zip(rows, a.argmax(1).tolist(), b.argmax(1).tolist(), strict=True):
        text = row["values"][pos]
        decisions.append(dict(root=row["root"], language=row["language"], order=row["order"],
                              assignment=row["assignment"], inventory=row["inventory"], number=text,
                              gold=row["values"][row["value"]], chosen_first=mark, gold_first=row["source"],
                              ids=[*linked.encode(tokenizer, text), eot], exact=pos == row["value"]))
    stats = {}
    for language in ("ko", "en"):
        language_rows = [row for row in decisions if row["language"] == language]
        groups = {}
        for row in language_rows:
            groups.setdefault(row["root"], []).append(row["exact"])
        if any(len(matches) != 8 for matches in groups.values()):
            raise ValueError("both table orders and four states are required in each test root")
        stats[language] = dict(rows=len(language_rows), first_correct=sum(
            row["chosen_first"] == row["gold_first"] for row in language_rows), number_correct=sum(
            row["exact"] for row in language_rows), groups_all_correct=sum(all(m) for m in groups.values()),
            groups=len(groups))
    return dict(summaries=stats, rows=decisions)


def run(profile, stop):
    checked, (tokenizer, specials, training, test) = prepare()
    if (profile != checked or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or stop.tzinfo is None or stop > linked.files.AUTHORIZATION_END
            or (stop - datetime.now(stop.tzinfo)).total_seconds() < 540):
        raise ValueError("the exact bounded CPU training approval is required")
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)
    torch.manual_seed(SEED)
    saved = torch.load(BODY, weights_only=True, map_location="cpu")
    if trial.state_sha(saved["model"]) != checked["state_sha256"]:
        raise ValueError("the exact P077 frozen body changed")
    body = TiedMLPTransformer(replace(TMTConfig(**saved["config"]), max_seq_len=1024)).eval().requires_grad_(False)
    body.load_state_dict(saved["model"], strict=True)
    body.freeze_quant()
    OUT.mkdir()
    before = perf_counter()
    pad, eot = specials["<pad>"], specials["<|im_end|>"]
    fit, valid = (features(body, rows, pad, stop) for rows in (training, test))
    feature_seconds = perf_counter() - before
    first = torch.tensor([row["source"] for row in training])
    target = torch.tensor([row["value"] for row in training])
    initial = LinkedValueHeads(body.cfg.dim)
    params = sum(p.numel() for p in initial.parameters())
    states = {name: val.detach().clone() for name, val in initial.state_dict().items()}
    answers = {"untrained": judge(initial, valid, test, tokenizer, eot)}
    for name, weight in ARMS.items():
        head = LinkedValueHeads(body.cfg.dim)
        head.load_state_dict(states)
        order = torch.Generator().manual_seed(SEED + 1)
        optimizer = torch.optim.AdamW(head.parameters(), lr=.004, weight_decay=.01)
        steps, losses = 0, []
        for epoch in range(EPOCHS):
            if datetime.now(stop.tzinfo) >= stop:
                raise TimeoutError("the paired CPU learning has reached its approval cutoff")
            epoch_loss = 0.
            for batch in torch.randperm(len(training), generator=order).split(BATCH):
                a, b = head(fit[batch])
                loss = F.nll_loss(b, target[batch]) + weight * F.cross_entropy(a, first[batch])
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
                epoch_loss += float(loss.detach())
                steps += 1
            losses.append(epoch_loss / (len(training) // BATCH))
        answers[name] = dict(judge(head, valid, test, tokenizer, eot), updates=steps, epoch_losses=losses,
                             training=judge(head, fit, training, tokenizer, eot)["summaries"])
        receipt = OUT / f"{name}.pt"
        with receipt.open("xb") as stream:
            torch.save(dict(body_sha256=checked["state_sha256"], head=head.state_dict()), stream)
        answers[name]["weights_sha256"] = trial.file_sha(receipt)
        print(name, steps, answers[name]["summaries"], flush=True)
    if trial.state_sha(body.state_dict()) != checked["state_sha256"]:
        raise ValueError("the supposedly frozen model weights changed")
    trial.publish(OUT / "report.json", dict(profile=profile, features_seconds=feature_seconds,
                                            head_parameters=params, head_fp32_bytes=params * 4, arms=answers,
                                            elapsed_seconds=perf_counter() - before))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        profile, _ = prepare()
        trial.publish(args.receipt, profile)
        print(trial.file_sha(args.receipt), profile["rows"], profile["max_tokens"], flush=True)
        return 0
    if args.stop_by is None:
        parser.error("the user's CPU approval cutoff is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
