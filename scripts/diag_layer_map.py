#!/usr/bin/env python3
"""★★P072 — **레이어 상호작용 지도.** 학습 0. 체크포인트만 읽는다.

## 무엇을 재나 (계획 P072 §3)

| # | 지도 | 무엇 |
|---|---|---|
| ★**U1** | 층↔층 **출력 델타 유사도** `cos(d_i, d_j)` | 어느 층이 어느 층과 **같은 일**을 하나 |
| ★**U2** | **층별 기여도** — 게이트를 0 으로 하고 손실 변화 | *"영향력이 큰 층"* 의 정의이자 측정 |
| **U3** | 잔차 노름 `‖x_i‖` 와 **상대 기여** `‖d_i‖/‖x_i‖` | 뒤 층일수록 상대 기여가 주는가 |
| ★★**U4** | **입력 유사도 vs 출력 유사도** | ★**"묶어도 되는가" 의 판별식** |
| ★**U6** | **재귀 통과별** 기여 | 2회차가 1회차의 몇 % 를 하나 |

## ★★왜 `x` 가 아니라 델타 `d = x_{i+1} − x_i` 인가

잔차 스트림 `x` 는 층을 지나며 **거의 안 변한다** — 그것이 잔차의 성질이다.
🚫`cos(x_i, x_j)` 는 **전부 0.99** 가 나와 **아무 정보가 없다.**
★**층이 한 일은 델타**이고, 결과 041 §17 의 cos 0.9882 도 **델타 기준**이었다.

## ★★U4 가 이 도구의 핵심 — **P049 의 오독을 푼다**

| `cos(in_i,in_j)` | `cos(d_i,d_j)` | 뜻 |
|---|---|---|
| 높음 | **높음** | ★**같은 입력에 같은 일** → **묶어도 된다** |
| 높음 | ★**낮음** | ★★**같은 입력에 다른 일** → 🚫**묶으면 안 된다** |
| 낮음 | 높음 | ⚠️**다른 입력에 비슷한 결과** — 함수가 둔감 |

★**P049 단계3 이 cos 0.9882 를 보고 "대체 가능" 으로 읽었다가 +0.0281 로 실패**했다.
**유사도가 높다 ≠ 대체 가능하다** — 그 이유를 이 표가 답한다.

## 계측 규약 (`check_diag_data.py` 계약)

    1. 절대지표에 난수 정답을 쓰지 않는다 — 실제 val 크롭만 쓴다
    2. 성공 기준값(M1~M5)을 결과보다 **먼저** 인쇄한다
    3. 고정 시드(val 크롭 규약과 같은 99)

사용법
    python scripts/diag_layer_map.py --models mC_initonly dense --preset m100R1c
    python scripts/diag_layer_map.py --models mC_r20_nokd --preset m100R1c --infer-repeat 2.0
    python scripts/diag_layer_map.py --models mC_initonly --preset m100R1c --skip-ablation
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def banner(s, ch="="):
    print("\n" + ch * 100)
    print(f"  {s}")
    print(ch * 100)


def _arch_of(tag):
    return "dense" if tag.startswith("dense") else "tied"


def heat(mat, labels, torch, lo=None, hi=None):
    """n×n 행렬을 **문자 히트맵**으로. 큰 행렬을 로그에 담는 유일한 방법이다."""
    ch = " .:-=+*#%@"
    v = mat.clone()
    n = v.shape[0]
    off = ~torch.eye(n, dtype=torch.bool, device=v.device)
    lo = float(v[off].min()) if lo is None else lo
    hi = float(v[off].max()) if hi is None else hi
    rng = max(hi - lo, 1e-9)
    print(f"      범례 '{ch}'  {lo:+.3f} ~ {hi:+.3f}  (대각선은 1.0 이므로 제외하고 정규화)")
    hdr = "".join(f"{i % 10}" for i in range(n))
    print(f"      {'':>4}{hdr}")
    for i in range(n):
        row = "".join(ch[min(len(ch) - 1, max(0, int((float(v[i, j]) - lo) / rng * (len(ch) - 1))))]
                      for j in range(n))
        print(f"      {labels[i]:>4}{row}")


def main():
    ap = argparse.ArgumentParser(description="P072 레이어 상호작용 지도 (학습 0)")
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--n-crops", type=int, default=8,
                    help="유사도·노름을 평균낼 크롭 수. 8 이면 8k 토큰")
    ap.add_argument("--abl-crops", type=int, default=16,
                    help="ablation 에 쓸 크롭 수. 층마다 forward 하므로 비싸다")
    ap.add_argument("--skip-ablation", action="store_true", help="U2 를 건너뛴다(빠르다)")
    ap.add_argument("--infer-repeat", type=float, default=1.0, help="★U6 — 재귀 통과별")
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--device", default=None)
    # ★2026-08-24 — 글리프 히트맵은 10단계 양자화라 **그림은 되지만 수는 안 된다.**
    #   `scripts/plot_results.py` 와 층별 불균등 압축 설계(REVIEW3 §5-6)에는
    #   정확한 행렬이 필요하다. 인쇄는 그대로 두고 **json 사본만 추가**한다.
    ap.add_argument("--dump-json", default=None, metavar="경로",
                    help="U1·U4 행렬과 U2·U3 표를 json 으로도 저장(인쇄는 무변)")
    a = ap.parse_args()

    import torch
    import torch.nn.functional as F
    from tinylm import paths
    from tinylm.data import prepare, Loader
    from tinylm.infer.generate import load_model

    dev = a.device or ("cuda" if torch.cuda.is_available() else "cpu")
    n_tok = int(float(a.tokens.rstrip("MmBb")) * (1e9 if a.tokens[-1] in "Bb" else 1e6))

    banner("★P072 — 레이어 상호작용 지도. **기준값을 결과보다 먼저 인쇄한다**(함정 34)", "#")
    print("  M1 자기 유사도            기준: **1.0 ± 1e-5** (계측이 옳은지부터)")
    print("  M2 dense 층간 cos 평균     기준: ⚙**0.3 미만** 예상. 높으면 '원래 닮았다'")
    print("  M3 타잉 그룹 내부 vs 그룹간 기준: ★**차 > 0.1** (경계가 닮은 층을 묶었는가)")
    print("  M4 기여도 최대/최소        기준: ⚙**5배 이상** 예상. 균등하면 최적화 여지가 없다")
    print("  M5 재귀 2회차/1회차 기여   기준: ⚙**0.3~0.7**")
    print("\n  ★★델타 `d = x_{i+1} - x_i` 로 잰다 — 잔차 `x` 자체는 거의 안 변해서")
    print("     `cos(x_i,x_j)` 가 전부 0.99 가 나온다(정보 0). **층이 한 일은 델타다.**")
    print(f"\n  device={dev}  크롭 {a.n_crops}(유사도) / {a.abl_crops}(ablation)  seed={a.seed}")

    meta = prepare(a.data, n_tok)

    dump = {}
    for tag in a.models:
        ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, tag)
        if not ck.exists():
            print(f"\n  [건너뜀] 체크포인트 없음: {ck.name}")
            continue
        model, cfg, _ = load_model(arch=_arch_of(tag), ckpt_path=str(ck), device=dev)
        model.eval()
        if a.infer_repeat != 1.0:
            cfg.infer_repeat = a.infer_repeat
        sch = model.visit_schedule()
        n_vis = len(sch)

        banner(f"[{tag}]  층 {cfg.n_layers}  방문 {n_vis}  "
               f"mlp_group {cfg.mlp_group}  attn_group {getattr(cfg,'attn_group',1)}  "
               f"cla_group {cfg.cla_group}")

        # ── 훅으로 각 방문의 입력·출력을 모은다
        acts = []                    # [(in, out)] 방문 순서
        hs = []

        def mk(store):
            def hook(mod, inp, out):
                store.append((inp[0].detach().float(), out.detach().float()
                              if not isinstance(out, tuple) else out[0].detach().float()))
            return hook

        for lyr in model.layers:
            hs.append(lyr.register_forward_hook(mk(acts)))

        va = Loader("val", 1, a.seq, dev, meta["dir"], seed=a.seed)
        ins, outs = None, None
        with torch.no_grad():
            for c in range(a.n_crops):
                acts.clear()
                x, _y = va()
                model(x)
                # 방문 수만큼 쌓인다(재귀면 층이 여러 번 나온다)
                ii = torch.stack([p[0].reshape(-1, cfg.dim).mean(0) for p in acts])
                dd = torch.stack([(p[1] - p[0]).reshape(-1, cfg.dim).mean(0) for p in acts])
                ins = ii if ins is None else ins + ii
                outs = dd if outs is None else outs + dd
        for h in hs:
            h.remove()
        ins, outs = ins / a.n_crops, outs / a.n_crops

        # ── U1 / U4
        ci = F.normalize(ins, dim=1) @ F.normalize(ins, dim=1).t()
        cd = F.normalize(outs, dim=1) @ F.normalize(outs, dim=1).t()
        m1 = float((ci.diag() - 1).abs().max()), float((cd.diag() - 1).abs().max())
        print(f"\n  ★M1 자기 유사도 오차  입력 {m1[0]:.2e} / 델타 {m1[1]:.2e}   "
              f"{'✅' if max(m1) < 1e-5 else '🚫 계측 이상'}")

        lab = [str(i) for i in sch]
        print(f"\n  ── U1 출력 델타 유사도 cos(d_i, d_j)  (행/열 = 방문 순서의 층 번호)")
        heat(cd, lab, torch)
        off = ~torch.eye(n_vis, dtype=torch.bool, device=cd.device)
        print(f"      비대각 평균 **{float(cd[off].mean()):+.4f}**  "
              f"최대 {float(cd[off].max()):+.4f}  최소 {float(cd[off].min()):+.4f}")

        print(f"\n  ── U4 입력 유사도 cos(in_i, in_j)")
        heat(ci, lab, torch)
        if a.dump_json:
            dump[tag] = {"visit_layers": [int(v) for v in sch],
                         "mlp_group": int(cfg.mlp_group or 1),
                         "attn_group": int(getattr(cfg, "attn_group", 1) or 1),
                         "cla_group": int(getattr(cfg, "cla_group", 1) or 1),
                         "n_layers": int(cfg.n_layers), "n_visits": int(n_vis),
                         "U1_delta_cos": [[round(float(v), 6) for v in row] for row in cd],
                         "U4_input_cos": [[round(float(v), 6) for v in row] for row in ci]}
        print(f"      비대각 평균 **{float(ci[off].mean()):+.4f}**")

        # ★U4 판별식 — 같은 입력·다른 일
        banner("★★U4 판별식 — **묶어도 되는가**", "-")
        print("      입력 cos 높고(>0.95) 델타 cos 낮은(<0.90) 쌍 = 🚫**묶으면 안 된다**")
        bad = [(i, j, float(ci[i, j]), float(cd[i, j]))
               for i in range(n_vis) for j in range(i + 1, n_vis)
               if ci[i, j] > 0.95 and cd[i, j] < 0.90]
        good = [(i, j, float(ci[i, j]), float(cd[i, j]))
                for i in range(n_vis) for j in range(i + 1, n_vis)
                if ci[i, j] > 0.95 and cd[i, j] > 0.95]
        print(f"      🚫 같은 입력·다른 일  **{len(bad)}쌍**" +
              ("  예: " + ", ".join(f"L{sch[i]}-L{sch[j]}(in {x:.3f}/d {y:.3f})"
                                    for i, j, x, y in bad[:4]) if bad else ""))
        print(f"      ✅ 같은 입력·같은 일  **{len(good)}쌍**" +
              ("  예: " + ", ".join(f"L{sch[i]}-L{sch[j]}(in {x:.3f}/d {y:.3f})"
                                    for i, j, x, y in good[:4]) if good else ""))
        if not bad and not good:
            print("      ⚠️ 어느 쪽도 없다 — 입력 유사도가 0.95 를 안 넘는다는 뜻이다")

        # ── M3: 타잉 그룹 내부 vs 그룹 간
        g = int(cfg.mlp_group or 1)
        if g > 1 and a.infer_repeat == 1.0:
            pre, mid = cfg.n_prelude, cfg.n_middle
            grp = {}
            for k, li in enumerate(sch):
                if pre <= li < pre + mid:
                    grp[k] = (li - pre) // g
            ks = sorted(grp)
            inn = [float(cd[i, j]) for x, i in enumerate(ks) for j in ks[x + 1:]
                   if grp[i] == grp[j]]
            out_ = [float(cd[i, j]) for x, i in enumerate(ks) for j in ks[x + 1:]
                    if grp[i] != grp[j]]
            if inn and out_:
                d = sum(inn) / len(inn) - sum(out_) / len(out_)
                print(f"\n  ★★M3 타잉 그룹(g={g}) 내부 {sum(inn)/len(inn):+.4f} vs "
                      f"그룹간 {sum(out_)/len(out_):+.4f}  차 **{d:+.4f}**  "
                      f"{'✅ 경계가 닮은 층을 묶었다' if d > 0.1 else '🚫★경계가 유사도를 안 따른다'}")

        # ── U3 노름
        nx = ins.norm(dim=1)
        nd = outs.norm(dim=1)
        print(f"\n  ── U3 잔차 노름과 상대 기여")
        print(f"      {'방문':>4}{'층':>4}{'‖x‖':>10}{'‖d‖':>10}{'‖d‖/‖x‖':>10}")
        for k in range(n_vis):
            print(f"      {k:>4}{sch[k]:>4}{float(nx[k]):>10.3f}{float(nd[k]):>10.3f}"
                  f"{float(nd[k]/nx[k].clamp(min=1e-9)):>10.4f}")

        # ── U2 ablation
        if not a.skip_ablation:
            banner("★U2 층별 기여도 — 게이트를 0 으로 하고 손실 변화", "-")
            print("      ⚠️★**한 층씩만** 뺀다. 층은 상호작용하므로 **Δ 의 합 ≠ 전부 뺀 값**.")
            print("        ★그래도 **순위**는 신뢰할 수 있고 그것이 필요한 것이다.\n")
            va2 = Loader("val", 1, a.seq, dev, meta["dir"], seed=a.seed)
            crops = [va2() for _ in range(a.abl_crops)]

            def loss_now():
                t = 0.0
                with torch.no_grad():
                    for x, y in crops:
                        lg = model(x)
                        t += float(F.cross_entropy(lg.reshape(-1, cfg.vocab_size),
                                                   y.reshape(-1)))
                return t / len(crops)

            base = loss_now()
            print(f"      기준 손실 **{base:.4f}**  (크롭 {a.abl_crops}개)")
            deltas = []
            uniq = sorted(set(sch))
            for li in uniq:
                lyr = model.layers[li]
                old = lyr.gates.data.clone()
                lyr.gates.data.zero_()
                deltas.append((li, loss_now() - base))
                lyr.gates.data = old
            deltas.sort(key=lambda t: -t[1])
            print(f"\n      {'순위':>4}{'층':>5}{'Δ손실':>12}  기여")
            mx = max(d for _l, d in deltas) or 1.0
            for r, (li, d) in enumerate(deltas, 1):
                bar = "#" * int(max(0, d) / mx * 40)
                print(f"      {r:>4}{li:>5}{d:>+12.4f}  {bar}")
            pos = [d for _l, d in deltas if d > 0]
            if pos:
                ratio = max(pos) / max(min(pos), 1e-9)
                print(f"\n      ★M4 최대/최소 = **{ratio:.1f}배**  "
                      f"{'✅ 층이 균등하지 않다 — 불균등 압축의 근거' if ratio > 5 else '⚠️균등하다'}")
            neg = [(l, d) for l, d in deltas if d < 0]
            if neg:
                print(f"      ⚠️★**빼면 오히려 좋아지는 층 {len(neg)}개**: "
                      f"{[l for l, _ in neg]} — 해로운 층인가, 계측 잡음인가")

        if a.dump_json and tag in dump:
            dump[tag]["U3_dnorm"] = [round(float(v), 6) for v in nd]
            dump[tag]["U2_ablation"] = [[int(l), round(float(d), 6)]
                                        for l, d in deltas] if not a.skip_ablation else []
        # ── U6
        if a.infer_repeat != 1.0:
            banner("★U6 재귀 통과별 기여", "-")
            seen, first, second = {}, [], []
            for k, li in enumerate(sch):
                c = seen.get(li, 0)
                seen[li] = c + 1
                (first if c == 0 else second).append(float(nd[k]))
            if first and second:
                r = (sum(second) / len(second)) / max(sum(first) / len(first), 1e-9)
                print(f"      1회차 평균 ‖d‖ {sum(first)/len(first):.4f}  "
                      f"2회차 {sum(second)/len(second):.4f}  ★비 **{r:.3f}**")
                print(f"      {'✅ M5 대역(0.3~0.7)' if 0.3 <= r <= 0.7 else '⚠️M5 대역 밖'}")

        del model
        if dev == "cuda":
            torch.cuda.empty_cache()

    if a.dump_json and dump:
        import json as _json
        _p = Path(a.dump_json)
        _p.parent.mkdir(parents=True, exist_ok=True)
        _p.write_text(_json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n  ★행렬 json 저장 -> {_p}  (모델 {len(dump)}개)")
        print("     ⚠️인쇄된 글리프 히트맵은 10단계 양자화다. **수는 이 json 을 쓴다.**")
    banner("판정 — ★이 지도를 P057 그룹 경계·P070 셔플·P049 재사용의 근거로 쓴다", "#")
    print("  ⚠️★**유사도는 상관이다. 인과가 아니다.**")
    print("     P049 단계3 이 정확히 그 함정에 빠졌다 — cos 0.9882 를 '대체 가능' 으로 읽고")
    print("     +0.0281 로 실패했다. ★**U4 의 '같은 입력·다른 일' 이 그 이유를 설명한다.**")
    print("  ⚠️★**학습 끝난 체크포인트에서만** 잰다. 학습 중 형성 과정은 못 본다.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
