"""CPU-only controls using a small real tied/recurrent TinyLM and no checkpoint."""

from contextlib import ExitStack
import copy
import hashlib
import json
import math
import os
from pathlib import Path

import torch
from torch.nn import functional as F

from scripts import p108_native_scale as native
from scripts import p108_weight_space as historical
from scripts.p108_shared_ternary_edit import apply_shared_down_packets, physical_down_owners
from tinylm.config import TMTConfig
from tinylm.model.transformer import TiedMLPTransformer


ROOT = Path(__file__).resolve().parents[1]
TAG = "p108_recurrent_ternary_owner_v1_20261118"
OUT = ROOT / "test_result/evidence" / TAG
SOURCES = (
    "scripts/diag_p108_shared_ternary_edit.py", "scripts/p108_shared_ternary_edit.py",
    "scripts/p108_native_scale.py", "scripts/p108_weight_space.py",
    "tinylm/config.py", "tinylm/model/transformer.py", "tinylm/model/modules.py", "tinylm/model/ternary.py",
)


def pinned_sources():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest().upper() for path in SOURCES}


def new_model():
    torch.manual_seed(1337)
    cfg = TMTConfig(vocab_size=67, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2, emb_rank=8,
        n_prelude=1, n_middle=4, n_coda=1, mlp_group=2, tie_mlp=True, cla_group=1, micro_group=8,
        max_seq_len=16, grad_checkpoint=False, quantize_embedding=False, n_modes=1, quant_anneal=1.)
    model = TiedMLPTransformer(cfg).eval()
    owners = physical_down_owners(model)
    assert {index: owner.layers for index, owner in owners.items()} == {0: (0,), 1: (1, 2), 3: (3, 4), 5: (5,)}
    with torch.no_grad():
        for index in (1, 3):
            owners[index].module.weight[0, :8] = torch.tensor([-.75, .75, -.16, .18, .75, .75, -.75, .75])
        model.freeze_quant()
    return model


def state(model):
    return {name: historical.tensor_sha(value) for name, value in model.state_dict().items()}


def forward_trace(model, tokens, before, expected):
    owners = physical_down_owners(model)
    layers, trace = [], []

    def record(owner_index, module, args, output):
        observed = historical.tensor_sha(module._wq)
        reference = expected[owner_index]
        assert observed == historical.tensor_sha(reference)
        torch.testing.assert_close(output, F.linear(args[0], reference), atol=0, rtol=0)
        same_input_baseline = F.linear(args[0], before[owner_index])
        direct_delta = F.linear(args[0], reference - before[owner_index])
        torch.testing.assert_close(output - same_input_baseline, direct_delta, atol=3e-6, rtol=1e-5)
        trace.append(dict(owner_layer=owner_index, compute_sha256=observed,
            edited=not torch.equal(reference, before[owner_index]), direct_effect_max=float(direct_delta.abs().max())))

    with ExitStack() as cleanup, torch.no_grad():
        for index, layer in enumerate(model.layers):
            handle = layer.register_forward_pre_hook(lambda _, __, i=index: layers.append(i))
            cleanup.callback(handle.remove)
        for index, owner in owners.items():
            handle = owner.module.register_forward_hook(lambda m, a, y, i=index: record(i, m, a, y))
            cleanup.callback(handle.remove)
        logits = model(tokens)
    assert layers == model.visit_schedule() and len(trace) == len(layers)
    by_layer = {layer: index for index, owner in owners.items() for layer in owner.layers}
    assert [r["owner_layer"] for r in trace] == [by_layer[layer] for layer in layers]
    assert torch.isfinite(logits).all()
    return logits, trace


def packet_sets(before):
    def flipped(index, selected):
        value = before[index].clone()
        value[0, selected] = -value[0, selected]
        return value

    single = {1: flipped(1, [0, 1])}
    split = {1: flipped(1, [0]), 3: flipped(3, [1])}
    return {name: dict(targets=targets, packets={index: native.packet(before[index], value, 8)
            for index, value in targets.items()}) for name, targets in (("single_owner", single), ("split_owners", split))}


def rejects(action, error, fragment):
    try:
        action()
    except error as exc:
        assert fragment in str(exc), str(exc)
    else:
        raise AssertionError(f"Missing guard for {fragment}")


def compare_schedule(model, tokens, before, arms, restored):
    repeat = model.cfg.infer_repeat
    baseline, baseline_trace = forward_trace(model, tokens, before, before)
    expected_layer_visits = 2 if repeat == 1. else 4
    records, outputs = {}, {}
    for arm, config in arms.items():
        expected = before | config["targets"]
        norms = [float((after - before[index]).square().sum()) for index, after in config["targets"].items()]
        ranks = [int(torch.linalg.matrix_rank((after - before[index]).to(torch.float64)))
                 for index, after in config["targets"].items()]
        assert math.fsum(norms) == 4.5 and ranks == [1] * len(norms)
        by_mode = {}
        for mode in ("codes", "sign"):
            with apply_shared_down_packets(model, config["packets"], realization=mode) as receipt:
                edited, observed = forward_trace(model, tokens, before, expected)
                assert sum(r["changed_trits"] for r in receipt) == 2
                assert sum(r["changed_master"] for r in receipt) == (0 if mode == "codes" else 2)
                assert sum(r["edited"] for r in observed) == len(norms) * expected_layer_visits
                assert all(len(r["visit_ordinals"]) == expected_layer_visits for r in receipt)
                assert not torch.equal(edited, baseline)
                by_mode[mode] = dict(receipts=receipt, visits=observed, logits_sha256=historical.tensor_sha(edited),
                    max_logit_change=float((edited - baseline).abs().max()))
                if mode == "codes":
                    outputs[arm] = edited.detach().clone()
                else:
                    torch.testing.assert_close(edited, outputs[arm], atol=0, rtol=0)
            assert restored()
            torch.testing.assert_close(model(tokens), baseline, atol=0, rtol=0)
        records[arm] = dict(ranks=ranks, squared_physical_delta_norm=math.fsum(norms), modes=by_mode)
    assert not torch.equal(outputs["single_owner"], outputs["split_owners"])
    return dict(schedule=model.visit_schedule(), baseline_trace=baseline_trace,
                baseline_sha256=historical.tensor_sha(baseline), comparisons=records)


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    sources = pinned_sources()
    if OUT.exists():
        raise FileExistsError(f"Preserve existing run {OUT.name}")
    model = new_model()
    owners = physical_down_owners(model)
    before = {index: owner.module._wq.detach().clone() for index, owner in owners.items()}
    caches = [(module, module._wq, module._anneal_t) for module in model._tlinear_cache]
    saved, parameter_ids = state(model), tuple(id(value) for value in model.parameters())

    def restored():
        return (saved == state(model) and tuple(id(value) for value in model.parameters()) == parameter_ids
                and all(module._wq is cache and module._anneal_t is anneal for module, cache, anneal in caches)
                and model._quant_frozen)

    tokens = torch.tensor([[3, 7, 8, 9, 11, 14], [4, 8, 15, 16, 23, 42]], dtype=torch.long)
    arms = packet_sets(before)
    schedules = {}
    for repeat in (1., 2.):
        model.cfg.infer_repeat = repeat
        schedules[str(repeat)] = compare_schedule(model, tokens, before, arms, restored)
    split = arms["split_owners"]["packets"]

    def apply(packets, mode="codes"):
        with apply_shared_down_packets(model, packets, realization=mode):
            pass

    rejects(lambda: historical.down_modules(model), ValueError, "shared MLP unsupported")
    rejects(lambda: apply({2: split[1]}), ValueError, "first logical layer")
    corrupted = copy.deepcopy(split[3]); corrupted["target_sha256"] = "0" * 64
    rejects(lambda: apply({1: split[1], 3: corrupted}), ValueError, "target or transition binding")
    assert restored()
    delta_target = before[1].clone()
    assert delta_target[0, 2] == 0 and delta_target[0, 1] == .75
    delta_target[0, 2] = .75
    unmask = {1: native.packet(before[1], delta_target, 8)}
    rejects(lambda: apply(unmask, "sign"), ValueError, "only flip existing nonzero trits")
    with apply_shared_down_packets(model, unmask, realization="codes") as receipt:
        _, trace = forward_trace(model, tokens, before, before | {1: delta_target})
        assert receipt[0]["changed_trits"] == 1 and receipt[0]["changed_master"] == 0
        assert sum(item["edited"] for item in trace) == 4
        rejects(lambda: apply(split), RuntimeError, "already owns")
    assert restored()

    def caller_failure():
        with apply_shared_down_packets(model, split, realization="sign"):
            raise RuntimeError("synthetic caller failure")

    rejects(caller_failure, RuntimeError, "synthetic caller failure")
    assert restored()
    module = owners[1].module
    master_copy = module.weight.detach().clone()
    with torch.no_grad():
        module.weight[0, 0].neg_()
    try:
        rejects(lambda: apply(split), ValueError, "differs from the current native master")
    finally:
        with torch.no_grad():
            module.weight.copy_(master_copy)
    assert restored() and pinned_sources() == sources and not torch.cuda.is_initialized()
    result = dict(schema="P108_SHARED_TERNARY_EDIT_CPU_V1", tag=TAG, source_sha256=sources, seed=1337,
        weight_count=sum(p.numel() for p in model.parameters()), original_owner_layers={i: o.layers for i,o in owners.items()},
        schedules=schedules, packets={k: v["packets"] for k,v in arms.items()}, unmask_visits=trace,
        rejection_cases=["LEGACY_SHARED", "LOGICAL_ALIAS", "FORGED_SECOND_PACKET", "SIGN_UNMASK", "NESTED", "STALE_CACHE"],
        exact_state_restore=True, exception_restore=True, model_checkpoint_loads=0, GPU_calls=0, training_updates=0)
    OUT.mkdir(exist_ok=False)
    with (OUT / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(file=stream)
    print("SHARED_TERNARY_EDIT_CPU", [{"repeat": k, "visits": len(v["schedule"])} for k,v in schedules.items()],
        "exact_restore", result["exact_state_restore"], "rejections", len(result["rejection_cases"]), flush=True)


if __name__ == "__main__":
    main()
