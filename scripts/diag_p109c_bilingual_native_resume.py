"""Verify a native save boundary with supervised bilingual heads and empty-slot skipping."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
import gc
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import time

import torch

from scripts import p109c_bilingual_supervised_training as objective


terms, prep, native = objective.terms, objective.prep, objective.native
inputs = terms.inputs
TAG = "p109c_bilingual_aux_resume_chat32_v1_20261124"
ADDRESSES = tuple(range(152, 156))
BOUNDARY = 2
SAVE_KEY = "p109c_bilingual_supervised_exposure"
NUMERIC_STATE = ("model", "opt", "opt_muon")


def prepare():
    bundle, layout = inputs.load_inputs()
    slots = terms.BilingualSlots(bundle, layout["layout_sha256"])
    pins = inputs.sources()
    own = [Path(m.__file__).resolve() for m in (objective, terms, terms.audited)]
    for path in [Path(__file__).resolve(), *own]:
        pins[str(path.relative_to(prep.ROOT))] = prep.sha(path)
    expected = []
    for address in ADDRESSES:
        schedule = bundle.schedule[address]
        target = slots.at(address)
        expected.append(dict(source_update=address + 1, empty_batches=int((schedule[:, 0] == -2).sum()),
                             context_targets=len(target.context_targets), location_targets=len(target.value_classes)))
    if not sum(row["empty_batches"] for row in expected) or not sum(row["context_targets"] for row in expected):
        raise ValueError("the bounded trial must cover both bilingual supervision and empty slots")
    profile = dict(tag=TAG, sources=pins, inputs=layout, source_addresses=expected, boundary=BOUNDARY,
                   validation_batches=2, optimizer_horizon=bundle.steps, padding="SKIP_TRUE_EMPTY_MICROBATCH",
                   course_ce=objective.COURSE_SHARE, location_ce=objective.VALUE_WEIGHT, transfer=0.)
    return profile, bundle, slots


class SavedEnough(Exception):
    """Both arms stop after the sealed optimizer boundary."""


def encode(row):
    return (json.dumps(row, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def cpu_snapshot(value):
    if isinstance(value, torch.Tensor):
        return value.detach().to(device="cpu", copy=True)
    if isinstance(value, dict):
        return {key: cpu_snapshot(item) for key, item in value.items()}
    if isinstance(value, list):
        return [cpu_snapshot(item) for item in value]
    return value


def differences(a, b):
    counts = dict(tensors=0, differing_tensors=0, max_abs=0., reference_l2=0., difference_l2=0.)

    def count(x, y):
        if isinstance(x, torch.Tensor):
            if x.shape != y.shape or x.dtype != y.dtype:
                raise ValueError("the restored tensor metadata differs")
            counts["tensors"] += 1
            x64 = x.to(torch.float64)
            counts["reference_l2"] += float(x64.square().sum())
            if not torch.equal(x, y):
                delta = x64 - y
                counts["differing_tensors"] += 1
                counts["max_abs"] = max(counts["max_abs"], float(delta.abs().max()))
                counts["difference_l2"] += float(delta.square().sum())
        elif isinstance(x, dict) and x.keys() == y.keys():
            for key in x:
                count(x[key], y[key])
        elif isinstance(x, list) and len(x) == len(y):
            for before, after in zip(x, y, strict=True):
                count(before, after)
        elif x != y:
            raise ValueError("the restored optimizer layout or hyperparameters differ")

    count(a, b)
    counts["reference_l2"] = math.sqrt(counts["reference_l2"])
    counts["difference_l2"] = math.sqrt(counts["difference_l2"])
    return counts


def checkpoint_context(state, profile, step):
    context = state[objective.trainer.CONTEXT_STATE_KEY]
    cursor = context["cursor"]["cursor"]
    binding = context["binding"]
    tools = objective.state_tools
    tools._validate_binding(binding)
    tools.validate_trainer_control(context["control"], step, cursor["optimizer_updates"])
    if (state["step"] != step or binding["recipe"]["p109c_bilingual_supervised"] != profile
            or context["payload_sha256"] != tools._payload_sha(context) or context["control"]["n_skip"]
            or cursor["next_update"] != step or cursor["optimizer_updates"] != step
            or cursor["draw_tokens"] != step * prep.ACCUM * objective.base.MICRO_TOKENS
            or not all(state.get(name) for name in NUMERIC_STATE)):
        raise ValueError("native checkpoint lacks the complete bound optimizer trajectory")
    return context


def run_arm(record, cutoff, profile, bundle, slots, progress, prefix=None):
    name = "resume" if prefix else "continuous"
    journal_path = record / f"{name}.jsonl"
    rows = list(prefix["rows"]) if prefix else []
    digest = sha256()
    reference_save = objective.saves.save_packed_checkpoint
    saved_prefix = final = None

    with journal_path.open("xb", buffering=0) as journal:
        def record_row(row):
            raw = encode(row)
            journal.write(raw)
            digest.update(raw)

        for row in rows:
            record_row(row)

        def observe(row):
            next_step = len(rows) + 1
            if row["step"] != next_step or any(
                    row[key] != value for key, value in profile["source_addresses"][next_step - 1].items()):
                raise ValueError("the actual optimizer applied a different input address")
            rows.append(row)
            record_row(row)
            print(json.dumps(dict(arm=name, step=row["step"], source=row["source_update"])), file=progress, flush=True)

        def save(main, path, state):
            nonlocal saved_prefix, final
            if path != main:
                return  # Keep one restartable checkpoint in this diagnostic.
            step = state["step"]
            if step != len(rows) or step not in (BOUNDARY, len(ADDRESSES)):
                raise ValueError("native save is outside the bound journal boundary")
            checkpoint_context(state, profile, step)
            state[SAVE_KEY] = dict(step=step, journal_sha256=digest.hexdigest().upper())
            os.fsync(journal.fileno())
            if step == BOUNDARY:
                if prefix or main.exists():
                    raise FileExistsError("only the original arm can publish the prefix")
                reference_save(main, state)
                saved_prefix = dict(path=main, sha256=prep.sha(main), rows=list(rows), seal=state[SAVE_KEY])
            else:
                final = {key: cpu_snapshot(state[key]) for key in (*NUMERIC_STATE, objective.trainer.CONTEXT_STATE_KEY)}
                raise SavedEnough()

        try:
            objective.native_training(bundle, slots, record, TAG, cutoff, profile=profile, addresses=ADDRESSES,
                                      resume=bool(prefix), save=save, observe=observe)
        except SavedEnough:
            pass
        else:
            raise RuntimeError("the native trainer did not reach the sealed diagnostic boundary")
    if final is None or (not prefix and saved_prefix is None):
        raise RuntimeError("the diagnostic did not capture both intended native save states")
    return final, rows, saved_prefix


def verify(record, profile, bundle, slots, cutoff):
    (record / "ckpt").mkdir()
    (record / "native_logs").mkdir()
    with (record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress:
        continuous, full_rows, prefix = run_arm(record, cutoff, profile, bundle, slots, progress)
        saved = torch.load(prefix["path"], map_location="cpu", mmap=True, weights_only=True)
        prefix_state = checkpoint_context(saved, profile, BOUNDARY)
        if (prefix["sha256"] != prep.sha(prefix["path"]) or saved[SAVE_KEY] != prefix["seal"]
                or sha256(b"".join(encode(row) for row in prefix["rows"])).hexdigest().upper() != prefix["seal"]["journal_sha256"]):
            raise ValueError("the exact saved native file and its exposure journal must agree")
        value_weights = {k: v for k, v in saved["model"].items() if k.startswith("value_link.")}
        value_update = differences(value_weights, {k: continuous["model"][k] for k in value_weights})
        if value_update["differing_tensors"] != 2:
            raise ValueError("the supervised location weights must actually change at the native optimizer step")
        prefix_sha = prefix_state["payload_sha256"]
        del saved
        gc.collect()
        torch.cuda.empty_cache()
        resumed, resumed_rows, _ = run_arm(record, cutoff, profile, bundle, slots, progress, prefix)
    bundle.unchanged()
    if prefix["sha256"] != prep.sha(prefix["path"]):
        raise ValueError("the resumed process modified its source checkpoint")
    ctx, ctx2 = [item[objective.trainer.CONTEXT_STATE_KEY] for item in (continuous, resumed)]
    keys = ("cursor", "binding", "validation_rng")
    equal = {key: ctx[key] == ctx2[key] for key in keys}
    equal.update({key: torch.equal(ctx[key], ctx2[key]) for key in ("cpu_rng", "cuda_rng")})
    same_fields = ("source_update", "actual_forwards", "reserved_batches", "empty_batches", "forward_layer_slots",
                   "raw_targets", "course_inputs", "answer_targets", "location_targets", "context_targets")
    if not all(equal.values()) or any(
            row[key] != other[key] for row, other in zip(full_rows, resumed_rows, strict=True) for key in same_fields):
        raise ValueError("the two native arms applied different input, route, optimizer or RNG state")
    return dict(status="NATIVE_CHECKPOINT_RECOVERY_MEASURED", sealed=profile,
                prefix=dict(path=str(prefix["path"]), sha256=prefix["sha256"], native_payload_sha256=prefix_sha),
                continuous_updates=full_rows, resumed_updates=resumed_rows,
                matched_discrete_state=equal, resume_comparison={
                    key: differences(continuous[key], resumed[key]) for key in NUMERIC_STATE},
                validation=dict(continuous=ctx["control"]["history"], resumed=ctx2["control"]["history"]),
                value_head_update_from_prefix=value_update,
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20)


def worker(path, sha, _resume, record, cutoff):
    with (inputs.training.locked_record(record),
          (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        sealed = json.loads(native.manifest_bytes(path, sha))
        profile, bundle, slots = prepare()
        if profile != sealed or torch.cuda.device_count() != 1:
            raise ValueError("the sealed diagnostic requires unchanged sources and exactly one GPU")
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        free, total = torch.cuda.mem_get_info()
        budget = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("the approved CUDA allocation budget is unavailable")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        native.publish(record / "report.json", verify(record, profile, bundle, slots, cutoff))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        profile, _, _ = prepare()
        native.publish(args.profile, profile)
        print(prep.sha(args.profile), profile["source_addresses"], flush=True)
        return 0
    if (args.profile_sha256 is None or args.stop_by is None or args.stop_by.tzinfo is None
            or args.stop_by > inputs.AUTHORIZATION_END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("the exact profile, approved cutoff and GPU 0 are required")
    return inputs.supervisor.supervise(worker, args.profile, args.profile_sha256, prep.EVIDENCE / TAG, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
