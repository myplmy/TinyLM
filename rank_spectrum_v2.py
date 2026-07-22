"""rank_spectrum_v2 — 레이어 통합의 세 가지 자유도를 모두 열어놓고 측정한다.

v1은 (인접 그룹 + 평균 base + 순수 Frobenius SVD) 한 조합만 봤다.
실제로 바꿀 수 있는 축은 세 개다.

  1) 그룹 구성    adjacent  vs  similarity  (거리 무관, 비슷한 레이어끼리)
  2) 공유 base    mean      vs  als         (base와 delta를 같이 최적화)
  3) 목적함수     frobenius vs  activation  (입력 공분산 가중 = 실제 손실에 가까움)

사용:
  python rank_spectrum_v2.py Qwen/Qwen3-1.7B --blocks 7
  python rank_spectrum_v2.py Qwen/Qwen3-1.7B --blocks 7 --calib wikitext

--calib을 주면 활성 가중 SVD를 쓴다. 보통 이게 가장 크게 바뀐다.
활성 가중은 ||(W-W'-BA) X||_F 를 최소화하므로, 실제로 쓰이지 않는
가중치 방향에 랭크를 낭비하지 않는다 (ASVD / SVD-LLM 계열).
"""
from __future__ import annotations
import argparse, torch


# --------------------------------------------------------------------------
def cluster_layers(mats: list[torch.Tensor], n_blocks: int, mode: str) -> list[list[int]]:
    """레이어를 n_blocks개 그룹으로. adjacent = 인접, similarity = 코사인 k-means."""
    L = len(mats)
    if mode == "adjacent":
        g = L // n_blocks
        return [list(range(b*g, min((b+1)*g, L))) for b in range(n_blocks)]

    X = torch.stack([m.flatten() for m in mats])
    X = X / X.norm(dim=1, keepdim=True)
    # k-means++ 스타일 초기화: 서로 가장 먼 레이어부터
    cen = [0]
    for _ in range(n_blocks - 1):
        d = torch.stack([1 - X @ X[c] for c in cen]).min(0).values
        cen.append(int(d.argmax()))
    C = X[cen].clone()
    for _ in range(50):
        a = (X @ C.T).argmax(1)
        for k in range(n_blocks):
            if (a == k).any():
                C[k] = torch.nn.functional.normalize(X[a == k].mean(0), dim=0)
    return [[i for i in range(L) if a[i] == k] for k in range(n_blocks) if (a == k).any()]


def solve_base_and_deltas(Ws: list[torch.Tensor], rank: int, mode: str,
                          S: torch.Tensor | None, iters: int = 12):
    """공유 base W' 와 각 레이어의 rank-r delta를 구한다.

    mean : W' = 평균 (delta=0일 때만 최적)
    als  : min_{W',A,B} sum ||(W_l - W' - B_l A_l) S|| 를 교대 최소화.
           delta가 있다는 전제에서 base를 다시 잡는다 -> 평균보다 항상 <= 오차.
    S    : 활성 화이트닝 행렬 (None이면 항등 = Frobenius)
    """
    W = torch.stack(Ws)
    base = W.mean(0)
    if mode == "mean" or rank == 0:
        iters = 1
    for _ in range(iters):
        R = W - base
        low = []
        for r_ in R:
            M = r_ @ S if S is not None else r_
            U, s, Vh = torch.linalg.svd(M, full_matrices=False)
            approx = (U[:, :rank] * s[:rank]) @ Vh[:rank]
            low.append(approx @ torch.linalg.inv(S) if S is not None else approx)
        low = torch.stack(low)
        if mode == "mean":
            break
        base = (W - low).mean(0)          # delta를 고정하고 base 재추정
    return base, low


def energy_captured(Ws, base, low, S):
    num = den = 0.0
    for W, D in zip(Ws, low):
        r_ = W - base
        A = r_ @ S if S is not None else r_
        B = (r_ - D) @ S if S is not None else (r_ - D)
        num += (A**2).sum().item() - (B**2).sum().item()
        den += (A**2).sum().item()
    return num / max(den, 1e-12)


# --------------------------------------------------------------------------
def collect_activation_scales(model, tok, name_filter, n_batches=8, seqlen=512):
    """각 선형층 입력의 채널별 RMS. 화이트닝 행렬 S = diag(rms)."""
    from datasets import load_dataset
    scales = {}
    hooks = []
    def hook(nm):
        def f(mod, inp, out):
            x = inp[0].detach().float().reshape(-1, inp[0].shape[-1])
            s = x.pow(2).mean(0).sqrt()
            scales[nm] = s if nm not in scales else torch.maximum(scales[nm], s)
        return f
    for nm, mod in model.named_modules():
        if isinstance(mod, torch.nn.Linear) and name_filter in nm:
            hooks.append(mod.register_forward_hook(hook(nm)))
    ds = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1", split="train")
    with torch.no_grad():
        for i in range(n_batches):
            ids = tok(ds[i*20]["text"] * 4, return_tensors="pt",
                      truncation=True, max_length=seqlen).input_ids
            if ids.shape[1] > 8:
                model(ids)
    for h in hooks:
        h.remove()
    return scales


def main():
    p = argparse.ArgumentParser()
    p.add_argument("model_id")
    p.add_argument("--blocks", type=int, default=7)
    p.add_argument("--ranks", type=int, nargs="+", default=[16, 32, 64, 128])
    p.add_argument("--calib", default=None, help="지정하면 활성 가중 SVD 사용")
    a = p.parse_args()

    from transformers import AutoModelForCausalLM, AutoTokenizer
    model = AutoModelForCausalLM.from_pretrained(a.model_id, torch_dtype=torch.float32)
    layers = model.model.layers
    names = [n for n, q in layers[0].named_parameters() if q.dim() == 2]
    print(f"{a.model_id}: {len(layers)}층 -> {a.blocks}블록\n")

    act = {}
    if a.calib:
        tok = AutoTokenizer.from_pretrained(a.model_id)
        act = collect_activation_scales(model, tok, "layers")
        print(f"활성 스케일 수집 완료 ({len(act)}개 선형층)\n")

    for nm in names:
        Ws_all = [dict(l.named_parameters())[nm].data for l in layers]
        S = None
        if a.calib:
            key = [k for k in act if k.endswith(nm.replace(".weight", ""))]
            if key:
                s = torch.stack([act[k] for k in key]).mean(0)
                S = torch.diag(s.clamp_min(1e-4))
        print(f"[{nm}]")
        hdr = "".join(f"{f'r={r}':>9}" for r in a.ranks)
        print(f"  {'그룹구성':<12}{'base':<7}{hdr}")
        for gmode in ("adjacent", "similarity"):
            groups = cluster_layers(Ws_all, a.blocks, gmode)
            for bmode in ("mean", "als"):
                out = []
                for r in a.ranks:
                    caps = []
                    for g in groups:
                        if len(g) < 2:
                            continue
                        Ws = [Ws_all[i] for i in g]
                        base, low = solve_base_and_deltas(Ws, r, bmode, S)
                        caps.append(energy_captured(Ws, base, low, S))
                    out.append(sum(caps)/max(len(caps), 1))
                print(f"  {gmode:<12}{bmode:<7}" + "".join(f"{v:>8.0%} " for v in out))
        if a.calib:
            print("  (활성 가중 기준)")
        print()


if __name__ == "__main__":
    main()
