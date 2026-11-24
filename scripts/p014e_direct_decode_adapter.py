"""Explicit one-row dispatch; multi-row prefill keeps the unchanged reference."""
from contextlib import contextmanager,ExitStack
from types import MethodType
from unittest.mock import patch
import torch
from scripts import p014e_packed_g128 as packed
from scripts import interactive_research_infer as identity


def dispatch(operator,reference,x,mode_p,counts):
    if x.ndim<1 or x.shape[-1]!=operator.in_f or x.numel()==0:raise ValueError("nonempty exact input width required")
    rows=x.numel()//operator.in_f
    if rows==1:
        counts["direct_one_row_calls"]+=1
        return operator(x,mode_p)
    counts["reference_multirow_calls"]+=1
    return reference(x,mode_p)


@contextmanager
def one_row_body(model,pairs):
    if torch.is_grad_enabled() or not isinstance(model,packed.PackedTransformer):
        raise ValueError("no-grad packed model required")
    body=[m for m in model.modules() if isinstance(m,packed.PackedGroupLinear)]
    if len(pairs)!=len(body) or len({id(m) for m,_ in pairs})!=len(pairs) or {id(m) for m,_ in pairs}!={id(m) for m in body}:
        raise ValueError("exact unique physical body-owner coverage required")
    for module,op in pairs:
        if(op.packed_codes.data_ptr()!=module.packed_codes.data_ptr()
           or op.group_scales.data_ptr()!=module.group_scales.data_ptr()
           or (op.in_f,op.out_f,op.group)!=(module.in_f,module.out_f,module.group)):
            raise ValueError("same body shape and aliased packed buffers required")
    original=[(m,m.forward.__func__) for m,_ in pairs];before=identity.state_fingerprint(model)
    keys=tuple(model.state_dict());counts=dict(direct_one_row_calls=0,reference_multirow_calls=0)
    proof=dict(counts=counts,physical_body_owners=len(body),extra_GPU_weight_storage_bytes=0,
               policy="M_EQ1_FP64_DIRECT;M_GT1_ORIGINAL_REFERENCE;NO_ERROR_FALLBACK",restored=False)
    try:
        with ExitStack() as stack:
            for module,op in pairs:
                reference=module.forward
                def forward(this,x,mode_p=None,_operator=op,_reference=reference):
                    return dispatch(_operator,_reference,x,mode_p,counts)
                stack.enter_context(patch.object(module,"forward",MethodType(forward,module)))
            yield proof
    finally:
        proof.update(restored=all(m.forward.__func__ is f for m,f in original),
            state_keys_unchanged=keys==tuple(model.state_dict()),
            physical_state_unchanged=identity.state_fingerprint(model)==before)
        if not proof["restored"] or not proof["state_keys_unchanged"] or not proof["physical_state_unchanged"]:
            raise RuntimeError("body dispatch failed exact restoration")
