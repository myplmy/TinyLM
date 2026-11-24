"""Measure a short, fresh G4 learning curve for the non-equivalent folded STE."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from unittest.mock import patch

from scripts import run_p109b_scratch_pair_20261120 as pair


OUT = pair.ROOT / "test_result/evidence/p109b_folded_ste_matched_learning_v2_20261120"
READY = pair.ROOT / "test_result/evidence/p109b_g4_ste_per_micro_exact_cuda_20261120/report.json"
END = datetime.fromisoformat("2026-11-20T16:59:45+09:00").timestamp()
STEPS = 80
ARMS = ("ordinary", "folded")
POLICY = "second_shuffle_r2"
VAL_HOLD = pair.ROOT / "test_result/evidence/p109b_firstpass_team_v1_readback_20261120/v1_1_authorized_followthrough.json"


def read(path):
    return json.loads(path.read_bytes())


def commands(arm):
    args = pair.commands(POLICY) + ["--anneal-start", "0.05"]
    for key, value in {"--tag": f"p109b_folded_ste_chat32_pilot_{arm}", "--tokens": "10M", "--steps": str(STEPS),
                       "--eval-every": "40", "--save-every": "80"}.items():
        args[args.index(key) + 1] = value
    return args


def worker(arm):
    import numpy as np
    import torch

    from scripts import p109_train_visit_policy as route
    from tinylm.train import trainer

    profile = read(OUT / "profile.json")
    if (time.time() >= END or pair.input_pins() != read(pair.OUT / "profile.json")["pins"]
            or profile["runner_sha256"] != pair.file_sha(Path(__file__))):
        raise RuntimeError("authorization or pilot identity changed")
    signal.alarm(max(1, int(END - time.time()) - 1))
    total, used = pair.idle_gpu()
    torch.cuda.set_per_process_memory_fraction((pair.CARD_LIMIT_MIB - used - 512) / total)
    directory = OUT / arm
    original_model, standard_clip, standard_eval = route.RoutedG4, torch.nn.utils.clip_grad_norm_, trainer.evaluate
    standard_loader = trainer.Loader
    exclude_lo, exclude_hi = read(VAL_HOLD)["new_safety_hold_val_tokens"]
    model = None
    vjps = 0

    class ObservedG4(original_model):
        def __init__(self, cfg):
            nonlocal model
            super().__init__(cfg)
            model = self
            pair.publish(directory / "initial.json", {"state_sha256": pair.initial_hash(self)})

        def forward(self, *args, **kwargs):
            if arm == "folded" and self.training and self.training_forwards == 0:
                self.begin_quant_update_cache()
            return super().forward(*args, **kwargs)

    def finish_before_clip(*args, **kwargs):
        nonlocal vjps
        if arm == "folded":
            if model.training_forwards != pair.ACCUM:
                raise RuntimeError("folded VJP requires all of the update microbatches")
            model.finish_quant_update_cache()
            vjps += 1
        return standard_clip(*args, **kwargs)

    def common_evaluate(model, *args, **kwargs):
        with patch.object(model.cfg, "infer_repeat", 2.0):
            return standard_eval(model, *args, **kwargs)

    class FilteredValidation(standard_loader):
        def __call__(self):
            positions = []
            while len(positions) < self.bs:
                offset = int(self.rng.integers(0, len(self.d) - self.seq - 1))
                if offset + self.seq + 1 <= exclude_lo or offset >= exclude_hi:
                    positions.append(offset)
            ids = self.d[np.asarray(positions)[:, None] + np.arange(self.seq + 1)].astype(np.int64)
            matrix = torch.from_numpy(ids).pin_memory().to("cuda", non_blocking=True)
            return matrix[:, :-1], matrix[:, 1:]

    def loader(split, *args, **kwargs):
        constructor = FilteredValidation if split == "val" else standard_loader
        return constructor(split, *args, **kwargs)

    with (patch.object(route, "RoutedG4", ObservedG4), patch.object(trainer, "evaluate", common_evaluate),
          patch.object(trainer, "prepare", pair.bound_prepare(trainer.prepare)),
          patch.object(trainer, "CKPT", directory), patch.object(trainer, "LOGS", directory), patch.object(trainer, "Loader", loader),
          patch.object(torch.nn.utils, "clip_grad_norm_", finish_before_clip)):
        receipt = route.run_native(POLICY, commands(arm))
    if vjps != (STEPS if arm == "folded" else 0):
        raise RuntimeError("folded quantization did not run exactly once per update")
    pair.publish(directory / "worker.json", {**receipt, "vjps": vjps, "excluded_val_token_range": [exclude_lo, exclude_hi],
                 "peak_allocated_mib": torch.cuda.max_memory_allocated() / 2**20,
                 "peak_reserved_mib": torch.cuda.max_memory_reserved() / 2**20})


def supervise(arm, telemetry):
    directory = OUT / arm
    directory.mkdir(exist_ok=False)
    peak = 0
    start = time.time()
    stop = None
    with (directory / "stdout.txt").open("x", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-B", "-u", "-m", "scripts.run_p109b_folded_ste_learning_pilot",
                                    "worker", arm], cwd=pair.ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                now = time.time()
                if now >= END:
                    stop = "TIME_LIMIT"
                    break
                _, used, utilization = pair.gpu_status()
                peak = max(peak, used)
                print(f"{now:.3f},{arm},{process.pid},{used},{utilization}", file=telemetry, flush=True)
                if used > pair.CARD_LIMIT_MIB:
                    stop = "CARD_MEMORY_LIMIT"
                    break
                time.sleep(2)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
            code = process.wait()
    result = dict(arm=arm, returncode=code, seconds=time.time() - start, stop=stop, peak_card_mib=peak)
    pair.publish(directory / "supervisor.json", result)
    return result


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("one explicit CUDA device required")
    while time.time() + 1000 < END:
        if READY.is_file() and READY.read_bytes().endswith(bytes([10])):
            break
        time.sleep(15)
    else:
        raise TimeoutError("insufficient authorized time for both fresh pilot arms")
    for _ in range(4):
        try:
            pair.idle_gpu()
            break
        except RuntimeError:
            time.sleep(3)
    pair.idle_gpu()
    OUT.mkdir(exist_ok=False)
    pair.publish(OUT / "profile.json", {"approval": "WIP 183", "commands": {arm: commands(arm) for arm in ARMS},
                 "cutoff": END, "main_profile_sha256": pair.file_sha(pair.OUT / "profile.json"),
                 "runner_sha256": pair.file_sha(Path(__file__)),
                 "control": "same native optimization and shuffle; fold changed only in the candidate"})
    status = []
    with (OUT / "device.csv").open("x", encoding="utf-8") as telemetry:
        print("epoch,arm,worker_pid,card_used_mib,utilization", file=telemetry, flush=True)
        for arm in ARMS:
            print("START_FOLDED_STE_PILOT", arm, flush=True)
            row = supervise(arm, telemetry)
            status.append(row)
            if row["returncode"]:
                break
    complete = len(status) == 2 and all(not row["returncode"] for row in status)
    report = {"complete": complete, "supervised": status}
    if complete:
        cores = [OUT / arm for arm in ARMS]
        previous, folded = [read(next(base.glob("m100s12_g4_ko-en_10M_*.json"))) for base in cores]
        initials = [read(base / "initial.json") for base in cores]
        if initials[0] != initials[1] or previous["context_source_cursor"]["cursor"]["rng"] != folded["context_source_cursor"]["cursor"]["rng"]:
            raise RuntimeError("fresh state and actual fixed data stream must agree")
        report.update(initial=initials[0], baseline=previous["final"], folded=folded["final"],
                      skipped_updates=[previous["n_skip"], folded["n_skip"]],
                      optimizer_updates=[value["context_source_cursor"]["cursor"]["optimizer_updates"]
                                         for value in (previous, folded)],
                      validation_delta=folded["final"]["val_loss"] - previous["final"]["val_loss"],
                      actual_targets_per_arm=STEPS * pair.MICRO * pair.ACCUM * pair.SEQ,
                      step_medians_ms=[previous["ms_step_median"], folded["ms_step_median"]])
    pair.publish(OUT / "report.json", report)
    if not complete:
        raise RuntimeError("paired learning pilot was interrupted")
    print("P109B_FOLDED_PILOT_FINAL", report, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("wait", "worker"))
    parser.add_argument("arm", choices=ARMS, nargs="?")
    cli = parser.parse_args()
    if cli.phase == "wait":
        main()
    elif cli.arm:
        worker(cli.arm)
    else:
        parser.error("worker requires an arm")
