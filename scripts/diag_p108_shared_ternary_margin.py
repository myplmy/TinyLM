"""Measure two initially identical ternary edits during small CPU AdamW updates."""

import copy
import hashlib
import json
import math
import os

import torch

from scripts import diag_p108_shared_ternary_retention as prior
from scripts.p108_shared_ternary_edit import physical_down_owners
from scripts.p108_weight_space import tensor_sha
from tinylm.model.ternary import ternary


TAG = "p108_shared_ternary_margin_v2_20261118"
OUT = prior.ROOT / "test_result/evidence" / TAG
COLUMNS = (0, 1, 4, 5, 6, 7)


def source_pins():
    pins = prior.source_pins()
    for path in (__file__, prior.OUT / "report.json"):
        file = prior.ROOT / path
        pins[str(file.relative_to(prior.ROOT))] = hashlib.sha256(file.read_bytes()).hexdigest().upper()
    return pins


def new_model():
    model = prior.new_model()
    model.cfg.train_repeat = 2.0
    model.clear_quant()
    return model


def down(model):
    return physical_down_owners(model)[1].module


@torch.no_grad()
def measures(model, selected, companion):
    module = down(model)
    group = module.weight[0, :8]
    threshold = group.abs().mean() * model.cfg.twn_thr_ratio
    active = group.abs() >= threshold
    scale = (group.abs() * active).sum() / active.count_nonzero().clamp_min(1)
    compute = ternary(module.weight, model.cfg)[0, :8]
    assert torch.equal(compute, scale * active * group.sign())
    return dict(master=group.tolist(), threshold=float(threshold), scale=float(scale),
        trits=compute.sign().to(torch.int8).tolist(),
        selected_margin=float(group[selected].abs() - threshold),
        companion_margin=float(group[companion].abs() - threshold))


@torch.no_grad()
def computed_state(model, tokens):
    model.eval()
    assert len(model.visit_schedule()) == 10
    model.freeze_quant()
    return tensor_sha(down(model)._wq), tensor_sha(model(tokens))


def run_arm(start, optimizer_state, batches, column, companion, mode):
    model = new_model()
    model.load_state_dict(start, strict=True)
    group = down(model).weight[0, :8]
    with torch.no_grad():
        begin_mass = float(group.abs().sum())
        group[column].neg_()
        if mode == "near":
            threshold = float(group.abs().mean() * model.cfg.twn_thr_ratio)
            margin_weight = (math.ceil(threshold * 65536) + 1) / 65536
            difference = float(group[column].abs()) - margin_weight
            group[column].copy_(group[column].sign() * margin_weight)
            group[companion].add_(group[companion].sign() * difference)
        assert float(group.abs().sum()) == begin_mass

    optimizer = prior.optimizer_for(model)
    optimizer.load_state_dict(copy.deepcopy(optimizer_state))
    before = measures(model, column, companion)
    initial = computed_state(model, batches[0])
    initial_optimizer = prior.optimizer_hash(optimizer)
    previous = before["master"][column]
    requested = before["trits"][column]
    cumulative = 0.0
    steps = []
    for index, tokens in enumerate(batches, 1):
        ce = prior.train_step(model, optimizer, tokens)
        observation = measures(model, column, companion)
        current = observation["master"][column]
        movement = current - previous
        cumulative += abs(movement)
        steps.append(dict(step=index, ce=ce, movement=movement, cumulative_abs_movement=cumulative,
            matches_requested_trit=observation["trits"][column] == requested, **observation))
        previous = current
    return dict(before=before, initial_matrix=initial[0], initial_logits=initial[1],
        initial_optimizer=initial_optimizer, steps=steps,
        first_exit=next((row["step"] for row in steps if not row["matches_requested_trit"]), None))


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not OUT.exists()
    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    pins = source_pins()
    batches = torch.randint(3, 67, (8, 2, 6), generator=torch.Generator().manual_seed(717))
    parent = new_model()
    warm_optimizer = prior.optimizer_for(parent)
    warm_ce = prior.train_step(parent, warm_optimizer, batches[-1])
    with torch.no_grad():
        down(parent).weight[0, :8] = torch.tensor([-.75, .75, -.125, .125, .75, .75, -.75, .75])
    start = copy.deepcopy(parent.state_dict())
    parent_state = computed_state(parent, batches[0])
    parent_optimizer = prior.optimizer_hash(warm_optimizer)
    original_trits = measures(parent, 0, 1)["trits"]
    assert {i for i, trit in enumerate(original_trits) if trit} == set(COLUMNS)
    pairs = []
    for index, column in enumerate(COLUMNS):
        companion = COLUMNS[(index + 1) % len(COLUMNS)]
        far, near = (run_arm(start, warm_optimizer.state_dict(), batches, column, companion, arm)
            for arm in ("far", "near"))
        for key in ("initial_matrix", "initial_logits", "initial_optimizer"):
            assert far[key] == near[key]
        assert far["initial_optimizer"] == parent_optimizer and far["initial_matrix"] != parent_state[0]
        assert far["before"]["scale"] == near["before"]["scale"]
        assert far["before"]["threshold"] == near["before"]["threshold"]
        expected = original_trits.copy()
        expected[column] *= -1
        assert far["before"]["trits"] == near["before"]["trits"] == expected
        assert 0 < near["before"]["selected_margin"] < 2 / 65536 < far["before"]["selected_margin"]
        assert far["steps"][0]["ce"] == near["steps"][0]["ce"]
        pairs.append(dict(selected_column=column, companion_column=companion, far=far, near=near))
    assert pins == source_pins() and not torch.cuda.is_initialized()
    report = dict(schema="P108_SHARED_TERNARY_MARGIN_CPU_V2", tag=TAG, sources=pins, pairs=pairs,
        shared_original_trits=original_trits, synthetic_seed=717, synthetic_tokens_sha256=tensor_sha(batches),
        optimizer_updates=97, case_targets_processed=970, warm_ce=warm_ce,
        thres_ratio=parent.cfg.twn_thr_ratio, candidate_selection="all six active positions in fixed group",
        external_data_accesses=0, checkpoint_writes=0, gpu_initialized=False)
    OUT.mkdir(exist_ok=False)
    with (OUT / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        print(file=stream)
    print("P108_SHARED_TERNARY_MARGIN_CPU", [(p["selected_column"], p["far"]["first_exit"],
        p["near"]["first_exit"]) for p in pairs], flush=True)


if __name__ == "__main__":
    main()
