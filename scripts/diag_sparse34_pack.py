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
| **codebook/tail** | 32개 코드 전수 + 1·2·7·8·9·17 group 경계의 flat/행별 왕복·바이트 수가 정확해야 한다 |
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
#   그중 `1.21·L` 이 **LUT 삼진 항**이다. 3:4 는 그 항만 건드린다.
LUT_PER_LAYER_MIB = 1.21
BASE_MIB = 9.0
KV_PER_ENTRY_MIB = 0.75
WINNERS = {                       # 태그 -> (층, 방문, cla_group, 현재 상주 MiB)
    "d12_cla2_r20": (12, 20, 2, 30.7),
    "d16_cla2_r20": (16, 28, 2, 38.5),
}
# ★품질 대가 — 결과 008 실측. ⚠️**타잉 몸통 + KD 조건**이고 dense 에서는 미측정이다.
S34_COST = {"g4_s34": 0.0364, "g8_s34": 0.0606}
# ★레버 가격선(결과 071 §4 · B.17.4) — 이 선보다 비싸면 지배당한다
LINE_NATS_PER_MIB = (0.00447, 0.00531)      # cla2e ~ 깊이 12->16


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1_000_000, help="왕복 시험 가중치 수")
    a = ap.parse_args()

    import torch                                # 여기서만
    from tinylm.model.lut import (pack_sparse34, unpack_sparse34, pack_sparse34_rows,
                                  unpack_sparse34_rows, unpack_sparse34_codes, sparse34_bytes,
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

    # CPU LUT는 출력행을 O(1)로 찾기 위해 **행마다** byte-align한다. flat stream 통과로는
    # 행 경계/tail 버그를 못 잡으므로 같은 7개 경계를 3행으로 별도 검증한다.
    row_errors = []
    for groups in edge_groups:
        expected_codes = torch.arange(groups, dtype=torch.int64) % 32
        zero_pos_row = expected_codes // 8
        sb_row = expected_codes % 8
        signs_row = torch.stack([
            (sb_row // 4) % 2,
            (sb_row // 2) % 2,
            sb_row % 2,
        ], dim=1)
        vals_row = (signs_row * 2 - 1).to(torch.int8)
        one_row = torch.zeros(groups, 4, dtype=torch.int8)
        keep_row = torch.ones(groups, 4, dtype=torch.bool)
        keep_row.scatter_(1, zero_pos_row.unsqueeze(1), False)
        one_row[keep_row] = vals_row.reshape(-1)
        rows = torch.stack((one_row.reshape(-1),
                            one_row.flip(0).reshape(-1),
                            one_row.roll(1, 0).reshape(-1)))
        packed_rows, n_row = pack_sparse34_rows(rows)
        restored_rows = unpack_sparse34_rows(packed_rows, n_row, dtype=torch.int8)
        decoded_rows = unpack_sparse34_codes(packed_rows, groups)
        expected_row_bytes = (groups * 5 + 7) // 8
        if (not torch.equal(restored_rows, rows)
                or packed_rows.shape != (3, expected_row_bytes)
                or not torch.equal(decoded_rows[0], expected_codes)):
            row_errors.append(
                f"groups={groups}: bad={int((restored_rows != rows).sum())}, "
                f"shape={tuple(packed_rows.shape)}/(3,{expected_row_bytes})")
    print("  [1c] row-stream/tail — 3 rows x groups "
          + ",".join(str(x) for x in edge_groups)
          + ("  ✅" if not row_errors else "  🚫**실패**"))
    if row_errors:
        fails += 1
        for error in row_errors:
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
        tern = LUT_PER_LAYER_MIB * L
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
        cost = S34_COST["g4_s34"]
        price = cost / saved
        ratio = price / LINE_NATS_PER_MIB[1]
        worst = max(worst, ratio)
        v = "✅선 안" if ratio <= 1.0 else "🚫**지배당함**"
        print(f"      {tag:<16}{saved:>10.2f}{cost:>11.4f}{price:>11.5f}"
              f"{ratio:>8.2f}x  {v}")
    print()
    print("      ★읽는 법: 같은 MiB 를 **깊이로 사면** 0.00531 nats 를 번다. 3:4 로 팔아서")
    print("      얻은 MiB 를 깊이에 다시 쓰면 얼마가 남는지가 이 비율이다.")
    print(f"      ⚠️대가 {S34_COST['g4_s34']:+.4f} 는 **결과 008 의 타잉 몸통 + KD** 값이다 —")
    print("      dense 몸통에서는 **미측정**이고, 재면 달라질 수 있다.")

    print()
    if fails:
        print(f"  🚫★**{fails}건 실패** — 포맷이 아직 못 쓴다.")
        return 1
    print("  ✅ flat/행별 포맷 검사 5종 통과. 상주 이득은 위 표가 정본이다.")
    print(f"  ★판정 요약: 최악 비율 **{worst:.2f}x** — "
          + ("선 안이라 채택 후보" if worst <= 1.0 else
             "🚫**선 밖이라 지배당한다.** 예산 천장에 걸렸을 때만 쓴다"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
