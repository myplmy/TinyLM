"""Verify a compact local 248K Qwen tokenizer against the pinned Rust tokenizer."""

from contextlib import nullcontext
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import random
from struct import pack as struct_pack
import subprocess
import sys
import sysconfig
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
TAG = "p109_compact_qwen_tokenizer_v1_20261119"
OUT = ROOT / "test_result/evidence" / TAG
ASSET = ROOT / "test_result/evidence/p106b_qwen_bonsai_tokenizer_map_v1_20261119/report.json"
AUTHORED = ROOT / "test_result/evidence/p106b_p109_actual_prefix_kd_v1_20261119/profile.json"
LONG = ROOT / "test_result/evidence/p109_g4_bytelevel_budget_v2_20261119/report.json"
CODEC = Path(__file__).with_name("p109_compact_qwen_tokenizer.py")


def digest(path):
    result = sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1 << 20), b""):
            result.update(part)
    return result.hexdigest().upper()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write(chr(10))


def snapshot():
    with open("/proc/self/status", encoding="ascii") as stream:
        high_water = next(int(row.split()[1]) * 1024 for row in stream if row.startswith("VmHWM:"))
    with open("/proc/self/smaps_rollup", encoding="ascii") as stream:
        rss = next(int(row.split()[1]) * 1024 for row in stream if row.startswith("Rss:"))
    return dict(hwm=high_water, rss=rss)


def vocab_check(tokenizer, size):
    value = sha256()
    for token_id in range(size):
        piece = tokenizer.id_to_token(token_id).encode("utf-8")
        value.update(struct_pack("<2I", token_id, len(piece)))
        value.update(piece)
    return dict(count=size, sha256=value.hexdigest().upper(),
                unassigned_decodes_empty=tokenizer.decode(list(range(size, 248320)), skip_special_tokens=False) == "")


def worker(mode, asset, cases, scope, output):
    start = snapshot()
    sys.path.append(sysconfig.get_path("purelib"))
    sys.path.append(str(CODEC.parent))
    from tokenizers import Tokenizer
    from p109_compact_qwen_tokenizer import CompactQwenTokenizer

    imported = snapshot()
    begin = perf_counter()
    if mode == "mapped":
        context = CompactQwenTokenizer(asset)
    else:
        context = nullcontext(Tokenizer.from_file(asset))
    with context as codec:
        seconds = perf_counter() - begin
        loaded = snapshot()
        size = codec.size if mode == "mapped" else codec.get_vocab_size()
        records = None
        check_seconds = 0.
        if scope == "vocab":
            result = vocab_check(codec, size)
        else:
            records = []
            with open(cases, encoding="utf-8") as stream:
                for line in stream:
                    name, text = json.loads(line)
                    t0 = perf_counter()
                    encoded = codec.encode(text) if mode == "mapped" else codec.encode(text, add_special_tokens=False)
                    kept = codec.decode(encoded.ids, skip_special_tokens=False)
                    stripped = codec.decode(encoded.ids, skip_special_tokens=True)
                    check_seconds += perf_counter() - t0
                    fields = dict(ids=encoded.ids, offsets=encoded.offsets, words=encoded.word_ids,
                                  kept=kept, stripped=stripped)
                    records.append(dict(case=name, tokens=len(encoded.ids), sha256=sha256(
                        json.dumps(fields, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    ).hexdigest().upper()))
            result = dict(cases=len(records), tokens=sum(row["tokens"] for row in records))
        complete = snapshot()
    result.update(assigned=size, mode=mode, scope=scope, load_seconds=seconds, codec_seconds=check_seconds,
                  history=dict(start=start, imported=imported, loaded=loaded, complete=complete),
                  peak=max(val for phase in (start, imported, loaded, complete) for val in phase.values()), records=records)
    write(output, result)
    print("TOKENIZER_WORKER", mode, scope, result["peak"], result.get("cases", size), flush=True)


def battery(config):
    authored = load(AUTHORED)["data"]["documents"]
    for row in authored:
        yield "authored_" + row["id"], row["text"]
    report = load(LONG)
    text = report["runs"]["split_model"][0]["outputs"]
    for name in ("english", "korean"):
        yield "long_" + name, text[name]["decoded"]
    for item in config["added_tokens"]:
        special = item["content"]
        for index, value in enumerate((special, "x" + special + "한글", "  " + special + "\r\n" + special + "x")):
            yield f"added_{item['id']}_{index}", value
    pool = (
        "", "\x00", "\t\r\n", "the\r\nquick\rbrown\nfox", "  multiple   spaces  ", "aaaaaaa rrttt",
        "cafe\u0301 caf\u00e9", "a\u0315\u0300 a\u0300\u0315", "a\u0301\u0327 \u00df\u00c5\u212b",
        "\u1100\u1161\u11a8 각 \u110b\u1161\u11ab", "안녕하세요 한글 문장을 읽고 있습니다.",
        "\u200d\ufe0f\U0001f469\U0001f3fd\u200d\U0001f4bb", "\u2028\u2029\u00a0\u202f\u200b",
        "<|im_start|>user\n이 숫자는 123456입니다.<|im_end|>\n<|im_start|>assistant\n",
        "(A) cafe\u0301 (B) caf\u00e9\t0102: \u00b2 + \u0967 + １２３",
        "I'M we're I'll wasn't she'd re-entry XYZ. 신호—새 단어…", "x" * 513, " " * 513,
    )
    for index, value in enumerate(pool):
        yield f"edge_{index}", value
    rng = random.Random(6899)
    fragments = (*pool[:16], "-", " ABC", "　", "너와 나", "0", "_", "<|im_end|>")
    for index in range(192):
        yield f"combination_{index}", "".join(rng.choices(fragments, k=2 + index % 8))


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    cutoff = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=300) < cutoff
    asset = load(ASSET)["assets"]["qwen35_hf"]
    source = ROOT / asset["path"]
    assert digest(source) == asset["file_sha256"]
    sys.path.append(str(CODEC.parent))
    from p109_compact_qwen_tokenizer import pack

    sources = {str(path.relative_to(ROOT)): digest(path) for path in (ASSET, AUTHORED, LONG, CODEC, Path(__file__))}
    OUT.mkdir(exist_ok=False)
    compact, cases = OUT / "qwen.qbpe", OUT / "cases.jsonl"
    start = perf_counter()
    pack(source, compact)
    pack_time = perf_counter() - start
    fixture = list(battery(load(source)))
    assert len({k for k, _ in fixture}) == len(fixture)
    with cases.open("x", encoding="utf-8") as stream:
        for row in fixture:
            stream.write(json.dumps(row, ensure_ascii=False) + chr(10))
    profile = dict(tag=TAG, sources=sources, original_sha256=asset["file_sha256"], compact_sha256=digest(compact),
        original_bytes=source.stat().st_size, compact_bytes=compact.stat().st_size, cases_sha256=digest(cases),
        directed_cases=len(fixture), build_seconds=pack_time, physical_head_rows=asset["physical_rows"])
    write(OUT / "profile.json", profile)
    reports = {}
    for mode, path in (("reference", source), ("mapped", compact)):
        for index, scope in enumerate(("battery", "battery", "vocab")):
            key = f"{mode}_{index}"
            report = OUT / f"{key}.json"
            command = [sys.executable,"-I","-S","-B","-X","utf8",str(Path(__file__)),"worker",
                       mode,str(path),str(cases),scope,str(report)]
            subprocess.run(command, cwd=ROOT, timeout=50, check=True)
            reports[key] = load(report)
    expected = reports["reference_0"]["records"]
    observed = reports["mapped_0"]["records"]
    mismatch = [left["case"] for left, right in zip(expected, observed, strict=True) if left != right]
    repeated = (reports["reference_1"]["records"] == expected and reports["mapped_1"]["records"] == observed)
    vocab_equal = reports["reference_2"]["sha256"] == reports["mapped_2"]["sha256"]
    assert all(report["assigned"] == asset["id_count"] for report in reports.values())
    assert repeated and all(reports[f"{name}_2"]["unassigned_decodes_empty"] for name in ("reference", "mapped"))
    assert digest(source) == profile["original_sha256"] and digest(compact) == profile["compact_sha256"]
    assert all(digest(ROOT / path) == sh for path, sh in sources.items())
    peaks = {mode: max(reports[f"{mode}_{i}"]["peak"] for i in (0, 1)) for mode in ("reference", "mapped")}
    write(OUT / "report.json", dict(case_count=len(expected), mismatches=mismatch, full_vocabulary_match=vocab_equal,
        peaks=peaks, vocabulary_scan_peak=reports["mapped_2"]["peak"], profile_sha256=digest(OUT / "profile.json"),
        reference_seconds=reports["reference_0"]["codec_seconds"], mapped_seconds=reports["mapped_0"]["codec_seconds"],
        weights_loaded=0, checkpoints_written=0))
    print("P109_QWEN_COMPACT", len(expected), len(mismatch), vocab_equal, peaks, flush=True)
    return 0 if not mismatch and vocab_equal and peaks["mapped"] <= 40_000_000 else 8


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        worker(*sys.argv[2:])
    else:
        sys.exit(main())
