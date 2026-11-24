"""Measure a fully retained 4,096-token context with the compact CPU runtime."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p077_compact_chat32_request as mapped
from scripts.diag_p108_g4_compact_fixed_edit_text import seal


TAG = "p077_g4_context4096_cpu_v1_20261121"
OUT = mapped.OUT.with_name(TAG)
native, trial, wide = mapped.native, mapped.trial, mapped.wide
CONTEXT = 4096
RECENT = 128
ARMS = {"k4v3": (4, 3), "k2v2": (2, 2)}


def source_for(stop, bits):
    r6 = native.tiled_rope.render(native.source_for(2048, 3, *stop))
    r6 = native.port.replace_once(r6, b"Limit = 2048;", b"Limit = 4096;")
    key, value = bits
    cache = f"cache(capacity, capacity - {RECENT}, {key}, {value})".encode()
    r6 = native.port.replace_once(r6, b"cache(capacity, 1920, 4, 3)", cache)
    return wide.render(r6, "online8")


def cache_size(length, bits):
    key, value = bits
    packed = length // 32 * 32
    old = max(0, (length - RECENT) // 32 * 32)
    codes = (packed - old) * 256 + old * 128 * (key + value) // 8
    minima = (old // 32 * 128 if key == 2 else 0) + (old * 2 if value == 2 else 0)
    scales = packed // 32 * 128 + packed * 2
    tail = min(length, 31) * 256
    return 14 * (codes + 2 * (scales + minima + tail))


def text_pairs(tok, table_rows, selected):
    pairs = []
    limit = CONTEXT - native.GEN + 1
    separator = tok.encode("\n", add_special_tokens=False).ids
    for item in selected:
        row = table_rows[item["root"]]
        for side in range(2):
            head, table, ask = native.wide.parts(tok, row, side)
            filler = native.training.controls.diverse_filler(
                tok, row["language"], limit - len(head) - len(table) - len(ask) - len(separator) - 2)
            for trim in range(32):
                blocks = (filler[trim:] + separator + table, table + separator + filler[trim:])
                texts = [tok.decode(head + block + ask, skip_special_tokens=False) for block in blocks]
                encoded = [tok.encode(text, add_special_tokens=False).ids for text in texts]
                if (any("\ufffd" in text for text in texts) or len(encoded[0]) != len(encoded[1])
                        or not limit - 35 <= len(encoded[0]) <= limit
                        or any(tok.decode(ids, skip_special_tokens=False) != text for ids, text in zip(encoded, texts))):
                    continue
                for place, text, ids in zip(("near", "far"), texts, encoded, strict=True):
                    table_text = tok.decode(table, skip_special_tokens=False)
                    if text.count(table_text) != 1:
                        raise ValueError("the value evidence must occur exactly once")
                    table_start = text.index(table_text)
                    table_end = table_start + len(table_text)
                    offsets = tok.encode(text, add_special_tokens=False).offsets
                    tokens_after = sum(start >= table_end for start, _ in offsets)
                    pairs.append(dict(root=row["root"], language=row["language"], side=side, place=place, text=text,
                                      ids=ids, gold=row["gold"][side], tokens_after_evidence=tokens_after))
                break
            else:
                raise ValueError("could not form a stable near/far UTF-8 pair")
    if len(pairs) != 8 or len({tuple(row["ids"]) for row in pairs}) != 8:
        raise ValueError("the long paired test must contain eight distinct prompts")
    return pairs


def prepare():
    existing, (tok, special, texts, refs, model, decoder, encoder) = mapped.prepare()
    _, (_, _, table_rows, _, _) = native.prepare(rope=True)
    selected = [texts[i] for i in (0, 4)]
    rows = text_pairs(tok, {row["root"]: row for row in table_rows}, selected)
    stop = (special["<|im_end|>"], tok.token_to_id("<eos>"))
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), native=existing, stop=list(stop),
                context=CONTEXT, recent=RECENT,
                arms={name: dict(bits=list(bits), engine=sha256(source_for(stop,bits)).hexdigest())
                      for name, bits in ARMS.items()},
                requests=trial.state_sha({str(i): torch.tensor(row["ids"]) for i, row in enumerate(rows)}),
                prior_cases={texts[i]["language"]: dict(ids=refs[i]["native"]["ids"],
                                                       prompt_tokens=len(texts[i]["ids"])) for i in (0,4)})
    return plan, (tok, rows, model, decoder, encoder)


def run(plan, deadline):
    if (OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or not deadline.tzinfo
            or deadline > mapped.compact.AUTHORIZATION_END):
        raise ValueError("requires a fresh authorized CPU-only request")

    def gate(reserve):
        if (OUT / "STOP").exists() or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < reserve:
            raise TimeoutError("the long CPU request reached its stop boundary")

    gate(480)
    checked, (tok, rows, model, decode_table, input_table) = prepare()
    if checked != plan:
        raise ValueError("the sealed long-context inputs changed")
    cpus = set(model["cpus"]) & os.sched_getaffinity(0)
    cpu = min(cpus)
    os.sched_setaffinity(0, {cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    binaries = {}
    for name, bits in ARMS.items():
        folder = OUT / name
        folder.mkdir()
        with patch.object(native.bounded, "OUT", folder):
            binaries[name] = native.bounded.build(source_for(plan["stop"], bits), caps=(64,))[64][1]
    normal, parts = native.text_codec(OUT)
    source = native.port.replace_once(normal.read_bytes(), b"len(ids) <= 2041",
                                      f"len(ids) <= {CONTEXT - native.GEN + 1}".encode())
    normal.write_bytes(source)
    mapped.request.render_decoder(normal, decode_table)
    wrapper = OUT / "mapped_request.py"
    mapped.render_input(wrapper, normal, input_table)
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            state = plan["native"]["native"]["native"]["state_sha256"]
            image = mapped.request.pack_model(stack, state, model)
        assets = [image]
        for i, part in enumerate(parts):
            fd = native.base.memfile(f"p077-4096-text-wire-{i}")
            stack.callback(os.close, fd)
            native.bounded.text.store(fd, part)
            seal(fd)
            assets.append(fd)
        results = []
        for i, row in enumerate(rows):
            arms = tuple(ARMS) if i % 2 == 0 else tuple(reversed(ARMS))
            for arm in arms:
                gate(100)
                ids = row["ids"]
                expected = dict(encoding=dict(ids=ids), native=dict(model_bytes=os.fstat(image).st_size,
                                kv_bytes=cache_size(len(ids) + native.GEN - 1, ARMS[arm])))
                raw_file = OUT / f"{arm}_{i:02d}.json"
                stats = native.port.request(binaries[arm], assets, row["text"].encode("utf-8"),
                                            raw_file, expected, wrapper=wrapper)
                raw = trial.read_json(raw_file)
                decoded = native.decoded(tok, raw["native"], row["gold"], plan["stop"])
                result = dict(index=i, arm=arm, language=row["language"], side=row["side"], place=row["place"],
                              gold=row["gold"], tokens_after_evidence=row["tokens_after_evidence"],
                              input_tokens=len(ids), first=raw["native"]["seconds"][0], **decoded,
                              seconds=stats["seconds"], scratch_bytes=stats["scratch_bytes"],
                              peak_rss=stats["peak_rss"], kv_bytes=stats["kv_bytes"])
                results.append(result)
                print(json.dumps(result, ensure_ascii=False), flush=True)
    trial.publish(OUT / "report.json", dict(plan=plan, cpu=cpu, results=results))


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
        parser.error("requires a sealed long-context comparison and an authorized cutoff")
    run(plan, args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
