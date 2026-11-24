"""Keep G4 activation statistics in FP32 while fusing elementwise GPU work."""

from contextlib import ExitStack
from unittest.mock import patch

import torch
from torch.autograd.function import once_differentiable
import triton
import triton.language as tl

from tinylm.model import modules


@triton.jit
def row_read(source, row, col, heads: tl.constexpr, time: tl.constexpr,
             sb: tl.constexpr, sh: tl.constexpr, st: tl.constexpr, cols: tl.constexpr, rows: tl.constexpr):
    batch = row // (heads * time)
    head = row // time % heads
    position = row % time
    return tl.load(source + batch*sb + head*sh + position*st + col,
                   (col < cols) & (row < rows), 0).to(tl.float32)


@triton.jit
def rms_fwd(source, output, inverse, heads: tl.constexpr, time: tl.constexpr,
            sb: tl.constexpr, sh: tl.constexpr, st: tl.constexpr,
            cols: tl.constexpr, rows: tl.constexpr, width: tl.constexpr,
            block_rows: tl.constexpr, epsilon: tl.constexpr):
    row = tl.program_id(0)*block_rows + tl.arange(0, block_rows)
    col = tl.arange(0, width)[None, :]
    x = row_read(source, row[:, None], col, heads, time, sb, sh, st, cols, rows)
    inv = tl.rsqrt(tl.sum(x*x, 1) / cols + epsilon)
    inv_cast = inv.to(source.dtype.element_ty).to(tl.float32)
    tl.store(output + row[:, None]*cols + col, x * inv_cast[:, None],
             (col < cols) & (row[:, None] < rows))
    tl.store(inverse + row, inv, row < rows)


@triton.jit
def rms_bwd(source, gradient, inverse, output, heads: tl.constexpr, time: tl.constexpr,
            sb: tl.constexpr, sh: tl.constexpr, st: tl.constexpr,
            gb: tl.constexpr, gh: tl.constexpr, gt: tl.constexpr,
            cols: tl.constexpr, rows: tl.constexpr, width: tl.constexpr, block_rows: tl.constexpr):
    row = tl.program_id(0)*block_rows + tl.arange(0, block_rows)
    col = tl.arange(0, width)[None, :]
    x = row_read(source, row[:, None], col, heads, time, sb, sh, st, cols, rows)
    dy = row_read(gradient, row[:, None], col, heads, time, gb, gh, gt, cols, rows)
    dtype = source.dtype.element_ty
    inv = tl.load(inverse + row, row < rows, 0)
    inv_cast = inv.to(dtype).to(tl.float32)
    d_scale = tl.sum((dy*x).to(dtype).to(tl.float32), 1).to(dtype).to(tl.float32)
    correction = ((-0.5 * d_scale * inv * inv * inv / cols)[:, None] * (2.0*x)).to(dtype).to(tl.float32)
    direct = (dy * inv_cast[:, None]).to(dtype).to(tl.float32)
    tl.store(output + row[:, None]*cols + col, direct + correction, (col < cols) & (row[:, None] < rows))


def heads_view(x):
    return x.unsqueeze(1) if x.ndim == 3 else x


class RMS(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, epsilon):
        rows = heads_view(x)
        batch, heads, time, cols = rows.shape
        inv = rows.new_empty(batch*heads*time, dtype=torch.float32)
        y = torch.empty(x.shape, device=x.device, dtype=x.dtype)
        group = 8 if cols <= 128 else 1
        rms_fwd[(triton.cdiv(inv.numel(), group),)](rows, y, inv, heads, time, *rows.stride()[:3],
                cols, inv.numel(), triton.next_power_of_2(cols), group, epsilon,
                num_warps=4, enable_fp_fusion=False)
        ctx.save_for_backward(rows, inv)
        return y

    @staticmethod
    @once_differentiable
    def backward(ctx, dy):
        rows, inv = ctx.saved_tensors
        gradient = heads_view(dy)
        if gradient.stride(-1) != 1:
            gradient = gradient.contiguous()
        _, heads, time, cols = rows.shape
        y = torch.empty(dy.shape, device=dy.device, dtype=dy.dtype)
        group = 8 if cols <= 128 else 1
        rms_bwd[(triton.cdiv(inv.numel(), group),)](rows, gradient, inv, y, heads, time, *rows.stride()[:3],
                *gradient.stride()[:3], cols, inv.numel(), triton.next_power_of_2(cols), group,
                num_warps=4, enable_fp_fusion=False)
        return y, None


@triton.jit
def rotate(source, cos, sin, output, rows: tl.constexpr, heads: tl.constexpr, time: tl.constexpr,
           sb: tl.constexpr, sh: tl.constexpr, st: tl.constexpr, cs: tl.constexpr, ss: tl.constexpr,
           half: tl.constexpr, width: tl.constexpr, inverse: tl.constexpr):
    index = tl.program_id(0)*width + tl.arange(0, width)
    row, j = index // half, index % half
    offset = row//(heads*time)*sb + row//time%heads*sh + row%time*st + j
    a = tl.load(source + offset, row < rows, 0).to(tl.float32)
    b = tl.load(source + offset + half, row < rows, 0).to(tl.float32)
    cosine = tl.load(cos + row%time*cs + j, row < rows, 0)
    sine = tl.load(sin + row%time*ss + j, row < rows, 0)
    if inverse:
        result1, result2 = a*cosine + b*sine, b*cosine - a*sine
    else:
        result1, result2 = a*cosine - b*sine, a*sine + b*cosine
    tl.store(output + row*(2*half) + j, result1, row < rows)
    tl.store(output + row*(2*half) + j+half, result2, row < rows)


def rotation(x, cos, sin, inverse):
    if x.stride(-1) != 1:
        x = x.contiguous()
    batch, heads, time, width = x.shape
    y = torch.empty_like(x, memory_format=torch.contiguous_format)
    rows = batch*heads*time
    rotate[(triton.cdiv(rows*width//2, 512),)](x, cos, sin, y, rows, heads, time, *x.stride()[:3],
                                              cos.stride(0), sin.stride(0), width//2, 512, inverse,
                                              num_warps=4, enable_fp_fusion=False)
    return y


class RoPE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, cos, sin):
        ctx.save_for_backward(cos, sin)
        return rotation(x, cos, sin, False)

    @staticmethod
    @once_differentiable
    def backward(ctx, dy):
        cos, sin = ctx.saved_tensors
        return rotation(dy, cos, sin, True), None, None


@triton.jit
def swiglu(gate, up, upstream, output, grad_up, elements: tl.constexpr,
           width: tl.constexpr, backward: tl.constexpr):
    index = tl.program_id(0)*width + tl.arange(0, width)
    mask = index < elements
    g = tl.load(gate+index, mask, 0).to(tl.float32)
    u = tl.load(up+index, mask, 0).to(tl.float32)
    sigmoid = tl.sigmoid(g)
    dtype = gate.dtype.element_ty
    silu = (g*sigmoid).to(dtype).to(tl.float32)
    if backward:
        dy = tl.load(upstream+index, mask, 0).to(tl.float32)
        ds = (dy*u).to(dtype).to(tl.float32)
        tl.store(grad_up+index, dy*silu, mask)
        value = ds*sigmoid*(1.0+g*(1.0-sigmoid))
    else:
        value = silu*u
    tl.store(output+index, value, mask)


class SwiGLU(torch.autograd.Function):
    @staticmethod
    def forward(ctx, gate, up):
        y = torch.empty_like(gate)
        swiglu[(triton.cdiv(gate.numel(), 512),)](gate, up, y, y, y, gate.numel(), 512, False,
                                                num_warps=4, enable_fp_fusion=False)
        ctx.save_for_backward(gate, up)
        return y

    @staticmethod
    @once_differentiable
    def backward(ctx, dy):
        gate, up = ctx.saved_tensors
        dg, du = torch.empty_like(gate), torch.empty_like(up)
        swiglu[(triton.cdiv(gate.numel(), 512),)](gate, up, dy.contiguous(), dg, du, gate.numel(), 512, True,
                                                num_warps=4, enable_fp_fusion=False)
        return dg, du


def fused_operations():
    """Use the three primitives only for the compatible diagnostic G4 route."""
    original_rms = modules.RMSNorm.forward
    original_rope = modules.apply_rope
    original_mlp = modules.MLP.forward

    def rms(layer, x):
        if x.is_cuda and x.ndim in (3, 4) and x.stride(-1) == 1:
            return RMS.apply(x, layer.eps)
        return original_rms(layer, x)

    def rope(x, cos, sin):
        if x.is_cuda and not (cos.requires_grad or sin.requires_grad):
            return RoPE.apply(x, cos, sin)
        return original_rope(x, cos, sin)

    def mlp(layer, x, mode, lora=None, film=None, lrm=None):
        if (x.is_cuda and not layer.gate_proj.cfg.x2_active_tiles and mode is None
                and lora is None and film is None and lrm is None):
            gate, up = layer.gate_proj(x), layer.up_proj(x)
            return layer.down_proj(SwiGLU.apply(gate, up))
        return original_mlp(layer, x, mode, lora, film, lrm)

    patches = ExitStack()
    patches.enter_context(patch.object(modules.RMSNorm, "forward", rms))
    patches.enter_context(patch.object(modules, "apply_rope", rope))
    patches.enter_context(patch.object(modules.MLP, "forward", mlp))
    return patches
