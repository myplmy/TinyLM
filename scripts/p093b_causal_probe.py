"""Small controlled forward interventions; no checkpoint/data IO or training."""
from __future__ import annotations
from contextlib import contextmanager, nullcontext
from pathlib import Path
import sys
import math
import random
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def history_controls(anchor, body, *, seed=1337):
    if not anchor or not body or len(body) < 1:
        raise ValueError("nonempty fixed anchor/history required")
    shuffled = list(body[:-1])
    random.Random(seed).shuffle(shuffled)
    shuffled.append(body[-1])
    distinct = list(dict.fromkeys(anchor))
    if len(distinct) < 2:
        raise ValueError("prompt-token foil requires at least two token types")
    cycle = [distinct[i % len(distinct)] for i in range(len(body) - 1)] + [body[-1]]
    return {"observed": list(anchor) + list(body),
            "order_shuffle": list(anchor) + shuffled,
            "prompt_cycle": list(anchor) + cycle}


def output_metrics(logits, focus, eos, decode):
    x = logits.detach().float().cpu().flatten()
    if not torch.isfinite(x).all() or not 0 <= focus < x.numel() or not 0 <= eos < x.numel():
        raise ValueError("finite logits and valid preregistered token IDs required")
    p = x.softmax(-1)
    other = x.clone(); other[focus] = -float("inf")
    best = int(x.argmax())
    return {"argmax_id": best, "argmax_text": decode([best]),
            "focus_id": focus, "focus_text": decode([focus]), "focus_logit": float(x[focus]),
            "focus_probability": float(p[focus]), "eos_logit": float(x[eos]),
            "eos_probability": float(p[eos]), "focus_minus_eos_logit": float(x[focus] - x[eos]),
            "focus_minus_best_other_logit": float(x[focus] - other.max()),
            "entropy_nats": float(-(p * p.clamp_min(1e-30).log()).sum())}


def patch_effect(patched, receiver, donor):
    effect = patched["focus_minus_eos_logit"] - receiver["focus_minus_eos_logit"]
    gap = donor["focus_minus_eos_logit"] - receiver["focus_minus_eos_logit"]
    return {"delta_focus_minus_eos_logit": effect,
            "delta_focus_probability": patched["focus_probability"] - receiver["focus_probability"],
            "donor_receiver_logit_gap": gap,
            "normalized_recovery": effect / gap if abs(gap) > 1e-6 else None,
            "normalization_scope": "not clamped; small donor-receiver gap is undefined",
            "causal_scope": "effect of this last-position activation intervention, not a unique global cause"}


@contextmanager
def precision(mode):
    if mode not in ("bf16_auto", "bf16_math", "fp32_math"):
        raise ValueError("unregistered precision profile")
    from torch.nn.attention import sdpa_kernel, SDPBackend
    old = torch.backends.cuda.matmul.fp32_precision
    try:
        if mode == "fp32_math":
            torch.backends.cuda.matmul.fp32_precision = "ieee"
        with (sdpa_kernel(SDPBackend.MATH) if mode.endswith("math") else nullcontext()):
            yield
    finally:
        torch.backends.cuda.matmul.fp32_precision = old


@contextmanager
def recurrence(model, repeat):
    if model.training or repeat not in (1., 2.) or model.cfg.train_repeat != 1.:
        raise ValueError("eval-only R1-trained model, explicit R1/R2 required")
    previous = model.cfg.infer_repeat
    try:
        model.cfg.infer_repeat = repeat
        yield
    finally:
        model.cfg.infer_repeat = previous


def controlled_forward(model, ids, *, mode="fp32_math", patches=None):
    if not ids or len(ids) > model.cfg.max_seq_len:
        raise ValueError("bounded nonempty prefix required; never crop")
    if patches and model.visit_schedule() != list(range(len(model.layers))):
        raise ValueError("activation donors only support the pinned single-visit graph")
    device = next(model.parameters()).device
    states, visits, counts, handles = {}, [], {}, []
    def hook(index, out):
        if not isinstance(out, torch.Tensor) or out.ndim != 3:
            raise ValueError("plain residual layer output required")
        occurrence = counts.get(index, 0); counts[index] = occurrence + 1
        visits.append(index)
        key = (index, occurrence)
        if patches and index in patches:
            donor = patches[index]
            if donor.shape != out[0, -1].shape or not torch.isfinite(donor).all():
                raise ValueError("finite aligned last-position donor required")
            out = out.clone()
            out[0, -1] = donor.to(device=out.device, dtype=out.dtype)
        states[key] = out[0, -1].detach().float().cpu().clone()
        return out if patches and index in patches else None
    try:
        for index, layer in enumerate(model.layers):
            handles.append(layer.register_forward_hook(
                lambda _m, _a, out, index=index: hook(index, out)))
        with torch.no_grad(), precision(mode), torch.autocast(device.type, dtype=torch.bfloat16,
                                                              enabled=device.type == "cuda" and mode != "fp32_math"):
            x = torch.tensor([ids], device=device, dtype=torch.long)
            logits = model(x, logits_last_only=True)[0, -1].detach().float().cpu()
    finally:
        for handle in handles:
            handle.remove()
    if visits != model.visit_schedule() or not torch.isfinite(logits).all():
        raise ValueError("actual visits/finite head differ")
    return logits, states, visits


def cache_prefix_pairs(model, prompt, generated, steps, *, mode):
    """Replay fixed already-observed IDs; not a second generation sampler."""
    from tinylm.infer.generate import _pick
    if model.visit_schedule() != list(range(len(model.layers))) or not prompt:
        raise ValueError("pinned R1 graph and prompt required")
    device = next(model.parameters()).device
    past, result = None, []
    with torch.no_grad(), precision(mode):
        for step in range(1, max(steps) + 1):
            actual = prompt if step == 1 else generated[step - 2:step - 1]
            if not actual:
                raise ValueError("fixed source IDs ended before target prefix")
            with torch.autocast(device.type, dtype=torch.bfloat16,
                                enabled=device.type == "cuda" and mode != "fp32_math"):
                logits, past = model(torch.tensor([actual], device=device),
                                     past_kv=past, use_cache=True, logits_last_only=True)
                if step in steps:
                    prefix = prompt + generated[:step - 1]
                    other = model(torch.tensor([prefix], device=device), logits_last_only=True)
                    a, b = logits[0, -1].float().cpu(), other[0, -1].float().cpu()
                    result.append({"step": step, "cached": a, "uncached": b,
                        "cached_id": int(_pick(a[None], 0, 1)), "uncached_id": int(_pick(b[None], 0, 1)),
                        "max_abs": float((a-b).abs().max()), "rms": float((a-b).square().mean().sqrt())})
    return result
