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
    aux_keys = set(target).intersection({"mtp_up2", "mtp_up4"})
    if aux_keys and aux_keys != {"mtp_up2", "mtp_up4"}:
        raise ValueError("MTP target must contain both auxiliary heads")
    missing = set(target) - set(source)
    unexpected = set(source) - set(target)
    if unexpected or missing - gain_keys - aux_keys:
        raise ValueError(f"unexpected/missing migration keys: {sorted(unexpected)} / {sorted(missing)}")
    if gain_keys and missing & gain_keys not in (set(), gain_keys):
        raise ValueError("partial QK gain migration is forbidden")
    if aux_keys and missing & aux_keys not in (set(), aux_keys):
        raise ValueError("partial MTP auxiliary migration is forbidden")
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
    if extra_rank and aux_keys and not aux_keys.issubset(missing):
        raise ValueError("rank expansion of an already-MTP checkpoint is unsupported")
    for key in aux_keys & missing:
        # Both independent heads start from the migrated main projection.
        out[key] = out["emb_up.weight"].detach().clone()
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


def mtp_aux_coefficients(update: int, updates: int) -> tuple[float, float]:
    """P101A 5% warmup, 5-80% hold, final 20% decay; endpoints are zero."""
    if updates < 2 or not 0 <= update < updates:
        raise ValueError("invalid MTP update position")
    progress = update / (updates - 1)
    scale = min(1.0, progress / 0.05, (1.0 - progress) / 0.20)
    return 0.20 * scale, 0.10 * scale


def mtp_loss_components(hidden: torch.Tensor, main_up: torch.Tensor,
                        aux2_up: torch.Tensor, aux4_up: torch.Tensor,
                        emb: torch.Tensor, x: torch.Tensor, y: torch.Tensor,
                        *, eos_id: int, chunk: int = 256) -> dict[int, tuple[torch.Tensor, torch.Tensor]]:
    """FP32 loss sums/counts for same-input NTP and horizon-2/4 aux heads.

    The three projection matrices are distinct; the vocabulary table is shared.
    Caller combines sums across every micro-batch before dividing by counts.
    This tensor core is not yet wired to the full TinyLM trainer.
    """
    from .p102a_contract import factorized_ce_loss_first

    if (hidden.ndim != 3 or x.ndim != 2 or y.shape != x.shape
            or hidden.shape[:2] != x.shape or x.shape[1] < 4
            or x.dtype != torch.long or y.dtype != torch.long
            or not isinstance(eos_id, int) or eos_id < 0):
        raise ValueError("MTP requires FP32 hidden and aligned [B,S] integer crop with S>=4")
    if (main_up.ndim != 2 or main_up.shape[0] != hidden.shape[2]
            or aux2_up.shape != main_up.shape or aux4_up.shape != main_up.shape
            or emb.ndim != 2 or emb.shape[1] != main_up.shape[1]):
        raise ValueError("MTP head/embedding dimensions differ")
    if any(value.dtype != torch.float32 for value in
           (hidden, main_up, aux2_up, aux4_up, emb)):
        raise ValueError("MTP tensor core currently requires FP32")
    if aux2_up.data_ptr() in (main_up.data_ptr(), aux4_up.data_ptr()):
        raise ValueError("MTP auxiliary projections must not alias")
    if aux4_up.data_ptr() == main_up.data_ptr():
        raise ValueError("MTP auxiliary projections must not alias")
    sums: dict[int, tuple[torch.Tensor, torch.Tensor]] = {}
    flat_hidden = hidden.reshape(-1, hidden.shape[-1])
    sums[1] = (factorized_ce_loss_first(flat_hidden, main_up, emb,
                                        y.reshape(-1), chunk),
               torch.as_tensor(y.numel(), device=y.device))
    for horizon, projection in ((2, aux2_up), (4, aux4_up)):
        target, valid = mtp_targets_from_xy(x, y, horizon, eos_id=eos_id)
        masked = target.masked_fill(~valid, -100)
        width = target.shape[1]
        loss_sum = factorized_ce_loss_first(
            hidden[:, :width].reshape(-1, hidden.shape[-1]),
            projection, emb, masked.reshape(-1), chunk)
        sums[horizon] = loss_sum, valid.sum()
    return sums


def mtp_weighted_mean(parts: list[dict[int, tuple[torch.Tensor, torch.Tensor]]],
                      lambda2: float, lambda4: float) -> torch.Tensor:
    """Normalize each head by its valid targets over the entire update."""
    if not parts or any(set(item) != {1, 2, 4} for item in parts):
        raise ValueError("MTP update must contain all three heads")
    if not (math.isfinite(lambda2) and math.isfinite(lambda4)
            and 0 <= lambda2 <= 0.20 and 0 <= lambda4 <= 0.10):
        raise ValueError("MTP auxiliary coefficients are out of range")
    totals = {k: sum(item[k][0] for item in parts) for k in (1, 2, 4)}
    counts = {k: sum(item[k][1] for item in parts) for k in (1, 2, 4)}
    # NTP has one target per input position; zero-target crops were rejected.
    return (totals[1] / counts[1]
            + lambda2 * totals[2] / counts[2].clamp_min(1)
            + lambda4 * totals[4] / counts[4].clamp_min(1))
