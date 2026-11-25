"""Run each admitted P109C 346M raw-visit arm with the original v3 trainer."""

import argparse
from datetime import datetime
from functools import partial
import os
from pathlib import Path

import numpy as np

from scripts import run_p109c_integrated_scratch as integrated


RECIPES = {2: "p109c_346m_r2_20261125", 1: "p109c_346m_r1thenr2_20261125"}
FIXED_CURRICULUM = ("original", "capped", "proportional", 0., True)
AUTHORIZATION_END = datetime.fromisoformat("2026-11-25T13:00:00+09:00")
TRAINING_CPUS = set(range(14))
TARGET_PREFIX = 209_969_152
BOUNDARY = 2050


def prepare(early_repeat, *curriculum):
    if curriculum != FIXED_CURRICULUM:
        raise ValueError("both raw visit arms require the original integrated v3 curriculum")
    profile, bundle, slots, policy = integrated.prepare(*curriculum)
    raw_targets = np.count_nonzero(bundle.schedule[:, :, 0] == -1, axis=1) * integrated.base.MICRO_TOKENS
    prefix = np.concatenate(([0], np.cumsum(raw_targets)))
    reference = int(np.abs(prefix * 10 - prefix[-1] * 7).argmin())
    if (bundle.steps != 2942 or reference != BOUNDARY or prefix[reference] != TARGET_PREFIX
            or int(prefix[-1]) != 300_023_808 or profile["totals"]["course_inputs"] != 46_292_274):
        raise ValueError("the original v3 exposure or nearest 70% raw boundary has changed")
    source = Path(__file__).resolve()
    signature = profile["signature"]
    signature["sources"][source.relative_to(integrated.prep.ROOT).as_posix()] = integrated.prep.sha(source)
    signature["raw_visit_schedule"] = dict(boundary=reference, prefix_raw_targets=int(prefix[reference]),
                                           early_repeat=early_repeat, late_repeat=2, course_repeat=2)
    signature["supervision"] = dict(cpu_affinity=sorted(TRAINING_CPUS),
                                    allocator_card_limit_mib=integrated.native.CARD_LIMIT_MIB)
    profile["tag"] = RECIPES[early_repeat]
    return profile, bundle, slots, policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--early-repeat", type=int, choices=tuple(RECIPES), required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--resume-checkpoint", type=Path)
    parser.add_argument("--resume-sha256")
    args = parser.parse_args()
    tag = RECIPES[args.early_repeat]
    profile_path = args.profile.absolute()
    if (profile_path.parent != integrated.prep.EVIDENCE or profile_path.name != f"{tag}_profile.json"
            or os.sched_getaffinity(0) != TRAINING_CPUS):
        parser.error("use the unique owned profile path and CPU 0–13")
    if args.mode == "prepare":
        if any((args.profile_sha256, args.record, args.stop_by, args.resume_checkpoint, args.resume_sha256)):
            parser.error("preparing a profile does not start or resume training")
        profile, *_ = prepare(args.early_repeat, *FIXED_CURRICULUM)
        integrated.native.publish(profile_path, profile)
        print(f"{tag} {integrated.prep.sha(profile_path)}", flush=True)
        return 0
    if (args.stop_by is None or args.stop_by.tzinfo is None or args.stop_by > AUTHORIZATION_END
            or os.environ.get("CUDA_VISIBLE_DEVICES") != "0" or not args.profile_sha256
            or args.record is None or bool(args.resume_checkpoint) != bool(args.resume_sha256)):
        parser.error("provide the sealed profile, one CUDA device, owned output and user cutoff")
    record = args.record.absolute()
    if record.parent != integrated.prep.EVIDENCE or not record.name.startswith(f"{tag}_run"):
        parser.error("use a fresh evidence directory for this arm")
    resume = (args.resume_checkpoint.absolute(), args.resume_sha256.upper()) if args.resume_checkpoint else None
    if resume and not resume[0].is_relative_to(integrated.prep.EVIDENCE):
        parser.error("resumption requires the owned arm's earlier evidence checkpoint")
    worker = partial(integrated.worker, resume, make_profile=partial(prepare, args.early_repeat))
    return integrated.supervisor.supervise(worker, profile_path, args.profile_sha256, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
