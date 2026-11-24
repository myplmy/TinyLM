"""Re-present a known evidence block from an identical long UTF-8 request."""

import argparse
from contextlib import ExitStack
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
from unittest.mock import patch

import torch

from scripts import diag_p077_g4_context4096 as full


TAG = "p077_g4_evidence_window_cpu_v1_20261121"
OUT = full.OUT.with_name(TAG)
native, mapped, trial = full.native, full.mapped, full.trial
LIMIT = 2048 - native.GEN + 1
ARMS = ("recent", "evidence")


def crop_options(tokenizer, text, record, side, prior_ids):
    head, table, ask = native.wide.parts(tokenizer, record, side)
    header, block, question = [tokenizer.decode(part, skip_special_tokens=False) for part in (head, table, ask)]
    if not text.startswith(header + block) or not text.endswith(question):
        raise ValueError("the original raw input must contain the same known evidence and question")
    table_start, table_end, question_start = len(header), len(header + block), len(text) - len(question)
    if not table_end < question_start:
        raise ValueError("the far table must precede unrelated text")
    filler = text[table_end:question_start]
    tokens = tokenizer.encode(filler, add_special_tokens=False)
    ends = [len(text[:p].encode("utf-8")) for p in (table_start, table_end, question_start, len(text))]
    raw = text.encode("utf-8")
    options = {arm: {} for arm in ARMS}
    for arm in ARMS:
        desired = LIMIT - len(head) - len(ask)
        if arm == "evidence":
            desired -= len(table) + 1
        for suffix in range(desired - 32, desired + 8):
            start = tokens.offsets[-suffix][0] + table_end
            filler_begin = len(text[:start].encode("utf-8"))
            ranges = [[0, ends[0]], [filler_begin, ends[2]]]
            if arm == "evidence":
                ranges.extend([None, [ends[0], ends[1]]])
            ranges.append([ends[2], ends[3]])
            payload = b"".join(b"\n" if interval is None else raw[slice(*interval)] for interval in ranges)
            cropped = payload.decode("utf-8")
            ids = tokenizer.encode(cropped, add_special_tokens=False).ids
            if (LIMIT - 32 <= len(ids) <= LIMIT and tuple(ids) not in prior_ids
                    and cropped.startswith(header) and cropped.endswith(question)
                    and (block in cropped) == (arm == "evidence")):
                options[arm][len(ids)] = (ids, ranges)
    shared = options["recent"].keys() & options["evidence"].keys()
    if not shared:
        raise ValueError("the oracle and recent views need the same fresh input length")
    chosen = max(shared)
    return {arm: dict(ids=options[arm][chosen][0], ranges=options[arm][chosen][1]) for arm in ARMS}


def prepare():
    long_plan, (tok, long_rows, model, decoder, encoder) = full.prepare()
    report_file = full.OUT / "report.json"
    report = trial.read_json(report_file)
    if report["plan"] != long_plan or len(report["results"]) != 16:
        raise ValueError("requires the actual completed same-source 4,096 comparison")
    _, (_, _, table_rows, _, _) = native.prepare(rope=True)
    tables = {row["root"]:row for row in table_rows}
    _, (_, _, _, reference, _, _, _) = mapped.prepare()
    previous = {tuple(req["encoding"]["ids"]) for req in reference}
    prompts = []
    for i, row in enumerate(long_rows):
        if row["place"] != "far":
            continue
        historical_request = full.OUT / f"k4v3_{i:02d}.json"
        archived = trial.read_json(historical_request)
        if archived["encoding"]["ids"] != row["ids"]:
            raise ValueError("the re-presented input must originate from the exact already-scored text")
        crops = crop_options(tok, row["text"], tables[row["root"]], row["side"], previous)
        raw = row["text"].encode("utf-8")
        before = native.decoded(tok, archived["native"], row["gold"], long_plan["stop"])
        prompts.append(dict(i=i, sha256=sha256(raw).hexdigest(), source_log=trial.file_sha(historical_request),
                            language=row["language"], gold=row["gold"], original=before, crops=crops))
    if len(prompts) != 4:
        raise ValueError("the exact long-source panel needs four requests")
    plan = dict(tag=TAG, source=trial.file_sha(Path(__file__)), original=trial.file_sha(report_file),
                proof=long_plan, prompts=prompts)
    return plan, (tok, long_rows, model, decoder, encoder)


def wrapper_for(path, original, prompt, arm):
    src = original.read_bytes()
    addition = f'''
    from hashlib import sha256

    if sha256(raw).hexdigest() != {prompt["sha256"]!r}:
        raise ValueError("the original long input does not match the sealed experiment")
    intervals = {prompt["crops"][arm]["ranges"]!r}
    raw = b"".join(b"\\n" if interval is None else raw[slice(*interval)] for interval in intervals)
'''
    anchor = b'    assert 0 < len(raw) <= 65536, "invalid UTF-8 request length"\n'
    path.write_bytes(native.port.replace_once(src, anchor, anchor + addition.encode("utf-8")))
    return path


def get_binary(plan):
    src = full.source_for(plan["proof"]["stop"], full.ARMS["k4v3"])
    old = trial.read_json(full.OUT / "k4v3" / "compiler.json")
    entry = old["binaries"]["64"][1]
    saved = Path(entry["path"])
    if old["source_sha256"] != sha256(src).hexdigest().upper():
        raise ValueError("the completed native engine used a different source")
    if saved.is_file() and native.base.SHA(saved) == entry["sha256"]:
        trial.publish(OUT / "compiler.json", old)
        return str(saved)
    with patch.object(native.bounded, "OUT", OUT):
        return native.bounded.build(src, caps=(64,))[64][1]


def run(plan, deadline):
    if (OUT.exists() or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or not deadline.tzinfo
            or deadline > mapped.compact.AUTHORIZATION_END
            or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 240):
        raise ValueError("requires a new bounded CPU experiment")
    checked, (tok, long_rows, model, decoder, encoder) = prepare()
    if checked != plan:
        raise ValueError("the source requests or window bounds changed")
    cpu = min(set(model["cpus"]) & os.sched_getaffinity(0))
    os.sched_setaffinity(0, {cpu})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    binary = get_binary(plan)
    source, parts = native.text_codec(OUT)
    mapped.request.render_decoder(source, decoder)
    mapped_source = OUT / "mapped_request.py"
    mapped.render_input(mapped_source, source, encoder)
    with ExitStack() as stack:
        with patch.object(mapped.request, "OUT", OUT):
            state = plan["proof"]["native"]["native"]["native"]["state_sha256"]
            image = mapped.request.pack_model(stack, state, model)
        assets = [image]
        for index, part in enumerate(parts):
            fd = native.base.memfile(f"p077-evidence-window-{index}")
            stack.callback(os.close, fd)
            native.bounded.text.store(fd, part)
            full.seal(fd)
            assets.append(fd)
        results = []
        for pair, prompt in enumerate(plan["prompts"]):
            arms = ARMS if pair % 2 == 0 else tuple(reversed(ARMS))
            source_payload = long_rows[prompt["i"]]["text"].encode("utf-8")
            for arm in arms:
                if (OUT / "STOP").exists() or (deadline - datetime.now(deadline.tzinfo)).total_seconds() < 75:
                    raise TimeoutError("the paired substitution reached its boundary")
                wrapper = wrapper_for(OUT / f"request_{pair}_{arm}.py", mapped_source, prompt, arm)
                ids = prompt["crops"][arm]["ids"]
                path = OUT / f"request_{pair}_{arm}.json"
                expect = dict(encoding=dict(ids=ids), native=dict(model_bytes=os.fstat(image).st_size,
                              kv_bytes=full.cache_size(len(ids) + native.GEN - 1, full.ARMS["k4v3"])))
                stats = native.port.request(binary, assets, source_payload, path, expect, wrapper=wrapper)
                raw = trial.read_json(path)
                decoded = native.decoded(tok, raw["native"], prompt["gold"], plan["proof"]["stop"])
                info = dict(pair=pair, arm=arm, language=prompt["language"], gold=prompt["gold"],
                            input_bytes=len(source_payload), visible_tokens=len(ids),
                            seconds=stats["seconds"], peak_rss=stats["peak_rss"], kv_bytes=stats["kv_bytes"],
                            first_token=raw["native"]["seconds"][0], **decoded)
                results.append(info)
                print(json.dumps(info, ensure_ascii=False), flush=True)
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
        parser.error("requires sealed exact windows and an authorized cutoff")
    run(plan, args.stop_by)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
