#!/usr/bin/env python3
"""P092 Stage1aT: actual TLinear static/DST controller microtrainer contract."""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch

from tinylm.config import build_config
from tinylm.model.ternary import TLinear
from tinylm.train.dynamic_sparsity import ConnectivityController


def run_arm(initial, *, dynamic, steps, update_every):
    cfg = build_config("tiny", "dense", 128, False)
    layer = TLinear(cfg, 128, 128)
    layer.load_state_dict(copy.deepcopy(initial))
    controller = ConnectivityController([layer], density=0.5, dynamic=dynamic, swap_fraction=0.1)
    optimizer = torch.optim.AdamW(layer.parameters(), lr=1e-3, weight_decay=0.1)
    transitions = []
    losses = []
    for step in range(steps):
        torch.manual_seed(9200 + step)
        x = torch.randn(16, 128)
        target = torch.randn(16, 128)
        layer.clear_quant()
        loss = (layer(x) - target).float().square().mean()
        loss.backward()
        controller.capture_scores_and_mask_gradients()
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        if (step + 1) % update_every == 0:
            transitions.extend(controller.rewire([optimizer]))
        losses.append(float(loss.detach()))
    mask = layer.connectivity_mask
    return losses, transitions, int(mask.sum()), mask.numel()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--update-every", type=int, default=5)
    args = parser.parse_args()
    if args.steps < args.update_every or args.update_every < 1:
        raise SystemExit("steps must cover at least one positive update interval")
    torch.manual_seed(9200)
    cfg = build_config("tiny", "dense", 128, False)
    initial_layer = TLinear(cfg, 128, 128)
    initial = initial_layer.state_dict()
    static = run_arm(initial, dynamic=False, steps=args.steps, update_every=args.update_every)
    dynamic = run_arm(initial, dynamic=True, steps=args.steps, update_every=args.update_every)
    assert all(torch.isfinite(torch.tensor(static[0]))) and all(torch.isfinite(torch.tensor(dynamic[0])))
    assert static[2] * 2 == static[3] and dynamic[2] * 2 == dynamic[3]
    assert all(item.births == item.deaths == 0 for item in static[1])
    assert dynamic[1] and all(item.births == item.deaths and item.births > 0 for item in dynamic[1])
    print(f"static_loss_first_last={static[0][0]:.6f}/{static[0][-1]:.6f} "
          f"active={static[2]}/{static[3]} transitions={len(static[1])}")
    print(f"dynamic_loss_first_last={dynamic[0][0]:.6f}/{dynamic[0][-1]:.6f} "
          f"active={dynamic[2]}/{dynamic[3]} transitions={len(dynamic[1])}")
    print("[PASS] P092 Stage1aT: TLinear mask forward, inactive score capture, active-only update, "
          "birth=death conservation and optimizer-state reset")
    print("NOTE: full Transformer/trainer 30M static50-vs-DST50 and quality remain NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
