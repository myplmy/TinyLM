"""Expand only the two bilingual head weights and their AdamW slots."""

import argparse
import math
from pathlib import Path

import torch

from scripts import audit_p109c_bilingual_prefix_reuse as admission
from tinylm.config import TMTConfig


prep, early, supervised = admission.prep, admission.early, admission.supervised
HEAD_SEED = 1337
AUDIT = prep.ROOT / "handoff/audit/P109C_BILINGUAL_PREFIX_REUSE_20261124.json"


def expanded_model(weights, shapes):
    if set(shapes) != set(admission.NEW_HEAD) or weights.keys() & shapes.keys():
        raise ValueError("exactly the two absent bilingual projections can be added")
    generator = torch.Generator(device="cpu").manual_seed(HEAD_SEED)
    result = dict(weights)
    for name in admission.NEW_HEAD:
        weight = torch.empty(shapes[name], dtype=torch.float32, device="cpu")
        torch.nn.init.kaiming_uniform_(weight, a=math.sqrt(5), generator=generator)
        result[name] = weight
    return result


def expanded_adamw(state, proof, old_names, new_names):
    old_slots = admission.state_names(state, old_names)
    ids = iter(range(sum(map(len, new_names))))
    new_groups = [dict(old, params=[next(ids) for _ in names])
                  for old, names in zip(state["param_groups"], new_names, strict=True)]
    new_slots = admission.state_names(dict(param_groups=new_groups, state={}), new_names)
    mapping = {str(slot): new_slots[name] for name, slot in old_slots.items()}
    if (mapping != proof["old_to_new"] or len(old_slots) != proof["preserved_parameters"]
            or len(state["state"]) != proof["preserved_moment_slots"]
            or {name: new_slots[name] for name in new_slots.keys() - old_slots.keys()} != proof["new_without_moments"]):
        raise ValueError("the native AdamW group layout differs from the archived mapping")
    remapped = {mapping[str(slot)]: moments for slot, moments in state["state"].items()}
    return dict(param_groups=new_groups, state=remapped)


def source_prefix():
    proof = prep.read_json(AUDIT)
    for name, sha in proof["sources"].items():
        if prep.sha(prep.ROOT / name) != sha:
            raise ValueError(f"prefix compatibility code changed at {name}")
    phase = prep.read_json(admission.ARCHIVE / "report.json")["phases"]["shared"]
    sha, state = early.phase_checkpoint(prep.ROOT / proof["checkpoint"], phase["identity"], torch)
    ctx = state[supervised.trainer.CONTEXT_STATE_KEY]
    if (sha != proof["checkpoint_sha256"] or state["step"] != proof["prefix_updates"]
            or ctx["payload_sha256"] != proof["training_state_sha256"]):
        raise ValueError("the source prefix changed after the optimizer audit")
    return state, proof


def verify_cpu_load():
    state, proof = source_prefix()
    cfg = TMTConfig(**state["cfg"])
    _, old_names = admission.model_contract(supervised.base.MixedG4, cfg, ())
    model = supervised.SupervisedG4(cfg)
    new_names = admission.optimizer_names(model, admission.NEW_HEAD)
    model.load_state_dict(expanded_model(state["model"], proof["new_weight_shapes"]), strict=True)
    adamw = torch.optim.AdamW([dict(params=[model.get_parameter(name) for name in names])
                             for names in new_names["opt"]])
    migrated = expanded_adamw(state["opt"], proof["optimizer_slots"]["opt"], old_names["opt"], new_names["opt"])
    adamw.load_state_dict(migrated)
    muon = admission.muon.Muon([model.get_parameter(name) for name in new_names["opt_muon"][0]])
    muon.load_state_dict(state["opt_muon"])
    observed_model = model.state_dict()
    if any(not torch.equal(tensor, observed_model[name]) for name, tensor in state["model"].items()):
        raise ValueError("an existing model tensor changed on load")
    for optimizer, saved in ((adamw, migrated), (muon, state["opt_muon"])):
        observed = optimizer.state_dict()
        if (saved["param_groups"] != observed["param_groups"] or saved["state"].keys() != observed["state"].keys()):
            raise ValueError("the optimizer altered the admitted slot membership or options")
        for slot, moments in saved["state"].items():
            restored = observed["state"][slot]
            if moments.keys() != restored.keys() or any(
                    not torch.equal(value, restored[name]) if isinstance(value, torch.Tensor) else value != restored[name]
                    for name, value in moments.items()):
                raise ValueError(f"an optimizer moment changed on load at slot {slot}")
    return dict(status="CPU_PREFIX_MODEL_AND_OPTIMIZER_LOAD_VERIFIED", compatibility_sha256=prep.sha(AUDIT),
                source_sha256=prep.sha(Path(__file__).resolve()), checkpoint_sha256=proof["checkpoint_sha256"],
                step=state["step"], preserved_model_tensors=len(state["model"]),
                adamw_moment_slots=len(adamw.state), muon_moment_slots=len(muon.state), new_head_seed=HEAD_SEED,
                new_head_moment_slots=sum(model.get_parameter(name) in adamw.state for name in admission.NEW_HEAD),
                gpu_optimizer_updates=0, context_binding_applied=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify_cpu_load()
    supervised.native.publish(args.output, result)
    print(result["status"], result["step"], result["adamw_moment_slots"], result["muon_moment_slots"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
