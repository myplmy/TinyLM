#!/usr/bin/env python3
"""P022B 단계3 — **학습 dtype 지도를 실측한다.** 학습 0 · GPU 진단 · 수 분.

## 왜 이 도구가 생겼나

`docs/20260821_학습-dtype-지도-....md` 가 **코드 독해로** 결론을 냈다:

    GEMM·활성은 이미 bf16, master·gradient·Adam 산술은 fp32,
    남은 후보는 `_wq` 하나.

그런데 **`_wq` 를 바꿀 값어치가 있는지는 크기를 몰라서 판정할 수 없었다.**
문서 §4.2 의 *"스텝당 2~3 GB 트래픽"* 은 **⚙계산값**이고, §4.3 의
*"타잉 때문에 같은 텐서를 16번 캐스팅할 수 있다"* 는 **⚙추정**이다.

★**둘 다 여기서 실측한다.** 그리고 ★**`torch.compile` 이 융합하면 추정이 크게 과대**인데
**M4 가 그것을 가른다** — 그래서 이 도구 없이 D1 을 구현하면 안 된다.

## 네 팔

    M1  dtype·바이트 재고        문서 §1 표를 **코드 독해에서 실측으로** 승격
    M2  F.linear 호출·캐스팅 계수  ★§4.3 의 "몇 번" 을 센다
    M3  refresh_quant 단독 타이밍  ★D1(=`_wq` bf16 저장)의 이득 상한
    M4  전체 스텝 대비 비중        "그래서 스텝의 몇 %인가"

## ★성공 기준값 — **결과 전에 못 박는다** (함정 34)

    M2 캐스팅 바이트가 스텝당 1 GB 미만        -> 🚫 D1 축 종료
    M3 refresh_quant 가 스텝의 5% 미만          -> 🚫 D1 축 종료
    M3 가 20% 이상                              -> ★D3(재계산 주기)까지 품질 실험으로 승격

⚠️ **이 도구는 "무엇이 느린가" 를 재지 "무엇을 고쳐야 하는가" 를 정하지 않는다.**
⚠️ **비트 동일**: 모델을 읽기만 한다. 학습도 저장도 하지 않는다.

사용법
    python scripts/diag_dtype_map.py --tag mC_initonly --preset m100R1c
    python scripts/diag_dtype_map.py --tag mC_d36_ag4 --preset m100R1c --iters 5
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ★성공 기준값. **먼저 인쇄하고 나중에 판정한다.**
GATE_CAST_GB = 1.0        # M2: 스텝당 캐스팅 바이트가 이보다 작으면 축 종료
GATE_REFRESH_PCT = 5.0    # M3: refresh_quant 비중이 이보다 작으면 축 종료
GATE_PROMOTE_PCT = 20.0   # M3: 이보다 크면 D3 까지 승격


def banner(s, ch="="):
    print("\n" + ch * 96)
    print(f"  {s}")
    print(ch * 96)


def _arch_of(tag):
    return "dense" if tag.startswith(("p6d", "dense", "p12d")) else "tied"


def mb(n):
    return n / 2 ** 20


# ---------------------------------------------------------------- M1

def m1_inventory(model, torch):
    """모든 텐서의 dtype·바이트를 **역할별로** 센다."""
    banner("M1 — dtype·바이트 재고 (실측)")
    buckets = defaultdict(lambda: Counter())      # 역할 -> {dtype: bytes}
    counts = defaultdict(lambda: Counter())

    def role_of(name):
        if ".emb" in name or name.startswith("emb"):
            return "embedding"
        if "attn" in name:
            return "attention"
        if "mlp" in name:
            return "mlp"
        return "기타(norm·gate·scale)"

    for n, p in model.named_parameters():
        buckets[role_of(n)][str(p.dtype)] += p.numel() * p.element_size()
        counts[role_of(n)][str(p.dtype)] += 1
    for n, b in model.named_buffers():
        buckets["buffer"][str(b.dtype)] += b.numel() * b.element_size()
        counts["buffer"][str(b.dtype)] += 1

    # `_wq` 는 파라미터도 버퍼도 아니다 — 직접 센다
    wq_bytes, wq_n, wq_dt = 0, 0, Counter()
    for m in getattr(model, "_tlinear_cache", []):
        w = getattr(m, "_wq", None)
        if w is not None:
            wq_bytes += w.numel() * w.element_size()
            wq_n += 1
            wq_dt[str(w.dtype)] += 1

    print(f"  {'역할':<22}{'dtype':<18}{'MB':>10}{'텐서':>8}")
    print("  " + "-" * 60)
    tot = 0
    for role in sorted(buckets):
        for dt, byt in sorted(buckets[role].items()):
            print(f"  {role:<22}{dt:<18}{mb(byt):>10.2f}{counts[role][dt]:>8}")
            tot += byt
    if wq_n:
        print(f"  {'★_wq(삼진 사본)':<22}{'/'.join(wq_dt):<18}{mb(wq_bytes):>10.2f}{wq_n:>8}")
    else:
        print(f"  {'★_wq(삼진 사본)':<22}{'(없음 — clear_quant 상태)':<18}")
    print("  " + "-" * 60)
    print(f"  {'파라미터+버퍼 합계':<40}{mb(tot):>10.2f} MB")
    print("\n  ⚠️ 이건 **모델 텐서**만이다. gradient·옵티마이저 상태·활성은 학습 중에만 존재한다.")
    print("     그 크기는 학습 로그의 `vram_alloc_gb`·`opt_state_mb` 를 본다.")
    return {"wq_bytes": wq_bytes, "wq_dtypes": dict(wq_dt), "param_bytes": tot}


# ---------------------------------------------------------------- M2

def m2_linear_calls(model, torch, x):
    """`F.linear` 호출을 세고 **가중치 dtype·바이트**를 기록한다.

    ★autocast 는 `F.linear` **안에서** 캐스팅하므로 밖에서 본 `w.dtype` 은 캐스팅 **전** 값이다.
      그래서 *"fp32 가중치가 몇 바이트 들어갔나"* 를 세면 **캐스팅 바이트의 상한**이 된다.
    """
    import torch.nn.functional as F
    banner("M2 — F.linear 호출 계수와 캐스팅 바이트 (autocast 안)")

    orig = F.linear
    rec = {"calls": 0, "w_fp32_bytes": 0, "w_bf16_bytes": 0, "x_dt": Counter(),
           "w_dt": Counter(), "uniq": Counter()}

    def counting_linear(inp, weight, bias=None):
        rec["calls"] += 1
        rec["x_dt"][str(inp.dtype)] += 1
        rec["w_dt"][str(weight.dtype)] += 1
        b = weight.numel() * weight.element_size()
        if weight.dtype == torch.float32:
            rec["w_fp32_bytes"] += b
        else:
            rec["w_bf16_bytes"] += b
        rec["uniq"][id(weight)] += 1
        return orig(inp, weight, bias)

    # ★`ternary.py` 는 `import torch.nn.functional as F` 로 잡아 두므로 모듈 속성을 바꾼다
    F.linear = counting_linear
    try:
        model.train()
        model.clear_quant()                       # `_wq` 를 다시 만들게 한다(학습 경로와 같게)
        with torch.no_grad(), torch.autocast(
                x.device.type, dtype=torch.bfloat16, enabled=(x.device.type == "cuda")):
            model(x)
    finally:
        F.linear = orig

    uniq_n = len(rec["uniq"])
    reuse = (rec["calls"] / uniq_n) if uniq_n else 0.0
    print(f"  호출 수                 {rec['calls']}")
    print(f"  유니크 가중치 텐서       {uniq_n}   → ★**평균 재사용 {reuse:.2f}회**")
    print(f"  입력 x dtype            {dict(rec['x_dt'])}")
    print(f"  가중치 w dtype          {dict(rec['w_dt'])}")
    print(f"  ★fp32 가중치 통과 바이트 {mb(rec['w_fp32_bytes']):.1f} MB "
          f"= **캐스팅 바이트의 상한**")
    print(f"  bf16 가중치 통과 바이트  {mb(rec['w_bf16_bytes']):.1f} MB")
    top = sorted(rec["uniq"].values(), reverse=True)[:5]
    print(f"  가장 많이 재사용된 텐서 상위 5: {top}")
    print("\n  ⚠️ **forward 1회** 기준이다. `grad_ckpt` ON 이면 학습 스텝에서 **약 2배**,")
    print("     `accum 16` 이면 **스텝당 16배**다(계산으로 환산할 것).")
    return rec


# ---------------------------------------------------------------- M3

def m3_refresh_timing(model, torch, iters):
    """`refresh_quant()` 만 단독으로 잰다."""
    banner("M3 — refresh_quant 단독 타이밍")
    dev = next(model.parameters()).device

    def sync():
        if dev.type == "cuda":
            torch.cuda.synchronize()

    model.train()
    model.clear_quant()
    for _ in range(2):                             # 워밍업
        model.refresh_quant()
    sync()
    t0 = time.perf_counter()
    for _ in range(iters):
        model.refresh_quant()
    sync()
    dt = (time.perf_counter() - t0) / iters
    print(f"  refresh_quant 1회 = **{dt * 1e3:.2f} ms**  (iters={iters}, device={dev})")
    print("  ⚠️ 워밍업 2회 후 측정. 첫 호출은 할당 때문에 느리다(속도 규약).")
    return dt


# ---------------------------------------------------------------- M4

def m4_step_share(model, torch, x, refresh_ms, iters):
    """forward+backward 한 스텝을 재고 M3 의 비중을 낸다."""
    import torch.nn.functional as F
    banner("M4 — 스텝 대비 비중")
    dev = next(model.parameters()).device

    def sync():
        if dev.type == "cuda":
            torch.cuda.synchronize()

    model.train()
    y = torch.randint(0, model.cfg.vocab_size, x.shape, device=x.device)

    def one():
        model.clear_quant()
        with torch.autocast(dev.type, dtype=torch.bfloat16, enabled=(dev.type == "cuda")):
            logits = model(x)
            loss = F.cross_entropy(logits.reshape(-1, model.cfg.vocab_size), y.reshape(-1))
        loss.backward()
        model.zero_grad(set_to_none=True)

    for _ in range(2):
        one()
    sync()
    t0 = time.perf_counter()
    for _ in range(iters):
        one()
    sync()
    step = (time.perf_counter() - t0) / iters
    pct = refresh_ms / step * 100 if step else 0.0
    print(f"  forward+backward 1회 = **{step * 1e3:.1f} ms**  (micro-batch, accum 미포함)")
    print(f"  ★refresh_quant 비중  = **{pct:.1f}%**")
    print("\n  ⚠️ 이건 **compile 없는** 경로다. 실제 학습은 `--compile` 이라 **융합될 수 있고**,")
    print("     그러면 이 비중이 **과대**다. ★**그 방향으로만 틀린다** — 실제는 이보다 작다.")
    return step, pct


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="학습 dtype 지도 실측 (학습 0)")
    ap.add_argument("--tag", default="mC_initonly")
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--micro-bs", type=int, default=2)   # 진단용. 학습 기준(8)이 아니다
    ap.add_argument("--seq", type=int, default=512)
    ap.add_argument("--iters", type=int, default=5)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()

    import torch
    from tinylm import paths
    from tinylm.infer.generate import load_model

    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    banner("P022B 단계3 — 학습 dtype 지도 실측 (학습 0 · 저장 0)", "#")
    print(f"  tag={a.tag}  preset={a.preset}  device={dev}  "
          f"micro_bs={a.micro_bs} seq={a.seq} iters={a.iters}")

    # ★규약: 성공 기준값을 **먼저** 인쇄한다(함정 34)
    print("\n  ★성공 기준값 — 결과 전에 못 박는다")
    print(f"    · M2 캐스팅 바이트가 스텝당 {GATE_CAST_GB:.1f} GB 미만  -> 🚫 D1 축 종료")
    print(f"    · M3 refresh_quant 가 스텝의 {GATE_REFRESH_PCT:.0f}% 미만 -> 🚫 D1 축 종료")
    print(f"    · M3 가 {GATE_PROMOTE_PCT:.0f}% 이상                     -> ★D3 까지 승격")
    print("  ⚠️ 기준을 못 넘으면 **모델이 아니라 축을 닫는다.** 기준값을 나중에 고치지 않는다.")

    ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, a.tag)
    if not ck.exists():
        print(f"\n  🚫 체크포인트가 없다: {ck.name}")
        return 2
    model, cfg, _ = load_model(arch=_arch_of(a.tag), ckpt_path=str(ck), device=dev)
    print(f"\n  로드 {ck.name}  ({cfg.n_layers}층, g={cfg.mlp_group}, "
          f"attn_group={getattr(cfg, 'attn_group', 1)})")

    x = torch.randint(0, cfg.vocab_size, (a.micro_bs, a.seq), device=dev)

    m1_inventory(model, torch)
    rec = m2_linear_calls(model, torch, x)
    dt = m3_refresh_timing(model, torch, a.iters)
    step, pct = m4_step_share(model, torch, x, dt, a.iters)

    # ---------------- 판정 ----------------
    banner("판정 — 기준값 대비")
    # ★grad_ckpt ON + accum 16 환산: forward 2회 × accum 16
    per_step_cast_gb = rec["w_fp32_bytes"] * 2 * 16 / 2 ** 30
    print(f"  ⚙환산 캐스팅 바이트/스텝 = {mb(rec['w_fp32_bytes']):.1f} MB × 2(grad_ckpt) × 16(accum)"
          f" = **{per_step_cast_gb:.2f} GB**")
    fails = []
    if per_step_cast_gb < GATE_CAST_GB:
        print(f"  🚫 M2 {per_step_cast_gb:.2f} GB < 기준 {GATE_CAST_GB:.1f} GB → **D1 축 종료 권고**")
        fails.append("M2")
    else:
        print(f"  ✅ M2 {per_step_cast_gb:.2f} GB ≥ 기준 {GATE_CAST_GB:.1f} GB → D1 검토 계속")
    if pct < GATE_REFRESH_PCT:
        print(f"  🚫 M3 {pct:.1f}% < 기준 {GATE_REFRESH_PCT:.0f}% → **D1 축 종료 권고**")
        fails.append("M3")
    elif pct >= GATE_PROMOTE_PCT:
        print(f"  ★★ M3 {pct:.1f}% ≥ {GATE_PROMOTE_PCT:.0f}% → **D3(재계산 주기)까지 승격 검토**")
    else:
        print(f"  ✅ M3 {pct:.1f}% → D1 검토 계속")

    print(f"\n  기준 미달 {len(fails)}건: {fails or '없음'}")
    print("  ⚠️ **두 기준이 갈리면(하나만 통과) 축을 닫지 않는다** — 원인이 다르기 때문이다.")
    print("     M2 는 **대역폭**, M3 는 **연산 시간**을 잰다(함정 1: 한 이름이 두 양).")
    print("  ⚠️ compile 미적용 경로다. 실제 학습은 이보다 **빠를 수 있다**(§M4 주의).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
