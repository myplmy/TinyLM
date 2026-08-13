#!/usr/bin/env python3
"""P049B 단계0 게이트 — **학습 시 재귀가 부모초기화된 모델을 얼마나 망가뜨리는가.** GPU 소 · 수 분.

## ★이 게이트가 P049 단계0 보다 깨끗한 이유

P049(깊이 확장)는 **학생이 36 물리층**이라 이식 자체가 새 기법이었고, 그게 결과 041 에서
계측 사고로 번졌다. **P049B 는 다르다**:

| | P049 | **P049B** |
|---|---|---|
| 물리 층 수 | 20 → **36** | ★**20 그대로** |
| 부모초기화 | 새 대응표(`_depth_map`) 필요 | ★**항등 사상 = 종전과 비트 동일** |
| 바뀌는 것 | 구조 | ★**forward 스케줄만** |

→ ★★**학생은 교사에서 완벽하게 이식된 상태로 시작한다.** 그 위에 반복만 얹으므로
**step0 CE 의 상승분이 곧 "합성 불일치의 크기"** 다. 결과 041 이 재려다 실패한 그 양이다.

## 무엇을 재나

| # | 게이트 | 통과 조건 | 왜 |
|---|---|---|---|
| **G0-a** | 죽지 않는다 | 예외 없음 | KV 뱅크가 `(owner, 통과번호)` 로 갈라지는지 |
| **G0-b** | ★**삼진 파라미터 불변** | `report()` 삼진이 R=1 과 **완전히 같다** | 반복이 파라미터를 늘리면 이 축의 존재 이유가 사라진다 |
| **G0-c** | ★**step0 CE 가 부모초기화 대역** | R=1 이 **5.0 ~ 9.40** (앵커 **7.77**, 결과 030 §2) | ★**이게 계측 건강 확인이다.** 여기가 어긋나면 나머지를 읽지 않는다 |
| **G0-d** | **반복의 대가** | R=2 의 CE − R=1 의 CE | ★**이 값이 P049B 의 출발 핸디캡**이다 |
| **G0-e** | 스케줄 길이 | R=2 면 방문 36회 | 모드가 실제로 적용됐는가 |

⚠️★**실제 val 데이터를 쓴다.** 난수 토큰을 쓰면 **이식이 성공할수록 지표가 나빠진다**
(결과 041 §11 · 계측 함정 31). 이 스크립트는 그 함정을 피하려고 만들어졌다.

사용:
    python scripts/diag_train_repeat.py
    python scripts/diag_train_repeat.py --repeats 1.0 1.5 2.0 --mode uniform
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch                                                    # noqa: E402
import torch.nn.functional as F                                 # noqa: E402

from tinylm import paths                                        # noqa: E402
from tinylm.config import build_config                          # noqa: E402
from tinylm.data import prepare, Loader                         # noqa: E402
from tinylm.model.transformer import TiedMLPTransformer         # noqa: E402
from tinylm.train.init_utils import init_from_dense             # noqa: E402

# ★★기준값 3종 (2026-08-13 교정 — 함정 34)
#
#   **처음 이 게이트는 R=1.0 의 step0 CE 가 `TEACHER_FULLVAL` 3.8080 근처여야 한다고 썼다.
#   그건 틀렸다.** `init_from_dense` 는 중간 MLP 를 **타잉 그룹별로 평균**한다
#   (`mid_mlps[j//g]` ← 교사 MLP g 개의 평균). 그래서 **부모초기화된 타잉 학생은
#   교사가 아니다** — 교사 점수를 낼 수 **없다**. 낸다면 오히려 타잉이 안 걸린 것이다.
#
#   ★결과 030 §2 에 옳은 앵커가 이미 있었다:
#     *"출력이 완전 무작위 … 같은 밤 `mC_g16` 은 **7.7742** 로 부모초기화 이득이 살아 있었다"*
#
#   → 게이트를 **점 검사에서 대역 검사로** 바꾼다. 바닥은 "교사보다 좋을 수 없다",
#     천장은 "난수보다는 나아야 한다". 앵커 7.77 로부터의 거리는 **정보로만** 인쇄한다.
TEACHER_FULLVAL = 3.8080          # 결과 040 §2 — dense 의 결정적 full-val. **도달 불가 하한**
PARENT_TIED_ANCHOR = 7.7742       # ★결과 030 §2 — mC_g16 부모초기화 step0 ce. **이게 옳은 앵커**
FLOOR = 5.0                       # 이보다 낮으면 타잉 평균화가 안 걸렸다는 뜻 (교사에 너무 가깝다)


def _hdr(s):
    print("\n" + "=" * 78 + f"\n  {s}\n" + "=" * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--teacher-preset", default="m100")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--bs", type=int, default=4)
    ap.add_argument("--repeats", type=float, nargs="+", default=[1.0, 1.5, 2.0, 2.5])
    ap.add_argument("--mode", default="uniform",
                    choices=["uniform", "block", "progressive"])
    ap.add_argument("--block", type=int, default=0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    dev, fails, notes = a.device, [], []

    ck = paths.resolve_ckpt(a.teacher_preset, a.data, a.tokens, "dense")
    if not Path(ck).exists():
        print(f"🚫 교사 체크포인트가 없다: {ck}")
        return 2

    _hdr("설정")
    print(f"  학생 {a.preset} / 교사 {a.teacher_preset} ({Path(ck).name})")
    print(f"  모드 {a.mode}" + (f" block={a.block}" if a.mode == "block" else ""))
    print(f"  ★실제 val 데이터(next-token 정답). 난수 토큰이 아니다 — 계측 함정 31")
    print(f"  ★G0-c 기준(2026-08-13 교정, 함정 34):")
    print(f"     하한 {FLOOR}  ^< CE ^<  천장 {math.log(32768)-1.0:.4f}(=ln V − 1)")
    print(f"     앵커 **{PARENT_TIED_ANCHOR}** = 부모초기화 타잉 step0 (결과 030 §2)")
    print(f"     ⚠️교사 full-val {TEACHER_FULLVAL} 은 **도달 불가**다 — 중간 MLP 가 g층 평균이라")
    print(f"       부모초기화 타잉 학생은 교사가 아니다. 종전 게이트가 여기서 틀렸다.")
    print(f"  ⚠️크롭 {a.bs}x{a.seq} = {a.bs*a.seq}토큰 **단일 표본**이다 — "
          f"다른 스크립트/다른 크롭의 CE 와 직접 비교하지 않는다")

    meta = prepare(a.data, int(float(a.tokens.rstrip("Mm")) * 1e6), exact=True)
    va = Loader("val", a.bs, a.seq, dev, meta["dir"], seed=99)   # ★val 시드 99 고정
    x, y = va()

    base_ter = None
    rows = []
    for R in a.repeats:
        _hdr(f"train_repeat = {R}")
        cfg = build_config(a.preset, "tied", a.seq, True)
        cfg.train_repeat, cfg.repeat_mode, cfg.repeat_block = float(R), a.mode, a.block
        torch.manual_seed(1337)
        try:
            m = TiedMLPTransformer(cfg).to(dev)
            init_from_dense(m, str(ck), dev)          # ★깊이가 같으므로 항등 사상 = 비트 동일
        except Exception as e:
            print(f"  🚫 G0-a 실패 — {type(e).__name__}: {e}")
            fails.append(f"G0-a[R={R}]")
            continue

        # --- G0-b : 삼진 파라미터 불변 ---
        rep = m.report() if hasattr(m, "report") else None
        ter = sum(p.weight_numel() for p in m._tlinear_cache)
        if base_ter is None:
            base_ter = ter
        same = (ter == base_ter)
        print(f"  삼진 파라미터 {ter/1e6:.2f}M   {'✅ 불변' if same else '🚫 변했다'}")
        if not same:
            fails.append(f"G0-b[R={R}]")

        # --- G0-e : 스케줄 ---
        m.train()                                     # ★train_repeat 은 training 일 때만 발화
        sched = m.visit_schedule()
        print(f"  방문 스케줄 길이 {len(sched)}  (물리 층 {cfg.n_layers})")
        print(f"    {sched[:16]}{' ...' if len(sched) > 16 else ''}")
        if R == 1.0 and len(sched) != cfg.n_layers:
            print("  🚫 G0-e 실패 — R=1.0 인데 스케줄이 종전과 다르다(비트 동일이 깨졌다)")
            fails.append("G0-e[R=1]")

        # --- G0-c/d : step0 CE ---
        if dev == "cuda":
            torch.cuda.reset_peak_memory_stats()
        with torch.no_grad():
            with torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda")):
                logits = m(x)
                ce = F.cross_entropy(logits.reshape(-1, cfg.vocab_size), y.reshape(-1)).item()
        peak = (torch.cuda.max_memory_allocated() / 2**30) if dev == "cuda" else 0.0
        print(f"  ★step0 CE {ce:.4f}   peak alloc {peak:.2f} GiB")
        rows.append((R, len(sched), ter, ce, peak))
        del m, logits
        if dev == "cuda":
            torch.cuda.empty_cache()

    # ── 판정 ────────────────────────────────────────────────────────────────
    _hdr("판정")
    if not rows:
        print("  잰 것이 없다.")
        return 2
    print(f"  {'R':>5}{'방문':>7}{'삼진(M)':>10}{'step0 CE':>12}{'peak GiB':>11}")
    print("  " + "-" * 48)
    for R, n, t, ce, pk in rows:
        print(f"  {R:>5.1f}{n:>7}{t/1e6:>10.2f}{ce:>12.4f}{pk:>11.2f}")

    base = next((r for r in rows if r[0] == 1.0), None)
    if base is None:
        print("\n  ⚠️ R=1.0 을 안 쟀다 — 기준선이 없으면 대가를 못 읽는다.")
        notes.append("no-baseline")
    else:
        b_ce = base[3]
        ceil_ = math.log(32768) - 1.0
        print(f"\n  ★G0-c 계측 건강: R=1.0 의 CE {b_ce:.4f}")
        print(f"     대역 [{FLOOR}, {ceil_:.4f}]   앵커 {PARENT_TIED_ANCHOR}(결과 030 §2) "
              f"로부터 {b_ce - PARENT_TIED_ANCHOR:+.4f}")
        if b_ce > ceil_:
            print(f"  🚫★난수 수준이다(천장 {ceil_:.4f} 초과). 부모초기화가 안 걸렸다 — "
                  f"**나머지를 읽지 말 것**")
            fails.append("G0-c[천장]")
        elif b_ce < FLOOR:
            print(f"  🚫★너무 좋다(하한 {FLOOR} 미만). **타잉 평균화가 안 걸렸을 수 있다** — "
                  f"부모초기화 타잉 학생은 교사({TEACHER_FULLVAL})에 근접할 수 없다")
            fails.append("G0-c[하한]")
        else:
            print(f"  ✅ 부모초기화 대역 안이다 — 계측이 건강하다. 이제 대가를 읽을 수 있다.")
            if abs(b_ce - PARENT_TIED_ANCHOR) > 1.0:
                print(f"  ⚠️ 앵커에서 1.0 이상 떨어져 있다. 통과이긴 하나 "
                      f"**프리셋·크롭이 030 과 다르다는 것을 결과문서에 적을 것**")
            print(f"\n  ★G0-d 반복의 출발 대가:")
            for R, n, t, ce, pk in rows:
                if R == 1.0:
                    continue
                print(f"    R={R:.1f}  Δ = {ce - b_ce:+.4f} nats   "
                      f"(방문 {n}회, alloc {pk - base[4]:+.2f} GiB)")
            print(f"\n  ⚠️ **이건 step0 값이다.** 학습이 이 대가를 회수하는지가 P049B 의 질문이고,")
            print(f"     그건 단계1 이 답한다. **여기서 크다고 축을 닫지 않는다** —")
            print(f"     결과 020 이 닫은 것은 '추론 반복' 이고 이쪽은 학습이 적응할 기회가 있다.")

    print()
    if fails:
        print(f"  🚫 실패: {', '.join(fails)}  -^> **단계1 을 돌리지 않는다**")
    else:
        print("  ✅ G0 통과 — run_P049B_stage1_repeat.bat 을 만들 수 있다")
        print("  ⚠️ 단 단계1 은 **벽시계 정합 대조군(mC_long)까지** 있어야 판정이 된다(계획 §5.2)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
