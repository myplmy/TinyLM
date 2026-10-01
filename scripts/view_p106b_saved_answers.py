#!/usr/bin/env python3
"""Read-only, noninteractive view of the exact observed v32 P106B answers.

No teacher/model loading, new scores, similarity checks or original-data writes.
Reports are hash-pinned; existing shard and concatenation hashes are verified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_shards import verify

BASE = "HF/sft_ready/p106b_teacher_sft/v32_prompt_wire_effort_panel"
REPORTS = {
    "effort-panel": "CB1A69B52A82BF55D6C7D76E4581425D443F1BDA2C3D5D832EA7F1B1286184EA",
    "a": "1A9DE65BC8532564B7B86676F65718F6FCAA199426996108D22D54E9222C89E2",
    "b": "E14092F824BAF3FD45F4CE1056AFB36BA7694047C81191DF1A3FBFBC1579020A",
}


def read_json(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("exact evidence absent/linked: " + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def report(name):
    path = ROOT / BASE / name / "report.json"
    value = read_json(path)
    if hashlib.sha256(path.read_bytes()).hexdigest().upper() != REPORTS[name]:
        raise ValueError("recorded v32 report SHA changed: " + name)
    return path.parent, value


def rows(folder, stem, expected):
    manifest = read_json(folder / (stem + "_shards_manifest.json"))
    verify(folder, manifest)
    if manifest.get("concat_sha256") != expected:
        raise ValueError("report/shard identity differs: " + stem)
    return [json.loads(line) for item in manifest["shards"]
            for line in (folder / item["path"]).read_text(encoding="utf-8").splitlines()]


def content(message):
    value = message["content"]
    return value if isinstance(value, str) else "".join(p["text"] for p in value if p["type"] == "text")


def panel_data():
    folder, value = report("effort-panel")
    raw = rows(folder, "raw", value["raw_concat_sha256"])
    canonical = rows(folder, "canonical", value["canonical_concat_sha256"])
    return value, raw, canonical


def print_panel(value, raw, canonical, base_relative=BASE):
    print("교사 대응 원답 — 원천별 세 effort. 옛 문자열 화면은 정답/품질 점수가 아닙니다.")
    by_id = {r["generation_id"]: r for r in raw}
    for group in sorted({r["group"] for r in value["records"]}):
        records = [r for r in value["records"] if r["group"] == group]
        first = by_id[records[0]["generation_id"]]
        print(f"\n원천 C{group:03d}\n원천 질문: {first['source']['source_payload']['question']}")
        for record in records:
            ident = record["generation_id"]
            evidence = by_id[ident]
            print(f"\n[{record['effort']}] 실제 요청 순서: {record['order']}; seed={record['seed']}")
            print(f"요청 시간={evidence['wall_sec']}초; 형식/양어휘 배선={record['wire_ok']}")
            selected = [r for r in canonical if r["meta"]["generation_id"] == ident
                        or r["meta"]["generation_id"].rsplit("_a", 1)[0] == ident]
            for row in selected:
                print("생성 질문: " + content(row["messages"][0]))
                print(f"답{row['meta'].get('answer_variant', 1)}: " + content(row["messages"][1]))
            if not selected:
                print("형식 미완결/파싱 실패; 원형 최종 필드: " +
                      evidence.get("teacher", {}).get("teacher_final_content", ""))
            print("과거 검사 관찰(현재 품질 판정 아님): " + json.dumps(record["content_issues"], ensure_ascii=False))
            print(f"원형/사고 참조: {base_relative}/effort-panel/raw_shards_manifest.json#{ident}")
    print("\n설정 선택 입력 없음. 교사 의미/정답 검증 NOT_RUN. 사고 전문은 학생 답에 포함하지 않습니다.")


def education_data():
    data = {}
    for arm in ("b", "a"):
        folder, value = report(arm)
        data[arm] = {label: rows(folder, "answers_" + label,
                    value[label + "_answers"]["raw_concat_sha256"]) for label in ("parent", "student")}
    return data


def print_education(data):
    print("학생 실제 원답 — 각자 부모/자식·각 시도를 함께 표시합니다. 좁은 rubric은 내용 전체의 정답률이 아닙니다.")
    for ident in sorted({r["id"] for r in data["b"]["parent"]}):
        print("\n질문 ID: " + ident)
        for arm in ("b", "a"):
            for label in ("parent", "student"):
                for row in data[arm][label]:
                    if row["id"] != ident:
                        continue
                    print(f"\n[{arm}/{label}/시도{row['attempt']}] 실제 입력:\n{row['prompt']}")
                    print("실제 출력: " + row["rendered_answer"])
                    print("기존 기록 rubric=" + str(row["narrow_rubric_pass"]) +
                          "; 생성 메타=" + json.dumps(row["generation"], ensure_ascii=False))
    print("\n새 채점·유사도·모델 실행0. 부모 구조/토크나이저가 달라 chat32 단독 인과비교가 아닙니다.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("panel", "education"), required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        data = panel_data() if args.mode == "panel" else education_data()
        if args.check_only:
            print("[PASS] exact recorded report/shards verified; semantic truth NOT_RUN; model execution0")
        elif args.mode == "panel":
            print_panel(*data)
        else:
            print_education(data)
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print("[EVIDENCE_ERROR] " + str(exc), file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
