"""Run the 2,048-token CPU request with the compact output decoder."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import torch

from scripts import diag_p077_g4_output_byte_table as byte_table
from scripts import diag_p077_grounded_near_native as native


TAG = "p077_g4_output_byte_request_cpu_v1_20261121"
OUT = native.ROPE_OUT.with_name(TAG)
trial = native.trial


def prepare():
    plan, (tok, special, _, _, text) = native.prepare(rope=True)
    previous = trial.read_json(native.ROPE_OUT / "identity.json")
    old_result_path = native.ROPE_OUT / "report.json"
    old_result = trial.read_json(old_result_path)
    decoder = trial.read_json(byte_table.OUT / "report.json")
    asset = byte_table.OUT / "output_table.bin"
    if (old_result["plan"] != plan or previous["preflight"] != plan
            or decoder["reference_sha256"] != trial.file_sha(old_result_path)
            or decoder["source_sha256"] != trial.file_sha(Path(byte_table.__file__))
            or decoder["packed_sha256"] != trial.file_sha(asset)
            or decoder["packed_bytes"] != asset.stat().st_size):
        raise ValueError("the known RoPE model or verified output table changed")
    original = [trial.read_json(native.ROPE_OUT / f"text_{i}_tile_rope_2048.json") for i in range(len(text["2048"]))]
    return dict(tag=TAG, native=plan, output_sha256=decoder["packed_sha256"],
                reference_sha256=trial.file_sha(old_result_path), source_sha256=trial.file_sha(Path(__file__))), (
                tok, special, text["2048"], original, previous, asset)


def render_decoder(wrapper, asset):
    original = (
        '    tok, version, module = tokenizer(vocab, merges)\n'
        '    loaded = snapshot()\n'
        '    assert version == encoded["tokenizers"] and module == encoded["tokenizer_path"]\n'
        '    text = tok.decode(ids, skip_special_tokens=True)\n'
    )
    replacement = f'''    import importlib.util
    import mmap

    spec = importlib.util.spec_from_file_location("p077_output_decoder", {byte_table.__file__!r})
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    with open({str(asset)!r}, "rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        decoder = codec.OutputTable(raw)
        loaded = snapshot()
        text = decoder.decode(ids)
        processed = snapshot()
'''
    source = native.port.replace_once(wrapper.read_bytes(), original.encode(), replacement.encode())
    # Include the moment when output pages are still mapped in the request peak.
    source = native.port.replace_once(source, b"pid=os.getpid(), startup=startup, loaded=loaded, complete=snapshot(),",
                                      b"pid=os.getpid(), startup=startup, loaded=loaded, complete=processed,")
    wrapper.write_bytes(source)


def pack_model(stack, state_fingerprint, previous):
    base = native.base
    deploy = base.prior.DEPLOY
    fds = [base.memfile(f"p077-output-request-r{version}") for version in (4, 5, 6)]
    for fd in fds:
        stack.callback(os.close, fd)
    state = torch.load(native.training.EXPORT_OUT / "near_only.pt", weights_only=True, map_location="cpu")
    if trial.state_sha(state["model"]) != state_fingerprint:
        raise ValueError("the deployment checkpoint model changed")
    model = native.wide.TiedMLPTransformer(replace(native.wide.TMTConfig(**state["config"]), max_seq_len=1024))
    model.load_state_dict(state["model"])
    model.eval()
    model.freeze_quant()
    pack = base.prior.embedding.PACK
    packed = pack.load_payload(pack.export_payload(model, provenance={"tag": native.TAG}, head_rows=128))
    packed.quantize_embedding("int8")
    packed.eval()
    base.model_blob(packed, fds[0], base.prior.model_storage(packed)["unique_storage_bytes"], small=True)
    packed_float = native.port.extend_positions(fds[0], fds[1], packed)
    if packed_float != previous["model5"]:
        raise ValueError("the repacked R5 changed")
    packed_tile = native.tiled_rope.pack(fds[1], fds[2], packed.cfg, OUT)
    if packed_tile != previous["compact_model"]:
        raise ValueError("the repacked R6 changed")
    if fcntl.fcntl(fds[2], deploy.F_GET_SEALS) != deploy.SEALS:
        raise ValueError("the packed model is unsealed")
    return fds[2]


def run(plan, stop_by):
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or OUT.exists() or stop_by.tzinfo is None
            or not 210 < (stop_by-datetime.now(stop_by.tzinfo)).total_seconds()
            or stop_by > byte_table.AUTHORIZATION_END):
        raise ValueError("requires a new CPU-only experiment in the authorized window")
    checked, (tok, special, queries, references, previous, asset) = prepare()
    if checked != plan:
        raise ValueError("full-request inputs changed")
    cpus = sorted(set(previous["cpus"]) & os.sched_getaffinity(0))
    if not cpus:
        raise ValueError("no previously used CPU cores are available")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir()
    compiler = OUT / "compile"
    compiler.mkdir()
    stop = (special["<|im_end|>"], tok.token_to_id("<eos>"))
    source = native.tiled_rope.render(native.source_for(2048, 3, *stop))
    with patch.object(native.bounded, "OUT", compiler):
        _, binary = native.bounded.build(source, caps=(64,))[64]
    wrapper, blobs = native.text_codec(OUT)
    render_decoder(wrapper, asset)
    with ExitStack() as stack:
        model = pack_model(stack, plan["native"]["state_sha256"], previous)
        descriptors = [model]
        for i, blob in enumerate(blobs):
            fd = native.base.memfile(f"p077-output-request-tokenizer-{i}")
            stack.callback(os.close, fd)
            native.bounded.text.store(fd, blob)
            fcntl.fcntl(fd, native.base.prior.DEPLOY.F_ADD_SEALS, native.base.prior.DEPLOY.SEALS)
            descriptors.append(fd)

        def lane(cpu, first):
            os.sched_setaffinity(0, {cpu})
            rows = []
            for i in range(first, len(queries), len(cpus)):
                if (OUT / "STOP").exists() or (stop_by-datetime.now(stop_by.tzinfo)).total_seconds() < 160:
                    raise TimeoutError("request stopped before the deadline")
                path = OUT / f"request_{i}.json"
                stats = native.port.request(binary, descriptors, queries[i]["text"].encode("utf-8"),
                                            path, references[i], wrapper=wrapper)
                result = trial.read_json(path)
                if not stats["ids_equal"] or not stats["text_equal"] or result["native"]["ids"] != references[i]["native"]["ids"]:
                    raise ValueError("the output wrapper changed the request")
                rows.append(dict(index=i, cpu=cpu, **stats))
                print(json.dumps(rows[-1]), flush=True)
            return rows

        with ThreadPoolExecutor(max_workers=len(cpus)) as pool:
            futures = [pool.submit(lane, cpu, i) for i, cpu in enumerate(cpus)]
            results = [record for future in futures for record in future.result()]
    trial.publish(OUT / "report.json", dict(plan=plan, rows=sorted(results, key=lambda row: row["index"])))
    return 0


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
        parser.error("run requires a sealed full-request profile and cutoff")
    return run(plan, args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
