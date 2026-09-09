"""P076 단계0 — **타잉 그룹 안의 층들이 서로 얼마나 닮았는가.** 학습 0 · GPU 0.

## 왜 이 진단이 먼저인가

타잉 부모초기화는 dense 부모의 `g` 개 층 `W1..Wg` 를 **산술평균**해서 공유 가중치
하나를 만든다(A1, 현행). 이 규약을 아무도 검증한 적이 없다.

★**평균의 위험은 상쇄다.** 층마다 방향이 다르면 더할수록 **크기가 줄어든다** —
부모초기화가 주는 신호(+0.1386)를 스스로 약화시키는 것이다.
계획 P076 이 대안 다섯(A2~A6)을 적어 뒀는데, **그중 A4(노름 보정 평균)만이
"방향은 평균, 크기는 원래" 를 정확히 복원**한다.

🚫**그런데 상쇄가 실제로 일어나는지를 한 번도 안 쟀다.** 이 도구가 그것부터 잰다.

## 무엇을 재나

| 지표 | 뜻 | 판정 |
|---|---|---|
| ★**축소비** `norm(mean(Wi)) / mean(norm(Wi))` | 평균이 크기를 얼마나 잃는가 | **1.0 = 상쇄 없음** |
| 평균 쌍 코사인 유사도 | 그룹 안 층들이 같은 방향인가 | 높을수록 평균이 안전 |
| 층 인덱스 추세 | 깊을수록 달라지는가 | — |

★**판정 규칙(P076 §3)**
    축소비 ^> 0.9  -> A1 과 A4 가 거의 같다. **Q1 이 시시해진다. 단계2 를 열지 않는다.**
    축소비 ^< 0.7  -> ★**A4 를 만들 값어치가 있다.** 단계2 를 연다.
    그 사이       -> 경계. 코사인 유사도를 함께 보고 사람이 정한다.

⚠️**이 도구는 dense 부모 체크포인트 하나만 읽는다.** 학습하지 않고 GPU 도 쓰지 않는다.
⚠️**torch 는 필요하다**(체크포인트를 읽어야 한다) — 정적 게이트가 아니다.

    python scripts/diag_group_agg.py --preset m100R1c --data ko-en --tokens 300M --tag dense
"""
from __future__ import annotations
import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ★성공 기준값 — `check_diag_data` 가 이 상수의 존재를 본다(함정 32).
GATE_SAFE = 0.90      # 이 위면 A1 == A4, 실험 불필요
GATE_OPEN = 0.70      # 이 아래면 A4 를 만든다


def main() -> int:
    ap = argparse.ArgumentParser(description="P076 단계0 — 타잉 그룹 내 유사도")
    ap.add_argument("--preset", default="m100R1c")
    ap.add_argument("--data", default="ko-en")
    ap.add_argument("--tokens", default="300M")
    ap.add_argument("--tag", default="dense", help="dense 부모의 태그")
    ap.add_argument("--seq", type=int, default=1024,
                    help="build_config 가 요구한다. 이 도구의 결과에는 영향이 없다(층 구조만 읽는다)")
    ap.add_argument("--group", type=int, default=None,
                    help="타잉 그룹 크기 g. 미지정이면 프리셋의 mlp_group")
    a = ap.parse_args()

    import torch
    import tinylm                                    # noqa: F401  (HF 캐시 리다이렉트)
    from tinylm import paths
    from tinylm.config import build_config

    ck = paths.resolve_ckpt(a.preset, a.data, a.tokens, a.tag)
    if not ck.exists():
        print(f"[!] 부모 체크포인트가 없다: {ck}")
        print("    dense 정본을 먼저 학습해야 한다. 이 도구는 학습하지 않는다.")
        return 1
    sd = torch.load(ck, map_location="cpu", weights_only=False)
    sd = sd.get("model", sd)

    cfg = build_config(a.preset, "tied", a.seq, True)
    g = a.group or int(getattr(cfg, "mlp_group", 8))
    p, m = int(cfg.n_prelude), int(cfg.n_middle)

    print("=" * 96)
    print("  P076 단계0 — 타잉 그룹 안의 층들이 서로 얼마나 닮았는가 (학습 0 · GPU 0)")
    print(f"  부모 = {ck.name}   그룹 크기 g = {g}   middle = {m}층 (prelude {p})")
    print("=" * 96)

    # 층 인덱스 -> 그 층의 MLP/어텐션 파라미터 이름들
    per_layer: dict[int, list[str]] = defaultdict(list)
    for k in sd:
        parts = k.split(".")
        for i, tokn in enumerate(parts):
            if tokn == "layers" and i + 1 < len(parts) and parts[i + 1].isdigit():
                per_layer[int(parts[i + 1])].append(k)
                break

    # ★★2026-09-02 — **MLP 를 여기서 놓치고 있었다.**
    #   `Layer` 는 `self.mlp = [mlp]` 로 모듈 등록을 피하므로 state_dict 에
    #   `layers.N.mlp.*` 가 **없다**. 실체는 최상위 `mid_mlps.{j}.*` 다.
    #   dense 부모(`tie_mlp=False`)에서는 j 가 middle 인덱스이므로 층 = p + j.
    n_mid_mlp = len({k.split('.')[1] for k in sd
                     if k.startswith('mid_mlps.') and k.split('.')[1].isdigit()})
    # ★★2026-09-02 E17 — **0개와 '개수가 다르다' 는 서로 다른 고장이다.**
    #   종전 조건 `if n_mid_mlp and ...` 은 **0 이면 조용히 지나갔고**,
    #   그 뒤 수집 루프도 0건이라 도구가 '이미 타잉' 도 '못 찾음' 도 아닌
    #   **세 번째 상태**로 끝났다. 두 세션이 그 상태를 각각 한 번씩 돌았다.
    if n_mid_mlp == 0:
        print('[!] ★state_dict 에 `mid_mlps.*` 키가 **하나도 없다.**')
        print('    이 도구는 MLP 를 거기서 읽는다. 아래가 실제로 있는 것이다:')
        _pref = defaultdict(int)
        for k in sd:
            _pref[k.split('.')[0]] += 1
        for _k, _n in sorted(_pref.items(), key=lambda kv: -kv[1])[:12]:
            print(f'      {_k:<24} {_n:>6}개')
        print('    MLP 로 보이는 키 예시:')
        _mlpish = [k for k in sd if 'mlp' in k.lower()
                   or 'gate_proj' in k or 'up_proj' in k or 'down_proj' in k]
        for k in _mlpish[:8]:
            print(f'      {k}')
        if not _mlpish:
            print('      (없다) — 전체 키 예시:')
            for k in list(sd)[:8]:
                print(f'      {k}')
        return 1
    if n_mid_mlp != m:
        print(f'[!] 부모의 mid_mlps 가 {n_mid_mlp}개인데 middle 은 {m}층이다 '
              f'-> 이 부모는 **이미 타잉된 것**이라 「그룹 안 상쇄」를 물을 수 없다.')
        print('    dense 부모를 준다. 이 도구는 dense 부모 전용이다.')
        return 1
    for k in sd:
        if k.startswith('mid_mlps.'):
            j = k.split('.')[1]
            if j.isdigit():
                per_layer[p + int(j)].append(k)

    if not per_layer:
        print("[!] state_dict 에서 `layers.N.` 도 `mid_mlps.N.` 도 못 찾았다. 키 예시:")
        for k in list(sd)[:6]:
            print(f"    {k}")
        return 1

    def kind(name: str) -> str:
        n = name.lower()
        if "mlp" in n:
            return "mlp"
        if any(t in n for t in ("attn", "q_proj", "k_proj", "v_proj", "o_proj", "wq", "wk")):
            return "attn"
        return "기타"

    # middle 층을 g 개씩 묶는다 — trainer 의 그룹 규약과 같은 순서다
    mids = [i for i in sorted(per_layer) if p <= i < p + m]
    groups = [mids[s:s + g] for s in range(0, len(mids), g)]
    print(f"  middle 층 {len(mids)}개 -> 그룹 {len(groups)}개 "
          f"(그룹당 {g}층, 마지막 {len(groups[-1]) if groups else 0}층)")
    print()

    rows = []
    for gi, grp in enumerate(groups):
        if len(grp) < 2:
            continue
        # 같은 접미사(= 같은 역할)의 텐서끼리 묶는다
        suffix = defaultdict(dict)
        for li in grp:
            for k in per_layer[li]:
                if k.startswith('mid_mlps.'):
                    # `mid_mlps.7.gate_proj.weight` -> `mlp.gate_proj.weight`
                    sfx = 'mlp.' + k.split('.', 2)[2]
                else:
                    sfx = k.split(f"layers.{li}.", 1)[-1]
                suffix[sfx][li] = k
        for sfx, mp in sorted(suffix.items()):
            if len(mp) < 2:
                continue
            ws = [sd[mp[li]].float().reshape(-1) for li in sorted(mp)]
            if ws[0].numel() < 64:                       # 스칼라·bias 는 의미가 없다
                continue
            W = torch.stack(ws)
            norms = W.norm(dim=1)
            mean_w = W.mean(0)
            shrink = (mean_w.norm() / norms.mean()).item()
            Wn = W / norms.unsqueeze(1).clamp_min(1e-12)
            cos = (Wn @ Wn.T)
            n = cos.shape[0]
            off = (cos.sum() - cos.diag().sum()) / (n * (n - 1))
            rows.append((gi, sfx, kind(sfx), shrink, off.item(), W.shape[1]))

    if not rows:
        print("[!] 비교할 텐서 쌍을 못 찾았다.")
        return 1

    print(f"  {'그룹':>4} {'종류':>5} {'파라미터':<34} {'원소':>10} {'축소비':>8} {'평균코사인':>10}")
    print("  " + "-" * 92)
    for gi, sfx, kd, sh, cs, ne in rows:
        flag = "  ★상쇄" if sh < GATE_OPEN else ("" if sh > GATE_SAFE else "  ⚠️경계")
        print(f"  {gi:>4} {kd:>5} {sfx[:34]:<34} {ne:>10,} {sh:>8.4f} {cs:>10.4f}{flag}")

    print()
    print("=" * 96)
    print("  ★판정")
    print("=" * 96)
    for kd in ("mlp", "attn", "기타"):
        sub = [r for r in rows if r[2] == kd]
        if not sub:
            continue
        sh = sum(r[3] for r in sub) / len(sub)
        cs = sum(r[4] for r in sub) / len(sub)
        lo = min(r[3] for r in sub)
        verdict = ("A1(평균) 과 A4(노름보정) 가 거의 같다 -> 단계2 를 열 근거가 없다"
                   if sh > GATE_SAFE else
                   "★A4 를 만들 값어치가 있다 -> 단계2 를 연다" if sh < GATE_OPEN else
                   "⚠️경계 — 코사인과 함께 사람이 정한다")
        print(f"  [{kd}] 텐서 {len(sub)}종 · 평균 축소비 {sh:.4f}(최소 {lo:.4f}) · "
              f"평균 코사인 {cs:.4f}")
        print(f"        -> {verdict}")
    print()
    # ★★2026-09-02 신설 — **이 실험의 주 대상은 MLP 다.**
    #   2026-08-31 판에서는 MLP 가 0종인 채로 어텐션만 재고 exit 0 이었다.
    #   R19: 주 지표를 0개 재고 정상 종료하는 것이 가장 나쁜 실패다.
    n_mlp = sum(1 for r in rows if r[2] == 'mlp')
    if n_mlp == 0:
        print()
        print('  🚫★**MLP 텐서를 한 종도 못 쟀다 — 이 실험의 주 대상이다.**')
        print('     아래가 이 체크포인트에 **실제로 있는 접미사**다 — 무엇을 못 읽었는지 보라.')
        # ★★E17 — 종전 판은 *"mid_mlps 가 있는지 확인하라"* 고 **지시만** 하고
        #   무엇이 있었는지는 안 찍었다. 그래서 두 번째 시도가 첫 번째와 똑같이 끝났다.
        #   🚫**게이트는 실패를 알리는 것으로 끝나지 않는다 — 다음 수를 줘야 한다.**
        _sfx = sorted({(r[0] if isinstance(r[0], str) else '') for r in rows})
        _seen = sorted({k.split('.', 1)[-1] if k.startswith('mid_mlps.')
                        else k.split('.', 2)[-1]
                        for li in sorted(per_layer)[:1] for k in per_layer[li]})
        for x in _seen[:16]:
            print(f'       {x}')
        _mlpish = [k for k in sd if 'gate_proj' in k or 'up_proj' in k
                   or 'down_proj' in k or 'mlp' in k.lower()]
        print(f'     ★MLP 로 보이는 키 전체 {len(_mlpish)}개'
              + (f' — 예: {_mlpish[0]}' if _mlpish else ' — **하나도 없다**'))
        return 1
    print(f"  기준: 축소비 ^> {GATE_SAFE} 안전 / ^< {GATE_OPEN} 열림  (P076 §3)")
    print("  ⚠️축소비는 **초기화 시점의 기하**만 말한다 — 학습이 그것을 얼마나 씻는지는")
    print("     이 도구가 답하지 않는다. 그것이 단계2(2.7h x 팔 수)의 몫이다.")
    print("  🚫**이 수치로 A1~A6 의 서열을 매기지 않는다.** 여는가 마는가만 정한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
