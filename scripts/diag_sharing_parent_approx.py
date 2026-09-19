#!/usr/bin/env python3
"""P093 Stage0c: dense-parent shared-base + low-rank residual approximation."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _parse_ranks(raw):
    values = sorted({int(value) for value in raw.split(",")})
    if not values or values[0] < 1:
        raise argparse.ArgumentTypeError("ranks must be positive")
    return values


def _approximation_gate(values, *, max_output_nrms, min_output_improvement):
    monotonic_weight = all(b[1] <= a[1] + 1e-8 for a, b in zip(values, values[1:]))
    monotonic_output = all(b[2] <= a[2] + 1e-8 for a, b in zip(values, values[1:]))
    baseline = values[0][2]
    best = values[-1][2]
    improvement = 1.0 - best / max(baseline, 1e-30)
    viable = best <= max_output_nrms and improvement >= min_output_improvement
    return monotonic_weight, monotonic_output, improvement, viable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--arch", choices=["dense", "tied"], default="dense")
    parser.add_argument("--device", choices=["cpu", "cuda"], default=None)
    parser.add_argument("--group", type=int, default=4)
    parser.add_argument("--ranks", type=_parse_ranks, default=_parse_ranks("4,8,16"))
    parser.add_argument("--samples", type=int, default=128)
    parser.add_argument("--max-output-nrms", type=float, default=0.90)
    parser.add_argument("--min-output-improvement", type=float, default=0.10)
    args = parser.parse_args()

    import torch
    import torch.nn.functional as F
    from tinylm.infer.generate import load_model

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    model, cfg, device = load_model(args.arch, args.ckpt, device)
    middle = list(range(cfg.n_prelude, cfg.n_prelude + cfg.n_middle))
    if len(middle) % args.group:
        print(f"[GATE FAIL] n_middle={len(middle)} not divisible by group={args.group}")
        return 2
    projections = ("gate_proj", "up_proj", "down_proj")
    ranks = [0] + args.ranks
    weight_error = {rank: [0.0, 0.0] for rank in ranks}
    output_error = {rank: [0.0, 0.0] for rank in ranks}
    torch.manual_seed(9300)

    for group_index in range(0, len(middle), args.group):
        layer_ids = middle[group_index:group_index + args.group]
        mlps = [model.layers[index].mlp[0] for index in layer_ids]
        bases = {}
        originals = [{} for _ in mlps]
        approximations = {rank: [{} for _ in mlps] for rank in ranks}
        for projection in projections:
            weights = [getattr(mlp, projection).weight.detach().float() for mlp in mlps]
            base = torch.stack(weights).mean(0)
            bases[projection] = base
            max_rank = max(args.ranks)
            for layer_offset, weight in enumerate(weights):
                originals[layer_offset][projection] = weight
                residual = weight - base
                q = min(max_rank, min(residual.shape) - 1)
                u, s, v = torch.svd_lowrank(residual, q=q, niter=3)
                approximations[0][layer_offset][projection] = base
                for rank in args.ranks:
                    used = min(rank, q)
                    recon = base + (u[:, :used] * s[:used]) @ v[:, :used].t()
                    approximations[rank][layer_offset][projection] = recon
                for rank in ranks:
                    delta = approximations[rank][layer_offset][projection] - weight
                    weight_error[rank][0] += float(delta.square().sum())
                    weight_error[rank][1] += float(weight.square().sum())

        x = torch.randn(args.samples, cfg.dim, device=device)
        for layer_offset, _mlp in enumerate(mlps):
            original_weights = originals[layer_offset]
            with torch.no_grad():
                original = F.linear(
                    F.silu(F.linear(x.float(), original_weights["gate_proj"]))
                    * F.linear(x.float(), original_weights["up_proj"]),
                    original_weights["down_proj"],
                )
            for rank in ranks:
                p = approximations[rank][layer_offset]
                with torch.no_grad():
                    candidate = F.linear(
                        F.silu(F.linear(x.float(), p["gate_proj"]))
                        * F.linear(x.float(), p["up_proj"]),
                        p["down_proj"],
                    )
                delta = candidate - original
                output_error[rank][0] += float(delta.square().sum())
                output_error[rank][1] += float(original.square().sum())

    print("rank\tweight_nrms\tmlp_output_nrms")
    values = []
    for rank in ranks:
        w = math.sqrt(weight_error[rank][0] / max(weight_error[rank][1], 1e-30))
        y = math.sqrt(output_error[rank][0] / max(output_error[rank][1], 1e-30))
        values.append((rank, w, y))
        print(f"{rank}\t{w:.9g}\t{y:.9g}")
    monotonic_weight, monotonic_output, output_improvement, viable = _approximation_gate(
        values,
        max_output_nrms=args.max_output_nrms,
        min_output_improvement=args.min_output_improvement,
    )
    print(f"best_output_nrms={values[-1][2]:.9g} "
          f"relative_output_error_reduction={output_improvement:.3%} "
          f"required_output_nrms<={args.max_output_nrms:.3f} "
          f"required_reduction>={args.min_output_improvement:.1%}")
    if not (monotonic_weight and monotonic_output):
        print(f"[GATE NEGATIVE] monotonic_weight={monotonic_weight} monotonic_output={monotonic_output}")
        return 8
    if not viable:
        print("[GATE NEGATIVE] rank growth is monotonic but does not recover enough parent output; "
              "do not open save/load or training integration")
        return 8
    print(f"[PASS] P093 Stage0c: groups={len(middle)//args.group} ranks={args.ranks} "
          "weight/output approximation errors decrease and pass the viability floor")
    print("NOTE: approximation is not save/load wiring, optimizer ownership, latency or quality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
