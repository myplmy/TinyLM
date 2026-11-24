"""Verify the archived raw prefix can seed a bilingual transfer comparison."""

import argparse
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from scripts import p109c_bilingual_supervised_training as supervised
from scripts import run_p109c_early_course_share as early
from tinylm.config import TMTConfig
from tinylm.train import muon
from tinylm.train.optimizer_audit import matrix_decay_groups


prep, inputs = supervised.prep, supervised.terms.inputs
ARCHIVE = prep.EVIDENCE / early.TAG
RECEIPT = prep.ROOT / "handoff/audit/P109C_EARLY_COURSE_SHARE_20261124.json"
NEW_HEAD = ("value_link.query.weight", "value_link.key.weight")


def optimizer_names(model, extra_heads):
    standard_split = muon.split_params
    names = {id(weight): name for name, weight in model.named_parameters()}
    auxiliary = {id(model.get_parameter(name)) for name in ("decimal_head.weight", *extra_heads)}

    def split(owner):
        matrices, others = standard_split(owner)
        return [weight for weight in matrices if id(weight) not in auxiliary], others

    with patch.object(muon, "split_params", split):
        groups, matrices = matrix_decay_groups(model, lr=1., matrix_weight_decay=0.)
    matrix_ids = {id(weight) for weight in matrices}
    adam = [tuple(names[id(weight)] for weight in group["params"] if id(weight) not in matrix_ids) for group in groups]
    return dict(opt=[group for group in adam if group],
                opt_muon=[tuple(names[id(weight)] for weight in matrices)])


def state_names(optimizer, groups):
    by_name = {}
    used = set()
    for saved, names in zip(optimizer["param_groups"], groups, strict=True):
        for index, name in zip(saved["params"], names, strict=True):
            if name in by_name or index in used:
                raise ValueError("a persisted optimizer slot must have one parameter name")
            by_name[name] = index
            used.add(index)
    if not optimizer["state"].keys() <= used:
        raise ValueError("an optimizer moment lost its parameter slot")
    return by_name


def model_contract(model_type, cfg, extra_heads):
    model = model_type(cfg)
    shapes = {name: tuple(weight.shape) for name, weight in model.state_dict().items()}
    return shapes, optimizer_names(model, extra_heads)


def verify():
    report, terminal = (prep.read_json(ARCHIVE / name) for name in ("report.json", "supervisor.json"))
    phase = report["phases"]["shared"]
    identity = phase["identity"]
    if (report["profile"] != prep.read_json(RECEIPT) or prep.sha(RECEIPT) != identity["profile_sha256"]
            or report["status"] != "MATCHED_PARTIAL_TRAINING_COMPLETE" or terminal["returncode"] != 0
            or terminal["stop_reason"] is not None or terminal["card_after_exit"]["compute_pids"]):
        raise ValueError("the archived unparented prefix must have completed")
    for name, digest in report["profile"]["sources"].items():
        if prep.sha(prep.ROOT / name) != digest:
            raise ValueError(f"the original training source changed at {name}")
    checkpoint = Path(phase["checkpoint"])
    sha, state = early.phase_checkpoint(checkpoint, identity, torch)
    if sha != phase["sha256"] or state["step"] != report["profile"]["shared_updates"]:
        raise ValueError("the native raw prefix must match the archived save")

    binding = state[supervised.trainer.CONTEXT_STATE_KEY]["binding"]
    old_manifest = prep.read_json(inputs.V2_ONLY_AUDIT)
    bundle = supervised.base.Bundle(inputs.MANIFEST, old_manifest["manifest_sha256"])
    if (bundle.digest != report["profile"]["manifest_sha256"] or bundle.cache != binding["cache"]
            or bundle.warmup != state["step"] or bundle.steps != identity["horizon"]):
        raise ValueError("the old and new training must refer to the same raw pool and horizon")
    prefix = bundle.schedule[:bundle.warmup].copy()
    layout = inputs.attach(bundle, inputs.LAYOUT, old_manifest["inherited_layout_sha256"])
    if (not np.all(prefix[:, :, 0] == -1)
            or not np.array_equal(prefix, bundle.schedule[:bundle.warmup])):
        raise ValueError("all executed raw prefix addresses must remain identical")

    cfg = TMTConfig(**state["cfg"])
    old_shapes, old_groups = model_contract(supervised.base.MixedG4, cfg, ())
    new_shapes, new_groups = model_contract(supervised.SupervisedG4, cfg, NEW_HEAD)
    saved_shapes = {name: tuple(weight.shape) for name, weight in state["model"].items()}
    if (old_shapes != saved_shapes or set(new_shapes) - set(old_shapes) != set(NEW_HEAD)
            or any(new_shapes.get(name) != shape for name, shape in old_shapes.items())):
        raise ValueError("the expanded architecture must preserve every archived tensor shape")

    mapping = {}
    for optimizer, before in old_groups.items():
        after = new_groups[optimizer]
        old_ids = state_names(state[optimizer], before)
        indexes = iter(range(sum(map(len, after))))
        virtual = dict(param_groups=[dict(params=[next(indexes) for _ in names]) for names in after], state={})
        new_ids = state_names(virtual, after)
        if [tuple(name for name in group if name not in NEW_HEAD) for group in after] != before:
            raise ValueError("existing optimizer groups and parameter ordering must match")
        moments = state[optimizer]["state"]
        for name, slot in old_ids.items():
            for tensor in moments.get(slot, {}).values():
                if isinstance(tensor, torch.Tensor) and tensor.numel() > 1 and tuple(tensor.shape) != old_shapes[name]:
                    raise ValueError(f"the stored optimizer moment does not fit {name}")
        mapping[optimizer] = dict(preserved_parameters=len(old_ids), preserved_moment_slots=len(moments),
                                  old_to_new={str(slot): new_ids[name] for name, slot in old_ids.items()},
                                  new_without_moments={name: new_ids[name] for name in NEW_HEAD if name in new_ids})
    if (set(mapping["opt"]["new_without_moments"]) != set(NEW_HEAD)
            or mapping["opt_muon"]["new_without_moments"]):
        raise ValueError("only the two new head weights may be added to AdamW")
    source = {str(path.relative_to(prep.ROOT)): prep.sha(path) for path in (
        Path(__file__).resolve(), Path(supervised.__file__).resolve(), Path(early.__file__).resolve(),
        Path(muon.__file__).resolve())}
    return dict(status="CPU_PREFIX_COMPATIBILITY_VERIFIED", sources=source,
                checkpoint=str(checkpoint.relative_to(prep.ROOT)), checkpoint_sha256=sha,
                binding_sha256=binding["binding_sha256"], training_state_sha256=state[
                    supervised.trainer.CONTEXT_STATE_KEY]["payload_sha256"],
                prefix_updates=state["step"], prefix_raw_addresses=int(prefix.shape[0] * prefix.shape[1]),
                layout=layout, optimizer_slots=mapping,
                new_weight_shapes={name: new_shapes[name] for name in NEW_HEAD},
                old_numeric_tensors=len(old_shapes), child_created=False, gpu_executed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify()
    supervised.native.publish(args.output, result)
    print(result["status"], result["prefix_updates"], result["prefix_raw_addresses"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
