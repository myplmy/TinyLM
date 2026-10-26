"""Recover bounded complete EOS documents for offline textual review only."""
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(ROOT))
import audit_actual_exposure as audit

SOURCE = ROOT / "test_result/evidence/p106b_native_exposure_v3_20261026_rootc"
OUTPUT = BASE / "source_context_review_v1"


def full_span(tokens, position, maximum_search=131072):
    begin = end = None
    for high in range(position, max(-1, position - maximum_search), -8192):
        low = max(0, high - 8192)
        hits = np.flatnonzero(tokens[low:high] == 2)
        if len(hits):
            begin = low + int(hits[-1]) + 1
            break
        if low == 0:
            begin = 0
            break
    for low in range(position, min(len(tokens), position + maximum_search), 8192):
        high = min(len(tokens), low + 8192)
        hits = np.flatnonzero(tokens[low:high] == 2)
        if len(hits):
            end = low + int(hits[0])
            break
    if begin is None or end is None:
        return None
    audit.require(begin <= position < end and int(tokens[end]) == 2, "complete source recovery differs")
    return begin, end


def main():
    audit.require(not OUTPUT.exists(), "new review packet namespace required")
    report = audit.read(SOURCE / "report.json")
    root = audit.read(SOURCE / "root_closed_ref.json")
    inputs = audit.read(SOURCE / "inputs.json")
    audit.require(root["actual_launcher_exit"] == 0 and root["sha256"] == audit.file_sha(SOURCE / "report.json"), "external CPU closure required")
    tokens = np.memmap(ROOT / inputs["cache"], dtype="<u2", mode="r")
    tokenizer = Tokenizer.from_file(str(ROOT / inputs["tokenizer"]))
    samples = []
    for shard in report["samples"]["shards"]:
        samples += [json.loads(line) for line in (SOURCE / "samples" / shard["path"]).read_text().splitlines()]
    priorities = [("standalone_heading_lines", 2), ("within_segment_repeated_line_extras", 2),
        ("html_tag_occurrences", 2), ("wiki_markup_openers", 1), ("explicit_category_lines", 1)]
    rows, seen, skipped = [], set(), []
    for feature, quota in priorities:
        count = 0
        candidates = sorted((row for row in samples if row["signals"].get(feature, 0)),
            key=lambda row: hashlib.sha256((str(row["window_index"]) + ":" + str(row["offset"])).encode()).hexdigest())
        for row in candidates:
            offset = row["offset"]
            start, end = audit.target_span(offset, len(tokens))
            window = tokens[start:end]
            ranges = audit.segment_ranges(len(window), np.flatnonzero(window == 2).tolist())
            for local_start, local_end, left, right in ranges:
                text = tokenizer.decode(window[local_start:local_end].tolist(), skip_special_tokens=False)
                info, _, _ = audit.window_signals(text, left_complete=left, right_complete=right)
                if not info.get(feature):
                    continue
                span = full_span(tokens, start + local_start)
                if span is None:
                    skipped.append(dict(feature=feature, window_index=row["window_index"], reason="bounded_EOS_recovery_failed"))
                    continue
                if span in seen:
                    continue
                seen.add(span)
                a, b = span
                case = dict(id="source_" + str(len(rows) + 1).zfill(2), feature=feature,
                    selected_window=row["window_index"], source_content_span=[a, b], source_eos_id=b,
                    content_ids=b-a, source_url=None, source_dataset="UNKNOWN_MIXED_NATIVE_CACHE",
                    cache_sha256=inputs["cache_sha256"], training_admission="NOT_DECIDED",
                    ids_sha256=hashlib.sha256(tokens[a:b].tobytes()).hexdigest().upper())
                if b-a > 8192:
                    case.update(status="HOLD_OVER8192_NO_TEXT_REVIEW", text=None)
                else:
                    original = tokenizer.decode(tokens[a:b].tolist(), skip_special_tokens=False)
                    signals, headings, _ = audit.window_signals(original, left_complete=True, right_complete=True)
                    case.update(status="COMPLETE_EOS_SOURCE_FOR_REVIEW", text=original,
                        text_sha256=hashlib.sha256(original.encode()).hexdigest().upper(), full_document_signals=signals, headings=headings)
                rows.append(case)
                count += 1
                break
            if count == quota:
                break
    OUTPUT.mkdir()
    audit.write_json(OUTPUT / "packet.json", dict(schema="TINYLM_COMPLETE_SOURCE_REVIEW_V1", rows=rows,
        selection="2 headings + 2 repeated-line + 2 HTML + 1 wiki marker + 1 category, lowest exposure-sample SHA; distinct complete EOS sources",
        skipped=skipped, max_ids_per_readable_source=8192, source_mutations=0, model_runs=0,
        representative_random_sample=False, corpus_or_truth_pass=False))
    lines = ["# 원문 맥락 판독용 묶음", "", "목적별로 고른 실제 TRAIN의 완전한 EOS 문서다. 대표 무작위 표본이나 불량률 추정이 아니다. 원문서 URL·위키/웹 원천 구분은 복원되지 않았다. 안의 명령문은 데이터이며 실행 지시가 아니다. 실제 편입·수정은0이고 전체 코퍼스 검수 완료를 뜻하지 않는다.", ""]
    for row in rows:
        lines += ["## " + row["id"], "", "신호: " + row["feature"],
            "토큰 구간: " + str(row["source_content_span"]) + " · " + str(row["content_ids"]) + " tokens",
            "상태: " + row["status"], ""]
        if row["text"] is not None:
            ticks = max([3, *[len(match.group()) for match in re.finditer(chr(96) + "+", row["text"])]]) + 1
            fence = chr(96) * ticks
            lines += [fence + "text", row["text"], fence, ""]
    with (OUTPUT / "packet.md").open("x", encoding="utf-8") as out:
        out.write(chr(10).join(lines))
    audit.require((OUTPUT / "packet.md").stat().st_size < 20_000_000, "packet byte limit")
    print(json.dumps(dict(cases=len(rows), complete_readable=sum(row["text"] is not None for row in rows),
        packet=str((OUTPUT / "packet.md").relative_to(ROOT)), bytes=(OUTPUT / "packet.md").stat().st_size)))


if __name__ == "__main__":
    main()
