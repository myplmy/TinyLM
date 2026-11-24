"""Check lifetime-based G4 buffer reuse in the verified Windows text request."""

import argparse
import os
from pathlib import Path
import re
import struct
import tempfile

import torch

from scripts import diag_p109_248k_win64_icu_text as text


win, io, gold, half, ROOT = text.win, text.io, text.gold, text.half, text.ROOT
OUT = text.OUT.with_name("p109_248k_win64_icu_buffers_v1_20261119")
OUT_MLP = text.OUT.with_name("p109_248k_win64_icu_mlp_v1_20261119")
FULL = text.OUT / "attempt_01"


def authority(seconds=0):
    if (OUT / "STOP").is_file() or (OUT_MLP / "STOP").is_file():
        raise RuntimeError("Windows buffer reuse was stopped")
    text.authority(seconds)


def reuse_buffers(source, fuse_mlp=False):
    edits = (
        (b"attention(query.data() + t*D, attn.data() + t*D, pos + 1, past);",
         b"attention(query.data() + t*D, norm.data() + t*D, pos + 1, past);"),
        (b"project(layer.o, attn.data(), projected.data(), n, weight.data());",
         b"project(layer.o, norm.data(), query.data(), n, weight.data());"),
        (b"resid[j] += layer.gates[0] * projected[j];", b"resid[j] += layer.gates[0] * query[j];"),
        (b"project(mlp.down, gate.data(), projected.data(), n, weight.data());",
         b"project(mlp.down, gate.data(), query.data(), n, weight.data());"),
        (b"resid[j] += layer.gates[1] * projected[j];", b"resid[j] += layer.gates[1] * query[j];"),
        (b"std::array<float, Tile*D> norm{}, query{}, attn{}, projected{};",
         b"std::array<float, Tile*D> norm{}, query{};"),
    )
    for before, after in edits:
        source = win.engine.replace(source, before, after)
    if fuse_mlp:
        source = reuse_mlp_buffers(source)
    return source


def reuse_mlp_buffers(source):
    edits = (
        (b"void project(const Matrix& hard, const float* x, float* y, int count, float* weight) {",
         b"""template<bool CombineGate = false>
void project(const Matrix& hard, const float* x, float* y, int count, float* weight) {"""),
        (b"""        for (int t = 0; t < count; ++t)
            y[t * hard.rows + row] = dot(x + t * hard.cols, weight, hard.cols);""",
         b"""        for (int t = 0; t < count; ++t) {
            const float result = dot(x + t * hard.cols, weight, hard.cols);
            float& cell = y[t * hard.rows + row];
            if constexpr (CombineGate) cell = cell / (1.F + std::exp(-cell)) * result;
            else cell = result;
        }"""),
        (b"project(layer.q, norm.data(), query.data(), n, weight.data());",
         b"project(layer.q, norm.data(), gate.data(), n, weight.data());"),
        (b"rotate(query.data() + t*D, model.cos", b"rotate(gate.data() + t*D, model.cos"),
        (b"attention(query.data() + t*D, norm.data() + t*D, pos + 1, past);",
         b"attention(gate.data() + t*D, norm.data() + t*D, pos + 1, past);"),
        (b"project(layer.o, norm.data(), query.data(), n, weight.data());",
         b"project(layer.o, norm.data(), gate.data(), n, weight.data());"),
        (b"resid[j] += layer.gates[0] * query[j];", b"resid[j] += layer.gates[0] * gate[j];"),
        (b"""            project(mlp.up, norm.data(), up.data(), n, weight.data());
            for (int j = 0; j < n * F; ++j) gate[j] = gate[j] / (1.F + std::exp(-gate[j])) * up[j];""",
         b"            project<true>(mlp.up, norm.data(), gate.data(), n, weight.data());"),
        (b"project(mlp.down, gate.data(), query.data(), n, weight.data());",
         b"project(mlp.down, gate.data(), norm.data(), n, weight.data());"),
        (b"resid[j] += layer.gates[1] * query[j];", b"resid[j] += layer.gates[1] * norm[j];"),
        (b"std::array<float, Tile*D> norm{}, query{};\n    std::array<float, Tile*F> gate{}, up{};",
         b"""// Gate is also the Q/O workspace, which has fewer columns.
    static_assert(F >= D);
    std::array<float, Tile*D> norm{};
    std::array<float, Tile*F> gate{};"""),
    )
    for before, after in edits:
        source = win.engine.replace(source, before, after)
    return source


def verify_traces(exe, out, scratch, half_scratch, model, prompts, references):
    rows = []
    for item in references:
        prefix, generate, language = (item[key] for key in ("prefix", "generated", "language"))
        prior_raw = half_scratch / f"trace_{prefix}_candidate.bin"
        previous = next(row for row in item["arms"] if row["arm"] == "candidate")
        if (not item["equal"] or not prior_raw.resolve().is_relative_to(half_scratch) or
                io.digest(prior_raw) != previous["sha256"]):
            raise ValueError("archived half-history trace differs")
        request = struct.pack(f"<{prefix + 2}I", prefix, generate, *prompts[language]["ids"][:prefix])
        if win.digest(request) != item["request_sha256"]:
            raise ValueError("the archived trace input differs")
        path = scratch / f"trace_{prefix}_reused.bin"
        authority(28)
        raw, seconds = win.run_process([str(exe), win.win_path(model), win.win_path(path)], 26, data=request)
        actual = path.read_bytes() if path.is_file() else b""
        identical = raw.returncode == 0 and len(actual) == previous["bytes"] and actual == prior_raw.read_bytes()
        rows.append(dict(prefix=prefix, generated=generate, equal=identical, bytes=len(actual),
                         sha256=win.digest(actual), **win.record(raw, seconds)))
    io.write(out / "traces.json", rows)
    if len(rows) != 2 or not all(row["equal"] for row in rows):
        raise ValueError("buffer reuse differs from the archived full logits")
    print("P109_WIN64_REUSED_BUFFERS_TRACE", len(rows), sum(row["bytes"] for row in rows), flush=True)


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--fuse-mlp", action="store_true")
    args = parser.parse_args()
    if args.attempt < 1 or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("positive attempt number and isolated CPU are required")
    authority(250)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    out = (OUT_MLP if args.fuse_mlp else OUT) / f"attempt_{args.attempt:02d}"
    out.mkdir(parents=True)
    scratch = Path(tempfile.mkdtemp(prefix="p109_win64_buffers_", dir="/tmp"))
    full_profile = io.load(FULL / "profile.json")
    full_report = io.load(FULL / "report.json")
    half_profile = io.load(text.HALF / "profile.json")
    half_scratch = Path(half_profile["scratch"])
    original = io.load(half.REFERENCE / "profile.json")
    prior_tmp = Path(original["scratch"])
    if half_scratch.resolve().parent != Path("/tmp") or prior_tmp.resolve().parent != Path("/tmp"):
        raise ValueError("previous run state is outside local scratch")
    if not full_report["full_match"] or not full_report["sources_intact"]:
        raise ValueError("the Windows full text baseline is incomplete")
    fixtures, vocabulary, guards = (io.load(FULL / name) for name in ("tokenizer.json", "vocabulary.json", "guards.json"))
    if fixtures["mismatches"] or vocabulary["mismatches"] or not all(row["matched"] for row in guards):
        raise ValueError("the archived tokenizer verification differs")
    generated = {name: (FULL / name).read_bytes() for name in full_profile["generated"]}
    if any(win.digest(data) != full_profile["generated"][name] for name, data in generated.items()):
        raise ValueError("the existing Windows source evidence differs")
    decoder = generated["decoder.cpp"]
    dimensions = re.search(rb"constexpr int D = (\d+), E = \d+, F = (\d+),", decoder)
    tile_size = re.search(rb"constexpr int Group = \d+, PackedGroup = \d+, Tile = (\d+);", decoder)
    if not dimensions or not tile_size:
        raise ValueError("the built G4 workspace dimensions changed")
    width, mlp_width = map(int, dimensions.groups())
    tile = int(tile_size[1])
    removed = tile * struct.calcsize("<f") * (width + mlp_width if args.fuse_mlp else 2 * width)
    if io.digest(text.PACK) != full_profile["inputs"][str(text.PACK.relative_to(ROOT))]:
        raise ValueError("the verified tokenizer asset differs")
    lookup = win.engine.LOOKUP.read_bytes() + b"\n" + win.engine.EXTENSION.read_bytes()
    if win.digest(lookup) != original["lookup_sha256"]:
        raise ValueError("the verified AVX2 implementation differs")
    lookup_file = scratch / "avx2_lookup.cpp"
    lookup_file.write_bytes(lookup)
    prompt_path = gold.OUT / "profile.json"
    prompts = io.load(prompt_path)["requests"]
    trace_path = text.HALF / "traces.json"
    trace_source = text.HALF / "candidate" / "decoder_at_execution.cpp"
    sources = {str(p.relative_to(ROOT)): io.digest(p) for p in (
        Path(__file__), Path(text.__file__), gold.PLAN, text.PACK, prompt_path, trace_path, trace_source,
        win.engine.SCALAR, win.engine.LOOKUP, win.engine.EXTENSION, FULL / "profile.json", FULL / "report.json",
        *(FULL / name for name in (*generated, "tokenizer.json", "vocabulary.json", "guards.json")),
        *(gold.OUT / f"request_{name}_{lang}_1.json" for name in gold.MODELS for lang in prompts),
    )}
    if args.fuse_mlp:
        prior_path = OUT / "attempt_01" / "report.json"
        prior = io.load(prior_path)
        if not (prior["full_match"] and prior["sources_intact"]):
            raise ValueError("the attention workspace baseline is incomplete")
        sources[str(prior_path.relative_to(ROOT))] = io.digest(prior_path)
        before = {(row["model"], row["language"]): row["peak"] for row in prior["rows"]}
    else:
        before = {(row["model"], row["language"]): row["peak_bytes"] for row in full_report["requests"]}
    (out / "plan_at_execution.md").write_bytes(gold.PLAN.read_bytes())
    io.write(out / "profile.json", dict(approval="WIP177", scratch=str(scratch), sources=sources,
             target_bytes=text.MEMORY_TARGET, tile=tile, work_array_bytes_removed=removed,
             fuse_mlp=args.fuse_mlp))
    trace_exe = half.compile_arm(scratch / "trace", out / "trace", lookup_file,
                                 reuse_buffers(trace_source.read_bytes(), args.fuse_mlp), generated[win.CACHE.name])
    models = {name: half.model_file(name, pair[0], prior_tmp, scratch, original["models"][name])
              for name, pair in gold.MODELS.items()}
    verify_traces(trace_exe, out, scratch, half_scratch, models["ce_48"], prompts, io.load(trace_path))
    build = scratch / "text"
    build.mkdir()
    generated["decoder.cpp"] = reuse_buffers(decoder, args.fuse_mlp)
    for name, data in generated.items():
        (build / name).write_bytes(data)
        (out / name).write_bytes(data)
    exe = win.compile_decoder(build / "decoder.cpp", lookup_file, build, out)
    rows = []
    for name, model in models.items():
        for language, prompt in prompts.items():
            authority(46)
            row = text.measure(exe, out, model, win.win_path(text.PACK), name, language, prompt)
            if row["actual_exit"] or not all(row[key] for key in (
                    "ids_equal", "tokens_equal", "decoded_equal", "finish_equal", "resource_shapes_equal")):
                raise ValueError("a fixed text request changed")
            sample = row["output"]
            rows.append(dict(model=name, language=language, peak=row["peak_bytes"],
                             baseline_peak=before[name, language], total_seconds=row["seconds"],
                             icu_released=sample["icu_released"]))
        if io.digest(model) != original["models"][name]["sha256"]:
            raise ValueError("the sealed model export changed")
    intact = all(io.digest(ROOT / path) == value for path, value in sources.items())
    peak = max(row["peak"] for row in rows)
    io.write(out / "report.json", dict(rows=rows, peak=peak, target_bytes=text.MEMORY_TARGET,
             working_set_target_met=peak <= text.MEMORY_TARGET, full_match=True,
             sources_intact=intact, binary_sha256=io.digest(exe), cuda_initialized=torch.cuda.is_initialized()))
    if not intact or torch.cuda.is_initialized() or not all(row["icu_released"] for row in rows):
        raise ValueError("source integrity, CPU isolation or phase release failed")


if __name__ == "__main__":
    main()
