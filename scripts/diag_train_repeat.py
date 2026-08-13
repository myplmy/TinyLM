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
| **G0-c** | ★**step0 CE 가 교사 근처** | R=1 이 **3.8080 근처**(결과 040 §2) | ★**이게 계측 건강 확인이다.** 여기가 어긋나면 나머지를 읽지 않는다 |
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

TEACHER_FULLVAL = 3.8080          # 결과 040 §2 — dense 의 결정적 full-val


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
    print(f"  ★참고: 교사 dense 결정적 full-val = **{TEACHER_FULLVAL}** (결과 040 §2)")

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
        print(f"\n  ★G0-c 계측 건강: R=1.0 의 CE {b_ce:.4f} vs 교사 full-val {TEACHER_FULLVAL}")
        if abs(b_ce - TEACHER_FULLVAL) > 0.5:
            print(f"  🚫★어긋난다({abs(b_ce-TEACHER_FULLVAL):.3f}). **나머지를 읽지 말 것** — "
                  f"결과 041 §11 과 같은 계측 사고일 수 있다.")
            print(f"     (크롭 표본이라 full-val 과 정확히 같을 수는 없지만 0.5 이내여야 한다)")
            fails.append("G0-c")
        else:
            print(f"  ✅ 같은 자릿수 — 계측이 건강하다. 이제 대가를 읽을 수 있다.")
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
