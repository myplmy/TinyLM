"""Resume the interrupted raw-window comparison from its committed native checkpoint."""

import argparse
from datetime import datetime
from functools import partial
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import torch

from scripts import p109_eval_resilient_supervisor as supervisor
from scripts import run_p109c_v2_raw_nonoverlap as treatment
from tinylm.train.context_micro_tokens import MicroTokensCursor, parse_context_plan


prep, native, mixed, state_tools = treatment.prep, treatment.native, treatment.mixed, treatment.state_tools
TAG = "p109c_v2_raw_nonoverlap_resumed_chat32_s1337_v1_20261124"
RECORD = prep.EVIDENCE / TAG
ORIGINAL = treatment.RECORD
PROFILE = prep.ROOT / "handoff/audit/P109C_V2_RAW_NONOVERLAP_FULL_20261124.json"
EXPOSURE = ("index", "source_update", "ce_weights", "raw_targets", "course_tokens", "answer_start_targets",
            "answer_body_targets", "answer_eot_targets", "decimal_targets", "contrast_questions", "n_valid")


def prepare():
    bundle, baseline_binding, baseline, original = treatment.prepare()
    profile_sha = prep.sha(PROFILE)
    receipt = prep.read_json(ORIGINAL / "supervisor.json")
    binding_receipt = prep.read_json(ORIGINAL / "binding_comparison.json")
    if (json.loads(native.manifest_bytes(PROFILE, profile_sha)) != original or receipt["returncode"] != -15
            or "no valid NVML card sample" not in (receipt["stop_reason"] or "")
            or receipt["card_after_exit"].get("compute_pids") != [] or not binding_receipt["matched_except_raw_positions"]
            or binding_receipt["baseline"] != baseline_binding["binding_sha256"]
            or any((ORIGINAL / name).exists() for name in ("report.json", "training.json", "evaluation.pt"))):
        raise ValueError("the original record must be the known incomplete returned comparison")
    _, display = mixed.native_commands(bundle, treatment.TAG, True)
    checkpoint = ORIGINAL / "ckpt" / f"{native.PRESET}_ko-en_{display}_{treatment.TAG}.pt"
    if checkpoint.resolve(strict=True) != checkpoint or not checkpoint.is_file():
        raise ValueError("the owned original full checkpoint must be a regular file")
    checkpoint_sha = prep.sha(checkpoint)
    payload = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    context = payload[mixed.trainer.CONTEXT_STATE_KEY]
    current = context["binding"]
    step = payload["step"]
    plan = parse_context_plan(f"{bundle.steps}:{prep.WIDTH}", micro_bs=prep.BATCH,
                              accum=prep.ACCUM, seq=prep.WIDTH, steps=bundle.steps)
    sampler = SimpleNamespace(bs=prep.BATCH, seq=prep.WIDTH, rng=np.random.default_rng())
    cursor = MicroTokensCursor(plan, sampler, source_sha256=bundle.cache["identity_sha256"])
    cursor.load_state_dict(context["cursor"])
    np.random.default_rng().bit_generator.state = context["validation_rng"]
    state_tools._validate_binding(current)
    state_tools.validate_trainer_control(context["control"], step, cursor.next_update)
    torch.Generator(device="cpu").set_state(context["cpu_rng"])
    state_tools._rng_tensor(context["cuda_rng"])
    if (not 0 < step < bundle.steps or current["binding_sha256"] != binding_receipt["treatment"]
            or current["recipe"][treatment.RECIPE_KEY] != original or current["cache"] != bundle.cache
            or current["plan"] != plan.contract() or context["payload_sha256"] != state_tools._payload_sha(context)
            or step != cursor.next_update or step != context["cursor"]["cursor"]["optimizer_updates"]
            or context["control"]["n_skip"] or payload["tokenizer_sha256"] != prep.TOKENIZER_SHA
            or not all(payload.get(key) for key in ("model", "opt", "opt_muon"))):
        raise ValueError("the exact treatment recipe, cursor, RNG and optimizer state are required")

    journal = ORIGINAL / "updates.jsonl"
    raw = journal.read_bytes()
    lines = raw.splitlines(keepends=True)
    rows = [json.loads(line) for line in lines]
    if not step <= len(rows) < bundle.steps or not raw.endswith(b"\n") or any(
            any(row[k] != baseline["exposure"][i][k] for k in EXPOSURE) for i, row in enumerate(rows)):
        raise ValueError("the source applied-update journal is incomplete or its invariant exposures changed")
    proof = dict(tag=TAG, original_record=str(ORIGINAL), original_profile=str(PROFILE),
                 original_profile_sha256=profile_sha, original_terminal_sha256=prep.sha(ORIGINAL / "supervisor.json"),
                 original_runner_sha256=prep.sha(Path(treatment.__file__).resolve()),
                 source_sha256=prep.sha(Path(__file__).resolve()), checkpoint=str(checkpoint),
                 checkpoint_sha256=checkpoint_sha, binding_sha256=current["binding_sha256"],
                 payload_sha256=context["payload_sha256"], applied_at_checkpoint=step, expected_total=bundle.steps,
                 observed_before_stop=len(rows), replay_after_checkpoint=len(rows) - step,
                 prefix_exposure_sha256=sha256(b"".join(lines[:step])).hexdigest().upper(),
                 original_peak_card_mib=receipt["peak_card_mib"])
    bundle.unchanged()
    return proof, rows[:step], baseline["updates"]


def pulse(record, stop):
    journal, heartbeat = record / "updates.jsonl", record / "progress.jsonl"
    last = None
    with heartbeat.open("x", buffering=1, encoding="utf-8") as stream:
        while not stop.wait(1.):
            if not journal.is_file():
                continue
            length = journal.stat().st_size
            if length != last:
                print(json.dumps(dict(suffix_journal_bytes=length)), file=stream, flush=True)
                last = length


def worker(profile, digest, _resume, record, cutoff):
    sealed = json.loads(native.manifest_bytes(profile, digest))
    checked, prefix, routes = prepare()
    if sealed != checked:
        raise ValueError("the original evidence or exact recovery changed")
    step = checked["applied_at_checkpoint"]
    path = Path(checked["checkpoint"])
    original_train, publish = mixed.train_bundle, native.publish

    def publish_recovered(output, value):
        if output == record / "training.json":
            binding = prep.read_json(record / "binding_comparison.json")
            if (binding["treatment"] != checked["binding_sha256"] or value["updates"] != routes[step:]
                    or any(a["index"] != b["index"] for a, b in zip(value["updates"], value["exposure"], strict=True))):
                raise ValueError("the recovery did not continue the unchanged uniform route and exact native cursor")
            # The earlier cursor certifies completed updates. Its uniform route is fixed by the sealed binding.
            value.update(updates=routes[:step] + value["updates"], exposure=prefix + value["exposure"],
                         layer_token_visits=sum(row["draw_tokens"] * row["visits"] for row in routes),
                         recovery=dict(**checked, suffix_updates=len(value["updates"]),
                                       prefix_route_source="VERIFIED_UNIFORM_BINDING_AND_APPLIED_CURSOR"))
        publish(output, value)

    publish(record / "resume_prefix.json", checked)
    stop = Event()
    thread = Thread(target=pulse, args=(record, stop), daemon=True)
    thread.start()
    try:
        with (patch.object(mixed, "train_bundle", partial(original_train, resume_from=(path, checked["checkpoint_sha256"]))),
              patch.object(native, "publish", publish_recovered)):
            treatment.worker(Path(checked["original_profile"]), checked["original_profile_sha256"], True, record, cutoff)
        if prep.sha(path) != checked["checkpoint_sha256"]:
            raise ValueError("the original checkpoint changed during recovery")
    finally:
        stop.set()
        thread.join(2.)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "run"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        checked, _, _ = prepare()
        native.publish(args.profile, checked)
        print(prep.sha(args.profile), checked["applied_at_checkpoint"], checked["observed_before_stop"], flush=True)
        return 0
    if (not args.profile_sha256 or not args.stop_by or not args.stop_by.tzinfo or args.stop_by > treatment.STOP
            or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("the exact resume preflight, approved GPU and cutoff are required")
    return supervisor.supervise(worker, args.profile.absolute(), args.profile_sha256, RECORD, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
