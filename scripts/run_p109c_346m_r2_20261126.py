"""Launch the previously sealed 346.316M R2 control in the November 26 window."""

from argparse import ArgumentParser
from datetime import datetime
from functools import partial
import os

from scripts import run_p109c_346m_1500_window as original


AUTHORIZED_END = datetime.fromisoformat("2026-11-26T15:00:00+09:00")
PROFILE_SHA256 = "EF8A129EC1C1436E836E0CB76107F4CCA386B751C90E77AA29366521B63FA9EE"


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= AUTHORIZED_END:
        parser.error("use a timezone-aware stop time inside the November 26 authorization")
    if os.sched_getaffinity(0) != original.pair.TRAINING_CPUS or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        parser.error("use logical CPUs 0–13 and CUDA device 0")

    integrated = original.pair.integrated
    tag = original.RECIPES[2]
    evidence = integrated.prep.EVIDENCE
    profile = evidence / f"{tag}_profile.json"
    record = evidence / f"{tag}_run1"
    if record.exists() or record.is_symlink():
        parser.error("the presealed R2 training record must be new")
    worker = partial(integrated.worker, None, make_profile=partial(original.prepare, 2))
    return integrated.supervisor.supervise(worker, profile, PROFILE_SHA256, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
