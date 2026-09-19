#!/usr/bin/env python3
"""Rebuild the experiment-plan index as one row per physical plan document.

This is a mechanical index formatter. Scientific state remains owned by each
plan/result document; ambiguous plans are conservatively classified ongoing.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / "test_plan"
INDEX = PLAN_DIR / "실험계획목록.md"
ID_RE = re.compile(r"^(P\d{3}[A-Za-z]?)_")
ROW_ID_RE = re.compile(r"\b(P\d{3}[A-Za-z]?)\b")

STATUS_OVERRIDES = {
    "P014D": "Stage0 측정 0건 원인을 수정했고 WSL Stage0bW CPU profile 재실행 대기.",
    "P022C": "C1 cast/scaling 포함 경로는 속도·메모리 음성. shadow/write-back은 별도 진행 중.",
    "P025B": "WSL synthetic 2:4 정합 PASS, 전 형상 속도 음성. sparse-master·whole-step은 미실행.",
    "P044B": "무KD FiLM도 자를 못 넘고 비용만 남아 종결. 결과 063.",
    "P060": "Windows 결과 046 보존·계획 종결. WSL native 후속은 P060B로 이관.",
    "P060B": "default GQA actual model 정합 PASS·11.1% 빠름. backend warning Wc 재확인 대기.",
    "P064": "Stage0/0b 완료. KorQuAD 소차 판정 불가·NLI 퇴화로 지표를 내리고 P069/P085로 승계.",
    "P071": "결과 054에서 CE/KD 청킹 등가성과 VRAM 효과를 확인해 종결.",
    "P072": "Stage0/0b 지도와 해석 정정 완료. 후속 경계 질문은 별도 계획으로 승계.",
    "P073": "Stage0~6b 완료. clip 격자는 이상 발생 전까지 명시 보류라 현 계획 종결.",
    "P074": "Stage1b/1c/2/3/5 완료. 얇은 dense 후속은 P079로 승계.",
    "P079": "Stage0~7·시드·다운스트림 완료. 승자 후속은 P085/P089/리뷰로 승계.",
    "P084": "Stage1/2/4 완료. Stage3는 34 MiB 예산 재개 조건의 조건부 종결.",
    "P085": "Stage0~10c 완료. held-out 개선 후속은 P096으로 승계.",
    "P087": "Stage1~3 학습 완료. 누락된 결정적 full-val paired Stage3bW SH 사용자 실행 대기.",
    "P077": "Stage1c까지 완료. fp16 채택은 사용자 결정, 생성 기반 품질 gate는 미설계.",
    "P088": "Stage1~11과 후속 장기 관측 완료. 새 장기학습은 P097 데이터 축으로 승계.",
    "P076": "A2/A4 구현·Stage1W SH 준비. mean/middle/norm_mean 실제 parent step0 gate 사용자 실행 대기.",
    "P078": "입력별 방문 이득 설명력이 r² 0.7~5.9%에 그쳐 종결. 재개 조건 r²>25% 특징.",
    "P091": "R2t 배선 PASS, synthetic S 순위 불안정. actual checkpoint R2/R3가 다음.",
    "P092": "Stage1aT TLinear/controller 계약 PASS. full Transformer 30M wiring이 다음.",
    "P093": "R1 rank16 output NRMS 0.974로 음성. D1 고계산·P091 의존 D2만 조건부 잔존.",
    "P094": "P022C packed/masterless evidence 부재로 R0 exit8 HOLD. R1 미개방.",
    "P095": "S0b bridge 계약 PASS. full Transformer coda wiring·학습성은 미실행.",
    "P096": "Q2a synthetic bounded-canary 계약 PASS. 실문항·팀 의미검토가 다음.",
    "P097": "세 600M cache 완성, 네 학습 0 step. 오류 교정 Stage1aB~dB 재실행 대기.",
}

# These are semantic states, not inferred from a single result row.  Plans not
# listed here are conservatively ongoing unless their document is explicitly
# -done or says that the whole plan is closed.
PLANNED_IDS = {
    "P004", "P006", "P009", "P010", "P011", "P013", "P019", "P020",
    "P023", "P024", "P025", "P027", "P033", "P041", "P050B", "P056",
    "P059", "P061B", "P068", "P069", "P070", "P080", "P081", "P082",
    "P083",
}
CLOSED_IDS = {
    "P014", "P014B", "P014C", "P034", "P034B", "P043", "P044", "P044B",
    "P045", "P045B", "P046", "P047", "P049", "P051", "P060", "P061",
    "P064", "P071", "P072", "P073", "P074", "P078", "P079", "P084", "P085", "P088",
}


def clean(text: str) -> str:
    text = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("★", "")
    for marker in ("✅", "🚫", "⚠️", "⚠", "🔜", "🔄", "⏸", "💡", "🏆"):
        text = text.replace(marker, "")
    text = re.sub(r"\s+", " ", text).strip(" -—")
    return text.replace("|", r"\|")


def plan_id(path: Path) -> str:
    match = ID_RE.match(path.name)
    if match is None:
        raise ValueError(f"invalid plan filename: {path.name}")
    return match.group(1)


def title(path: Path) -> str:
    first = next(line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("# "))
    value = re.sub(
        r"^#\s+(?:실험계획\s+)?P\d{3}[A-Za-z]?(?:\s*\([^)]*\))?\s*(?:—|-)\s*",
        "",
        first,
    )
    return clean(value)


def old_dates_and_notes(text: str):
    dates: dict[str, list[str]] = {}
    notes: dict[str, list[str]] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        match = ROW_ID_RE.search(cells[0])
        if match is None:
            continue
        ident = match.group(1)
        dates.setdefault(ident, []).extend(re.findall(r"20\d{2}-\d{2}-\d{2}", line))
        if len(cells) >= 3:
            notes.setdefault(ident, []).append(cells[2])
    return dates, notes


def first_status(text: str) -> str | None:
    lines = text.splitlines()[:28]
    collected = []
    active = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("- **상태**:", "> **상태", "> **현재 상태", "- **현재 상태")):
            active = True
        if active:
            if stripped and not stripped.startswith((">", "-")):
                break
            collected.append(stripped.lstrip(">- "))
    value = clean(" ".join(collected))
    return value or None


def result_mentions() -> set[str]:
    found = set()
    for path in (ROOT / "test_result").glob("[0-9][0-9][0-9]_*.md"):
        head = path.read_text(encoding="utf-8", errors="replace")[:4000]
        found.update(re.findall(r"\bP\d{3}[A-Za-z]?\b", head))
    return found


def classify(path: Path, text: str, mentioned: set[str]) -> str:
    ident = plan_id(path)
    head = text[:5000]
    if ident in CLOSED_IDS:
        return "closed"
    if ident in PLANNED_IDS:
        return "planned"
    if path.name.endswith("-done.md") or re.search(
        r"(?:이 계획은 종결됐다|실행 완료[· ]*종결|전 단계 완료|상태[^\n]{0,40}종결|P078 을 여기서 닫는다)",
        head,
    ):
        return "closed"
    if re.search(r"상태[^\n]{0,50}진행 중", head):
        return "ongoing"
    if ident not in mentioned and not re.search(r"(?:✅|실행 완료|결과\s*\d{3}|PASS)", text):
        return "planned"
    return "ongoing"


def status_note(path: Path, text: str, state: str, old_notes: dict[str, list[str]]) -> str:
    ident = plan_id(path)
    if ident in STATUS_OVERRIDES:
        return STATUS_OVERRIDES[ident]
    if state == "planned":
        return "실행 전. 계획서의 첫 선결과 비용을 확인한다."
    status = first_status(text)
    if status:
        return status[:260]
    return {
        "planned": "실행 전. 계획서의 첫 선결과 비용을 확인한다.",
        "ongoing": "일부 단계 완료 또는 구현 진행 중. 계획서의 최신 단계표를 따른다.",
        "closed": "종결 판정과 재개 조건은 계획서·결과문서가 소유한다.",
    }[state]


def sort_key(path: Path):
    ident = plan_id(path)
    match = re.fullmatch(r"P(\d{3})([A-Za-z]?)", ident)
    return int(match.group(1)), match.group(2).lower(), match.group(2)


def render() -> str:
    old = INDEX.read_text(encoding="utf-8")
    dates, old_notes = old_dates_and_notes(old)
    mentioned = result_mentions()
    plans = sorted(PLAN_DIR.glob("P*.md"), key=sort_key)
    groups = {"planned": [], "ongoing": [], "closed": []}
    for path in plans:
        text = path.read_text(encoding="utf-8")
        state = classify(path, text, mentioned)
        ident = plan_id(path)
        explicit_dates = re.findall(r"20\d{2}-\d{2}-\d{2}", text)
        date = max([*dates.get(ident, []), *explicit_dates], default="미기록")
        groups[state].append(
            f"| [{ident}]({path.name}) | {title(path)} | "
            f"{clean(status_note(path, text, state, old_notes))} | {date} |"
        )
    lines = [
        "# 실험 계획 목록",
        "",
        "한 계획 문서는 아래 세 상태 중 정확히 한 표에 한 행만 둔다. 단계 하나의 완료를 계획 전체",
        "종결로 승격하지 않으며, 애매하거나 후속 단계가 남으면 진행 중으로 분류한다. 세부 수치와",
        "실행 명령은 각 계획서·결과문서·docs/EXPERIMENT_BASELINES.md가 소유한다.",
        "",
        "## 1. 계획만 있고 실행 전",
        "",
        "| 계획 | 질문·범위 | 현재 판정·첫 관문 | 최근갱신 |",
        "|---|---|---|---|",
        *groups["planned"],
        "",
        "## 2. 진행 중",
        "",
        "| 계획 | 질문·범위 | 현재 판정·첫 관문 | 최근갱신 |",
        "|---|---|---|---|",
        *groups["ongoing"],
        "",
        "## 3. 종결",
        "",
        "| 계획 | 질문·범위 | 종결 판정·재개 조건 | 최근갱신 |",
        "|---|---|---|---|",
        *groups["closed"],
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    output = render()
    if args.apply:
        INDEX.write_text(output, encoding="utf-8")
        print(f"[APPLY] {INDEX.relative_to(ROOT)} rows={sum(1 for line in output.splitlines() if line.startswith('| [P'))}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
