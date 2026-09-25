#!/usr/bin/env python3
"""P095 S0bT user-run tiny Transformer first-coda Scout integration gate."""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def check_only() -> None:
    source = ROOT / "tinylm" / "model" / "scout_coda.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    if "ScoutCodaAdapter" not in classes:
        raise RuntimeError("P095 coda adapter class missing")
    print("[CHECK_ONLY] P095 wrapper syntax/entrypoint PASS; model and memory E2E NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        check_only()
        return 0

    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.model.scout_memory import CausalScoutMemory, ScoutMemoryBridge
    from tinylm.model.scout_coda import ScoutCodaAdapter

    torch.set_num_threads(1)
    torch.manual_seed(9502)
    cfg = TMTConfig(vocab_size=256, dim=128, ffn_dim=256, n_q_heads=4,
                    n_kv_heads=2, emb_rank=64, n_prelude=1, n_middle=2,
                    n_coda=1, mlp_group=1, cla_group=2, tie_mlp=False,
                    grad_checkpoint=False, max_seq_len=32)
    backbone = TiedMLPTransformer(cfg)
    memory = CausalScoutMemory(slots=128, key_dim=32, value_dim=64, dtype=torch.float32)
    wrapped = ScoutCodaAdapter(backbone, memory)
    backbone.eval()
    wrapped.eval()
    fact_a = torch.tensor([[11, 12, 13, 14]])
    fact_b = torch.tensor([[11, 12, 13, 15]])
    question = torch.tensor([[31, 32, 33]])
    future = torch.tensor([[31, 32, 33, 34]])
    write_fact = torch.ones(fact_a.shape[1], dtype=torch.bool)
    no_write = torch.zeros(question.shape[1], dtype=torch.bool)
    empty = memory.empty()

    with torch.no_grad():
        baseline = backbone(question)
        off, off_state = wrapped(question, empty, no_write)
        if not torch.equal(baseline, off) or int(off_state.cursor) != 0:
            raise RuntimeError("default gate=0 did not preserve exact backbone output/reset")
        _, state_a = wrapped(fact_a, memory.empty(), write_fact)
        _, state_b = wrapped(fact_b, memory.empty(), write_fact)
        if int(state_a.cursor) != fact_a.shape[1] or int(state_b.cursor) != fact_b.shape[1]:
            raise RuntimeError("fact write count differs from explicit mask")
        wrapped.bridge.gate.fill_(1.0)
        qa, qa_state = wrapped(question, state_a, no_write)
        qb, _ = wrapped(question, state_b, no_write)
        qempty, _ = wrapped(question, memory.empty(), no_write)
        qfuture, _ = wrapped(future, state_a, torch.zeros(future.shape[1], dtype=torch.bool))
        qa_again, _ = wrapped(question, state_a, no_write)
    history_delta = float((qa - qempty).abs().amax())
    fact_delta = float((qa - qb).abs().amax())
    prefix_delta = float((qa - qfuture[:, :question.shape[1]]).abs().amax())
    if (history_delta <= 1e-8 or fact_delta <= 1e-8 or prefix_delta > 5e-5
            or not torch.equal(qa, qa_again) or int(qa_state.cursor) != int(state_a.cursor)):
        raise RuntimeError(
            f"memory effect/prefix/reset failed history={history_delta} "
            f"fact={fact_delta} prefix={prefix_delta}"
        )

    wrapped.train()
    wrapped.zero_grad(set_to_none=True)
    _, train_state = wrapped(fact_a, memory.empty(), write_fact)
    train_logits, _ = wrapped(question, train_state, no_write)
    train_logits.float().square().mean().backward()
    names = ("bridge.fuse.weight", "bridge.write_value.weight", "backbone.emb.weight")
    params = dict(wrapped.named_parameters())
    norms = {}
    for name in names:
        grad = params[name].grad
        if grad is None or not torch.isfinite(grad).all():
            raise RuntimeError(f"missing/nonfinite gradient at {name}")
        norms[name] = float(grad.norm())
    if min(norms.values()) <= 0:
        raise RuntimeError("zero gradient in Scout-coda causal path")
    print(f"off_exact=1 fact_writes={int(state_a.cursor)} "
          f"history_delta={history_delta:.8g} fact_delta={fact_delta:.8g} "
          f"prefix_delta={prefix_delta:.8g} reset_equal=1")
    print(f"state_bytes={ScoutMemoryBridge.state_bytes(state_a)} "
          f"gradient_norms={norms}")
    print("[PASS] P095 S0bT real tiny Transformer first-coda wiring, explicit read-before-write, no context shortcut, prefix/reset and backward")
    print("[LIMIT] synthetic tokens and 128-slot fixture; 1 MiB full state, learned WRITE, language QA, compiled trainer and deployment NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
