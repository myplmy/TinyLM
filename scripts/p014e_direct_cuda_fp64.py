"""Same five-trit/scales and FP32 output, with a separate FP64 dot accumulator."""
import torch
import triton
import triton.language as tl
from scripts import p014e_direct_cuda as original


@triton.jit
def _linear64(X,CODES,SCALES,Y,N:tl.constexpr,K:tl.constexpr,G:tl.constexpr,
              GROUPS:tl.constexpr,BYTES:tl.constexpr,BLOCK:tl.constexpr):
    row=tl.program_id(0);case=tl.program_id(1);column=tl.arange(0,BLOCK)
    group=column//G;within=column%G
    byte=tl.load(CODES+row*GROUPS*BYTES+group*BYTES+within//5,mask=column<K,other=121).to(tl.int32)
    trit=(byte//original._power3(within%5))%3-1
    scale=tl.load(SCALES+row*GROUPS+group,mask=column<K,other=0.)
    x=tl.load(X+case*K+column,mask=column<K,other=0.)
    weight=trit.to(tl.float32)*scale
    result=tl.sum(x.to(tl.float64)*weight.to(tl.float64),axis=0)
    tl.store(Y+case*N+row,result.to(tl.float32))


class FP64DirectBodyOperator(original.DirectPackedOperator):
    def forward(self,x,mode_p=None):
        if mode_p is not None:raise ValueError("mode-dependent delta is not serialized")
        if self.group!=128:raise ValueError("separate FP64 body route supports only original G128")
        self._check(x);x2=x.reshape(-1,self.in_f).contiguous()
        result=torch.empty((x2.shape[0],self.out_f),device=x.device,dtype=torch.float32)
        block=triton.next_power_of_2(self.in_f)
        _linear64[(self.out_f,x2.shape[0])](x2,self.packed_codes,self.group_scales,result,
            self.out_f,self.in_f,self.group,self.in_f//self.group,(self.group+4)//5,
            BLOCK=block,num_warps=4 if block<=1024 else 8,enable_fp_fusion=False)
        self.forward_calls=getattr(self,"forward_calls",0)+1
        return result.reshape(*x.shape[:-1],self.out_f)
