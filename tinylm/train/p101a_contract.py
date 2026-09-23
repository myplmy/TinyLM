"""P101A opt-in mathematical contracts for factorized rank expansion and MTP targets."""
from __future__ import annotations

import math
from collections.abc import Mapping

import torch


def expand_factorized(w: torch.Tensor, up: torch.Tensor, extra_rank: int,
                      *, random_std: float = 0.02,
                      generator: torch.Generator | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Return W[V,E+R], U[D,E+R] with identical real-valued input/head maps."""
    if w.ndim != 2 or up.ndim != 2 or w.shape[1] != up.shape[1]:
        raise ValueError("factorized W and U must share the rank dimension")
    if extra_rank < 1 or random_std <= 0:
        raise ValueError("extra rank and random_std must be positive")
    random_cols = torch.randn(w.shape[0], extra_rank, device=w.device, dtype=w.dtype,
                              generator=generator) * random_std
    zero_cols = torch.zeros(up.shape[0], extra_rank, device=up.device, dtype=up.dtype)
    return torch.cat((w, random_cols), dim=1), torch.cat((up, zero_cols), dim=1)



def migrate_p101a_state(source: Mapping[str, torch.Tensor],
                        target: Mapping[str, torch.Tensor], *, seed: int = 101,
                        random_std: float = 0.02) -> dict[str, torch.Tensor]:
    """Build an exact-key state for E expansion and optional QK gain.

    Input must be an already prefix-stripped old checkpoint state. This changes
    neither the checkpoint nor the default model path. The returned mapping is
    meant for a subsequent strict load into the target model.
    """
    if not isinstance(seed, int) or seed < 0 or not 0 < random_std < 1:
        raise ValueError("invalid P101A migration seed or initialization scale")
    weight_keys = {"emb.weight", "emb_up.weight"}
    if not weight_keys.issubset(source) or not weight_keys.issubset(target):
        raise ValueError("P101A requires factorized embedding and projection")
    gain_keys = {key for key in target if key.endswith(".qk_gain_logit")}
    missing = set(target) - set(source)
    unexpected = set(source) - set(target)
    if unexpected or (missing and missing != gain_keys):
        raise ValueError(f"unexpected/missing migration keys: {sorted(unexpected)} / {sorted(missing)}")
    if gain_keys and missing not in (set(), gain_keys):
        raise ValueError("partial QK gain migration is forbidden")
    w, up = source["emb.weight"], source["emb_up.weight"]
    tw, tup = target["emb.weight"], target["emb_up.weight"]
    if w.dtype != torch.float32 or up.dtype != torch.float32:
        raise ValueError("P101A checkpoint migration requires FP32 master weights")
    if w.ndim != 2 or up.ndim != 2 or tw.ndim != 2 or tup.ndim != 2:
        raise ValueError("factorized embedding parameters must be matrices")
    if w.shape[0] != tw.shape[0] or up.shape[0] != tup.shape[0]:
        raise ValueError("vocabulary or model dimension changed")
    if w.shape[1] != up.shape[1] or tw.shape[1] != tup.shape[1]:
        raise ValueError("embedding/projection rank mismatch")
    extra_rank = tw.shape[1] - w.shape[1]
    if extra_rank < 0:
        raise ValueError("rank reduction is not a P101A migration")
    out = dict(source)
    if extra_rank:
        generator = torch.Generator(device=w.device).manual_seed(seed)
        out["emb.weight"], out["emb_up.weight"] = expand_factorized(
            w, up, extra_rank, random_std=random_std, generator=generator)
    for key in gain_keys:
        if key in missing:
            initial = target[key]
            expected = math.log(1.0 / 6.0)
            if initial.ndim != 1 or not torch.allclose(
                    initial.float(), torch.full_like(initial.float(), expected), atol=1e-6, rtol=0):
                raise ValueError(f"QK gain is not initialized at tau=1: {key}")
            out[key] = initial.detach().clone().to(device=w.device)
    for key, value in out.items():
        if not isinstance(value, torch.Tensor) or value.shape != target[key].shape:
            raise ValueError(f"migration tensor shape mismatch: {key}")
    if set(out) != set(target):
        raise ValueError("migration did not produce the exact target key set")
    return out

def mtp_targets_from_xy(x: torch.Tensor, y: torch.Tensor, horizon: int,
                        *, eos_id: int | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    """Return horizon-k targets and same-document mask from legacy S+1 crop.

    Position t uses only hidden at t to predict raw[t+k]. The EOS target itself
    is permitted; any EOS strictly between source and target invalidates it.
    This is a pretraining contract, not an assistant-message SFT mask.
    """
    if x.ndim != 2 or y.shape != x.shape or horizon < 1 or horizon > x.shape[1]:
        raise ValueError("x/y must be aligned [B,S] with 1 <= horizon <= S")
    if not torch.equal(x[:, 1:], y[:, :-1]):
        raise ValueError("x/y are not an S+1 next-token crop")
    raw = torch.cat((x[:, :1], y), dim=1)
    width = raw.shape[1] - horizon
    target = raw[:, horizon:]
    valid = torch.ones_like(target, dtype=torch.bool)
    if eos_id is not None:
        eos = (raw == eos_id).to(torch.long)
        before = eos.cumsum(dim=1) - eos
        valid = before[:, :width] == before[:, horizon:]
    return target, valid
