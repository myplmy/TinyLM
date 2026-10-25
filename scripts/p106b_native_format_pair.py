#!/usr/bin/env python3
"""같은 EOS 캐시 구간의 원형/형식 두 풀을 준비하는 CPU 전용 builder.

실제 대량 실행은 총괄 소유다. 정확 policy, HOLD roster, VAL 경로와 SHA가
없으면 시작하지 않는다. EOS 구간은 원 URL 문서가 아니며, 내용 전수 검수,
언어 균형, 근접 중복과 전역 기사 누설을 검증했다고 주장하지 않는다.
외부 OS timeout과 실제 종료 회수는 총괄이 별도로 수행해야 한다.
"""
from __future__ import annotations
import time
STARTED = time.monotonic()
from array import array
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_native_format_candidate as fmt
from scripts import diag_p106b_native_expansion as native
from scripts.p106b_native_text_audit import file_sha, write_json
from scripts.p106b_source_cleanup import sha
from scripts.p106b_shards import ShardWriter, verify

SCHEMA = "P106B_NATIVE_FORMAT_PAIR_V1"
POLICY = "P106B_NATIVE_FORMAT_PAIR_POLICY_V1"
REPORT = "data_cache/p106b_native_format_v2_full_20261022/report.json"
SOURCE = "data_cache/p106b_native_expansion_v1_s1337/train.bin"
SOURCE_SHA = "6DB291329CB1562E127A2D753F879C8ED8D3AB46789A3EF2B4BC3C4258846138"
TOKEN_SHA = "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
MIN_IDS = 2289 * 8 * 16 * 1024 * 2
END = datetime(2026, 10, 26, 8, tzinfo=timezone.utc)
CODE = ("scripts/p106b_native_format_pair.py", "scripts/test_p106b_native_format_pair.py",
        "scripts/p106b_native_format_candidate.py", "scripts/p106b_native_text_audit.py",
        "scripts/p106b_source_cleanup.py", "scripts/p106b_shards.py",
        "scripts/diag_p106b_native_expansion.py", "scripts/p106b_stage_receipt.py")


class Hold(FileNotFoundError):
    """정확한 총괄 policy 또는 입력 명세가 없는 준비 보류."""


def require(value, message):
    if not value:
        raise ValueError(message)


def safe(name, root=ROOT):
    name = Path(name)
    require(not name.is_absolute() and name.parts and ".." not in name.parts
            and name.parts[0] != "ai_dev_tool"
            and not any(p in {"TinyDataset", "CLAUDE.md", ".claude", ".codex", ".agents", ".aws"} for p in name.parts),
            "보호 경로가 아닌 정확한 저장소 상대 경로가 필요하다")
    path = Path(root) / name
    require(not any(p.is_symlink() for p in (path, *path.parents)), "소스와 출력 링크를 허용하지 않는다")
    return path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def source_identity(root=ROOT):
    files = {name: file_sha(safe(name, root)) for name in CODE}
    return dict(sha256=hashlib.sha256(canonical(files)).hexdigest().upper(), files=files)


def read_json(path):
    require(Path(path).is_file() and Path(path).stat().st_size < 20_000_000,
            "20MB 미만의 작은 JSON 명세가 필요하다")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    canonical(value)
    return value


class Budget:
    def __init__(self, seconds, deadline, *, started=None, clock=time.monotonic):
        self.clock = clock
        self.started = clock() if started is None else started
        require(math.isfinite(seconds) and 0 < seconds <= 28800
                and math.isfinite(self.started) and self.started <= clock(), "현재 시작과 최대 8시간 예산이 필요하다")
        self.end = min(self.started + seconds, clock() + deadline - time.time())
        self.check("시작")

    def remaining(self):
        return self.end - self.clock()

    def check(self, stage):
        if self.remaining() <= 0:
            raise TimeoutError("전체 CPU 시간창을 넘었다: " + stage)


def metadata(policy_path, *, root=ROOT, synthetic=False):
    path = safe(policy_path, root)
    if not path.is_file():
        raise Hold("총괄이 작성한 정확 policy JSON이 필요하다")
    policy = read_json(path)
    require(policy.get("schema") == POLICY and policy.get("approved_train_reuse") is True
            and policy.get("scope") == "TRAIN_FORMAT_COMPARISON_ONLY"
            and policy.get("full_semantic_review") is False
            and policy.get("review_queue_policy") == "PRESERVE_NOT_AUTOMATIC_HOLD"
            and policy.get("reserved_action") == "EXCLUDE_BOTH",
            "TRAIN 재사용·내용 검수 미확인·공통 제외의 명시 policy가 필요하다")
    minimum = policy.get("minimum_ids_per_arm")
    require(type(minimum) is int and minimum > 0 and (synthetic or minimum == MIN_IDS),
            "각 풀은 300M 학습의 엄격한 두 배 이상이어야 한다")
    for key in ("source", "report", "tokenizer", "validation", "holds"):
        item = policy.get(key)
        require(isinstance(item, dict) and isinstance(item.get("path"), str)
                and re.fullmatch("[A-Fa-f0-9]{64}", item.get("sha256", "")),
                "정확한 입력 경로와 SHA가 필요하다: " + key)
        safe(item["path"], root)
    if not synthetic:
        require(policy["source"] == {"path": SOURCE, "sha256": SOURCE_SHA}
                and policy["report"]["path"] == REPORT
                and policy["tokenizer"]["sha256"] == TOKEN_SHA,
                "승인된 원 TRAIN과 후보 report·토크나이저만 허용한다")
    for key in ("report", "holds"):
        require(file_sha(safe(policy[key]["path"], root)) == policy[key]["sha256"].upper(),
                "작은 입력 명세 SHA가 다르다: " + key)
    report = read_json(safe(policy["report"]["path"], root))
    require(report.get("schema") == "P106B_WHOLE_NATIVE_FORMAT_CANDIDATE_V1"
            and report.get("source") == policy["source"]["path"]
            and report.get("source_sha256") == policy["source"]["sha256"].upper()
            and report.get("tokenizer_sha256") == policy["tokenizer"]["sha256"].upper()
            and report.get("full_eos_pool_transformed") is True
            and report.get("remaining_ids") == 0
            and report.get("through_id_exclusive") == report.get("source_ids"),
            "후보의 전량 원형 계보가 다르다")
    if not synthetic:
        require(report["documents"] == 1441175 and report["source_ids"] == 1191116192
                and report["counts"]["changed_documents"] == 46051
                and len(report["manifests"]["format_candidate"]["shards"]) == 294,
                "지정된 전체 후보의 개수와 형상이 다르다")
    holds = read_json(safe(policy["holds"]["path"], root))
    require(holds.get("schema") == "P106B_NATIVE_FORMAT_HOLDS_V1"
            and holds.get("source_sha256") == policy["source"]["sha256"].upper()
            and isinstance(holds.get("holds"), list), "같은 원형에 묶인 명시 HOLD roster가 필요하다")
    return policy, report, holds


class Holds:
    def __init__(self, document, source_sha):
        self.entries = document["holds"]
        self.index, self.hits = {}, Counter()
        owners = set()
        for number, row in enumerate(self.entries):
            key = row.get("id")
            require(isinstance(key, str) and key and key not in owners, "HOLD 항목 ID가 없거나 중복됐다")
            owners.add(key)
            text_sha = row.get("original_text_sha256")
            if text_sha is not None:
                require(re.fullmatch("[A-Fa-f0-9]{64}", text_sha), "HOLD 원문 SHA가 유효하지 않다")
                row["original_text_sha256"] = text_sha.upper()
            span, eos = row.get("cache_segment_ids"), row.get("eos_segment_index")
            if eos is not None:
                require(type(eos) is int and eos >= 0, "HOLD의 EOS ID가 유효하지 않다")
            if span is not None or eos is not None:
                require(row.get("source_sha256") == source_sha, "숫자 HOLD는 같은 source SHA에만 적용한다")
            if span is not None:
                require(isinstance(span, list) and len(span) == 2
                        and all(type(v) is int for v in span) and 0 <= span[0] <= span[1],
                        "HOLD의 정확 구간이 필요하다")
                identity = ("span", tuple(span))
            elif eos is not None:
                require(type(eos) is int and eos >= 0, "HOLD의 EOS ID가 유효하지 않다")
                identity = ("eos", eos)
            else:
                require(text_sha is not None and row.get("match_scope") == "ALL_IDENTICAL_ORIGINAL_TEXT",
                        "원문 SHA HOLD의 전체 동일 원문 적용을 명시해야 한다")
                identity = ("sha", row["original_text_sha256"])
            self.index.setdefault(identity, []).append(number)

    def match(self, row):
        candidates = set()
        for key in (("span", tuple(row["cache_segment_ids"])), ("eos", row["eos_segment_index"]),
                    ("sha", row["original_text_sha256"])):
            candidates.update(self.index.get(key, []))
        found = []
        for number in sorted(candidates):
            item = self.entries[number]
            for key in ("cache_segment_ids", "eos_segment_index", "original_text_sha256"):
                if key in item:
                    require(item[key] == row[key], "HOLD의 구간·EOS ID·원문 SHA가 충돌한다")
            self.hits[item["id"]] += 1
            found.append(item["id"])
        return found

    def complete(self):
        unresolved = [row["id"] for row in self.entries if not self.hits[row["id"]]]
        require(not unresolved, "HOLD 매핑 미해결: " + ",".join(unresolved[:16]))
        return dict(self.hits)


def edit_spans(original, candidate, removals):
    if original == candidate:
        return []
    normalized = unicodedata.normalize("NFC", original.replace("\r\n", "\n").replace("\r", "\n"))
    events = []
    if normalized != original:
        events.append(dict(operation="NFC_NEWLINES", input_char_span=[0, len(original)],
                           output_char_span=[0, len(normalized)], before_sha256=sha(original),
                           after_sha256=sha(normalized)))
    cursor = len(normalized)
    for removal in removals:
        text = removal["text"]
        start = cursor - len(text)
        require(start >= 0 and normalized[start:cursor] == text, "정제 tail span이 원문에 연결되지 않는다")
        events.append(dict(operation="EMPTY_TERMINAL_HEADING", normalized_char_span=[start, cursor],
                           removed_text_sha256=sha(text), reason=removal["reason"]))
        cursor = start
    require(normalized[:cursor] == candidate, "기존 transform의 정제 span과 본문이 다르다")
    return events


def language_proxy(text):
    return dict(codepoints=len(text), hangul_syllables=sum("가" <= c <= "힣" for c in text),
                ascii_letters=sum(c.isascii() and c.isalpha() for c in text))


def pair_for_val(codec, vocab):
    value = SimpleNamespace(current=codec, layout={"vocab": vocab})
    value.current_segment = lambda ids: native.CodecPair.current_segment(value, ids)
    return value


def verify_inputs(policy, report, root, budget):
    for key in ("source", "tokenizer", "validation", "report", "holds"):
        budget.check("입력 전체 SHA 전: " + key)
        require(file_sha(safe(policy[key]["path"], root)) == policy[key]["sha256"].upper(),
                "원형 입력 SHA가 다르다: " + key)
        budget.check("입력 전체 SHA 후: " + key)
    parent = safe(policy["report"]["path"], root).parent
    require(set(report["manifests"]) == {"format_candidate", "review_queue"}, "원 후보 명세 집합이 다르다")
    require(report["manifests"]["format_candidate"]["rows"] == report["documents"]
            and report["manifests"]["review_queue"]["rows"] == report["counts"]["pending_review_documents"],
            "원 후보와 검토 queue의 전량 행 수가 다르다")
    for key, manifest in report["manifests"].items():
        budget.check("원 후보 shard 전체 검산 전")
        require(manifest["lineage"] == dict(source=policy["source"]["path"],
            source_sha256=policy["source"]["sha256"].upper(),
            tokenizer_sha256=policy["tokenizer"]["sha256"].upper(), training_admission="NOT_ADMITTED"),
            "원 후보 shard 계보가 다르다")
        verify(parent / key, manifest)
        budget.check("원 후보 shard 전체 검산 후")


def verify_outputs(output, summary, budget):
    require(not (output / "failed.json").exists(), "실패 또는 시간초과가 남은 partial이다")
    manifest = summary["ledger"]
    verify(output / "ledger", manifest)
    counts = Counter()
    offsets = {"original": 0, "format": 0}
    cursor = documents = 0
    ledger_stream = None
    streams = {arm: (output / (arm + ".bin")).open("rb") for arm in offsets}
    try:
        for spec in manifest["shards"]:
            ledger_stream = (output / "ledger" / spec["path"]).open(encoding="utf-8")
            for line in ledger_stream:
                budget.check("양팔 독립 ledger 재검산")
                row = json.loads(line)
                start, stop = row["cache_segment_ids"]
                require(type(row["eos_segment_index"]) is int and row["eos_segment_index"] == documents
                        and start == cursor and stop >= start and type(row["kept"]) is bool
                        and bool(row["exclusions"]) == (not row["kept"]), "출력 roster 순서·누락·제외 계약이 다르다")
                cursor, documents = stop + 1, documents + 1
                if not row["kept"]:
                    require("original" not in row and "format" not in row, "제외 문서가 한 팔에 들어갔다")
                    continue
                for arm in offsets:
                    item = row[arm]
                    require(item["offset_ids"] == offsets[arm] and type(item["tokens"]) is int
                            and item["tokens"] > 0, "출력 독립 offsets가 연속적이지 않다")
                    raw = streams[arm].read(item["tokens"] * 2)
                    require(len(raw) == item["tokens"] * 2
                            and hashlib.sha256(raw).hexdigest().upper() == item["ids_sha256"],
                            "출력 구간 bytes SHA가 다르다")
                    values = array("H"); values.frombytes(raw)
                    if sys.byteorder != "little":
                        values.byteswap()
                    require(values[-1] == 2 and values.count(2) == 1, "출력 구간의 EOS2 경계가 다르다")
                    offsets[arm] += item["tokens"]
                counts["kept"] += 1
            ledger_stream.close()
        for arm, stream in streams.items():
            require(not stream.read(1) and offsets[arm] == summary["arms"][arm]["tokens"]
                    and file_sha(output / (arm + ".bin")) == summary["arms"][arm]["sha256"],
                    "출력 전체 크기·토큰·SHA가 다르다")
    finally:
        if ledger_stream is not None:
            ledger_stream.close()
        for stream in streams.values():
            stream.close()
    require(counts["kept"] == summary["kept_documents"], "양팔 문서 roster 개수가 다르다")
    require(documents == summary["documents"] and cursor == summary["source_ids"], "전체 원 구간 roster가 다르다")
    return dict(tokens=dict(offsets), kept_documents=counts["kept"])


def build(policy_path, output_name, *, root=ROOT, codec=None, budget=None):
    synthetic = codec is not None
    budget = budget or Budget(3600, END.timestamp())
    policy, report, hold_document = metadata(policy_path, root=root, synthetic=synthetic)
    policy_sha = file_sha(safe(policy_path, root))
    require(read_json(safe(policy_path, root)) == policy, "policy 읽기 중 원형이 달라졌다")
    holds = Holds(hold_document, policy["source"]["sha256"].upper())
    identity = source_identity()
    require(policy.get("source_code_sha256") == identity["sha256"], "builder와 helper 소스 신원이 다르다")
    output = safe(output_name, root)
    require(Path(output_name).parts[0] == "data_cache" and not output.exists()
            and len(Path(output_name).parts) == 2, "data_cache 아래 새 독립 이름공간만 허용한다")
    output.mkdir()
    write_json(output / "partial.json", dict(schema=SCHEMA, policy_sha256=policy_sha,
               source_identity=identity, synthetic=synthetic, completion="NOT_COMPLETE"))
    streams, writer, candidate_stream = {}, None, None
    try:
        verify_inputs(policy, report, root, budget)
        if codec is None:
            config = read_json(safe(policy["tokenizer"]["path"], root))
            codec = native.ByteCodec(config)
            vocab = len(config["model"]["vocab"])
        else:
            vocab = codec.vocab
        reserved = set(codec.specials)
        require(2 in reserved and set(codec.specials) >= {0, 1, 2}, "PAD/BOS/EOS의 원형 정의가 필요하다")
        literals = re.compile("|".join(re.escape(s) for s in sorted(codec.specials.values(), key=len, reverse=True)))
        source_path = safe(policy["source"]["path"], root)
        val_path = safe(policy["validation"]["path"], root)
        require(source_path.stat().st_size == report["source_ids"] * 2 and val_path.stat().st_size % 2 == 0,
                "원형 또는 VAL uint16 차원이 다르다")
        with val_path.open("rb") as val_stream:
            val_reader = native.UInt16Input(val_stream, val_path.stat().st_size // 2)
            validation = native.build_val_index(val_reader, pair_for_val(codec, vocab))
            require(val_reader.hexdigest() == policy["validation"]["sha256"].upper(),
                    "VAL 전체 consumer SHA가 다르다")
        writer = ShardWriter(output / "ledger", "pairs", limit=19_999_999)
        offsets, hashes, proxy = {}, {}, {}
        for arm in ("original", "format"):
            streams[arm] = (output / (arm + ".bin")).open("xb")
            offsets[arm], hashes[arm], proxy[arm] = 0, hashlib.sha256(), Counter()
        counts = Counter()
        cursor = 0
        candidate_dir = safe(policy["report"]["path"], root).parent / "format_candidate"
        with source_path.open("rb") as source_stream, mmap.mmap(source_stream.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for shard in report["manifests"]["format_candidate"]["shards"]:
                budget.check("원 후보 shard 읽기")
                candidate_stream = (candidate_dir / shard["path"]).open(encoding="utf-8")
                for line in candidate_stream:
                    budget.check("문서 원형과 정제 대조")
                    row = json.loads(line)
                    start, stop = row["cache_segment_ids"]
                    require(type(start) is int and type(stop) is int and start == cursor
                            and 0 <= start <= stop < report["source_ids"]
                            and type(row["eos_segment_index"]) is int
                            and row["eos_segment_index"] == counts["documents"], "구간·순서·누락 없는 원 roster가 필요하다")
                    raw = mm[start*2:(stop+1)*2]
                    ids = array("H"); ids.frombytes(raw)
                    if sys.byteorder != "little":
                        ids.byteswap()
                    require(ids[-1] == 2 and ids.count(2) == 1 and len(ids) <= native.MAX_SEGMENT_IDS,
                            "정확히 한 개의 EOS2와 bounded 원 구간이 필요하다")
                    original, original_bytes = codec.text(ids[:-1])
                    require(sha(original) == row["original_text_sha256"], "decode된 원문 SHA가 다르다")
                    candidate, removed, review, structure = fmt.transform(original)
                    require(candidate == row["text"] and sha(candidate) == row["candidate_text_sha256"]
                            and removed == row["removed_empty_terminal_headings"] and review == row["review_reasons"]
                            and row["normalization_changed"] == (original != unicodedata.normalize("NFC", original.replace("\r\n", "\n").replace("\r", "\n"))),
                            "원 transform과 후보 본문·SHA·편집이 다르다")
                    changed = candidate != original
                    counts["changed_documents"] += changed
                    counts["pending_review_documents"] += bool(review)
                    counts["remaining_structure_documents"] += bool(structure)
                    counts["removed_headings"] += len(removed)
                    held = holds.match(row)
                    special_ids = Counter(str(v) for v in ids[:-1] if v in reserved)
                    special_literals = Counter(literals.findall(original))
                    candidate_ids = list(codec.backend.encode(candidate, add_special_tokens=False).ids) if changed else list(ids[:-1])
                    if changed:
                        counts["encoded_changed_documents"] += 1
                    else:
                        counts["unchanged_token_slices_reused"] += 1
                    candidate_special = Counter(str(v) for v in candidate_ids if v in reserved)
                    candidate_literals = Counter(literals.findall(candidate))
                    require(all(type(v) is int and 0 <= v < vocab for v in candidate_ids), "정제 ID가 원 어휘 범위를 벗어났다")
                    if changed:
                        restored, body_bytes = codec.text(candidate_ids)
                        require(restored == candidate and body_bytes == candidate.encode("utf-8"),
                                "정제 본문이 encode/decode에서 달라졌다")
                    reasons = []
                    if held:
                        reasons.append("EXPLICIT_HOLD")
                    if special_ids or special_literals or candidate_special or candidate_literals:
                        reasons.append("RESERVED_TOKEN_OR_LITERAL")
                    original_hits, original_odd = validation.match(list(ids))
                    format_ids = candidate_ids + [2]
                    format_hits, format_odd = validation.match(format_ids)
                    reasons.extend("ORIGINAL_" + item for item in original_hits)
                    reasons.extend("FORMAT_" + item for item in format_hits)
                    event = dict(eos_segment_index=row["eos_segment_index"], cache_segment_ids=[start, stop],
                        original_text_sha256=row["original_text_sha256"], candidate_text_sha256=row["candidate_text_sha256"],
                        changed=changed, kept=not reasons, exclusions=reasons, holds=held,
                        reserved=dict(original_ids=dict(special_ids), original_literals=dict(special_literals),
                                      format_ids=dict(candidate_special), format_literals=dict(candidate_literals)),
                        edits=edit_spans(original, candidate, removed), review_reasons=review,
                        structure_signals=structure, unaligned_val_matches_ignored=original_odd+format_odd)
                    if not reasons:
                        counts["kept"] += 1
                        for arm, data, text in (("original", raw, original),
                                               ("format", native.ids_bytes(format_ids) if changed else raw, candidate)):
                            event[arm] = dict(offset_ids=offsets[arm], tokens=len(data)//2,
                                              ids_sha256=hashlib.sha256(data).hexdigest().upper())
                            streams[arm].write(data)
                            hashes[arm].update(data)
                            offsets[arm] += len(data)//2
                            proxy[arm].update(language_proxy(text))
                    else:
                        counts["excluded"] += 1
                    writer.append(event)
                    counts["documents"] += 1
                    cursor = stop + 1
                candidate_stream.close()
        holds_readback = holds.complete()
        require(cursor == report["source_ids"] and counts["documents"] == report["documents"]
                and counts["changed_documents"] == report["counts"]["changed_documents"]
                and counts["encoded_changed_documents"] == counts["changed_documents"]
                and counts["pending_review_documents"] == report["counts"]["pending_review_documents"]
                and counts["remaining_structure_documents"] == report["counts"]["remaining_structure_documents"]
                and counts["removed_headings"] == report["counts"]["empty_terminal_heading_lines_removed"],
                "원 후보의 전량 구간·변경·검토 개수가 다르다")
        require(all(n >= policy["minimum_ids_per_arm"] for n in offsets.values()),
                "공통 제외 후 어느 풀이든 최소 600047616 ID 또는 명시 합성 기준에 부족하다")
        for stream in streams.values():
            stream.flush(); os.fsync(stream.fileno()); stream.close()
        lineage = dict(source_sha256=policy["source"]["sha256"], policy_sha256=policy_sha,
                       source_code_sha256=identity["sha256"], same_roster_and_order=True)
        ledger = writer.close(lineage=lineage)
        summary = dict(schema=SCHEMA, synthetic=synthetic, source_identity=identity,
            policy_sha256=lineage["policy_sha256"], unit="EOS_CACHE_SEGMENTS_NOT_ORIGINAL_URL_DOCUMENTS",
            documents=counts["documents"], source_ids=report["source_ids"],
            kept_documents=counts["kept"], counts=dict(counts),
            holds=holds_readback, validation=validation.summary, ledger=ledger,
            arms={arm:dict(tokens=offsets[arm], bytes=offsets[arm]*2, sha256=hashes[arm].hexdigest().upper(),
                  language_proxy=dict(proxy[arm]), language_proxy_ratios=dict(
                      hangul_syllable_codepoint_fraction=(proxy[arm]["hangul_syllables"] / proxy[arm]["codepoints"]
                                                         if proxy[arm]["codepoints"] else None),
                      ascii_letter_codepoint_fraction=(proxy[arm]["ascii_letters"] / proxy[arm]["codepoints"]
                                                       if proxy[arm]["codepoints"] else None))) for arm in offsets},
            language_proxy_limit="CHARACTER_COUNTS_ONLY_NOT_LANGUAGE_LABELS_OR_BALANCE",
            review_queue="PRESERVED_NOT_AUTOMATIC_BADNESS_OR_HOLD",
            full_semantic_review=False, near_or_global_article_leakage="NOT_ESTABLISHED",
            training_admission="SYNTHETIC_ONLY_NOT_ADMITTED" if synthetic else "CPU_CACHE_PREPARED_NOT_TRAIN_OR_QUALITY_PASS")
        summary["output_readback"] = verify_outputs(output, summary, budget)
        verify_inputs(policy, report, root, budget)
        require(file_sha(safe(policy_path, root)) == policy_sha and read_json(safe(policy_path, root)) == policy,
                "준비 중 총괄 policy가 달라졌다")
        require(source_identity()["sha256"] == identity["sha256"], "준비 중 builder 소스가 달라졌다")
        budget.check("완결 저장 전")
        write_json(output / "complete.json", summary)
        require(read_json(output / "complete.json") == summary, "완결 저장 후 재읽기가 다르다")
        budget.check("완결 저장 후")
        return summary
    except BaseException as error:
        cleanup = []
        if candidate_stream is not None:
            try:
                candidate_stream.close()
            except BaseException as secondary:
                cleanup.append(dict(stage="후보 입력 닫기", error_type=type(secondary).__name__))
        for stream in streams.values():
            if not stream.closed:
                try:
                    stream.close()
                except BaseException as secondary:
                    cleanup.append(dict(stage="partial bin 닫기", error_type=type(secondary).__name__))
        if writer is not None and writer._file is not None:
            try:
                writer._file.close()
            except BaseException as secondary:
                cleanup.append(dict(stage="partial ledger 닫기", error_type=type(secondary).__name__))
        try:
            write_json(output / "failed.json", dict(schema=SCHEMA, error_type=type(error).__name__,
                       message=str(error)[:2000], cleanup_errors=cleanup, completion="PARTIAL_NOT_USABLE"))
        except BaseException:
            pass
        raise


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    parser.add_argument("--policy", required=True)
    parser.add_argument("--policy-sha256")
    parser.add_argument("--output")
    parser.add_argument("--max-wall-sec", type=int, default=3600)
    parser.add_argument("--deadline", default=END.isoformat())
    args = parser.parse_args(argv)
    output, prepared = None, False
    try:
        deadline = datetime.fromisoformat(args.deadline.replace("Z", "+00:00"))
        require(deadline.tzinfo is not None and deadline <= END, "26일 17시 이내의 명시 마감이 필요하다")
        active = Budget(args.max_wall_sec, deadline.timestamp(), started=STARTED)
        policy, report, holds = metadata(args.policy)
        if args.policy_sha256 is not None:
            require(file_sha(safe(args.policy)) == args.policy_sha256.upper(), "총괄이 고정한 policy SHA가 다르다")
        identity = source_identity()
        require(policy.get("source_code_sha256") == identity["sha256"], "현재 builder source identity를 policy에 고정해야 한다")
        if args.check_only:
            Holds(holds, policy["source"]["sha256"].upper())
            print(json.dumps(dict(schema=SCHEMA, source_identity=identity, policy_sha256=file_sha(safe(args.policy)),
                  documents=report["documents"], minimum_ids_per_arm=policy["minimum_ids_per_arm"],
                  hold_entries=len(holds["holds"]), full_input_hashes="NOT_RUN",
                  corpus_read=False, gpu_calls=0, model_loads=0, files_written=0), ensure_ascii=False), flush=True)
            active.check("작은 check-only 출력 후")
            return 0
        require(args.output is not None, "새 data_cache 출력 경로가 필요하다")
        require(args.policy_sha256 is not None, "대량 실행에는 총괄이 고정한 policy SHA가 필요하다")
        output = safe(args.output)
        with native.single_core_environment(), native.termination_guard(), native.wall_limit(max(1, int(active.remaining()))):
            result = build(args.policy, args.output, budget=active)
            prepared = True
            print(json.dumps(dict(schema=SCHEMA, kept_documents=result["kept_documents"],
                  arms=result["arms"], quality_pass=False), ensure_ascii=False), flush=True)
            active.check("작은 stdout 후")
        active.check("타이머와 환경 복원 후")
        return 0
    except BaseException as error:
        if prepared and output is not None and output.is_dir() and not (output / "failed.json").exists():
            try:
                write_json(output / "failed.json", dict(schema=SCHEMA, error_type=type(error).__name__,
                           message=str(error)[:2000], completion="PARTIAL_NOT_USABLE"))
            except BaseException:
                pass
        print(json.dumps(dict(schema=SCHEMA, returncode=8 if isinstance(error, Hold) else 9,
                  error_type=type(error).__name__), ensure_ascii=False), flush=True)
        return 8 if isinstance(error, Hold) else 9


if __name__ == "__main__":
    raise SystemExit(main())

