"""Native rival-margin VJPs projected into declared matrix coordinates."""
from __future__ import annotations
import numpy as np
import torch


def projected_vjps(logits,gold,weights,rights,*,lefts=None):
    if logits.ndim!=2 or len(gold)!=len(logits) or set(weights)!=set(rights):
        raise ValueError("complete logits, target IDs and identical physical owners required")
    gold=torch.as_tensor(gold,device=logits.device,dtype=torch.long)
    detached=logits.detach().clone();detached[torch.arange(len(gold),device=gold.device),gold]=-torch.inf
    rivals=detached.argmax(-1)
    margins=logits[torch.arange(len(gold),device=gold.device),gold]-logits[
        torch.arange(len(gold),device=gold.device),rivals]
    ordered=sorted(weights);parameters=[weights[layer]for layer in ordered]
    if any(not weight.requires_grad or weight.grad is not None for weight in parameters):
        raise ValueError("native differentiable weights and empty persistent .grad required")
    right_gpu={layer:torch.as_tensor(rights[layer],device=weights[layer].device,dtype=torch.float64)
               for layer in ordered}
    left_gpu=None if lefts is None else {layer:torch.as_tensor(lefts[layer],device=weights[layer].device,
               dtype=torch.float64)for layer in ordered}
    blocks={layer:[]for layer in ordered};norms={layer:[]for layer in ordered}
    for position in range(len(gold)):
        gradients=torch.autograd.grad(margins[position],parameters,retain_graph=position+1<len(gold))
        for layer,gradient in zip(ordered,gradients):
            if not bool(torch.isfinite(gradient).all()):raise RuntimeError("non-finite native margin derivative")
            wide=gradient.detach().double()
            projected=wide@right_gpu[layer].T
            right_energy=float(projected.square().sum())
            if left_gpu is not None:projected=left_gpu[layer].T@projected
            blocks[layer].append(projected.cpu().numpy().copy())
            norms[layer].append(dict(native_energy=float(wide.square().sum()),right_energy=right_energy,
                                      final_energy=float(projected.square().sum())))
            projected=wide=None
        gradients=None
    if any(weight.grad is not None for weight in parameters):raise RuntimeError("VJP accumulated parameter .grad")
    return {layer:np.stack(blocks[layer])for layer in ordered},dict(
        gold=gold.detach().cpu().tolist(),rivals=rivals.detach().cpu().tolist(),
        margins=margins.detach().cpu().tolist(),norms=norms,native_vjp_calls=len(gold))
