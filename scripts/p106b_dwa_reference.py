"""DWA ingredients only: detached token weights and bounded CPU Soft-DTW reference.

Not full DWA-KD: cross-model attention, native integration and self-band policy are absent.
"""
import math
import torch
from torch.nn import functional as F


def normalized_weights(student_logits,projected_teacher_logits,teacher_logits,*,detach):
    if (type(detach)is not bool or student_logits.ndim!=2 or projected_teacher_logits.shape!=student_logits.shape
            or teacher_logits.ndim!=2 or min(student_logits.shape+teacher_logits.shape)<1
            or student_logits.shape[1]<2 or teacher_logits.shape[1]<2
            or len({t.device for t in [student_logits,projected_teacher_logits,teacher_logits]})!=1
            or any(not t.is_floating_point()or not bool(torch.isfinite(t).all())for t in [student_logits,projected_teacher_logits,teacher_logits])):
        raise ValueError('finite complete student/teacher distributions and explicit gradient policy required')
    def entropy(z):
        p=F.log_softmax(z,dim=-1);return -(p.exp()*p).sum(-1)
    raw_s=entropy(student_logits)*projected_teacher_logits.softmax(-1).amax(-1)
    raw_t=1-entropy(teacher_logits)/math.log(teacher_logits.shape[1])
    raw_t=raw_t.clamp_min(0.)
    def normalize(x):
        if float(x.sum().detach())<=torch.finfo(x.dtype).eps:raise ValueError('zero token-weight mass requires explicit HOLD/fallback policy')
        return x*len(x)/x.sum()
    s=normalize(raw_s);t=normalize(raw_t)
    return (s.detach(),t.detach())if detach else(s,t)


def adaptive_band_cost(cost,attention,*,alpha=.7,base=5.,entropy_scale=2.,penalty=1.):
    if (cost.ndim!=2 or attention.shape!=cost.shape or min(cost.shape)<1
            or not bool(torch.isfinite(cost).all())or not bool(torch.isfinite(attention).all())
            or bool((attention<0).any())or not torch.allclose(attention.sum(1),torch.ones(cost.shape[0],dtype=attention.dtype,device=attention.device),atol=1e-6,rtol=1e-6)
            or not all(math.isfinite(float(x))for x in [alpha,base,entropy_scale,penalty])or not 0<=alpha<=1 or min(base,entropy_scale,penalty)<0):
        raise ValueError('finite row-stochastic cross-attention and declared band parameters required')
    a=attention.detach();s,t=cost.shape;j=torch.arange(1,t+1,device=cost.device,dtype=cost.dtype)
    i=torch.arange(1,s+1,device=cost.device,dtype=cost.dtype)
    center=alpha*(a*j).sum(1)+(1-alpha)*i*t/s
    entropy=-(a*torch.where(a>0,a.log(),torch.zeros_like(a))).sum(1)
    width=base+entropy_scale*entropy
    outside=(j.unsqueeze(0)-center.unsqueeze(1)).abs()>width.unsqueeze(1)
    return cost+penalty*outside.to(cost.dtype)


def soft_dtw(cost,*,gamma,max_cells=4096):
    if (cost.ndim!=2 or min(cost.shape)<1 or not cost.is_floating_point()or not bool(torch.isfinite(cost).all())
            or not math.isfinite(gamma)or gamma<=0 or type(max_cells)is not int or max_cells<1
            or cost.numel()>max_cells):raise ValueError('finite bounded CPU reference cost and positive gamma required')
    if cost.device.type!='cpu':raise ValueError('slow CPU reference is not a production GPU kernel')
    n,m=cost.shape;inf=cost.new_tensor(float('inf'));r=[[inf for _ in range(m+1)]for _ in range(n+1)];r[0][0]=cost.new_zeros(())
    for i in range(1,n+1):
        for j in range(1,m+1):r[i][j]=cost[i-1,j-1]-gamma*torch.logsumexp(-torch.stack((r[i-1][j],r[i][j-1],r[i-1][j-1]))/gamma,dim=0)
    return r[n][m]


def unbanded_divergence(x,y,*,gamma,max_cells=4096):
    if (x.ndim!=2 or y.ndim!=2 or x.shape[1]!=y.shape[1]or min(x.shape+y.shape)<1
            or not bool(torch.isfinite(x).all())or not bool(torch.isfinite(y).all())
            or bool((x.norm(dim=-1)==0).any())or bool((y.norm(dim=-1)==0).any())):
        raise ValueError('finite nonzero same-space vectors required')
    x=F.normalize(x,dim=-1);y=F.normalize(y,dim=-1)
    d=lambda a,b:soft_dtw(1-a@b.T,gamma=gamma,max_cells=max_cells)
    return d(x,y)-.5*(d(x,x)+d(y,y))
