# -*- coding: utf-8 -*-
"""★★핸드오프 파일명 시각의 **정본 검증**. 통계 휴리스틱을 쓰지 않는다.

## 왜 이 파일이 따로 있나

2026-09-06 제안서는 *"분이 `:00`·`:30` 이면 지어낸 것"* 이라는 **통계 규칙**을 제안했다.
🚫**사용자가 그 조건을 거절했다**(2026-09-07 지시 3):

> *"00, 30이라고 지어낸것으로 판정하지 말고 특정 핸드오프메모 파일의 최초 git 커밋(스테이징)
>  시간과 10분이상 차이나는지 혹은 최초 작성일자 기준으로 10분이상 차이나는지 등
>  **코드로 실측가능한 사항**으로 확인하고, 통계 예측으로 00분 30분과 같은 기준 사용하지 말 것."*

★**그 판단이 옳다.** `:00` 규칙은 두 가지가 나쁘다:

| | |
|---|---|
| 🚫**미탐** | 실제 13건 중 `…2359`(:59)는 통과한다. 다음번엔 `:07` 로 지어내면 그만이다 |
| 🚫**오탐** | 진짜로 `:00` 에 쓸 수 있다(68분의 1) — 그리고 **그 오탐을 반증할 방법이 규칙 안에 없다** |

★**대신 이 모듈은 바깥의 증거 하나만 본다** — *"그 파일이 **언제부터 존재했는가**"*.
파일명이 **존재 증거보다 미래**를 주장하면 그것은 **물리적으로 불가능**하다.
🚫추측이 아니라 모순이다.

## 규칙 (한 줄)

    파일명 시각 > 최초 존재 증거 + 10분   →   에러

`최초 존재 증거` 는 **있는 것 중 가장 이른 것**:

| 순위 | 증거 | 언제 쓰나 |
|---:|---|---|
| 1 | **그 파일을 담은 최초 git 커밋의 author 시각** | 커밋된 파일 |
| 2 | 파일시스템 `mtime` | 아직 커밋 안 된 파일(**막 쓴 핸드오프가 여기**) |

★**한쪽만 본다**(one-sided). 파일명이 증거보다 **이른** 것은 정상이다 —
쓴 뒤에 고치면 `mtime` 이 뒤로 간다. **미래를 주장하는 것만** 잡는다.

★**그래서 커밋 전에도 돈다** — 갓 만든 파일의 `mtime` 이 곧 "지금" 이므로,
AI 가 23:30 이라고 지어내고 실제로 14:00 이면 **그 자리에서 잡힌다**.
🚫제안서 §8 위험 2(*"커밋 전에 못 돈다"*)가 이 설계로 사라졌다.
"""
from __future__ import annotations

import datetime as _dt
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOL_MIN = 10          # ★사용자가 정한 값(지시 3)
NAME_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})_HANDOFF\.md$")


def claimed(path) -> _dt.datetime | None:
    """파일명이 주장하는 시각."""
    m = NAME_RE.match(Path(path).name)
    if not m:
        return None
    y, mo, d, h, mi = (int(x) for x in m.groups())
    try:
        return _dt.datetime(y, mo, d, h, mi)
    except ValueError:
        return None


def first_commit(path) -> _dt.datetime | None:
    """그 경로를 **처음 담은** 커밋의 author 시각(로컬). 없으면 None."""
    try:
        rel = str(Path(path).resolve().relative_to(ROOT)).replace(chr(92), "/")
    except ValueError:
        # ★저장소 밖(스크래치패드 자체시험 등) — git 증거가 없으니 mtime 으로 떨어진다.
        return None
    try:
        out = subprocess.run(
            ["git", "log", "--follow", "--diff-filter=A", "--format=%ad",
             "--date=format:%Y-%m-%d %H:%M:%S", "--", rel],
            cwd=str(ROOT), capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    lines = [l.strip() for l in out.stdout.splitlines() if l.strip()]
    if not lines:
        return None
    # `--follow` 는 최신부터 준다. **가장 이른 것**을 쓴다.
    stamps = []
    for l in lines:
        try:
            stamps.append(_dt.datetime.strptime(l, "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
    return min(stamps) if stamps else None


def evidence(path):
    """(최초 존재 증거, 출처이름). 커밋이 있으면 그것, 없으면 mtime."""
    c = first_commit(path)
    if c is not None:
        return c, "최초 커밋"
    p = Path(path)
    if p.exists():
        return _dt.datetime.fromtimestamp(p.stat().st_mtime), "파일 mtime(미커밋)"
    return None, "없음"


def audit_one(path):
    """(상태, 메시지). 상태는 'ok' | 'bad' | 'skip'."""
    cl = claimed(path)
    if cl is None:
        return "skip", f"{Path(path).name}: 이름이 규약 형식이 아니다"
    ev, src = evidence(path)
    if ev is None:
        return "skip", f"{Path(path).name}: 존재 증거를 못 찾았다"
    gap_min = (cl - ev).total_seconds() / 60.0
    if gap_min > TOL_MIN:
        return "bad", (f"{Path(path).name}: 파일명이 **{cl:%Y-%m-%d %H:%M}** 을 주장하는데 "
                       f"{src}는 **{ev:%Y-%m-%d %H:%M}** 이다 — "
                       f"**{gap_min/60:.1f}시간 미래**(허용 {TOL_MIN}분). "
                       f"파일이 존재하기 전의 시각을 이름에 쓸 수 없다")
    return "ok", (f"{Path(path).name}: 주장 {cl:%H:%M} vs {src} {ev:%H:%M} "
                  f"(차 {gap_min:+.0f}분)")


def audit_all(paths=None):
    """(bad, ok, skip) 리스트 셋."""
    ps = list(paths) if paths else sorted((ROOT / "handoff").glob("*_HANDOFF.md"))
    bad, ok, skip = [], [], []
    for p in ps:
        st, msg = audit_one(p)
        {"bad": bad, "ok": ok, "skip": skip}[st].append(msg)
    return bad, ok, skip


if __name__ == "__main__":
    import sys
    b, o, s = audit_all(sys.argv[1:] or None)
    print("=" * 96)
    print("  ★핸드오프 파일명 시각 감사 — **증거 대조**(통계 휴리스틱 아님)")
    print(f"  규칙: 파일명 시각 > 최초 존재 증거 + {TOL_MIN}분 이면 에러. 한쪽만 본다")
    print("=" * 96)
    for m in b:
        print(f"  🚫 {m}")
    for m in s:
        print(f"  ⚠️ {m}")
    print(f"\n  검사 {len(b)+len(o)+len(s)}건 · 🚫모순 {len(b)}건 · ✅정합 {len(o)}건 · ⚠️건너뜀 {len(s)}건")
    # ★계측 0 에 exit 0 금지(R19)
    if not (b or o or s):
        print("  🚫검사한 파일이 0건이다 — 경로를 확인할 것")
        sys.exit(2)
    sys.exit(1 if b else 0)
