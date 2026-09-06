"""정적 게이트 15 — **배치가 쓰는 학습 조합 중 스모크가 한 번도 안 돌린 것.**

★왜 생겼나 (2026-08-27, 결과 059 §7)
    최근 코드 사고를 한 줄씩 놓으면 형태가 같다 — **새 기능이 아니라 새 조합**이었다.

        `--cla-group`      축은 있었다. 그 값의 스모크 팔이 없었다     (2026-08-23)
        bf16 임베딩 3연속   임베딩도 양자화도 있었다. **타잉 x 새 dtype** 이 처음
        `common_bpb` OOM   도구는 있었다. **도구 x 어휘 151,936** 이 처음
        P074 네 팔 전멸     dense 도 --init-from 도 오래됐다. **둘의 조합**이 처음

    규약을 더 쓰는 것으로는 안 막힌다 — 규약은 **사람이 기억했을 때** 작동하고,
    조합은 기억의 대상이 아니라 **세기의 대상**이다. 그래서 센다.

무엇을 보나
    `scripts/batch/tool_smoke.bat` 의 학습 팔이 실제로 켠 플래그 집합과,
    최상위 `run_*.bat`(아직 `-done` 이 아닌 것)이 켜는 플래그 집합을 대조한다.
    **배치가 켜는데 스모크가 한 번도 안 켠 축**을 나열한다.

    ⚠️**이 게이트는 플래그 단위만 본다.** "어휘 크기 x 청크 없는 CE" 같은 **값 단위 조합**은
    여전히 못 센다(결과 059 §7.1). 🚫"재발 방지 완료" 라고 쓰지 않는다.

    python scripts/check_smoke_coverage.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts" / "batch" / "tool_smoke.bat"

# 학습의 뼈대 — 축이 아니다. 모든 런이 쓰므로 대조에서 뺀다.
BOILER = {
    "--arch", "--preset", "--tiny", "--data", "--tokens", "--pool-tokens",
    "--exact-cache", "--steps", "--micro-bs", "--accum", "--seq", "--lr",
    "--sched", "--anneal-end", "--decay-frac", "--seed", "--eval-every",
    "--compile", "--tag", "--save-every",
}
# 스모크로 재현할 수 없는 축(외부 자산·장시간 전용). 사유를 반드시 적는다.
ALLOW = {
    "--kd-teacher-hf": "외부 HF 교사 가중치가 필요하다. tiny/synthetic 로 대체 불가",
    "--tokenizer-hf": "외부 HF 토크나이저가 필요하다",
    "--kd-teacher-tag": "압축 교사 체크포인트가 선행 학습으로 있어야 한다",
    "--init-from-tag": "특정 태그 체크포인트가 선행으로 있어야 한다",
}

TRAIN = re.compile(r"run100m\.py\s+train\s+(.*)$")


def flags_of(line: str) -> tuple[str, set[str]]:
    m = TRAIN.search(line)
    if not m:
        return "", set()
    toks = m.group(1).split()
    arch = "tied"
    for i, t in enumerate(toks):
        if t == "--arch" and i + 1 < len(toks):
            arch = toks[i + 1]
    fl = {t for t in toks if t.startswith("--")}
    return arch, fl


def scan(path: Path) -> list[tuple[str, set[str]]]:
    out = []
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return out
    for line in txt.splitlines():
        if line.lstrip().upper().startswith("REM"):
            continue
        arch, fl = flags_of(line)
        if fl or arch:
            if TRAIN.search(line):
                out.append((arch, fl))
    return out


smoke = scan(SMOKE)
smoke_flags = set().union(*[f for _, f in smoke]) if smoke else set()
smoke_arch_flags = {(a, x) for a, f in smoke for x in f}
smoke_archs = {a for a, _ in smoke}

# ★`-done` 도 본다. 사용자가 실행 후 개명하므로 제외하면 **볼 것이 남지 않는다**.
#   "이 조합을 우리가 실제로 쓰는가" 의 증거는 과거 배치에 있다.
batches = sorted(list(ROOT.glob("run_*.bat")) +
                 list((ROOT / "moonshot_batch").glob("run_*.bat")))

missing_flag: dict[str, list[str]] = {}
missing_pair: dict[tuple[str, str], list[str]] = {}
for p in batches:
    for arch, fl in scan(p):
        for x in fl - BOILER:
            if x not in smoke_flags:
                missing_flag.setdefault(x, []).append(p.name)
            elif (arch, x) not in smoke_arch_flags:
                missing_pair.setdefault((arch, x), []).append(p.name)

print("=" * 96)
print("  정적 게이트 15 — 배치가 쓰는 축 대 스모크가 실제로 돌린 축 (torch 0)")
print("=" * 96)
print(f"  스모크 학습 팔 {len(smoke)}개 · arch {sorted(smoke_archs)} · 축 {len(smoke_flags - BOILER)}종")
print(f"  대조 배치 {len(batches)}개 (`-done` 포함)")

err = 0
if missing_flag:
    print("\n  🚫★**스모크가 한 번도 안 켠 축**")
    for x, who in sorted(missing_flag.items()):
        if x in ALLOW:
            print(f"    - {x:<22} (허용: {ALLOW[x]})  <- {', '.join(sorted(set(who))[:3])}")
        else:
            err += 1
            print(f"    - {x:<22} 🚫 <- {', '.join(sorted(set(who))[:3])}")
if missing_pair:
    print("\n  ⚠️★**축은 있는데 그 arch 에서는 안 돌린 조합**  (P074 가 죽은 형태)")
    for (a, x), who in sorted(missing_pair.items()):
        err += 1
        print(f"    - arch={a:<6} {x:<22} <- {', '.join(sorted(set(who))[:3])}")

if err:
    print(f"\n  🚫 {err}건. **새 축을 뚫으면 그 축을 켠 스모크 팔을 함께 넣는다**"
          f" (`scripts/batch/tool_smoke.bat` + `check_smoke.py` 의 EXPECT).")
    print("     스모크로 재현 불가한 축이면 이 파일의 ALLOW 에 **사유와 함께** 등록한다.")
    sys.exit(1)
print("\n  ✅ 배치가 쓰는 축을 스모크가 전부 돌린다")
sys.exit(0)
