#!/usr/bin/env python3
"""★★P014 단계0 — **LUT 참조 구현의 정확성·메모리 게이트.** 학습 0.

## 이 도구가 답하는 것

| # | 질문 | 성공 기준값(사전 고정) |
|---|---|---|
| **L1** | 패킹 왕복이 **무손실인가** | ★**불일치 0개.** 하나라도 있으면 포맷이 깨진 것 |
| **L2** | LUT matmul 이 dense matmul 과 **같은가** | ★**상대오차 < 1e-5**(fp32). 정수 가중치·실수 활성이라 **원리적으로 정확**하다 |
| **L3** | 그룹 스케일(`micro_group`)을 **받는가** | ★**받는다.** P014B §1.1 게이트 **U2** |
| **L4** | 실제 packed bpw | ★**1.600**(5트릿/바이트). 이론 하한 1.585 대비 낭비 **0.95%** |
| **L5** | 상주 추정 | ★**결과 052 재현 + 표준모델 신규 추정.** ⚠️052 의 18.3 은 `m100R1q` 값이고 **표준모델이 아니다** |

⚠️★**이 도구는 속도를 일부러 안 잰다.** 참조 구현은 느리고, **느린 것을 재면
"LUT 는 느리다" 라는 틀린 결론**이 남는다. 속도 게이트는 **P014B** 가 소유한다
(`check_fused_int8.py` 가 같은 이유로 속도를 안 재는 것과 같은 규약).

## 계측 규약 (`check_diag_data.py` 계약)

    1. 절대지표에 난수 정답을 쓰지 않는다 — L1/L2 는 **실제 텐서 대조**다
    2. 성공 기준값을 결과보다 **먼저** 인쇄한다 (위 표)
    3. 시드 고정

사용법
    python scripts/diag_lut_kernel.py                 # 합성 텐서로 L1~L4
    python scripts/diag_lut_kernel.py --ckpt <경로>   # 실제 체크포인트로 L5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def banner(s, ch="="):
    print("\n" + ch * 96)
    print(f"  {s}")
    print(ch * 96)


def main():
    ap = argparse.ArgumentParser(description="P014 단계0 LUT 참조 구현 게이트 (학습 0)")
    ap.add_argument("--g", type=int, default=4, help="LUT 묶음 크기. 3^g 로 폭발하므로 4 권장")
    ap.add_argument("--dim", type=int, default=768)
    ap.add_argument("--out", type=int, default=2048)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--micro-group", type=int, default=128)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--ckpt", default=None, help="실제 체크포인트로 L5 를 잰다")
    a = ap.parse_args()

    import torch
    from tinylm.model import lut as L

    torch.manual_seed(a.seed)

    banner("★P014 단계0 — LUT 참조 구현. **성공 기준값을 결과보다 먼저 인쇄한다**(함정 34)", "#")
    print("  L1 패킹 왕복 불일치        기준: **0개**")
    print("  L2 LUT vs dense 상대오차   기준: **< 1e-5** (fp32, 정수 가중치라 원리적으로 정확)")
    print("  L3 그룹 스케일 수용         기준: **받는다** (P014B §1.1 게이트 U2)")
    print("  L4 packed bpw              기준: **1.600** (이론 하한 log2(3)=1.585, 낭비 0.95%)")
    print("  L5 상주 추정               기준: **052 의 18.3 재현**(m100R1q) + 표준모델은 별도")
    print("\n  🚫★**속도는 일부러 안 잰다.** 참조 구현은 느리다 — 재면 틀린 결론이 남는다.")
    print("     속도 게이트는 P014B 가 소유한다.")

    fails = []

    # ── L1
    banner("L1 — 패킹 왕복")
    w = torch.randint(-1, 2, (a.out, a.dim), dtype=torch.int8)
    packed, n = L.pack_trits(w)
    back = L.unpack_trits(packed, n)
    bad = int((back != w).sum())
    print(f"  원본 {tuple(w.shape)} int8 -> packed {tuple(packed.shape)} uint8 -> 복원 {tuple(back.shape)}")
    print(f"  불일치 **{bad}개**   {'✅ 통과' if bad == 0 else '🚫 실패'}")
    if bad:
        fails.append(f"L1 패킹 왕복 불일치 {bad}개")

    # 경계: 5의 배수가 아닌 길이
    for n_odd in (1, 4, 6, 9, 771):
        w2 = torch.randint(-1, 2, (3, n_odd), dtype=torch.int8)
        p2, n2 = L.pack_trits(w2)
        if int((L.unpack_trits(p2, n2) != w2).sum()):
            fails.append(f"L1 길이 {n_odd} 에서 왕복 실패")
            print(f"  🚫 길이 {n_odd} 왕복 실패")
    print(f"  경계 길이 5종(1·4·6·9·771) {'✅ 전부 통과' if not fails else '🚫 실패 있음'}")

    # ── L2
    banner("L2 — LUT matmul vs dense matmul (스케일 없음)")
    x = torch.randn(a.batch, a.dim)
    codes, i_pad = L.weight_codes(w, a.g)
    y_lut = L.lut_linear(x, codes, a.g, i_pad)
    y_ref = x @ w.to(torch.float32).t()
    rel = float((y_lut - y_ref).abs().max() / y_ref.abs().max().clamp(min=1e-12))
    print(f"  codes {tuple(codes.shape)} (int64 인덱스, 3^{a.g}={3**a.g} 패턴)")
    print(f"  최대 상대오차 **{rel:.3e}**   {'✅ 통과' if rel < 1e-5 else '🚫 실패'}")
    if rel >= 1e-5:
        fails.append(f"L2 상대오차 {rel:.3e} >= 1e-5")

    # ── L3
    banner("L3 — 그룹 스케일 수용 (P014B 게이트 U2)")
    ng = a.dim // a.micro_group
    if a.dim % a.micro_group:
        print(f"  ⚠️ dim {a.dim} 이 micro_group {a.micro_group} 의 배수가 아니다 — L3 건너뜀")
    else:
        alpha = torch.rand(a.out, ng) * 0.05 + 0.01
        y_lut_a = L.lut_linear(x, codes, a.g, i_pad, alpha=alpha, group=a.micro_group)
        wf = w.to(torch.float32).reshape(a.out, ng, a.micro_group) * alpha.unsqueeze(-1)
        y_ref_a = x @ wf.reshape(a.out, a.dim).t()
        rel_a = float((y_lut_a - y_ref_a).abs().max() / y_ref_a.abs().max().clamp(min=1e-12))
        print(f"  그룹 {ng}개 x {a.micro_group}원소, alpha {tuple(alpha.shape)}")
        print(f"  최대 상대오차 **{rel_a:.3e}**   {'✅ 통과' if rel_a < 1e-5 else '🚫 실패'}")
        print("  ★**우리 커널은 그룹 스케일을 받는다.** BitNet 원형(텐서 스케일)과 다르고,")
        print("    이것이 외부 커널을 그대로 못 쓰는 이유의 절반이다(P014B §1.1 U2).")
        if rel_a >= 1e-5:
            fails.append(f"L3 그룹스케일 상대오차 {rel_a:.3e}")

    # ── L4
    banner("L4 — packed bpw 실측")
    nw = a.out * a.dim
    pb = L.packed_bytes(nw)
    got = pb * 8 / nw
    print(f"  가중치 {nw:,}개 -> packed **{pb:,} 바이트** = **{got:.4f} bpw**")
    print(f"  int8 이라면 {nw:,} 바이트 ({nw / pb:.2f}배)  /  fp32 라면 {nw * 4:,} 바이트")
    print(f"  이론 하한 log2(3) = 1.5850,  낭비 **{(got / 1.58496 - 1) * 100:.2f}%**")
    print(f"  {'✅ 통과' if abs(got - 1.6) < 0.01 else '🚫 실패'}  기준 1.600")
    if abs(got - 1.6) >= 0.01:
        fails.append(f"L4 bpw {got:.4f} != 1.600")

    # ── L5
    banner("L5 — 상주 추정 (결과 052 재현 + 표준모델 신규 추정)")
    print("  ⚠️★**결과 052 §3.1 의 18.3 MiB 는 `m100R1q` 값이다** — **표준모델이 아니다.**")
    print("     `m100R1q` 는 **임베딩이 인수분해**돼 있어 임베딩 int8 이 8.3 MiB 다.")
    print("     ★**2026-08-22 확정된 표준모델 `mC_d36_ag4_nokd` 는 임베딩이 통짜 32768x768** 이라")
    print("     같은 표를 그대로 옮기면 **틀린다.** 아래에서 둘을 따로 낸다.\n")

    # (A) 결과 052 재현 — 표의 MiB 에서 역산한다. **개수를 지어내지 않는다.**
    T_MIB_Q, E_MIB_Q, O_MIB_Q = 37.4, 8.3, 0.4      # 052 §3.1 int8 + emb int8 행
    n_tern_q = int(T_MIB_Q * 2 ** 20)                # int8 이므로 1바이트 = 1가중치
    rq = L.residency_bytes(n_tern_q, 0, 4, n_groups=n_tern_q // a.micro_group)
    tot_q = rq["codes_MiB"] + rq["alpha_MiB"] + E_MIB_Q + O_MIB_Q
    print(f"  (A) m100R1q 재현  삼진 {n_tern_q:,}개")
    print(f"      LUT 코드 {rq['codes_MiB']:.2f} + alpha {rq['alpha_MiB']:.2f} "
          f"+ emb int8 {E_MIB_Q} + 기타 {O_MIB_Q} = **{tot_q:.2f} MiB**")
    print(f"      결과 052 는 **18.3** 이라고 적었다. 차 {tot_q - 18.3:+.2f} MiB")
    if abs(tot_q - 18.3) > 1.0:
        print("      ⚠️★**1 MiB 넘게 다르다.** 052 는 1.71 bpw 를 가정했고 우리 포맷은 "
              f"{L.bpw():.3f} bpw + alpha 다. **어느 쪽이 옳은지는 실측이 정한다** — "
              "지금은 **둘을 다 적어 둔다**(함정 34: 기준값을 먼저 의심).")

    # (B) 표준모델 — 실제 형상에서 센다
    VOCAB, DIM = 32768, 768
    n_emb = VOCAB * DIM
    print(f"\n  (B) 표준모델 mC_d36_ag4_nokd  (임베딩 {VOCAB}x{DIM} = {n_emb:,} 통짜)")
    if a.ckpt:
        import torch as _t
        sd = _t.load(a.ckpt, map_location="cpu")
        sd = sd.get("model", sd)
        n_tern = sum(v.numel() for k, v in sd.items() if k.endswith("weight") and v.dim() == 2
                     and v.shape[0] != VOCAB and v.shape[1] != VOCAB)
        print(f"      ✅**체크포인트 실측** 2차원 비임베딩 가중치 {n_tern:,}개")
    else:
        n_tern = 47_255_552
        print(f"      ⚠️**추정값 {n_tern:,}** — `--ckpt <경로>` 를 주면 실측한다")
    for name, eb in (("emb fp32", 4), ("emb bf16", 2), ("emb int8", 1)):
        r = L.residency_bytes(n_tern, n_emb, other_bytes_per=eb,
                              n_groups=n_tern // a.micro_group)
        tot = r["total_MiB"] + O_MIB_Q
        mark = "✅" if tot < 40 else "🚫"
        print(f"      LUT + {name:<9} 코드 {r['codes_MiB']:6.2f} + alpha {r['alpha_MiB']:5.2f} "
              f"+ emb {r['other_MiB']:6.2f} + 기타 {O_MIB_Q} = {mark}**{tot:6.2f} MiB**")
    print("\n  ★★**표준모델에서는 여유가 052 의 21.7 MiB 가 아니다.** 임베딩이 통짜라서 그렇다.")
    print("     → ★**LUT 와 임베딩 양자화는 둘 다 필요하고, 표준모델에서는 더 그렇다.**")
    print("  ⚠️★이것은 **계산**이다. 배포 경로가 생기면 `mem_runtime.py` 로 실측한다.")
    print("     ★그리고 **상주**다 — 저장(packed)과 섞지 않는다(함정 1).\n")

    banner("판정")
    if fails:
        for f in fails:
            print(f"  🚫 {f}")
        print(f"\n  총 {len(fails)}건 실패 — **포맷이나 참조 구현이 틀렸다.**")
        print("  ⚠️★게이트가 실패를 찍으면 **모델보다 기준값을 먼저 의심**한다(함정 34, 4번 중 4번).")
    else:
        print("  ✅ L1~L4 전 게이트 통과. 포맷과 참조 구현이 성립한다.")
        print("  ★**다음은 속도다** — P014B §1.1 의 U1(dim 768 에서 LUT 가 이득인가). "
              "이 파일은 그 질문에 답하지 않는다.")
    print("=" * 96)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
