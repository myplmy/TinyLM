#!/usr/bin/env python3
"""P103A frozen-boundary dependency contract without TinyLM model loading."""
from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tinylm.train.p103a_model_boundary import freeze_lower_dependency, validate_frozen_split


class Parameter:
    def __init__(self):
        self.requires_grad = True


class Module:
    def __init__(self):
        self.params = [Parameter()]

    def parameters(self):
        return iter(self.params)

    def requires_grad_(self, enabled):
        for param in self.params:
            param.requires_grad = enabled
        return self


class Layer(Module):
    def __init__(self, mlp):
        super().__init__()
        self.mlp = [mlp]  # Deliberately unregistered, as in TinyLM Layer.


def fixture(shared=False, tied=False):
    low_mlp, high_mlp = Module(), Module()
    if shared:
        high_mlp = low_mlp
    cfg = SimpleNamespace(
        n_layers=2, tie_mlp=tied, n_modes=1, attn_group=1,
        grad_checkpoint=False, use_ternary_kernel=False,
        train_repeat=1.0, infer_repeat=1.0,
        repeat_embed_reinject=False, reuse_attn_on_dup=False,
        mlp_lora_rank=0, mlp_film=False, mlp_lrm=False,
        x2_active_tiles=(),
    )
    model = SimpleNamespace(cfg=cfg, owner=[0, 1], emb=Module(),
                            emb_up=Module(), layers=[Layer(low_mlp), Layer(high_mlp)])
    return model, low_mlp, high_mlp


def main():
    model, lower, upper = fixture()
    freeze_lower_dependency(model, 1)
    validate_frozen_split(model, 1)
    if (any(p.requires_grad for p in lower.parameters())
            or not all(p.requires_grad for p in upper.parameters())
            or not all(p.requires_grad for p in model.layers[1].parameters())):
        raise RuntimeError("P103A lower/upper MLP freeze ownership differs")
    model, _, _ = fixture(shared=True)
    try:
        freeze_lower_dependency(model, 1)
    except ValueError as exc:
        if "shared" not in str(exc):
            raise
    else:
        raise RuntimeError("P103A shared lower/upper MLP was accepted")
    model, _, _ = fixture(tied=True)
    try:
        freeze_lower_dependency(model, 1)
    except ValueError:
        pass
    else:
        raise RuntimeError("P103A tied MLP boundary was accepted")
    print("[PASS] P103A lower MLP reference freeze and shared-boundary rejection; model/GPU NOT_RUN")


if __name__ == "__main__":
    main()
