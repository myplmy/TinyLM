"""Exact native FP32 replay, separate FP64 ideal arithmetic and one-shot replacement."""
from contextlib import contextmanager
import torch
from torch.nn import functional as F
from scripts import p108_weight_space as metrics


def packet_from_record(record,weight):
    if weight.ndim!=2 or weight.dtype!=torch.float32 or metrics.tensor_sha(weight)!=record['base_weight_sha256']:
        raise ValueError('exact original FP32 weight required')
    left=torch.tensor(record['left'],dtype=torch.float64);right=torch.tensor(record['right'],dtype=torch.float64)
    if (left.ndim!=2 or right.ndim!=2 or left.shape[1]!=right.shape[1]
            or (left.shape[0],right.shape[0])!=tuple(weight.shape)
            or not bool(torch.isfinite(left).all()) or not bool(torch.isfinite(right).all())):
        raise ValueError('finite frozen packet factor dimensions required')
    delta=(left@right.T).float()
    if metrics.tensor_sha(delta)!=record['delta_sha256']:raise ValueError('original materialized packet bytes changed')
    return delta


def operator_evidence(inputs,before_output,after_output,before_weight,after_weight):
    items=(inputs,before_output,after_output,before_weight,after_weight)
    if any(not isinstance(t,torch.Tensor) or t.dtype!=torch.float32 or not bool(torch.isfinite(t).all()) for t in items):
        raise ValueError('finite original FP32 tensors required')
    if (inputs.ndim<2 or before_weight.ndim!=2 or after_weight.shape!=before_weight.shape
            or inputs.shape[-1]!=before_weight.shape[1] or before_output.shape!=after_output.shape
            or before_output.shape!=inputs.shape[:-1]+(before_weight.shape[0],)
            or len({t.device for t in items})!=1 or not inputs.is_contiguous()):
        raise ValueError('same contiguous native input/output/weight shapes and device required')
    with torch.no_grad(),torch.autocast(device_type=inputs.device.type,enabled=False):
        replay_before=F.linear(inputs,before_weight);replay_after=F.linear(inputs,after_weight)
    wb=before_weight.detach().cpu();wa=after_weight.detach().cpu();x=inputs.detach().cpu().reshape(-1,inputs.shape[-1])[-1].double()
    yb=before_output.detach().cpu().reshape(-1,before_weight.shape[0])[-1].double()
    ya=after_output.detach().cpu().reshape(-1,before_weight.shape[0])[-1].double()
    delta_double=(wa.double()-wb.double())@x
    old_pred=(wa-wb).double()@x
    double_before=wb.double()@x;double_after=wa.double()@x
    observed=ya-yb;roundoff=observed-delta_double;weight_roundoff=delta_double-old_pred
    old_close=torch.isclose(observed,old_pred,atol=1e-5,rtol=1e-4)
    return dict(native_before_exact=torch.equal(replay_before,before_output),
        native_after_exact=torch.equal(replay_after,after_output),
        before_replay_max_abs=float((replay_before-before_output).abs().max()),
        after_replay_max_abs=float((replay_after-after_output).abs().max()),
        double_linearity_close=bool(torch.allclose(double_after-double_before,delta_double,atol=1e-10,rtol=1e-10)),
        double_linearity_max_abs=float((double_after-double_before-delta_double).abs().max()),
        original_gate_close=bool(old_close.all()),original_gate_outside=int((~old_close).sum()),
        original_gate_max_abs=float((observed-old_pred).abs().max()),original_atol=1e-5,original_rtol=1e-4,
        fp32_forward_roundoff_max_abs=float(roundoff.abs().max()),
        fp32_weight_difference_roundoff_max_abs=float(weight_roundoff.abs().max()),
        decomposition_max_abs=float((observed-old_pred-roundoff-weight_roundoff).abs().max()))


def require_operator(evidence):
    if not all(evidence[k] for k in ('native_before_exact','native_after_exact','double_linearity_close')):
        raise RuntimeError('actual native operator or independent FP64 linearity is inconsistent')


@contextmanager
def replace_once(module,target):
    if not isinstance(target,torch.Tensor) or target.ndim!=1 or target.dtype!=torch.float32 or not bool(torch.isfinite(target).all()):
        raise ValueError('one observed FP32 output row required')
    state=dict(fires=0);failed=False
    def hook(_module,_args,output):
        if state['fires']:return None
        if output.ndim!=3 or output.shape[0]!=1 or output.shape[-1]!=len(target) or output.dtype!=torch.float32:
            raise ValueError('same batch-one native prefill output width/dtype required')
        result=output.clone();result[0,-1]=target.to(result);state['fires']+=1;return result
    handle=module.register_forward_hook(hook)
    try:yield state
    except BaseException:failed=True;raise
    finally:
        handle.remove()
        if not failed and state['fires']!=1:raise RuntimeError('replacement must fire exactly once')
