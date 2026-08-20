#!/usr/bin/env python3
"""P049 단계2 — **복제층 어텐션은 첫 통과와 같은 것을 계산하는가.** 학습 0 · 수 분.

## 왜 이 도구가 생겼나 (`docs/20260806_...` §7.4)

사용자 질문: *"복제층의 두 번째 통과에서 어텐션이 같은 위치 패턴을 다시 계산한다면
묶음계산이 가능한가?"*

우리는 §7.1 에서 **그 문장이 두 명제를 가리킨다**고 답했다:

    ① 출력이 같다   -> 두 번째 통과를 **아예 안 돌려도 된다**(묶음보다 강하다)
    ② 기여가 작다   -> 게이트가 꺼졌다는 뜻일 뿐, 출력은 다를 수 있다

★**결과 041 §15 가 잰 것은 ②** 다(복제층 `|g_attn|` 이 비복제층의 0.279배).
🚫**①은 한 번도 안 쟀다.** 이 도구가 ①을 잰다.

## 두 측정

    A  코사인 유사도   같은 교사층에서 복제된 층 쌍의 **어텐션 출력**이 얼마나 같은가
    B  잔차 기여도     `‖g0·attn_out‖ / ‖x_in‖` — **스트림을 얼마나 바꾸는가**

★**B 가 더 직접적이다.** 기여가 1% 면 **유사도와 무관하게** 생략이 거의 공짜다.
★**A 가 더 강하다.** 0.95 를 넘으면 *"첫 통과 결과를 재사용하라"* 가 성립한다.

## ★★대조군 없이는 A 를 읽을 수 없다

어텐션 출력끼리는 **원래 비슷하다**(좁은 원뿔에 산다). 그래서 세 무리를 함께 잰다:

    (a) 복제 쌍          같은 교사층 → 같은 어텐션 모듈
    (b) 같은 모듈·비복제  attn_group 으로 묶였지만 교사층이 다른 쌍
    (c) 다른 모듈        무관한 쌍 = **바닥 수준**

**(a) 가 (b)·(c) 보다 뚜렷하게 높아야** 의미가 있다. 절대값만 보면 안 된다.

## ★성공 기준값 — 결과 전에 못 박는다 (함정 34)

    A: (a) 평균 cos ≥ 0.95 **이고** (a) − (c) ≥ 0.20   -> ★"재사용 가능" 성립
    A: (a) − (c) < 0.05                                -> 🚫 ①기각. 묶음·재사용 불가
    B: 복제층 기여도가 비복제층의 1/4 미만              -> ★"생략" 후보(②의 정량화)

⚠️ **이 도구는 "생략해도 되는가" 를 답하지 않는다.** 생략의 품질 대가는
**실제로 빼고 full-val 을 재야** 나온다(§후속 B).

사용법
    python scripts/diag_repeat_attn_sim.py --tag mC_d36_ag4 --preset m100R1c
    python scripts/diag_repeat_attn_sim.py --tag mC_d36 --preset m100R1c
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GATE_COS = 0.95          # (a) 평균 코사인이 이보다 크고
GATE_MARGIN = 0.20       # (a) − (c) 가 이보다 크면 "재사용 가능"
GATE_REJECT = 0.05       # (a) − (c) 가 이보다 작으면 ① 기각
GATE_CONTRIB = 0.25      # 복제층 기여도가 비복제층의 이 배수 미만이면 "생략 후보"


def banner(s, ch="="):
    print("\n" + ch * 96)
    print(f"  {s}")
    print(ch * 96)


def main():
    ap = argparse.ArgumentParser(description="복제층 어텐션 출력 유사도·기여도 (학습 0)")
    ap.add_argument("--tag", default="mC_d36_ag4")
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--teacher-preset", default="m100")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--crops", type=int, default=8)
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()

    import numpy as np
    import torch
    import torch.nn.functional as F
    from tinylm import paths
    from tinylm.data import prepare
    from tinylm.infer.generate import load_model

    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    banner("P049 단계2 — 복제층 어텐션은 같은 것을 계산하는가 (학습 0)", "#")
    print(f"  tag={a.tag}  preset={a.preset}  device={dev}  crops={a.crops} seq={a.seq}")
    print("\n  ★성공 기준값 — 결과 전에 못 박는다")
    print(f"    · (a)평균 cos ≥ {GATE_COS} **이고** (a)−(c) ≥ {GATE_MARGIN} → ★재사용 가능")
    print(f"    · (a)−(c) < {GATE_REJECT}                          → 🚫 ①기각")
    print(f"    · 복제층 기여도 < 비복제층 × {GATE_CONTRIB}          → ★생략 후보")
    print("  ⚠️ **대조군 (c) 없이 (a) 절대값만 읽지 않는다.** 어텐션 출력은 원래 비슷하다.")

    ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, a.tag)
    if not ck.exists():
        print(f"\n  🚫 체크포인트가 없다: {ck.name}")
        return 2
    model, cfg, _ = load_model(arch="tied", ckpt_path=str(ck), device=dev)
    n = cfg.n_layers
    print(f"\n  로드 {ck.name}  {cfg.n_prelude}+{cfg.n_middle}+{cfg.n_coda} = {n}층 · "
          f"attn_group={getattr(cfg, 'attn_group', 1)}")

    # ── 복제 대응표 (단일 소스: init_utils._depth_map, 함정 18) ──────────────
    lmap = None
    tck = paths.resolve_ckpt(a.teacher_preset, a.data, a.tokens, "dense")
    if tck.exists():
        try:
            from tinylm.config import TMTConfig
            from tinylm.train.init_utils import _depth_map
            tst = torch.load(str(tck), map_location="cpu", weights_only=False)
            tc = TMTConfig(**{k: v for k, v in tst["cfg"].items()
                              if k in TMTConfig.__dataclass_fields__})
            lmap, _lrep = _depth_map(cfg, tc)
            print(f"  교사 {tck.name} {tc.n_layers}층 → 대응표 확보")
        except Exception as e:                                  # noqa: BLE001
            print(f"  ⚠️ 대응표를 못 만들었다({type(e).__name__}) — **(a)/(b) 를 못 가른다**")
    if lmap is None:
        print("  🚫 교사 대응표가 없으면 '복제 쌍' 을 정의할 수 없다. 중단한다.")
        return 2

    # ── 층별 어텐션 모듈 id ─────────────────────────────────────────────────
    layers = list(model.layers)
    attn_id = [id(l.attn_mod) for l in layers]
    n_uniq = len(set(attn_id))
    print(f"  유니크 어텐션 모듈 {n_uniq}개 / {n}층  (평균 {n / n_uniq:.2f}층이 공유)")

    # ── 훅: 유니크 모듈마다 호출 순서대로 (입력, 출력) 저장 ────────────────
    store = {}                                        # id -> [출력 텐서, ...]
    handles = []
    seen = set()
    for l in layers:
        m = l.attn_mod
        if id(m) in seen:
            continue
        seen.add(id(m))
        store[id(m)] = []

        def hook(mod, inp, out, key=id(m)):
            store[key].append(out.detach().float())
            return None
        handles.append(m.register_forward_hook(hook))

    # 잔차 기여도용: 층 입력과 gates
    lay_in = []

    def lay_hook(mod, inp, out, idx=None):
        lay_in.append(inp[0].detach().float())
        return None
    for l in layers:
        handles.append(l.register_forward_hook(lay_hook))

    # ── 데이터: 실제 val 크롭 (난수 아님 — 계측 규약) ──────────────────────
    meta = prepare(a.data, int(float(a.tokens.rstrip("MmBb")) * 1e6))
    d = np.memmap(Path(meta["dir"]) / "val.bin", dtype=np.uint16, mode="r")
    arr = np.stack([d[i * a.seq:(i + 1) * a.seq] for i in range(a.crops)]).astype(np.int64)
    x = torch.from_numpy(arr).to(dev)
    print(f"  데이터: val.bin 앞 {a.crops}크롭 × {a.seq}토큰 (**실제 데이터**, 난수 아님)")

    model.eval()
    with torch.no_grad(), torch.autocast(dev, dtype=torch.bfloat16, enabled=(dev == "cuda")):
        model(x)
    for h in handles:
        h.remove()

    # ── 호출 순서 → 층 번호 매핑 ────────────────────────────────────────────
    order = {}                                        # id -> [층번호, ...] (실행 순)
    for i, mid in enumerate(attn_id):
        order.setdefault(mid, []).append(i)
    out_of = {}                                       # 층번호 -> 어텐션 출력
    for mid, layer_idxs in order.items():
        outs = store.get(mid, [])
        if len(outs) != len(layer_idxs):
            print(f"  ⚠️ 모듈 {mid}: 호출 {len(outs)}회 ≠ 사용 층 {len(layer_idxs)}개 — 건너뛴다")
            continue
        for li, o in zip(layer_idxs, outs):
            out_of[li] = o

    # ── A: 세 무리의 코사인 ─────────────────────────────────────────────────
    def cos(u, v):
        return float(F.cosine_similarity(u.reshape(-1), v.reshape(-1), dim=0))

    grp = {"a_복제쌍": [], "b_같은모듈_비복제": [], "c_다른모듈": []}
    for i in range(n):
        for j in range(i + 1, n):
            if i not in out_of or j not in out_of:
                continue
            same_mod = attn_id[i] == attn_id[j]
            same_src = lmap[i] == lmap[j]
            c = cos(out_of[i], out_of[j])
            if same_mod and same_src:
                grp["a_복제쌍"].append((i, j, c))
            elif same_mod:
                grp["b_같은모듈_비복제"].append((i, j, c))
            else:
                grp["c_다른모듈"].append((i, j, c))

    banner("A — 어텐션 출력 코사인 유사도 (세 무리)")
    means = {}
    print(f"  {'무리':<22}{'쌍 수':>7}{'평균 cos':>11}{'최소':>9}{'최대':>9}")
    print("  " + "-" * 60)
    for k, v in grp.items():
        if not v:
            print(f"  {k:<22}{0:>7}{'—':>11}")
            means[k] = None
            continue
        cs = [c for _, _, c in v]
        means[k] = statistics.fmean(cs)
        print(f"  {k:<22}{len(v):>7}{means[k]:>11.4f}{min(cs):>9.4f}{max(cs):>9.4f}")

    if grp["a_복제쌍"]:
        print("\n  복제 쌍 상위 8개 (층i, 층j, cos):")
        for i, j, c in sorted(grp["a_복제쌍"], key=lambda t: -t[2])[:8]:
            print(f"    ({i:>2},{j:>2})  {c:.4f}   교사층 {lmap[i]}")

    # ── B: 잔차 기여도 ──────────────────────────────────────────────────────
    banner("B — 잔차 기여도  ‖g0·attn_out‖ / ‖x_in‖")
    dup_flag = [sum(1 for k in range(n) if lmap[k] == lmap[i]) > 1 for i in range(n)]
    rows = []
    for i in range(n):
        if i not in out_of or i >= len(lay_in):
            continue
        g0 = float(layers[i].gates[0].detach())
        num = float((g0 * out_of[i]).norm())
        den = float(lay_in[i].norm()) or 1.0
        rows.append((i, dup_flag[i], g0, num / den))
    print(f"  {'층':>3}{'복제':>6}{'g0':>10}{'기여도':>11}")
    print("  " + "-" * 32)
    for i, dp, g0, r in rows:
        print(f"  {i:>3}{'Y' if dp else '·':>6}{g0:>10.5f}{r:>11.5f}")
    dv = [r for _, dp, _, r in rows if dp]
    nv = [r for _, dp, _, r in rows if not dp]
    md = statistics.fmean(dv) if dv else float("nan")
    mn = statistics.fmean(nv) if nv else float("nan")
    print(f"\n  복제층 평균 {md:.5f} ({len(dv)}층)  ·  비복제층 평균 {mn:.5f} ({len(nv)}층)")
    ratio = (md / mn) if (nv and mn) else float("nan")
    print(f"  ★비 = **{ratio:.3f}**")

    # ── 판정 ────────────────────────────────────────────────────────────────
    banner("판정 — 기준값 대비")
    ma, mc = means.get("a_복제쌍"), means.get("c_다른모듈")
    if ma is None or mc is None:
        print("  ⚠️ 무리가 비어 판정할 수 없다. (복제 쌍이 없는 모델이면 정상 — 대조군이다)")
    else:
        margin = ma - mc
        print(f"  (a) {ma:.4f}   (c) {mc:.4f}   **차 {margin:+.4f}**")
        if ma >= GATE_COS and margin >= GATE_MARGIN:
            print("  ★★**①성립** — 복제층 어텐션 출력이 사실상 같다. "
                  "**첫 통과 결과 재사용을 설계할 수 있다**")
        elif margin < GATE_REJECT:
            print(f"  🚫★**①기각** — 차 {margin:+.4f} < {GATE_REJECT}. "
                  f"**출력이 같지 않다. 묶음도 재사용도 불가**")
            print("     → 남는 것은 ②(생략)뿐이고, 그건 B 가 답한다")
        else:
            print(f"  ⚠️**판정 불가** — 기준 사이다. 표본(크롭 {a.crops})을 늘려 다시 본다")
    if dv and nv:
        if ratio < GATE_CONTRIB:
            print(f"  ★**②정량화** — 복제층 기여도가 비복제층의 {ratio:.3f}배 "
                  f"(< {GATE_CONTRIB}) → **생략 후보**")
        else:
            print(f"  🚫 복제층 기여도 비 {ratio:.3f} ≥ {GATE_CONTRIB} → **생략도 공짜가 아니다**")

    print("\n  ⚠️ **생략의 품질 대가는 여기서 안 나온다.** 실제로 빼고 full-val 을 재야 한다.")
    print("  ⚠️ bf16 autocast 아래에서 쟀다 — 코사인 4자리는 **자릿수 관찰**이지 정밀값이 아니다.")
    print("  ⚠️ 크롭 앞부분만 썼다(결정적). **문서 분포가 다르면 값이 달라질 수 있다**(P037 계열).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
