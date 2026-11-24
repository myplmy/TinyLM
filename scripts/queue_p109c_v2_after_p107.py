"""Run the sealed P109C technical gate and full training after the owned P107 GPU return."""

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys

from scripts import wait_p109_cuda_return as returned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--probe-record", required=True, type=Path)
    parser.add_argument("--record", required=True, type=Path)
    parser.add_argument("--until", required=True, type=datetime.fromisoformat)
    parser.add_argument("--evaluation-python", type=Path, required=True)
    parser.add_argument("--evaluation-profile", type=Path, required=True)
    parser.add_argument("--evaluation-profile-sha256", required=True)
    parser.add_argument("--evaluation-record", type=Path, required=True)
    parser.add_argument("--evaluation-until", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    after = args.after.resolve(strict=True)
    if (args.until.tzinfo is None or args.evaluation_until.tzinfo is None or args.evaluation_until <= args.until
            or args.pid <= 0 or not after.name.startswith("p107_v11_mask_pair300_")
            or after.parent != returned.EVIDENCE):
        parser.error("the queue needs an owned P107 evidence record, PID and authorized deadline")
    records = (args.probe_record.absolute(), args.record.absolute(), args.evaluation_record.absolute())
    if (len(set(records)) != len(records) or any(p.parent != returned.EVIDENCE or p.exists() or p.is_symlink()
                                       or not p.name.startswith("p109c_") for p in records)):
        parser.error("the output records must be fresh distinct P109C evidence paths")
    common = (
        "--manifest", str(args.manifest.absolute()), "--manifest-sha256", args.manifest_sha256,
        "--source-sha256", args.source_sha256,
    )

    def train(mode, path, stop):
        print("P109C_V2_QUEUE_START", mode, datetime.now(args.until.tzinfo).isoformat(), path, flush=True)
        return subprocess.run(
            (sys.executable, "-X", "utf8", "-B", "-m", "scripts.run_p109c_scratch_mixed", mode, *common,
             "--record", str(path), "--stop-by", stop.isoformat()),
            cwd=returned.ROOT, check=False,
        ).returncode

    print("P109C_V2_QUEUE_WAIT", after, args.pid, flush=True)
    returned.wait_for_return(after / "supervisor.json", args.pid, args.until)
    previous = json.loads((after / "report.json").read_text(encoding="utf-8"))
    if previous["status"] not in ("FULL_300M_PAIR", "MATCHED_PARTIAL_BUDGET_PAIR"):
        raise ValueError("the preceding run did not close a matched research boundary")
    stop = min(args.until, datetime.now(args.until.tzinfo) + timedelta(minutes=4))
    probe, record, evaluation = records
    if code := train("probe", probe, stop):
        return code
    terminal = json.loads((probe / "supervisor.json").read_text(encoding="utf-8"))
    returned.wait_for_return(probe / "supervisor.json", terminal["pid"], args.until)
    measured = json.loads((probe / "report.json").read_text(encoding="utf-8"))
    if (measured["status"] != "TECHNICAL_PROBE_COMPLETE"
            or measured["input_manifest_sha256"] != args.manifest_sha256.upper()
            or measured["loss_contract"]["source_sha256"] != args.source_sha256.upper()):
        raise ValueError("P109C full training requires a successful technical gate for these sealed inputs")
    if code := train("run", record, args.until):
        return code
    print("P109C_V2_QUEUE_START", "evaluation", datetime.now(args.until.tzinfo).isoformat(), evaluation, flush=True)
    return subprocess.run(
        (str(args.evaluation_python.absolute()), "-X", "utf8", "-B", "-m", "scripts.resume_p109c_v2_common_eval", "--fresh",
         "--profile", str(args.evaluation_profile.absolute()), "--profile-sha256", args.evaluation_profile_sha256,
         "--record", str(evaluation), "--stop-by", args.evaluation_until.isoformat()),
        cwd=returned.ROOT, check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
