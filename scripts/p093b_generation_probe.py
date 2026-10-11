"""Diagnostic-only nucleus selection/few-shot prefixes; no model or private IO."""
from __future__ import annotations
from contextlib import contextmanager
from unittest.mock import patch
import torch

VERSION="P093B_GENERATION_ATTRIBUTION_V1"
EXAMPLES={
"ko_context":"정보: 가=초록, 나=노랑입니다.\n질문: 가의 색은 무엇입니까?\n답: 초록\n\n",
"en_context":"Facts: X=green, Y=yellow.\nQuestion: What is the color of X?\nAnswer: green\n\n",
"ko_math":"질문: 2 더하기 2는 얼마입니까?\n답: 4\n\n",
"en_math":"Question: What is 2 plus 2?\nAnswer: 4\n\n",
"ko_literal":"질문: 숫자 2만 출력하세요.\n답: 2\n\n",
"en_literal":"Question: Output only the number 2.\nAnswer: 2\n\n",
"ko_reason":"문장: 눈이 오면 바닥이 차가워집니다.\n질문: 바닥이 차가워질 수 있는 이유는 무엇입니까?\n답: 눈이 왔기 때문일 수 있습니다.\n\n",
"en_reason":"Sentence: A floor can get cold when snow falls.\nQuestion: Why might the floor be cold?\nAnswer: Snow may have fallen.\n\n"}

def prompt(ident,original,kind):
    if kind=="plain":return original
    if kind!="fewshot" or ident not in EXAMPLES:raise ValueError("known diagnostic prompt required")
    return EXAMPLES[ident]+original


def nucleus_probs(probs,p=.95):
    if not 0<p<=1 or probs.ndim!=2 or not torch.isfinite(probs).all() or (probs<0).any():
        raise ValueError("finite batched nonnegative probabilities required")
    if (probs.sum(-1)<=0).any():raise ValueError("positive mass required")
    values,order=probs.sort(-1,descending=True)
    keep=values.cumsum(-1)-values<p*values.sum(-1,keepdim=True)
    selected=torch.where(keep,values,0)
    out=torch.zeros_like(probs).scatter(-1,order,selected)
    return out/out.sum(-1,keepdim=True)


@contextmanager
def nucleus_scope(p=.95):
    """Reuse the single generation loop; alter sampling only in this diagnostic."""
    original=torch.multinomial
    def filtered(probs,*args,**kwargs):
        return original(nucleus_probs(probs,p),*args,**kwargs)
    with patch.object(torch,"multinomial",filtered):yield


def representation_stats(hidden,ids):
    """Small last-hidden observation, not an automatic quality/collapse decision."""
    x=hidden.detach().float()
    tokens=torch.as_tensor(ids,device=x.device,dtype=torch.long)
    if x.ndim!=2 or tokens.ndim!=1 or len(tokens)!=len(x) or len(x)>256:
        raise ValueError("aligned <=256-position hidden/token IDs required")
    if not torch.isfinite(x).all():raise ValueError("nonfinite hidden")
    if len(x)<2:return {"positions":len(x),"status":"INSUFFICIENT_POSITIONS"}
    norms=x.norm(dim=-1)
    if (norms<=1e-12).any():raise ValueError("zero hidden norm")
    unit=x/norms[:,None];cos=unit@unit.T
    upper=torch.triu(torch.ones_like(cos,dtype=torch.bool),diagonal=1)
    same=tokens[:,None]==tokens[None,:]
    def aggregate(mask):
        values=cos[mask]
        return {"pairs":int(values.numel()),"mean":float(values.mean()) if values.numel() else None,
                "above_point9_fraction":float((values>.9).float().mean()) if values.numel() else None}
    centered=unit-unit.mean(0,keepdim=True)
    eigen=torch.linalg.eigvalsh(centered@centered.T).clamp_min(0)
    energy=eigen.sum()
    p=eigen/energy if float(energy)>1e-12 else eigen
    rank=float(torch.exp(-(p[p>0]*p[p>0].log()).sum())) if float(energy)>1e-12 else 0.
    return {"positions":len(x),"dimensions":x.shape[1],"same_token":aggregate(upper&same),
        "different_token":aggregate(upper&~same),"centered_covariance_entropy_rank":rank,
        "rank_upper_bound":min(len(x)-1,x.shape[1]),"norm_mean":float(norms.mean()),
        "status":"OBSERVED","decision":"NONE; token similarity is not semantic error or quality PASS"}
