#!/usr/bin/env python3
"""P014C 단계2 — **per-row 융합 int8 이 언팩 캐시(19.07 tok/s)를 넘는가.** CPU 디코드 · 학습 0.

## 무엇이 병목이었나

결과 014 §11.4: int8 저장 경로는 forward 마다 `_wq_from_i8()` 로 **fp32 를 복원**한다.
층당 2.1~2.2ms × 20층 ≈ **43ms/토큰**. 그래서 int8 상주는 메모리를 절반으로 줄이면서
**속도를 −62~67%** 냈다(CPU 한정. CUDA 는 −12~15%).

두 가지 대응이 있었다:
  1. **언팩 캐시**(P034 단계3C, 완료) — 타잉 그룹 안에서 복원 결과를 재사용. **19.07 tok/s**
  2. **융합 mpGEMM**(이 단계) — 복원 자체를 없앤다. `torch._weight_int8pack_mm`

단계1 이 **연산이 존재함**을 확인했다(결과 028 §11, 상대오차 1.7e-3 = bf16 누산).
남은 질문은 **빠른가** 하나다.

## ★게이트 G2 — **19.07 tok/s 를 넘어야 한다**

못 넘으면 **이 경로를 접고 언팩 캐시로 만족한다.** 언팩 캐시는 이미 완료됐고 순수 PyTorch 다.
"있는 것보다 나쁘면 의미가 없다."

## ⚠️ 이 벤치가 재는 것과 재지 않는 것

- **재는 것**: 같은 프로세스·같은 모델·같은 프롬프트에서 세 경로의 tok/s
- **안 재는 것**: 품질. per-row α 의 품질 대가는 **결과 028 이 이미 쟀다**(+0.0050~0.0063 bpb)
- ⚠️★**체크포인트를 per-row 로 재양자화한다.** 원래 g128 로 학습된 가중치를 per-row 로
  다시 묶는 것이므로 **출력이 학습된 모델과 다르다.** 속도만 읽어야 하고,
  **이 경로의 품질 판정에는 쓸 수 없다**(그건 P014C 단계3 = 재학습이다).
- ⚠️ **단독 실행**. 결과 016 §12.5 — 다른 GPU/CPU 작업이 있으면 무효.
  세션 간 드리프트가 7.5% 다(결과 037 §11.4) → **세 조건을 같은 실행 안에서** 잰다.

사용:
    python scripts/bench_fused_int8.py --models mC_wsd
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch                                                    # noqa: E402

from tinylm import paths                                        # noqa: E402
from tinylm.infer import load_model                             # noqa: E402
from tinylm.model.ternary import TLinear                        # noqa: E402

GATE = 19.07          # 결과 016 §15 — 언팩 캐시 tok/s. 이걸 넘어야 한다


def _hdr(s):
    print("\n" + "=" * 78 + f"\n  {s}\n" + "=" * 78)


def _tlinears(model):
    return [m for m in model.modules() if isinstance(m, TLinear)]


def _prep(model, per_row, unpack_cache):
    """freeze -> (선택) per-row 재양자화 -> int8 저장 -> 캐시 설정."""
    for m in _tlinears(model):
        m.clear_quant()
    if per_row:
        # ★per-row 센티널. cfg 는 층들이 공유하므로 한 번만 바꾼다.
        model.cfg.micro_group = 0
    else:
        model.cfg.micro_group = 128
    model.freeze_quant()
    for m in _tlinears(model):
        m.to_int8()
        m.set_unpack_gen(0 if unpack_cache else None)
    return model


@torch.no_grad()
def _decode(model, n_new, dev, warm=4):
    """배치1 그리디 디코드. 캐시 없이 전체 재계산(결과 016 §15 와 같은 규약)."""
    ids = torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8]], dtype=torch.long, device=dev)
    for _ in range(warm):                    # 워밍업(첫 호출의 할당·오토튠 제외)
        model(ids)
    t0 = time.perf_counter()
    cur = ids
    for _ in range(n_new):
        logits = model(cur)
        nxt = logits[:, -1, :].argmax(-1, keepdim=True)
        cur = torch.cat([cur, nxt], dim=1)
    dt = time.perf_counter() - t0
    return n_new / dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["mC_wsd"])
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--max-new", type=int, default=32)
    ap.add_argument("--device", default="cpu",
                    help="★기본 cpu — 이 경로의 존재 이유가 CPU 배포다(결과 014 §11)")
    a = ap.parse_args()

    print(f"torch {torch.__version__} / device {a.device} / threads {torch.get_num_threads()}")
    print(f"★게이트 G2 = 언팩 캐시 {GATE} tok/s (결과 016 §15)")
    has_op = hasattr(torch, "_weight_int8pack_mm")
    print(f"torch._weight_int8pack_mm 존재: {has_op}")
    if not has_op:
        print("🚫 융합 연산이 없다 — 단계1 결과와 모순이다. torch 버전 확인 필요.")
        return 2

    rows = []
    for tag in a.models:
        ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, tag)
        if not Path(ck).exists():
            print(f"[SKIP] 체크포인트 없음: {ck}")
            continue
        _hdr(f"{tag}   <- {Path(ck).name}")
        for label, per_row, cache, fused in (
                ("int8, 캐시 off (기준선)", False, False, False),
                ("int8 + 언팩 캐시",        False, True,  False),
                ("★per-row 융합",           True,  False, True)):
            model, cfg, _ = load_model("tied", str(ck), device=a.device)
            model.eval()
            try:
                _prep(model, per_row, cache)
                model.cfg.fused_int8 = fused
                tps = _decode(model, a.max_new, a.device)
                # 상주 바이트(참고). 융합은 fp32 복원 버퍼가 안 생기는 것이 요점이다
                nb = sum(m._i8.numel() + m._alpha.numel() * 4 for m in _tlinears(model)
                         if m._i8 is not None)
                print(f"  {label:<26} {tps:8.2f} tok/s   삼진저장 {nb/1e6:8.2f} MB")
                rows.append((tag, label, tps))
            except Exception as e:
                print(f"  {label:<26} 🚫 {type(e).__name__}: {str(e)[:110]}")
                rows.append((tag, label, None))
            finally:
                del model
    _hdr("판정 — G2")
    if not rows:
        print("  잰 것이 없다.")
        return 2
    print(f"  {'런':<10}{'경로':<28}{'tok/s':>9}   vs 게이트")
    print("  " + "-" * 62)
    worst = None
    for tag, label, tps in rows:
        if tps is None:
            print(f"  {tag:<10}{label:<28}{'실패':>9}")
            continue
        mark = ""
        if "융합" in label:
            mark = "✅ 통과" if tps > GATE else "🚫 미달 -^> 경로 폐기"
            worst = tps
        print(f"  {tag:<10}{label:<28}{tps:>9.2f}   {mark}")
    print()
    print("  ⚠️ 재양자화된 가중치라 **속도만 유효**하다. 품질은 P014C 단계3(재학습)이 잰다.")
    print("  ⚠️ 세 조건을 같은 실행에서 쟀다 — 다른 날 숫자와 비교하지 말 것(드리프트 7.5%).")
    return 0 if (worst is not None and worst > GATE) else 1


if __name__ == "__main__":
    raise SystemExit(main())
