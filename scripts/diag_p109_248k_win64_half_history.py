"""Verify a smaller FP16 history workspace for the existing Windows G4 decoder."""

import argparse
import json
import os
from pathlib import Path
import struct
import tempfile

import torch

from scripts import diag_p109_248k_win64_cpu as win


ROOT, io, gold = win.ROOT, win.io, win.gold
OUT = win.OUT.with_name("p109_248k_win64_half_history_v1_20261119")
REFERENCE = win.OUT / "attempt_03"
VOCAB = 248066
HISTORY_HELPERS = b"""__m256 load_history8(const uint16_t* values) {
    return _mm256_cvtph_ps(_mm_loadu_si128(reinterpret_cast<const __m128i*>(values)));
}

float dot_history(const float* x, const uint16_t* y) {
    __m256 a = _mm256_setzero_ps(), b = a, c = a, d = a;
    for (int j = 0; j < Head; j += 32) {
        a = _mm256_fmadd_ps(_mm256_loadu_ps(x+j), load_history8(y+j), a);
        b = _mm256_fmadd_ps(_mm256_loadu_ps(x+j+8), load_history8(y+j+8), b);
        c = _mm256_fmadd_ps(_mm256_loadu_ps(x+j+16), load_history8(y+j+16), c);
        d = _mm256_fmadd_ps(_mm256_loadu_ps(x+j+24), load_history8(y+j+24), d);
    }
    return reduce(_mm256_add_ps(_mm256_add_ps(a, b), _mm256_add_ps(c, d)));
}

"""
HISTORY_CACHE_METHODS = b"""    void restore(int slot, int past, uint16_t* keys, uint16_t* values) const {
        const int complete = past / GroupTokens * GroupTokens;
        for (int start = 0; start < complete; start += GroupTokens) {
            const int row = slot * packed_rows_ + start;
            const uint16_t* scales = key_scales_.data() + (row / GroupTokens) * Kv;
            for (int column = 0; column < Kv; column += 8) {
                const __m256 key_scale = _mm256_cvtph_ps(_mm_loadu_si128(
                    reinterpret_cast<const __m128i*>(scales + column)));
                for (int t = 0; t < GroupTokens; ++t) {
                    const int offset = (row + t) * Kv + column;
                    const int output = (start + t) * Kv + column;
                    const uint16_t scale = value_scales_[(row + t) * KvHeads + column / Head];
                    restore8(keys + output, key_codes_.data() + offset, key_scale);
                    restore8(values + output, value_codes_.data() + offset, _mm256_set1_ps(win_half_to_float(scale)));
                }
            }
        }
        if (const int remaining = past - complete) {
            const int offset = slot * tail_rows_ * Kv;
            std::copy_n(tail_keys_.data() + offset, remaining * Kv, keys + complete * Kv);
            std::copy_n(tail_values_.data() + offset, remaining * Kv, values + complete * Kv);
        }
    }

    void append(int slot, int past, int count, const float* keys, const float* values) {
        const int end = past + count;
        const int complete = end / GroupTokens * GroupTokens;
        const int tail_offset = slot * tail_rows_ * Kv;
        for (int start = past / GroupTokens * GroupTokens; start < complete; start += GroupTokens) {
            const int previous = std::max(past - start, 0);
            if (previous) {
                std::copy_n(tail_keys_.data() + tail_offset, previous * Kv, work_keys_.data());
                std::copy_n(tail_values_.data() + tail_offset, previous * Kv, work_values_.data());
            }
            const int current = (start + previous - past) * Kv;
            const int cells = (GroupTokens - previous) * Kv;
            store_half(work_keys_.data() + previous * Kv, keys + current, cells);
            store_half(work_values_.data() + previous * Kv, values + current, cells);
            encode_group(slot * packed_rows_ + start);
        }
        const int residual_start = std::max(past, complete);
        if (const int remaining = end - residual_start) {
            const int offset = tail_offset + (residual_start - complete) * Kv;
            const int current = (residual_start - past) * Kv;
            store_half(tail_keys_.data() + offset, keys + current, remaining * Kv);
            store_half(tail_values_.data() + offset, values + current, remaining * Kv);
        }
    }

"""


def authority(seconds=0):
    if (OUT / "STOP").is_file():
        raise RuntimeError("Windows KV history diagnostic was stopped")
    win.authority(seconds)


def enable_trace(source):
    changes = (
        (b"#include <io.h>\n", b"#include <io.h>\n#include <memory>\n"),
        (b'        require(argc == 2, "expected a packed model path");',
         b'        require(argc == 2 || argc == 3, "expected a model and optional new trace path");'),
        (b"        const int logits_fd = -1;\n", b""),
        (b"        Runtime runtime(model, prefix + generate - 1, logits_fd >= 0);",
         b"""        const WinHandle trace(argc == 3 ? CreateFileW(argv[2], GENERIC_WRITE, 0,
            nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr) : nullptr);
        require(trace.value != INVALID_HANDLE_VALUE, "could not create exclusive logits trace");
        Runtime runtime(model, prefix + generate - 1, trace.value != nullptr);"""),
        (b"            if (logits_fd < 0 && ids[i] == 248044) break;",
         b"""            if (trace.value) {
                const DWORD bytes = static_cast<DWORD>(runtime.logits.size() * sizeof(float));
                DWORD written = 0;
                require(WriteFile(trace.value, runtime.logits.data(), bytes, &written, nullptr) &&
                        written == bytes, "incomplete logits trace");
            } else if (ids[i] == 248044) break;"""),
    )
    for before, after in changes:
        source = win.engine.replace(source, before, after)
    return source


def history_cache(source):
    source = win.span(source, b"    void restore(int slot,", b"private:\n", HISTORY_CACHE_METHODS)
    source = win.engine.replace(
        source, b"static void restore8(float* target,", b"static void restore8(uint16_t* target,")
    return win.engine.replace(source, b"_mm256_storeu_ps(target, _mm256_cvtph_ps(half));",
                              b"_mm_storeu_si128(reinterpret_cast<__m128i*>(target), half);")


def history_decoder(source):
    changes = (
        (b"struct Runtime {", HISTORY_HELPERS + b"struct Runtime {"),
        (b"""        : model(weights), capacity(capacity), x(std::min(PrefillTokens, capacity) * D), key(capacity * Kv),
          value(capacity * Kv), cache(capacity), logits(trace ? ActiveV : 0) {}""",
         b"""        : model(weights), capacity(capacity), x(std::min(PrefillTokens, capacity) * D),
          history_keys(new uint16_t[(capacity - 1) * Kv]), history_values(new uint16_t[(capacity - 1) * Kv]),
          cache(capacity), logits(trace ? ActiveV : 0) {}"""),
        (b"        return sizeof(*this) + (x.capacity() + key.capacity() + value.capacity() + logits.capacity()) * sizeof(float);",
         b"""        return sizeof(*this) + (x.capacity() + key.capacity() + value.capacity() + logits.capacity()) * sizeof(float)
               + 2 * (capacity - 1) * Kv * sizeof(uint16_t);"""),
        (b"        cache.restore(slot, past, key.data(), value.data());",
         b"""        if (key.size() != static_cast<size_t>(count * Kv)) {
            key = std::vector<float>(count * Kv);
            value = std::vector<float>(count * Kv);
        }
        cache.restore(slot, past, history_keys.get(), history_values.get());"""),
        (b"key.data() + (past + base) * Kv", b"key.data() + base * Kv"),
        (b"value.data() + (past + base) * Kv", b"value.data() + base * Kv"),
        (b"void attention(const float* q, float* output, int end)", b"void attention(const float* q, float* output, int end, int past)"),
        (b"""            for (int t = 0; t < end; ++t) {
                score[t] = dot(query, key.data() + t * Kv + offset, Head) * 0.125F;
                largest = std::max(largest, score[t]);
            }""",
         b"""            for (int t = 0; t < past; ++t) {
                score[t] = dot_history(query, history_keys.get() + t * Kv + offset) * 0.125F;
                largest = std::max(largest, score[t]);
            }
            for (int t = past; t < end; ++t) {
                score[t] = dot(query, key.data() + (t - past) * Kv + offset, Head) * 0.125F;
                largest = std::max(largest, score[t]);
            }"""),
        (b"""            for (int t = 0; t < end; ++t) {
                const __m256 prob = _mm256_set1_ps(score[t] / denom);
                const float* v = value.data() + t * Kv + offset;""",
         b"""            for (int t = 0; t < past; ++t) {
                const __m256 prob = _mm256_set1_ps(score[t] / denom);
                const uint16_t* v = history_values.get() + t * Kv + offset;
                for (int j = 0; j < Head / 8; ++j)
                    sums[j] = _mm256_fmadd_ps(prob, load_history8(v+j*8), sums[j]);
            }
            for (int t = past; t < end; ++t) {
                const __m256 prob = _mm256_set1_ps(score[t] / denom);
                const float* v = value.data() + (t - past) * Kv + offset;"""),
        (b"attention(query.data() + t*D, attn.data() + t*D, pos + 1);",
         b"attention(query.data() + t*D, attn.data() + t*D, pos + 1, past);"),
        (b"    GroupedInt8Cache cache;", b"    std::unique_ptr<uint16_t[]> history_keys, history_values;\n    GroupedInt8Cache cache;"),
    )
    for before, after in changes:
        source = win.engine.replace(source, before, after)
    return source


def compile_arm(root, out, lookup_source, source, cache):
    authority(65)
    root.mkdir()
    out.mkdir()
    source_path = root / "decoder.cpp"
    source_path.write_bytes(source)
    (root / win.CACHE.name).write_bytes(cache)
    (out / "decoder_at_execution.cpp").write_bytes(source)
    (out / win.CACHE.name).write_bytes(cache)
    return win.compile_decoder(source_path, lookup_source, root, out)


def model_file(name, source, prior_tmp, scratch, expected):
    packed = prior_tmp / f"{name}.packed"
    if not packed.is_file():
        packed = scratch / f"{name}.packed"
        win.export_model(name, source, expected, packed)
    if not packed.resolve().is_relative_to(Path("/tmp")) or io.digest(packed) != expected["sha256"]:
        raise ValueError(f"prior packed model differs for {name}")
    return packed


def compare_traces(control, candidate, model, requests, scratch, out):
    rows = []
    for prefix, steps, language in ((31, 3, "english"), (257, 2, "korean")):
        ids = requests[language]["ids"][:prefix]
        request = struct.pack(f"<{prefix + 2}I", prefix, steps, *ids)
        outputs = []
        raw = []
        for label, exe in (("control", control), ("candidate", candidate)):
            authority(26)
            path = scratch / f"trace_{prefix}_{label}.bin"
            result, elapsed = win.run_process([str(exe), win.win_path(model), win.win_path(path)], 24, data=request)
            trace = path.read_bytes() if path.is_file() else b""
            outputs.append(dict(arm=label, **win.record(result, elapsed),
                                bytes=len(trace), sha256=win.digest(trace)))
            raw.append(trace)
        size = steps * VOCAB * 4
        equal = raw[0] == raw[1] and len(raw[0]) == size and all(row["actual_exit"] == 0 for row in outputs)
        rows.append(dict(prefix=prefix, generated=steps, language=language,
                         request_sha256=win.digest(request), equal=equal, arms=outputs))
    io.write(out / "traces.json", rows)
    if not all(row["equal"] for row in rows):
        raise ValueError("the candidate differed at a grouped cache boundary")
    print("P109_WIN64_HALF_TRACES", len(rows), sum(row["generated"] for row in rows), flush=True)


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
    scratch = Path(tempfile.mkdtemp(prefix="p109_win64_half_", dir="/tmp"))
    previous = io.load(REFERENCE / "profile.json")
    previous_report = io.load(REFERENCE / "report.json")
    requests = io.load(gold.OUT / "profile.json")["requests"]
    prior_tmp = Path(previous["scratch"])
    if prior_tmp.parent != Path("/tmp") or not previous_report["all_ids_equal"]:
        raise ValueError("the previous Windows comparator is missing or invalid")
    source, cache = REFERENCE / "decoder_at_execution.cpp", REFERENCE / win.CACHE.name
    original, original_cache = source.read_bytes(), cache.read_bytes()
    if (win.digest(original) != previous["source_windows_sha256"] or
            win.digest(original_cache) != previous["cache_windows_sha256"]):
        raise ValueError("sealed Windows decoder or cache source differs")
    lookup = win.engine.LOOKUP.read_bytes() + b"\n" + win.engine.EXTENSION.read_bytes()
    if win.digest(lookup) != previous["lookup_sha256"]:
        raise ValueError("sealed AVX2 lookup differs")
    lookup_source = scratch / "avx2_lookup.cpp"
    lookup_source.write_bytes(lookup)
    plan = gold.PLAN
    (out / "plan_at_execution.md").write_bytes(plan.read_bytes())
    paths = [Path(__file__), Path(win.__file__), source, cache, plan, win.engine.LOOKUP,
             win.engine.EXTENSION, win.engine.SCALAR, REFERENCE / "profile.json",
             REFERENCE / "report.json", gold.OUT / "profile.json"]
    paths.extend(path for pair in gold.MODELS.values() for path in pair)
    pins = {str(path.relative_to(ROOT)): io.digest(path) for path in paths}
    for path, value in pins.items():
        if path in previous["inputs"] and path != str(plan.relative_to(ROOT)) and value != previous["inputs"][path]:
            raise ValueError(f"existing matched condition differs: {path}")
    io.write(out / "profile.json", dict(approval="WIP177", scratch=str(scratch), sources=pins,
             memories="native_windows_working_set", prefix=768, generate=256,
             comparator=str(REFERENCE.relative_to(ROOT)), prefill=256))
    original = enable_trace(original)
    control = compile_arm(scratch / "control", out / "control", lookup_source, original, original_cache)
    candidate = compile_arm(scratch / "candidate", out / "candidate", lookup_source,
                            history_decoder(original), history_cache(original_cache))
    win.check_guards(candidate, out)
    models = {name: model_file(name, asset, prior_tmp, scratch, previous["models"][name])
              for name, (asset, _) in gold.MODELS.items()}
    compare_traces(control, candidate, models["ce_48"], requests, scratch, out)
    rows = []
    baseline = {(row["model"], row["language"]): row for row in previous_report["requests"]}
    for name, model in models.items():
        for language, request in requests.items():
            authority(46)
            previous_row = baseline[name, language]
            row = win.measure(candidate, model, out, name, language,
                              request["ids"], previous_row["output"]["ids"])
            if row["actual_exit"] or row["prefix_ids_sha256"] != previous_row["prefix_ids_sha256"]:
                raise ValueError("a fixed Windows request failed or changed")
            measured = row["output"]
            previous_output = previous_row["output"]
            if any(measured[key] != previous_output[key] for key in ("model_bytes", "kv_bytes")):
                raise ValueError("the model payload or persistent KV size differed")
            baseline_peak = previous_output["complete"]["peak_working_set"]
            peak = measured["complete"]["peak_working_set"]
            rows.append(dict(model=name, language=language, ids_equal=row["all_ids_equal"],
                             peak=peak, baseline_peak=baseline_peak, saved=baseline_peak-peak,
                             seconds=row["seconds"], baseline_seconds=previous_row["seconds"],
                             first_token=measured["seconds"][0], tail_median=row["tail_32_median_seconds"]))
        if io.digest(model) != previous["models"][name]["sha256"]:
            raise ValueError("previous packed source changed")
    intact = all(io.digest(ROOT / path) == value for path, value in pins.items())
    ids_equal = len(rows) == 4 and all(row["ids_equal"] for row in rows)
    io.write(out / "report.json", dict(rows=rows, all_ids_equal=ids_equal, sources_intact=intact,
             candidate_pe_sha256=io.digest(candidate), control_pe_sha256=io.digest(control),
             target_bytes=40_000_000, peak=max(row["peak"] for row in rows),
             cuda_initialized=torch.cuda.is_initialized(), trace_bytewise_equal=True))
    if not ids_equal or not intact or torch.cuda.is_initialized():
        raise ValueError("Windows compressed history changed the generation contract")


if __name__ == "__main__":
    main()
