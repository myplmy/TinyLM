"""Score the admitted P109C training trajectory on the frozen BabyLM AoA cases."""

import argparse
from datetime import datetime
import gc
import hashlib
import json
import os
from pathlib import Path
import signal
import time

from scripts import diag_p109b_aoa_trajectory as aoa
from scripts import eval_p109c_completed as evaluation
from scripts import run_p109c_scratch330 as training


STEPS = (*range(training.EVAL_EVERY, training.BOUNDARY + 1, training.EVAL_EVERY), training.STEPS)
SLOTS = training.MICRO * training.ACCUM * training.WIDTH


def wait_for_json(path, record, cutoff):
    while time.time() < cutoff:
        if path.is_file():
            try:
                return evaluation.read_json(path)
            except json.JSONDecodeError:
                pass
        if (record / "supervisor.json").is_file() and not path.is_file():
            raise RuntimeError(f"training closed without {path.name}")
        if time.time() - (record / "gpu.csv").stat().st_mtime > 120:
            raise RuntimeError("training telemetry stopped before the next weight receipt")
        time.sleep(5.)
    raise TimeoutError(f"the authorized CPU AoA window elapsed before {path.name}")


def snapshot(record, manifest_sha256, step, cutoff):
    if step == training.STEPS:
        wait_for_json(record / "supervisor.json", record, cutoff)
        return evaluation.completed_checkpoint(record, manifest_sha256)
    path = record / "evaluation_steps" / f"aoa_step_{step}.pt"
    proof = wait_for_json(path.with_suffix(".json"), record, cutoff)
    checksum = evaluation.core6.digest(evaluation.regular_file(path))
    if (proof["step"] != step or proof["optimizer_updates"] != step or proof["input_slots"] != step * SLOTS
            or proof["checkpoint"] != path.name or proof["sha256"] != checksum
            or proof["tokenizer_sha256"].upper() != evaluation.TOKENIZER_SHA):
        raise ValueError(f"the exact native AoA archive receipt for step {step} differs")
    return path, checksum


def reuse_scored_step(path, step, checksum, rows):
    result = evaluation.read_json(evaluation.regular_file(path))
    if (result["step"] != step or result["checkpoint_sha256"] != checksum or result["policy"] != evaluation.MODEL_NAME
            or [(item["context_id"], item["target_word"], item["step"]) for item in result["results"]]
            != [(row["context_id"], row["target_word"], str(step)) for row in rows]):
        raise ValueError("the previously scored AoA step does not match the frozen contexts")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-record", required=True, type=Path)
    parser.add_argument("--training-manifest-sha256", required=True)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    parser.add_argument("--existing-aoa-record", type=Path)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("a CPU-only device mask and scoped deadline are required")
    cutoff = args.stop_by.timestamp()
    if cutoff - time.time() <= 60:
        raise TimeoutError("less than one minute remains in the authorized CPU window")
    signal.alarm(int(cutoff - time.time()))

    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    path = args.training_record.absolute()
    parent = evaluation.training_input(path, args.training_manifest_sha256)
    schedule = evaluation.read_json(path / "evaluation_steps/schedule.json")
    if (schedule["expected_steps"] != list(STEPS[:-1])
            or schedule["parent_manifest_sha256"] != parent["manifest_sha256"]
            or schedule["resume"] != (args.existing_aoa_record is not None)):
        raise ValueError("the training archive schedule is outside the original lineage")
    prior = None
    prefix_step = 0
    if schedule["resume"]:
        native = evaluation.read_json(path / "resume_prefix.json")
        prior = Path(native["original_record"])
        prefix_step = native["step"]
        if evaluation.training_input(prior, parent["manifest_sha256"]) != parent:
            raise ValueError("the interrupted and resumed training inputs differ")
    extractor, tokenizer, official, rows = aoa.prepare()
    case_sha = hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest().upper()
    source_paths = (Path(__file__), Path(aoa.__file__), Path(evaluation.__file__))
    sources = {str(p): evaluation.core6.digest(p) for p in source_paths}
    output = args.record.absolute()
    output.mkdir(exist_ok=False)
    profile = dict(checkpoint_steps=list(STEPS), input_slots=[step * SLOTS for step in STEPS],
                   cases_sha256=case_sha, contexts=len(rows), words=len({row["target_word"] for row in rows}),
                   official_source=aoa.MANIFEST_SHA, official_assets=aoa.ASSET_SHA, sources=sources,
                   training_manifest_sha256=parent["manifest_sha256"], device="cpu")
    existing = args.existing_aoa_record.absolute() if prior else None
    if existing is not None:
        old = evaluation.read_json(evaluation.regular_file(existing / "profile.json"))
        comparable = ("cases_sha256", "checkpoint_steps", "input_slots", "official_source", "official_assets",
                      "training_manifest_sha256")
        if any(old[key] != profile[key] for key in comparable):
            raise ValueError("the existing CPU AoA profile differs from the admitted trajectory")
        profile.update(original_training_record=str(prior), existing_aoa_record=str(existing), prefix_step=prefix_step)
    training.publish(output / "profile.json", profile)
    print("P109C_AOA_PROFILE", profile["contexts"], profile["words"], case_sha, flush=True)
    scores, snapshots = [], []
    for step in STEPS:
        checkpoint, checksum = snapshot(prior if step <= prefix_step else path, parent["manifest_sha256"], step, cutoff)
        reused = existing / f"step_{step}.json" if step <= prefix_step else None
        if reused is not None:
            result = reuse_scored_step(reused, step, checksum, rows)
        else:
            model = evaluation.load_model(checkpoint, step, "cpu")
            with torch.inference_mode():
                error = aoa.compare_oracle(extractor, tokenizer, model, rows[:8])
            result = aoa.score(evaluation.MODEL_NAME, step, checksum, model, rows, error)
            model.clear_quant()
            del model
            gc.collect()
        if evaluation.core6.digest(checkpoint) != checksum:
            raise ValueError("evaluation input checkpoint changed")
        step_receipt = {key: result[key] for key in ("step", "checkpoint_sha256", "oracle_max_abs_error", "seconds")}
        if reused is not None:
            step_receipt.update(reused_score_path=str(reused), reused_score_sha256=evaluation.core6.digest(reused))
        else:
            training.publish(output / f"step_{step}.json", result)
        snapshots.append(step_receipt)
        scores.extend(result["results"])
        status = "P109C_AOA_SNAPSHOT_REUSED" if reused else "P109C_AOA_SNAPSHOT_COMPLETE"
        print(status, step, len(result["results"]), result["seconds"], flush=True)
    if {str(p): evaluation.core6.digest(p) for p in source_paths} != sources:
        raise ValueError("AoA sources changed while scoring")
    fit = official.compute_curve_fitness({"results": scores}, tokenizer)
    training.publish(output / "report.json", dict(metrics=fit, checkpoints=snapshots, contexts_per_step=len(rows),
        profile_sha256=evaluation.core6.digest(output / "profile.json"), cuda_initialized=torch.cuda.is_initialized()))
    print("P109C_AOA_COMPLETE", fit, flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
