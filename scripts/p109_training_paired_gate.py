"""Fuse G4 gate/up projections through one per-update quantized weight pair."""

from contextlib import ExitStack
from unittest.mock import patch

import torch
from torch.nn import functional as F
from torch.autograd.function import once_differentiable
import triton
import triton.language as tl

from tinylm.model import modules


@triton.jit
def pair_glu(pair, derivative, output, elements: tl.constexpr,
             columns: tl.constexpr, width: tl.constexpr, backward: tl.constexpr):
    index = tl.program_id(0)*width + tl.arange(0, width)
    mask = index < elements
    pos = index//columns*(2*columns) + index%columns
    gate = tl.load(pair+pos, mask, 0).to(tl.float32)
    up = tl.load(pair+pos+columns, mask, 0).to(tl.float32)
    sigmoid = tl.sigmoid(gate)
    dtype = pair.dtype.element_ty
    silu = (gate*sigmoid).to(dtype).to(tl.float32)
    if backward:
        dy = tl.load(derivative+index, mask, 0).to(tl.float32)
        ds = (dy*up).to(dtype).to(tl.float32)
        tl.store(output+pos+columns, dy*silu, mask)
        tl.store(output+pos, ds*sigmoid*(1.+gate*(1.-sigmoid)), mask)
    else:
        tl.store(output+index, silu*up, mask)


class GLU(torch.autograd.Function):
    @staticmethod
    def forward(ctx, pair):
        columns = pair.size(-1)//2
        output = pair.new_empty((*pair.shape[:-1], columns))
        pair_glu[(triton.cdiv(output.numel(), 512),)](pair, output, output, output.numel(), columns, 512,
                                                    False, num_warps=4, enable_fp_fusion=False)
        ctx.save_for_backward(pair)
        return output

    @staticmethod
    @once_differentiable
    def backward(ctx, gradient):
        pair, = ctx.saved_tensors
        output = torch.empty_like(pair)
        pair_glu[(triton.cdiv(gradient.numel(), 512),)](pair, gradient.contiguous(), output, gradient.numel(),
                                                     gradient.size(-1), 512, True, num_warps=4, enable_fp_fusion=False)
        return output


class PairedGates:
    def __init__(self, model):
        if model.cfg.wq_dtype != "bf16" or model.cfg.x2_active_tiles:
            raise ValueError("gated projection pairing needs the full BF16 STE path")
        self.layers = [module for module in model.modules() if isinstance(module, modules.MLP)]
        self.active = {}
        self.begin_native = model.begin_quant_update_cache
        self.finish_native = model.finish_quant_update_cache
        self.abort_native = model.abort_quant_update_cache
        self.model = model

    def begin(self):
        if self.active:
            raise RuntimeError("the former paired projection state has not been finalized")
        self.begin_native()
        try:
            for layer in self.layers:
                gate, up = layer.gate_proj._wq, layer.up_proj._wq
                if gate.shape != up.shape or gate.dtype != torch.bfloat16 or up.dtype != gate.dtype:
                    raise ValueError("paired gates must have the same quantization shape and dtype")
                pair = torch.cat((gate.detach(), up.detach()), dim=0).requires_grad_()
                self.active[layer] = (gate, up, pair)
        except BaseException:
            self.abort()
            raise

    def finish(self):
        for gate, up, pair in self.active.values():
            if pair.grad is None or gate.grad is not None or up.grad is not None:
                raise ValueError("paired projection gradients must own both tied tables")
            gate.grad, up.grad = pair.grad.split(gate.size(0), dim=0)
        self.active.clear()
        self.finish_native()

    def abort(self):
        self.active.clear()
        self.abort_native()

    def patches(self):
        original = modules.MLP.forward

        def apply(layer, x, mode, lora=None, film=None, lrm=None):
            if layer not in self.active:
                return original(layer, x, mode, lora, film, lrm)
            if any(value is not None for value in (mode, lora, film, lrm)):
                raise ValueError("the fused comparison needs the original full shared G4 MLP")
            pair = F.linear(x, self.active[layer][-1])
            return layer.down_proj(GLU.apply(pair))

        patches = ExitStack()
        patches.enter_context(patch.object(modules.MLP, "forward", apply))
        patches.enter_context(patch.object(self.model, "begin_quant_update_cache", self.begin))
        patches.enter_context(patch.object(self.model, "finish_quant_update_cache", self.finish))
        patches.enter_context(patch.object(self.model, "abort_quant_update_cache", self.abort))
        return patches
