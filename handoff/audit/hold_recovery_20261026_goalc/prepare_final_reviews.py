"""Freeze saved review artifacts and author-independent follow-up assignments.

This audit helper never edits corpus text or previously saved review versions.
"""
from collections import Counter
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import file_sha, write_json
from scripts import p106b_hold_recovery as recovery

spec = importlib.util.spec_from_file_location("context_tables", Path(__file__).with_name("collect_context_reviews.py"))
tables = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tables)
BASE = recovery.BASE


def catalog():
    result = {}
    for name in ["packets_initial_v2/manifest.json"] + [f"proposals_v{i}/review_packets/manifest.json" for i in (1, 2, 3)]:
        for raw in json.loads((BASE / name).read_text(encoding="utf-8"))["rows"]:
            row = dict(raw)
            row["original_path"] = row.get("original_path", row.get("path"))
            assert row["id"] not in result
            result[row["id"]] = row
    return result


def decision(row):
    value = row.get("판정", row.get("처리", row.get("제안 상태 / 복구 판정")))
    if value is None and "변경" in row:
        value = "EDIT"
    assert value, row
    if value.startswith("PROPOSAL_PASS"):
        return "PROPOSAL_PASS"
    if value.startswith("HOLD_CONFIRMED"):
        return "HOLD_CONFIRMED"
    leading = re.match(r"^(KEEP|EDIT|HOLD)(?=\s|[;+]|$)", value)
    if leading:
        return leading[1]
    first = value.split("/")[0].strip()
    value = first if first in ("KEEP", "EDIT", "HOLD") else value.split("/")[-1].strip()
    return {"부분 복구": "EDIT"}.get(value, value)


def artifacts(role, phase, sources, ids=None):
    review = BASE / "agents" / role / phase / "review.md"
    output = []
    numeric_source = "expanded_train" if (role, phase) == ("historical_review", "validation_v5") else None
    for item in tables.rows(review, default_source=numeric_source):
        ident = item["ID"]
        if ids is not None and ident not in ids:
            continue
        raw = sources[ident]
        original = ROOT / raw["original_path"]
        assert file_sha(original) == raw["original_text_sha256"]
        chosen = decision(item)
        stem = ident.replace(":", "_")
        text = review.parent / (stem + ".txt")
        if chosen == "PASS" and phase == "validation_v5":
            assert text.is_file()
            chosen = "EDIT"
        # A repair review's KEEP can mean KEEP the existing edited draft.
        if chosen == "KEEP" and text.is_file() and text.read_bytes() != original.read_bytes():
            chosen = "EDIT"
        row = dict(id=ident, role=role, version=phase, decision=chosen,
            input_text_sha256=raw["original_text_sha256"], original_path=raw["original_path"],
            review=str(review.relative_to(ROOT)),
            reason=next((v for k, v in item.items() if any(x in k for x in ("근거", "사유", "이유"))),
                " ; ".join(v for k, v in item.items() if k not in ("ID", "판정", "파일", "전체 판독"))),
            root_reviewed=False, recovery_review=True,
            source_proof="handoff/audit/hold_recovery_20261026_goalc/review_source_proof_all_v3.json")
        if chosen == "EDIT":
            assert text.is_file() and 0 < text.stat().st_size < 20_000_000, (ident, text)
            assert not recovery.corpus.MEMOS.search(text.read_text(encoding="utf-8")), ident
            row.update(path=str(text.relative_to(ROOT)), sha256=file_sha(text))
        sidecar = review.parent / (stem + "_hold.md")
        if sidecar.is_file():
            row.update(sidecar_path=str(sidecar.relative_to(ROOT)), sidecar_sha256=file_sha(sidecar))
        output.append(row)
    assert output, (role, phase, "empty author review is not complete")
    if ids is not None:
        assert {r["id"] for r in output} == ids
    return output


def write_assignments(rows, name, targets):
    assert len({r["id"] for r in rows}) == len(rows)
    assert rows and all(r["decision"] in ("KEEP", "EDIT", "HOLD") for r in rows)
    write_json(BASE / (name + "_candidates.json"), dict(schema="P106B_FROZEN_REVIEW_ARTIFACTS_V1", rows=rows, admission="NOT_APPROVED"))
    by_reviewer = {}
    for row in rows:
        reviewer = targets[row["role"]]
        assert reviewer != row["role"]
        by_reviewer.setdefault(reviewer, []).append(row)
    for reviewer, items in by_reviewer.items():
        lines = ["# " + reviewer + " " + name + " 독립 대조", "",
            "읽기는 이 assignment와 아래 정확 원문/실제본문/존재하는 sidecar/작성자 review의 해당 ID 행만 허용한다. 원문과 실제본문 전문을 대조한다. 출력 잘림은 같은 허용 파일을 구간별로 재독한다.",
            "쓰기 허용은 data_cache/p106b_hold_recovery_v1_20261026_goalc/agents/" + reviewer + "/counter_" + name + ".md 새 파일 하나뿐이다. 본문 수정/코드/분석스크립트/시험/계수/해시/모델/GPU/Git/웹/JSON/memory/목록외 읽기는 금지. 일반 텍스트 읽기·검토표 작성만 허용한다.", "",
            "| ID | 작성판정 | 정확원문 | 실제본문 | sidecar | 작성자review |", "|---|---|---|---|---|---|"]
        for row in items:
            lines.append("| " + " | ".join([row["id"], row["decision"], "`" + row["original_path"] + "`", "`" + row.get("path", row["original_path"]) + "`", "`" + row["sidecar_path"] + "`" if row.get("sidecar_path") else "없음", "`" + row["review"] + "`"]) + " |")
        lines += ["", "고정 출력: | ID | 판정 | 근거 | 전체 판독 |. PASS/REVISE/HOLD를 쓰고, 과도한 HOLD는 RECOVERABLE과 정확한 경계를 기록한다. 유효 서지/명칭/수치/인용주체/부정/조건/불확실성/코드/Unicode를 보존하고 빈 UI/필드/고아 참조만 정리했는지 확인한다. 제목·날짜·소실수식·사실을 생성하지 않는다. 본문에 없는 UI/한정을 있다고 주장하지 말고 실제 저장물을 근거로 쓴다. sidecar는 손실을 자동 정당화하지 않는다. 770104는 원문에서 지정된 빈 링크 예고 한 문장만 제외한 초안이다. 775126은 기존 두 실제 함수호출 사이 줄바꿈만 허용한다. 애매한 경우 총괄에게 정확 문자열과 문맥을 질의한다."]
        path = BASE / "assignments" / (reviewer + "_counter_" + name + ".md")
        with path.open("x", encoding="utf-8") as stream:
            stream.write(chr(10).join(lines) + chr(10))
    print(dict(name=name, decisions=dict(Counter(r["decision"] for r in rows)), assignments={k: len(v) for k, v in by_reviewer.items()}))


def versions():
    sources = catalog()
    rows = artifacts("legacy_review", "context_repair_v3", sources)
    replacement = artifacts("legacy_review", "context_repair_v4", sources)
    rows = [r for r in rows if r["id"] not in {x["id"] for x in replacement}] + replacement
    rows += artifacts("context_latin", "context_repair_v3", sources)
    rows += artifacts("context_controls", "root_extra_v1", sources)
    rows += artifacts("context_controls", "root_extra_v2", sources)
    write_assignments(rows, "versions_wave4", {"legacy_review": "context_controls", "context_latin": "historical_review", "context_controls": "historical_review"})


def validation():
    sources = catalog()
    rows = []
    coverage = {}
    for role in recovery.ROLE_NAMES:
        expected = set(re.findall(r"^\| ((?:expanded_train|historical_train|validation):[0-9]+) \|", (BASE / "assignments" / (role + "_validation_v3.md")).read_text(encoding="utf-8"), re.M))
        extra = []
        revised = BASE / "agents" / role / "validation_v4/review.md"
        if revised.is_file():
            extra = artifacts(role, "validation_v4", sources)
            assert {r["id"] for r in extra} <= expected
        current = artifacts(role, "validation_v3", sources, expected - {r["id"] for r in extra}) + extra
        assert {r["id"] for r in current} == expected
        coverage[role] = dict(Counter(r["decision"] for r in current))
        rows.extend(current)
    write_json(BASE / "validation_v3_complete_review.json", dict(schema="P106B_V3_CONTEXT_COVERAGE_V1", rows=rows, counts=coverage, admission="NOT_APPROVED"))
    manual = [r for r in rows if r["decision"] in ("KEEP", "EDIT", "HOLD")]
    write_assignments(manual, "validation_v3_saved", {"context_hangul": "context_latin", "context_latin": "legacy_review", "historical_review": "context_controls", "legacy_review": "context_hangul", "context_controls": "historical_review"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["versions", "validation"])
    args = parser.parse_args()
    {"versions": versions, "validation": validation}[args.stage]()
