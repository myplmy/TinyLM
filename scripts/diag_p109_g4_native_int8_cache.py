"""Compare the native grouped INT8 and FP16 G4 cache with sealed assets."""

from contextlib import ExitStack
from datetime import datetime, timedelta
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
import struct
import subprocess
import sys
import tempfile
from time import perf_counter

import numpy as np
import torch

from scripts import diag_p109_g4_text_avx2_lookup as avx


base, text, token = avx.base, avx.text_exec, avx.bytelevel
ROOT = avx.ROOT
TAG = "p109_g4_native_int8_cache_v1_20261119"
OUT = base.OUT.with_name(TAG)
CACHE = "scripts/p109_g4_grouped_int8_cache.hpp"
LIMIT = 240
GROUP, SLOTS, KV, HEAD = 32, 14, 192, 64
ANCHORS = (
    (b"struct Runtime {", b'#include "p109_g4_grouped_int8_cache.hpp"\n\nstruct Runtime {'),
    (b"value(capacity * Kv), kept_key(Slots * capacity * Kv),\n          kept_value(Slots * capacity * Kv) {}",
     b"value(capacity * Kv), cache(capacity) {}"),
    (b"return (kept_key.capacity() + kept_value.capacity()) * sizeof(uint16_t);", b"return cache.bytes();"),
    (b"        auto* ks = kept_key.data() + slot * capacity * Kv;\n"
     b"        auto* vs = kept_value.data() + slot * capacity * Kv;\n"
     b"        load_half(key.data(), ks, past * Kv);\n"
     b"        load_half(value.data(), vs, past * Kv);",
     b"        cache.restore(slot, past, key.data(), value.data());"),
    (b"        store_half(ks + past * Kv, key.data() + past * Kv, count * Kv);\n"
     b"        store_half(vs + past * Kv, value.data() + past * Kv, count * Kv);",
     b"        cache.append(slot, past, count, key.data(), value.data());"),
    (b"std::vector<uint16_t> kept_key, kept_value;", b"GroupedInt8Cache cache;"),
)


def render(reference):
    candidate = reference
    for before, after in ANCHORS:
        assert candidate.count(before) == 1
        candidate = candidate.replace(before, after, 1)
    return candidate


def build(reference, candidate):
    folder = Path(tempfile.mkdtemp(prefix="p109_native_int8_", dir="/tmp"))
    scalar, fast = [str(folder / name) for name in ("scalar.o", "avx2.o")]
    flags = ["-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off",
             "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "scripts")]
    commands = []

    def run(cmd, source=None):
        subprocess.run(cmd, input=source, cwd=ROOT, timeout=80, check=True)
        commands.append(cmd)

    run(["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
         "-Dp014e_cpu_lookup=p014e_scalar_lookup", "-c", base.C, "-o", scalar])
    run(["/usr/bin/g++", *flags, "-c", avx.LOOKUP, "-o", fast])
    engines = {}
    for name, source in (("fp16", reference), ("int8", candidate)):
        exe = folder / name
        run(["/usr/bin/g++", *flags, "-x", "c++", "-", "-x", "none", fast, scalar,
             "-static", "-o", str(exe)], source)
        engines[name] = exe
    obj, full = folder / "int8_core.o", folder / "int8_text"
    run(["/usr/bin/g++", *flags, "-Dmain=run_compact_g4", "-x", "c++", "-", "-c", "-o", str(obj)], candidate)
    run(["/usr/bin/g++", *flags, text.WRAPPER, str(obj), fast, scalar, "-static", "-o", str(full)])
    engines["full"] = full
    assert all("INTERP" not in subprocess.check_output(["/usr/bin/readelf", "-l", str(binary)], text=True)
               for binary in engines.values())
    base.WRITE(OUT / "compiler.json", dict(commands=commands, binaries={
        name: dict(path=str(p), sha256=base.SHA(p)) for name, p in engines.items()},
        rendered_sha256={"fp16": sha256(reference).hexdigest().upper(),
                         "int8": sha256(candidate).hexdigest().upper()}))
    return engines


def int8_capacity(context):
    packed = context // GROUP * GROUP
    residual_capacity = min(context, GROUP - 1)
    return SLOTS * (2 * packed * KV + 2 * (packed // GROUP) * KV
                    + 2 * packed * (KV // HEAD) + 4 * residual_capacity * KV)


def numeric(binary, model_fd, ids):
    scores_fd = base.memfile("g4_native_int8_scores")
    try:
        request = struct.pack(f"<{len(ids) + 2}I", len(ids), text.GEN, *ids)
        process = subprocess.run([str(binary), str(model_fd), str(scores_fd)], input=request,
                                 pass_fds=(model_fd, scores_fd), capture_output=True, timeout=180)
        if process.returncode:
            print(process.stderr.decode("utf-8", "replace"), file=sys.stderr, flush=True)
            process.check_returncode()
        data = json.loads(process.stdout)
        os.lseek(scores_fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(scores_fd), "rb") as stream:
            scores = np.frombuffer(stream.read(), dtype="<f4").reshape(text.GEN, 32768)
    finally:
        os.close(scores_fd)
    assert np.isfinite(scores).all()
    return data, scores


def compare(engines, model_fd, name, ids, reference_ids=None):
    reference, left = numeric(engines["fp16"], model_fd, ids)
    candidate, right = numeric(engines["int8"], model_fd, ids)
    context = len(ids) + text.GEN - 1
    assert reference_ids is None or reference["ids"] == reference_ids
    assert candidate["model_bytes"] == reference["model_bytes"]
    assert reference["kv_bytes"] == 4 * SLOTS * context * KV
    assert candidate["kv_bytes"] == int8_capacity(context)
    absolute, fixed_history = [], True
    for ref_id, cur_id, ref_scores, cur_scores in zip(reference["ids"], candidate["ids"], left, right, strict=True):
        if fixed_history:
            absolute.append(float(np.abs(ref_scores - cur_scores).max()))
        fixed_history = fixed_history and ref_id == cur_id
    row = dict(name=name, context=context, argmax_equal=fixed_history,
        max_abs_logits_same_history=max(absolute), per_step_abs_logits=absolute,
        identical_prefill=bool(np.array_equal(left[0], right[0])), reference=reference, candidate=candidate)
    print("P109_NATIVE_INT8_NUMERIC", name, candidate["kv_bytes"], row["identical_prefill"],
          fixed_history, row["max_abs_logits_same_history"], flush=True)
    return row


def peak(row):
    return max(
        *(row["native"][stage][key] for stage in ("before", "loaded", "prefilled", "complete")
          for key in ("rss", "vm_hwm")),
        *(value for branch in ("encoding", "decoding") for stage in ("startup", "loaded", "complete")
          for value in row[branch][stage].values()),
    )


def text_request(binary, assets, payload, reference, name, repeat):
    with ExitStack() as stack:
        extra = tuple(base.memfile(f"g4_grouped_cache_{i}") for i in range(3))
        for item in extra:
            stack.callback(os.close, item)
        fds = (*assets, *extra)
        args = [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(ROOT / text.SCRIPT),
                "encode", str(binary), *map(str, fds)]
        start = perf_counter()
        process = subprocess.run(args, input=payload, pass_fds=fds, capture_output=True, timeout=180)
        seconds = perf_counter() - start
        if process.returncode:
            print(process.stderr.decode("utf-8", "replace"), file=sys.stderr, flush=True)
            process.check_returncode()
        row = json.loads(process.stdout)
    base.WRITE(OUT / f"{name}_text_{repeat}.json", row)
    assert row["encoding"]["pid"] == row["native_pid"] == row["decoding"]["pid"]
    assert row["encoding"]["ids"] == reference["encoding"]["ids"]
    assert row["native"]["model_bytes"] == reference["native"]["model_bytes"]
    exact = row["native"]["ids"] == reference["native"]["ids"] and row["decoding"]["text"] == reference["decoding"]["text"]
    result = dict(language=name, repeat=repeat, outputs_equal=exact, peak_rss=peak(row), seconds=seconds,
                  first_seconds=row["native"]["seconds"][0], decode_seconds=sum(row["native"]["seconds"][1:]),
                  kv_bytes=row["native"]["kv_bytes"], scratch_bytes=row["native"]["scratch_bytes"])
    print("P109_NATIVE_INT8_TEXT", result, flush=True)
    return result


@torch.inference_mode()
def run():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    cutoff = base.prior.ORIGIN.CUTOFF
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=LIMIT + 20) < cutoff
    profile_path, report_path = text.OUT / "profile.json", text.OUT / "report.json"
    profile, report = base.READ(profile_path), base.READ(report_path)
    assert report["profile_sha256"] == base.SHA(profile_path)
    assert all(base.SHA(ROOT / p) == digest for p, digest in profile["sources"].items())
    pins = base.pins()
    assert pins == profile["pins"]
    codec_profile = base.READ(token.OUT / "profile.json")
    codec_report = base.READ(token.OUT / "report.json")
    assert base.SHA(token.OUT / "report.json") == profile["tokenizer_reference"]
    source_vocab = token.TOK.read_bytes()
    assert sha256(source_vocab).hexdigest().upper() == codec_profile["source_sha256"]
    codec_bytes = token.wire(json.loads(source_vocab))
    assert [sha256(blob).hexdigest().upper() for blob in codec_bytes] == [
        row["sha256"] for row in codec_profile["files"]["split_model"]]
    reference = (ROOT / base.CPP).read_bytes().replace(avx.tile.ORIGINAL, avx.tile.CHANGED, 1)
    assert sha256(reference).hexdigest().upper() == profile["core_sha256"]
    sources = {str(Path(__file__).relative_to(ROOT)): base.SHA(Path(__file__)), CACHE: base.SHA(ROOT / CACHE),
               avx.LOOKUP: base.SHA(ROOT / avx.LOOKUP), **profile["sources"]}
    os.sched_setaffinity(0, {profile["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir(exist_ok=False)
    base.WRITE(OUT / "profile.json", dict(tag=TAG, sources=sources, cpu=profile["cpu"],
        reference_profile=base.SHA(profile_path), reference_report=base.SHA(report_path),
        avx_report=base.SHA(avx.OUT / "report.json"), group_tokens=GROUP, full_input_limit=LIMIT))
    engines = build(reference, render(reference))
    references = {row["case"]:row for row in report["runs"]}
    texts = codec_report["runs"]["split_model"][0]["outputs"]
    prior_rows = base.READ(avx.OUT / "report.json")["runs"]
    with ExitStack() as stack:
        def fd(label):
            opened = base.memfile(label)
            stack.callback(os.close, opened)
            return opened

        model_fd = fd("g4_grouped_cache_model")
        model = base.prior.load_candidate(pins["candidate"])
        artifact = base.model_blob(model, model_fd, pins["candidate"]["model_tensor_bytes"])
        del model
        assert artifact == report["source"]
        tokenizer = [fd("g4_grouped_cache_vocab"), fd("g4_grouped_cache_merges")]
        for item, payload in zip(tokenizer, codec_bytes, strict=True):
            text.store(item, payload)
            seals = base.prior.DEPLOY.SEALS
            fcntl.fcntl(item, base.prior.DEPLOY.F_ADD_SEALS, seals)
            assert fcntl.fcntl(item, base.prior.DEPLOY.F_GET_SEALS) == seals
        ids = references["english"]["encoding"]["ids"]
        numeric_rows = [compare(engines, model_fd, f"boundary_{n}", ids[:n]) for n in (31, 63)]
        full = []
        for lang in ("english", "korean"):
            ref = references[lang]
            numeric_rows.append(compare(engines, model_fd, lang, ref["encoding"]["ids"], ref["native"]["ids"]))
            payload = texts[lang]["decoded"].encode("utf-8")
            full.extend(text_request(engines["full"], (model_fd, *tokenizer), payload, ref, lang, repeat)
                        for repeat in (1, 2))
    assert not torch.cuda.is_initialized() and base.pins() == pins
    assert all(base.SHA(ROOT / p) == digest for p, digest in sources.items())
    comparisons = {}
    for lang in ("english", "korean"):
        old = [row for row in prior_rows if row["language"] == lang and row["arm"] == "avx2"]
        new = [row for row in full if row["language"] == lang]
        assert len(old) == len(new) == 2
        comparisons[lang] = dict(previous_wall_seconds=median(v["wall_seconds"] for v in old),
            current_wall_seconds=median(v["seconds"] for v in new),
            previous_byte_peak=max(v["peak_bytes"] for v in old), current_byte_peak=max(v["peak_rss"] for v in new))
    result = dict(numeric=numeric_rows, full=full, comparisons=comparisons, checkpoint_writes=0,
                  profile_sha256=base.SHA(OUT / "profile.json"))
    base.WRITE(OUT / "report.json", result)
    assert all(row["identical_prefill"] for row in numeric_rows)


if __name__ == "__main__":
    run()
