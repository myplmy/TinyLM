"""Measure the completed P109C on the existing compact x86 text engine."""

import argparse
from contextlib import ExitStack
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import diag_p077_compact_chat32_request as mapped
from scripts import diag_p077_lowbit_full_text as long_text
from scripts import diag_p109_g4_bounded_prefill as bounded
from scripts import eval_p109b_first_use as first
from scripts import eval_p109c_completed as evaluation
from scripts import run_p109c_scratch330 as training


base = bounded.base
ROOT = evaluation.ROOT
STOPS = (2, 4)
PREFILL = 64
SOURCES = (
    "scripts/eval_p109c_compact_cpu.py", "scripts/eval_p109c_completed.py",
    "scripts/eval_p109b_first_use.py", "scripts/diag_p109_g4_bounded_prefill.py",
    "scripts/diag_p109_g4_compact_cpu.py", "scripts/diag_p109_g4_compact_tile_cpu.py",
    "scripts/diag_p109_g4_text_exec.py", "scripts/p109_g4_text_exec.cpp",
    "scripts/p109_g4_compact_cpu.cpp", "scripts/p014e_direct_cpu.c", "scripts/p109_g4_avx2_lookup.cpp",
    "scripts/diag_p077_compact_chat32_input.py", "scripts/diag_p077_compact_chat32_request.py",
    "scripts/diag_p077_g4_output_byte_table.py", "scripts/diag_p077_g4_output_byte_request.py",
    "scripts/diag_p077_lowbit_full_text.py", "scripts/p109_compact_qwen_tokenizer.py",
)


def pins():
    return {name: evaluation.core6.digest(ROOT / name) for name in SOURCES}


def replace_once(source, previous, new):
    if source.count(previous) != 1:
        raise ValueError(f"the pinned native template anchor differs: {previous!r}")
    return source.replace(previous, new, 1)


def engine_source():
    source = (ROOT / base.CPP).read_bytes()
    tile = bounded.prior.avx.tile
    source = replace_once(source, tile.ORIGINAL, tile.CHANGED)
    # Reuse the bounded prefill loop with the FP16 cache and original
    # output_dot kernel from the current x86 source.
    for before, after in (bounded.ANCHORS[index] for index in (0, 2, 5, 6, -1)):
        source = replace_once(source, before, after)
    source = replace_once(source, b"generate <= 8", b"generate <= 128")
    source = replace_once(source, b"std::array<uint32_t,8> ids{};", b"std::array<uint32_t,128> ids{};")
    source = replace_once(source, b"std::array<double,8> times{};", b"std::array<double,128> times{};")
    source = replace_once(source, b"Memory prefilled{};", b"Memory prefilled{};\n        uint32_t produced = 0;")
    source = replace_once(source, b"if (logits_fd >= 0) write_logits(logits_fd, runtime.logits);",
        b"if (logits_fd >= 0) write_logits(logits_fd, runtime.logits);\n"
        b"            produced = i + 1;\n            if (ids[i] == 2 || ids[i] == 4) break;")
    cutoff = source.index(b'printf(",\\"ids\\":[");')
    report = source[cutoff:]
    if report.count(b"i < generate; ++i") != 2:
        raise ValueError("the two native output loops changed")
    return source[:cutoff] + report.replace(b"i < generate; ++i", b"i < produced; ++i")


def prepare(record):
    from scripts import diag_p077_g4_output_byte_table as decoder
    from scripts.p109_compact_qwen_tokenizer import CompactQwenTokenizer

    record.mkdir(exist_ok=False)
    source_pins = pins()
    tokenizer = evaluation.load_tokenizer()
    cases = first.examples(tokenizer)
    tokenizer_data = evaluation.read_json(evaluation.TOKENIZER)
    encode_file = record / "input_table.bin"
    mapped.compact.pack_chat32(tokenizer_data, encode_file)
    with CompactQwenTokenizer(encode_file) as candidate:
        input_cases = mapped.compact.verify(tokenizer, candidate, [row["prompt"] for row in cases])
    output_table = decoder.pack(tokenizer_data["model"]["vocab"],
                                {row["id"] for row in tokenizer_data["added_tokens"]})
    decode_file = record / "output_table.bin"
    with decode_file.open("xb") as stream:
        stream.write(output_table)
    output_cases = decoder.verify(tokenizer, output_table, [row["input_ids"] for row in cases])

    default_wrapper = long_text.wrapper(record / "default_wrapper.py", first.INPUT, first.ANSWER)
    mapped.request.render_decoder(default_wrapper, decode_file)
    wrapper = record / "text_request.py"
    mapped.render_input(wrapper, default_wrapper, encode_file)
    with patch.object(bounded, "OUT", record):
        numeric, binary = (Path(path) for path in bounded.build(engine_source(), caps=(PREFILL,))[PREFILL])
    if pins() != source_pins:
        raise ValueError("source changed during offline preparation")
    artifacts = [wrapper, encode_file, decode_file, numeric, binary]
    profile = dict(schema="P109C_X86_COMPACT_TEXT_V1", source_sha256=source_pins,
                   artifacts={str(path): evaluation.core6.digest(path) for path in artifacts},
                   first_use_cases=len(cases), verified_encoder_cases=input_cases, verified_decoder_cases=output_cases,
                   prefill_tile=PREFILL, numeric=str(numeric), binary=str(binary), wrapper=str(wrapper),
                   tokenizer_sha256=evaluation.TOKENIZER_SHA, stop_ids=list(STOPS))
    training.publish(record / "profile.json", profile)
    print("P109C_X86_PREPARED", input_cases, output_cases, evaluation.core6.digest(record / "profile.json"), flush=True)
    return profile


def export_blob(model, record, fd):
    embedding = base.prior.embedding
    payload = embedding.PACK.export_payload(model, provenance={"tag": evaluation.MODEL_NAME},
                                            head_rows=embedding.HEAD_ROWS)
    packed = embedding.PACK.load_payload(payload)
    del payload
    packed.quantize_embedding("int8")
    packed.cfg.emb_chunk = embedding.HEAD_ROWS
    packed.cfg.kv_dtype = "fp16"
    bytes_in_tensors = base.prior.model_storage(packed)["unique_storage_bytes"]
    proof = base.model_blob(packed, fd, bytes_in_tensors)
    path = record / "p109c_g4_compact.bin"
    with os.fdopen(os.dup(fd), "rb") as source, path.open("xb") as target:
        source.seek(0)
        shutil.copyfileobj(source, target)
    if evaluation.core6.digest(path) != proof["artifact_sha256"]:
        raise ValueError("the persisted model bytes differ from the sealed execution artifact")
    return packed, proof


def numeric_check(packed, model_fd, driver, ids):
    import numpy as np
    import struct
    import torch

    logits = base.memfile("p109c_deploy_check")
    try:
        data = struct.pack(f"<{len(ids)+2}I", len(ids), 1, *ids)
        native = subprocess.run([driver, str(model_fd), str(logits)], input=data, pass_fds=(model_fd, logits),
                                capture_output=True, timeout=120, check=True)
        with os.fdopen(os.dup(logits), "rb") as stream:
            stream.seek(0)
            scores = np.frombuffer(stream.read(), dtype="<f4")
        with base.prior.DEPLOY.native_unpack(packed):
            full, _ = packed(torch.tensor([ids]), use_cache=True, logits_last_only=True)
        expected = full[0, 0].detach().numpy()
        if scores.shape != expected.shape or not np.isfinite(scores).all():
            raise ValueError("native trace did not return all finite vocabulary logits")
        return dict(max_abs_difference=float(np.max(np.abs(scores-expected))),
                    native_id=json.loads(native.stdout)["ids"][0], packed_reference_id=int(expected.argmax()))
    finally:
        os.close(logits)


def text_request(profile, ids, prompt, assets, cutoff):
    with ExitStack() as stack:
        request = tuple(base.memfile(f"p109c_cpu_request_{n}") for n in range(3))
        for fd in request:
            stack.callback(os.close, fd)
        descriptors = assets + request
        cmd = [sys.executable, "-I", "-S", "-B", "-X", "utf8", profile["wrapper"],
               "encode", profile["binary"], *map(str, descriptors)]
        started = time.perf_counter()
        process = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, pass_fds=descriptors,
                                 timeout=min(300, max(1, cutoff-time.time())), check=True)
        result = json.loads(process.stdout)
    if result["encoding"]["ids"] != ids or not (
            result["encoding"]["pid"] == result["native_pid"] == result["decoding"]["pid"]):
        raise ValueError("actual prompt IDs or single-PID request contract differs")
    native = result["native"]
    if len(native["ids"]) != len(native["seconds"]) or not 1 <= len(native["ids"]) <= first.ANSWER:
        raise ValueError("the native timing/token generation receipt differs")
    peak_text = lambda kind: max(value for when in ("startup", "loaded", "complete")
                                 for value in result[kind][when].values())
    result["peaks"] = dict(encoder=peak_text("encoding"), decoder=peak_text("decoding"),
        native=max(native[phase][key] for phase in ("before", "loaded", "prefilled", "complete") for key in ("rss", "vm_hwm")))
    result["wall_seconds"] = time.perf_counter() - started
    return result


def model_requests(profile, checkpoint, checksum, record, cutoff):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from tinylm.infer.generate import sample

    if (profile["source_sha256"] != pins()
            or any(evaluation.core6.digest(Path(path)) != digest for path, digest in profile["artifacts"].items())):
        raise ValueError("a sealed CPU engine, tokenizer table or source changed")
    core = min(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {core})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    tokenizer = evaluation.load_tokenizer()
    cases = first.examples(tokenizer)
    model = evaluation.load_model(checkpoint, training.STEPS, "cpu")
    rows = []
    with ExitStack() as stack, torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
        model_fd, vocab, merges = tuple(base.memfile(f"p109c_deploy_{n}") for n in range(3))
        for fd in (model_fd, vocab, merges):
            stack.callback(os.close, fd)
        for fd in (vocab, merges):
            fcntl.fcntl(fd, base.prior.DEPLOY.F_ADD_SEALS, base.prior.DEPLOY.SEALS)
        packed, artifact = export_blob(model, record, model_fd)
        numeric = numeric_check(packed, model_fd, profile["numeric"], cases[0]["input_ids"])
        training.publish(record / "numeric.json", numeric)
        del packed
        for index, case in enumerate(cases):
            if time.time() >= cutoff:
                raise TimeoutError("the authorized CPU deployment window elapsed")
            capture = first.DecodeSuffix(tokenizer, case["input_ids"])
            began = time.perf_counter()
            content, meta = sample(model, model.cfg, capture, case["prompt"], max_new=first.ANSWER,
                                   temperature=0., top_k=1, device="cpu", eos_id=STOPS[0],
                                   stop_token_sequences=[[STOPS[1]]], logits_last_only=True, return_metadata=True)
            dense_elapsed = time.perf_counter() - began
            raw = text_request(profile, case["input_ids"], case["prompt"], (model_fd, vocab, merges), cutoff)
            engine = raw["native"]
            if (engine["model_bytes"] != artifact["artifact_bytes"]
                    or engine["kv_bytes"] != (len(case["input_ids"]) + first.ANSWER - 1) * 14 * 2 * 3 * 64 * 2):
                raise ValueError("actual native model or FP16 KV bytes differ")
            answer = raw["decoding"]["text"]
            if answer != tokenizer.decode(engine["ids"], skip_special_tokens=True):
                raise ValueError("actual deployed decoder differs from the source tokenizer")
            row = dict(case=case["case"], language=case["language"], expected=case["answer"],
                       input_tokens=len(case["input_ids"]), dense_answer=content, packed_answer=answer,
                       dense_exact=first.strict(content)==first.strict(case["answer"]),
                       packed_exact=first.strict(answer)==first.strict(case["answer"]),
                       token_ids_equal=capture.ids==engine["ids"], dense_ids=capture.ids, packed_ids=engine["ids"],
                       dense_seconds=dense_elapsed, packed_seconds=raw["wall_seconds"],
                       packed_first_token_seconds=engine["seconds"][0], peak_rss_bytes=max(raw["peaks"].values()),
                       packed_tokens_per_second=(len(engine["ids"])-1)/sum(engine["seconds"][1:]) if len(engine["ids"])>1 else None,
                       dense_finish=meta["finish_reason"], packed_stopped=engine["ids"][-1] in STOPS,
                       pack_model_bytes=engine["model_bytes"], kv_bytes=engine["kv_bytes"], scratch_bytes=engine["scratch_bytes"])
            training.publish(record / f"native_request_{index:02d}.json", raw)
            rows.append(row)
            print("P109C_X86_REQUEST", index, row["language"], row["packed_exact"], row["peak_rss_bytes"], flush=True)
    if evaluation.core6.digest(checkpoint) != checksum or profile["source_sha256"] != pins():
        raise ValueError("the exact completed model or deployment source changed")
    return dict(checkpoint_sha256=checksum, checkpoint_bytes=checkpoint.stat().st_size,
                cpu=core, artifact=artifact, numeric=numeric, rows=rows, cuda_initialized=torch.cuda.is_initialized())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--training-record", type=Path)
    parser.add_argument("--training-manifest-sha256")
    parser.add_argument("--wait-pid", type=int)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("requires CPU-only mode")
    record = args.record.absolute()
    if args.phase == "prepare":
        prepare(record)
        return
    if not all((args.profile, args.profile_sha256, args.training_record,
                args.training_manifest_sha256, args.stop_by)) or args.stop_by.tzinfo is None:
        parser.error("requires a sealed preparation, training lineage and authorized deadline")
    profile = json.loads(training.manifest_bytes(args.profile.absolute(), args.profile_sha256))
    cutoff = args.stop_by.timestamp()
    if args.wait_pid is not None:
        evaluation.wait_for_training(args.training_record.absolute(), args.wait_pid, cutoff)
    if time.time() >= cutoff:
        raise TimeoutError("no authorized time remains for CPU deployment")
    checkpoint, checksum = evaluation.completed_checkpoint(args.training_record.absolute(), args.training_manifest_sha256)
    record.mkdir(exist_ok=False)
    result = model_requests(profile, checkpoint, checksum, record, cutoff)
    training.publish(record / "report.json", result)
    print("P109C_X86_COMPLETE", len(result["rows"]), flush=True)


if __name__ == "__main__":
    main()
