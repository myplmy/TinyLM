"""Place the same directly queried ledger early or late in a long request."""

import argparse
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
from unittest.mock import patch

import torch

from scripts import diag_p077_file_int8_staged24 as file24
from scripts import diag_p077_linked_tables as tables


files, native, trial, mapped = file24.files, file24.native, file24.trial, file24.mapped
TAG = "p077_long_guided_placement_cpu_v1_20261124"
OUT = file24.OUT.with_name(TAG)
ARMS = ("early", "late")


def render(tokenizer, lang, items):
    _, ledger, _, _, _ = tables.LANGUAGES[lang]
    for requested in range(3976, 3903, -8):
        filler = "\n\n".join(tables.shared_gaps(tokenizer, lang, requested))
        rows = []
        for item in items:
            tables_in = tables.TABLE.finditer(item["prompt"]["full"]["text"])
            body = next(block[2] for block in tables_in if block[1] == ledger)
            short = item["prompt"]["guided"]["text"]
            if not short.startswith(tables.HEADER + body + " ") or item["gold"] in filler:
                raise ValueError("the neutral background or original direct lookup changed")
            question = short[len(tables.HEADER + body + " "):-len(tables.TAIL)]
            arms = {}
            for name, blocks in (("early", (body, filler, question)), ("late", (filler, body, question))):
                text = tables.HEADER + "\n\n".join(blocks) + tables.TAIL
                ids = tables.encode(tokenizer, text)
                if tokenizer.decode(ids, skip_special_tokens=False) != text:
                    raise ValueError("the same source passages must round-trip exactly")
                arms[name] = dict(text=text, ids=ids)
            rows.append(dict(case=item["case"], language=lang, gold=item["gold"], arms=arms))
        lengths = {len(value["ids"]) for row in rows for value in row["arms"].values()}
        if len(lengths) == 1 and 3968 <= next(iter(lengths)) <= tables.LIMIT:
            return rows
    raise ValueError("no source order reached the same long context length")


def prepare():
    bound24, (identity, _, cli, _, engine_src) = file24.prepare()
    previous, (_, _, archived_items, _) = tables.prepare()
    record = tables.OUT / "report.json"
    archive = trial.read_json(record)
    old = {row["case"]: row for row in archive["results"] if row["arm"] == "guided"}
    if archive["profile"] != previous or len(old) != len(archived_items):
        raise ValueError("the original direct lookup inputs or outputs changed")
    tokenizer, special, *_ = trial.load_cases()
    chosen = {tuple(item["prompt"]["guided"]["ids"]): item for item in reversed(archived_items)}
    if len(chosen) != 8:
        raise ValueError("eight distinct direct prompts are required")
    rows = [row for lang in tables.LANGUAGES for row in render(
        tokenizer, lang, [item for item in chosen.values() if item["language"] == lang])]
    compile_receipt = file24.OUT / "width24" / "compiler.json"
    compiled = trial.read_json(compile_receipt)
    entry = compiled["binaries"]["64"][1]
    binary = Path(entry["path"])
    if (compiled["source_sha256"].upper() != sha256(engine_src).hexdigest().upper()
            or trial.file_sha(binary).upper() != entry["sha256"].upper()):
        raise ValueError("the existing executable must be the validated file INT8 width-24 binary")
    digest = sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper()
    bound = dict(tag=TAG, source=trial.file_sha(Path(__file__).resolve()), long_panel_sha256=digest,
                 previous_report=trial.file_sha(record), prior=bound24, engine_sha256=trial.file_sha(binary),
                 stop=special["<|im_end|>"], tokens={lang: len(next(row["arms"]["early"]["ids"] for row in rows
                        if row["language"] == lang)) for lang in tables.LANGUAGES})
    return bound, (identity, cli, binary, rows, old)


def run(profile, deadline):
    current, (identity, cli, engine, rows, old) = prepare()
    if (current != profile or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or deadline.tzinfo is None
            or deadline > files.AUTHORIZATION_END or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 340):
        raise ValueError("the sealed measurement needs the admitted CPU-only scope and time")
    os.sched_setaffinity(0, {profile["prior"]["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir(exist_ok=False)
    results, grouped = [], defaultdict(list)
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            ancestor = profile["prior"]["prior"]["previous"]["prior"]["source_receipt"]["prior"]["prior"]
            state = ancestor["native"]["native"]["native"]["state_sha256"]
            model = mapped.request.pack_model(stack, state, identity)
        codec = os.open(files.codec.ASSET, os.O_RDONLY)
        stack.callback(os.close, codec)
        for index, row in enumerate(rows):
            for arm in ARMS if index % 2 == 0 else reversed(ARMS):
                case = dict(row["arms"][arm], case=row["case"])
                capture, seconds = files.request(OUT, case, arm, cli, engine, model, codec, deadline)
                output = capture["native"]
                text = capture["decoding"]["text"].strip()
                eot = bool(output["ids"] and output["ids"][-1] == profile["stop"])
                measure = dict(case=row["case"], arm=arm, language=row["language"], gold=row["gold"], answer=text,
                               short_exact=old[row["case"]]["exact"], exact=text == row["gold"] and eot,
                               content=text == row["gold"], eot=eot, seconds=seconds, input_tokens=len(case["ids"]),
                               peak_rss=native.bounded.prior.peak(capture), file_read_bytes=output["kv_read_bytes"])
                results.append(measure)
                grouped[f"{row['language']}/{arm}"].append(measure)
                print(json.dumps(measure, ensure_ascii=False), flush=True)
    summary = {key: dict(rows=len(items), exact=sum(row["exact"] for row in items),
                         content=sum(row["content"] for row in items), short_exact=sum(row["short_exact"] for row in items),
                         median_seconds=median(row["seconds"] for row in items),
                         max_rss=max(row["peak_rss"] for row in items)) for key, items in grouped.items()}
    trial.publish(OUT / "report.json", dict(profile=profile, results=results, summary=summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        profile, _ = prepare()
        trial.publish(args.profile.absolute(), profile)
        print(profile["tokens"], trial.file_sha(args.profile), flush=True)
    elif args.stop_by:
        run(trial.read_json(args.profile), args.stop_by)
    else:
        parser.error("--stop-by is required for the measured run")


if __name__ == "__main__":
    main()
