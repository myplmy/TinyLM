"""Verify the ICU/QBPE Windows tokenizer and measure complete 248K text requests."""

import argparse
import json
import os
from pathlib import Path
from statistics import median
import struct
import tempfile

import torch

from scripts import diag_p109_248k_win64_half_history as half
from scripts.p109_compact_qwen_tokenizer import CompactQwenTokenizer


win, io, gold, ROOT = half.win, half.io, half.gold, half.ROOT
OUT = half.OUT.with_name("p109_248k_win64_icu_text_v1_20261119")
CASE_DIR = gold.prior.TOKENIZER.parent
PACK = gold.prior.TOKENIZER
HALF = half.OUT / "attempt_01"
NATIVE = (ROOT / "scripts/p109_win64_qbpe.hpp", ROOT / "scripts/p109_win64_text_request.inc")
HEADER = struct.Struct("<8s5I")
MEMORY_TARGET = 40_000_000


def authority(seconds=0):
    if (OUT / "STOP").is_file():
        raise RuntimeError("Windows text request diagnostic was stopped")
    half.authority(seconds)


def archive_contract(pack):
    with pack.open("rb") as stream:
        magic, count, ordinary, rules, preprocessor, pieces = HEADER.unpack(stream.read(HEADER.size))
        offset = HEADER.size + (count + 1) * 4 + rules * 16
        if magic != b"TLQBPE1\0" or (count, ordinary) != (248066, 248044) or not 0 < preprocessor < 100000:
            raise ValueError("unknown QBPE layout")
        stream.seek(offset)
        spec = json.loads(stream.read(preprocessor))
    if pack.stat().st_size != offset + preprocessor + pieces:
        raise ValueError("incomplete QBPE layout")
    byte_level = dict(type="ByteLevel", add_prefix_space=False, trim_offsets=False, use_regex=False)
    split, level = spec["pre_tokenizer"]["pretokenizers"]
    if (spec["normalizer"] != {"type": "NFC"} or spec["pre_tokenizer"]["type"] != "Sequence" or
            level != byte_level or spec["decoder"] != byte_level or spec["post_processor"] != byte_level or
            split["type"] != "Split" or split["invert"] or split["behavior"] != "Isolated"):
        raise ValueError("unknown Qwen preprocessor")
    regex = split["pattern"]["Regex"]
    if not isinstance(regex, str) or not regex.isascii() or not regex.isprintable():
        raise ValueError("the generated native regex must be printable ASCII")
    added = sorted(spec["added_tokens"], key=lambda item: item["id"])
    if (len(added) != count - ordinary or [item["id"] for item in added] != list(range(ordinary, count)) or
            any(not item["content"] or not item["content"].isascii() or not item["content"].isprintable()
                or any(item[key] for key in ("lstrip", "rstrip", "normalized", "single_word")) for item in added)):
        raise ValueError("unknown Qwen added tokens")
    literal = set(range(33, 127)) | set(range(161, 173)) | set(range(174, 256))
    remapped = iter(range(256, 512))
    points = [byte if byte in literal else next(remapped) for byte in range(256)]
    raw_vocab = spec["model"]["vocab"]
    ids = [raw_vocab[chr(point)] for point in points]
    if set(ids) != set(range(256)):
        raise ValueError("unknown ByteLevel seed IDs")
    inverse = [-1] * (max(points) + 1)
    for byte, point in enumerate(points):
        inverse[point] = byte
    numbers = (
        ("Assigned", count), ("Ordinary", ordinary), ("Rules", rules),
        ("PreprocessorBytes", preprocessor), ("PieceBytes", pieces),
    )
    lines = [f"inline constexpr uint32_t {key} = {value};" for key, value in numbers]
    lines.append(f"inline constexpr wchar_t RegexPattern[] = L{json.dumps(regex)};")
    for kind, name, array in (("uint8_t", "ByteToId", ids), ("int16_t", "PointToByte", inverse)):
        lines.append(f"inline constexpr std::array<{kind}, {len(array)}> {name} = {{")
        for begin in range(0, len(array), 16):
            lines.append("    " + ", ".join(map(str, array[begin:begin + 16])) + ",")
        lines.append("};")
    lines.append(f"inline constexpr AddedToken Added[{len(added)}] = {{")
    for item in added:
        literal = json.dumps(item["content"])
        special = "true" if item["special"] else "false"
        lines.append(f'    {{{literal}, {item["id"]}, {special}}},')
    lines.append("};")
    return ("\n".join(lines) + "\n").encode("ascii")


def frame(text):
    data = text.encode("utf-8")
    if len(data) > 65536:
        raise ValueError("the saved text exceeds the native request limit")
    return struct.pack("<I", len(data)) + data


def check_tokenizer(exe, out, pack_path, profile):
    authority(30)
    cases_path = CASE_DIR / "cases.jsonl"
    if io.digest(cases_path) != profile["cases_sha256"]:
        raise ValueError("sealed tokenizer cases differ")
    cases = [json.loads(line) for line in cases_path.read_bytes().splitlines() if line]
    reference = io.load(CASE_DIR / "reference_0.json")["records"]
    raw, seconds = win.run_process([str(exe), "--tokenizer", pack_path], 26,
                                   data=b"".join(frame(text) for _, text in cases))
    rows = raw.stdout.splitlines() if raw.returncode == 0 else []
    if raw.returncode or len(rows) != len(cases):
        io.write(out / "tokenizer.json", dict(actual_exit=raw.returncode, expected=len(cases), actual=len(rows),
                 seconds=seconds, stderr=raw.stderr.decode("utf-8", "replace")))
        raise ValueError("native QBPE fixture process failed")
    mismatches = []
    tokens = 0
    with CompactQwenTokenizer(PACK) as codec:
        for (name, text), row, expected in zip(cases, rows, reference, strict=True):
            encoded = codec.encode(text)
            kept = codec.decode(encoded.ids, skip_special_tokens=False)
            stripped = codec.decode(encoded.ids, skip_special_tokens=True)
            original = dict(ids=encoded.ids, offsets=encoded.offsets, words=encoded.word_ids,
                            kept=kept, stripped=stripped)
            if expected["case"] != name or win.digest(json.dumps(
                    original, ensure_ascii=False, separators=(",", ":")).encode()) != expected["sha256"]:
                raise ValueError(f"WSL tokenizer no longer matches the archived original for {name}")
            actual = json.loads(row)
            fields = [k for k in ("ids", "kept", "stripped") if actual[k] != original[k]]
            if fields:
                mismatches.append(dict(case=name, fields=fields, expected_ids=encoded.ids, actual_ids=actual["ids"]))
            tokens += len(encoded.ids)
    io.write(out / "tokenizer.json", dict(cases=len(cases), tokens=tokens, mismatches=len(mismatches),
             first_differences=mismatches[:16], seconds=seconds, actual_exit=raw.returncode,
             raw_sha256=win.digest(raw.stdout)))
    print("P109_WIN64_QBPE_CASES", len(cases), tokens, len(mismatches), flush=True)
    if mismatches:
        raise ValueError("Windows QBPE differs from the pinned tokenizer fixtures")


def check_vocabulary(exe, out, pack_path):
    authority(30)
    raw, seconds = win.run_process([str(exe), "--vocab", pack_path], 26)
    rows = raw.stdout.splitlines() if raw.returncode == 0 else []
    mismatches = []
    with CompactQwenTokenizer(PACK) as codec:
        if raw.returncode == 0 and len(rows) == codec.size:
            for token, row in enumerate(rows):
                if json.loads(row) != codec.decode([token], skip_special_tokens=False):
                    mismatches.append(token)
        valid = raw.returncode == 0 and len(rows) == codec.size and not mismatches
    io.write(out / "vocabulary.json", dict(actual_exit=raw.returncode, assigned=len(rows),
             mismatches=len(mismatches), first_differences=mismatches[:16], seconds=seconds,
             raw_sha256=win.digest(raw.stdout), stderr=raw.stderr.decode("utf-8", "replace")))
    if not valid:
        raise ValueError("Windows QBPE single-token decoding differed")
    print("P109_WIN64_QBPE_VOCAB", len(rows), flush=True)


def check_guards(exe, out, pack_path):
    cases = (("steps", "257", frame("A"), "unsupported generation limit"),
             ("oversize", "1", struct.pack("<I", 65537), "invalid UTF-8 request frame"),
             ("truncated", "1", struct.pack("<I", 3) + b"x", "truncated UTF-8 request"),
             ("invalid_utf8", "1", struct.pack("<I", 1) + b"\xff", "invalid UTF-8 input"),
             ("empty", "1", frame(""), "unsupported tokenized request shape"))
    rows = []
    for kind, steps, request, expected in cases:
        authority(10)
        raw, seconds = win.run_process([str(exe), "invalid-model-path", pack_path, steps], 8, data=request)
        record = win.record(raw, seconds)
        rows.append(dict(case=kind, matched=raw.returncode == 1 and expected in record["stderr"], **record))
    io.write(out / "guards.json", rows)
    if not all(row["matched"] for row in rows):
        raise ValueError("native text request did not reject invalid input before model mapping")


def measure(exe, out, model, pack_path, name, language, prompt):
    authority(46)
    reference = io.load(gold.OUT / f"request_{name}_{language}_1.json")
    data = frame(prompt["text"])
    raw, seconds = win.run_process([str(exe), win.win_path(model), pack_path, str(gold.GENERATE)], 44, data=data)
    row = dict(model=name, language=language, native_seconds=seconds, request_sha256=win.digest(data),
               **win.record(raw, seconds))
    if raw.returncode == 0:
        actual = json.loads(raw.stdout)
        memory = actual["finished"]["peak_working_set"]
        row.update(output=actual, ids_equal=actual["input_ids"] == prompt["ids"] == reference["encoding"]["ids"],
                   tokens_equal=actual["ids"] == reference["native"]["ids"],
                   decoded_equal=actual["decoded"] == reference["decoding"]["text"],
                   finish_equal=actual["finish"] == reference["decoding"]["finish"],
                   resource_shapes_equal=all(actual[k] == reference["native"][k] for k in ("model_bytes", "kv_bytes")),
                   peak_bytes=memory, tail_median_seconds=median(actual["seconds"][-32:]))
    io.write(out / f"request_{name}_{language}.json", row)
    print("P109_WIN64_TEXT_REQUEST", name, language, raw.returncode, row.get("peak_bytes"), round(seconds, 3), flush=True)
    return row


@torch.inference_mode()
def main():
    options = argparse.ArgumentParser(description=__doc__)
    options.add_argument("--attempt", type=int, default=1)
    args = options.parse_args()
    if args.attempt < 1 or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        options.error("a positive attempt number and isolated CPU are required")
    authority(250)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    out = OUT / f"attempt_{args.attempt:02d}"
    out.mkdir(parents=True)
    build = Path(tempfile.mkdtemp(prefix="p109_win64_icu_", dir="/tmp"))
    profile = io.load(CASE_DIR / "profile.json")
    original_profile = io.load(half.REFERENCE / "profile.json")
    if io.digest(PACK) != profile["compact_sha256"]:
        raise ValueError("frozen QBPE file differs")
    references = io.load(gold.OUT / "profile.json")["requests"]
    base = HALF / "candidate" / "decoder_at_execution.cpp"
    cache = HALF / "candidate" / win.CACHE.name
    windows = (half.REFERENCE / "decoder_at_execution.cpp").read_bytes()
    if base.read_bytes() != half.history_decoder(half.enable_trace(windows)):
        raise ValueError("verified half-history decoder differs")
    if cache.read_bytes() != half.history_cache((half.REFERENCE / win.CACHE.name).read_bytes()):
        raise ValueError("verified half-history cache differs")
    decoder = base.read_bytes().split(b"int wmain(int argc, wchar_t** argv) {")
    if len(decoder) != 2:
        raise ValueError("Windows decoder entry point changed")
    lookup = win.engine.LOOKUP.read_bytes() + b"\n" + win.engine.EXTENSION.read_bytes()
    if win.digest(lookup) != original_profile["lookup_sha256"]:
        raise ValueError("same AVX2 lookup unavailable")
    lookup_file = build / "avx2_lookup.cpp"
    lookup_file.write_bytes(lookup)
    generated = {
        "decoder.cpp": decoder[0] + b'#include "p109_win64_text_request.inc"\n',
        "p109_win64_qbpe_contract.inc": archive_contract(PACK),
        win.CACHE.name: cache.read_bytes(),
        **{path.name: path.read_bytes() for path in NATIVE},
    }
    for name, data in generated.items():
        (build / name).write_bytes(data)
        (out / name).write_bytes(data)
    files = [Path(__file__), *NATIVE, gold.PLAN, PACK, CASE_DIR / "profile.json", CASE_DIR / "cases.jsonl",
             CASE_DIR / "reference_0.json", base, cache, half.REFERENCE / "profile.json",
             gold.OUT / "profile.json", win.engine.SCALAR, win.engine.LOOKUP, win.engine.EXTENSION]
    files.extend(gold.OUT / f"request_{name}_{language}_1.json" for name in gold.MODELS for language in references)
    pins = {str(path.relative_to(ROOT)): io.digest(path) for path in files}
    (out / "plan_at_execution.md").write_bytes(gold.PLAN.read_bytes())
    io.write(out / "profile.json", dict(approval="WIP177", scratch=str(build), inputs=pins,
             generated={name: win.digest(data) for name, data in generated.items()},
             models=original_profile["models"], input_tokens=gold.PREFIX, generation_cap=gold.GENERATE,
             target_bytes=MEMORY_TARGET))
    exe = win.compile_decoder(build / "decoder.cpp", lookup_file, build, out)
    pack_path = win.win_path(PACK)
    check_tokenizer(exe, out, pack_path, profile)
    check_vocabulary(exe, out, pack_path)
    check_guards(exe, out, pack_path)
    prior_tmp = Path(original_profile["scratch"])
    if prior_tmp.resolve().parent != Path("/tmp"):
        raise ValueError("the existing packed exports are outside scratch")
    rows = []
    for name, (asset, _) in gold.MODELS.items():
        expected = original_profile["models"][name]
        model = half.model_file(name, asset, prior_tmp, build, expected)
        for language, prompt in references.items():
            rows.append(measure(exe, out, model, pack_path, name, language, prompt))
        if io.digest(model) != expected["sha256"]:
            raise ValueError("the existing packed file changed")
    intact = all(io.digest(ROOT / path) == value for path, value in pins.items())
    matched = len(rows) == 4 and all(all(row.get(key) for key in (
        "ids_equal", "tokens_equal", "decoded_equal", "finish_equal", "resource_shapes_equal",
    )) for row in rows)
    peak = max((row["peak_bytes"] for row in rows if "peak_bytes" in row), default=None)
    io.write(out / "report.json", dict(requests=rows, sources_intact=intact, full_match=matched,
             peak=peak, target_bytes=MEMORY_TARGET, candidate_pe_sha256=io.digest(exe),
             cuda_initialized=torch.cuda.is_initialized()))
    if not matched or not intact or torch.cuda.is_initialized():
        raise ValueError("the Windows full text contract differed")


if __name__ == "__main__":
    main()
