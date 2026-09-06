#!/usr/bin/env python3
"""★P016/P014 — **3:4 준정형 패킹의 왕복 무손실과 상주 이득**(학습 0 · GPU 0 · CPU 만).

## 왜 이 도구가 생겼나 (2026-09-05 사용자 지시 *"미뤄 온 구현에 착수할 것"*)

`--sparse34` 는 **학습 경로**에 이미 있고 품질 대가도 측정돼 있다(결과 008:
`g4_s34` **+0.0364** · `g8_s34` **+0.0606**). 🚫**그런데 배포 상주에서 무엇을 버는지를
한 번도 안 쟀다** — 상주 식에 **bpw 가 없기 때문**이다(함정 1).

★그래서 *"1.25 bpw"* 라는 수가 **저장** 이야기인지 **상주** 이야기인지 3주 동안 미확정이었다.
`tinylm/model/lut.py` 에 **실제 패킹**을 넣었고, 이 도구가 그것을 산다.

## 성공 기준값 (★결과 전에 고정 — `check_diag_data` 요구)

| 검사 | 성공했을 때 나와야 하는 값 |
|---|---|
| **왕복 무손실** | ★**불일치 0** — 패킹→언패킹이 **비트 동일**이어야 한다 |
| **codebook/tail** | 32개 코드 전수 + 1·2·7·8·9·17 group 경계의 왕복·바이트 수가 정확해야 한다 |
| **bpw** | ★**정확히 1.250** (5비트 / 4가중치). 이론 하한 `log2(4)+3 = 5.000비트` 와 **같다** |
| LUT 대비 | ★**1.600 → 1.250 = −21.9%** |
| 🚫3:4 가 아닌 입력 | ★**`ValueError`** — 조용히 근사하면 함정 1 의 재발이다 |

## 🚫이 도구가 **하지 않는** 것

- **속도를 안 잰다.** 언패킹해서 곱하는 참조 경로다. ★상주가 목적이다.
- **품질을 안 잰다.** 3:4 의 대가는 결과 008 이 이미 쟀고 **재학습이 필요하다**.
- ⚠️**모델을 안 만든다** — 합성 텐서로 포맷만 산다.

사용:  python scripts/diag_sparse34_pack.py [--models d12_cla2_r20 d16_cla2_r20]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tinylm                                   # noqa: E402  ★R40

_ = tinylm

# ★상주 회계 정본(기준표 B.14·B.17): 9.0 + 1.21·L + 0.75·(방문/cla_group) MiB
#
# 🚫★**2026-09-06 정정 — `1.21·L` 을 삼진 항으로 쓰면 절감이 4.8% 커진다.**
#   그 계수에는 **삼진이 아닌 항이 층당 약 0.057 MiB** 섞여 있다(norm·bias·cla 사영).
#   3:4 는 **삼진만** 건드리므로 비율을 곱할 대상은 `1.21·L` 이 아니라 **유니크 삼진 실측**이다.
#   실측 유니크 삼진(기준표 B.18.5 · 결과 008 §6.3)으로 직접 잡는다 —
#   층당으로 환산하면 13.836/12 = 18.447/16 = **1.153 MiB/층**으로 두 승자가 일치한다.
LUT_PER_LAYER_MIB = 1.21          # ⚠️상주식의 계수. 🚫삼진 항이 아니다
TERNARY_MIB_PER_LAYER = 1.153     # ★3:4 가 실제로 건드리는 항(LUT 1.600 bpw 기준)
BASE_MIB = 9.0
KV_PER_ENTRY_MIB = 0.75
WINNERS = {                       # 태그 -> (층, 방문, cla_group, 현재 상주 MiB)
    "d12_cla2_r20": (12, 20, 2, 30.7),
    "d16_cla2_r20": (16, 28, 2, 38.5),
}
# ★품질 대가.
#   `g4_s34`·`g8_s34` = 결과 008 실측이지만 **타잉 몸통 + KD** 조건이다.
#   ★`dense` = 2026-09-06 P016 단계3 실측(`d12_cla2_r20` 3.5571875 -> 3.59921875).
#   🚫**그 런은 깨진 패킹 포맷과 무관하다**(학습 경로의 `--sparse34` 는 0 강제일 뿐
#   패킹을 안 탄다) — 그래도 **판정은 재확인 대기**다: 사전등록 문턱이 절감 3.18 을
#   전제로 세워졌는데 절감이 3.027 로 줄었으므로 문턱 자체가 바뀐다(P016 단계4b).
S34_COST = {"g4_s34": 0.0364, "g8_s34": 0.0606, "dense": 0.04203}
# ★레버 가격선(결과 071 §4 · B.17.4) — 이 선보다 비싸면 지배당한다
LINE_NATS_PER_MIB = (0.00447, 0.00531)      # cla2e ~ 깊이 12->16


def _quantize_34(w, group):
    """latent weight -> **삼진 부호 패턴**(-1/0/+1). `--ckpt` 실측 전용.

    ⚠️★`ternary.py:_TernarySTE.forward` 의 `sparse34` 분기와 **같은 식**이다.
    복제한 이유는 `diag_sparse34.py:masks_for` 와 같다 — 학습 경로는 `sign*mask*alpha`
    (실수값)를 내는데 패킹이 받아야 하는 것은 **부호 패턴**이라 alpha 를 빼야 한다.
    🚫**식이 어긋나면 이 실측이 무의미하므로 `ternary.py` 를 고치면 여기도 고친다.**
    (alpha 는 1.25 bpw 회계에 안 들어간다 — 코드공간만 센다. 도구 머리말 참조)
    """
    import torch
    O, I = w.shape
    G = I // group
    wg = w.reshape(O, G, group)
    b = wg.abs().reshape(O, G, group // 4, 4)
    keep = torch.ones_like(b)
    keep.scatter_(3, b.argmin(dim=3, keepdim=True), 0.0)
    mask = keep.reshape(O, G, group)
    return (torch.sign(wg) * mask).reshape(O, I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1_000_000, help="왕복 시험 가중치 수")
    # ★★2026-09-06 신설(사용자 지시 4) — **이 도구는 합성 텐서만 봐 왔다.**
    #   그래서 §4 의 절감은 실측이 아니라 `층당 MiB x 층수 x (1.25/1.60)` 산수였고,
    #   그 계수가 틀려 3주 동안 4.8% 큰 수를 인쇄했다(3.18 vs 정본 3.027).
    #   ★진짜 체크포인트의 3:4 텐서를 실제로 패킹하면 **바이트를 세면 된다.**
    #   🚫`--ckpt` 없이 돌리면 종전과 **완전히 같다**(기본 off = 비트 동일, R-신규플래그).
    ap.add_argument("--ckpt", default=None,
                    help="실제 체크포인트 태그(예: d12_cla2_r20_s34). 주면 [6] 실측 절이 붙는다")
    ap.add_argument("--preset", default="m100s8", help="--ckpt 와 함께 쓰는 프리셋")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--arch", default="dense", choices=["dense", "tied"])
    a = ap.parse_args()

    import torch                                # 여기서만
    from tinylm.model.lut import (pack_sparse34, unpack_sparse34, sparse34_bytes,
                                  sparse34_vs_lut, is_sparse34, SPARSE34_BPW)

    print("=" * 96)
    print("  3:4 준정형 패킹 — 왕복 무손실 · bpw · 상주 이득 (학습 0 · GPU 0)")
    print("=" * 96)
    print(f"  ★성공 기준: 왕복 불일치 **0** · bpw **정확히 1.250** · "
          f"3:4 아닌 입력은 **ValueError**")

    fails = 0

    # ── 1. 왕복 무손실 ──────────────────────────────────────────────────────
    g = torch.Generator().manual_seed(99)
    n = (a.n // 4) * 4
    zero_pos = torch.randint(0, 4, (n // 4,), generator=g)
    signs = torch.randint(0, 2, (n // 4, 4), generator=g) * 2 - 1
    t = signs.to(torch.float32)
    t.scatter_(1, zero_pos.unsqueeze(1), 0.0)
    t = t.reshape(-1)
    assert is_sparse34(t.reshape(1, -1)), "합성 텐서가 3:4 가 아니다 — 시험 자체가 틀렸다"

    packed, n_orig = pack_sparse34(t.reshape(1, -1))
    back = unpack_sparse34(packed, n_orig)
    n_bad = int((back != t).sum())
    print(f"{chr(10)}  [1] 왕복 — 가중치 {n:,}개 · 불일치 **{n_bad}**"
          + ("  ✅" if n_bad == 0 else "  🚫**실패**"))
    if n_bad:
        fails += 1
        idx = (back != t).nonzero()[:5].reshape(-1).tolist()
        print(f"      처음 5곳 {idx}: 원본 {t[idx].tolist()} vs 복원 {back[idx].tolist()}")

    # ── 1b. 32-state codebook + 5-byte chunk tail 경계 ───────────────────────────
    # 기본 n=1,000,000은 group 수가 8의 배수라 끝 부분 잘라내기 버그를 놓칠 수 있다.
    edge_groups = (1, 2, 7, 8, 9, 17, 32)
    edge_errors = []
    for groups in edge_groups:
        codes = torch.arange(groups, dtype=torch.int64) % 32
        zero_pos_edge = codes // 8
        sb_edge = codes % 8
        signs_edge = torch.stack([
            (sb_edge // 4) % 2,
            (sb_edge // 2) % 2,
            sb_edge % 2,
        ], dim=1)
        vals_edge = (signs_edge * 2 - 1).to(torch.float32)
        original_edge = torch.zeros(groups, 4, dtype=torch.float32)
        keep_edge = torch.ones(groups, 4, dtype=torch.bool)
        keep_edge.scatter_(1, zero_pos_edge.unsqueeze(1), False)
        original_edge[keep_edge] = vals_edge.reshape(-1)

        packed_edge, n_edge = pack_sparse34(original_edge)
        restored_edge = unpack_sparse34(packed_edge, n_edge)
        expected_bytes = sparse34_bytes(n_edge)
        if (not torch.equal(restored_edge, original_edge.reshape(-1))
                or packed_edge.numel() != expected_bytes):
            edge_errors.append(
                f"groups={groups}: bad="
                f"{int((restored_edge != original_edge.reshape(-1)).sum())}, "
                f"bytes={packed_edge.numel()}/{expected_bytes}")
    edge_ok = not edge_errors
    print("  [1b] codebook/tail — groups "
          + ",".join(str(x) for x in edge_groups)
          + ("  ✅" if edge_ok else "  🚫**실패**"))
    if edge_errors:
        fails += 1
        for error in edge_errors:
            print(f"      {error}")

    # ── 2. bpw ─────────────────────────────────────────────────────────────
    b34 = packed.numel()
    b34_formula = sparse34_bytes(n)
    bpw = b34 * 8 / n
    ok = abs(bpw - 1.25) < 1e-9 and b34 == b34_formula
    print(f"  [2] bpw — {b34:,} 바이트 / {n:,} 가중치 = **{bpw:.6f}** "
          f"(기준 {SPARSE34_BPW:.3f}, 회계 {b34_formula:,} 바이트)"
          + ("  ✅" if ok else "  🚫**실패**"))
    fails += 0 if ok else 1

    # ── 3. 3:4 가 아닌 입력을 거절하는가 ────────────────────────────────────
    dense = torch.ones(1, 8)
    try:
        pack_sparse34(dense)
        print("  [3] 거절 — 🚫**실패**: 3:4 가 아닌 텐서를 받아들였다")
        fails += 1
    except ValueError:
        print("  [3] 거절 — ✅ 3:4 가 아닌 입력에 `ValueError`")

    # ── 4. ★상주 이득 — 승자 둘에 대해 ─────────────────────────────────────
    print(f"{chr(10)}  [4] ★상주 이득 — 승자 둘 (LUT 1.600 -> 3:4 1.250)")
    print(f"      {'모델':<16}{'층':>4}{'현재':>9}{'삼진항':>9}{'3:4':>9}"
          f"{'절감':>9}{'새 상주':>10}")
    print("      " + "-" * 68)
    rows = []
    for tag, (L, visits, cg, cur) in WINNERS.items():
        tern = TERNARY_MIB_PER_LAYER * L      # 🚫LUT_PER_LAYER_MIB 가 아니다 — 위 정정 참조
        new_tern = tern * (1.25 / 1.60)
        saved = tern - new_tern
        rows.append((tag, saved, cur, cur - saved))
        print(f"      {tag:<16}{L:>4}{cur:>9.1f}{tern:>9.2f}{new_tern:>9.2f}"
              f"{saved:>9.2f}{cur - saved:>10.1f}")

    # ── 5. ★★판정 — 레버 가격선 위인가 아래인가 ────────────────────────────
    print(f"{chr(10)}  [5] ★★교환비 — **파는 쪽**이다. 우리 선({LINE_NATS_PER_MIB[0]:.5f}"
          f"~{LINE_NATS_PER_MIB[1]:.5f} nats/MiB)과 견준다")
    print(f"      {'모델':<16}{'절감 MiB':>10}{'대가(g4)':>11}{'nats/MiB':>11}"
          f"{'선 대비':>9}  판정")
    print("      " + "-" * 74)
    worst = 0.0
    for tag, saved, cur, new in rows:
        cost = S34_COST["dense"]              # ★승자는 dense 몸통이다
        price = cost / saved
        ratio = price / LINE_NATS_PER_MIB[1]
        worst = max(worst, ratio)
        v = "✅선 안" if ratio <= 1.0 else "🚫**지배당함**"
        print(f"      {tag:<16}{saved:>10.2f}{cost:>11.4f}{price:>11.5f}"
              f"{ratio:>8.2f}x  {v}")
    print()
    print("      ★읽는 법: 같은 MiB 를 **깊이로 사면** 0.00531 nats 를 번다. 3:4 로 팔아서")
    print("      얻은 MiB 를 깊이에 다시 쓰면 얼마가 남는지가 이 비율이다.")
    print(f"      ★대가 {S34_COST['dense']:+.5f} 는 **dense 몸통 실측**이다"
          f"(P016 단계3, 2026-09-06). 타잉+KD 는 {S34_COST['g4_s34']:+.4f} 였다.")
    print("      ⚠️★그 런은 **깨진 패킹 포맷과 무관**하다 — 학습 경로의 `--sparse34` 는")
    print("      4블록마다 0 을 하나 강제할 뿐이고 `pack_sparse34` 를 안 탄다.")
    print("      🚫**그래도 판정은 다시 해야 한다**: 사전등록 문턱이 절감 3.18 을 전제로")
    print("      세워졌는데 실제 절감이 3.027 이라 문턱이 3.18/3.027 배로 내려간다(P016 단계4b).")

    # ── 6. ★★실측 — 진짜 체크포인트를 실제로 패킹한다 (--ckpt 있을 때만) ──────
    if a.ckpt:
        print(f"{chr(10)}  [6] ★★실측 — 체크포인트 `{a.ckpt}` 의 3:4 텐서를 진짜로 패킹한다")
        from tinylm import paths
        from tinylm.infer.generate import load_model
        from tinylm.model.ternary import TLinear
        ck = paths.RUNS / "ckpt" / f"{a.preset}_{a.data}_{a.tokens}_{a.ckpt}.pt"
        if not ck.exists():
            print(f"      🚫 체크포인트가 없다: {ck.name}")
            fails += 1
        else:
            model, cfg, _ = load_model(arch=a.arch, ckpt_path=str(ck), device="cpu")
            if not bool(getattr(cfg, "sparse34", False)):
                print("      🚫 이 체크포인트는 `sparse34=False` 다 — 3:4 가 아니다.")
                fails += 1
            else:
                tl = [m for m in model.modules() if isinstance(m, TLinear)]
                n_w = n_b = n_skip = 0
                bad_rt = 0
                with torch.no_grad():
                    for m in tl:
                        # 학습 경로의 3:4 는 **양자화 뒤**에 성립한다. latent weight 는
                        # 3:4 가 아니므로 같은 식으로 삼진화한 뒤 검사한다.
                        q = _quantize_34(m.weight.detach().float(), cfg.micro_group)
                        if not is_sparse34(q.reshape(1, -1)):
                            n_skip += 1
                            continue
                        pk, n0 = pack_sparse34(q.reshape(1, -1))
                        if not torch.equal(unpack_sparse34(pk, n0), q.reshape(-1)):
                            bad_rt += 1
                        n_w += q.numel()
                        n_b += pk.numel()
                real_bpw = (n_b * 8 / n_w) if n_w else float("nan")
                real_mib = n_b / (1024 ** 2)
                lut_mib = n_w * 1.600 / 8 / (1024 ** 2)
                print(f"      TLinear {len(tl)}개 · 3:4 아님 건너뜀 {n_skip}개 · "
                      f"왕복 실패 {bad_rt}개")
                print(f"      삼진 가중치 {n_w:,}개 -> 패킹 {n_b:,} 바이트 = "
                      f"**{real_bpw:.6f} bpw**")
                print(f"      ★LUT 1.600 이면 {lut_mib:.3f} MiB · 3:4 는 "
                      f"**{real_mib:.3f} MiB** · 절감 **{lut_mib - real_mib:.3f} MiB**")
                print(f"      ⚠️추정치({TERNARY_MIB_PER_LAYER:.3f} MiB/층 x 층수 x 1.25/1.60)와 "
                      f"대조하세요 — 이 줄이 **실측**이고 그쪽이 산수다.")
                if bad_rt or n_skip == len(tl):
                    fails += 1

    print()
    if fails:
        print(f"  🚫★**{fails}건 실패** — 포맷이 아직 못 쓴다.")
        return 1
    print("  ✅ 포맷 검사 4종 통과. 상주 이득은 위 표가 정본이다.")
    print(f"  ★판정 요약: 최악 비율 **{worst:.2f}x** — "
          + ("선 안이라 채택 후보" if worst <= 1.0 else
             "🚫**선 밖이라 지배당한다.** 예산 천장에 걸렸을 때만 쓴다"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
