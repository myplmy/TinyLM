"""Isolate linear and attention shape effects in G4 cached CPU inference."""

from contextlib import ExitStack, nullcontext
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

import torch
import torch.nn.functional as F
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p108_g4_shared_pack as prior


TAG = "p108_g4_cache_shapes_v1_20261119"
OUT = prior.OUT.parent.with_name(TAG)
PLAN = prior.ROOT / "test_plan/P108_직접가중치-방향수리와-학습개입.md"


def position_linear(native):
    def linear(value, weight, bias=None):
        if value.ndim != 3:
            return native(value, weight, bias)
        return torch.cat([native(token.contiguous(), weight, bias)
                          for token in value.split(1, dim=1)], dim=1)
    return linear


def prefix_attention(native):
    def attention(q, k, v, attn_mask=None, dropout_p=0., is_causal=False, **kwargs):
        assert dropout_p == 0.
        q_len, k_len = q.shape[-2], k.shape[-2]
        previous = k_len - q_len
        assert previous >= 0
        if attn_mask is not None:
            expected = torch.ones((q_len, k_len), dtype=torch.bool, device=q.device).tril(previous)
            assert not is_causal and torch.equal(attn_mask, expected)
        else:
            assert is_causal and previous == 0
        rows = []
        for index in range(q_len):
            stop = previous + index + 1
            rows.append(native(q[..., index:index + 1, :].contiguous(),
                               k[..., :stop, :].contiguous(), v[..., :stop, :].contiguous(),
                               is_causal=False, **kwargs))
        return torch.cat(rows, dim=-2)
    return attention


@torch.no_grad()
def run():
    previous = json.loads(prior.OUT.read_bytes())
    assert previous["checkpoint_sha256"] == prior.PARENT_SHA
    assert prior.PARENT.is_file() and not prior.PARENT.is_symlink()
    assert prior.digest(prior.PARENT) == prior.PARENT_SHA
    sources = {name: prior.digest(prior.ROOT / name) for name in prior.SOURCES}
    plan_sha = prior.digest(PLAN)
    model, step = prior.load_model()
    owner = prior.physical_down_owners(model)[2]
    initial = prior.tensor_sha(owner.module._wq)
    packet, _ = prior.edit_packet(owner.module._wq, model.cfg.micro_group)
    assert packet["target_sha256"] == previous["packet"]["target_sha256"]
    tokens = torch.tensor(previous["prompts"])
    original_linear, original_attention = F.linear, F.scaled_dot_product_attention
    arms = {}
    for label, change in (("original", None), ("frozen_edit", packet)):
        modes = {}
        arms[label] = modes
        edit = nullcontext() if change is None else prior.apply_shared_down_packets(
            model, {2: change}, realization="codes")
        with edit, sdpa_kernel(SDPBackend.MATH):
            for name, shaped_linear, shaped_attention in (
                ("native", False, False), ("linear", True, False),
                ("attention", False, True), ("both", True, True),
            ):
                with ExitStack() as stack:
                    if shaped_linear:
                        stack.enter_context(patch.object(F, "linear", position_linear(original_linear)))
                    if shaped_attention:
                        stack.enter_context(patch.object(F, "scaled_dot_product_attention",
                                                         prefix_attention(original_attention)))
                    full, cached, visits = prior.probe(model, owner.module, tokens)
                if name == "native":
                    native_full, native_cached = full, cached
                modes[name] = dict(within=prior.compare(full, cached), visits=visits,
                                   full_vs_native=prior.compare(native_full, full),
                                   cache_vs_native=prior.compare(native_cached, cached))
        assert prior.tensor_sha(owner.module._wq) == initial
    assert prior.digest(prior.PARENT) == prior.PARENT_SHA and not torch.cuda.is_initialized()
    assert sources == {name: prior.digest(prior.ROOT / name) for name in prior.SOURCES}
    assert plan_sha == prior.digest(PLAN)
    report = dict(tag=TAG, checkpoint_step=step, checkpoint_sha256=prior.PARENT_SHA,
                  source_pins=sources, plan_sha256=plan_sha, diagnostic_sha256=prior.digest(Path(__file__)),
                  reused_result_sha256=prior.digest(prior.OUT), arms=arms,
                  prompts=tokens.tolist(), optimizer_updates=0, checkpoint_writes=0)
    OUT.mkdir(exist_ok=False)
    with (OUT / "report.json").open("x", encoding="utf-8") as stream:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), file=stream)
    for name, modes in arms.items():
        print("P108_CACHE_SHAPES", name, {key: row["within"] for key, row in modes.items()}, flush=True)
    return 0


if __name__ == "__main__":
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and datetime.now(prior.CUTOFF.tzinfo) < prior.CUTOFF
    assert not OUT.exists()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    sys.exit(run())
