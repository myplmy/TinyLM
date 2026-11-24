"""Inference-only CUDA consumption of the existing five-trit original scales.

No alternate quantizer, float master, unpacked matrix cache, or silent fallback.
The decoder handles group-local padding rather than treating rows as one stream.
"""
import torch
from torch import nn
import triton
import triton.language as tl
from scripts import p014e_packed_g128 as reference


@triton.jit
def _power3(position):
    return tl.where(position==0,1,tl.where(position==1,3,tl.where(position==2,9,tl.where(position==3,27,81))))


@triton.jit
def _lookup_kernel(CODES,SCALES,IDS,Y,K:tl.constexpr,G:tl.constexpr,
                   GROUPS:tl.constexpr,BYTES:tl.constexpr,BLOCK:tl.constexpr):
    case=tl.program_id(0);block=tl.program_id(1)
    index=tl.load(IDS+case);column=block*BLOCK+tl.arange(0,BLOCK)
    group=column//G;within=column%G
    byte=tl.load(CODES+index*GROUPS*BYTES+group*BYTES+within//5,mask=column<K,other=121).to(tl.int32)
    trit=(byte//_power3(within%5))%3-1
    scale=tl.load(SCALES+index*GROUPS+group,mask=column<K,other=0.)
    tl.store(Y+case*K+column,trit.to(tl.float32)*scale,mask=column<K)


@triton.jit
def _linear_kernel(X,CODES,SCALES,Y,N:tl.constexpr,K:tl.constexpr,G:tl.constexpr,
                   GROUPS:tl.constexpr,BYTES:tl.constexpr,BLOCK:tl.constexpr):
    row=tl.program_id(0);case=tl.program_id(1);column=tl.arange(0,BLOCK)
    group=column//G;within=column%G
    byte=tl.load(CODES+row*GROUPS*BYTES+group*BYTES+within//5,mask=column<K,other=121).to(tl.int32)
    trit=(byte//_power3(within%5))%3-1
    scale=tl.load(SCALES+row*GROUPS+group,mask=column<K,other=0.)
    x=tl.load(X+case*K+column,mask=column<K,other=0.)
    result=tl.sum(x*(trit.to(tl.float32)*scale),axis=0)
    tl.store(Y+case*N+row,result)


class DirectPackedOperator(nn.Module):
    def __init__(self,record,*,device="cuda"):
        super().__init__()
        if record["codes"].device.type!="cpu":raise ValueError("validate immutable payload on CPU before transfer")
        reference.validate_record(record)
        self.in_f=record["in_features"];self.out_f=record["out_features"];self.group=record["group"]
        self.register_buffer("packed_codes",record["codes"].to(device))
        self.register_buffer("group_scales",record["scales"].to(device))
        self.eval()

    def train(self,mode=True):
        if mode:raise RuntimeError("direct packed deployment is inference-only")
        return super().train(False)

    def _check(self,x,*,lookup=False):
        if torch.is_grad_enabled():raise RuntimeError("direct packed inference needs no_grad or inference_mode")
        if(self.packed_codes.device.type!="cuda" or x.device!=self.packed_codes.device
           or not self.packed_codes.is_contiguous() or not self.group_scales.is_contiguous()):
            raise ValueError("real contiguous CUDA payload and colocated input required")
        if torch.is_autocast_enabled("cuda"):raise ValueError("autocast is an unverified route")
        if lookup:
            if x.dtype!=torch.long or x.ndim!=1 or x.numel()==0 or x.numel()>1024:
                raise ValueError("bounded nonempty one-dimensional long IDs required")
            if not bool(((x>=0)&(x<self.out_f)).all()):raise ValueError("lookup IDs outside real vocabulary")
        elif(x.dtype!=torch.float32 or x.ndim<1 or x.shape[-1]!=self.in_f or x.numel()==0
             or not bool(torch.isfinite(x).all())):
            raise ValueError("finite nonempty FP32 activation with exact input width required")

    def lookup(self,ids):
        self._check(ids,lookup=True);ids=ids.contiguous()
        result=torch.empty((ids.numel(),self.in_f),device=ids.device,dtype=torch.float32)
        _lookup_kernel[(ids.numel(),triton.cdiv(self.in_f,256))](self.packed_codes,self.group_scales,ids,result,
            self.in_f,self.group,self.in_f//self.group,(self.group+4)//5,BLOCK=256,
            num_warps=4,enable_fp_fusion=False)
        return result

    def forward(self,x,mode_p=None):
        if mode_p is not None:raise ValueError("mode-dependent delta is not serialized")
        self._check(x);x2=x.reshape(-1,self.in_f).contiguous()
        result=torch.empty((x2.shape[0],self.out_f),device=x.device,dtype=torch.float32)
        block=triton.next_power_of_2(self.in_f)
        _linear_kernel[(self.out_f,x2.shape[0])](x2,self.packed_codes,self.group_scales,result,
            self.out_f,self.in_f,self.group,self.in_f//self.group,(self.group+4)//5,
            BLOCK=block,num_warps=4 if block<=1024 else 8,enable_fp_fusion=False)
        return result.reshape(*x.shape[:-1],self.out_f)

    def storage_bytes(self):
        tensors={v.untyped_storage().data_ptr():v.untyped_storage().nbytes() for v in self.buffers()}
        return sum(tensors.values())
