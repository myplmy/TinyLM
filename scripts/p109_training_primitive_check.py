"""Compare the experimental kernels with their eager forward and input VJPs."""

import torch
from torch.nn import functional as F

from scripts.p109_training_elementwise import RMS, RoPE, SwiGLU
from scripts.p109_training_head import RowLoss
from tinylm.model.modules import apply_rope, build_rope
from tinylm.train.recomputed_ce import _RecomputedNLL


def delta(reference, candidate):
    a, b = reference.detach().float().flatten(), candidate.detach().float().flatten()
    gap = (a - b).abs()
    if not torch.isfinite(gap).all():
        raise ValueError("nonfinite diagnostic kernel output")
    return dict(max_abs=gap.max().item(), rms_relative=(gap.norm()/a.norm().clamp_min(1.e-9)).item(),
                differing=int(torch.count_nonzero(gap).item()), elements=gap.numel())


def compare(native, adjusted, args, upstream):
    a = native(*args)
    b = adjusted(*args)
    da = torch.autograd.grad(a, args, upstream)
    db = torch.autograd.grad(b, args, upstream)
    return dict(output=delta(a, b), gradients=[delta(x, y) for x, y in zip(da, db, strict=True)])


def run():
    gen = torch.Generator(device="cuda").manual_seed(581)

    def rand(shape, dtype):
        return torch.randn(shape, generator=gen, device="cuda", dtype=dtype)

    def rms(x):
        return x * torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + 1e-5).to(x.dtype)

    results = {}
    for dtype in (torch.float32, torch.bfloat16):
        key = str(dtype)
        x = rand((4, 17, 768), dtype).requires_grad_()
        q = rand((2, 33, 12, 64), dtype).transpose(1, 2).requires_grad_()
        cosine, sine = build_rope(64, 33, 10000., device="cuda")
        g, u = (rand((4, 29, 2048), dtype).requires_grad_() for _ in range(2))
        results[key] = dict(residual_rms=compare(rms, lambda a: RMS.apply(a, 1e-5), (x,), rand(x.shape, dtype)),
                            qk_rms=compare(rms, lambda a: RMS.apply(a, 1e-5), (q,), rand(q.shape, dtype)),
                            rope=compare(lambda a: apply_rope(a, cosine, sine),
                                         lambda a: RoPE.apply(a, cosine, sine), (q,), rand(q.shape, dtype)),
                            swiglu=compare(lambda a, b: F.silu(a)*b, SwiGLU.apply, (g, u), rand(g.shape, dtype)))

    x = (rand((128, 256), torch.bfloat16)*.25).requires_grad_()
    table = (rand((32768, 256), torch.bfloat16)*.15).requires_grad_()
    target = torch.randint(32768, (128,), generator=gen, device="cuda")
    target[::7] = -100
    upstream = rand((128,), torch.float32) / 128
    results["row_loss"] = compare(lambda a, b: _RecomputedNLL.apply(a, b, target, 32),
                                  lambda a, b: RowLoss.apply(a, b, target, True), (x, table), upstream)
    ignored = RowLoss.apply(x, table, target, True)[target == -100]
    results["row_loss"]["masked_values_zero"] = bool(torch.all(ignored == 0))
    if not results["row_loss"]["masked_values_zero"]:
        raise ValueError("ignored CE targets acquired a loss")
    return results
