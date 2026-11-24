"""Measure the existing 248K grouped-INT8 decoder on Windows x64."""

import argparse
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from statistics import median
import struct
import subprocess
import tempfile
from time import perf_counter, time

import torch

from scripts import diag_p109_248k_long_text as gold


ROOT, engine, io = gold.ROOT, gold.engine, gold.io
OUT = gold.OUT.with_name("p109_248k_win64_int8_v1_20261119")
VC = Path("/mnt/c/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/"
          "VC/Tools/MSVC/14.44.35207")
SDK = "C:/Program Files (x86)/Windows Kits/10"
SDK_VERSION = "10.0.26100.0"
CUTOFF = datetime.fromisoformat("2026-11-20T16:58:00+09:00").timestamp()
CACHE = ROOT / "scripts/p109_g4_grouped_int8_cache.hpp"
WINDOWS_FP16 = b"""inline float win_half_to_float(uint16_t value) {
    return _mm_cvtss_f32(_mm_cvtph_ps(_mm_cvtsi32_si128(value)));
}

inline uint16_t win_float_to_half(float value) {
    return static_cast<uint16_t>(_mm_cvtsi128_si32(_mm_cvtps_ph(
        _mm_set_ss(value), _MM_FROUND_TO_NEAREST_INT)));
}

"""
WINDOWS_HEADERS = b"""#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <Windows.h>
#include <Psapi.h>
#include <io.h>
#if !defined(_M_X64)
#error This diagnostic requires Windows x64.
#endif
"""
WINDOWS_MAPPING = b"""class WinHandle {
public:
    explicit WinHandle(HANDLE value) : value(value) {}
    WinHandle(const WinHandle&) = delete;
    WinHandle& operator=(const WinHandle&) = delete;
    ~WinHandle() { if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value); }
    const HANDLE value;
};

class Mapping {
public:
    explicit Mapping(const wchar_t* path)
        : file(CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING,
                           FILE_ATTRIBUTE_NORMAL, nullptr)) {
        require(file.value != INVALID_HANDLE_VALUE, "unable to open Windows model");
        LARGE_INTEGER length{};
        require(GetFileSizeEx(file.value, &length) && length.QuadPart > 0 &&
                length.QuadPart < 30000000, "invalid Windows model size");
        size = static_cast<size_t>(length.QuadPart);
        const WinHandle section(CreateFileMappingW(file.value, nullptr, PAGE_READONLY, 0, 0, nullptr));
        require(section.value != nullptr, "Windows file mapping could not be created");
        data = static_cast<const uint8_t*>(MapViewOfFile(section.value, FILE_MAP_READ, 0, 0, size));
        require(data != nullptr, "Windows file mapping could not be read");
    }
    Mapping(const Mapping&) = delete;
    Mapping& operator=(const Mapping&) = delete;
    ~Mapping() { UnmapViewOfFile(data); }
    const uint8_t* data = nullptr;
    size_t size = 0;
private:
    const WinHandle file;
};

"""
WINDOWS_MEMORY = br"""struct Memory {
    size_t working_set, peak_working_set, private_commit;
};

Memory read_memory() {
    PROCESS_MEMORY_COUNTERS_EX value{};
    require(K32GetProcessMemoryInfo(GetCurrentProcess(),
                reinterpret_cast<PROCESS_MEMORY_COUNTERS*>(&value), sizeof(value)) &&
            value.WorkingSetSize > 0 && value.PeakWorkingSetSize >= value.WorkingSetSize,
            "incomplete Windows memory accounting");
    return {value.WorkingSetSize, value.PeakWorkingSetSize, value.PrivateUsage};
}

void print_memory(const char* name, const Memory& m) {
    printf(",\"%s\":{\"working_set\":%zu,\"peak_working_set\":%zu,\"private_commit\":%zu}",
           name, m.working_set, m.peak_working_set, m.private_commit);
}
"""


def authority(seconds=0):
    if time() + seconds >= CUTOFF or (OUT / "STOP").exists():
        raise RuntimeError("outside the approved Windows CPU experiment or stopped")


def digest(data):
    return sha256(data).hexdigest().upper()


def span(source, first, last, replacement):
    if source.count(first) != 1 or source.count(last) != 1:
        raise ValueError("portable decoder source boundaries changed")
    start = source.index(first)
    stop = source.index(last, start)
    return source[:start] + replacement + source[stop:]


def render_windows(source):
    for old, new in (
        (b"#include <sys/mman.h>\n#include <sys/stat.h>\n#include <unistd.h>\n", WINDOWS_HEADERS),
        (b"int main(int argc, char** argv)", b"int wmain(int argc, wchar_t** argv)"),
        (b'        require(argc == 3, "expected model and optional logit file descriptors");\n'
         b"        const int model_fd = std::stoi(argv[1]), logits_fd = std::stoi(argv[2]);",
         b'        require(argc == 2, "expected a packed model path");\n'
         b'        require(_setmode(_fileno(stdin), _O_BINARY) != -1, "cannot set stdin to binary");\n'
         b'        const int logits_fd = -1;'),
        (b"        Mapping packed(model_fd);", b"        Mapping packed(argv[1]);"),
        (b"            if (logits_fd >= 0) write_logits(logits_fd, runtime.logits);\n", b""),
    ):
        source = engine.replace(source, old, new)
    source = span(source, b"class Mapping {", b"struct Reader {", WINDOWS_MAPPING)
    return span(source, b"struct Memory {", b"}  // namespace", WINDOWS_MEMORY)


def render_windows_cache(source):
    if source.count(b"_cvtsh_ss(") != 4:
        raise ValueError("grouped INT8 cache half conversions changed")
    source = source.replace(b"_cvtsh_ss(", b"win_half_to_float(")
    source = engine.replace(
        source, b"_cvtss_sh(std::max(peak / 127.F, MinimumScale), _MM_FROUND_TO_NEAREST_INT)",
        b"win_float_to_half(std::max(peak / 127.F, MinimumScale))")
    anchor = b"class GroupedInt8Cache {"
    return engine.replace(source, anchor, WINDOWS_FP16 + anchor)


def win_path(path):
    return subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()


def run_process(args, seconds, env=None, data=None):
    authority(seconds)
    start = perf_counter()
    result = subprocess.run(args, env=env, input=data, timeout=seconds, capture_output=True)
    return result, perf_counter() - start


def record(result, elapsed):
    def decode(value):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return value.decode("cp949", "replace")

    return dict(actual_exit=result.returncode, seconds=elapsed,
                stdout=decode(result.stdout), stderr=decode(result.stderr))


def compile_decoder(source, lookup_source, build, out):
    vc = win_path(VC)
    include = [vc + "/include", *(f"{SDK}/Include/{SDK_VERSION}/{name}"
                                 for name in ("ucrt", "shared", "um"))]
    lib = [vc + "/lib/x64", *(f"{SDK}/Lib/{SDK_VERSION}/{name}/x64" for name in ("ucrt", "um"))]
    config = dict(INCLUDE=";".join(include), LIB=";".join(lib), TMP=win_path(build),
                  TEMP=win_path(build), VSLANG="1033")
    forwarded = [entry for entry in os.environ.get("WSLENV", "").split(":")
                 if entry and entry.split("/", 1)[0] not in config]
    env = dict(os.environ, **config, WSLENV=":".join([*forwarded, *config]))
    cc = str(VC / "bin/Hostx64/x64/cl.exe")
    common = [cc, "/nologo", "/O2", "/MT", "/arch:AVX2", "/fp:strict"]
    scalar, exe = build / "scalar.obj", build / "decoder.exe"
    commands = (
        [*common, "/c", "/Dp014e_cpu_lookup=p014e_scalar_lookup",
         "/Fo" + win_path(scalar), win_path(engine.SCALAR)],
        [*common, "/EHsc", "/std:c++17", "/DP109_PREFILL_TOKENS=256", "/I" + win_path(engine.BODY.parent),
         "/Fo" + win_path(build) + "/", "/Fe" + win_path(exe),
         win_path(source), win_path(lookup_source), win_path(scalar),
         "/link", "/MACHINE:X64", "/STACK:16777216"],
    )
    receipts = []
    for command in commands:
        result, elapsed = run_process(command, 30, env)
        receipts.append(dict(command=command, **record(result, elapsed)))
        if result.returncode:
            break
    io.write(out / "compiler.json", dict(sdk=SDK_VERSION, receipts=receipts))
    if any(row["actual_exit"] for row in receipts):
        raise RuntimeError("MSVC build failed, see compiler.json")
    image = exe.read_bytes()
    offset = struct.unpack_from("<I", image, 0x3C)[0]
    if image[:2] != b"MZ" or image[offset:offset + 6] != b"PE\0\0d\x86":
        raise ValueError("decoder is missing the AMD64 PE header")
    exe.chmod(0o700)
    return exe


def export_model(name, asset, source, path):
    model = gold.prior.learned.load_payload(torch.load(asset, map_location="cpu", weights_only=True),
                                          device="cpu", tile_rows=4096)
    model.cfg.kv_dtype = "fp32"
    fd = engine.prefill.base.memfile(f"p109_win64_{name}")
    try:
        metadata = gold.prior.serialize(model, fd)
        if metadata != source:
            raise ValueError(f"Windows model export differs from the WSL model {name}")
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(fd), "rb") as stream, path.open("xb") as output:
            shutil.copyfileobj(stream, output)
    finally:
        os.close(fd)
    path.chmod(0o400)
    if io.digest(path) != source["sha256"]:
        raise ValueError(f"packed file differs for {name}")


def check_guards(exe, out):
    cases = ((1, gold.GENERATE + 1), (gold.LIMIT, gold.GENERATE), (gold.PREFIX, 0))
    rows = []
    for prefix, count in cases:
        result, elapsed = run_process([str(exe), "invalid-model-path"], 8,
                                      data=struct.pack("<2I", prefix, count))
        rows.append(dict(prefix=prefix, count=count, **record(result, elapsed)))
    io.write(out / "guards.json", rows)
    if any(row["actual_exit"] != 1 or "unsupported request shape" not in row["stderr"] for row in rows):
        raise ValueError("an out-of-contract request reached model mapping")


def measure(exe, model, out, name, language, ids, expected):
    request = struct.pack(f"<{len(ids) + 2}I", len(ids), gold.GENERATE, *ids)
    result, elapsed = run_process([str(exe), win_path(model)], 44, data=request)
    row = dict(model=name, language=language, prefix_ids_sha256=digest(request),
               **record(result, elapsed))
    if result.returncode == 0:
        output = json.loads(result.stdout)
        actual = output["ids"]
        matched = next((i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]),
                       min(len(actual), len(expected)))
        row.update(output=output, expected_ids=expected, matched_prefix=matched,
                   all_ids_equal=actual == expected,
                   tail_32_median_seconds=median(output["seconds"][-32:]))
    io.write(out / f"request_{name}_{language}.json", row)
    print("P109_WIN64_248K_REQUEST", name, language, row["actual_exit"],
          row.get("matched_prefix", 0), round(elapsed, 3), flush=True)
    return row


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=int, default=1)
    args = parser.parse_args()
    if args.attempt < 1 or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("positive attempt number and isolated CPU are required")
    authority(250)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    out = OUT / f"attempt_{args.attempt:02d}"
    out.mkdir(parents=True)
    build = Path(tempfile.mkdtemp(prefix="p109_win64_int8_", dir="/tmp"))
    old_profile = io.load(gold.OUT / "profile.json")
    old_report = io.load(gold.OUT / "report.json")
    reference_hash = io.load(gold.OUT / "compiler.json")["source_sha256"][1]
    _, rendered = gold.render()
    if digest(rendered) != reference_hash or gold.model_sources() != old_profile["assets"]:
        raise ValueError("existing packed runtime or model source differs")
    generated = render_windows(rendered)
    source = build / "decoder.cpp"
    source.write_bytes(generated)
    (out / "decoder_at_execution.cpp").write_bytes(generated)
    generated_cache = render_windows_cache(CACHE.read_bytes())
    (build / CACHE.name).write_bytes(generated_cache)
    (out / CACHE.name).write_bytes(generated_cache)
    lookup_source = build / "avx2_lookup.cpp"
    lookup_bytes = engine.LOOKUP.read_bytes() + b"\n" + engine.EXTENSION.read_bytes()
    lookup_source.write_bytes(lookup_bytes)
    plan = gold.PLAN
    (out / "plan_at_execution.md").write_bytes(plan.read_bytes())
    references = {(name, language): gold.OUT / f"request_{name}_{language}_1.json"
                  for name in gold.MODELS for language in old_profile["requests"]}
    files = [Path(__file__), plan, engine.BODY, engine.LOOKUP, engine.EXTENSION, engine.SCALAR,
             CACHE, gold.OUT / "compiler.json",
             gold.OUT / "profile.json", gold.OUT / "report.json", *references.values()]
    files.extend(item for pair in gold.MODELS.values() for item in pair)
    pins = {str(path.relative_to(ROOT)): io.digest(path) for path in files}
    for path in files:
        name = str(path.relative_to(ROOT))
        if name != str(plan.relative_to(ROOT)) and name in old_profile["sources"]:
            if pins[name] != old_profile["sources"][name]:
                raise ValueError(f"pinned dependency differs from 4Z: {name}")
    io.write(out / "profile.json", dict(approval="WIP177", scratch=str(build), inputs=pins,
             source_reference_sha256=reference_hash, source_windows_sha256=digest(generated),
             cache_windows_sha256=digest(generated_cache), lookup_sha256=digest(lookup_bytes),
             models=old_report["assets"],
             prefix=gold.PREFIX, generate=gold.GENERATE))
    print("P109_WIN64_248K_READY", out.relative_to(ROOT), flush=True)
    exe = compile_decoder(source, lookup_source, build, out)
    check_guards(exe, out)
    rows = []
    for name, (asset, _) in gold.MODELS.items():
        authority(100)
        model = build / f"{name}.packed"
        source_info = old_report["assets"][name]
        export_model(name, asset, source_info, model)
        for language, request in old_profile["requests"].items():
            expected = io.load(references[name, language])
            if expected["encoding"]["ids"] != request["ids"]:
                raise ValueError("WSL input token sequence differed")
            row = measure(exe, model, out, name, language, request["ids"], expected["native"]["ids"])
            if row["actual_exit"] == 0 and row["output"]["model_bytes"] != source_info["bytes"]:
                raise ValueError("Windows mapped model size differed")
            rows.append(row)
        if io.digest(model) != source_info["sha256"]:
            raise ValueError("Windows mapped model changed during generation")
    sources_intact = all(io.digest(ROOT / path) == value for path, value in pins.items())
    all_ids_equal = len(rows) == 4 and all(row.get("all_ids_equal", False) for row in rows)
    io.write(out / "report.json", dict(binary_sha256=io.digest(exe), requests=rows,
             all_ids_equal=all_ids_equal, sources_intact=sources_intact,
             cuda_initialized=torch.cuda.is_initialized(), memory="windows_process_working_set"))
    if not all_ids_equal or not sources_intact or torch.cuda.is_initialized():
        raise RuntimeError("Windows compatibility check differed, see report.json")


if __name__ == "__main__":
    main()
