#!/usr/bin/env python3
"""★`cfg.return_probs` 진단 경로 검증 — **동적 게이트**(torch 필요, GPU 불필요).

## 왜 별도 스크립트인가

새 축을 뚫으면 **그 축을 켠 스모크 팔을 함께 넣는다**(함정 37). 그런데
`return_probs` 는 **학습에서 켤 수 없다**(활성 메모리가 배치 x 헤드로 늘어나 단언으로 막았다).
-> 🚫**학습 팔로는 검증할 수 없다.** 그래서 이 스크립트가 그 자리를 대신하고
`tool_smoke.bat` 이 부른다.

## 무엇을 단언하나

| # | 단언 | 왜 |
|---|---|---|
| ★**1** | `return_probs` on/off 의 **로짓이 비트 동일** | 이것이 이 구현의 전체 주장이다. 확률은 **읽기만** 하고 출력 경로에 안 들어간다 |
| **2** | 확률 행 합 = 1 | softmax 가 마스크 뒤에 제대로 걸렸는가 |
| ★**3** | **상삼각이 정확히 0** | causal 마스크가 맞는가. 🚫여기가 틀리면 싱크 수치가 조용히 틀린다 |
| **4** | `last_probs` 가 **어텐션 모듈마다** 생긴다 | 한 층만 채워지고 나머지가 None 이면 평균이 거짓말한다 |
| ★**5** | 학습 모드에서 **단언이 뜬다** | 실수로 학습에 켜는 것을 코드가 막는가 |

체크포인트도 데이터셋도 안 쓴다 — **난수 초기화 tiny 모델**이다.
🚫**품질은 아무것도 안 본다.** 경로가 도는가만 본다.

사용:
    python scripts/check_return_probs.py
종료코드 0 = 통과 / 1 = 실패
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    import torch
    import tinylm                                     # noqa: F401
    from tinylm.config import build_config
    from tinylm.model.transformer import TMT

    print("=" * 96)
    print("  check_return_probs — 어텐션 확률 진단 경로 (난수 tiny 모델, 학습 0)")
    print("=" * 96)

    fails = []
    torch.manual_seed(1337)
    cfg = build_config("tiny", "tied", 128, True)
    model = TMT(cfg).eval()
    ids = torch.randint(0, cfg.vocab_size, (1, 64))

    # ── 1. 비트 동일 ────────────────────────────────────────────────
    cfg.return_probs = False
    model.cfg.return_probs = False
    with torch.no_grad():
        a = model(ids)
    a = a[0] if isinstance(a, tuple) else a
    cfg.return_probs = True
    model.cfg.return_probs = True
    with torch.no_grad():
        b = model(ids)
    b = b[0] if isinstance(b, tuple) else b
    same = bool(torch.equal(a, b))
    print(f"  [1] 로짓 비트 동일 (off vs on)        : {'✅ 같다' if same else '🚫 다르다'}"
          f"   max|d| = {float((a - b).abs().max()):.3e}")
    if not same:
        fails.append("★return_probs 를 켜니 로짓이 바뀐다 — 진단 경로가 출력에 새고 있다")

    # ── 2~4. 확률 자체 ──────────────────────────────────────────────
    mods = [m for m in model.modules() if getattr(m, "last_probs", None) is not None]
    print(f"  [4] `last_probs` 가 채워진 어텐션 모듈 : {len(mods)}개")
    if not mods:
        fails.append("★`last_probs` 가 하나도 없다 — return_probs 가 forward 에 안 닿았다(함정 37)")
    else:
        p = mods[0].last_probs[0]                      # (H, T, T)
        rows = p.sum(-1)
        ok_sum = bool(torch.allclose(rows, torch.ones_like(rows), atol=1e-5))
        T = p.shape[-1]
        upper = torch.triu(torch.ones(T, T, dtype=torch.bool), diagonal=1)
        ok_causal = float(p[:, upper].abs().max()) == 0.0
        print(f"  [2] 행 합 = 1                        : "
              f"{'✅' if ok_sum else '🚫'}  (최대 편차 {float((rows - 1).abs().max()):.2e})")
        print(f"  [3] 상삼각(미래) = 정확히 0          : "
              f"{'✅' if ok_causal else '🚫'}  (최대 {float(p[:, upper].abs().max()):.2e})")
        if not ok_sum:
            fails.append("확률 행 합이 1 이 아니다 — 마스크와 softmax 순서를 볼 것")
        if not ok_causal:
            fails.append("★미래 위치에 확률이 있다 — causal 마스크가 틀렸다. "
                         "이대로면 싱크 수치가 조용히 틀린다")

    # ── 5. 학습 모드 차단 ───────────────────────────────────────────
    model.train()
    blocked = False
    try:
        model(ids)
    except AssertionError:
        blocked = True
    except Exception as e:                             # noqa: BLE001
        print(f"  [5] ⚠️학습 모드에서 다른 예외: {type(e).__name__}: {e}")
    print(f"  [5] 학습 모드에서 차단                : "
          f"{'✅ 단언으로 막힌다' if blocked else '🚫 그냥 돈다'}")
    if not blocked:
        fails.append("★학습에서 return_probs 가 막히지 않는다 — 활성 메모리가 배치x헤드로 늘어난다")

    print("=" * 96)
    if fails:
        print(f"  🚫 실패 {len(fails)}건")
        for f in fails:
            print(f"     · {f}")
        return 1
    print("  ✅ 전부 통과 — 확률 경로가 돌고, 출력에는 안 샌다.")
    print("  ⚠️경로가 도는 것만 본다. 싱크가 있는지는 `diag_attention_sink.py` 가 잰다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
