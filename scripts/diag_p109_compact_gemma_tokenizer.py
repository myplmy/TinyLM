"""Test the existing 262K student tokenizer in the mapped BPE format."""

from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from scripts import diag_p109_compact_qwen_tokenizer as evidence
from scripts.p109_compact_qwen_tokenizer import HEADER, MAGIC, MERGE, OFFSET


ROOT = evidence.ROOT
TAG = "p109_compact_gemma_tokenizer_v1_20261119"
OUT = evidence.OUT.with_name(TAG)
PROFILE = ROOT / "handoff/audit/oct27_independent/large_vocab_deploy_profile_v4.json"
WORKER = Path(evidence.__file__)


def pack_gemma(config, path):
    model = config["model"]
    if (model["type"] != "BPE" or model["dropout"] is not None or not model["byte_fallback"]
            or model["ignore_merges"] or model["continuing_subword_prefix"] or model["end_of_word_suffix"]
            or config["truncation"] is not None or config["padding"] is not None):
        raise ValueError("unsupported Gemma BPE layout")
    vocabulary = model["vocab"]
    added = {row["content"]: row["id"] for row in config["added_tokens"]}
    for piece,id_ in added.items():
        if piece in vocabulary and vocabulary[piece] != id_:
            raise ValueError("added token ID disagrees with the base vocabulary")
    all_ids = vocabulary | added
    if set(all_ids.values()) != set(range(len(all_ids))) or len(vocabulary) != 262144:
        raise ValueError("unexpected Gemma vocabulary layout")
    fallback = {f"<0x{i:02X}>" for i in range(256)} | {model["unk_token"]}
    assert fallback <= vocabulary.keys()
    seed = {piece: id_ for piece, id_ in vocabulary.items() if len(piece) == 1 or piece in fallback}
    scaffold = dict(config, model=dict(model,vocab=seed | added,merges=[]))
    small_json = json.dumps(scaffold,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode("utf-8")
    entries = sorted(all_ids.items(),key=lambda pair:pair[1])
    pieces = bytearray()
    offsets = bytearray(OFFSET.pack(0))
    for piece,_ in entries:
        pieces.extend(piece.encode("utf-8"))
        offsets.extend(OFFSET.pack(len(pieces)))
    rules = sorted(((vocabulary[a]<<32) | vocabulary[b],rank,vocabulary[a+b])
                   for rank,(a,b) in enumerate(model["merges"]))
    if any(a[0] == b[0] for a,b in zip(rules,rules[1:])):
        raise ValueError("duplicate Gemma merge pair")
    with Path(path).open("xb") as output:
        output.write(HEADER.pack(MAGIC,len(entries),len(vocabulary),len(rules),len(small_json),len(pieces)))
        output.write(offsets)
        for row in rules:
            output.write(MERGE.pack(*row))
        output.write(small_json)
        output.write(pieces)
    return dict(characters=len(seed)-len(fallback),added=len(added),merged=len(rules),scaffold_bytes=len(small_json),
                physically_outside=[i for i in sorted(added.values()) if i >= len(vocabulary)])


def run():
    cutoff = datetime.fromisoformat("2026-11-19T16:58:00+09:00")
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert datetime.now(cutoff.tzinfo) + timedelta(seconds=320) < cutoff
    asset = evidence.load(PROFILE)["tokenizer"]
    source = ROOT / asset["path"]
    assert evidence.digest(source) == asset["sha256"]
    config = evidence.load(source)
    sources = {str(p.relative_to(ROOT)): evidence.digest(p) for p in (PROFILE,WORKER,evidence.CODEC,
        evidence.AUTHORED,evidence.LONG,Path(__file__))}
    OUT.mkdir(exist_ok=False)
    compact, cases = OUT / "gemma.qbpe", OUT / "cases.jsonl"
    start = perf_counter()
    structure = pack_gemma(config,compact)
    build_seconds = perf_counter()-start
    chosen = [row for i,row in enumerate(config["added_tokens"]) if i%64==0 or row["special"] or i<24]
    fixtures = list(evidence.battery(dict(config,added_tokens=chosen)))
    fixtures.extend((
        ("turn_markers","<start_of_turn>user\n오늘의 답은 42입니다.<end_of_turn>\n<start_of_turn>model\n"),
        ("three_bos","<bos>가<bos>나<bos>"),
        ("outside_guard","<image_soft_token>뒤의 문장"),
        ("byte_fallback_a","\U0001fae8\U0001f9cc\U000f0000\U0010fffc\u200d\u00e9"),
        ("byte_fallback_b","A\U0010ffffB가\ufffd\u0000"),
    ))
    with cases.open("x",encoding="utf-8") as stream:
        for row in fixtures:
            stream.write(json.dumps(row,ensure_ascii=False)+chr(10))
    profile = dict(tag=TAG,sources=sources,source_tokenizer_sha256=asset["sha256"],source_bytes=source.stat().st_size,
        compact_bytes=compact.stat().st_size,compact_sha256=evidence.digest(compact),build_seconds=build_seconds,
        cases_sha256=evidence.digest(cases),sampled_added_rules=len(chosen),structure=structure)
    evidence.write(OUT / "profile.json",profile)
    reports = {}
    for mode,path in (("reference",source),("mapped",compact)):
        for index,scope in enumerate(("battery","battery","vocab")):
            key = f"{mode}_{index}"
            output = OUT / f"{key}.json"
            subprocess.run([sys.executable,"-I","-S","-B","-X","utf8",str(WORKER),"worker",mode,
                 str(path),str(cases),scope,str(output)],cwd=ROOT,timeout=50,check=True)
            reports[key] = evidence.load(output)
    old,new = (reports[k]["records"] for k in ("reference_0","mapped_0"))
    mismatches = [a["case"] for a,b in zip(old,new,strict=True) if a!=b]
    assert reports["reference_1"]["records"]==old and reports["mapped_1"]["records"]==new
    assert all(r["assigned"]==262145 for r in reports.values())
    vocabulary_ok = reports["reference_2"]["sha256"]==reports["mapped_2"]["sha256"]
    assert {k:evidence.digest(ROOT/k) for k in sources}==sources
    assert profile["source_tokenizer_sha256"]==evidence.digest(source)
    peaks = {m:max(reports[f"{m}_{r}"]["peak"] for r in (0,1)) for m in ("reference","mapped")}
    evidence.write(OUT / "report.json",dict(case_count=len(old),mismatches=mismatches,full_vocabulary_match=vocabulary_ok,
        peaks=peaks,vocabulary_scan_peak=reports["mapped_2"]["peak"],profile_sha256=evidence.digest(OUT/"profile.json"),
        reference_seconds=reports["reference_0"]["codec_seconds"],mapped_seconds=reports["mapped_0"]["codec_seconds"],
        model_head_rows=262144,tokenizer_ids=262145,weights_loaded=0))
    print("P109_GEMMA_COMPACT",len(old),len(mismatches),vocabulary_ok,peaks,flush=True)
    return 0 if not mismatches and vocabulary_ok and peaks["mapped"]<=40_000_000 else 8


if __name__ == "__main__":
    sys.exit(run())
