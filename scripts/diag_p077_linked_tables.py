"""Test whether the same native G4 follows changes in two distant, linked source tables."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from random import Random
import re
from unittest.mock import patch

import torch

from scripts import build_p109c_authored_course as authored
from scripts import diag_p077_file_int8_blocks as packed


files, native, trial, mapped = packed.files, packed.native, packed.trial, packed.mapped
TAG = "p077_linked_tables_file_int8_cpu_v1_20261124"
OUT = packed.OUT.with_name(TAG)
HEADER = "<|im_start|>user\n"
TAIL = "<|im_end|>\n<|im_start|>assistant\n"
TABLE = re.compile(r"^\[table ([^\]\n]+)\]\n([^\n]+)\n\[/table\]$", re.MULTILINE)
LIMIT = 4096 - native.GEN + 1
ARMS = ("full", "both", "guided")
LANGUAGES = {
    "ko": ("배정 장부", "작업 장부", "야간 점검", "작업표에는 다음과 같이 적혀 있습니다. ",
           "배정 장부에서 야간 점검에 지정된 항목을 확인하고, 작업 장부에서 그 항목의 번호를 찾으세요. 숫자만 답하세요."),
    "en": ("Assignment Ledger", "Work Ledger", "Overnight audit", "The work log has these entries. ",
           "Find the field assigned to the overnight audit in the Assignment Ledger. Then look up its number in the Work Ledger. Answer with only the number."),
}


def encode(tokenizer, text):
    return tokenizer.encode(text, add_special_tokens=False).ids


def table(title, body):
    return f"[table {title}]\n{body}\n[/table]"


def candidate_fields(tokenizer, language):
    title, _, item, _, _ = LANGUAGES[language]
    groups = {}
    for index, field in enumerate(authored.FIELDS[language]):
        length = len(encode(tokenizer, table(title, f"{item}: {field}")))
        groups.setdefault(length, []).append(index)
    matches = [items[:2] for items in groups.values() if len(items) >= 2]
    if not matches:
        raise ValueError("the assignment alternatives must have equal token lengths")
    return matches[0]


def candidate_values(tokenizer, fields, seed):
    randomizer = Random(seed)
    groups = {}
    for value in randomizer.sample(range(1200, 9700), 128):
        shape = tuple(len(encode(tokenizer, f" {value}{end}")) for end in (",", "."))
        group = groups.setdefault(shape, [])
        group.append(value)
        if len(group) == 6:
            initial, changed = list(group[:4]), list(group[:4])
            for field, number in zip(fields, group[4:], strict=True):
                changed[field] = number
            return initial, changed
    raise ValueError("the work records need six distinct matched-width numbers")


def shared_gaps(tokenizer, language, total):
    ids = native.training.controls.diverse_filler(tokenizer, language, total)
    center = len(ids) // 2
    for trim in range(8):
        for split in range(center - 6, center + 7):
            a = tokenizer.decode(ids[:split], skip_special_tokens=False)
            b = tokenizer.decode(ids[split:len(ids) - trim], skip_special_tokens=False)
            if "\ufffd" not in a + b and a != b:
                return a, b
    raise ValueError("the two background spans must round-trip as UTF-8")


def views(language, text):
    title, ledger, item, _, ask = LANGUAGES[language]
    blocks = list(TABLE.finditer(text))
    if (not text.startswith(HEADER) or not text.endswith(ask + TAIL) or len(blocks) != 2
            or {block[1] for block in blocks} != {title, ledger}):
        raise ValueError("the two named sources and stable question must occur exactly once")
    by_title = {block[1]: block[2] for block in blocks}
    name, field = by_title[title].split(": ", 1)
    names = authored.FIELDS[language]
    if name != item or field not in names:
        raise ValueError("the first source must resolve one known field label")
    both = HEADER + "\n\n".join(block[0] for block in blocks) + "\n\n" + ask + TAIL
    guided = HEADER + by_title[ledger] + " " + authored.field_question(language, names.index(field), 2) + TAIL
    return {"full": text, "both": both, "guided": guided}, field


def variants(tokenizer, language, seed):
    route, ledger, item, lead, ask = LANGUAGES[language]
    fields = candidate_fields(tokenizer, language)
    values = candidate_values(tokenizer, fields, seed)
    names = authored.FIELDS[language]
    cells = [(a, b, table(route, f"{item}: {names[field]}"),
              table(ledger, lead + authored.values_text(language, numbers, range(4))), str(numbers[field]))
             for a, field in enumerate(fields) for b, numbers in enumerate(values)]
    if len({value for _, _, _, _, value in cells}) != 4:
        raise ValueError("the factorial panel must have distinct answers in all four states")
    for total in range(3984, 3903, -8):
        gap1, gap2 = shared_gaps(tokenizer, language, total)
        panel = []
        for order in (0, 1):
            for a, b, left, right, gold in cells:
                first, second = (left, right) if order == 0 else (right, left)
                full = HEADER + "\n\n".join((first, gap1, second, gap2, ask)) + TAIL
                view, linked = views(language, full)
                if linked != names[fields[a]]:
                    raise ValueError("the source field and independent fixture disagree")
                prompt = {arm: dict(text=text, ids=encode(tokenizer, text)) for arm, text in view.items()}
                for arm, fixture in prompt.items():
                    if (tokenizer.decode(fixture["ids"], skip_special_tokens=False) != fixture["text"]
                            or (arm != "full" and len(fixture["ids"]) > 896)):
                        raise ValueError("a request did not preserve text or exceeded the normal input limit")
                panel.append(dict(case=f"{language}-o{order}-a{a}-b{b}", language=language, order=order,
                                  assignment=a, inventory=b, gold=gold, field=linked, prompt=prompt))
        lengths = {len(row["prompt"]["full"]["ids"]) for row in panel}
        if len(lengths) == 1 and 3968 <= next(iter(lengths)) <= LIMIT:
            return panel
    raise ValueError("the natural UTF-8 routes must share the same near-limit input length")


def prepare():
    profile, (identity, _, cli, _, engine) = packed.prepare()
    archive = packed.OUT / "report.json"
    prior = trial.read_json(archive)
    if prior["profile"] != profile or not all(row["ids_equal"] for row in prior["rows"]):
        raise ValueError("need the same verified packed file cache and native engine")
    tokenizer, special, *_ = trial.load_cases()
    rows = [case for i, lang in enumerate(LANGUAGES) for case in variants(tokenizer, lang, 160403 + i)]
    if len(rows) != 16 or len({tuple(row["prompt"]["full"]["ids"]) for row in rows}) != len(rows):
        raise ValueError("both orders and both independent changes must reach the model")
    h = sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest().upper()
    receipt = dict(tag=TAG, source=trial.file_sha(Path(__file__)), past_result=trial.file_sha(archive),
                   engine_sha256=sha256(engine).hexdigest().upper(), previous=profile, panel_sha256=h,
                   stop=[special["<|im_end|>"], tokenizer.token_to_id("<eos>")],
                   count=len(rows), cpu=profile["cpu"],
                   lengths={arm: sorted({len(row["prompt"][arm]["ids"]) for row in rows}) for arm in ARMS})
    return receipt, (identity, cli, rows, engine)


def engine_path(source, receipt):
    file = packed.OUT / "int8" / "compiler.json"
    prior = trial.read_json(file)
    entry = prior["binaries"]["64"][1]
    binary = Path(entry["path"])
    if prior["source_sha256"] != receipt["engine_sha256"]:
        raise ValueError("the completed candidate compiler used a different engine source")
    if binary.is_file() and native.base.SHA(binary) == entry["sha256"]:
        trial.publish(OUT / "compiler.json", prior)
        return binary
    with patch.object(native.bounded, "OUT", OUT):
        return native.bounded.build(source, caps=(64,))[64][1]


def summaries(results):
    summary = {}
    for arm in ARMS:
        records = [row for row in results if row["arm"] == arm]
        languages = {}
        for language in LANGUAGES:
            subset = [row for row in records if row["language"] == language]
            orders = [[row for row in subset if row["order"] == i] for i in (0, 1)]
            if any(len(order) != 4 for order in orders):
                raise ValueError("all four independent states in both orders must be recorded")
            groups = [all(row["exact"] for row in order) for order in orders]
            languages[language] = dict(content=sum(row["content_correct"] for row in subset),
                                       exact=sum(row["exact"] for row in subset), eot=sum(row["eot"] for row in subset),
                                       groups=sum(groups), both_orders=all(groups),
                                       peak_rss=max(row["peak_rss"] for row in subset))
        summary[arm] = languages
    return summary


def run(receipt, deadline):
    checked, (identity, cli, rows, engine) = prepare()
    if (checked != receipt or OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != ""
            or deadline.tzinfo is None or deadline > files.AUTHORIZATION_END
            or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 480):
        raise ValueError("the sealed two-source experiment needs an authorized CPU-only window")
    os.sched_setaffinity(0, {receipt["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    trial.publish(OUT / "requests.json", rows)
    binary = engine_path(engine, checked)
    captures, results = {}, []
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            ancestor = receipt["previous"]["previous"]["prior"]["source_receipt"]["prior"]["prior"]
            state = ancestor["native"]["native"]["native"]["state_sha256"]
            model = mapped.request.pack_model(stack, state, identity)
        archive = os.open(files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, archive)
        for i, case in enumerate(rows):
            order = ARMS if i % 2 == 0 else tuple(reversed(ARMS))
            for arm in order:
                request = case["prompt"][arm]
                key = tuple(request["ids"])
                if key not in captures:
                    capture, elapsed = files.request(OUT, dict(request, case=case["case"]), arm, cli, binary,
                                                       model, archive, deadline)
                    captures[key] = capture, elapsed, case["case"]
                capture, elapsed, original = captures[key]
                native_out = capture["native"]
                ids = native_out["ids"]
                text = capture["decoding"]["text"].strip()
                eot, correct = ids[-1] == receipt["stop"][0], text == case["gold"]
                results.append(dict(case=case["case"], arm=arm, language=case["language"], order=case["order"],
                                    assignment=case["assignment"], inventory=case["inventory"], field=case["field"],
                                    gold=case["gold"], answer=text, ids=ids, eot=eot, content_correct=correct,
                                    exact=eot and correct, actual_request=original, input_tokens=len(key),
                                    elapsed=elapsed, first=native_out["seconds"][0],
                                    peak_rss=native.bounded.prior.peak(capture), read=native_out["kv_read_bytes"]))
            print(json.dumps(dict(case=case["case"], completed=len(results), requests=len(captures)), ensure_ascii=False), flush=True)
    trial.publish(OUT / "report.json", dict(profile=receipt, results=results, summaries=summaries(results),
                                            distinct_requests=len(captures)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        profile, _ = prepare()
        trial.publish(args.receipt, profile)
        print(trial.file_sha(args.receipt), profile["lengths"], flush=True)
        return 0
    if args.stop_by is None:
        parser.error("an authorized cutoff with a timezone is required")
    run(trial.read_json(args.receipt), args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
