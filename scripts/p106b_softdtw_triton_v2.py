"""First-order FP64 Soft-DTW cost prototype, one anti-diagonal CTA per matrix."""
import math
import torch
import triton
import triton.language as tl
from triton.language.extra.cuda import libdevice


@triton.jit
def _forward(C,P,O,G,N:tl.constexpr,M:tl.constexpr,BLOCK:tl.constexpr):
    j=tl.arange(0,BLOCK);jm=tl.maximum(j-1,0)
    prev=tl.full((BLOCK,),float('inf'),tl.float64)
    prev2=tl.full((BLOCK,),float('inf'),tl.float64)
    gamma=tl.load(G)
    for d in range(N+M-1):
        i=d-j;valid=(j<M)&(i>=0)&(i<N)
        a=tl.where(valid&(i>0),prev,float('inf'))
        b=tl.where(valid&(j>0),tl.gather(prev,jm,axis=0),float('inf'))
        c=tl.where(valid&(i>0)&(j>0),tl.gather(prev2,jm,axis=0),float('inf'))
        c=tl.where(valid&(i==0)&(j==0),0.,c)
        minimum=tl.where(valid,tl.minimum(a,tl.minimum(b,c)),0.)
        ea=libdevice.exp((minimum-a)/gamma);eb=libdevice.exp((minimum-b)/gamma);ec=libdevice.exp((minimum-c)/gamma)
        z=tl.where(valid,ea+eb+ec,1.)
        value=tl.load(C+i*M+j,mask=valid,other=0.)+minimum-gamma*libdevice.log(z)
        value=tl.where(valid,value,float('inf'))
        offset=i*M+j
        tl.store(P+offset,ea/z,mask=valid);tl.store(P+N*M+offset,eb/z,mask=valid);tl.store(P+2*N*M+offset,ec/z,mask=valid)
        tl.store(O+tl.zeros((BLOCK,),tl.int32),value,mask=valid&(i==N-1)&(j==M-1))
        prev2=prev
        prev=value


@triton.jit
def _backward(P,GO,GC,N:tl.constexpr,M:tl.constexpr,BLOCK:tl.constexpr):
    j=tl.arange(0,BLOCK);jp=tl.minimum(j+1,BLOCK-1)
    nxt=tl.zeros((BLOCK,),tl.float64)
    nxt2=tl.zeros((BLOCK,),tl.float64)
    scale=tl.load(GO)
    for step in range(N+M-1):
        i=N+M-2-step-j;valid=(j<M)&(i>=0)&(i<N)
        down=tl.load(P+(i+1)*M+j,mask=valid&(i+1<N),other=0.)*nxt
        right=tl.load(P+N*M+i*M+j+1,mask=valid&(j+1<M),other=0.)*tl.gather(nxt,jp,axis=0)
        diagonal=tl.load(P+2*N*M+(i+1)*M+j+1,mask=valid&(i+1<N)&(j+1<M),other=0.)*tl.gather(nxt2,jp,axis=0)
        value=tl.where(valid,down+right+diagonal,0.)
        value=tl.where(valid&(i==N-1)&(j==M-1),scale,value)
        tl.store(GC+i*M+j,value,mask=valid)
        nxt2=nxt
        nxt=value


class _SoftDtw(torch.autograd.Function):
    @staticmethod
    def forward(ctx,cost,gamma):
        n,m=cost.shape;block=triton.next_power_of_2(m);warps=8 if block>=256 else 4
        p=torch.empty((3,n,m),device=cost.device,dtype=cost.dtype);out=torch.empty((),device=cost.device,dtype=cost.dtype)
        g=cost.new_tensor(gamma)
        _forward[(1,)](cost,p,out,g,N=n,M=m,BLOCK=block,num_warps=warps)
        ctx.save_for_backward(p);ctx.shape=(n,m);ctx.block=block;ctx.warps=warps
        return out
    @staticmethod
    @torch.autograd.function.once_differentiable
    def backward(ctx,gradient):
        p,=ctx.saved_tensors;n,m=ctx.shape;out=torch.empty((n,m),device=p.device,dtype=p.dtype)
        _backward[(1,)](p,gradient.contiguous(),out,N=n,M=m,BLOCK=ctx.block,num_warps=ctx.warps)
        return out,None


def soft_dtw(cost,*,gamma):
    if (not isinstance(cost,torch.Tensor)or cost.ndim!=2 or cost.device.type!='cuda'or cost.dtype!=torch.float64
            or not cost.is_contiguous()or min(cost.shape)<1 or max(cost.shape)>1024
            or type(gamma)not in(int,float)or not math.isfinite(gamma)or gamma<=0
            or not bool(torch.isfinite(cost).all())):
        raise ValueError('contiguous finite CUDA FP64 matrix1..1024 and positive gamma required')
    return _SoftDtw.apply(cost,float(gamma))
