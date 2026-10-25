#!/usr/bin/env python3
"""Admit full arms only from actual closed paired cost observations."""
from pathlib import Path
from types import SimpleNamespace
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_native_format_training as train

def main():
    base = Path(__file__).resolve().parent
    inputs, _ = train.read(str((base / "native_training_inputs_v1.json").relative_to(ROOT)),
        "850EA5767D568C58907C085A9053E8343F6FC3D5B309E81813CB89462B7A411F")
    args = SimpleNamespace(mode="cost", profile=inputs["profile"]["path"],
        profile_sha256=inputs["profile"]["sha256"], f4=inputs["f4"]["path"],
        f4_sha256=inputs["f4"]["sha256"])
    state = train.metadata(args)
    costs, estimates, observations = {}, {}, {}
    for arm in ("format_muon", "format_normuon"):
        folder = ROOT / "test_result/evidence" / (train.PREFIX + arm + "_cost")
        spec = json.loads((folder / "root_closed_ref.json").read_text())
        closed = train.read_closed(spec, state, arm, "cost")
        floor = train.forecasts(closed["worker"], closed["root_actual_parent_wall_seconds"])
        costs[arm] = spec
        estimates[arm] = float(floor + 600)
        child = closed["worker"]
        observations[arm] = {"actual_parent_seconds": closed["root_actual_parent_wall_seconds"],
            "preparation_seconds": child["pre_training_seconds"], "step_seconds": child["step_seconds"],
            "late_seconds": child["late"]["seconds"], "primary_peak": child["primary_peak"],
            "full_forecast_floor_sec": floor, "no_quality_decision": True}
    value = {"schema": "P106B_NATIVE_FORMAT_COST_ADMISSION_V1", "root_approved": True,
        "source_sha256": state["source_identity"]["sha256"], "profile_sha256": state["profile_sha256"],
        "f4_sha256": state["f4_sha256"], "pair_complete_sha256": state["complete_sha256"],
        "admitted_arms": ["format_muon", "format_normuon"], "cost_reports": costs,
        "conservative_seconds_by_arm": estimates, "unmeasured_post_training_reserve_sec_per_arm": 600,
        "actual_cost_observations": observations, "written_epoch": time.time(),
        "prediction_not_guarantee": True, "small_run_quality_selection": False}
    path = base / "native_training_cost_admission_v1.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
    args.mode, args.arm = "train", "format_muon"
    args.budget, args.budget_sha256 = str(path.relative_to(ROOT)), train.pair.file_sha(path)
    admission = train.budget_admission(args, state)
    print(json.dumps({"path": args.budget, "sha256": args.budget_sha256, "estimates": estimates,
        "total_forecast_sec": admission["pending_forecast_seconds"],
        "train_window_remaining_sec": train.TRAIN_END.timestamp() - time.time()}, ensure_ascii=False))

if __name__ == "__main__":
    main()
