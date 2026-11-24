"""Continue the shared raw-only prefix with supervised bilingual inputs."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import json
import math
import os
from pathlib import Path
import time
from unittest.mock import patch

import torch

from scripts import p109c_bilingual_prefix_state as prefix
from tinylm.config import TMTConfig


supervised, prep = prefix.supervised, prefix.prep
terms, native = supervised.terms, supervised.native
inputs = terms.inputs
TAG = "p109c_bilingual_supervised_from_raw100_chat32_v3_20261124"
RECORD = prep.EVIDENCE / TAG
CPU_RECEIPT = prep.ROOT / "handoff/audit/P109C_BILINGUAL_PREFIX_STATE_CPU_20261124.json"
BOUNDARY, START, END = 20, 100, 160
COURSE_SHARE, VALUE_CE = .10, .008
ORIGIN = "p109c_bilingual_raw_prefix_origin"


class SavedBoundary(Exception):
    """The supervised prefix reached its bound checkpoint."""


def prepare():
    cpu = prep.read_json(CPU_RECEIPT)
    if (cpu["status"] != "CPU_PREFIX_MODEL_AND_OPTIMIZER_LOAD_VERIFIED" or cpu["step"] != START
            or cpu["source_sha256"] != prep.sha(Path(prefix.__file__).resolve())
            or cpu["compatibility_sha256"] != prep.sha(prefix.AUDIT)):
        raise ValueError("the existing CPU model and optimizer load proof is required")
    bundle, layout = inputs.load_inputs()
    slots = terms.BilingualSlots(bundle, layout["layout_sha256"])
    if bundle.warmup != START or not START < END < bundle.steps or END % BOUNDARY:
        raise ValueError("the supervised prefix must start at the archive's raw-only boundary")
    planned = []
    for address in range(START, END):
        batch = bundle.schedule[address]
        target = slots.at(address)
        planned.append(dict(source_update=address + 1, reserved_batches=len(batch),
                            empty_batches=int((batch[:, 0] == -2).sum()),
                            raw_targets=int((batch[:, 0] == -1).sum()) * supervised.base.MICRO_TOKENS,
                            context_targets=len(target.context_targets) if target else 0,
                            location_targets=len(target.value_classes) if target else 0,
                            bilingual_pairs=len(target.gold) if target else 0))
    if not sum(row["bilingual_pairs"] for row in planned):
        raise ValueError("the shared supervised prefix must contain bilingual pairs")
    sources = inputs.sources()
    for path in (Path(__file__).resolve(), Path(prefix.__file__).resolve(), Path(supervised.__file__).resolve(),
                 Path(terms.__file__).resolve(), Path(terms.audited.__file__).resolve()):
        sources[str(path.relative_to(prep.ROOT))] = prep.sha(path)
    profile = dict(tag=TAG, inputs=layout, sources=sources, cpu_receipt_sha256=prep.sha(CPU_RECEIPT),
                   checkpoint_sha256=cpu["checkpoint_sha256"], start_update=START, end_update=END, boundary=BOUNDARY,
                   validation_batches=50, course_ce=COURSE_SHARE, value_ce=VALUE_CE, transfer_weight=0.,
                   source_updates=planned)
    return profile, bundle, slots


def rebind_context(context, target):
    tools = supervised.state_tools
    old = context["binding"]
    tools._validate_binding(old)
    tools._validate_binding(target)
    old_recipe, new_recipe = (dict(binding["recipe"]) for binding in (old, target))
    changes = set(old_recipe) | set(new_recipe)
    nonmatching = {name for name in changes if old_recipe.get(name) != new_recipe.get(name)}
    if (nonmatching - {"tag", "p109c_mixed_v2", "p109c_bilingual_supervised"}
            or "p109c_mixed_v2" not in old_recipe or "p109c_bilingual_supervised" not in new_recipe
            or any(old.get(key) != target.get(key) for key in set(old) | set(target)
                   if key not in {"recipe", "binding_sha256"})):
        raise ValueError(f"native prefix rebinding found an unexpected difference: {sorted(nonmatching)}")
    if context["payload_sha256"] != tools._payload_sha(context):
        raise ValueError("the original context payload must pass its normal checksum")
    derived = dict(context, binding=target)
    derived["payload_sha256"] = tools._payload_sha(derived)
    return derived


def inherit_threads(state):
    runtime = state[supervised.trainer.CONTEXT_STATE_KEY]["binding"]["runtime"]
    torch.set_num_threads(runtime["threads"])
    torch.set_num_interop_threads(runtime["interop_threads"])


def run_prefix(record, cutoff, profile, state, proof, bundle, slots, progress):
    context_key = supervised.trainer.CONTEXT_STATE_KEY
    original_binding = supervised.state_tools.make_binding
    original_save = supervised.saves.save_packed_checkpoint
    original_aux = terms.auxiliary
    ckpt_dir = record / "ckpt"
    ckpt_dir.mkdir()
    _, display = supervised.base.native_commands(bundle, TAG, resume=True)
    checkpoint = ckpt_dir / inputs.training.checkpoint_name(display, TAG)
    cfg = TMTConfig(**state["cfg"])
    _, original_names = prefix.admission.model_contract(supervised.base.MixedG4, cfg, ())
    _, expanded_names = prefix.admission.model_contract(supervised.SupervisedG4, cfg, prefix.admission.NEW_HEAD)
    origin = dict(parent_checkpoint_sha256=profile["checkpoint_sha256"],
                  source_context_sha256=state[context_key]["payload_sha256"], optimizer_prefix_steps=START,
                  initialized_head_seed=prefix.HEAD_SEED)
    updates = []
    tools = supervised.state_tools
    parent_binding = state[context_key]["binding"]
    recipe = dict(parent_binding["recipe"], tag=TAG, p109c_bilingual_supervised=profile)
    del recipe["p109c_mixed_v2"]
    expected_binding = {key: value for key, value in parent_binding.items() if key != "binding_sha256"}
    expected_binding["recipe"] = tools._canonical(recipe)
    expected_binding["binding_sha256"] = tools._sha(expected_binding)
    rebound = rebind_context(state[context_key], expected_binding)
    derived = dict(state, model=prefix.expanded_model(state["model"], proof["new_weight_shapes"]),
                   opt=prefix.expanded_adamw(state["opt"], proof["optimizer_slots"]["opt"],
                                            original_names["opt"], expanded_names["opt"]),
                   **{context_key: rebound, ORIGIN: origin})
    if checkpoint.exists():
        raise FileExistsError("the new prefix checkpoint already exists")
    original_save(checkpoint, derived)
    del derived
    print(json.dumps(dict(rebound_update=START)), file=progress, flush=True)

    def adopt(plan, recipe, cache, device):
        route = dict(schema="P109_VISIT_POLICY_NTP_V1", policy="uniform_r2", seed=1337, steps=bundle.steps,
                     eval_route="uniform_r2", sources=supervised.routed.source_pins())
        target = original_binding(plan, dict(recipe, **{supervised.routed.RECIPE_KEY: route}), cache, device)
        if target != expected_binding:
            changed = [key for key in expected_binding if target[key] != expected_binding[key]]
            raise ValueError(f"the native CLI resume binding differs in {changed}")
        return target

    def counted_aux(model, hidden, target, transfer_weight):
        if transfer_weight != 0:
            raise ValueError("the shared supervised prefix must apply zero transfer")
        context, location, metric, report = original_aux(model, hidden, target, transfer_weight=1.)
        report.update(transfer_eligible=report["transfer_pairs"], transfer_pairs=0, weighted_transfer=0.)
        return context, location, torch.zeros_like(metric), report

    def apply(row):
        index = len(updates)
        expected = profile["source_updates"][index]
        observed = {"bilingual_pairs": 0, **row}
        if (row["step"] != START + index + 1 or any(observed[key] != value for key, value in expected.items())
                or row["actual_forwards"] != row["reserved_batches"] - row["empty_batches"]
                or row.get("transfer_pairs", 0) != 0 or row.get("weighted_transfer", 0.) != 0.
                or not math.isclose(sum(w * n for w, n in zip(row["answer_weights"], row["answer_targets"], strict=True)),
                                    COURSE_SHARE, abs_tol=1e-12)):
            raise ValueError("observed optimizer step differs from the supervised prefix")
        updates.append(row)
        print(json.dumps(dict(step=row["step"], transfer_eligible=row.get("transfer_eligible", 0))),
              file=progress, flush=True)

    def save(main, path, payload):
        if path != main:
            return
        if main != checkpoint or payload["step"] != START + len(updates):
            raise ValueError("the supervised checkpoint must cover the complete applied journal")
        payload[ORIGIN] = origin
        original_save(path, payload)
        if payload["step"] == END:
            raise SavedBoundary()

    try:
        with (patch.object(supervised.state_tools, "make_binding", adopt),
              patch.object(supervised, "COURSE_SHARE", COURSE_SHARE),
              patch.object(supervised, "VALUE_WEIGHT", VALUE_CE),
              patch.object(terms, "auxiliary", counted_aux)):
            supervised.native_training(bundle, slots, record, TAG, cutoff, profile=profile,
                                       addresses=range(bundle.steps), resume=True, save=save, observe=apply)
    except SavedBoundary:
        pass
    else:
        raise RuntimeError("native training did not stop at the sealed boundary")
    state = torch.load(checkpoint, mmap=True, map_location="cpu", weights_only=True)
    context = state[context_key]
    cursor = context["cursor"]["cursor"]
    if (len(updates) != END - START or state["step"] != END or state[ORIGIN] != origin
            or cursor["next_update"] != END or cursor["optimizer_updates"] != END
            or context["payload_sha256"] != supervised.state_tools._payload_sha(context)):
        raise ValueError("the final checkpoint is not the exact supervised prefix")
    return dict(checkpoint=str(checkpoint.relative_to(prep.ROOT)), checkpoint_sha256=prep.sha(checkpoint),
                context_payload_sha256=context["payload_sha256"], optimizer_update=END, origin=origin,
                actual_updates=len(updates), eligible=sum(row.get("transfer_eligible", 0) for row in updates),
                bilingual_pairs=sum(row.get("bilingual_pairs", 0) for row in updates), updates=updates,
                last_validation=context["control"]["history"][-1])


def worker(path, digest, _resume, record, cutoff):
    with (inputs.training.locked_record(record),
          (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress,
          redirect_stdout(log), redirect_stderr(log)):
        sealed = json.loads(native.manifest_bytes(path, digest))
        profile, bundle, slots = prepare()
        if sealed != profile or torch.cuda.device_count() != 1 or time.time() >= cutoff:
            raise ValueError("the sealed supervised prefix requires the approved idle CUDA device")
        state, proof = prefix.source_prefix()
        inherit_threads(state)
        if proof["checkpoint_sha256"] != profile["checkpoint_sha256"]:
            raise ValueError("the CPU-verified prefix differs from the launched profile")
        free, total = torch.cuda.mem_get_info()
        budget = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("no usable budget on the approved CUDA device")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        result = run_prefix(record, cutoff, profile, state, proof, bundle, slots, progress)
        native.publish(record / "report.json", dict(status="SHARED_SUPERVISED_PREFIX_COMPLETE", profile=profile,
                                                    **result, peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        profile, _, _ = prepare()
        native.publish(args.profile, profile)
        print(prep.sha(args.profile), len(profile["source_updates"]), flush=True)
        return 0
    if (not args.profile_sha256 or not args.stop_by or not args.stop_by.tzinfo
            or args.stop_by > inputs.AUTHORIZATION_END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("the sealed receipt and approved CUDA device and time are required")
    return inputs.supervisor.supervise(worker, args.profile.absolute(), args.profile_sha256, RECORD, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
