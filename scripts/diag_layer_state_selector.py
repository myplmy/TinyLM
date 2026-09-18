#!/usr/bin/env python3
"""P091 R2: actual TinyLM S/U selector pipeline on deterministic tiny windows."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
import torch.nn.functional as F

from diag_layer_state_mapping import optimizers_for
from tinylm.config import build_config
from tinylm.model.transformer import TiedMLPTransformer
from tinylm.train.layer_state_mapping import build_layer_state_map


def _ranks(values):
    order = sorted(range(len(values)), key=lambda index: (values[index], index))
    result = [0.0] * len(values)
    for rank, index in enumerate(order):
        result[index] = float(rank)
    return result


def _spearman(left, right):
    if len(left) < 2:
        return 1.0
    a, b = _ranks(left), _ranks(right)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else 0.0


def _window(initial_state, seed):
    torch.manual_seed(seed)
    cfg = build_config("tiny", "tied", 128, False)
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(initial_state)
    optimizers = optimizers_for(model)
    mapping = build_layer_state_map(model, optimizers)
    modules = {}
    occurrences = {}
    for layer_index, layer in enumerate(model.layers):
        key = str(id(layer.mlp[0]))
        modules[key] = layer.mlp[0]
        occurrences.setdefault(key, []).append(layer_index)
    keys = sorted(modules, key=lambda key: occurrences[key])
    labels = ["layers=" + ",".join(map(str, occurrences[key])) for key in keys]
    x = torch.randint(0, cfg.vocab_size, (2, 32))
    y = torch.randint(0, cfg.vocab_size, (2, 32))
    with torch.no_grad():
        baseline = float(F.cross_entropy(model(x).reshape(-1, cfg.vocab_size), y.reshape(-1)))
    sensitivity = {key: [] for key in keys}
    for layer_index, layer in enumerate(model.layers):
        old = layer.gates.data[1].clone()
        layer.gates.data[1].zero_()
        with torch.no_grad():
            loss = float(F.cross_entropy(model(x).reshape(-1, cfg.vocab_size), y.reshape(-1)))
        layer.gates.data[1].copy_(old)
        sensitivity[str(id(layer.mlp[0]))].append(loss - baseline)
    s_values = [sum(sensitivity[key]) / len(sensitivity[key]) for key in keys]

    before = {
        id(parameter): parameter.detach().clone()
        for key in keys for parameter in modules[key].parameters()
    }
    opt_map = mapping["optimizer_parameters"]
    loss = F.cross_entropy(model(x).reshape(-1, cfg.vocab_size), y.reshape(-1))
    loss.backward()
    for _name, optimizer in optimizers:
        optimizer.step()
    u_values = []
    for key in keys:
        numerator = denominator = 0.0
        for parameter in modules[key].parameters():
            old = before[id(parameter)]
            info = opt_map[id(parameter)]
            expected_after_decay = old * (1.0 - info["lr"] * info["weight_decay"])
            optimizer_only = parameter.detach() - expected_after_decay
            numerator += float(optimizer_only.float().square().sum())
            denominator += float(old.float().square().sum())
        u_values.append(math.sqrt(numerator / max(denominator, 1e-30)))
    assert all(math.isfinite(value) for value in s_values + u_values)
    return labels, s_values, u_values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--windows", type=int, default=3)
    args = parser.parse_args()
    if args.windows < 2:
        raise SystemExit("--windows must be >=2")
    torch.manual_seed(9100)
    cfg = build_config("tiny", "tied", 128, False)
    initial = TiedMLPTransformer(cfg).state_dict()
    rows = [_window(initial, 9100 + index) for index in range(args.windows)]
    labels = rows[0][0]
    assert all(row[0] == labels for row in rows)
    print("window\tblock_layers\tS_gate_zero\tU_optimizer_only_over_weight")
    for window, row in enumerate(rows):
        for label, s_value, u_value in zip(labels, row[1], row[2]):
            print(f"{window}\t{label}\t{s_value:.9g}\t{u_value:.9g}")
    s_rho = [_spearman(rows[0][1], row[1]) for row in rows[1:]]
    u_rho = [_spearman(rows[0][2], row[2]) for row in rows[1:]]
    print(f"S_rank_rho_vs_window0={s_rho}")
    print(f"U_rank_rho_vs_window0={u_rho}")
    print(f"[PASS] P091 R2 pipeline: logical_layers={cfg.n_layers} unique_mlp={len(labels)} "
          f"windows={args.windows} finite_S_U=true weight_decay_separated=true")
    print("NOTE: tiny synthetic windows do not establish selector-to-realized-gain prediction; R3 remains NOT_RUN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
