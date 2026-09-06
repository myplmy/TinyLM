#!/usr/bin/env python3
"""★스모크 진단런 계약 검사 — 표(`smoke_diag_contract.tsv`)와 **배치·로그**를 대조한다.

## 왜 생겼나 (2026-09-06 사용자 지시 2)

2026-09-05 스모크에서 `diag_sparse34_pack.py` 가 **exit 1** 이었는데 마지막 판정은
*"총 에러 0건 — 계측 계약이 지켜지고 있습니다"* 였다. 그물이 셋인데 다 통과했다:

| 그물 | 무엇을 보나 | 🚫왜 못 잡았나 |
|---|---|---|
| `check_smoke.py` | 계측 **필드** 가 json 에 있는가 | **종료코드를 하나도 안 본다** |
| `summarize_smoke.py` | 팔의 **종료코드** | 배치가 `--` 를 빠뜨려 **한 번도 안 돌았다**(지시 1) |
| `check_smoke_coverage.py` | 배치가 쓰는 **축** 을 스모크가 도는가 | 학습 팔의 *플래그* 를 본다. 진단런은 안 본다 |

★**아무도 *"이 진단 팔이 실제로 무엇을 인쇄했는가"* 를 안 봤다.**
그래서 진단런은 **조용히 죽거나 항목이 사라져도** 통과한다 — 실제로 두 번 그랬다:
`check_return_probs.py` 는 없는 이름을 import 해 **신설 이래 한 번도 안 돌았고**(2026-09-03),
`diag_sparse34_pack.py` 는 **두 항목이 실패한 채** 스모크 두 번을 지나갔다.

## 세 가지를 본다

1. **집합** — 배치가 runlog 로 돌리는 비학습 스크립트 == 표의 script 열인가.
   늘었으면 표에 안 적힌 팔이고, 줄었으면 표만 남고 팔이 사라진 것이다.
2. **항목 실재** — 표의 `items` 표지가 **그 스크립트 소스에 실제로 있는가.**
   항목을 지우고 표를 안 고치는 것을 잡는다(반대 방향은 1번이 잡는다).
3. **로그 인쇄** — 최신 스모크 로그에서 그 팔의 블록 안에 항목이 **실제로 찍혔는가.**
   ★**여기가 다른 게이트에 없는 것**이다. 소스에 있는 것과 도는 것은 다르다(함정 37).

## 🚫하지 않는 것

- **값이 옳은지 모른다.** *"그 검사가 돌았는가"* 만 본다.
- **로그가 없으면 3번을 건너뛴다**(경고). 로그 없음을 실패로 치면 첫 실행이 막힌다.
- ⚠️★**자기 사본과 대조하지 않는다** — 표는 사람이 쓰고, 대조 대상은 **배치와 로그**다.
  표와 배치가 같은 손에서 나오지만 **로그는 실행이 만든 것**이라 3번은 독립이다.

사용:  python scripts/check_smoke_diag.py [--log <경로>]
종료코드 0 정상 / 1 불일치
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "scripts" / "smoke_diag_contract.tsv"
BATCH = ROOT / "scripts" / "batch" / "tool_smoke.bat"
LOGDIR = ROOT / "smoketest_logs"

RE_CMD = re.compile(r"^\[runlog\] cmd=(.+?)\s*$")
RE_END = re.compile(r"^\[runlog\] 종료코드 (\d+)\s")


def load_tsv():
    rows = []
    for ln in TSV.read_text(encoding="utf-8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        c = ln.split("\t")
        if c[0] == "script":
            continue
        if len(c) < 6:
            raise SystemExit(f"[!] TSV 열이 6개가 아니다: {ln[:60]!r}")
        rows.append({"script": c[0].strip(), "kind": c[1].strip(),
                     "items": [x.strip() for x in c[2].split(";") if x.strip()],
                     "exit0": c[3].strip(), "axis": c[4].strip(), "note": c[5].strip()})
    return rows


def batch_scripts():
    """배치가 runlog 로 돌리는 `scripts\\*.py` 집합. 학습(run100m.py)은 제외."""
    txt = BATCH.read_text(encoding="utf-8", errors="replace")
    out = []
    for ln in txt.splitlines():
        s = ln.strip()
        if s.upper().startswith("REM") or "runlog.py" not in s:
            continue
        m = re.search(r"--\s+python\s+scripts[\\/]([A-Za-z0-9_]+\.py)", s)
        if m:
            out.append(m.group(1))
    return out


def newest_log(explicit=None):
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    if not LOGDIR.exists():
        return None
    c = sorted(LOGDIR.glob("*_smoke_*.txt"), key=lambda p: p.stat().st_mtime)
    return c[-1] if c else None


def log_blocks(path):
    """로그를 `[runlog] cmd=` 단위로 쪼개 {스크립트명: (본문, 종료코드)} 로 준다."""
    blocks, cur, body = {}, None, []
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RE_CMD.match(ln)
        if m:
            cur, body = m.group(1), []
            continue
        e = RE_END.match(ln)
        if e and cur is not None:
            k = re.search(r"scripts[\\/]([A-Za-z0-9_]+\.py)", cur)
            if k and "run100m.py" not in cur:
                blocks[k.group(1)] = ("\n".join(body), int(e.group(1)))
            cur, body = None, []
            continue
        if cur is not None:
            body.append(ln)
    return blocks


def main():
    ap = argparse.ArgumentParser(description="스모크 진단런 계약 검사")
    ap.add_argument("--log", default=None, help="검사할 스모크 로그(기본: 최신)")
    a = ap.parse_args()

    rows = load_tsv()
    declared = [r["script"] for r in rows]
    fails, warns = [], []

    print("=" * 92)
    print("  스모크 진단런 계약 — 표 vs 배치 vs 로그")
    print("=" * 92)

    # ── 1. 집합 대조 ────────────────────────────────────────────────────────
    actual = batch_scripts()
    dup = [s for s in set(actual) if actual.count(s) > 1]
    missing = [s for s in declared if s not in actual]
    extra = [s for s in actual if s not in declared]
    print(f"{chr(10)}  [1] 집합 — 표 {len(declared)}개 · 배치 {len(actual)}개")
    for s in missing:
        fails.append(f"표에 있는데 배치가 안 돌린다: {s}")
        print(f"      🚫 표에만 있다: {s}")
    for s in extra:
        fails.append(f"배치가 돌리는데 표에 없다: {s} — 점검 항목이 정의되지 않았다")
        print(f"      🚫 배치에만 있다: {s}")
    for s in dup:
        warns.append(f"배치가 {s} 를 {actual.count(s)}번 돌린다")
        print(f"      ⚠️ 중복 호출: {s} x{actual.count(s)}")
    if not missing and not extra:
        print("      ✅ 일치")

    # ── 1b. ★같은 것을 두 번 검사하는 팔이 있는가 (2026-09-06 사용자 지시 5) ──
    #   물음: *"검증런 중에 동일한 항목을 검증하는 것이 없는가."*
    #   ★두 축으로 본다 — 표가 선언한 `axis` 가 겹치는가, 그리고 `items` 표지가 겹치는가.
    #   🚫**이름이 닮았다고 중복이 아니다.** 실측(2026-09-06):
    #     `diag_sparse34.py`    = **학습 경로** 감사(실제 비영률·결정 뒤집힘·bpw 규약),
    #                             실제 체크포인트가 필요하고 **스모크에 없다**
    #     `diag_sparse34_pack.py` = **배포 포맷** 감사(왕복·bpw·상주), 합성 텐서
    #   → 같은 단어를 쓸 뿐 **다른 양**이다(함정 28). 중복이 아니다.
    print(f"{chr(10)}  [1b] 항목 중복 — 두 팔이 같은 것을 재는가")
    ax = {}
    for r in rows:
        ax.setdefault(r["axis"], []).append(r["script"])
    dup_ax = {k: v for k, v in ax.items() if len(v) > 1}
    it = {}
    for r in rows:
        for i in r["items"]:
            it.setdefault(i, []).append(r["script"])
    dup_it = {k: v for k, v in it.items() if len(v) > 1}
    for k, v in dup_ax.items():
        warns.append(f"축 '{k}' 를 {len(v)}개 팔이 잰다: {v}")
        print(f"      ⚠️ 같은 축 '{k}': {v}")
    for k, v in dup_it.items():
        warns.append(f"표지 '{k}' 를 {len(v)}개 팔이 인쇄한다: {v}")
        print(f"      ⚠️ 같은 표지 '{k}': {v}")
    if not dup_ax and not dup_it:
        print(f"      ✅ 축 {len(ax)}종 · 표지 {len(it)}종 — 겹치는 팔 없다")

    # ── 2. 항목이 소스에 실재하는가 ─────────────────────────────────────────
    print(f"{chr(10)}  [2] 항목 실재 — 표의 표지가 스크립트 소스에 있는가")
    n_items = 0
    for r in rows:
        p = ROOT / "scripts" / r["script"]
        if not p.exists():
            fails.append(f"스크립트가 없다: {r['script']}")
            print(f"      🚫 {r['script']}: 파일이 없다")
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        gone = [it for it in r["items"] if it not in src]
        n_items += len(r["items"])
        if gone:
            fails.append(f"{r['script']}: 표가 요구하는 항목이 소스에 없다 — {gone}")
            print(f"      🚫 {r['script']}: {gone}")
    if not any(f.startswith(tuple(d + ':' for d in declared)) for f in fails):
        print(f"      ✅ 항목 {n_items}개 전부 소스에 있다")

    # ── 3. 로그에 실제로 찍혔는가 ───────────────────────────────────────────
    log = newest_log(a.log)
    print(f"{chr(10)}  [3] 로그 인쇄 — {log.name if log else '(로그 없음)'}")
    if not log:
        warns.append("스모크 로그가 없어 3번을 건너뛴다")
        print("      ⚠️ 로그가 없다. `run_smoke_check.bat` 을 돌린 뒤 다시 보세요")
    else:
        # ★★로그가 코드보다 낡았는가 — 이 판정이 [3] 을 에러로 볼지 경고로 볼지 정한다.
        #   🚫낡은 로그의 실패를 에러로 올리면, 스크립트를 고칠 때마다 게이트가 빨개지고
        #   사용자가 GPU 로 스모크를 다시 돌리기 전에는 안 꺼진다 = **사실상 영구히 빨간
        #   게이트**이고, 그것은 게이트가 아니다(2026-09-06 `check_heldout_defects` 교훈).
        #   낡았으면 *"고친 뒤 아직 안 돌렸다"* 라고 말하고 경고로 둔다.
        blocks = log_blocks(log)
        watched = [ROOT / "scripts" / r["script"] for r in rows]
        watched += [ROOT / "tinylm" / "model" / "lut.py", BATCH]
        newest_code = max((p.stat().st_mtime for p in watched if p.exists()), default=0)
        stale = log.stat().st_mtime < newest_code
        sink = warns if stale else fails
        if stale:
            print("      ⚠️★이 로그는 **코드보다 낡았다** — 고친 뒤 스모크를 아직 안 돌렸다.")
            print("         아래 실패는 **그때의 코드**에 대한 것이라 경고로 둔다.")
        for r in rows:
            s = r["script"]
            if s not in blocks:
                sink.append(f"{s}: 이 로그에 그 팔의 블록이 없다 — 팔이 안 돌았다")
                print(f"      🚫 {s}: 블록이 없다(안 돌았다)")
                continue
            body, code = blocks[s]
            gone = [it for it in r["items"] if it not in body]
            mark = "🚫" if (gone or code) else "✅"
            print(f"      {mark} {s:<26} exit {code}"
                  + (f"  · 안 찍힌 항목 {gone}" if gone else ""))
            if gone:
                sink.append(f"{s}: 로그에 안 찍힌 항목 {gone} — 소스엔 있는데 경로가 안 돌았다")
            if code:
                sink.append(f"{s}: exit {code} — {r['exit0']} 가 성립하지 않았다")

    print()
    print("  " + "-" * 88)
    for w in warns:
        print(f"  ⚠️ {w}")
    if fails:
        print(f"  🚫 **불일치 {len(fails)}건**")
        for f in fails:
            print(f"     - {f}")
        print("  ★표가 틀렸는지 코드가 틀렸는지 먼저 정하세요(함정 34: 4번 중 4번 표가 틀렸다).")
        return 1
    print("  ✅ 표·배치·로그 셋이 일치한다.")
    print("  🚫단 이것은 '그 검사가 돌았다' 이지 '값이 옳다' 가 아니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
