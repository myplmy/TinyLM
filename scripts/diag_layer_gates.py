#!/usr/bin/env python3
"""P049 사후 진단 — **복제된 층이 학습으로 깨어났는가.** 학습 0 · GPU 0 · 수 초.

## 왜 필요한가

결과 041 §13.4 가 *"단계1 이 **반드시** 기록해야 하는 것"* 으로 못 박은 항목인데
**배치에 반영되지 않아 미측정으로 끝났다**(결과 041 §14.5, 함정 13 계열).

`--depth-init gate_scale` 은 교사 층을 복제할 때 그 층의 residual gate 를
**복제 횟수로 나눈다**. 36층 학생에서 32개 중간층이 교사 16층을 2회씩 쓰므로
**복제된 층은 gate 를 절반으로 들고 출발**한다.

> ★**질문**: 학습이 끝난 뒤 그 gate 가 **0 에서 멀어졌는가**.
> 안 깨어났으면 **36층은 실질 20층**이고 P049 는 자기 질문에 답하지 못한 것이다.
> 답에 따라 *"깊이 축이 죽었다"* 와 *"우리 이식 방식이 깊이를 못 살렸다"* 가 갈린다.

## 무엇을 보는가

`Layer.forward` 가 `x = x + gates[0]*attn(...)` , `x = x + gates[1]*mlp(...)` 이므로
**gate 가 그 층의 잔차 기여 크기 그 자체**다. 파라미터만 읽으면 된다 —
**모델을 짓지 않고 `state_dict` 만 연다.**

| 지표 | 뜻 |
|---|---|
| `g_final` | 학습 끝난 gate (attn, mlp) |
| `g_init` | 이식 직후 값 = 교사 gate ÷ 복제횟수(`gate_scale` 일 때) |
| ★`move` | `(|g_final| − |g_init|) / |g_init|` — **초기값 대비 상대 이동** |

★**판정은 "복제층 move" 와 "비복제층 move" 의 비교**로 한다. 절대값이 아니다 —
복제층은 절반에서 출발하므로 절대값만 보면 항상 작아 보인다.

## 성공 기준값 (참고값 — 결과 전에 적는다)

| 상태 | 무엇이 보이나 |
|---|---|
| ✅ **깨어났다** | 복제층 `move` 가 비복제층과 **같은 자릿수**(비 0.5~2.0) |
| ⚠️ **부분** | 비 0.2~0.5 — 움직이긴 했으나 덜 움직였다 |
| 🚫 **안 깨어났다** | 비 < 0.2, 또는 복제층 `|g_final|` 이 비복제층의 **1/4 미만** |

사용:
    python scripts/diag_layer_gates.py --tag mC_d36 --preset m100R1d
    python scripts/diag_layer_gates.py --tag mC_wsd --preset m100R1c   (대조군: 복제 없음)
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch                                                     # noqa: E402

from tinylm import paths                                         # noqa: E402
from tinylm.config import TMTConfig                              # noqa: E402


def _hdr(s):
    print("\n" + "=" * 78 + f"\n  {s}\n" + "=" * 78)


def _cfg_from(blob):
    """저장된 `cfg.__dict__` 에서 **현재 데이터클래스에 있는 필드만** 뽑는다.

    ⚠️ 옛 체크포인트에는 지금 없는 키가, 새 체크포인트에는 옛 코드가 모르는 키가 있을 수 있다.
    `TMTConfig(**d)` 를 그대로 부르면 그때 죽는다 — 이 도구는 **읽기 전용**이므로 죽을 이유가 없다.
    """
    known = {f.name for f in dataclasses.fields(TMTConfig)}
    d = {k: v for k, v in (blob.get("cfg") or {}).items() if k in known}
    dropped = sorted(set((blob.get("cfg") or {})) - known)
    return TMTConfig(**d), dropped


def _gates(sd):
    """`state_dict` 에서 층별 gate 를 뽑는다. `_orig_mod.` 접두(compile)도 받는다."""
    out = {}
    for k, v in sd.items():
        kk = k.replace("_orig_mod.", "")
        if kk.startswith("layers.") and kk.endswith(".gates"):
            try:
                i = int(kk.split(".")[1])
            except ValueError:
                continue
            out[i] = [float(x) for x in v.detach().float().flatten().tolist()]
    return out


def main():
    ap = argparse.ArgumentParser(description="복제층 gate 가 깨어났는가 (학습 0 · GPU 0)")
    ap.add_argument("--tag", required=True, help="학생 태그. 예: mC_d36")
    ap.add_argument("--preset", default="m100R1d")
    ap.add_argument("--teacher-preset", default="m100")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--ckpt", default=None, help="직접 경로를 줄 때")
    a = ap.parse_args()

    ck = a.ckpt or str(paths.resolve_ckpt(a.preset, a.data, a.tokens, a.tag))
    if not Path(ck).exists():
        print(f"  🚫 체크포인트가 없다: {ck}")
        return 2
    st = torch.load(ck, map_location="cpu", weights_only=False)
    sc, dropped = _cfg_from(st)
    gs = _gates(st.get("model", {}))
    if not gs:
        print("  🚫 `layers.N.gates` 키를 하나도 못 찾았다 — 체크포인트 구조가 다르다")
        return 2

    _hdr("대상")
    print(f"  학생 {Path(ck).name}")
    print(f"  구조 {sc.n_prelude}+{sc.n_middle}+{sc.n_coda} = {sc.n_layers}층, "
          f"g={sc.mlp_group}, step={st.get('step')}")
    if dropped:
        print(f"  ⚠️ 이 코드가 모르는 cfg 키 {len(dropped)}개 무시: {dropped[:6]}")
    print(f"  gate 를 읽은 층 {len(gs)}개")

    # ── 교사와 대응표 ────────────────────────────────────────────────────────
    lmap = lrep = None
    tg = {}
    depth_init = str(st.get("cfg", {}).get("depth_init", "") or "")
    tck = paths.resolve_ckpt(a.teacher_preset, a.data, a.tokens, "dense")
    if Path(tck).exists():
        tst = torch.load(str(tck), map_location="cpu", weights_only=False)
        tc, _ = _cfg_from(tst)
        tg = _gates(tst.get("model", {}))
        try:
            from tinylm.train.init_utils import _depth_map     # ★대응표는 단일 소스다(함정 18)
            lmap, lrep = _depth_map(sc, tc)
        except Exception as e:                                  # noqa: BLE001
            print(f"  ⚠️ 대응표를 못 만들었다({type(e).__name__}) — 초기값 비교는 생략한다")
        print(f"  교사 {Path(tck).name}  {tc.n_layers}층   depth_init={depth_init or '(미기록)'}")
    else:
        print(f"  ⚠️ 교사 체크포인트가 없다({Path(tck).name}) — **초기값 비교 생략**, "
              f"최종 gate 만 본다")

    # ── 층별 표 ──────────────────────────────────────────────────────────────
    _hdr("층별 gate  (gates[0]=어텐션 잔차, gates[1]=MLP 잔차)")
    print(f"  {'층':>3} {'복제':>4} {'g_attn':>9} {'g_mlp':>9} "
          f"{'init_attn':>10} {'init_mlp':>9} {'move_attn':>10} {'move_mlp':>9}")
    print("  " + "-" * 72)

    rows = []
    for i in sorted(gs):
        g = gs[i]
        rep = int(lrep[i]) if lrep is not None and i < len(lrep) else 1
        ini = None
        if lmap is not None and i < len(lmap) and lmap[i] in tg:
            base = tg[lmap[i]]
            div = float(rep) if depth_init == "gate_scale" and rep > 1 else 1.0
            ini = [b / div for b in base]
        mv = [None, None]
        if ini:
            for j in (0, 1):
                mv[j] = (abs(g[j]) - abs(ini[j])) / max(abs(ini[j]), 1e-12)
        rows.append((i, rep, g, ini, mv))
        f = lambda x, w=9: (f"{x:>{w}.5f}" if x is not None else " " * (w - 1) + "-")
        print(f"  {i:>3} {rep:>4} {f(g[0])} {f(g[1])} "
              f"{f(ini[0] if ini else None, 10)} {f(ini[1] if ini else None)} "
              f"{f(mv[0], 10)} {f(mv[1])}")

    # ── 판정 ─────────────────────────────────────────────────────────────────
    _hdr("판정 — 복제층이 깨어났는가")
    dup = [r for r in rows if r[1] > 1]
    org = [r for r in rows if r[1] == 1]
    if not dup:
        print("  ⏸ **복제된 층이 없다**(모든 lrep = 1). 이 진단의 대상이 아니다 — "
              "대조군으로는 유효하다(비복제 모델의 gate 분포를 본다).")
    mean = lambda xs: (sum(xs) / len(xs)) if xs else float("nan")
    for j, nm in ((0, "어텐션"), (1, "MLP")):
        ad = mean([abs(r[2][j]) for r in dup])
        ao = mean([abs(r[2][j]) for r in org])
        print(f"\n  [{nm}]  |g| 평균   복제층 {ad:.5f}   비복제층 {ao:.5f}   "
              f"비 {ad / ao if ao else float('nan'):.3f}")
        md = [r[4][j] for r in dup if r[4][j] is not None]
        mo = [r[4][j] for r in org if r[4][j] is not None]
        if md and mo:
            rd, ro = mean(md), mean(mo)
            ratio = rd / ro if ro else float("nan")
            print(f"           move 평균  복제층 {rd:+.4f}   비복제층 {ro:+.4f}   "
                  f"비 {ratio:.3f}")
            if ratio >= 0.5:
                print("           ✅ **깨어났다** — 복제층이 비복제층과 같은 자릿수로 움직였다")
            elif ratio >= 0.2:
                print("           ⚠️ **부분** — 움직이긴 했으나 덜 움직였다")
            else:
                print("           🚫 **안 깨어났다** — 복제층이 초기값 근처에 머물렀다")
        else:
            print("           (초기값을 못 구해 move 판정 생략 — 교사 체크포인트 필요)")

    print("\n  ⚠️ **이 진단은 gate 크기만 본다.** gate 가 커도 그 층이 유용한 것을 계산한다는 "
          "증명은 아니다 — 그건 층 제거 ablation 이 답한다(더 비싸다).")
    print("  ⚠️ 참고: 이식 직후 값은 `gate_scale` 이면 교사 gate ÷ 복제횟수, "
          "`prop` 이면 교사 gate 그대로, `identity` 면 복제층이 정확히 0 이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
