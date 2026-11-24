"""Use the closed native pilot control for one additional fresh G4 training arm."""

from contextlib import redirect_stdout, redirect_stderr
import argparse
import os
from pathlib import Path
import time
from unittest.mock import patch

from scripts import run_p109b_folded_ste_learning_pilot as pilot
from scripts import run_p109b_scratch_pair_20261120 as pair


OUT = pair.ROOT / "test_result/evidence/p109b_micro_ste_matched_learning_20261120"
BASE = pilot.OUT
TAG = "p109b_per_micro_ste_chat32_pilot"
BALANCED_OUT = pair.ROOT / "test_result/evidence/p109b_balanced_second_pass_learning_v2_20261120"
BALANCED_TAG = "p109b_balanced_second_pass_chat32_pilot_v2"


def wait_for_control():
    while time.time() + 550 < pilot.END:
        prior = BASE / "report.json"
        if prior.is_file() and prior.read_bytes().endswith(bytes([10])):
            if not pilot.read(prior)["complete"]:
                raise ValueError("the exact native pilot control is unavailable")
            try:
                pair.idle_gpu()
            except RuntimeError:
                time.sleep(3)
                continue
            return
        time.sleep(10)
    raise TimeoutError("the remaining approved window does not fit one fresh pilot arm")


def main(balanced):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise ValueError("explicit device selection required")
    wait_for_control()
    from scripts import p109_train_visit_policy as route
    from scripts import p070b_cla_routes as cla
    from scripts.diag_p109b_second_pass_balance import balanced_orders
    from scripts.diag_p109b_ste_exact_micro import UpdateQuantizationReuse

    output, tag = (BALANCED_OUT, BALANCED_TAG) if balanced else (OUT, TAG)
    original = pilot.commands
    args = original("ordinary")
    args[args.index("--tag")+1] = tag
    baseline = pilot.read(BASE / "profile.json")["commands"]["ordinary"]
    expected = args.copy()
    expected[expected.index("--tag")+1] = baseline[baseline.index("--tag")+1]
    if baseline != expected:
        raise ValueError("data, policy or the companion optimization differs")

    class ReuseG4(route.RoutedG4):
        def __init__(self, cfg):
            super().__init__(cfg)
            self.update_cache = None

        def clear_quant(self):
            self.update_cache = None
            return super().clear_quant()

        def refresh_quant(self):
            if not self.training:
                return super().refresh_quant()
            if self.update_cache is None:
                self.update_cache = UpdateQuantizationReuse(self)
                cache_updates.append(self.training_route)
            self.update_cache.refresh()

    cache_updates = []
    balanced_updates = []
    native_route = route.route_for
    balanced_policy = "balanced_second_pass_r2"

    def make_route(cfg, owners, policy, seed, index, steps):
        original = native_route(cfg, owners, "uniform_r2", seed, index, steps)
        _, groups, _ = cla.middle_units(cfg, owners)
        if policy != balanced_policy or seed != 1337 or len(groups) != 6:
            raise ValueError("the frozen six-group 1337 candidate is required")
        offset = cfg.n_prelude + cfg.n_middle
        stage, position = divmod(index, len(groups))
        current = balanced_orders(stage)[position]
        schedule = [*original[:offset], *(layer for group in current for layer in groups[group]),
                    *original[offset+cfg.n_middle:]]
        cla.trace(cfg, owners, schedule)
        balanced_updates.append(index)
        return tuple(schedule)

    directory = output / "ordinary"
    directory.mkdir(parents=True, exist_ok=False)
    source = Path(pilot.__file__)
    pair.publish(output / "profile.json", {"runner_sha256": pair.file_sha(source), "command": args,
                 "baseline_sha256": pair.file_sha(BASE/"report.json"),
                 "technique": balanced_policy if balanced else "per-micro STE, reusable tensors"})
    model_type = route.RoutedG4 if balanced else ReuseG4
    policy = balanced_policy if balanced else pilot.POLICY
    build_route = make_route if balanced else native_route
    with (directory.joinpath("stdout.txt").open("x", encoding="utf-8", buffering=1) as stream,
          redirect_stdout(stream), redirect_stderr(stream), patch.object(pilot, "OUT", output),
          patch.object(pilot, "commands", return_value=args), patch.object(route, "RoutedG4", model_type),
          patch.object(pilot, "POLICY", policy), patch.object(route, "POLICIES", (*route.POLICIES, balanced_policy)),
          patch.object(route, "route_for", build_route)):
        pilot.worker("ordinary")
    initial = pilot.read(directory / "initial.json")
    reference = pilot.read(BASE / "report.json")
    log_path = directory / f"m100s12_g4_ko-en_10M_{tag}.json"
    trained = pilot.read(log_path)
    native = pilot.read(next((BASE/"ordinary").glob("m100s12_g4_ko-en_10M_*ordinary.json")))
    applied = len(balanced_updates) if balanced else len(cache_updates)
    if (initial != reference["initial"] or applied != pilot.STEPS
            or native["context_source_cursor"] != trained["context_source_cursor"]):
        raise ValueError("control initializer, same data or update boundaries differ")
    result = {"complete": True, "targets": trained["tokens"], "updates": pilot.STEPS,
              "controlled_candidate_updates": applied, "final": trained["final"],
              "baseline_final": native["final"], "validation_delta": trained["final"]["val_loss"]-native["final"]["val_loss"],
              "step_medians_ms": [native["ms_step_median"], trained["ms_step_median"]],
              "peak_reserved_gib": trained["vram_reserved_gb"],
              "candidate_log_sha256": pair.file_sha(log_path)}
    pair.publish(output / "report.json", result)
    print("P109B_PILOT_FINAL", result, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--balanced-second-pass", action="store_true")
    main(parser.parse_args().balanced_second_pass)
