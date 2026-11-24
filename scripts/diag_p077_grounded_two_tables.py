"""Compare named-table routing with a fixed first table on independent long requests."""

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
from random import Random
import re
import sys

import torch

from scripts import train_p077_grounded_separate_views as separate


TAG = "p077_grounded_two_tables_gpu_v1_20261121"
OUT = separate.OUT.with_name(TAG)
AUTHORIZATION_END = datetime.fromisoformat("2026-11-21T17:00:00+09:00")
HEADER = "<|im_start|>user\n"
TAIL = "<|im_end|>\n<|im_start|>assistant\n"
TABLE = re.compile(r"\[table (L[0-9]{4})\]\n([^\n]+)\n\[/table\]")
QUESTION = re.compile(r"\[question (L[0-9]{4})\]\n([^\n]+)$")
FILLER = {
    "ko": "이 절은 이전 분기의 일정을 설명합니다. 새 운영 절차는 다음 회의에서 다시 검토합니다. ",
    "en": "This section describes last quarter's calendar. The next meeting will review the new procedure. ",
}
trial = separate.trial
foundation = separate.foundation
authored = separate.data.authored


def parse_request(tok, text):
    tables = list(TABLE.finditer(text))
    question = QUESTION.search(text)
    if question is None or len(tables) != 2 or tables[-1].end() >= question.start():
        raise ValueError("the request must have two marked tables followed by a question")
    titles = [match[1] for match in tables]
    if len(set(titles)) != 2 or question[1] not in titles:
        raise ValueError("the requested table must match one unique identifier")
    query = tok.encode(HEADER + question[2] + TAIL).ids
    spans = []
    for match in tables:
        ids = tok.encode(HEADER + match[2]).ids
        positions, values = separate.previous.observation(tok, ids)
        spans.append(dict(table=ids, query=query, positions=positions, values=values))
    return titles.index(question[1]), spans


def fixture(tok):
    chat_prefix = tok.encode(HEADER, add_special_tokens=False).ids
    training, _ = separate.training_samples(tok, chat_prefix)
    used, _ = separate.training.old_value_groups(tok)
    for row in training:
        text = tok.decode(row["table"], skip_special_tokens=False)
        used.add(tuple(sorted(int(value) for value in foundation.VALUE.findall(text))))

    rng = Random(823747)
    samples = []
    payloads = []
    for group in range(64):
        language = ("ko", "en")[group % 2]
        field = (group // 2) % 4
        titles = [f"L{item}" for item in rng.sample(range(1000, 9999), 2)]
        while True:
            values = rng.sample(range(1000, 9999), 8)
            keys = [tuple(sorted(values[i:i+4])) for i in (0, 4)]
            if used.isdisjoint(keys):
                used.update(keys)
                break
        lead = "작업표에는 다음과 같이 적혀 있습니다. " if language == "ko" else "The work log has these entries. "
        entries = [lead + authored.values_text(language, values[i:i+4], rng.sample(range(4), 4)) for i in (0, 4)]
        blocks = [f"[table {title}]\n{table}\n[/table]" for title, table in zip(titles, entries, strict=True)]
        root = authored.digest([titles, values, entries, language, field])
        ask = authored.field_question(language, field, (group // 8) % 3)
        filler = FILLER[language]
        for order in ((0, 1), (1, 0)):
            for target in (0, 1):
                tail = f"\n[question {titles[target]}]\n{ask}"
                # Keep the payload and both gap sizes fixed across query and order changes.
                gap = filler * (880 // len(tok.encode(filler).ids))
                text = f"{blocks[order[0]]}\n{gap}\n{blocks[order[1]]}\n{gap}{tail}"
                width = len(tok.encode(HEADER + text + TAIL).ids)
                resolved, spans = parse_request(tok, text)
                if resolved != order.index(target) or not 1550 <= width <= 2048:
                    raise ValueError(f"invalid table order or request width: {width}")
                gold = str(values[target*4+field])
                if gold not in spans[resolved]["values"] or gold in spans[1-resolved]["values"]:
                    raise ValueError("the authored gold must only come from its own table")
                metadata = dict(root=root, language=language, side=target, gold=gold)
                samples.append(dict(order=order, target=target, width=width, routed=resolved,
                                    spans=[dict(span, **metadata) for span in spans]))
                payloads.append(dict(root=root, order=order, target=target, width=width, text=text, gold=gold))
    return samples, payloads


def prepare():
    tok, special, _, _, _ = trial.load_cases()
    base_path = foundation.OUT / "foundation.pt"
    head_path = separate.OUT / "selector.pt"
    previous = trial.read_json(separate.OUT / "report.json")
    terminal = trial.read_json(separate.OUT / "supervisor.json")
    fingerprint = previous["plan"]["source"]["base"]["state_sha256"]
    if (terminal["returncode"] or terminal["stop_reason"]
            or trial.file_sha(head_path) != previous["head_checkpoint_sha256"]):
        raise ValueError("the input head must come from the completed separate-view experiment")
    samples, payloads = fixture(tok)
    plan = dict(tag=TAG, body_state_sha256=fingerprint, body_file_sha256=trial.file_sha(base_path),
                head_sha256=previous["head_checkpoint_sha256"], fixture_sha256=authored.digest(payloads),
                decoder_input_sha256=authored.digest(samples), requests=len(samples),
                width_min=min(row["width"] for row in samples), width_max=max(row["width"] for row in samples),
                sources={str(path.relative_to(trial.ROOT)): trial.file_sha(path) for path in
                         (Path(__file__), Path(separate.__file__), Path(separate.previous.__file__))})
    return plan, (tok, special, samples, payloads)


def worker(plan, fraction):
    torch.set_num_threads(1)
    checked, (tok, special, samples, payloads) = prepare()
    if checked != plan:
        raise ValueError("table routing inputs changed")
    torch.cuda.set_per_process_memory_fraction(fraction)
    weights = torch.load(foundation.OUT / "foundation.pt", weights_only=True, map_location="cpu")
    state = weights["model"]
    cfg = replace(separate.wide.TMTConfig(**weights["config"]), max_seq_len=trial.WIDTH)
    saved = torch.load(separate.OUT / "selector.pt", weights_only=True, map_location="cpu")
    if trial.state_sha(state) != saved["body_state_sha256"] or saved["body_state_sha256"] != plan["body_state_sha256"]:
        raise ValueError("body and selection head do not share the sealed state")
    model = separate.wide.TiedMLPTransformer(cfg).to("cuda").eval().requires_grad_(False)
    model.load_state_dict(state)
    model.freeze_quant()
    selector = foundation.ValueLink(cfg.dim).to("cuda").eval()
    selector.load_state_dict(saved["train_head"])
    pad, end = (special[key] for key in ("<pad>", "<|im_end|>"))
    results = []
    for offset in range(0, len(samples), 4):
        rows = samples[offset:offset+4]
        spans = [span for row in rows for span in row["spans"]]
        predictions = separate.observe(selector, separate.features(model, spans, pad), spans, tok, end)
        for i, row in enumerate(rows):
            choices = predictions[2*i:2*i+2]
            results.append(dict(root=choices[0]["root"], language=choices[0]["language"],
                                target=row["target"], order=row["order"], routed=row["routed"],
                                fixed_first=choices[0], named=choices[row["routed"]]))
    counts = {}
    for route in ("fixed_first", "named"):
        counts[route] = {}
        for language in ("ko", "en"):
            subset = [row for row in results if row["language"] == language]
            groups = [subset[i:i+4] for i in range(0, len(subset), 4)]
            if not all(len({row["root"] for row in group}) == 1 and
                       len({(row["order"], row["target"]) for row in group}) == 4 for group in groups):
                raise ValueError("a table group is missing a question or order")
            counts[route][language] = dict(requests=sum(row[route]["correct"] for row in subset),
                                           all_four=sum(all(row[route]["correct"] for row in group) for group in groups))
    trial.publish(OUT / "report.json", dict(plan=plan, counts=counts, inputs=payloads, outputs=results,
                  peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))
    print(json.dumps(counts), flush=True)


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
        parser.error("run requires a sealed fixture and authorized cutoff")
    return separate.wide.owner.supervise(worker, (plan,), OUT, args.stop_by,
                                         authorization_end=AUTHORIZATION_END, min_seconds=180)


if __name__ == "__main__":
    sys.exit(main())
