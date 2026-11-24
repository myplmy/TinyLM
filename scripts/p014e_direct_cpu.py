"""CPU-only direct consumption with a pinned local C ABI and bounded workers."""
import ctypes
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import torch
from torch import nn
from scripts import p014e_packed_g128 as reference

ABI=0x50453036


class KernelRuntime:
    def __init__(self,path,sha256,*,workers=4):
        path=Path(path).resolve()
        expected=Path(__file__).resolve().parents[1]/"test_result/evidence/p014e_direct_packed_v1_s1337/cpu_v1/runtime"
        if(not path.is_relative_to(expected) or path.suffix!=".so"
           or hashlib.sha256(path.read_bytes()).hexdigest().upper()!=sha256
           or workers not in (1,4)):
            raise ValueError("explicit owned library/SHA and one or four workers required")
        self.path=path;self.workers=workers;self.closed=False
        self.library=ctypes.CDLL(str(path),mode=ctypes.RTLD_LOCAL)
        self.library.p014e_cpu_abi.argtypes=[];self.library.p014e_cpu_abi.restype=ctypes.c_uint32
        if self.library.p014e_cpu_abi()!=ABI:raise ValueError("packed CPU ABI version mismatch")
        pointer=ctypes.c_void_p;integer=ctypes.c_int64
        self.linear_fn=self.library.p014e_cpu_linear
        self.linear_fn.argtypes=[pointer]*4+[integer]*6;self.linear_fn.restype=ctypes.c_int
        self.lookup_fn=self.library.p014e_cpu_lookup
        self.lookup_fn.argtypes=[pointer]*4+[integer]*4;self.lookup_fn.restype=ctypes.c_int
        self.pool=ThreadPoolExecutor(max_workers=workers,thread_name_prefix="p014e-cpu") if workers>1 else None

    def close(self):
        if self.pool is not None:self.pool.shutdown(wait=True,cancel_futures=False)
        self.closed=True

    def linear(self,op,x):
        m=x.numel()//op.in_f
        output=torch.empty((*x.shape[:-1],op.out_f),dtype=torch.float32)
        total=m*op.out_f
        args=(x.data_ptr(),op.packed_codes.data_ptr(),op.group_scales.data_ptr(),output.data_ptr(),
              m,op.out_f,op.in_f,op.group)
        futures=[];codes=[]
        if self.pool is None:codes=[self.linear_fn(*args,0,total)]
        else:
            try:
                for i in range(self.workers):
                    futures.append(self.pool.submit(self.linear_fn,*args,i*total//self.workers,(i+1)*total//self.workers))
            finally:
                # Every pointer owner remains live until all submitted work has completed.
                codes=[f.result() for f in futures]
        if any(codes):raise ValueError("packed CPU linear rejected ABI input: "+str(codes))
        return output

    def lookup(self,op,ids):
        output=torch.empty((ids.numel(),op.in_f),dtype=torch.float32)
        code=self.lookup_fn(op.packed_codes.data_ptr(),op.group_scales.data_ptr(),ids.data_ptr(),output.data_ptr(),
                            ids.numel(),op.out_f,op.in_f,op.group)
        if code:raise ValueError("packed CPU lookup rejected ABI input: "+str(code))
        return output


class PackedCPUOperator(nn.Module):
    def __init__(self,record,runtime):
        super().__init__()
        if record["codes"].device.type!="cpu":raise ValueError("CPU payload required")
        reference.validate_record(record)
        self.in_f=record["in_features"];self.out_f=record["out_features"];self.group=record["group"]
        self.register_buffer("packed_codes",record["codes"]);self.register_buffer("group_scales",record["scales"])
        self.runtime=runtime;self.eval()

    def train(self,mode=True):
        if mode:raise RuntimeError("packed CPU deployment is inference-only")
        return super().train(False)

    def _check(self,x,lookup=False):
        if torch.is_grad_enabled():raise RuntimeError("packed CPU inference requires no_grad")
        if self.runtime.closed:raise RuntimeError("packed CPU runtime is closed")
        if(x.device.type!="cpu" or not x.is_contiguous() or self.packed_codes.device.type!="cpu"
           or torch.is_autocast_enabled("cpu")):raise ValueError("contiguous CPU inference without autocast required")
        if lookup:
            if(x.dtype!=torch.long or x.ndim!=1 or not 0<x.numel()<=1024
               or not bool(((x>=0)&(x<self.out_f)).all())):raise ValueError("bounded CPU long IDs required")
        elif(x.dtype!=torch.float32 or x.ndim<1 or x.numel()==0 or x.shape[-1]!=self.in_f
             or x.numel()//self.in_f>1024 or not bool(torch.isfinite(x).all())):
            raise ValueError("finite nonempty contiguous FP32 input with exact width required")

    def lookup(self,ids):
        self._check(ids,lookup=True);return self.runtime.lookup(self,ids)

    def forward(self,x,mode_p=None):
        if mode_p is not None:raise ValueError("mode delta is not serialized")
        self._check(x);return self.runtime.linear(self,x)

    def storage_bytes(self):
        return sum({x.untyped_storage().data_ptr():x.untyped_storage().nbytes() for x in self.buffers()}.values())
