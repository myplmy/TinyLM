"""Exact FP32 after-state replay through the existing guarded edit contexts."""
from contextlib import contextmanager,ExitStack
import numpy as np
import torch
from scripts import p108e_io as native
from scripts import p108_weight_space as identity


def two_addends(before,after):
    if(before.dtype!=np.float32 or after.dtype!=np.float32 or before.shape!=after.shape
       or not np.isfinite(before).all()or not np.isfinite(after).all()):
        raise ValueError("same finite native FP32 matrices required")
    first=(after-before).astype(np.float32)
    intermediate=before+first
    second=(after-intermediate).astype(np.float32)
    if not np.isfinite(first).all()or not np.isfinite(second).all():
        raise ValueError("FP32 addends overflow; exact-copy adapter required")
    if not np.array_equal((intermediate+second).view(np.uint32),after.view(np.uint32)):
        raise RuntimeError("two-step native addition did not reconstruct exact after bits")
    return first,second


@contextmanager
def install_after(active,physical,after):
    first={};second={};before={}
    for layer,module in physical.items():
        before[layer]=module.weight.detach().cpu().numpy().copy()
        first[layer],second[layer]=two_addends(before[layer],after[layer])
    proof=dict(format="EXACT_AFTER_TWO_GUARDED_ADDITIONS",primary_receipts=[],correction_receipts=[],
               rounding_correction_values=sum(int(np.sum(delta!=0))for delta in second.values()))
    try:
        with ExitStack()as stack:
            proof["primary_receipts"]=stack.enter_context(native.install(active,physical,first))
            if proof["rounding_correction_values"]:
                proof["correction_receipts"]=stack.enter_context(native.install(active,physical,second))
            for layer,module in physical.items():
                if identity.tensor_sha(module.weight)!=identity.tensor_sha(torch.from_numpy(after[layer])):
                    raise RuntimeError("exact native after-state hash mismatch")
            yield proof
    finally:
        for layer,module in physical.items():
            if identity.tensor_sha(module.weight)!=identity.tensor_sha(torch.from_numpy(before[layer])):
                raise RuntimeError("exact replay did not restore original weight bits")

