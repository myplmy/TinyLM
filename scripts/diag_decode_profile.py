#!/usr/bin/env python3
"""★P014D 선결 — **디코드 시간이 어디로 가는지 프로파일러로 본다.** (⚙1h, GPU 0)

## 왜 이것이 LUT 커널보다 먼저인가

`docs/methods/12_inference_speed.md` §12.4 가 그렇게 배치했고, 사용자가 2026-08-31 에
승인했다(판단 C2). 이유 둘:

| # | 모르는 것 | 왜 문제인가 |
|---|---|---|
| ★**1** | 디코드 76.2 ms/token 중 **절편 13.67 ms(17.9%)의 원인** | fp32 경로에서는 **3.3~4.3 ms** 였다. **배포 경로에서 4배가 된 이유가 미상**이고, 그것이 **방문 수와 무관한 고정비**라 짧은 응답일수록 비중이 커진다 |
| ★**2** | **언팩 몫이 ⚙30~42 ms** | 폭이 40% 다. 🚫**전부 유도이고 프로파일러를 한 번도 안 돌렸다** |

🚫**언팩이 실제로 얼마인지 모르는 채 ⚙6시간짜리 커널을 짜는 것은 도박**이다.
★**이 도구가 그 두 수를 실측**하고, 그 결과가 P014D 를 열지 말지 정한다.

## 무엇을 하나

같은 체크포인트를 **경로별로** 디코드시키고 `torch.profiler` 로 self CPU time 을 모은다.

    fp32   : latent 2벌 그대로 (가장 빠른 것으로 실측된 경로)
    int8   : latent 해제 + int8 저장  <- 언팩이 여기서 생긴다
    lut    : latent 해제 + LUT 1.600bpw

★**세 경로가 같은 가중치·같은 프롬프트·같은 토큰 수**이므로 차이는 **경로뿐**이다.

## 읽는 법 — 이 도구가 답하는 것과 안 하는 것

| ✅답한다 | 🚫안 한다 |
|---|---|
| 어느 연산이 시간을 먹는가(self CPU time 상위) | 🚫품질. 이 도구는 로짓을 안 본다 |
| 언팩(dequant) 계열 op 의 **합계와 비중** | 🚫커널을 짜면 얼마나 빨라지는지 — 그건 상한 계산이지 실측이 아니다 |
| 경로 사이의 토큰당 ms 차이 | 🚫다른 날 런과의 비교(세션 드리프트 7.5%) |

⚠️★**프로파일러 자체가 느리게 만든다.** 절대 tok/s 를 여기서 인용하지 않는다 —
**비중과 순위**만 읽는다. 절대 속도는 `mem_runtime` / `bench` 경로가 소유한다.

사용:
    python scripts/diag_decode_profile.py --preset m100R1c --models mC_cla2_ag4
종료코드 0 = 쟀다 / 2 = 체크포인트 없음
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROMPT = "대한민국의 수도 서울은"
# ★언팩·양자화 계열로 보는 op 이름 조각. 🚫**여기 없는 이름은 '기타' 로 간다** —
#   합계가 100% 가 되게 만들려고 억지로 분류하지 않는다.
UNPACK_HINTS = ("dequant", "unpack", "to_copy", "mul", "index_select", "gather",
                "_weight_int8pack_mm", "convert_element_type")
# ★★2026-09-02 E16 — **`aten::copy_` 를 놓치고 있었다.**
#   힌트가 `"to_copy"` 라 `aten::_to_copy` 는 잡히고 `aten::copy_` 는 안 잡혔다.
#   그런데 int8 경로에서 `copy_` 가 **386.2 ms = 35.3% 로 1위**였다(로그 065 [4/6]).
#   🚫**인쇄된 20.3% 는 과소평가**였고, 도구는 그 과소평가에 자기 판정 규칙
#   ("20% 아래면 다른 축을 먼저 본다")을 적용했다 — 판정 대상과 판정한 대상이 갈라졌다.
#   ⚠️단 `copy_` 는 fp32 경로에도 9.6 ms 있다 — **순수 언팩이 아니다.**
#   -> 하나로 못 정하므로 **대역**으로 낸다. 아래는 '언팩일 수도 있는' 집합이다.
UNPACK_MAYBE = ("copy_",)
GEMM_HINTS = ("addmm", "mm", "matmul", "linear", "bmm", "_weight_int8pack_mm")
# ★성공 기준값 — `check_diag_data` 가 본다(함정 32).
#   ⚙12_inference_speed §12.2 의 유도값. **이 도구가 그것을 검증하러 간다.**
EXPECTED_UNPACK_LO, EXPECTED_UNPACK_HI = 0.40, 0.55


def profile_path(model, cfg, tok, device, n_new, label):
    import torch
    from torch.profiler import profile, ProfilerActivity
    ids = torch.tensor([tok.encode(PROMPT).ids], dtype=torch.long, device=device)
    with torch.no_grad():
        model(ids)                                       # warm-up + prefill
    # ★`tinylm/infer/generate.py` 의 디코드 루프와 **같은 규약**으로 돈다 —
    #   첫 스텝은 프롬프트 전체(prefill), 이후는 직전 1토큰만. 그리디로 고정한다.
    #   🚫여기서 루프를 새로 발명하면 프로파일이 실제 경로와 달라진다(함정 18).
    assert _accepts_cache(model), "forward 가 past_kv 를 안 받는다 — 디코드 경로가 아니다"
    with torch.no_grad(), profile(activities=[ProfilerActivity.CPU],
                                  record_shapes=False) as prof:
        x = ids
        past = None
        for _ in range(n_new):
            xin = x if past is None else x[:, -1:]
            logits, past = model(xin, past_kv=past, use_cache=True)
            nxt = logits[:, -1, :].float().argmax(-1, keepdim=True)
            x = torch.cat([x, nxt], dim=1)
    evs = prof.key_averages()
    total = sum(e.self_cpu_time_total for e in evs) / 1e3      # ms
    rows = sorted(evs, key=lambda e: -e.self_cpu_time_total)
    unpack = sum(e.self_cpu_time_total for e in evs
                 if any(h in e.key for h in UNPACK_HINTS)) / 1e3
    # ★확실 집합에 안 든 것 중 '언팩일 수도 있는' 것 — 겹치지 않게 뺀다.
    maybe = sum(e.self_cpu_time_total for e in evs
                if any(h in e.key for h in UNPACK_MAYBE)
                and not any(h in e.key for h in UNPACK_HINTS)) / 1e3
    gemm = sum(e.self_cpu_time_total for e in evs
               if any(h in e.key for h in GEMM_HINTS)) / 1e3
    return {"label": label, "total_ms": total, "per_token": total / max(n_new, 1),
            "unpack_ms": unpack, "maybe_ms": maybe, "gemm_ms": gemm,
            "top": rows[:12], "n": n_new}


def _accepts_cache(model) -> bool:
    import inspect
    try:
        return "past_kv" in inspect.signature(model.forward).parameters
    except (ValueError, TypeError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="디코드 시간 분해 (P014D 선결)")
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--max-new", type=int, default=32)
    ap.add_argument("--paths", nargs="+", default=["fp32", "int8", "lut"],
                    choices=["fp32", "int8", "lut"])
    a = ap.parse_args()

    import torch                                          # noqa: F401
    import tinylm                                         # noqa: F401
    from tinylm import paths
    from tinylm.data import load_tokenizer
    from tinylm.infer.generate import load_model
    from tokenizers import Tokenizer

    tok = load_tokenizer(a.data)
    base = f"{a.preset}_{a.data}_{a.tokens}"
    print("=" * 96)
    print("  P014D 선결 — 디코드 시간 분해 (torch.profiler, CPU, 학습 0)")
    print(f"  프롬프트 1개 · 새 토큰 {a.max_new}개 · 경로 {a.paths}")
    print("  ⚠️★프로파일러가 켜져 있으면 느려진다. **비중과 순위만** 읽는다.")
    print("=" * 96)

    any_ok = False
    for tag in a.models:
        ck = paths.RUNS / "ckpt" / f"{base}_{tag}.pt"
        if not ck.exists():
            print(f"\n  [건너뜀] 체크포인트 없음: {ck.name}")
            continue
        arch = "dense" if "dense" in tag else "tied"
        results = []
        for path in a.paths:
            # ★★2026-09-02 — 여기서 죽었다(ValueError: 모르는 fmt: 'fp32').
            #   `path` 는 **경로 이름**이고 `emb_quant` 는 **양자화 형식**이다.
            #   같은 문자열 'fp32' 가 두 양을 가리켰다(함정 28).
            #   임베딩을 그대로 두는 것은 `None` 이지 'fp32' 가 아니다.
            model, cfg, dev = load_model(
                arch=arch, ckpt_path=str(ck), device="cpu",
                emb_quant=("int8" if path != "fp32" else None))
            if path != "fp32":
                model.drop_latent()
                if path == "lut":
                    model.cfg.lut_out_chunk = 0
                    model.to_lut()
                else:
                    model.to_int8()
            model.eval()
            results.append(profile_path(model, cfg, tok, dev, a.max_new, path))
            del model
        any_ok = True

        print(f"\n  ── {tag} ({arch}) " + "-" * 40)
        print(f"     {'경로':>6}{'총 ms':>10}{'토큰당':>10}"
              f"{'언팩(확실)':>12}{'+copy_':>10}{'★언팩 대역':>18}{'GEMM':>9}")
        for r in results:
            lo = r['unpack_ms'] / max(r['total_ms'], 1e-9)
            hi = (r['unpack_ms'] + r['maybe_ms']) / max(r['total_ms'], 1e-9)
            print(f"     {r['label']:>6}{r['total_ms']:>10.1f}{r['per_token']:>10.2f}"
                  f"{r['unpack_ms']:>12.1f}{r['maybe_ms']:>10.1f}"
                  f"{lo:>9.1%} ~{hi:>7.1%}"
                  f"{r['gemm_ms'] / max(r['total_ms'], 1e-9):>9.1%}")
        base_r = next((r for r in results if r["label"] == "fp32"), None)
        for r in results:
            if base_r and r is not base_r:
                d = r["per_token"] - base_r["per_token"]
                print(f"     ★{r['label']} 이 fp32 보다 토큰당 {d:+.2f} ms "
                      f"({d / max(base_r['per_token'], 1e-9):+.0%})")
        for r in results:
            print(f"\n     [{r['label']}] self CPU time 상위 12")
            for e in r["top"]:
                ms = e.self_cpu_time_total / 1e3
                print(f"        {ms:>9.1f} ms  {ms / max(r['total_ms'], 1e-9):>6.1%}  "
                      f"{e.key[:52]}")
        for r in results:
            if r["label"] == "fp32":
                continue
            lo = r["unpack_ms"] / max(r["total_ms"], 1e-9)
            hi = (r["unpack_ms"] + r["maybe_ms"]) / max(r["total_ms"], 1e-9)
            # ★대역이 유도구간과 **겹치면 판정하지 않는다.**
            #   점 하나로 축을 닫은 적이 있다(E16) — 그때 그 점이 과소평가였다.
            if hi < EXPECTED_UNPACK_LO:
                v = "🚫★**유도 대역 아래**(상한으로도 못 미친다)"
            elif lo > EXPECTED_UNPACK_HI:
                v = "🚫★**유도 대역 위**(하한으로도 넘는다)"
            else:
                v = "⚠️★**판정 불가 — 대역이 유도(40~55%)와 겹친다**"
            print(f"\n     ★{r['label']} 언팩 비중 {lo:.1%} ~ {hi:.1%} -> {v}")
            print("        (12_inference_speed §12.2 의 ⚙30~42 ms / ⚙40~55% 유도)")
            if base_r:
                d = r["total_ms"] - base_r["total_ms"]
                print(f"        ★fp32 대비 증분 {d:+.1f} ms = 총시간의 "
                      f"{d / max(r['total_ms'], 1e-9):.1%} — **가정 없이 재는 유일한 수**다")

    print("\n" + "=" * 96)
    print("  ★이 수가 P014D 를 여는가")
    print("    · 언팩 **대역**이 유도(40~55%) 안이면 LUT 커널의 상한이 실재한다 -> ⚙6h 를 쓸 만하다")
    print("    · 대역의 **상한**이 20% 아래면 커널을 짜도 이론 상한이 작다 -> **다른 축을 먼저 본다**")
    print("    · 🚫대역이 걸치면 **판정하지 않는다**(E16: 점 추정 하나가 과소평가였다)")
    print("    · 어느 쪽이든 **절편의 정체**를 상위 12 목록에서 찾는다 — 그것이 §12.1 의 미해결이다")
    print("  🚫**여기서 tok/s 를 인용하지 않는다.** 프로파일러가 켜진 수치다.")
    print("=" * 96)
    return 0 if any_ok else 2


if __name__ == "__main__":
    sys.exit(main())
