"""Read back the actual native GPU logs and execution receipts for WIP 182."""

from collections import Counter
import csv
from datetime import datetime
import json
from pathlib import Path
from statistics import median

from scripts import run_p109b_scratch_pair_20261120 as pair


def read(path):
    return json.loads(path.read_bytes())


def summarize():
    profile = read(pair.OUT / "profile.json")
    queue = read(pair.OUT / "queue.json")
    if not queue["complete"] or tuple(row["policy"] for row in queue["arms"]) != tuple(pair.ARMS):
        raise ValueError("two completed arms in their original order are required")
    if profile["pins"] != pair.input_pins() or profile["commands"] != {p: pair.commands(p) for p in pair.ARMS}:
        raise ValueError("the authorized profile changed")
    columns = {policy: [] for policy in pair.ARMS}
    with (pair.OUT / "device.csv").open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            columns[row["policy"]].append(row)

    arms, native, initials = {}, {}, []
    previous_end = 0
    expected_targets = pair.STEPS * pair.MICRO * pair.ACCUM * pair.SEQ
    for owner in queue["arms"]:
        policy = owner["policy"]
        base = pair.OUT / policy
        initials.append(read(base / "initial.json")["state_dict_sha256"])
        if (owner != read(base / "supervisor.json") or owner["returncode"] != 0 or owner["stop_reasons"]
                or not previous_end <= owner["started"] < owner["ended"] <= pair.CUTOFF):
            raise ValueError("the recorded GPU window or process exit differs")
        previous_end = owner["ended"]
        worker = read(base / "worker.json")
        rows = worker["updates"]
        if (worker["policy"]["policy"] != policy or len(rows) != pair.STEPS
                or worker["layer_token_visits"] != 28 * expected_targets
                or any((row["index"], row["visits"], row["draw_tokens"], row["optimizer_applied"])
                       != (i, 28, expected_targets // pair.STEPS, True) for i, row in enumerate(rows))):
            raise ValueError("declared finite optimizer and input accounting differs")
        name = f"m100s12_g4_ko-en_300M_{pair.ARMS[policy]}"
        log = pair.ROOT / "runs" / "logs" / (name + ".json")
        ckpt = pair.ROOT / "runs" / "ckpt" / (name + ".pt")
        result = read(log)
        cursor = result["context_source_cursor"]["cursor"]
        if (not ckpt.is_file() or cursor["draw_tokens"] != expected_targets
                or cursor["ntp_targets"] != expected_targets or cursor["optimizer_updates"] != pair.STEPS
                or result["n_skip"] or result["context_resume_start_step"] != 0 or result["init_from"] or result["kd"]):
            raise ValueError("a native log or final checkpoint cannot certify a fresh 300M arm")
        samples = columns[policy]
        if (not samples or any(int(row["worker_pid"]) != owner["pid"] for row in samples)
                or max(int(row["card_used_mib"]) for row in samples) != owner["peak_card_mib"]
                or owner["peak_card_mib"] > pair.CARD_LIMIT_MIB):
            raise ValueError("unverified device telemetry or limit exceeded")
        arms[policy] = dict(tag=owner["tag"], log=log.relative_to(pair.ROOT).as_posix(),
            log_sha256=pair.file_sha(log), checkpoint=ckpt.relative_to(pair.ROOT).as_posix(),
            checkpoint_sha256=pair.file_sha(ckpt), updates=pair.STEPS, draw_tokens=expected_targets,
            layer_token_visits=worker["layer_token_visits"], optimizer_skips=result["n_skip"],
            final=result["final"], history=result["history"], median_update_ms=result["ms_step_median"],
            median_update_measurements=result["ms_step_n"], trainer_wall_seconds=result["wall_sec"],
            supervised_wall_seconds=owner["ended"] - owner["started"],
            started=datetime.fromtimestamp(owner["started"]).astimezone().isoformat(),
            ended=datetime.fromtimestamp(owner["ended"]).astimezone().isoformat(),
            peak_card_mib=owner["peak_card_mib"], device_samples=len(samples),
            median_card_utilization_pct=median(int(row["utilization"]) for row in samples),
            unique_routes=len(Counter(row["route_sha256"] for row in rows)),
            peak_allocated_mib=worker["peak_allocated_mib"], peak_reserved_mib=worker["peak_reserved_mib"],
            intermediate_steps=[step for step in (572, 1144, 1716) if (base / f"aoa_step_{step}.pt").is_file()])
        native[policy] = result

    first, second = pair.ARMS
    fields = ("preset", "data", "params", "seed", "steps", "seq", "micro_bs", "accum", "pool_tokens", "exact_cache",
              "grad_ckpt", "optimizer", "muon_scale", "muon_lr_mult", "train_repeat", "cla_group", "mlp_group",
              "sched", "lr", "tokenizer_sha256", "ce_recompute_rows", "context_cache_identity", "context_curriculum",
              "context_source_cursor", "bytes_per_token", "save_every", "eval_every")
    matches = all(native[first][key] == native[second][key] for key in fields)
    if initials[0] != initials[1] or not matches or (arms[first]["unique_routes"], arms[second]["unique_routes"]) != (1, 691):
        raise ValueError("the underlying native optimized inputs, initial values, or routes differ")
    delta = {key: arms[second]["final"][key] - arms[first]["final"][key] for key in ("val_loss", "ppl", "bpb")}
    return dict(complete=True, arms=arms, common_initial_state_sha256=initials[0], fixed_native_axes=list(fields),
                common_final_source_state_sha256=native[first]["context_source_cursor"]["state_sha256"],
                validation_draw_targets=100 * pair.MICRO * pair.SEQ, candidate_minus_control=delta,
                profile_sha256=pair.file_sha(pair.OUT / "profile.json"), queue_sha256=pair.file_sha(pair.OUT / "queue.json"))


if __name__ == "__main__":
    result = summarize()
    pair.publish(Path(pair.OUT / "readback.json"), result)
    print(result["candidate_minus_control"])
