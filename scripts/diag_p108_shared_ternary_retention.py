"""Track fixed trits and latent sign edits across real tiny CPU AdamW updates."""

import copy
import hashlib
import json
import math
import os

import torch
from torch.nn import functional as F

from scripts import p108_native_scale as native
from scripts.diag_p108_shared_ternary_edit import ROOT, SOURCES, new_model, state
from scripts.p108_shared_ternary_edit import apply_shared_down_packets, physical_down_owners
from scripts.p108_weight_space import tensor_sha


TAG = "p108_shared_ternary_update_retention_v1_20261118"
OUT = ROOT / "test_result/evidence" / TAG
PRIOR = ROOT / "test_result/evidence/p108_recurrent_ternary_owner_v1_20261118/report.json"
SOURCE_FILES = (*SOURCES, "scripts/diag_p108_shared_ternary_retention.py")


def source_pins():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest().upper() for name in SOURCE_FILES}


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest().upper()


def optimizer_for(model):
    return torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=.01, foreach=False, fused=False)


def optimizer_hash(optimizer):
    payload = optimizer.state_dict()
    states = {i: {key: tensor_sha(x) if isinstance(x, torch.Tensor) else x for key, x in record.items()}
              for i, record in payload["state"].items()}
    return object_hash(dict(state=states, param_groups=payload["param_groups"]))


def train_step(model, optimizer, tokens):
    model.train()
    model.clear_quant()
    assert not model._quant_frozen and len(model.visit_schedule()) == 10
    optimizer.zero_grad(set_to_none=True)
    logits = model(tokens)
    targets = tokens[:, 1:]
    assert targets.numel() == 10
    loss = F.cross_entropy(logits[:, :-1].reshape(-1, logits.shape[-1]), targets.reshape(-1))
    loss.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    assert math.isfinite(float(loss.detach()))
    return float(loss.detach())


def selected_state(model, optimizer):
    model.eval()
    with torch.no_grad():
        model.freeze_quant()
    owner = physical_down_owners(model)[1].module
    compute = owner._wq[0, :2]
    return dict(trits=compute.sign().to(torch.int8).tolist(), compute=compute.tolist(),
        master=owner.weight[0, :2].detach().tolist(), model_sha256=object_hash(state(model)),
        optimizer_sha256=optimizer_hash(optimizer))


def frozen_forks(model, tokens):
    owner = physical_down_owners(model)[1].module
    initial = owner._wq.detach().clone()
    changed = initial.clone()
    assert bool(initial[0, :2].ne(0).all())
    changed[0, :2] = -changed[0, :2]
    plan = {1: native.packet(initial, changed, model.cfg.micro_group)}
    forks = {"original": copy.deepcopy(model.state_dict())}
    frozen_logits = {}
    with torch.no_grad():
        frozen_logits["original"] = tensor_sha(model(tokens))
        for key, mode in (("code_cache", "codes"), ("master_sign", "sign")):
            with apply_shared_down_packets(model, plan, realization=mode) as details:
                assert details[0]["changed_trits"] == 2 and len(details[0]["visit_ordinals"]) == 4
                forks[key] = copy.deepcopy(model.state_dict())
                frozen_logits[key] = tensor_sha(model(tokens))
    assert frozen_logits["code_cache"] == frozen_logits["master_sign"] != frozen_logits["original"]
    assert all(torch.equal(forks["original"][name], forks["code_cache"][name]) for name in forks["original"])
    changed_keys = [name for name, master in forks["master_sign"].items()
                    if not torch.equal(master, forks["original"][name])]
    aliases = [name for name, master in model.state_dict(keep_vars=True).items() if master is owner.weight]
    assert changed_keys == aliases and aliases
    assert all(int(forks["master_sign"][key].ne(forks["original"][key]).sum()) == 2 for key in changed_keys)
    return forks, frozen_logits, changed[0, :2].sign().to(torch.int8).tolist(), changed_keys


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    if OUT.exists():
        raise FileExistsError(f"Preserve existing run {OUT.name}")
    torch.set_num_threads(1)
    sources = source_pins()
    readback = json.loads(PRIOR.read_text())
    assert readback["exact_state_restore"] and all(sources[k] == v for k, v in readback["source_sha256"].items())
    tokens = torch.tensor([[3, 7, 8, 9, 11, 14], [4, 8, 15, 16, 23, 42]], dtype=torch.long)
    parent = new_model()
    parent.cfg.train_repeat = 2.
    optimizer = optimizer_for(parent)
    warm_ce = train_step(parent, optimizer, tokens)
    warm = selected_state(parent, optimizer)
    warm_optimizer = copy.deepcopy(optimizer.state_dict())
    branches, frozen, requested_trits, changed_keys = frozen_forks(parent, tokens)
    assert selected_state(parent, optimizer) == warm
    arms = {}
    for name, masters in branches.items():
        model = new_model()
        model.cfg.train_repeat = 2.
        model.clear_quant()
        model.load_state_dict(masters, strict=True)
        arm_optimizer = optimizer_for(model)
        arm_optimizer.load_state_dict(copy.deepcopy(warm_optimizer))
        before = selected_state(model, arm_optimizer)
        assert before["optimizer_sha256"] == warm["optimizer_sha256"]
        steps = []
        for ordinal in range(1, 5):
            ce = train_step(model, arm_optimizer, tokens)
            row = selected_state(model, arm_optimizer)
            steps.append(dict(ordinal=ordinal, ce=ce, optimizer_update=True, **row))
        for row in (before, *steps):
            row["matching_requested_trits"] = sum(a == b for a, b in zip(row["trits"], requested_trits, strict=True))
        arms[name] = dict(before_update=before, steps=steps)
    assert arms["original"] == arms["code_cache"]
    assert arms["master_sign"]["before_update"]["matching_requested_trits"] == 2
    assert sources == source_pins() and not torch.cuda.is_initialized()
    report = dict(schema="P108_SHARED_TERNARY_RETENTION_CPU_V1", tag=TAG, sources=sources,
        preceding_owner_report_sha256=hashlib.sha256(PRIOR.read_bytes()).hexdigest().upper(),
        warm=dict(ce=warm_ce, **warm), requested_trits=requested_trits, frozen_logits=frozen,
        changed_alias_keys=changed_keys, training=arms, case_targets_per_update=10, optimizer_updates=13,
        case_targets_processed=130, original_and_code_replay_bit_exact=True, GPU_calls=0,
        language_corpus=False, existing_checkpoints_read=0, checkpoint_writes=0)
    OUT.mkdir(exist_ok=False)
    with (OUT / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        print(file=stream)
    print("SHARED_TERNARY_RETENTION_CPU", {name: [x["matching_requested_trits"] for x in arm["steps"]]
          for name, arm in arms.items()}, flush=True)


if __name__ == "__main__":
    main()
