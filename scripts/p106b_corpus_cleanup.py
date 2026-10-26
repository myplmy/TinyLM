#!/usr/bin/env python3
"""CPU-only whole-pool cleanup inventory and resumable, lossless source scan.

Existing format proposals are reused. Risk signals cause an explicit review
HOLD, not destructive deletion or a claim that the source is factually wrong.
No model, torch, network, training, original mutation or automatic admission.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_native_format_candidate as fmt
from scripts.diag_p106b_native_expansion import ByteCodec
from scripts.p106b_native_text_audit import file_sha, signals, write_json
from scripts.p106b_source_cleanup import FENCE, safe, sha
from scripts.p106b_shards import ShardWriter, verify

SCHEMA = "P106B_WHOLE_CORPUS_CLEANUP_V1"
RULES = "CONTEXT_HOLD_AND_EXISTING_EMPTY_TAIL_V1"
BASE = ROOT / "data_cache/p106b_corpus_cleanup_v1_20261026_goalc"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
INPUTS = (
    ("expanded_train", "train", "data_cache/p106b_native_expansion_v1_s1337/train.bin",
     "data_cache/p106b_native_expansion_v1_s1337/meta.json"),
    ("historical_train", "train", "data_cache/ko-en_601000000_chat32/train.bin",
     "data_cache/ko-en_601000000_chat32/meta.json"),
    ("validation", "val", "data_cache/ko-en_601000000_chat32/val.bin",
     "data_cache/ko-en_601000000_chat32/meta.json"),
)
LIMIT = 19_999_999
HANGUL = re.compile("[가-힣]")
LATIN = re.compile("[A-Za-z]")
UI = re.compile(r"\b(?:add to (?:cart|basket)|out of stock|in stock|SKU\s*:|accept all cookies)\b", re.I)
BROKEN = re.compile(r"(?:\{\||\|\}|colspan\s*=|rowspan\s*=|^\s*[|!]\s*[-+}])", re.M | re.I)
MEMOS = re.compile(r"(?mi)^\s*(?:검수\s*메모|편집\s*메모|정제\s*사유|보관\s*설명|\[HOLD\]|\[REVIEW\])")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def relative(path):
    return str(Path(path).relative_to(ROOT))


def proxy(text):
    return dict(codepoints=len(text), hangul_syllables=len(HANGUL.findall(text)),
                ascii_letters=len(LATIN.findall(text)))


def language_bucket(text):
    return "HAS_HANGUL" if HANGUL.search(text) else "NO_HANGUL"


def open_fence(text):
    marker = None
    for line in text.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if not match:
            continue
        run, rest = match.groups()
        if marker is None:
            marker = run
        elif run[0] == marker[0] and len(run) >= len(marker) and not rest.strip():
            marker = None
    return marker is not None


def propose(text):
    # The old tail routine cannot know that an unmatched fence contains a
    # terminal word such as References. Preserve the entire input in that case.
    if open_fence(text):
        return text, [], signals(text)[0], ["OPEN_CODE_FENCE_CONTEXT"]
    candidate, removed, _, info = fmt.transform(text)
    plain = "".join(FENCE.split(candidate)[::2])
    reasons = []
    if info.get("standalone_heading_lines"):
        reasons.append("APPENDIX_OR_NAVIGATION_CONTEXT")
    if info.get("within_doc_repeated_line_extras"):
        reasons.append("REPETITION_CONTEXT")
    if info.get("html_tag_occurrences") or info.get("html_comment_openers"):
        reasons.append("MARKUP_OR_SCHOLARLY_TRANSCRIPTION_CONTEXT")
    if info.get("wiki_markup_openers") or BROKEN.search(plain):
        reasons.append("BROKEN_WIKI_OR_TABLE_CONTEXT")
    if info.get("explicit_category_lines"):
        reasons.append("CATEGORY_METADATA_CONTEXT")
    if UI.search(plain):
        reasons.append("COMMERCIAL_OR_COOKIE_UI_CONTEXT")
    if any(line.strip() in fmt.OUTLINE for line in plain.splitlines()):
        reasons.append("LIST_RELATION_CONTEXT")
    if not text.strip():
        reasons.append("EMPTY_TEXT")
    return candidate, removed, info, reasons


def freeze(base=BASE, specs=INPUTS, tokenizer=TOKENIZER):
    import numpy as np
    base, tokenizer = safe(base), safe(tokenizer)
    base.mkdir(parents=True, exist_ok=True)
    require(not (base / "scope.json").exists(), "scope is write-once")
    rows = []
    for name, split, path_name, meta_name in specs:
        path, meta = safe(ROOT / path_name), safe(ROOT / meta_name)
        before = (path.stat().st_size, path.stat().st_mtime_ns)
        require(before[0] > 0 and before[0] % 2 == 0, "nonempty complete uint16 input required")
        ids, ends, last = before[0] // 2, 0, -1
        with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for start in range(0, ids, 8_000_000):
                view = np.frombuffer(mm, dtype="<u2", count=min(8_000_000, ids-start), offset=start*2)
                positions = np.flatnonzero(view == 2)
                ends += len(positions)
                if len(positions):
                    last = start + int(positions[-1])
                del view, positions
        digest = file_sha(path)
        require(before == (path.stat().st_size, path.stat().st_mtime_ns), "input changed during scope freeze")
        rows.append(dict(name=name, split=split, path=path_name, sha256=digest, bytes=before[0],
            ids=ids, eos_segments=ends, incomplete_tail_ids=ids-last-1,
            intervals=ends + int(last+1 < ids), metadata=meta_name, metadata_sha256=file_sha(meta),
            original_document_id=None, source_url=None, source_kind="UNKNOWN_MIXED_NATIVE_CACHE",
            prefix_policy="HOLD_UNKNOWN_FIRST_FRAGMENT" if split == "val" else "GENERATED_TRAIN_START",
            stored_epoch="NOT_APPLICABLE_REPLACEMENT_SAMPLING"))
    value = dict(schema=SCHEMA, created_utc=datetime.now(timezone.utc).isoformat(), rules=RULES,
        session_id=os.environ.get("CODEX_SESSION_ID"), inputs=rows,
        tokenizer=dict(path=relative(tokenizer), sha256=file_sha(tokenizer), eos_id=2,
                       serialization="little-endian uint16, one EOS2 per complete segment"),
        source_unit="EOS_CACHE_SEGMENTS_NOT_ORIGINAL_URL_DOCUMENTS",
        metadata_mixture_is_not_document_provenance=True,
        previous_exposure=dict(windows=292992, targets_per_window=1024, targets=300023808,
            pool_ids=1185169307, repeated_draws_and_overlap=True, unique_corpus_tokens=False,
            source="data_cache/p106b_native_format_pair_v1_20261026_s1337/format.bin"),
        exclusions=[
            dict(path="datasets/TinyDataset/**", reason="PROTECTED_NO_ACCESS"),
            dict(path="data_cache/ko-en_1200000000/train.bin", reason="LEGACY_TOKENIZER_ANCESTOR_ALREADY_CONVERTED; immutable existing conversion ledger, not another unique pool"),
            dict(path="data_cache/p106b_native_format_v2_full_20261022/", reason="EXISTING_DERIVATIVE_SAME_EXPANDED_INPUT; helper/rule reuse, not another unique pool"),
            dict(path="data_cache/p106b_native_format_pair_v1_20261026_s1337/", reason="HISTORICAL_FORMAT_COMPARISON_DERIVATIVE; exposure audit only, no duplicate corpus credit"),
            dict(path="SFT/teacher drafts and evaluation questions/answers", reason="DISTINCT_TASK_OR_EVALUATION; not native full-input cleanup, never added to training"),
            dict(path="checkpoints and other-session exclusive paths", reason="OUT_OF_SCOPE_NO_ACCESS")],
        full_semantic_fact_verification=False, training_authorized=False)
    write_json(base / "scope.json", value)
    return value


def segments(path, *, start=0, ordinal=0, limit=None):
    import numpy as np
    total = path.stat().st_size // 2
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        cursor, index = start, ordinal
        for block in range(start, total, 8_000_000):
            view = np.frombuffer(mm, dtype="<u2", count=min(8_000_000, total-block), offset=block*2)
            ends = np.flatnonzero(view == 2).tolist()
            del view
            for local in ends:
                end = block + local
                raw = mm[cursor*2:(end+1)*2]
                values = np.frombuffer(raw, dtype="<u2").tolist()
                yield index, cursor, end+1, raw, values, True
                cursor, index = end+1, index+1
                if limit is not None and index-ordinal >= limit:
                    return
        if cursor < total:
            raw = mm[cursor*2:]
            yield index, cursor, total, raw, np.frombuffer(raw, dtype="<u2").tolist(), False


def iter_scan(base, source=None):
    scope = read(base / "scope.json")
    for spec in scope["inputs"]:
        if source and spec["name"] != source:
            continue
        for stamp in sorted((base / "scan" / spec["name"]).glob("unit_*/complete.json")):
            info = read(stamp)
            for shard in info["manifest"]["shards"]:
                with (stamp.parent / "records" / shard["path"]).open(encoding="utf-8") as stream:
                    for line in stream:
                        yield json.loads(line)


def scan(base=BASE, source=None, *, unit_documents=20000, max_units=0):
    base = safe(base)
    scope = read(base / "scope.json")
    tok_spec = scope["tokenizer"]
    require(file_sha(ROOT / tok_spec["path"]) == tok_spec["sha256"], "tokenizer identity differs")
    codec = ByteCodec(read(ROOT / tok_spec["path"]))
    completed_now = 0
    started = last_print = time.monotonic()
    for spec in scope["inputs"]:
        if source and spec["name"] != source:
            continue
        parent = base / "scan" / spec["name"]
        parent.mkdir(parents=True, exist_ok=True)
        stamps = sorted(parent.glob("unit_*/complete.json"))
        cursor = ordinal = number = 0
        for stamp in stamps:
            old = read(stamp)
            require(old["start_ids"] == cursor and old["start_ordinal"] == ordinal
                    and old["source_sha256"] == spec["sha256"], "scan resume chain differs")
            verify(stamp.parent / "records", old["manifest"])
            cursor, ordinal = old["end_ids"], old["end_ordinal"]
            number += 1
        path = safe(ROOT / spec["path"])
        before = (path.stat().st_size, path.stat().st_mtime_ns)
        require(before[0] == spec["bytes"] and file_sha(path) == spec["sha256"], "source SHA differs")
        while cursor < spec["ids"]:
            if max_units and completed_now >= max_units:
                return dict(status="CHUNK_BOUNDARY_PAUSE_NOT_COMPLETE", units_completed=completed_now)
            attempt = 0
            while True:
                directory = parent / f"unit_{number:06d}_attempt_{attempt:03d}"
                if not directory.exists():
                    break
                attempt += 1
            writer = ShardWriter(directory / "records", "documents", limit=LIMIT)
            counts, before_signals, after_signals = Counter(), Counter(), Counter()
            before_proxy, after_proxy = Counter(), Counter()
            samples = {}
            unit_start, ordinal_start = cursor, ordinal
            for index, start, end, raw, ids, complete in segments(path, start=cursor, ordinal=ordinal, limit=unit_documents):
                reasons = []
                valid_utf8 = True
                try:
                    text, _ = codec.text(ids[:-1] if complete else ids)
                except UnicodeError:
                    # Partial split edges can cut a Unicode byte sequence.
                    valid_utf8 = False
                    text = ""
                    reasons.append("INCOMPLETE_UTF8_BOUNDARY_RAW_ONLY")
                candidate, removed, info, risk = propose(text)
                original_info = signals(text)[0]
                reasons.extend(risk)
                if not complete:
                    reasons.append("INCOMPLETE_SOURCE_TAIL")
                if spec["split"] == "val" and index == 0:
                    reasons.append("UNKNOWN_VALIDATION_PREFIX_FRAGMENT")
                reserved = Counter(str(v) for v in (ids[:-1] if complete else ids) if v in codec.specials)
                if reserved:
                    reasons.append("RESERVED_TOKEN_IN_BODY")
                if not valid_utf8 or not complete or reasons:
                    decision = "HOLD"
                else:
                    decision = "EDIT" if candidate != text else "KEEP"
                row = dict(id=f"{spec['name']}:{index}", source=spec["name"], split=spec["split"],
                    ordinal=index, source_ids=[start,end], complete_eos=complete,
                    input_ids=end-start, source_ids_sha256=hashlib.sha256(raw).hexdigest().upper(),
                    original_text_sha256=sha(text) if valid_utf8 else None, text=text,
                    source_kind=spec["source_kind"], source_url=None, original_document_id=None,
                    valid_utf8=valid_utf8, automatic_decision=decision, review_reasons=sorted(set(reasons)),
                    candidate_text_sha256=sha(candidate) if valid_utf8 else None,
                    removed_empty_terminal_headings=removed, original_signals=original_info,
                    candidate_signals=info, language_proxy=proxy(text), language_bucket=language_bucket(text),
                    rules=RULES, truth="NOT_FACT_CHECKED", training_admission="NOT_ADMITTED")
                writer.append(row)
                counts.update(documents=1, input_ids=len(ids), complete_eos=int(complete), **{decision:1})
                before_signals.update(original_info); after_signals.update(info)
                before_proxy.update(row["language_proxy"]); after_proxy.update(proxy(candidate))
                kinds = reasons or (["EMPTY_TERMINAL_HEADING_EDIT"] if removed else ["NO_RISK_SIGNAL"])
                if "```" in text or "~~~" in text:
                    kinds = [*kinds, "PROTECTED_CODE_EXAMPLE"]
                for kind in set(kinds):
                    key = row["language_bucket"] + ":" + kind
                    bucket = samples.setdefault(key, [])
                    # Deterministic lowest hashes within each completed unit.
                    item = dict(id=row["id"], source_ids=row["source_ids"],
                                sha256=row["original_text_sha256"], bytes=len(text.encode("utf-8")),
                                unit=relative(directory))
                    bucket.append(item)
                    bucket.sort(key=lambda x:(x["sha256"] or "",x["id"]))
                    del bucket[3:]
                cursor, ordinal = end, index+1
                if time.monotonic()-last_print >= 20:
                    print(json.dumps(dict(phase="scan", source=spec["name"], documents=ordinal,
                        through_ids=cursor, source_ids=spec["ids"], elapsed_seconds=round(time.monotonic()-started,1))), flush=True)
                    last_print=time.monotonic()
            manifest = writer.close(lineage=dict(source=spec["path"], source_sha256=spec["sha256"],
                                                tokenizer_sha256=tok_spec["sha256"], rules=RULES))
            verify(directory / "records", manifest)
            write_json(directory / "complete.json", dict(schema=SCHEMA, source_sha256=spec["sha256"],
                start_ids=unit_start,end_ids=cursor,start_ordinal=ordinal_start,end_ordinal=ordinal,
                manifest=manifest,counts=dict(counts),before_signals=dict(before_signals),
                after_signals=dict(after_signals),before_proxy=dict(before_proxy),after_proxy=dict(after_proxy),
                samples=samples))
            number+=1;completed_now+=1
        require(before == (path.stat().st_size,path.stat().st_mtime_ns) and file_sha(path)==spec["sha256"], "input changed during scan")
        require(cursor==spec["ids"] and ordinal==spec["intervals"], "scan has unexplained missing intervals")
    return dict(status="SELECTED_INPUTS_FULLY_SCANNED",units_completed=completed_now,seconds=time.monotonic()-started)


def packets(base=BASE, *, each=8, name="packets"):
    base=safe(base)
    selected={}
    for stamp in sorted((base/"scan").glob("*/unit_*/complete.json")):
        for key,values in read(stamp)["samples"].items():
            group=selected.setdefault(key,{})
            for item in values:
                if item["sha256"] and 0<item["bytes"]<=32000:
                    group.setdefault(item["sha256"],item)
    wanted={}
    for key,group in selected.items():
        for item in sorted(group.values(),key=lambda x:x["sha256"])[:each]:
            wanted.setdefault(item["id"],dict(item,channels=[]))["channels"].append(key)
    require(name.isascii() and name.replace("_", "").isalnum(), "safe packet version name required")
    target=base/name
    target.mkdir(exist_ok=True)
    found=[]
    for row in iter_scan(base):
        if row["id"] not in wanted:
            continue
        item=wanted[row["id"]]
        name=row["id"].replace(":","_")
        path=target/(name+".txt")
        with path.open("x",encoding="utf-8",newline="") as out:
            out.write(row["text"])
        item.update(path=relative(path),decision=row["automatic_decision"],reasons=row["review_reasons"])
        found.append(item)
    require(len(found)==len(wanted) and found,"packet source coverage differs")
    write_json(target/"manifest.json",dict(schema=SCHEMA,selection="lowest SHA per completed-unit risk/language stratum; purpose sample, not a prevalence estimate",rows=found))
    return dict(packet_documents=len(found),strata=len(selected))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["freeze","scan","packets"])
    parser.add_argument("--base",type=Path,default=BASE)
    parser.add_argument("--source",choices=[s[0] for s in INPUTS])
    parser.add_argument("--max-units",type=int,default=0)
    parser.add_argument("--unit-documents",type=int,default=20000)
    parser.add_argument("--packet-name",default="packets")
    args=parser.parse_args(argv)
    require(args.max_units>=0 and args.unit_documents>0,"invalid work chunk, not a completion cap")
    os.environ.update(TOKENIZERS_PARALLELISM="false",RAYON_NUM_THREADS="1",CUDA_VISIBLE_DEVICES="")
    if args.command=="freeze":
        value=freeze(args.base)
        print(json.dumps(dict(schema=SCHEMA,inputs=value["inputs"],training_authorized=False)),flush=True)
    elif args.command=="scan":
        print(json.dumps(scan(args.base,args.source,unit_documents=args.unit_documents,max_units=args.max_units)),flush=True)
    else:
        print(json.dumps(packets(args.base,name=args.packet_name)),flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
