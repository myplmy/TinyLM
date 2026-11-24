"""Check native packed KV bytes and run new precision arms on the saved R5 cohort."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from hashlib import sha256
import json
import os
from pathlib import Path
import struct
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np

from scripts import diag_p077_kv_six_bits as synthetic


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EVIDENCE = ROOT / "test_result/evidence"
OLD = EVIDENCE / "p077_r5_long_choice_cpu_v1_20261121"
RESULT = EVIDENCE / "p077_r5_lowbit_native_cpu_v1_20261121"
PROOF = EVIDENCE / "p077_lowbit_codec_native_cpu_v1_20261121"
HEADER = "p109_g4_grouped_int8_cache.hpp"
TEST = "test_p077_lowbit_native.cpp"
ARMS = {"k3v3": (1920, 3, 3, 5_408_256), "k2v4": (1920, 2, 4, 5_730_816), "k4v2": (1920, 4, 2, 5_569_536)}


def read(path):
    return json.loads(path.read_bytes())


def publish(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write(chr(10))


def seal(paths):
    return {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in paths}


def compile_probe(source, exe, flags=()):
    subprocess.run(["/usr/bin/g++", "-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off",
                    "-Wall", "-Wextra", "-Werror", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
                    "-I", str(SCRIPTS), *flags, source, "-o", exe], check=True, cwd=ROOT, timeout=80)


def native_codec():
    if PROOF.exists():
        raise FileExistsError(PROOF)
    with TemporaryDirectory(prefix="p077_lowbit_native_", dir="/tmp") as name:
        work = Path(name)
        with ZipFile(OLD/"sources_at_execution.zip") as archive:
            archived_header = sha256(archive.read(f"scripts/{HEADER}")).hexdigest()
            for file in (HEADER, "p109_g4_compact_cpu.cpp"):
                (work/file).write_bytes(archive.read(f"scripts/{file}"))
        (work/TEST).write_bytes((SCRIPTS/TEST).read_bytes())
        before, after = work/"before", work/"after"
        compile_probe(work/TEST, before, ("-DP077_ARCHIVE_REFERENCE",))
        compile_probe(SCRIPTS/TEST, after)
        rng = np.random.default_rng(20261121)
        shape = (2048, 3, 64)
        key = rng.normal(size=shape).astype(np.float16)
        value = rng.normal(size=shape).astype(np.float16)
        key[:32, 0, 0] = np.float16(0.125)
        value[1919, -1].fill(np.float16(-0.5))
        key[1920:1952, -1, -1] = np.float16(2**-14)
        payload = key.astype("<f4").tobytes() + value.astype("<f4").tobytes()

        def run(binary, prefix, k, v):
            return subprocess.check_output([binary, str(k), str(v), str(prefix)], input=payload, timeout=30)

        archive = run(before, 1024, 4, 4)
        current = run(after, 1024, 4, 4)
        if archive != current:
            raise ValueError("unchanged INT4 route differs from its archived native output")
        results = {"archive_int4": dict(bytes=struct.unpack_from("<Q", archive)[0], bit_exact=True,
                                        output_sha256=sha256(archive).hexdigest())}
        for arm, (prefix, k, v, expected_bytes) in ARMS.items():
            received = run(after, prefix, k, v)
            nbytes = struct.unpack_from("<Q", received)[0]
            actual = np.frombuffer(received[8:], dtype="<f4").reshape(2, 2, *shape)
            expected = np.array([synthetic.mixed(sign*key, sign*value, prefix, k, v, k == 2, v == 2)[:2]
                                 for sign in (1, -1)], dtype=np.float32)
            if nbytes != expected_bytes or not np.array_equal(actual, expected):
                raise ValueError(f"native bytes or restored numeric values differ for {arm}")
            results[arm] = dict(bytes=nbytes, restored=actual.size, exact_values=True,
                                output_sha256=sha256(received).hexdigest())
    PROOF.mkdir()
    publish(PROOF/"report.json", dict(arms=results, sources=seal((Path(__file__), SCRIPTS/HEADER, SCRIPTS/TEST)),
                                        archive_header_sha256=archived_header))
    print(json.dumps(results), flush=True)


def evaluate_native():
    from scripts import diag_p077_long_choices as score

    proof = read(PROOF/"report.json")
    if proof["sources"] != seal((Path(__file__), SCRIPTS/HEADER, SCRIPTS/TEST)):
        raise ValueError("the compiled cache proof is stale")
    saved, reference = read(OLD/"fixture.json"), read(score.REFERENCE/"report.json")
    prior = {(item["task"], item["index"]): item for item in read(OLD/"report.json")["rows"]
             if item["mode"] == "int4" and item["placement"] == "far"}
    rows = saved["chosen"]
    if len(rows) != 8 or len(prior) != len(rows):
        raise ValueError("the saved eight matched questions are required")
    RESULT.mkdir(exist_ok=False)
    native = score.native
    bounded = native.bounded
    base = bounded.base
    source = (ROOT/base.CPP).read_bytes()
    common = score.render_forcing(native.render(source, 2048, 3, True, True))
    binaries = {}
    for arm in ("k2v4", "k4v2"):
        prefix, k, v, _ = ARMS[arm]
        rendered = native.replace_once(common, b"cache(capacity, 1024, 3)", f"cache(capacity, {prefix}, {k}, {v})".encode())
        folder = RESULT/arm
        folder.mkdir()
        with patch.object(bounded, "OUT", folder):
            binaries[arm] = bounded.build(rendered, caps=(64,))[64][0]

    with ExitStack() as cleanup:
        descriptors = [base.memfile(f"p077-lowbits-{version}") for version in ("r4", "r5")]
        for descriptor in descriptors:
            cleanup.callback(os.close, descriptor)
        origin, r5 = descriptors
        profile = base.READ(bounded.text.OUT/"profile.json")["pins"]["candidate"]
        g4 = base.prior.load_candidate(profile)
        if base.model_blob(g4, origin, profile["model_tensor_bytes"]) != reference["model"]:
            raise ValueError("R4 model differs from the saved run")
        identity = native.extend_positions(origin, r5, g4)
        if identity != saved["model"] or identity != reference["extended_model"]:
            raise ValueError("R5 model differs from the saved run")
        del g4
        cpus = sorted(set(score.CPU_CORES) & os.sched_getaffinity(0))[:4]
        if not cpus:
            raise RuntimeError("no approved benchmark cores are available")
        queue = [(arm, row) for row in rows for arm in binaries]

        def worker(cpu, jobs):
            for arm, row in jobs:
                received = score.compare(row, binaries[arm], r5, cpu, RESULT, "far", resources=True)
                if any(t["kv_bytes"] != ARMS[arm][3] for t in received["choices"]):
                    raise ValueError(f"the real R5 repeated width differs from {arm}")
                task, index = row["task"], row["index"]
                old = prior[(task, index)]
                received.update(task=task, index=index, mode=arm, cpu=cpu,
                                previous_correct=old["correct"], previous_margin=old["margin"])
                publish(RESULT/arm/f"{task}-{index}.json", received)
                print(json.dumps(dict(arm=arm, task=task, index=index, correct=received["correct"],
                                      margin=received["margin"])), flush=True)
                yield received

        with ThreadPoolExecutor(max_workers=len(cpus)) as executor:
            futures = [executor.submit(lambda c, jobs: list(worker(c, jobs)), cpu, queue[i::len(cpus)])
                       for i, cpu in enumerate(cpus)]
            items = [item for future in futures for item in future.result()]
    if len(items) != len(queue):
        raise RuntimeError("not every authorized matched choice finished")
    publish(RESULT/"report.json", dict(model=identity, chosen=len(rows), rows=items,
             sources=seal((Path(__file__), SCRIPTS/HEADER, Path(score.__file__))),
             previous_fixture_sha256=sha256((OLD/"fixture.json").read_bytes()).hexdigest()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("codec", "r5"))
    (native_codec if parser.parse_args().mode == "codec" else evaluate_native)()
