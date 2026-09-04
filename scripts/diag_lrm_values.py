#!/usr/bin/env python3
"""★P086 게이트 — **층별 승수가 1.0 에서 정말 움직였는가**(학습 0 · GPU 0).

## 왜 이 도구가 있나 (2026-09-04, 결과 072 §5)

`--mlp-lrm` 런의 json 은 `mlp_lrm=True` 를 찍었고 `params` 도 **정확히 +24** 늘었다.
그것으로 *"플래그가 도달했다"* 는 확인됐다. 🚫**그러나 그것은 파라미터가 **존재**한다는
증거이지 **학습됐다**는 증거가 아니다.**

★**함정 37 의 네 번째 얼굴**:

| 얼굴 | 언제 | 무엇이 거짓이었나 |
|---|---|---|
| 1 | 결과 044 | 필드가 기록된다 ≠ 그 경로가 실행된다 |
| 2 | 2026-09-03 | 파일이 있다 ≠ 그 파일이 import 된다 |
| 3 | 결과 053 | 플래그가 파서에 있다 ≠ 그 플래그가 무언가 한다 |
| ★**4** | **여기** | **파라미터가 만들어졌다 ≠ 그 파라미터가 1.0 에서 움직였다** |

승수에는 **WD 0.01** 이 걸려 있어 **1.0 쪽으로 당겨진다**. 전부 1.0 근처에 머물렀다면
결과 072 의 결론은 *"LRM 이 효과 없다"* 가 아니라 ***"LRM 이 켜지지 않았다"*** 여야 한다.
**두 문장은 다음에 할 일이 다르다** — 앞이면 축을 닫고, 뒤면 LR·WD 를 고쳐 다시 돈다.

## 성공 기준값 (★결과 전에 고정한다 — `check_diag_data` 요구)

- **PASS**: `max |s − 1| >= 1e-2` — 승수가 **1% 이상** 움직였다. 결과 072 의 판정이 유효하다.
- **WEAK**: `1e-4 <= max |s − 1| < 1e-2` — 움직이긴 했으나 미미하다. **경고**(exit 0).
- ★**FAIL(exit 1)**: `max |s − 1| < 1e-4` — 사실상 안 움직였다. **결과 072 §1 을 철회한다.**

🚫**임계값의 근거는 산술이 아니라 규약**이다: fp32 학습에서 2,289 스텝 동안 lr 1e-3 을
받은 스칼라가 1e-4 도 안 움직였다면 그것은 **기울기가 안 왔다는 뜻**이다.

## 사용법

    python scripts/diag_lrm_values.py --ckpt runs/ckpt/m100s8_ko-en_300M_d12_cla2_r20_lrm.pt
    python scripts/diag_lrm_values.py --tag d12_cla2_r20_lrm          # 전역 검색
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))                   # ★직접 실행해도 `tinylm` 을 찾게(P075 단계0b)

import tinylm                                   # noqa: E402  ★R40 — HF 캐시 리다이렉트를 먼저 건다

_ = tinylm

CKPT = ROOT / "runs" / "ckpt"

PASS_MIN = 1e-2          # ★성공 기준값 — 위 docstring 과 같은 수
WEAK_MIN = 1e-4
NAMES = ("gate", "up", "down")


def find_ckpt(tag: str):
    hit = sorted(CKPT.glob(f"*_{tag}.pt"))
    return hit[0] if hit else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default=None)
    ap.add_argument("--tag", default=None, help="`*_{tag}.pt` 를 runs/ckpt 에서 찾는다")
    a = ap.parse_args()

    if not a.ckpt and not a.tag:
        print("  🚫 --ckpt 또는 --tag 가 필요하다.", file=sys.stderr)
        return 2
    path = Path(a.ckpt) if a.ckpt else find_ckpt(a.tag)
    if path is None or not path.is_file():
        print(f"  🚫 체크포인트를 못 찾았다: {a.ckpt or a.tag}", file=sys.stderr)
        return 2

    import torch                                # 여기서만 필요하다(임포트 비용)
    st = torch.load(path, map_location="cpu")
    sd = st.get("model", st)

    print("=" * 96)
    print(f"  P086 승수 진단 — {path.name}")
    print("=" * 96)
    print(f"  ★성공 기준: max |s-1| >= {PASS_MIN:g} 이면 통과 · "
          f"< {WEAK_MIN:g} 이면 **실패**(승수가 학습되지 않았다)")

    rows = [(k, v) for k, v in sd.items() if k.endswith(".lrm")]
    if not rows:
        # ★R19 — 잰 것이 0 이면 조용히 0 을 통과시키지 않는다
        print("  🚫★**승수가 하나도 없다.** 이 체크포인트는 `--mlp-lrm` 으로 학습되지 않았다.",
              file=sys.stderr)
        return 1

    worst = 0.0
    print(f"\n  {'층':<28} {'gate':>10} {'up':>10} {'down':>10}   max|s-1|")
    print("  " + "-" * 76)
    for k, v in rows:
        vals = [float(x) for x in v.reshape(-1)[:3]]
        dev = max(abs(x - 1.0) for x in vals)
        worst = max(worst, dev)
        print(f"  {k[:-4]:<28} " + " ".join(f"{x:>10.5f}" for x in vals) + f"   {dev:9.6f}")

    n = len(rows)
    print("  " + "-" * 76)
    print(f"  층 {n}개 · 스칼라 {n * 3}개 · ★**max |s-1| = {worst:.6f}**")
    print()
    if worst >= PASS_MIN:
        print(f"  ✅**통과** — 승수가 {worst:.4f} 만큼 움직였다. 결과 072 의 판정이 유효하다.")
        print("     ★그 판정은 *'움직였는데도 품질이 안 변했다'* 이다 — 이것이 축을 닫는 근거다.")
        return 0
    if worst >= WEAK_MIN:
        print(f"  ⚠️★**약하다** — 최대 변화가 {worst:.6f} 로 1% 미만이다.")
        print("     🚫**결과 072 를 '효과 없음' 으로 읽기 전에 WD 0.01 이 과했는지 본다.**")
        print(f"     재시도 후보: WD 를 0.001 로. ⚙3.2h.")
        return 0
    print(f"  🚫★★**실패** — 최대 변화가 {worst:.2e} 로 사실상 1.0 그대로다.")
    print("     ★**결과 072 §1 의 결론을 철회한다.** 잰 것은 *'LRM 의 효과'* 가 아니라")
    print("     *'LRM 이 켜지지 않았다'* 이다(함정 37 네 번째 얼굴).")
    print("     선결: 승수가 옵티마이저 param group 에 실제로 들어갔는지 확인(`transformer.py:813`).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
