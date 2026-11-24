"""Reduce the compact G4 prefill workspace and check complete text requests."""

from contextlib import ExitStack
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
from time import perf_counter

import numpy as np
import torch

from scripts import diag_p109_g4_native_int8_cache as prior


base, text, token, ROOT = prior.base, prior.text, prior.token, prior.ROOT
TAG = "p109_g4_bounded_prefill_v1_20261119"
OUT = prior.OUT.with_name(TAG)
LIMIT = 320
TEXT_ORDER = (1024, 256, 64, 64, 256)
ANCHORS = (
    (b"struct Runtime {", b"constexpr int PrefillTokens = P109_PREFILL_TOKENS;\n\nstruct Runtime {"),
    (b"explicit Runtime(const Model& weights, int capacity)",
     b"explicit Runtime(const Model& weights, int capacity, bool trace)"),
    (b"x(capacity * D)", b"x(std::min(PrefillTokens, capacity) * D)"),
    (b"value(capacity * Kv), cache(capacity) {}", b"value(capacity * Kv), cache(capacity), logits(trace ? V : 0) {}"),
    (b"(x.capacity() + key.capacity() + value.capacity()) * sizeof(float)",
     b"(x.capacity() + key.capacity() + value.capacity() + logits.capacity()) * sizeof(float)"),
    (b"uint32_t next(const uint32_t* tokens, int count, int past) {",
     b"uint32_t next(const uint32_t* tokens, int count, int past, bool emit = true) {\n"
     b"        require(count <= PrefillTokens, \"prefill exceeds allocated tile\");"),
    (b"        normalize(norm.data(), x.data() + (count - 1)*D, D);",
     b"        if (!emit) return 0;\n        normalize(norm.data(), x.data() + (count - 1)*D, D);"),
    (b"        for (int token = 0; token < V; ++token) {",
     b"        float best_score = -INFINITY;\n        uint32_t best_id = 0;\n"
     b"        for (int token = 0; token < V; ++token) {"),
    (b"            logits[token] = reduce(total);\n"
     b"            require(std::isfinite(logits[token]), \"nonfinite output\");\n        }\n"
     b"        return static_cast<uint32_t>(std::max_element(logits.begin(), logits.end()) - logits.begin());",
     b"            const float score = reduce(total);\n"
     b"            require(std::isfinite(score), \"nonfinite output\");\n"
     b"            if (!logits.empty()) logits[token] = score;\n"
     b"            if (score > best_score) {\n                best_score = score;\n"
     b"                best_id = static_cast<uint32_t>(token);\n            }\n        }\n        return best_id;"),
    (b"std::array<float, V> logits{};", b"std::vector<float> logits;"),
    (b"const std::array<float,V>& scores", b"const std::vector<float>& scores"),
    (b"Runtime runtime(model, prefix + generate - 1);", b"Runtime runtime(model, prefix + generate - 1, logits_fd >= 0);"),
    (b"            ids[i] = i == 0 ? runtime.next(tokens.data(), prefix, 0)\n"
     b"                            : runtime.next(&ids[i-1], 1, prefix + i - 1);",
     b"            if (i == 0) {\n"
     b"                uint32_t offset = 0;\n"
     b"                for (; prefix - offset > static_cast<uint32_t>(PrefillTokens); offset += PrefillTokens)\n"
     b"                    runtime.next(tokens.data() + offset, PrefillTokens, offset, false);\n"
     b"                ids[i] = runtime.next(tokens.data() + offset, prefix - offset, offset);\n"
     b"            } else {\n                ids[i] = runtime.next(&ids[i-1], 1, prefix + i - 1);\n            }"),
)


def render(origin):
    source = origin
    for before, after in ANCHORS:
        assert source.count(before) == 1, before
        source = source.replace(before, after, 1)
    return source


def build(source, *, caps=(1024, 256, 64)):
    folder = Path(tempfile.mkdtemp(prefix="p109_bounded_prefill_", dir="/tmp"))
    scalar, fast = (str(folder / n) for n in ("scalar.o", "avx2.o"))
    flags = ["-std=c++17", "-O3", "-mavx2", "-mfma", "-mf16c", "-ffp-contract=off", "-Werror",
             "-Wall", "-Wextra", "-I", str(ROOT / "scripts")]
    commands = []

    def call(args, source_data=None):
        subprocess.run(args, input=source_data, cwd=ROOT, timeout=80, check=True)
        commands.append(args)

    call(["/usr/bin/gcc", "-std=c11", "-O3", "-Wall", "-Wextra", "-Werror",
          "-Dp014e_cpu_lookup=p014e_scalar_lookup", "-c", base.C, "-o", scalar])
    call(["/usr/bin/g++", *flags, "-c", prior.avx.LOOKUP, "-o", fast])
    versions = {}
    driver = b"int run_compact_g4(int, char**);\nint main(int n, char** a) { return run_compact_g4(n, a); }\n"
    for cap in caps:
        obj, num, full = (str(folder / f"{cap}_{suffix}") for suffix in ("core.o", "num", "text"))
        call(["/usr/bin/g++", *flags, f"-DP109_PREFILL_TOKENS={cap}", "-Dmain=run_compact_g4", "-x", "c++", "-",
              "-c", "-o", obj], source)
        call(["/usr/bin/g++", *flags, "-x", "c++", "-", "-x", "none", obj, fast, scalar, "-static", "-o", num], driver)
        call(["/usr/bin/g++", *flags, text.WRAPPER, obj, fast, scalar, "-static", "-o", full])
        versions[cap] = (num, full)
    binaries = {str(k):[{"path": x, "sha256": base.SHA(Path(x))} for x in paths] for k, paths in versions.items()}
    assert all("INTERP" not in subprocess.check_output(["/usr/bin/readelf", "-l", x], text=True)
               for paths in versions.values() for x in paths)
    base.WRITE(OUT / "compiler.json", dict(commands=commands, binaries=binaries,
               source_sha256=sha256(source).hexdigest().upper()))
    return versions


def compare(name, limit, reference, candidate):
    left, left_scores = reference
    right, right_scores = candidate
    assert left["model_bytes"] == right["model_bytes"] and left["kv_bytes"] == right["kv_bytes"]
    errors, same_history = [], True
    for a, b, p, q in zip(left["ids"], right["ids"], left_scores, right_scores, strict=True):
        if same_history:
            errors.append(float(np.abs(p-q).max()))
        same_history = same_history and a == b
    row = dict(name=name, prefill_limit=limit, same_ids=same_history, differences=errors,
        max_abs_same_history=max(errors), bit_equal_prefill=bool(np.array_equal(left_scores[0], right_scores[0])),
        reference_ids=left["ids"], candidate_ids=right["ids"], first_seconds=right["seconds"][0],
        scratch_with_trace=right["scratch_bytes"])
    print("P109_BOUNDED_PREFILL_NUM", row, flush=True)
    return row


def request(binary, cap, assets, payload, reference, language, index):
    with ExitStack() as stack:
        extra = tuple(base.memfile(f"g4_bounded_prefill_{i}") for i in range(3))
        for item in extra:
            stack.callback(os.close, item)
        fds = (*assets, *extra)
        cmd = [sys.executable, "-I", "-S", "-B", "-X", "utf8", str(ROOT / text.SCRIPT),
               "encode", binary, *map(str, fds)]
        start = perf_counter()
        proc = subprocess.run(cmd, input=payload, pass_fds=fds, capture_output=True, timeout=180)
        elapsed = perf_counter()-start
        if proc.returncode:
            print(proc.stderr.decode("utf-8", "replace"), file=sys.stderr, flush=True)
            proc.check_returncode()
    report = json.loads(proc.stdout)
    base.WRITE(OUT / f"{language}_{index}_request.json", report)
    assert report["encoding"]["pid"] == report["native_pid"] == report["decoding"]["pid"]
    assert reference["encoding"]["ids"] == report["encoding"]["ids"]
    assert report["native"]["model_bytes"] == reference["native"]["model_bytes"]
    assert report["native"]["kv_bytes"] == prior.int8_capacity(len(report["encoding"]["ids"])+text.GEN-1)
    expected_scratch = 5_117_168 - (1024-cap)*768*4 - 32768*4 + 24
    assert report["native"]["scratch_bytes"] == expected_scratch
    row = dict(language=language, cap=cap, index=index, peak_rss=prior.peak(report), seconds=elapsed,
        first_seconds=report["native"]["seconds"][0], scratch_bytes=report["native"]["scratch_bytes"],
        ids_equal=report["native"]["ids"] == reference["native"]["ids"],
        text_equal=report["decoding"]["text"] == reference["decoding"]["text"])
    print("P109_BOUNDED_PREFILL_TEXT", row, flush=True)
    return row


@torch.inference_mode()
def main():
    cutoff = base.prior.ORIGIN.CUTOFF
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=LIMIT+20) < cutoff
    old_profile, old_receipt, old_compile = (prior.OUT / f"{n}.json" for n in ("profile", "report", "compiler"))
    old = base.READ(old_profile)
    assert base.READ(old_receipt)["profile_sha256"] == base.SHA(old_profile)
    assert all(base.SHA(ROOT / p)==h for p,h in old["sources"].items())
    codec_profile, codec = (base.READ(token.OUT / f"{n}.json") for n in ("profile", "report"))
    text_profile = base.READ(text.OUT / "profile.json")
    text_report = base.READ(text.OUT / "report.json")
    assert base.SHA(text.OUT / "report.json") == old["reference_report"]
    assert base.SHA(token.OUT / "report.json") == text_profile["tokenizer_reference"]
    source_tokenizer = token.TOK.read_bytes()
    assert sha256(source_tokenizer).hexdigest().upper() == codec_profile["source_sha256"]
    tokenizer_wire = token.wire(json.loads(source_tokenizer))
    assert [sha256(b).hexdigest().upper() for b in tokenizer_wire] == [
        v["sha256"] for v in codec_profile["files"]["split_model"]]
    origin = (ROOT / base.CPP).read_bytes().replace(prior.avx.tile.ORIGINAL, prior.avx.tile.CHANGED, 1)
    source = prior.render(origin)
    compiler = base.READ(old_compile)
    assert sha256(source).hexdigest().upper() == compiler["rendered_sha256"]["int8"]
    ref_binary = Path(compiler["binaries"]["int8"]["path"])
    assert ref_binary.is_relative_to(Path("/tmp")) and base.SHA(ref_binary) == compiler["binaries"]["int8"]["sha256"]
    pins = base.pins()
    assert pins == text_profile["pins"]
    os.sched_setaffinity(0, {old["cpu"]})
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    OUT.mkdir(exist_ok=False)
    self_sha = base.SHA(Path(__file__))
    base.WRITE(OUT / "profile.json", dict(tag=TAG, script_sha256=self_sha, previous_profile=base.SHA(old_profile),
        previous_report=base.SHA(old_receipt), previous_compile=base.SHA(old_compile), cpu=old["cpu"],
        reference_numeric=base.SHA(ref_binary), text_order=list(TEXT_ORDER), bound_seconds=LIMIT))
    variants = build(render(source))
    refs = {row["case"]:row for row in text_report["runs"]}
    texts = codec["runs"]["split_model"][0]["outputs"]
    with ExitStack() as stack:
        def fd(label):
            result = base.memfile(label)
            stack.callback(os.close, result)
            return result

        model_fd = fd("g4_bounded_prefill_model")
        model = base.prior.load_candidate(pins["candidate"])
        artifact = base.model_blob(model, model_fd, pins["candidate"]["model_tensor_bytes"])
        del model
        assert artifact == text_report["source"]
        vocab, merges = (fd("g4_bounded_" + name) for name in ("vocab", "merges"))
        for desc, blob in zip((vocab, merges), tokenizer_wire, strict=True):
            text.store(desc, blob)
            fcntl.fcntl(desc, base.prior.DEPLOY.F_ADD_SEALS, base.prior.DEPLOY.SEALS)
            assert fcntl.fcntl(desc, base.prior.DEPLOY.F_GET_SEALS) == base.prior.DEPLOY.SEALS
        short = refs["english"]["encoding"]["ids"][:65]
        numeric = [compare("stream_65", 1024, prior.numeric(ref_binary, model_fd, short),
                           prior.numeric(variants[1024][0], model_fd, short))]
        assert numeric[0]["max_abs_same_history"] == 0 and numeric[0]["same_ids"]
        runs = []
        for lang in ("english", "korean"):
            ref = refs[lang]
            ids = ref["encoding"]["ids"]
            unchunked = prior.numeric(ref_binary, model_fd, ids)
            for cap in (256, 64):
                numeric.append(compare(lang, cap, unchunked, prior.numeric(variants[cap][0], model_fd, ids)))
            payload = texts[lang]["decoded"].encode("utf-8")
            for index, cap in enumerate(TEXT_ORDER):
                runs.append(request(variants[cap][1], cap, (model_fd, vocab, merges), payload, ref, lang, index))
    summary = {}
    for cap in (1024, 256, 64):
        rows = [r for r in runs if r["cap"] == cap]
        summary[str(cap)] = dict(peak_rss=max(r["peak_rss"] for r in rows), outputs_equal=all(r["text_equal"] and r["ids_equal"] for r in rows),
            wall_by_language={l: median(r["seconds"] for r in rows if r["language"] == l) for l in ("english", "korean")})
    assert not torch.cuda.is_initialized() and base.pins() == pins
    assert base.SHA(Path(__file__)) == self_sha and all(base.SHA(ROOT / p)==h for p,h in old["sources"].items())
    base.WRITE(OUT / "report.json", dict(numeric=numeric, runs=runs, summary=summary,
        profile_sha256=base.SHA(OUT / "profile.json"), checkpoint_writes=0))


if __name__ == "__main__":
    main()
