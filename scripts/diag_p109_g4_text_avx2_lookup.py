"""Compare the scalar and exact AVX2 row expansion inside the same text request."""

from contextlib import ExitStack
import ctypes
from datetime import datetime, timedelta
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
import tempfile
import time

import numpy as np
import torch

from scripts import diag_p109_g4_compact_tile_cpu as tile
from scripts import diag_p109_g4_text_exec as text_exec
from scripts import diag_p109_g4_tokenizer_budget as bytelevel


base = tile.dynamic
ROOT = base.ROOT
TAG = "p109_g4_text_avx2_lookup_v1_20261119"
OUT = base.OUT.with_name(TAG)
LOOKUP = "scripts/p109_g4_avx2_lookup.cpp"
SCRIPT = "scripts/diag_p109_g4_text_avx2_lookup.py"
ORDER = ("scalar", "avx2", "avx2", "scalar")


def build(core):
    folder = Path(tempfile.mkdtemp(prefix="p109_g4_avx2_lookup_", dir="/tmp"))
    scalar, fast, engine = (folder / name for name in ("scalar.o", "avx2.o", "compact.o"))
    binary, audit = folder / "g4_text_fast", folder / "lookup_audit.so"
    flags = ["-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off",
             "-Wall", "-Wextra", "-Werror"]
    commands = [
        ["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Wextra", "-Werror", "-fPIC",
         "-Dp014e_cpu_lookup=p014e_scalar_lookup", "-c", base.C, "-o", str(scalar)],
        ["/usr/bin/g++", *flags, "-fPIC", "-c", LOOKUP, "-o", str(fast)],
        ["/usr/bin/g++", *flags, "-Dmain=run_compact_g4", "-x", "c++", "-", "-c", "-o", str(engine)],
        ["/usr/bin/g++", *flags, text_exec.WRAPPER, str(engine), str(fast), str(scalar),
         "-static", "-o", str(binary)],
        ["/usr/bin/g++", "-shared", str(fast), str(scalar), "-o", str(audit)],
    ]
    for i, cmd in enumerate(commands):
        subprocess.run(cmd, input=core if i == 2 else None, cwd=ROOT, timeout=90, check=True)
    assert "INTERP" not in subprocess.check_output(["/usr/bin/readelf", "-l", str(binary)], text=True)
    base.WRITE(OUT / "compiler.json", dict(
        commands=commands, binary=str(binary), sha256=base.SHA(binary),
        audit=str(audit), audit_sha256=base.SHA(audit),
    ))
    return binary, audit


def compare_rows(model, library):
    runtime = ctypes.CDLL(str(library))
    original, fast = runtime.p014e_scalar_lookup, runtime.p014e_cpu_lookup
    for fn in (original, fast):
        fn.argtypes = [ctypes.c_void_p] * 4 + [ctypes.c_int64] * 4
        fn.restype = ctypes.c_int

    def check(codes, scales, ids, n, k, g, code=0):
        # Both ends are checked in addition to all restored float bits.
        results = [np.full(8 + k * len(ids), 0xA5A5A5A5, dtype=np.uint32) for _ in range(2)]
        for out, fn in zip(results, (original, fast), strict=True):
            status = fn(codes, scales, ids.ctypes.data, out.ctypes.data + 16, len(ids), n, k, g)
            assert status == code
            assert (out[:4] == 0xA5A5A5A5).all() and (out[-4:] == 0xA5A5A5A5).all()
        assert np.array_equal(*results)

    # Both accelerated widths, serial fallback and invalid partial-output behavior.
    controls = 0
    for k in (128, 768, 2048):
        n, groups = 2, k // 128
        raw = (np.arange(n * groups * 26, dtype=np.int64) % 243).astype(np.uint8)
        scales = np.tile(np.array([0.0, -0.0, 0.003125, 3.25], dtype=np.float32), n * groups)[:n * groups].copy()
        for ids in ([0], [1], [1, 0]):
            check(raw.ctypes.data, scales.ctypes.data, np.array(ids, dtype=np.int64), n, k, 128)
            controls += 1
        for bad in (1, groups * 26 - 1):
            corrupt = raw.copy()
            corrupt[bad] = 243
            check(corrupt.ctypes.data, scales.ctypes.data, np.array([0], dtype=np.int64), n, k, 128, code=4)
            controls += 1

    packed = base.prior.embedding.PACK.PackedGroupLinear
    modules = [m for m in model.modules() if isinstance(m, packed)]
    rows, weights = 0, 0
    assert len(modules) == 69
    for module in modules:
        assert module.group == 128 and module.in_f in (768, 2048)
        signals = [np.empty(module.in_f, dtype=np.float32) for _ in range(2)]
        indexes = ctypes.c_int64()
        values = (module.packed_codes.data_ptr(), module.group_scales.data_ptr(), ctypes.byref(indexes))
        for row in range(module.out_f):
            indexes.value = row
            for dest, fn in zip(signals, (original, fast), strict=True):
                assert fn(*values, dest.ctypes.data, 1, module.out_f, module.in_f, 128) == 0
            assert np.array_equal(signals[0].view(np.uint32), signals[1].view(np.uint32))
        rows += module.out_f
        weights += module.out_f * module.in_f
    return dict(physical_matrices=len(modules), rows=rows, float_values=weights, controls=controls)


def request(binary, assets, text, baseline, name, language, index):
    with ExitStack() as stack:
        intermediate = tuple(base.memfile(f"g4_avx2_stage_{index}_{n}") for n in range(3))
        for fd in intermediate:
            stack.callback(os.close, fd)
        fds = (*assets, *intermediate)
        args = [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(ROOT / text_exec.SCRIPT),
                "encode", str(binary), *map(str, fds)]
        start = time.perf_counter()
        proc = subprocess.run(args, input=text, pass_fds=fds, capture_output=True, timeout=300)
        elapsed = time.perf_counter() - start
        if proc.returncode:
            print(proc.stderr.decode("utf-8", "replace"), file=sys.stderr, flush=True)
            proc.check_returncode()
        row = json.loads(proc.stdout)
    row.update(arm=name, language=language, index=index, wall_seconds=elapsed)
    base.WRITE(OUT / f"raw_case_{index}.json", row)
    assert row["encoding"]["pid"] == row["native_pid"] == row["decoding"]["pid"]
    assert row["encoding"]["ids"] == baseline["encoding"]["ids"]
    assert row["native"]["ids"] == baseline["native"]["ids"]
    assert row["decoding"]["text"] == baseline["decoding"]["text"]
    core = row["native"]
    for key in ("model_bytes", "kv_bytes", "scratch_bytes"):
        assert core[key] == baseline["native"][key]
    peak = max(
        max(core[stage][key] for stage in ("before", "loaded", "prefilled", "complete")
            for key in ("rss", "vm_hwm")),
        *(value for branch in ("encoding", "decoding") for stage in ("startup", "loaded", "complete")
          for value in row[branch][stage].values()),
    )
    summary = dict(index=index, language=language, arm=name, peak_bytes=peak,
                   within_si=peak <= 40_000_000, within_mib=peak <= 40 * 2**20,
                   first_seconds=core["seconds"][0], decode_seconds=sum(core["seconds"][1:]),
                   wall_seconds=elapsed, exact=True)
    print("P109_AVX2_REQUEST", summary, flush=True)
    return summary


@torch.inference_mode()
def run():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert datetime.now(base.prior.ORIGIN.CUTOFF.tzinfo) + timedelta(seconds=1200) < base.prior.ORIGIN.CUTOFF
    prof = base.READ(text_exec.OUT / "profile.json")
    old = base.READ(text_exec.OUT / "report.json")
    assert old["profile_sha256"] == base.SHA(text_exec.OUT / "profile.json")
    assert all(base.SHA(ROOT / p) == value for p, value in prof["sources"].items())
    pins = base.pins()
    assert pins == prof["pins"]
    os.sched_setaffinity(0, {prof["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    before = base.READ(text_exec.OUT / "compiler.json")
    baseline = Path(before["binary"])
    assert baseline.is_relative_to(Path("/tmp")) and baseline.is_file() and not baseline.is_symlink()
    assert base.SHA(baseline) == before["sha256"]
    codec = base.READ(bytelevel.OUT / "report.json")
    codec_proof = base.READ(bytelevel.OUT / "profile.json")
    assert base.SHA(bytelevel.OUT / "profile.json") == prof["tokenizer_profile"]
    assert base.SHA(bytelevel.OUT / "report.json") == prof["tokenizer_reference"]
    source_bytes = bytelevel.TOK.read_bytes()
    assert sha256(source_bytes).hexdigest().upper() == codec_proof["source_sha256"]
    data = bytelevel.wire(json.loads(source_bytes))
    assert [sha256(d).hexdigest().upper() for d in data] == [v["sha256"] for v in codec_proof["files"]["split_model"]]
    texts = codec["runs"]["split_model"][0]["outputs"]
    refs = {r["case"]: r for r in old["runs"]}
    core = (ROOT / base.CPP).read_bytes().replace(tile.ORIGINAL, tile.CHANGED, 1)
    assert sha256(core).hexdigest().upper() == prof["core_sha256"]
    OUT.mkdir(exist_ok=False)
    sources = {path: base.SHA(ROOT / path) for path in (LOOKUP, SCRIPT, *prof["sources"])}
    base.WRITE(OUT / "profile.json", dict(
        tag=TAG, sources=sources, prior_report=base.SHA(text_exec.OUT / "report.json"),
        baseline_sha256=before["sha256"], core_sha256=prof["core_sha256"], cpu=prof["cpu"], order=list(ORDER),
    ))
    fast, audit = build(core)
    runs = []
    with ExitStack() as stack:
        def fd(name):
            item = base.memfile(name)
            stack.callback(os.close, item)
            return item

        model_fd = fd("g4_lookup_model")
        model = base.prior.load_candidate(pins["candidate"])
        replay = compare_rows(model, audit)
        base.WRITE(OUT / "replay.json", replay)
        print("P109_AVX2_REPLAY", replay, flush=True)
        artifact = base.model_blob(model, model_fd, pins["candidate"]["model_tensor_bytes"])
        del model
        assert artifact == old["source"]
        tokenizer = [fd(name) for name in ("g4_lookup_vocab", "g4_lookup_merges")]
        for item, payload in zip(tokenizer, data, strict=True):
            text_exec.store(item, payload)
            fcntl.fcntl(item, base.prior.DEPLOY.F_ADD_SEALS, base.prior.DEPLOY.SEALS)
            assert fcntl.fcntl(item, base.prior.DEPLOY.F_GET_SEALS) == base.prior.DEPLOY.SEALS
        bins = {"scalar": baseline, "avx2": fast}
        for language in ("english", "korean"):
            for name in ORDER:
                runs.append(request(bins[name], (model_fd, *tokenizer), texts[language]["decoded"].encode("utf-8"),
                                    refs[language], name, language, len(runs)))
    assert not torch.cuda.is_initialized() and base.pins() == pins
    assert all(base.SHA(ROOT / path) == digest for path, digest in sources.items())
    pair = {
        lang: {
            arm: {metric: median(x[metric] for x in runs if x["language"] == lang and x["arm"] == arm)
                  for metric in ("first_seconds", "decode_seconds", "wall_seconds")}
            for arm in ORDER[:2]
        } for lang in ("english", "korean")
    }
    base.WRITE(OUT / "report.json", dict(
        runs=runs, medians=pair, replay=replay, profile_sha256=base.SHA(OUT / "profile.json"),
        artifact=artifact, cuda_initialized=False, checkpoint_writes=0,
    ))


if __name__ == "__main__":
    run()
