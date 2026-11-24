"""Temporary head/lookup-only integration; keep every body operator unchanged."""
from contextlib import contextmanager
from types import MethodType
from unittest.mock import patch
import torch
from torch.nn import functional as F
from scripts import p014e_packed_g128 as packed
from scripts import interactive_research_infer as identity


@contextmanager
def direct_head(model,operator):
    if(torch.is_grad_enabled() or not isinstance(model,packed.PackedTransformer)
       or not isinstance(model.packed_embedding,packed.PackedTernaryTable)):
        raise ValueError("no-grad packed model and original table required")
    table=model.packed_embedding
    if(operator.packed_codes.data_ptr()!=table.packed_codes.data_ptr()
       or operator.group_scales.data_ptr()!=table.group_scales.data_ptr()):
        raise ValueError("head operator must alias the existing packed buffers")
    original_head=model._head_logits.__func__;original_rows=table.rows.__func__
    body_owners=[id(m) for m in model.modules() if isinstance(m,packed.PackedGroupLinear)]
    before=identity.state_fingerprint(model);keys=tuple(model.state_dict())
    proof=dict(original_state_sha256=before,body_physical_owners=len(body_owners),
               extra_GPU_weight_storage_bytes=0,head_lookup_only=True,restored=False)
    def head(this,x):
        if this.emb_up is not None:x=F.linear(x,this._emb_up_w().t())
        return operator(x)
    def rows(this,indices):
        if isinstance(indices,slice):
            start,stop,step=indices.indices(this.vocab_size)
            if step!=1 or not 0<stop-start<=this.head_rows:raise ValueError("same bounded row-slice policy required")
            indices=torch.arange(start,stop,device=this.packed_codes.device,dtype=torch.long)
        if not isinstance(indices,torch.Tensor):raise ValueError("explicit bounded lookup IDs required")
        return operator.lookup(indices)
    try:
        with patch.object(model,"_head_logits",MethodType(head,model)),patch.object(table,"rows",MethodType(rows,table)):
            yield proof
    finally:
        proof.update(restored=model._head_logits.__func__ is original_head and table.rows.__func__ is original_rows,
            body_owners_unchanged=body_owners==[id(m) for m in model.modules() if isinstance(m,packed.PackedGroupLinear)],
            state_keys_unchanged=keys==tuple(model.state_dict()),final_state_sha256=identity.state_fingerprint(model))
        if(not proof["restored"] or not proof["body_owners_unchanged"] or not proof["state_keys_unchanged"]
           or proof["final_state_sha256"]!=before):raise RuntimeError("head context changed body/storage or failed restoration")
