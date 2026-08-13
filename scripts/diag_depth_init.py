#!/usr/bin/env python3
"""P049 단계0 게이트 — **깊이 확장 이식이 실제로 도움이 되는가.** 학습 0 · 수 분.

## 왜 게이트를 먼저 두나

결과 030 이 값을 지불했다: **초기화가 깨진 채로 아키텍처를 재서 "판정 불가" 가 나왔다.**
그리고 결과 038 §9 가 **부모초기화의 몫이 +0.1386 이고 시드 노이즈까지 6.4배 줄인다**고
정량화했다 — 즉 **이식이 깨지면 아키텍처를 두 번 과소평가**한다.

P049 는 학생 36층 vs 교사 20층이라 **종전 코드로는 `mid_mlps` 에서 `IndexError` 로 죽는다.**
새 이식 로직(`_depth_map`)이 들어갔으니, **5.8시간짜리 단계1 앞에 수 분짜리 게이트**를 둔다.

## 무엇을 보는가 — 세 가지

| # | 무엇 | 통과 조건 | 왜 이 값인가 |
|---|---|---|---|
| **G0-a** | 죽지 않는다 | 예외 없음 | 종전 코드는 IndexError 였다 |
| **G0-b** | 알린다 | `[init] ★★` 경고 출력 | 조용한 부분 이식이 이 저장소 사고의 형태다 |
| **G0-c** | **이식이 실제로 돕는다** | **step0 CE < ln(vocab) − 1.0** | 난수 초기화면 CE ≈ ln(V). 그보다 확실히 낮아야 "이식됐다" |

★**추가로 `prop` 과 `gate_scale` 을 둘 다 재서 어느 쪽이 나은지 고른다.**
잔차 중복(같은 층 2회 통과)이 실제 문제인지 **추측하지 않고 측정**한다.

## 왜 tiny 가 아니라 실제 프리셋인가

tiny 는 층이 4개라 **복제 배수가 실제와 다르다**. 그런데 m100R1d 는 63M×36층이라 CPU 에서
느리다 → **GPU 1회 forward 만** 한다(backward 없음, 학습 0). 그래도 수 분이다.

사용:
    python scripts/diag_depth_init.py
    python scripts/diag_depth_init.py --preset m100R1d --teacher-preset m100
"""
from __future__ import annotations

import argparse
import io
import math
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch                                                    # noqa: E402
import torch.nn.functional as F                                 # noqa: E402

from tinylm import paths                                        # noqa: E402
from tinylm.config import build_config                          # noqa: E402
from tinylm.model.transformer import TiedMLPTransformer         # noqa: E402
from tinylm.train.init_utils import init_from_dense, _depth_map  # noqa: E402


def _hdr(s):
    print("\n" + "=" * 78 + f"\n  {s}\n" + "=" * 78)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="m100R1d")
    ap.add_argument("--teacher-preset", default="m100")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--seq", type=int, default=512)
    ap.add_argument("--bs", type=int, default=2)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args()
    dev, fails = a.device, []

    sc = build_config(a.preset, "tied", a.seq, True)
    tc = build_config(a.teacher_preset, "dense", a.seq, True)
    _hdr("구조 · 대응표")
    print(f"  학생 {a.preset}: {sc.n_prelude}+{sc.n_middle}+{sc.n_coda} = {sc.n_layers}층, "
          f"g={sc.mlp_group}, 유니크 MLP {sc.n_prelude + sc.n_mlp_groups + sc.n_coda}")
    print(f"  교사 {a.teacher_preset}: {tc.n_prelude}+{tc.n_middle}+{tc.n_coda} = {tc.n_layers}층")
    lmap, lrep = _depth_map(sc, tc)
    print(f"  대응표 {lmap}")
    print(f"  ★교사 층당 최대 복제 {max(lrep)}회  -^> 잔차 기여가 그만큼 중복된다")

    ck = paths.resolve_ckpt(a.teacher_preset, a.data, a.tokens, "dense")
    if not Path(ck).exists():
        print(f"\n  🚫 교사 체크포인트가 없다: {ck}")
        print("  -^> `run100m.py train --arch dense ...` 로 부모를 먼저 만들어야 한다.")
        return 2
    print(f"  교사 파일 {Path(ck).name}")

    # ★★2026-08-13 정정 — **종전에는 난수 토큰을 입력·정답으로 썼다. 그건 게이트가 아니었다.**
    #
    #   `x = randint(...)`, `y = randint(...)` 로 **서로 무관한 난수**를 넣고 CE 를 쟀다.
    #   그러면:
    #     · 난수 초기화 모델 → 균등 출력 → CE ≈ ln(V) = 10.40   (맞다)
    #     · **학습된 가중치를 이식한 모델 → 확신을 갖고 예측 → 난수 정답과 안 맞음 → CE ≫ ln(V)**
    #   즉 **이식이 성공할수록 이 지표가 나빠진다.** 부호가 뒤집힌 계측이다.
    #
    #   실제로 결과 041 이 그 함정에 걸렸다 — `identity`(수학적으로 **교사와 동일한 함수**)가
    #   13.4887 을 찍었고 그것을 "실패" 로 읽었다. 13.4887 은 **교사 자신의 점수**다.
    #
    #   → **실제 데이터와 next-token 정답**을 쓴다. 그러면 CE 가 의미를 갖는다:
    #     난수 ≈ ln(V), 이식 성공 ≈ 교사의 val(약 3.8).
    from tinylm.data import prepare, Loader                      # noqa: E402
    meta = prepare(a.data, int(float(a.tokens.rstrip("Mm")) * 1e6), exact=True)
    va = Loader("val", a.bs, a.seq, dev, meta["dir"], seed=99)   # ★val 시드 99 고정 = 표준
    x, y = va()
    ln_v = math.log(sc.vocab_size)
    thr = ln_v - 1.0
    print(f"\n  ★실제 val 데이터 사용(next-token 정답). 난수 토큰이 아니다 — 결과 041 §11 참조")
    print(f"  기준: ln(vocab={sc.vocab_size}) = {ln_v:.4f}  -^>  G0-c 통과선 CE ^< {thr:.4f}")
    print(f"  ★참고: 교사 dense 의 결정적 full-val 은 **3.8080**(결과 040). "
          f"이식이 제대로 됐으면 그 근처여야 한다.")

    results = {}
    # 대조군: 이식 없음(난수) — **이식이 뭘 걷어내는지 크기를 보기 위해서**
    for mode in ("(난수 대조군)", "prop", "gate_scale", "identity"):
        _hdr(f"모드 {mode}")
        torch.manual_seed(1337)
        m = TiedMLPTransformer(sc).to(dev)
        warned = True
        if mode != "(난수 대조군)":
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    init_from_dense(m, str(ck), dev, depth_init=mode)
            except Exception as e:
                print(f"  🚫 G0-a 실패 — {type(e).__name__}: {e}")
                fails.append(f"G0-a[{mode}]")
                continue
            out = buf.getvalue()
            print("  " + "\n  ".join(out.strip().splitlines()))
            warned = "★★" in out
            if not warned:
                print("  🚫 G0-b 실패 — 구조 불일치인데 경고를 안 찍었다")
                fails.append(f"G0-b[{mode}]")
        m.eval()
        with torch.no_grad():
            with torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda")):
                logits = m(x)
                ce = F.cross_entropy(logits.reshape(-1, sc.vocab_size), y.reshape(-1)).item()
            act = logits.float().abs().max().item()
        results[mode] = (ce, act)
        print(f"\n  step0 CE {ce:.4f}   |logit|max {act:.2f}")
        del m, logits
        if dev == "cuda":
            torch.cuda.empty_cache()

    _hdr("판정")
    print(f"  {'모드':<16}{'step0 CE':>12}{'|logit|max':>13}   G0-c")
    print("  " + "-" * 60)
    best, best_ce = None, None
    for k, (ce, act) in results.items():
        ok = ce < thr
        print(f"  {k:<16}{ce:>12.4f}{act:>13.2f}   {'✅' if ok else '🚫'}")
        if k != "(난수 대조군)" and (best_ce is None or ce < best_ce):
            best, best_ce = k, ce
    rnd = results.get("(난수 대조군)", (None,))[0]
    if best_ce is not None and best_ce >= thr:
        fails.append("G0-c")
    print()
    if rnd is not None and best_ce is not None:
        d = rnd - best_ce
        if d > 0:
            print(f"  ★이식이 걷어낸 출발 핸디캡: {d:+.4f} nats "
                  f"(난수 {rnd:.4f} -^> {best} {best_ce:.4f})")
        else:
            # ★2026-08-13 정정: 종전에는 음수도 "걷어냈다" 로 인쇄해 **정반대로 읽혔다**.
            print(f"  🚫★이식이 출발점을 **더 나쁘게** 만들었다: {-d:.4f} nats "
                  f"(난수 {rnd:.4f} -^> {best} {best_ce:.4f})")
            print(f"     -^> 이건 '초기화가 안 됐다' 가 아니라 **'초기화가 해롭다'** 는 뜻이다. "
                  f"복제된 층이 교사가 본 적 없는 입력을 받는다(합성 불일치).")
    if best:
        print(f"  ★권장 depth_init = **{best}**")
        for other in ("gate_scale", "identity"):
            if other in results and "prop" in results:
                d = results["prop"][0] - results[other][0]
                print(f"    prop − {other} = {d:+.4f} nats "
                      f"({other + ' 이 낫다' if d > 0 else 'prop 이 낫다'})")
            print("    ⚠️ **이건 step0 값이다.** 학습 후에도 그 순서가 유지된다는 보장은 없다 — "
                  "단계1 은 이 값으로 하나만 고르고, 뒤집힐 가능성을 결과문서에 적는다.")
    print()
    if fails:
        print(f"  🚫 실패: {', '.join(fails)}  -^> **단계1(5.8h)을 돌리지 않는다**")
    else:
        print("  ✅ G0 전부 통과 — run_P049_depth_g16x2.bat 을 돌릴 수 있다")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
