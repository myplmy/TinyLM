#!/usr/bin/env python3
"""P030 단계1.5-B — KV 캐시 정확성의 **진짜 게이트**: teacher-forced 로짓 동등성.

★왜 기존 게이트를 대체하는가 (결과 014 §8)
  P030 계획 단계1 이 요구한 것은 **"캐시 유/무의 로짓이 일치"** 다.
  `check_cache_equivalence()` 는 그것을 **"디코딩된 문자열이 완전히 같다"** 로 대리했다.
  그 대리는 세 가지를 통과시킨다:
    (a) bf16 autocast(cuda) — 가수 8비트
    (b) **자기회귀 24스텝** — near-tie 한 번 뒤집히면 이후 전부가 달라진다(혼돈 증폭)
    (c) 토크나이저 decode
  실제로 `mA_g4s34_k4` 가 2/5 불일치, `p6d` 가 5/5 일치로 갈렸는데,
  RoPE 슬라이스와 SDPA 마스크는 **dense 와 tied 가 공유하는 코드**다. p6d 가 통과했으므로
  그 둘은 이미 무죄이고, 게이트는 **아키텍처가 아니라 near-tie 빈도**를 재고 있었다.

★이 스크립트가 재는 것
  같은 토큰열을 두 경로로 흘리되 **샘플링도 피드백도 없다(teacher forcing)**:
    path A : 전체 시퀀스 1회 forward, 캐시 없음
    path B : 앞부분을 prefill(use_cache) → 나머지를 **알려진 다음 토큰**으로 1개씩
  위치별 로짓을 비교한다. **결정론적이고 증폭이 없다.**

  하드 게이트 : fp32 에서 max|Δlogit| < tol (기본 1e-3)
  보고 전용   : bf16 그리디 불일치 + **최초 분기점의 top-2 로짓 간격**
                간격이 관측된 로짓 오차보다 작으면 **타이브레이크**이지 버그가 아니다.

★오차 패턴이 버그 위치를 지목한다 (기존 게이트는 못 하던 것)
    위치에 따라 증가            → RoPE 절대위치 오프셋
    prefill 경계 이후 균일하게 큼 → SDPA 마스크 정렬
    tied 에서만 큼              → CLA owner 키 캐시(kv_bank)
    평탄한 1e-6                 → 정상

사용법
  python scripts/diag_kvcache.py --models mA_g4s34_k4 mC_g8_k4 p6d --device cpu --tol 1e-3
  python scripts/diag_kvcache.py --models mA_g4s34_k4 --device cuda --report-greedy
종료코드: 0 통과 / 1 허용오차 초과 / 2 체크포인트 없음
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 한글 프롬프트가 필요해 .bat 이 아니라 여기 산다(ASCII 규약). P029 프롬프트와 같은 집합.
PROMPTS = [
    "대한민국의 수도 서울은",
    "조선 시대의 과학 기술은 세종대왕 때",
    "물이 끓는 온도는 섭씨",
    "The Industrial Revolution began in",
    "인공지능 기술의 발전은 사회에",
]

DEFAULT_MODELS = [("mA_g4s34_k4", "tied"), ("mC_g8_k4", "tied"), ("p6d", "dense")]


def banner(s, ch="="):
    print("\n" + ch * 88)
    print(f"  {s}")
    print(ch * 88)


def _arch_of(tag):
    return "dense" if tag.startswith(("p6d", "dense", "p12d")) else "tied"


def teacher_forced_delta(model, cfg, tok, prompt, max_new, device, use_autocast):
    """★핵심. 같은 토큰열을 두 경로로 흘려 위치별 로짓 차이를 잰다.

    토큰열은 **캐시 없는 경로의 그리디 결과**로 만든다(둘 중 하나를 골라야 하고,
    어느 쪽을 고르든 두 경로 모두 **같은 입력**을 받는다는 점이 중요하다).
    반환: (per_step_max, per_step_mean, argmax_agree, n_steps, prefill_len)
    """
    import torch

    ids = tok.encode(prompt).ids
    T0 = len(ids)
    dev_t = device if isinstance(device, str) else device.type
    ac = dict(device_type=dev_t, dtype=torch.bfloat16, enabled=bool(use_autocast))

    # 1) 캐시 없는 경로로 토큰열을 만든다(그리디). 이 열이 두 경로의 공통 입력이 된다.
    x = torch.tensor([ids], dtype=torch.long, device=device)
    with torch.no_grad():
        for _ in range(max_new):
            with torch.autocast(**ac):
                lg = model(x[:, -cfg.max_seq_len:])[:, -1, :].float()
            x = torch.cat([x, lg.argmax(-1, keepdim=True)], dim=1)
    seq = x                                              # (1, T0+max_new)

    # 2) path A — 전체 1회 forward, 캐시 없음
    with torch.no_grad(), torch.autocast(**ac):
        logits_A = model(seq)[0].float()                 # (T, V)

    # 3) path B — prefill(T0) 후 나머지를 1토큰씩. **teacher forcing** 이라 피드백이 없다.
    outs, past = [], None
    with torch.no_grad():
        with torch.autocast(**ac):
            lg, past = model(seq[:, :T0], past_kv=None, use_cache=True)
        outs.append(lg[0].float())                       # prefill 구간 전체
        for t in range(T0, seq.shape[1]):
            with torch.autocast(**ac):
                lg, past = model(seq[:, t:t + 1], past_kv=past, use_cache=True)
            outs.append(lg[0].float())
    logits_B = torch.cat(outs, dim=0)                    # (T, V)

    assert logits_A.shape == logits_B.shape, f"{logits_A.shape} vs {logits_B.shape}"
    d = (logits_A - logits_B).abs()
    per_max = d.max(dim=-1).values                       # (T,)
    per_mean = d.mean(dim=-1)
    agree = (logits_A.argmax(-1) == logits_B.argmax(-1))
    return per_max, per_mean, agree, seq.shape[1], T0


def greedy_tie_margin(model, cfg, tok, prompt, max_new, device, use_autocast):
    """보고 전용: 캐시 유/무 그리디를 **각자** 돌려 최초 분기 위치와 그 지점의 top-2 간격."""
    import torch

    ids = tok.encode(prompt).ids
    dev_t = device if isinstance(device, str) else device.type
    ac = dict(device_type=dev_t, dtype=torch.bfloat16, enabled=bool(use_autocast))

    def run(use_cache):
        x = torch.tensor([ids], dtype=torch.long, device=device)
        gaps, past = [], None
        with torch.no_grad():
            for _ in range(max_new):
                if use_cache:
                    xin = x if past is None else x[:, -1:]
                    with torch.autocast(**ac):
                        lg, past = model(xin, past_kv=past, use_cache=True)
                    lg = lg[:, -1, :].float()
                else:
                    with torch.autocast(**ac):
                        lg = model(x[:, -cfg.max_seq_len:])[:, -1, :].float()
                top2 = lg.topk(2, dim=-1).values[0]
                gaps.append(float(top2[0] - top2[1]))
                x = torch.cat([x, lg.argmax(-1, keepdim=True)], dim=1)
        return x[0].tolist(), gaps

    a_ids, a_gaps = run(True)
    b_ids, _ = run(False)
    n0 = len(ids)
    for i in range(n0, min(len(a_ids), len(b_ids))):
        if a_ids[i] != b_ids[i]:
            return i - n0, a_gaps[i - n0]                # (분기 스텝, 그 지점 top-2 간격)
    return None, None


def main():
    ap = argparse.ArgumentParser(description="KV 캐시 teacher-forced 로짓 동등성 게이트")
    ap.add_argument("--kv-dtype", choices=["fp32", "bf16", "fp16"], default="fp32",
                    help="★P077 단계1 — KV **저장** 정밀도. 이 게이트가 바로 그 대가를 잰다. "
                         "fp32 = 종전 = 비트 동일. bf16 이면 편차가 **작지만 0 이 아니어야** 한다 — "
                         "정확히 0 이면 플래그가 아무것도 안 한 것이다(함정 37)")
    ap.add_argument("--models", nargs="*", help="태그 목록(기본 mA_g4s34_k4 mC_g8_k4 p6d)")
    ap.add_argument("--device", default="cpu",
                    help="cpu 면 autocast 가 꺼져 fp32(하드 게이트용). cuda 는 bf16")
    ap.add_argument("--tol", type=float, default=None,
                    help="허용 max|Δlogit|. 생략하면 **KV dtype 이 정한다**(아래 KV_TOL). "
                         "명시하면 그 값이 이긴다")
    ap.add_argument("--max-new", type=int, default=24, help="teacher-forced 스텝 수")
    ap.add_argument("--report-greedy", action="store_true",
                    help="그리디 분기 위치와 top-2 간격을 함께 보고(판정에는 쓰지 않는다)")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--preset", default="m100")
    a = ap.parse_args()

    from tinylm import paths
    from tinylm.infer.generate import load_model
    from tokenizers import Tokenizer
    from tinylm.data import tokenizer_path

    models = [(t, _arch_of(t)) for t in a.models] if a.models else DEFAULT_MODELS
    tok = Tokenizer.from_file(str(tokenizer_path(a.data)))
    base = f"{a.preset}_{a.data}_{a.tokens}"
    use_ac = (a.device == "cuda")

    # ★★2026-08-31 신설 — **허용오차는 KV 저장 dtype 이 정한다**(결과 065 §오류 E4).
    #   종전에는 tol 이 1e-3 고정이라 `--kv-dtype bf16` 런이 **exit 1** 로 끝나고
    #   *"fp32 에서 초과 = 실제 버그다"* 라는 **fp32 용 진단문**을 찍었다. 함정 38 계열
    #   (인쇄와 판정이 갈라진다) + 함정 40(지표가 조건을 잰다).
    #   근거: 가수 비트수 → 상대오차. bf16 = 8비트(2^-8 = 3.9e-3), fp16 = 11비트(4.9e-4).
    #   로짓 규모가 O(10) 이므로 절대 편차 상한을 그 곱의 한 자릿수 여유로 잡는다.
    tol_map = {"fp32": 1.0e-3, "bf16": 5.0e-2, "fp16": 5.0e-3}
    tol = a.tol if a.tol is not None else tol_map[a.kv_dtype]
    lossy_kv = (a.kv_dtype != "fp32")

    banner(f"P030 1.5-B — teacher-forced 로짓 동등성  device={a.device}  "
           f"{'bf16 autocast' if use_ac else 'fp32(autocast off)'}  "
           f"KV={a.kv_dtype}  tol={tol:g}")
    print("  ★자기회귀 피드백을 끊었으므로 이 수치는 결정론적이다.")
    print("  ★오차 패턴 읽는 법: 위치증가=RoPE / prefill 이후 균일=마스크 / tied만=CLA / 평탄 1e-6=정상")
    if use_ac:
        print("  ※ cuda 는 bf16 이라 tol 을 넘는 것이 정상일 수 있다. **하드 게이트는 cpu(fp32)** 다.")
    if lossy_kv:
        print(f"  ★★KV 저장이 **손실 dtype**({a.kv_dtype}) 이므로 통과 조건이 셋이다 —")
        print(f"     ① 편차 ^> 0 (0 이면 플래그가 캐시에 안 닿았다 · 함정 37)")
        print(f"     ② 편차 ^< tol {tol:g} (가수 비트수에서 유도)")
        print(f"     ③ ★**argmax 불일치 0** — 결정이 안 바뀌는 것이 캐시가 지켜야 할 계약이다")

    worst, missing, rows = {}, [], []
    for tag, arch in models:
        ck = paths.RUNS / "ckpt" / f"{base}_{tag}.pt"
        if not ck.exists():
            print(f"\n  [건너뜀] 체크포인트 없음: {ck.name}")
            missing.append(tag)
            continue
        model, cfg, device = load_model(arch=arch, ckpt_path=str(ck), device=a.device)
        # ★★P077 단계1 — KV **저장** 정밀도. 이 게이트가 바로 그 대가를 잰다.
        #   ⚠️`fp32` 면 아무것도 안 한다 = 비트 동일. bf16 이면 편차가 **작지만 0 이 아니어야**
        #   한다 — 정확히 0 이면 플래그가 캐시에 안 닿은 것이다(함정 37).
        if a.kv_dtype != "fp32":
            cfg.kv_dtype = a.kv_dtype
            model.cfg.kv_dtype = a.kv_dtype
            print(f"  ★KV 저장 dtype = {a.kv_dtype} (계산은 fp32 로 되올린다). "
                  f"편차가 0 이면 플래그가 안 닿은 것이다")
        print(f"\n  ── {tag} ({arch}, cla_group={cfg.cla_group}, "
              f"mlp_group={cfg.mlp_group if cfg.tie_mlp else 1}, "
              f"sparse34={bool(getattr(cfg, 'sparse34', False))}) "
              + "─" * 20)
        m_all = 0.0
        nag_all = 0                                  # ★argmax 불일치 총합 — 손실 KV 의 본 게이트
        for prompt in PROMPTS:
            per_max, per_mean, agree, T, T0 = teacher_forced_delta(
                model, cfg, tok, prompt, a.max_new, device, use_ac)
            pre = float(per_max[:T0].max())          # prefill 구간(캐시 무관 — 두 경로 동일해야 함)
            dec = float(per_max[T0:].max()) if T > T0 else 0.0
            # 위치 의존성: decode 구간 전반부 vs 후반부 (RoPE 오프셋이면 뒤로 갈수록 커진다)
            half = T0 + max(1, (T - T0) // 2)
            d1 = float(per_max[T0:half].max()) if half > T0 else 0.0
            d2 = float(per_max[half:].max()) if T > half else 0.0
            nag = int((~agree).sum())
            m_all = max(m_all, dec, pre)
            nag_all += nag
            flag = "OK " if max(pre, dec) < tol else "!! "
            print(f"    {flag}{prompt[:22]:<24} prefill {pre:.2e}  decode {dec:.2e}  "
                  f"(전반 {d1:.2e} / 후반 {d2:.2e})  argmax불일치 {nag}/{T}")
            if a.report_greedy:
                idx, gap = greedy_tie_margin(model, cfg, tok, prompt, a.max_new, device, use_ac)
                if idx is None:
                    print(f"        그리디: 일치")
                else:
                    verdict = ("타이브레이크(간격 < 로짓오차)" if gap is not None and gap < dec
                               else "간격이 로짓오차보다 크다 — 조사 필요")
                    print(f"        그리디: 스텝 {idx} 에서 분기, 그 지점 top-2 간격 {gap:.4f}  → {verdict}")
        worst[tag] = (m_all, nag_all)
        rows.append((tag, arch, cfg, m_all, nag_all))
        del model

    def verdict_of(m: float, nag: int) -> str:
        """★손실 KV 는 통과 조건이 셋이다(편차^>0 · 편차^<tol · argmax 0)."""
        if lossy_kv and m == 0.0:
            return "무반응"                          # 함정 37 — 플래그가 안 닿았다
        if m >= tol:
            return "초과"
        if lossy_kv and nag:
            return "결정변경"
        return "통과"

    banner("요약")
    print(f"    {'모델':<16}{'arch':>7}{'cla':>5}{'g':>4}{'s34':>7}"
          f"{'max|dlogit|':>14}{'argmax≠':>9}  판정")
    print("    " + "-" * 72)
    for tag, arch, cfg, m, nag in rows:
        print(f"    {tag:<16}{arch:>7}{cfg.cla_group:>5}"
              f"{(cfg.mlp_group if cfg.tie_mlp else 1):>4}"
              f"{str(bool(getattr(cfg, 'sparse34', False))):>7}{m:>14.3e}{nag:>9}  "
              f"{verdict_of(m, nag)}")
    print("    ★cla=1 인 모델(dense)만 통과하고 cla=2 가 초과하면 CLA 캐시 경로다.")
    if missing:
        print(f"\n    [건너뜀] {', '.join(missing)}")
        if not rows:
            return 2

    bad = [t for t, (m, nag) in worst.items() if verdict_of(m, nag) != "통과"]
    if not bad:
        if lossy_kv:
            mx = max(m for m, _ in worst.values())
            print(f"\n  ✅ **KV {a.kv_dtype} 통과** — 편차 {mx:.3e} (0 ^< x ^< {tol:g}) 이고 "
                  f"**argmax 불일치 0**.")
            print("     ★편차가 0 이 아니므로 플래그가 캐시에 닿았고(함정 37), "
                  "결정은 하나도 안 바뀌었다.")
            print("     ⚠️★**이것은 품질 대가가 아니다** — teacher-forced 평가는 "
                  "자기회귀 피드백이 없다. 진짜 대가는 생성 기반 평가가 잰다(P077 단계2).")
        else:
            print(f"\n  ✅ 전 모델 max|Δlogit| < {tol:g}"
                  + ("  — **캐시 구현 정확성 확인.** 속도 측정으로 진행 가능."
                     if not use_ac else
                     "  — bf16 에서도 통과. 정밀도 여유가 충분하다는 뜻."))
        return 0

    print(f"\n  ❌ 통과하지 못함: {', '.join(bad)}")
    zero = [t for t, (m, _) in worst.items() if lossy_kv and m == 0.0]
    if zero:
        print(f"     ★★**편차가 정확히 0 이다**: {', '.join(zero)}")
        print("     → `--kv-dtype` 가 캐시에 **안 닿았다**(함정 37). 뒤따르는 회계는 전부 허구다.")
        print("        볼 곳: transformer.forward 의 use_cache 반환 시 캐스팅, cfg 전파 경로")
    elif lossy_kv:
        print(f"     ★손실 KV({a.kv_dtype}) 에서 초과 — 이것은 **양자화 오차이지 버그가 아닐 수 있다.**")
        print("       argmax 불일치가 0 이면 결정은 안 바뀐 것이므로 tol 을 의심한다(함정 34).")
        print("       argmax 불일치가 있으면 그 dtype 은 이 모델에 부족하다 — 축을 닫는다.")
    elif use_ac:
        print("     단 이것은 **bf16** 이다. 하드 게이트는 `--device cpu`(fp32) 로 판정한다.")
    else:
        print("     fp32 에서 초과 = **실제 버그**다. 위의 prefill/decode/전반·후반 분해로 위치를 좁혀라.")
        print("       prefill 부터 큼        → 캐시와 무관한 문제(모델 로드·양자화)")
        print("       decode 만 크고 증가    → RoPE 오프셋(transformer.forward 의 rope 슬라이스)")
        print("       decode 만 크고 평탄    → SDPA 마스크(modules.Attention 의 tril)")
        print("       tied 만 큼             → CLA owner 키 캐시(kv_bank 키가 owner 인지)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
