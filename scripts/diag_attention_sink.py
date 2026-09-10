"""P081 단계0 — **어텐션 싱크 실사.** ✅**2026-08-31 선결 해소, 이제 돈다.**

## 왜 이 파일이 오래 "막힘" 이었나

StreamingLLM(arXiv:2309.17453)의 전제는 *"처음 몇 토큰이 어텐션 질량을 크게 먹는다"* 다.
그것이 우리 모델에서도 사실이면 **최근 창 W + 싱크 S 만 남기고** KV 를 버릴 수 있고,
KV 가 **컨텍스트와 무관한 상수**가 된다(P081 §0). ★`KV = 엔트리 x 토큰 x 바이트` 중
**엔트리는 결과 062 가 닫았고 바이트는 결과 065 가 절반으로 만들었다 — 토큰이 마지막 축**이다.

🚫**그런데 SDPA 는 확률을 안 돌려준다.** Flash 백엔드에서는 물질화조차 안 된다.
⚠️★**훅으로 밖에서 재계산하는 우회를 쓰지 않았다** — RoPE·QK-norm·GQA 복제·마스크 규약을
**두 곳에서 정의**하는 일이고(함정 18) 그렇게 만든 수치가 실제와 달라도 **조용히 틀린다**.

## ✅선결 — `cfg.return_probs` (2026-08-31 구현)

`Attention.forward` 안에서, **이미 만들어진 q·k·mask 그대로** 확률을 한 번 더 계산해
`self.last_probs` 에 둔다. ★**출력 경로에 안 들어간다** — `o` 는 SDPA 가 만든 그대로이므로
**켜도 로짓이 비트 동일**하고 대가는 메모리·시간뿐이다.
🚫학습에서는 단언으로 막는다(활성 메모리가 배치 x 헤드로 늘어난다).

## 무엇을 인쇄하나

| 지표 | 판정 |
|---|---|
| 위치 0~3 이 받는 어텐션 질량(층·헤드 평균) | ^> 10% 싱크 있음 / 3~10% 경계 / ^< 3% 없음 |
| ★★**causal 균등 기준선** | 🚫**`S/T` 가 아니다**(아래 정정). T=1024·S=4 면 **2.5101%** |
| 층별 분포 | 논문은 깊은 층일수록 크다고 한다 — 우리도 그런가 |
| ★**최근 창 W 가 받는 질량** | StreamingLLM 이 남기는 나머지 절반 |
| ★**싱크 S + 창 W 로 덮이는 질량** | ★**이것이 실제 판정 지표**다 — 버릴 KV 가 얼마나 안 중요한가 |

⚠️★**이 도구는 질량만 본다. 잘라 보고 손실이 얼마나 오르는지는 안 잰다** — 그것이 단계1 이다.
질량이 커도 **남은 1% 가 결정적일 수 있다.**

사용:
    python scripts/diag_attention_sink.py --preset m100R1c --models mC_cla2_ag4 --seq 1024
종료코드 0 = 쟀다 / 2 = 체크포인트 없음
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ★성공 기준값 — `check_diag_data` 가 이 상수의 존재를 본다(함정 32).
SINK_YES = 0.10
SINK_NO = 0.03
SINK_POS = 4          # 앞 몇 토큰을 '싱크' 로 볼 것인가(논문 기본 4)
WINDOW = 256          # 최근 창 W. StreamingLLM 이 남기는 나머지
NULL_RATIO_HIGH = 2.0  # ★이 배수 이상이면 "균등이 아니다". causal null 기준이다


def causal_null(T: int, S: int) -> float:
    """★★**causal 어텐션의 균등 기준선**(2026-09-10, 외부 조치 A10).

    🚫★**종전에는 `S/T` 를 썼다. 그것은 틀린 기준이다.**

    `S/T` 는 **마지막 질의 하나**(과거 T 개를 다 보는 질의)의 비율이다. 그런데 우리가 재는 수는
    **모든 질의 위치의 평균**이고, causal 이라 질의 `t` 는 **`t` 개만** 본다.
    질의 1~4 는 앞 4개 말고 볼 것이 아예 없어서 **싱크 질량이 1.0** 이다.

        null(T,S) = (1/T) * 합_{t=1..T} min(S,t)/t

    T=1024·S=4 → **2.5101%**. 🚫**종전 기준 0.39% 의 6.4배**다.

    ★**그래서 판정이 하나 뒤집힌다**: 결과 070 이 적은 *"싱크 2.01~2.73% = 균등의 5.2~7.0배 =
    균등이 아니다"* 는 **거짓**이다 — 옳은 기준으로 보면 **0.80~1.09배 = 우연 수준**이다.
    ⚠️**주 결론(싱크가 2% 뿐이라 StreamingLLM 전제가 성립 안 한다)은 그대로**이고
    오히려 더 강해진다.
    """
    if T <= 0 or S <= 0:
        return 0.0
    return sum(min(S, t) / t for t in range(1, T + 1)) / T


def causal_null_tail(T: int, S: int, start: int) -> float:
    """★같은 기준선을 **꼬리 질의 구간**(위치 `start` 이상, 0-기반)에서만 계산한다."""
    lo = max(1, int(start) + 1)
    if lo > T:
        return 0.0
    return sum(min(S, t) / t for t in range(lo, T + 1)) / (T - lo + 1)


def main() -> int:
    ap = argparse.ArgumentParser(description="P081 단계0 — 어텐션 싱크 실사")
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--seq", type=int, default=1024, help="프롬프트 길이(val 앞부분에서 자른다)")
    ap.add_argument("--sink", type=int, default=SINK_POS)
    ap.add_argument("--window", type=int, default=WINDOW)
    ap.add_argument("--device", default="cpu",
                    help="cpu 가 기본 — 확률 행렬이 (H, T, T) 라 GPU 를 점유할 이유가 없다")
    a = ap.parse_args()

    import numpy as np
    import torch
    import tinylm                                     # noqa: F401  (HF 캐시 리다이렉트)
    from tinylm import paths
    from tinylm.data import prepare
    from tinylm.infer.generate import load_model

    print("=" * 96)
    print("  P081 단계0 — 어텐션 싱크 실사 (학습 0)")
    print(f"  seq {a.seq} · 싱크 앞 {a.sink} 토큰 · 최근 창 {a.window}")
    _null_s = causal_null(a.seq, a.sink)
    _null_w = causal_null(a.seq, a.window)
    print(f"  ★★causal 균등 기준선: 싱크 **{_null_s:.4%}** · 창 **{_null_w:.4%}**")
    print(f"     🚫종전 기준 `S/T`(싱크 {a.sink / a.seq:.4%} · 창 {a.window / a.seq:.4%})는 "
          f"**마지막 질의 하나**의 비율이라 틀렸다 — 우리는 **모든 질의의 평균**을 잰다(A10)")
    print("=" * 96)

    n_tok = int(float(a.tokens.rstrip("MmBb")) * (1e9 if a.tokens[-1] in "Bb" else 1e6))
    meta = prepare(a.data, n_tok)
    vb = np.memmap(Path(meta["dir"]) / "val.bin", dtype=np.uint16, mode="r")
    ids = torch.tensor(np.asarray(vb[: a.seq], dtype=np.int64))[None, :]

    base = f"{a.preset}_{a.data}_{a.tokens}"
    any_ok = False
    for tag in a.models:
        ck = paths.RUNS / "ckpt" / f"{base}_{tag}.pt"
        if not ck.exists():
            print(f"\n  [건너뜀] 체크포인트 없음: {ck.name}")
            continue
        arch = "dense" if "dense" in tag else "tied"
        model, cfg, device = load_model(arch=arch, ckpt_path=str(ck), device=a.device)
        cfg.return_probs = True
        model.cfg.return_probs = True
        model.eval()
        with torch.no_grad():
            model(ids.to(device))

        # ★어텐션 모듈을 **모델이 실제로 만든 것**에서 모은다 — 이름으로 짐작하지 않는다.
        mods = [m for m in model.modules() if hasattr(m, "last_probs")]
        if not mods:
            print(f"\n  🚫 {tag}: `last_probs` 가 하나도 없다 — "
                  f"`return_probs` 가 forward 에 안 닿았다(함정 37)")
            continue
        any_ok = True

        print(f"\n  ── {tag} ({arch}, cla_group={cfg.cla_group}, "
              f"어텐션 모듈 {len(mods)}개) " + "-" * 20)
        print(f"     {'모듈':>6}{'싱크 질량':>12}{'창 질량':>12}{'싱크+창':>12}{'중간(버릴)':>12}")
        s_all, w_all, b_all = [], [], []
        _tail_probs = []                              # ★A10 — 꼬리 질의만의 싱크 질량
        for i, m in enumerate(mods):
            p = m.last_probs[0]                       # (H, T, T)
            # ★질의 위치마다 분모가 다르다(causal). **질의별로 정규화된 확률**이므로
            #   위치별 합이 1 이고, 그것을 질의 축으로 평균하면 '평균 질량 배분' 이 된다.
            sink = float(p[:, :, : a.sink].sum(-1).mean())
            # 최근 창: 질의 j 에 대해 [j-W, j] 구간. 대각 밴드라 인덱스로 만든다.
            T = p.shape[-1]
            j = torch.arange(T)[:, None]
            k = torch.arange(T)[None, :]
            band = (k <= j) & (k > j - a.window)
            win = float((p * band).sum(-1).mean())
            both = float((p * (band | (k < a.sink))).sum(-1).mean())
            _tf = max(a.window, a.seq // 2)
            _tail_probs.append(float(p[:, _tf:, : a.sink].sum(-1).mean()))
            s_all.append(sink)
            w_all.append(win)
            b_all.append(both)
            print(f"     {i:>6}{sink:>11.2%}{win:>12.2%}{both:>12.2%}{1 - both:>12.2%}")
            m.last_probs = None                        # 메모리 반납

        s = sum(s_all) / len(s_all)
        w = sum(w_all) / len(w_all)
        # ★★2026-09-02 E18 — **겹침을 두 번 세면 안 된다.**
        #   질의 j 가 작을 때 `[j-W, j]` 창은 싱크(0..S-1)를 **포함한다**.
        #   그래서 `s + w` 는 겹친 질량을 두 번 세고, 창이 커질수록 그 편향이 커진다
        #   (실측 +1.5pp @128 -> +2.25pp @768). 창 768 에서 **-0.3%** 라는
        #   물리적으로 불가능한 값이 나온 것이 그 증상이다.
        #   ★표의 `중간(버릴)` 열은 처음부터 `1-both`(합집합)로 옳았다 —
        #   갈라진 것은 **요약줄뿐**이다(함정 38 의 얼굴).
        b = sum(b_all) / len(b_all)
        unif = _null_s                       # ★A10 — causal null. 🚫`S/T` 가 아니다
        print(f"\n     ★평균 싱크 질량 {s:.2%}  "
              f"(★causal 균등 {unif:.4%} 의 **{s / unif:.2f}배** · "
              f"🚫옛 기준 {a.sink / a.seq:.4%} 로는 {s / (a.sink / a.seq):.1f}배로 보였다)")
        print(f"     ★평균 창 질량   {w:.2%}  (causal 균등 {_null_w:.2%} 의 {w / _null_w:.2f}배)")
        # ★★A10 — **꼬리 질의만** 따로 본다. 시작 질의는 볼 것이 없어 싱크 질량이 1.0 이라
        #   전체 평균을 끌어올린다. 배포에서 중요한 것은 **문맥이 찬 뒤**의 행동이다.
        _tail_from = max(a.window, a.seq // 2)
        _ts, _tn = [], causal_null_tail(a.seq, a.sink, _tail_from)
        for m2 in _tail_probs:
            _ts.append(m2)
        if _ts:
            _t = sum(_ts) / len(_ts)
            print(f"     ★★꼬리 질의(위치 ^>={_tail_from}) 싱크 질량 **{_t:.2%}**  "
                  f"(그 구간 causal 균등 {_tn:.4%} 의 **{_t / _tn:.2f}배**)")
            print("        ★이것이 **배포에서 실제로 겪는 값**이다 — 시작 질의는 볼 것이 없어 1.0 이다")
        # ★★2026-09-02 — 판정을 **두 축으로 나눈다**(함정 28).
        #   ① 절대: StreamingLLM 처럼 **가운데를 버릴 수 있는가** (질량 기준)
        #   ② 상대: 분포가 **균등과 다른가** (배수 기준)
        #   2.2% 는 ①에서 '못 쓴다' 이고 ②에서는 '5.7배 = 균등이 아니다' 다.
        #   종전에는 ①의 문턱으로 ②의 단어('싱크 없음')를 찍었다.
        v = ("✅**압축에 쓸 수 있다**" if s > SINK_YES else
             "🚫**압축에 못 쓴다**" if s < SINK_NO else "⚠️**경계**")
        print(f"     -> {v}   (기준 ^>{SINK_YES:.0%} 쓸 수 있다 / ^<{SINK_NO:.0%} 못 쓴다)")
        rel = ("★균등이 아니다" if s / unif >= NULL_RATIO_HIGH else "**causal 균등과 구분 안 된다**")
        print(f"     -> 분포 자체는 {rel} (causal 균등의 {s / unif:.2f}배). "
              f"🚫**'싱크가 없다' 와 '싱크를 못 쓴다' 는 다른 말이다**")
        print(f"     -> ★**버리게 되는 질량 {1 - b:.1%}** (싱크 {a.sink}개 + 최근 {a.window}개를 남길 때)")
        print(f"        (합집합 기준이다. 겹침을 두 번 세는 1-(s+w) 는 {1 - (s + w):.1%} 로 **과소평가**한다)")
        print(f"     ★깊이 추세: 앞 3개 {sum(s_all[:3]) / 3:.2%} vs "
              f"뒤 3개 {sum(s_all[-3:]) / 3:.2%} — 논문은 깊을수록 크다고 한다")
        del model

    print("\n" + "=" * 96)
    # ★★A10 조치 — **재귀 런에서는 마지막 방문만 남는다.** 잊지 않게 매번 찍는다.
    print("  ⚠️★★**재귀 런에서는 `last_probs` 가 그 모듈의 *마지막 방문*만 담는다.**")
    print("     `--train-repeat` / `--infer-repeat` 런의 앞 방문은 **덮여서 사라진다** —")
    print("     그래서 재귀 팔의 '깊이 추세' 를 논문의 깊이 법칙과 대조하면 안 된다(결과 070).")
    print("  ⚠️★**이 도구는 질량만 본다.** 잘라 보고 손실이 얼마나 오르는지는 단계1 이 잰다.")
    print("     질량이 커도 **남은 1% 가 결정적일 수 있다** — 질량은 필요조건이지 충분조건이 아니다.")
    print("  ⚠️프롬프트가 **val 앞부분 한 조각**이다. 문서 경계·언어가 섞여 있을 수 있다.")
    print("=" * 96)
    return 0 if any_ok else 2


if __name__ == "__main__":
    sys.exit(main())
