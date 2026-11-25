"""Prepare and run the P109C 346.316M arm with an earlier return to raw R2."""

from argparse import ArgumentParser
from datetime import datetime
from functools import partial
import json
import os
from pathlib import Path

import numpy as np

from scripts import run_p109c_346m_1500_window as previous


TAG = "p109c_346m_r1thenr2_60_20261126_chat32"
AUTHORIZED_END = datetime.fromisoformat("2026-11-26T15:00:00+09:00")
BOUNDARY = 1753
PREFIX_TARGETS = 179_986_432
EVAL_PROFILE_SHA = "64C6F17853FABEDBBE4DC513FF9DDCE2BCF34F0911B271038CEC03B08076F37C"


def prepare(*curriculum):
    profile, bundle, slots, policy = previous.prepare(1, *curriculum)
    integrated = previous.pair.integrated
    raw_by_update = np.count_nonzero(bundle.schedule[:, :, 0] == -1, axis=1) * integrated.base.MICRO_TOKENS
    prefix = np.concatenate(([0], np.cumsum(raw_by_update)))
    boundary = int(np.abs(5 * prefix - 3 * prefix[-1]).argmin())
    if boundary != BOUNDARY or int(prefix[boundary]) != PREFIX_TARGETS:
        raise ValueError("the nearest 60% boundary differs from the frozen exposure")
    signature = profile["signature"]
    signature["raw_visit_schedule"].update(boundary=boundary, prefix_raw_targets=int(prefix[boundary]))
    source = Path(__file__).resolve()
    signature["sources"][source.relative_to(integrated.prep.ROOT).as_posix()] = integrated.prep.sha(source)
    profile["tag"] = TAG
    return profile, bundle, slots, policy


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    integrated = previous.pair.integrated
    evidence = integrated.prep.EVIDENCE
    profile_path = evidence / f"{TAG}_profile.json"
    record = evidence / f"{TAG}_run1"
    if args.mode == "prepare":
        if args.profile_sha256 or args.stop_by or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
            parser.error("profile preparation requires a CPU-only device mask")
        profile, *_ = prepare(*previous.pair.FIXED_CURRICULUM)
        source = evidence / "p109c_346m_r1thenr2_20261125_chat32_common_eval_ko_first_profile.json"
        official = json.loads(integrated.native.manifest_bytes(source, EVAL_PROFILE_SHA))
        if official["training_manifest_sha256"] != profile["signature"]["manifest_sha256"]:
            raise ValueError("the new arm does not share the frozen validation conditions")
        official.update(training_tag=TAG, training_record=str(record))
        official_path = evidence / f"{TAG}_common_eval_profile.json"
        if any(path.exists() or path.is_symlink() for path in (profile_path, official_path, record)):
            parser.error("the 60% records must be new")
        integrated.native.publish(profile_path, profile)
        integrated.native.publish(official_path, official)
        for path in (profile_path, official_path):
            print(path.name, integrated.prep.sha(path), flush=True)
        return 0

    if (args.stop_by is None or args.stop_by.tzinfo is None
            or not datetime.now().astimezone() < args.stop_by <= AUTHORIZED_END
            or not args.profile_sha256 or os.sched_getaffinity(0) != previous.pair.TRAINING_CPUS
            or os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or record.exists() or record.is_symlink()):
        parser.error("use the sealed arm, new record, CPUs 0–13, CUDA device 0 and a November 26 cutoff")
    worker = partial(integrated.worker, None, make_profile=prepare)
    return integrated.supervisor.supervise(worker, profile_path, args.profile_sha256, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
