"""Reuse fixed quantization tensors while keeping the native VJP on each microbatch."""

import os
from statistics import median
from unittest.mock import patch

import torch

from scripts import diag_p109b_ste_g4_cpu as reference
from scripts import p109_train_visit_policy as route
from scripts import run_p109b_scratch_pair_20261120 as pair
from tinylm.config import build_config
from tinylm.model.ternary import ternary


OUT = pair.ROOT / "test_result/evidence/p109b_g4_ste_per_micro_exact_cpu_20261120"


class PerMicroVjp(torch.autograd.Function):
    @staticmethod
    def forward(ctx, latent, quantized, multiplier):
        ctx.save_for_backward(multiplier)
        return quantized.view_as(latent)

    @staticmethod
    def backward(ctx, gradient):
        multiplier, = ctx.saved_tensors
        return gradient * multiplier, None, None


class UpdateQuantizationReuse:
    def __init__(self, model):
        self.model = model
        cfg = model.cfg
        if (cfg.grad_checkpoint or cfg.wq_dtype != "fp32" or cfg.center_weights or model._arena is not None
                or any(layer.connectivity_mask is not None or layer._i8 is not None or layer._lut_codes is not None
                       for layer in model._tlinear_cache)):
            raise ValueError("the experiment supports only the declared G4 FP32 surrogate path")
        self.anneal_version = model._anneal._version
        self.buffers = []

    def refresh(self):
        model = self.model
        if not self.buffers:
            for layer in model._tlinear_cache:
                w = layer.weight.detach().requires_grad_(True)
                with torch.enable_grad():
                    q = ternary(w, model.cfg)
                    multiplier, = torch.autograd.grad(q, w, grad_outputs=torch.ones_like(q))
                with torch.no_grad():
                    value = q + (1.0 - model._anneal) * (w - q)
                self.buffers.append((layer, layer.weight._version, value, multiplier))
        for layer, version, value, multiplier in self.buffers:
            if layer.weight._version != version or model._anneal._version != self.anneal_version:
                raise RuntimeError("a parameter or anneal value changed within the update")
            layer._wq = PerMicroVjp.apply(layer.weight, value, multiplier)


def cached_update(model, initial, batches, bf16, ce_rows):
    cache = UpdateQuantizationReuse(model)
    with patch.object(model, "refresh_quant", cache.refresh):
        result = reference.update(model, initial, batches, cached=False, bf16=bf16, ce_rows=ce_rows)
    model.clear_quant()
    return {**result, "quantized_weights": len(cache.buffers)}


def compare(model, initial, batches, bf16, ce_rows=32):
    trials = {False: [], True: []}
    deltas = []
    ordinary = None
    for use_cache in (False, True, True, False):
        if use_cache:
            trial = cached_update(model, initial, batches, bf16, ce_rows)
        else:
            trial = reference.update(model, initial, batches, cached=False, bf16=bf16, ce_rows=ce_rows)
        trials[use_cache].append({key: trial[key] for key in ("seconds", "peak_allocated_mib", "peak_reserved_mib")})
        if ordinary is None:
            ordinary = trial
            continue
        delta = {"candidate": use_cache, "max_abs_loss": max(abs(a - b) for a, b in
                                                            zip(ordinary["losses"], trial["losses"], strict=True)),
                 "abs_clip_norm_delta": abs(ordinary["norm"] - trial["norm"])}
        for field in ("gradient", "weights"):
            common = ordinary[field].keys() & trial[field].keys()
            if not common:
                raise ValueError("the comparison lost all common parameter tensors")
            value, name = reference.peak_delta(ordinary, trial, field, common)
            delta[field] = {"max_abs": value, "parameter": name,
                            "presence_differences": sorted(ordinary[field].keys() ^ trial[field].keys())}
        deltas.append(delta)
    durations = {kind: [value["seconds"] for value in records] for kind, records in trials.items()}
    exact = all(delta["max_abs_loss"] == delta["abs_clip_norm_delta"] == 0
                and all(delta[field]["max_abs"] == 0 and not delta[field]["presence_differences"]
                        for field in ("gradient", "weights")) for delta in deltas if delta["candidate"])
    return {"reference_seconds_abba": durations[False], "candidate_seconds_abba": durations[True],
            "reference_trials": trials[False], "candidate_trials": trials[True],
            "delta_pct": 100 * (median(durations[True]) / median(durations[False]) - 1),
            "loss_gradient_clip_and_post_muon_adamw_weights_exact": exact,
            "numeric_deltas": deltas, "quantization_precomputations_per_weight": [len(batches), 1],
            "parameter_tensors": len(ordinary["gradient"])}


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("explicit CPU only")
    torch.set_num_threads(2)
    torch.manual_seed(1337)
    cfg = build_config("m100s12_g4", "tied", 64, ckpt=False)
    cfg.train_repeat = 2.0
    model = route.RoutedG4(cfg).train()
    model.set_anneal(reference.ANNEAL)
    model.training_route = route.route_for(cfg, model.owner, "second_shuffle_r2", 1337, 19, pair.STEPS)
    initial = {name: value.detach().clone() for name, value in model.state_dict().items()}
    batches = reference.sample()
    results = {}
    for name, bf16 in (("fp32", False), ("autocast_bf16", True)):
        results[name] = compare(model, initial, batches, bf16)
        print(name, results[name], flush=True)
    OUT.mkdir(exist_ok=False)
    pair.publish(OUT / "report.json", dict(results=results, target_tokens=512, visits=28,
        training_scheme="identical native CE, four independent fresh CPU samples per precision in ABBA order",
        no_checkpoint_writes=True, cuda="NOT_RUN", full_curve="NOT_RUN"))


if __name__ == "__main__":
    main()
