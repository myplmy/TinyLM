"""인접 레이어 잔차의 랭크 스펙트럼 분석.

delta 아이디어의 성패는 "인접 레이어의 차이가 저랭크인가"에 달려 있다.
이 스크립트는 임의의 HF 모델에서 그걸 직접 측정한다.

    pip install transformers torch
    python rank_spectrum.py Qwen/Qwen3-1.7B --group 4

group=4면 인접 4개 레이어를 한 블록으로 묶는 시나리오를 평가한다.
(Relaxed Recursive Transformers, arXiv:2410.20672 의 Average+SVD init과 동일한 계산)
"""
import sys, argparse, torch

def analyze(model_id, group, ranks=(8, 16, 32, 64, 128)):
    from transformers import AutoModelForCausalLM
    m = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
    layers = m.model.layers
    names = [n for n, _ in layers[0].named_parameters() if _.dim() == 2]
    print(f"{model_id}: {len(layers)}층, 블록당 {group}층\n")
    print(f"{'행렬':<26}{'break-even r*':>14}" + "".join(f"{f'r={r}':>9}" for r in ranks))
    print("-" * (40 + 9*len(ranks)))
    for nm in names:
        caps = {r: [] for r in ranks}; rstar = None
        for b in range(len(layers)//group):
            Ws = [dict(layers[b*group+i].named_parameters())[nm].data for i in range(group)]
            shared = torch.stack(Ws).mean(0)                  # Average init
            for W in Ws:
                s = torch.linalg.svdvals(W - shared)
                e = (s**2).cumsum(0) / (s**2).sum().clamp_min(1e-12)
                for r in ranks:
                    caps[r].append(e[min(r, len(e))-1].item())
            o, i = shared.shape
            rstar = 1.71*o*i / (16*(o+i))
        print(f"{nm[:26]:<26}{rstar:>14.0f}" +
              "".join(f"{sum(caps[r])/len(caps[r]):>8.0%} " for r in ranks))
    print("\n판정: r*보다 훨씬 작은 랭크에서 에너지 포착률이 70%를 넘으면 delta가 유리.")
    print("      r=16~32에서 30% 미만이면 블록 수를 늘리는 편이 낫다.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("model_id"); p.add_argument("--group", type=int, default=4)
    a = p.parse_args(); analyze(a.model_id, a.group)
