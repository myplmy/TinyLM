"""Train one v2-quality comparison by replacing only the raw window positions."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch

from scripts import p109_gpu_supervisor as telemetry
from scripts import prepare_p109c_nonoverlap_raw as windows
from scripts import run_p109c_scratch_mixed as mixed


prep, native, state_tools = mixed.prep, mixed.native, mixed.context_training_state
TAG = "p109c_v2_raw_nonoverlap_chat32_s1337_v1_20261124"
RECORD = prep.EVIDENCE / TAG
STOP = datetime.fromisoformat("2026-11-25T17:00:00+09:00")
BASELINE = prep.EVIDENCE / "p109c_scratch_mixed_v2_v11_chat32_s1337_run1_20261123"
MANIFEST = prep.ROOT / "data_cache/p109c_mixed_v2_v11_course_20261122_v1/manifest.json"
WINDOWS = prep.ROOT / "data_cache/p109c_v2_raw_nonoverlap_20261123"
RECIPE_KEY = "p109c_v2_raw_window_selection"


def unique(starts):
    coordinates = np.sort(starts.ravel())
    return prep.WIDTH + int(np.minimum(np.diff(coordinates), prep.WIDTH).sum())


def prepare():
    window_path = WINDOWS / "profile.json"
    selection = prep.read_json(window_path)
    bundle = mixed.Bundle(MANIFEST, selection["original_manifest_sha256"])
    replacement_path = WINDOWS / "raw_starts.npy"
    order = windows.read_array(replacement_path, selection["stored_npy_sha256"])
    if (selection["status"] != "NONOVERLAP_PROFILE_READY" or order.shape != bundle.starts.shape
            or order.dtype != bundle.starts.dtype or order.min() < 0 or order.max() + prep.WIDTH >= len(bundle.raw)
            or selection["original_starts_sha256"] != bundle.manifest["raw_starts_sha256"]
            or sha256(order.tobytes()).hexdigest().upper() != selection["raw_positions_sha256"]
            or (np.diff(np.sort(order.ravel())) <= prep.WIDTH).any()):
        raise ValueError("the matched raw layout is missing, changed, or overlapping")

    baseline_receipt = prep.read_json(BASELINE / "supervisor.json")
    baseline_report = prep.read_json(BASELINE / "report.json")
    baseline_training = prep.read_json(BASELINE / "training.json")
    _, display = mixed.native_commands(bundle, baseline_report["tag"], False)
    path = BASELINE / "ckpt" / f"{native.PRESET}_ko-en_{display}_{baseline_report['tag']}.pt"
    state = torch.load(path, map_location="cpu", mmap=True, weights_only=True)
    context = state[mixed.trainer.CONTEXT_STATE_KEY]
    bound = context["binding"]
    state_tools._validate_binding(bound)
    cursor = context["cursor"]["cursor"]
    state_tools.validate_trainer_control(context["control"], bundle.steps, cursor["optimizer_updates"])
    if (baseline_receipt["returncode"] != 0 or baseline_receipt["stop_reason"] is not None
            or baseline_receipt["card_after_exit"]["compute_pids"]
            or baseline_report["status"] != "FULL_SCRATCH_MIXED_COMPLETE"
            or baseline_report["input_manifest_sha256"] != bundle.digest or baseline_report["steps"] != bundle.steps
            or context["payload_sha256"] != state_tools._payload_sha(context) or context["control"]["n_skip"]
            or any(state["step"] != cursor[key] for key in ("next_update", "optimizer_updates"))
            or state["step"] != bundle.steps or baseline_training["policy"]["sources"] != mixed.routed.source_pins()
            or bound["recipe"]["p109c_mixed_v2"]["source_sha256"] != prep.sha(Path(mixed.__file__))):
        raise ValueError("the original v2 treatment requires its actual intact full run")
    count = np.cumsum(np.count_nonzero(bundle.schedule[:, :, 0] == -1, axis=1))
    coverage = []
    for step in (100, 160, 256, 500, 1000, 1048, 1250, 1500, 2000, 2354, bundle.steps):
        windows_drawn = count[step - 1]
        coverage.append(dict(step=step, raw_draws=int(windows_drawn * prep.BATCH * prep.WIDTH),
                             original_unique=unique(bundle.starts[:windows_drawn]),
                             nonoverlap_unique=unique(order[:windows_drawn])))
    if coverage[-1]["nonoverlap_unique"] != baseline_report["raw_tokens"]:
        raise ValueError("the candidate must retain exactly the original raw exposure")
    pins = {str(p.relative_to(prep.ROOT)): prep.sha(p)
            for p in (Path(__file__).resolve(), Path(windows.__file__).resolve(), Path(telemetry.__file__).resolve(),
                      Path(native.__file__).resolve(), path, window_path, replacement_path)}
    bundle.stamps[replacement_path] = native.file_stamp(replacement_path)
    bundle.stamps[window_path] = native.file_stamp(window_path)
    order.flags.writeable = False
    bundle.starts = order
    contract = dict(tag=TAG, inputs=selection, sources=pins, original_binding_sha256=bound["binding_sha256"],
                    corpus_sha256=bundle.digest, coverage=coverage, original_report=baseline_report,
                    maximum_card_mib=native.CARD_LIMIT_MIB)
    return bundle, bound, baseline_training, contract


def worker(path, checksum, _resume, record, cutoff):
    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        bundle, baseline, original, contract = prepare()
        if json.loads(native.manifest_bytes(path, checksum)) != contract or time.time() >= cutoff:
            raise ValueError("the source and actual raw positions must match the preflight")
        if torch.cuda.device_count() != 1:
            raise ValueError("the approved GPU must be uniquely visible")
        torch.set_num_threads(baseline["runtime"]["threads"])
        torch.set_num_interop_threads(baseline["runtime"]["interop_threads"])
        free, total = torch.cuda.mem_get_info()
        budget = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("the GPU has no approved headroom")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        original_bind = state_tools.make_binding

        def bind(plan, recipe, cache, device):
            current = original_bind(plan, dict(recipe, **{RECIPE_KEY: contract}), cache, device)
            old_recipe, new_recipe = dict(baseline["recipe"]), dict(current["recipe"])
            old_recipe.pop("tag")
            if (new_recipe.pop("tag") != TAG or new_recipe.pop(RECIPE_KEY) != contract
                    or old_recipe != new_recipe
                    or any(current[key] != baseline[key] for key in ("plan", "cache", "runtime", "sources"))):
                raise ValueError("baseline and treatment must use the same recipe, runtime and train code")
            native.publish(record / "binding_comparison.json", dict(matched_except_raw_positions=True,
                           baseline=baseline["binding_sha256"], treatment=current["binding_sha256"]))
            return current

        native.publish(record / "input.json", dict(manifest_sha256=bundle.digest, steps=bundle.steps,
                       raw_tokens=contract["original_report"]["raw_tokens"],
                       course_tokens=bundle.manifest["course_tokens"], raw_window_sha256=contract["inputs"]["raw_positions_sha256"]))
        with patch.object(mixed, "TAG", TAG), patch.object(state_tools, "make_binding", bind):
            mixed.train_bundle(bundle, record, cutoff, flash=True, sft_share=.25, decimal_weight=.02)

        observed = prep.read_json(record / "training.json")
        fields = ("index", "source_update", "raw_targets", "course_tokens", "answer_start_targets",
                  "answer_body_targets", "answer_eot_targets", "contrast_questions", "decimal_targets")
        if (observed["updates"] != original["updates"] or len(observed["exposure"]) != bundle.steps
                or any(a[key] != b[key] for a, b in zip(observed["exposure"], original["exposure"], strict=True)
                       for key in fields)):
            raise ValueError("the completed treatment changed non-window exposures or visit routes")
        native.publish(record / "raw_comparison_ready.json",
                       dict(status="NONOVERLAP_TRAINING_COMPLETE", raw=contract["coverage"][-1],
                            evaluation_sha256=observed["evaluation_sha256"], official_evaluation="PENDING"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.mode == "prepare":
        _, _, _, contract = prepare()
        native.publish(args.profile, contract)
        print(prep.sha(args.profile), contract["coverage"][-1], flush=True)
        return 0
    if (args.profile_sha256 is None or args.stop_by is None or args.stop_by.tzinfo is None
            or args.stop_by > STOP or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("one GPU, an exact preflight profile and the approved end time are required")
    with (patch.object(native, "gpu_worker", worker),
          patch.object(native, "gpu_status", partial(telemetry.gpu_status, RECORD))):
        return native.supervise(args.profile, args.profile_sha256, False, RECORD, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
