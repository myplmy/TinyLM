"""Verify the portable compact G4 kernels and the full Linux UTF-8 request."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from time import perf_counter

import numpy as np
import torch

from scripts import diag_p108_g4_compact_fixed_edit_text as edits
from tinylm.model.lut import pack_trits, unpack_trits


base, fast, tile, text, codec = edits.base, edits.fast, edits.tile, edits.text_exec, edits.bytelevel
ROOT, END = edits.ROOT, edits.END
TAG = "p109_g4_portable_cpu_v1_20261119"
OUT = fast.OUT.with_name(TAG)
PLAN = ROOT / "test_plan/P109_16층-공유-재귀-프리셋-통합.md"
PROBES = ROOT / "scripts/test_p109_g4_portable_kernels.cpp"
PORTABLE = ["-mno-avx", "-mno-avx2", "-mno-fma", "-mno-f16c"]
AVX2 = ["-mavx2", "-mfma", "-mf16c"]
FLAGS = ["-std=c++17", "-O3", "-ffp-contract=off", "-Wall", "-Wextra", "-Werror"]
CASES = {"english": fast.OUT / "raw_case_1.json", "korean": fast.OUT / "raw_case_5.json"}
LIMIT = 720
SEED, WIDTH = 65109, 33


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(END.tzinfo) + timedelta(seconds=reserve) >= END:
        raise RuntimeError("owned STOP or deadline")


def build():
    directory = Path(tempfile.mkdtemp(prefix="p109_portable_cpu_"))
    lookup = directory / "lookup.o"
    portable_core = directory / "portable.o"
    native, full = (directory / name for name in ("g4", "g4_text"))
    tests = [directory / name for name in ("probe_scalar", "probe_avx2")]
    commands = [
        (["/usr/bin/gcc", "-std=c11", "-O3", *PORTABLE, "-c", base.C, "-o", str(lookup)], None),
    ]
    for switches, test in zip((PORTABLE, AVX2), tests, strict=True):
        commands.append((["/usr/bin/g++", *FLAGS, *switches, str(PROBES), str(lookup), "-o", str(test)], None))
    original = (ROOT / base.CPP).read_bytes()
    assert original.count(tile.ORIGINAL) == 1
    source = original.replace(tile.ORIGINAL, tile.CHANGED, 1)
    commands.extend([
        (["/usr/bin/g++", *FLAGS, *PORTABLE, "-x", "c++", "-c", "-", "-o", str(portable_core)], source),
        (["/usr/bin/g++", "-static", str(portable_core), str(lookup), "-o", str(native)], None),
        (["/usr/bin/g++", *FLAGS, *PORTABLE, "-Dmain=run_compact_g4", "-x", "c++", "-c", "-", "-o",
          str(directory / "exec.o")], source),
        (["/usr/bin/g++", *FLAGS, *PORTABLE, "-static", text.WRAPPER, str(directory / "exec.o"),
          str(lookup), "-o", str(full)], None),
    ])
    for command, data in commands:
        subprocess.run(command, input=data, cwd=ROOT, timeout=60, check=True)
    results = [subprocess.check_output([str(path)], timeout=15) for path in tests]
    half_decode, half_encode, rounding, kernel_scalars = 65536, 65536, 256000, 97*(6+64)
    expected = half_decode*4 + (half_encode+rounding)*2 + kernel_scalars*4
    fingerprints = [sha256(data).hexdigest().upper() for data in results]
    if len(results[0]) != expected or results[0] != results[1]:
        first = next((i for i, (a, b) in enumerate(zip(*results)) if a != b), -1)
        raise ValueError(f"portable kernel byte comparison failed at {first}, lengths {[len(x) for x in results]}")
    objdump = subprocess.check_output(["/usr/bin/objdump", "-d", "--no-show-raw-insn", str(portable_core)], text=True)
    assert not re.search(r"^\s*[0-9a-f]+:\s+v[a-z0-9]+\b|%[yz]mm", objdump, flags=re.MULTILINE)
    for path in (native, full):
        assert "INTERP" not in subprocess.check_output(["/usr/bin/readelf", "-l", str(path)], text=True)
    return dict(binaries=dict(native=str(native), full=str(full)), hashes={str(p):base.SHA(p) for p in (native,full)},
        commands=[cmd for cmd, _ in commands], kernel_output_sha256=fingerprints[0], exact_output_bytes=expected,
        half_patterns=half_decode, f32_rounding_cases=rounding, dot_output_attention_values=kernel_scalars,
        compiler=subprocess.check_output(["/usr/bin/g++","--version"],text=True).splitlines()[0],
        core_without_avx_instructions=True)


def verify(profile):
    assert profile["tag"] == TAG and profile["approval"] == 177
    for path, digest in (profile["pins"] | profile["build"]["hashes"]).items():
        assert base.SHA(Path(path)) == digest, path


def prepare():
    old = base.READ(fast.OUT / "report.json")
    e, eprofile = (base.READ(edits.OUT / f"{name}.json") for name in ("report", "profile"))
    assert old["profile_sha256"] == base.SHA(fast.OUT / "profile.json")
    assert e["profile_sha256"] == base.SHA(edits.OUT / "profile.json") and e["source"] == old["artifact"]
    assert base.SHA(base.prior.ORIGIN.PARENT) == base.prior.ORIGIN.PARENT_SHA == eprofile["parent_sha256"]
    assert all(row["exact"] for row in old["runs"])
    historical = edits.pinned_binary(eprofile["pretokenized"], eprofile["pretokenized_sha256"])
    references = [edits.OUT / f"{name}_transfer.json" for name in edits.ARMS]
    paths = [fast.OUT / "profile.json", fast.OUT / "report.json", edits.OUT / "profile.json",
             edits.OUT / "report.json", codec.OUT / "profile.json", codec.OUT / "report.json", codec.TOK,
             ROOT / base.CPP, ROOT / base.C, ROOT / text.WRAPPER, ROOT / text.SCRIPT, PROBES,
             Path(__file__), historical, base.prior.ORIGIN.PARENT, edits.OFFSETS, *references, *CASES.values()]
    plan = PLAN.read_text(encoding="utf-8").split("#### 4AJ.", 1)
    assert len(plan) == 2 and TAG in plan[1]
    OUT.mkdir(exist_ok=False)
    receipt_path = OUT / "plan_at_execution.md"
    receipt_path.write_text("#### 4AJ." + plan[1].split("## 5.",1)[0], encoding="utf-8")
    paths.append(receipt_path)
    if base.SHA(codec.TOK) != base.READ(codec.OUT / "profile.json")["source_sha256"]:
        raise ValueError("32K tokenizer bytes differ")
    profile = dict(tag=TAG, approval=177, pins={str(p):base.SHA(p) for p in paths},
                   build=build(), candidate=eprofile["candidate"], original_model=old["artifact"],
                   reference_binary=str(historical), short_seed=SEED, edit_probe_seed=eprofile["short_seed"])
    verify(profile)
    assert not torch.cuda.is_initialized()
    base.WRITE(OUT / "profile.json", profile)
    print("PORTABLE_G4_KERNELS", profile["build"]["kernel_output_sha256"],
          profile["build"]["exact_output_bytes"], flush=True)


def compare_logits(profile, model_fd):
    rng = torch.Generator().manual_seed(profile["short_seed"])
    ids = [1, *torch.randint(35, 32768, (WIDTH-1,), generator=rng).tolist()]
    results = [base.run_native(path, model_fd, ids, scores=True)
               for path in (profile["reference_binary"], profile["build"]["binaries"]["native"])]
    (a, baseline), (b, new) = results
    assert a["ids"] == b["ids"]
    assert baseline.tobytes() == new.tobytes(), float(np.max(np.abs(baseline - new)))
    proof = dict(inputs=ids, outputs=b["ids"], rows=new.shape[0], vocabulary=new.shape[1],
                 logits_sha256=sha256(new.tobytes()).hexdigest().upper(), bit_equal=True,
                 short_seconds=(a["process_seconds"], b["process_seconds"]))
    base.WRITE(OUT / "short_logits.json", proof)
    print("PORTABLE_G4_LOGITS", proof["short_seconds"], proof["logits_sha256"], flush=True)


def verify_edits(profile, model_fd, fd):
    offsets = base.READ(edits.OFFSETS)["cases"]
    plain = os.pread(model_fd, profile["original_model"]["artifact_bytes"], 0)
    ids = torch.randint(35, 32768, (base.SHORT,),
                        generator=torch.Generator().manual_seed(profile["edit_probe_seed"])).tolist()
    results = []
    for arm in edits.ARMS:
        reference = base.READ(edits.OUT / f"{arm}_transfer.json")
        positions = reference["changed_serialized_byte_offsets"]
        checks = sorted(offsets[arm]["checks"], key=lambda row: row["physical_layer"])
        raw = bytearray(plain)
        for offset, row in zip(positions, checks, strict=True):
            word = unpack_trits(torch.tensor([raw[offset]],dtype=torch.uint8), 5)
            for digit, weight in row["edited_trits"]:
                word[digit] = weight
            value, _ = pack_trits(word)
            assert raw[offset] != value.item()
            raw[offset] = value.item()
        digest = sha256(raw).hexdigest().upper()
        assert digest == reference["blob"]["artifact_sha256"], arm
        handle = fd("portable_edit_" + arm)
        text.store(handle, raw)
        edits.seal(handle)
        native, _ = base.run_native(profile["build"]["binaries"]["native"], handle, ids)
        assert native["ids"] == reference["short_native_ids"], arm
        results.append(dict(arm=arm, changed_bytes=positions, model_sha256=digest, ids=native["ids"],
                            short_seconds=native["process_seconds"]))
        print("PORTABLE_G4_EDIT", results[-1], flush=True)
    base.WRITE(OUT / "direct_edits.json", results)


def full_request(binary, fds, language, message, cpu, reference):
    gate(LIMIT+15)
    with ExitStack() as local:
        scratch = [base.memfile(f"portable_{language}_{i}") for i in range(3)]
        for item in scratch:
            local.callback(os.close, item)
        args = (*fds, *scratch)
        command = ["/usr/bin/taskset", "-c", str(cpu), sys.executable, "-I", "-S", "-B", "-X", "utf8",
                   str(ROOT / text.SCRIPT), "encode", binary, *map(str, args)]
        start = perf_counter()
        print("PORTABLE_G4_START", language, cpu, flush=True)
        proc = subprocess.run(command, input=message, capture_output=True, timeout=LIMIT, pass_fds=args, cwd=ROOT)
        if proc.returncode:
            print(language, proc.stderr.decode("utf-8", "replace"), flush=True)
            proc.check_returncode()
        elapsed = perf_counter() - start
    result = json.loads(proc.stdout)
    base.WRITE(OUT / f"raw_{language}.json", result)
    a, b = reference["native"], result["native"]
    peak = max(
        *(b[stage][key] for stage in ("before", "loaded", "prefilled", "complete") for key in ("rss", "vm_hwm")),
        *(value for stage in ("encoding", "decoding") for record in result[stage].values()
          if isinstance(record, dict) for key, value in record.items() if key.endswith("_bytes")),
    )
    same = (result["encoding"]["ids"] == reference["encoding"]["ids"] and a["ids"] == b["ids"]
            and result["decoding"]["text"] == reference["decoding"]["text"])
    assert same and result["encoding"]["pid"] == result["native_pid"] == result["decoding"]["pid"]
    assert all(a[key] == b[key] for key in ("model_bytes", "kv_bytes", "scratch_bytes"))
    observed = dict(language=language, cpu=cpu, peak_rss_bytes=peak, within_40mb=peak <= 40_000_000,
                    native_first=b["seconds"][0], native_decode=sum(b["seconds"][1:]),
                    wall_seconds=elapsed, exact=same)
    base.WRITE(OUT / f"summary_{language}.json", observed)
    print("PORTABLE_G4_TEXT", observed, flush=True)
    return observed


@torch.inference_mode()
def run(profile):
    gate(2*LIMIT+120)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    available = sorted(os.sched_getaffinity(0))
    workers = max(1, min(2, len(available)))
    cpus = dict(zip(CASES, (available[0], available[-1]), strict=True))
    tok_ref = base.READ(codec.OUT / "profile.json")
    payloads = codec.wire(json.loads(codec.TOK.read_bytes()))
    assert [sha256(data).hexdigest().upper() for data in payloads] == [
        row["sha256"] for row in tok_ref["files"]["split_model"]]
    prompts = base.READ(codec.OUT / "report.json")["runs"]["split_model"][0]["outputs"]
    with ExitStack() as parent:
        def fd(name):
            handle = base.memfile(name)
            parent.callback(os.close, handle)
            return handle

        model_fd = fd("g4_portable_unchanged_model")
        model = base.prior.load_candidate(profile["candidate"])
        artifact = base.model_blob(model, model_fd, profile["candidate"]["model_tensor_bytes"])
        del model
        assert artifact == profile["original_model"]
        print("PORTABLE_G4_MODEL", artifact["artifact_sha256"], flush=True)
        vocab, merges = fd("g4_portable_vocab"), fd("g4_portable_merges")
        for handle, data in zip((vocab, merges), payloads, strict=True):
            text.store(handle, data)
            edits.seal(handle)
        compare_logits(profile, model_fd)
        verify_edits(profile, model_fd, fd)
        binary = profile["build"]["binaries"]["full"]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {language:pool.submit(full_request, binary, (model_fd,vocab,merges), language,
                        prompts[language]["decoded"].encode(), cpus[language], base.READ(reference))
                        for language, reference in CASES.items()}
            requests = [task.result() for task in futures.values()]
    verify(profile)
    assert not torch.cuda.is_initialized()
    base.WRITE(OUT / "report.json", dict(tag=TAG, profile_sha256=base.SHA(OUT/"profile.json"),
        source=artifact, short=base.READ(OUT/"short_logits.json"), edits=base.READ(OUT/"direct_edits.json"),
        cases=requests, sources_preserved=True, cuda_initialized=False, checkpoint_writes=0))
    print("PORTABLE_G4_ACTUAL_COMPLETE", requests, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run"))
    phase = parser.parse_args().phase
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    gate()
    if phase == "prepare":
        prepare()
    else:
        profile = base.READ(OUT / "profile.json")
        verify(profile)
        run(profile)
