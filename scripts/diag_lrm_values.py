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

## 🚫★2026-09-05 정정 — **초판의 기준값이 틀렸었다**(함정 34 의 다섯 번째)

초판 docstring 은 *"승수에는 WD 0.01 이 걸려 있어 **1.0 쪽으로 당겨진다**"* 라고 적었다.
🚫**거짓이다.** AdamW 의 **decoupled** weight decay 는 `p <- p*(1 - lr_t*wd)` 라 **0 쪽으로**
당긴다. 1.0 에서 출발한 스칼라는 **기울기가 하나도 안 와도** 아래로 내려간다.

그래서 초판의 `PASS_MIN = 1e-2` 는 **미탐 구멍**이었다 — 표준 조건(2,289스텝 · lr 1e-3 ·
wsd)에서 **순수 WD 만으로 |s-1| = 0.0202** 가 나오므로, ★**한 번도 학습되지 않은 승수가
'✅통과' 를 찍는다.** 함정 38(인쇄와 판정이 갈라진다)이 아니라 **함정 34 의 반대 얼굴**이다:
기준값을 *적었는데* 그 값이 **틀렸다.**

★**정정된 판정 규약** — 관측값을 **WD 바닥으로 나눈 뒤** 본다:

    s_wd(t) = 곱[ 1 - lr_t * wd ]          # 순수 WD 궤적. 기울기 0 일 때의 예측값
    r       = s / s_wd                     # ★기울기가 만든 몫만 남는다
    지표    = max |r - 1|

## 성공 기준값 (★결과 전에 고정한다 — `check_diag_data` 요구)

- **PASS**: `max |r - 1| >= 1e-2` — 기울기가 승수를 **1% 이상** 움직였다. 결과 072 판정 유효.
- **WEAK**: `1e-4 <= max |r - 1| < 1e-2` — 움직이긴 했으나 미미하다. **경고**(exit 0).
- ★**FAIL(exit 1)**: `max |r - 1| < 1e-4` — 관측된 변화가 **전부 WD 로 설명된다.**
  **결과 072 §1 을 철회한다.**

참고 상수(우리 표준 조건, 이 파일이 계산한다): 2,289스텝 **s_wd = 0.979778** ·
250스텝 **s_wd = 0.997820** · 4,578스텝 **0.960**대 · 9,156스텝 **0.923**대.

🚫**json 을 못 찾으면 `s_wd` 를 1.0 으로 두고 raw 로 판정하되 반드시 경고를 찍는다** —
그때의 PASS 는 *"WD 를 포함해 움직였다"* 까지만 말한다.

## 사용법

    python scripts/diag_lrm_values.py --ckpt runs/ckpt/m100s8_ko-en_300M_d12_cla2_r20_lrm.pt
    python scripts/diag_lrm_values.py --tag d12_cla2_r20_lrm          # 전역 검색
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))                   # ★직접 실행해도 `tinylm` 을 찾게(P075 단계0b)

import tinylm                                   # noqa: E402  ★R40 — HF 캐시 리다이렉트를 먼저 건다

_ = tinylm

CKPT = ROOT / "runs" / "ckpt"
LOGS = ROOT / "runs" / "logs"

PASS_MIN = 1e-2          # ★성공 기준값 — 위 docstring 과 같은 수. **WD 보정 후**의 값이다
WEAK_MIN = 1e-4
LRM_WD = 0.01            # ★정본은 `tinylm/model/transformer.py` 의 param_groups() 마지막 그룹
NAMES = ("gate", "up", "down")


def find_ckpt(tag: str):
    hit = sorted(CKPT.glob(f"*_{tag}.pt"))
    return hit[0] if hit else None


def _lr_factor(s, warm, steps, sched, decay_frac):
    """🚫**정본은 `tinylm/train/trainer.py::_lr_factor`** — 여기는 그 복제다.

    ⚠️복제인 이유: 이 도구는 **torch 없이도 논리를 읽을 수 있어야** 하고 trainer 를 import
    하면 학습 모듈 전체가 딸려 온다. ★대신 `check_lr_factor_sync.py` 가 두 함수가 같은 값을
    내는지 기계로 대조한다(함정 18 — 같은 규칙을 두 곳에 두면 하나가 낡는다).
    """
    if sched == "decay":
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * s / max(steps, 1)))
    if s < warm:
        return (s + 1) / warm
    p = (s - warm) / max(steps - warm, 1)
    if sched == "stable":
        return 1.0
    if sched == "wsd":
        if p < 1.0 - decay_frac:
            return 1.0
        q = (p - (1.0 - decay_frac)) / decay_frac
        return 0.1 + 0.9 * 0.5 * (1 + math.cos(math.pi * q))
    return 0.1 + 0.45 * (1 + math.cos(math.pi * p))


def wd_floor(meta):
    """기울기가 0 일 때 승수가 도달하는 값 `s_wd`. meta 가 없으면 None."""
    if not meta:
        return None
    steps = meta.get("steps")
    lr = meta.get("lr")
    if not steps or not lr:
        return None
    sched = meta.get("sched", "wsd")
    decay_frac = meta.get("decay_frac", 0.2)
    warm = 0 if sched == "decay" else max(5, min(int(steps) // 10, 100))
    s = 1.0
    for t in range(int(steps)):
        s *= (1.0 - float(lr) * _lr_factor(t, warm, int(steps), sched, decay_frac) * LRM_WD)
    return s


def load_meta(path: Path):
    j = LOGS / (path.stem.replace("_best", "") + ".json")
    if not j.is_file():
        return None
    try:
        return json.loads(j.read_text(encoding="utf-8"))
    except Exception:
        return None


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

    meta = load_meta(path)
    s_wd = wd_floor(meta)

    print("=" * 96)
    print(f"  P086 승수 진단 — {path.name}")
    print("=" * 96)
    if s_wd is None:
        print("  ⚠️★**학습 json 을 못 찾아 WD 바닥을 계산하지 못했다.** raw 로 판정한다 —")
        print("     이때의 통과는 *'WD 를 포함해 움직였다'* 까지만 말한다.")
        s_wd = 1.0
        have_floor = False
    else:
        have_floor = True
        print(f"  ★순수 WD 바닥 s_wd = **{s_wd:.6f}**  (|s-1| = {1 - s_wd:.6f})"
              f"  [steps={meta.get('steps')} lr={meta.get('lr')} "
              f"sched={meta.get('sched', 'wsd')} wd={LRM_WD}]")
        print("     ★이만큼은 **기울기가 하나도 안 와도** 내려간다. 이 아래는 학습이 아니다.")
    print(f"  ★성공 기준: **WD 보정 후** max |s/s_wd - 1| >= {PASS_MIN:g} 이면 통과 · "
          f"< {WEAK_MIN:g} 이면 **실패**(승수가 학습되지 않았다)")

    # P086 stage3 (2026-09-08(3rd)) - vector mode names are .lrm_gate/.lrm_up/.lrm_down.
    #   endswith(".lrm") alone prints "no multipliers" and exits 1 on a vector run.
    rows = [(k, v) for k, v in sd.items()
            if k.rsplit(".", 1)[-1].startswith("lrm")]
    is_vec = any(not k.endswith(".lrm") for k, _ in rows)
    if not rows:
        # ★R19 — 잰 것이 0 이면 조용히 0 을 통과시키지 않는다
        print("  🚫★**승수가 하나도 없다.** 이 체크포인트는 `--mlp-lrm` 으로 학습되지 않았다.",
              file=sys.stderr)
        return 1

    worst_raw, worst = 0.0, 0.0
    if is_vec:
        # ★벡터 모드 — 원소가 층당 수천 개라 값을 다 못 찍는다. **요약 통계**로 본다.
        print()
        print(f"  ★**벡터 승수 모드**(P086 단계3) — 파라미터 {len(rows)}개")
        print()
        print("  {:<34} {:>7} {:>9} {:>10} | {:>9} {:>10}".format(
              "파라미터", "개수", "평균", "max|s-1|", "평균/wd", "max|r-1|"))
        print("  " + "-" * 96)
        for k, v in rows:
            f = v.reshape(-1).float()
            mean = float(f.mean())
            raw = float((f - 1.0).abs().max())
            corr = float((f / s_wd - 1.0).abs().max())
            worst_raw = max(worst_raw, raw)
            worst = max(worst, corr)
            print(f"  {k[:34]:<34} {f.numel():>7} {mean:>9.5f} {raw:>10.6f} | "
                  f"{mean / s_wd:>9.5f} {corr:>10.6f}")
        n_el = sum(v.reshape(-1).numel() for _, v in rows)
        print("  " + "-" * 96)
        print(f"  파라미터 {len(rows)}개 · 원소 {n_el}개 · raw max |s-1| = {worst_raw:.6f} · "
              f"★**WD 보정 max |r-1| = {worst:.6f}**")
        if have_floor:
            print(f"  ★기울기 몫 / WD 몫 = **{worst / max(1 - s_wd, 1e-12):.1f}배**"
                  "  — 1.0 근처면 관측된 움직임이 전부 WD 다")
        print()
        if worst >= PASS_MIN:
            print(f"  ✅**통과** — WD 를 걷어내고도 승수가 {worst:.4f} 만큼 움직였다.")
            return 0
        if worst >= WEAK_MIN:
            print(f"  ⚠️★**약하다** — WD 보정 후 최대 변화가 {worst:.6f} 로 1% 미만이다.")
            return 0
        print(f"  🚫★★**실패** — WD 보정 후 최대 변화가 {worst:.2e} 다.", file=sys.stderr)
        return 1
    print(f"\n  {'층':<26} {'gate':>9} {'up':>9} {'down':>9} | "
          f"{'gate/wd':>9} {'up/wd':>9} {'down/wd':>9}   max|r-1|")
    print("  " + "-" * 104)
    for k, v in rows:
        vals = [float(x) for x in v.reshape(-1)[:3]]
        corr = [x / s_wd for x in vals]
        worst_raw = max(worst_raw, max(abs(x - 1.0) for x in vals))
        dev = max(abs(x - 1.0) for x in corr)
        worst = max(worst, dev)
        print(f"  {k[:-4]:<26} " + " ".join(f"{x:>9.5f}" for x in vals) + " | "
              + " ".join(f"{x:>9.5f}" for x in corr) + f"   {dev:9.6f}")

    n = len(rows)
    print("  " + "-" * 104)
    print(f"  층 {n}개 · 스칼라 {n * 3}개 · raw max |s-1| = {worst_raw:.6f} · "
          f"★**WD 보정 max |r-1| = {worst:.6f}**")
    if have_floor:
        print(f"  ★기울기 몫 / WD 몫 = **{worst / max(1 - s_wd, 1e-12):.1f}배**"
              "  — 1.0 근처면 관측된 움직임이 전부 WD 다")
    print()
    if worst >= PASS_MIN:
        print(f"  ✅**통과** — WD 를 걷어내고도 승수가 {worst:.4f} 만큼 움직였다. "
              "결과 072 의 판정이 유효하다.")
        print("     ★그 판정은 *'움직였는데도 품질이 안 변했다'* 이다 — 이것이 축을 닫는 근거다.")
        return 0
    if worst >= WEAK_MIN:
        print(f"  ⚠️★**약하다** — WD 보정 후 최대 변화가 {worst:.6f} 로 1% 미만이다.")
        print("     🚫**결과 072 를 '효과 없음' 으로 읽기 전에 WD 0.01 이 과했는지 본다.**")
        print("     재시도 후보: WD 를 0.001 로. ⚙3.2h.")
        return 0
    print(f"  🚫★★**실패** — WD 보정 후 최대 변화가 {worst:.2e} 다. "
          "관측된 움직임이 **전부 weight decay** 로 설명된다.")
    print("     ★**결과 072 §1 의 결론을 철회한다.** 잰 것은 *'LRM 의 효과'* 가 아니라")
    print("     *'LRM 이 켜지지 않았다'* 이다(함정 37 네 번째 얼굴).")
    print("     선결: 승수가 옵티마이저 param group 에 실제로 들어갔는지 확인(`transformer.py:813`).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
