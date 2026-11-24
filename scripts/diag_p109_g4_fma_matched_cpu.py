"""Compare FMA on and off in the same 32K G4 full-text CPU requests."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from statistics import median
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

import torch

from scripts import diag_p109_g4_portable_cpu as prior
from scripts import diag_p109_g4_portable_fma_text as fma


base, text, codec = prior.base, prior.text, prior.codec
TAG = "p109_g4_fma_matched_cpu_v1_20261120"
OUT = prior.OUT.with_name(TAG)
LIMIT = 480
ORDERS = {
    "english": ("software", "hardware", "hardware", "software"),
    "korean": ("hardware", "software", "software", "hardware"),
}
CPUS = {"english": 14, "korean": 12}


def build_pair(directory):
    lookup = directory / "lookup.o"
    original = (prior.ROOT / base.CPP).read_bytes()
    if original.count(prior.tile.ORIGINAL) != 1:
        raise ValueError("Exact shared eight-token tiling source required")
    source = original.replace(prior.tile.ORIGINAL, prior.tile.CHANGED, 1)
    commands = [["/usr/bin/gcc", "-std=c11", "-O3", *prior.PORTABLE,
                 "-c", base.C, "-o", str(lookup)]]
    subprocess.run(commands[0], cwd=prior.ROOT, timeout=55, check=True)
    builds = {}
    for arm, switch in (("software", "-mno-fma"), ("hardware", "-mfma")):
        kernel = directory / f"{arm}.o"
        program = directory / f"g4_text_{arm}"
        flags = [*prior.FLAGS, *(switch if flag == "-mfma" else flag for flag in fma.FLAGS)]
        compile_cmd = ["/usr/bin/g++", *flags, "-Dmain=run_compact_g4",
                       "-x", "c++", "-c", "-", "-o", str(kernel)]
        link_cmd = ["/usr/bin/g++", *flags, "-static", text.WRAPPER,
                    str(kernel), str(lookup), "-o", str(program)]
        subprocess.run(compile_cmd, input=source, cwd=prior.ROOT, timeout=55, check=True)
        subprocess.run(link_cmd, cwd=prior.ROOT, timeout=55, check=True)
        commands.extend((compile_cmd, link_cmd))
        disassembly = subprocess.check_output(
            ["/usr/bin/objdump", "-d", str(kernel)], text=True, timeout=15,
        )
        fused = len(re.findall(r"\bv(?:f|fn)m(?:add|sub)[a-z0-9]*\b", disassembly))
        if (bool(fused) != (arm == "hardware")
                or "vcvtph2ps" in disassembly or "vcvtps2ph" in disassembly):
            raise ValueError(f"FMA instruction or shared software FP16 contract differs in {arm}")
        builds[arm] = dict(executable=str(program), sha256=base.SHA(program), flags=flags,
                           kernel_fma_instructions=fused)
    return builds, dict(commands=commands, tile8_source_sha256=sha256(source).hexdigest().upper(),
                        compiler=subprocess.check_output(["/usr/bin/g++", "--version"], text=True).splitlines()[0])


def run_language(language, builds, descriptors, prompt, reference):
    results = []
    for i, arm in enumerate(ORDERS[language], 1):
        result = prior.full_request(
            builds[arm]["executable"], descriptors, f"{language}_{i}_{arm}",
            prompt, CPUS[language], reference,
        )
        results.append({**result, "arm": arm, "trial": i})
    summarizes = {}
    for arm in builds:
        rows = [row for row in results if row["arm"] == arm]
        summarizes[arm] = dict(
            median_wall_seconds=median(row["wall_seconds"] for row in rows),
            median_first_seconds=median(row["native_first"] for row in rows),
            median_decode_seconds=median(row["native_decode"] for row in rows),
            max_rss_bytes=max(row["peak_rss_bytes"] for row in rows),
        )
    return dict(language=language, cpu=CPUS[language], trials=results, summaries=summarizes)


@torch.inference_mode()
def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or not set(CPUS.values()) <= os.sched_getaffinity(0):
        raise ValueError("CPU-only mode with the two selected cores is required")
    cores = {
        lang: int(Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/core_id").read_text())
        for lang, cpu in CPUS.items()
    }
    if len(set(cores.values())) != len(CPUS):
        raise ValueError("Use a different physical core for each language")
    prior_profile_path = prior.OUT / "profile.json"
    prior_profile = base.READ(prior_profile_path)
    prior.verify(prior_profile)
    archived = {lang: prior.OUT / f"raw_{lang}.json" for lang in ORDERS}
    codec_profile = codec.OUT / "profile.json"
    codec_report = codec.OUT / "report.json"
    source_paths = (Path(__file__), Path(prior.__file__), Path(fma.__file__), prior.ROOT / base.C,
                    prior.ROOT / base.CPP, prior.ROOT / text.WRAPPER, prior.ROOT / text.SCRIPT,
                    prior_profile_path, codec_profile, codec_report, codec.TOK, *archived.values())
    pins = {str(path): base.SHA(path) for path in source_paths}
    plan = prior.PLAN.read_text(encoding="utf-8").split('id="p109-g4-fma-matched-cpu-plan"', 1)[1]
    plan = plan.split("## 5. 판정 기준", 1)[0]
    if TAG not in plan:
        raise ValueError("Missing current plan for the matched comparison")
    OUT.mkdir()
    plan_path = OUT / "plan_at_execution.md"
    plan_path.write_text(plan[plan.index("####"):], encoding="utf-8")
    pins[str(plan_path)] = base.SHA(plan_path)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    payloads = codec.wire(json.loads(codec.TOK.read_bytes()))
    target_hashes = [row["sha256"] for row in base.READ(codec_profile)["files"]["split_model"]]
    already = base.READ(codec_report)["runs"]["split_model"][0]["outputs"]
    if [sha256(data).hexdigest().upper() for data in payloads] != target_hashes:
        raise ValueError("The pinned text byte tables differ")

    with (TemporaryDirectory(prefix="p109_g4_fma_matched_") as directory, ExitStack() as stack,
          patch.multiple(prior, OUT=OUT, LIMIT=LIMIT)):
        prior.gate(1120)
        builds, build_evidence = build_pair(Path(directory))
        fds = tuple(base.memfile(name) for name in ("matched_weights", "matched_vocab", "matched_merges"))
        for fd in fds:
            stack.callback(os.close, fd)
        model = base.prior.load_candidate(prior_profile["candidate"])
        artifact = base.model_blob(model, fds[0], prior_profile["candidate"]["model_tensor_bytes"])
        del model
        if artifact != prior_profile["original_model"]:
            raise ValueError("The unchanged packed 32K model is required")
        for fd, payload in zip(fds[1:], payloads, strict=True):
            text.store(fd, payload)
            prior.edits.seal(fd)
        base.WRITE(OUT / "profile.json", dict(tag=TAG, approval=177, builds=builds, build=build_evidence,
                    pins=pins, artifact=artifact, logical_cpus=CPUS, physical_cores=cores, orders=ORDERS))
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(run_language, lang, builds, fds, already[lang]["decoded"].encode(),
                                base.READ(reference)) for lang, reference in archived.items()]
            results = [job.result() for job in jobs]
        if any(base.SHA(Path(row["executable"])) != row["sha256"] for row in builds.values()):
            raise ValueError("An executable changed during measurement")
    prior.verify(prior_profile)
    if torch.cuda.is_initialized() or any(base.SHA(Path(name)) != sha for name, sha in pins.items()):
        raise ValueError("CPU-only execution or source-pin check failed")
    base.WRITE(OUT / "report.json", dict(tag=TAG, cases=results, cuda_initialized=False, checkpoint_writes=0,
                                        source_preserved=True, artifact=artifact))
    print("P109_FMA_MATCHED_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
