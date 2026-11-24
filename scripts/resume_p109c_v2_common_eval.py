"""Run or resume P109C v2 evaluation with progress-based device supervision."""

import argparse
from datetime import datetime
from functools import partial
import json
from pathlib import Path
import shutil
import time
from unittest.mock import patch

from scripts import eval_p109c_mixed_visit_count as visits
from scripts import eval_p109c_mixed_v2 as common
from scripts import p109_eval_resilient_supervisor as supervisor
from scripts.p106b_official_lm_adapter import TorchLikelihood
from scripts.p106b_shards import verify


original, native = common.original, common.native
GENERATED = {"first_use": 16, "final200": 200}


def completed_units(previous, choices, model, inputs):
    terminal = original.read_json(original.regular_file(previous / "supervisor.json"))
    if (terminal["returncode"] == 0 or not terminal["stop_reason"]
            or terminal["card_after_exit"].get("compute_pids") != []):
        raise ValueError("the interrupted evaluation needs a return receipt")
    receipt = previous / "evaluation_input.json"
    if (receipt.exists() or receipt.is_symlink()) and original.read_json(original.regular_file(receipt)) != inputs:
        raise ValueError("the previous model or evaluation profile differs from the new execution")
    groups = set(inputs["groups"])
    generated = {name: rows for name, rows in GENERATED.items() if name in groups}
    core_tasks = original.core6.TASK_COUNTS if "core6" in groups else {}
    subsets = ((generated, ("answers",)), (core_tasks, ("samples", "lengths")), (choices, ("samples",)))
    done = {}
    for sizes, fields in subsets:
        for name, size in sizes.items():
            path = previous / f"{name}.json"
            if not path.is_file():
                continue
            row = original.read_json(original.regular_file(path))
            if row["rows"] != size:
                raise ValueError(f"the prior full denominator differs: {name}")
            for field in fields:
                manifest = row[field]
                saved = original.read_json(original.regular_file(previous / f"{name}_{field}_shards_manifest.json"))
                if saved != manifest or manifest["lineage"]["model"] != model:
                    raise ValueError(f"the prior model lineage or manifest differs: {name}")
                if manifest["lineage"]["task"] != name or (field != "lengths" and manifest["rows"] != size):
                    raise ValueError(f"the prior completed shard counts differ: {name}")
                verify(previous, manifest)
            done[name] = row
    return terminal, done


def reuse_files(previous, record, rows):
    for name, row in rows.items():
        for field in ("answers", "samples", "lengths"):
            if field not in row:
                continue
            manifest = row[field]
            for entry in manifest["shards"]:
                shutil.copyfile(previous / entry["path"], record / entry["path"])
            shutil.copyfile(previous / f"{name}_{field}_shards_manifest.json", record / f"{name}_{field}_shards_manifest.json")
            verify(record, manifest)
        if name not in GENERATED:
            shutil.copyfile(previous / f"{name}.json", record / f"{name}.json")


def worker(previous, inputs, end, defer_hellaswag, choices, visit_count, profile, checksum, resume, record, cutoff):
    import torch

    torch.cuda.set_per_process_memory_fraction(min(1., 8192 * 2**20 / torch.cuda.get_device_properties(0).total_memory))
    model = inputs["mode"]
    native.publish(record / "evaluation_input.json", inputs)
    terminal, saved = None, {}
    if previous is not None:
        terminal, saved = completed_units(previous, choices, model, inputs)
        reuse_files(previous, record, saved)
    original_core = original.evaluate_core6
    original_choices = original.evaluate_korean_choices
    original_generation = original.evaluate_generation
    original_score = TorchLikelihood.__call__
    core_tasks = original.core6.TASK_COUNTS if "core6" in inputs["groups"] else {}
    deferred = {"hellaswag"} if defer_hellaswag and "hellaswag" in core_tasks else set()
    pending = {name: count for name, count in core_tasks.items() if name not in saved and name not in deferred}
    carried = {name: saved[name] for name in core_tasks if name in saved}
    pending_choices = [name for name in choices if name not in saved]

    def core(lm, tasks, target, check):
        with patch.object(original.core6, "TASK_COUNTS", pending):
            return dict(carried, **original_core(lm, tasks, target, check))

    def generation(group, runtime, target, rows, check):
        check()
        return saved[group] if group in saved else original_generation(group, runtime, target, rows, check)

    def korean(lm, inputs, target, check):
        tasks, items = inputs
        pending_tasks = {name: tasks[name] for name in pending_choices}
        carried_choices = {name: saved[name] for name in choices if name in saved}
        return dict(carried_choices, **original_choices(lm, (pending_tasks, items), target, check))

    native.publish(record / "reuse.json", dict(
        previous=str(previous) if previous is not None else None,
        previous_pid=terminal["pid"] if terminal else None, profile_sha256=checksum,
        reused={key: original.core6.digest(previous / f"{key}.json") for key in saved},
        pending_core6=list(pending), deferred_core6=sorted(deferred), pending_choices=pending_choices,
        no_repeated_completed_units=True))
    with ((record / "progress.jsonl").open("x", encoding="utf-8", buffering=1) as progress,
          patch.object(original, "evaluate_core6", core),
          patch.object(original, "evaluate_korean_choices", korean),
          patch.object(original, "evaluate_generation", generation)):
        last, scored, generated = time.monotonic(), 0, 0
        print(json.dumps(dict(unix_seconds=time.time(), scored=scored)), file=progress)

        def heartbeat():
            nonlocal last
            now = time.monotonic()
            if now - last >= 2:
                print(json.dumps(dict(unix_seconds=time.time(), scored=scored, generation_checks=generated)),
                      file=progress)
                last = now

        def score(self, batch):
            nonlocal scored
            result = original_score(self, batch)
            scored += len(result)
            heartbeat()
            return result

        def evaluate_group(group, runtime, target, rows, check):
            def check_progress():
                nonlocal generated
                check()
                generated += 1
                heartbeat()

            return generation(group, runtime, target, rows, check_progress)

        evaluate = visits.worker if visit_count else common.worker
        with (patch.object(common, "MODEL_NAME", model),
              patch.object(TorchLikelihood, "__call__", score),
              patch.object(original, "evaluate_generation", evaluate_group)):
            evaluate(end, profile, checksum, resume, record, cutoff)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    origin = parser.add_mutually_exclusive_group(required=True)
    origin.add_argument("--fresh", action="store_true")
    origin.add_argument("--previous", type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    parser.add_argument("--defer-hellaswag", action="store_true")
    parser.add_argument("--visit-count", action="store_true")
    args = parser.parse_args()
    previous = args.previous.absolute() if args.previous else None
    record, profile = args.record.absolute(), args.profile.absolute()
    if (args.stop_by.tzinfo is None or record.parent != common.returned.EVIDENCE
            or (previous is not None and previous.parent != common.returned.EVIDENCE)
            or record.exists() or record.is_symlink()):
        parser.error("evaluation requires an owned new record and an authorized cutoff")
    checksum = native.digest(args.profile_sha256)
    sealed = json.loads(native.manifest_bytes(profile, checksum))
    sources = visits.sources if args.visit_count else common.pinned_sources
    if sealed["sources"] != sources():
        raise ValueError("the original common evaluation profile or source changed")
    training = Path(sealed["training_record"])
    end = original.read_json(training / "input.json")["steps"]
    with patch.object(native, "STEPS", end):
        _, checkpoint_sha = common.completed_v2(training, sealed["training_manifest_sha256"])
    requests = sealed["inputs"].get("korean_choices", {}).get("requests", {})
    choices = {name: request["rows"] for name, request in requests.items()}
    label = visits.MODEL_NAME if args.visit_count else common.MODEL_NAME
    if training_tag := sealed.get("training_tag"):
        completed = original.read_json(original.regular_file(training / "report.json"))
        if args.visit_count or completed["tag"] != training_tag:
            raise ValueError("the explicit evaluation tag must match the completed training")
        label = training_tag
    inputs = dict(profile_sha256=checksum, model_sha256=checkpoint_sha, mode=label, groups=sealed["groups"])
    if previous is not None:
        completed_units(previous, choices, label, inputs)
    target = partial(worker, previous, inputs, end, args.defer_hellaswag, choices, args.visit_count)
    return supervisor.supervise(target, profile, checksum, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
