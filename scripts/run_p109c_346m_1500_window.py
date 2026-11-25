"""Launch an already sealed P109C arm within the renewed November 25 window."""

from argparse import ArgumentParser
from datetime import datetime
from functools import partial
import os
from pathlib import Path

from scripts import run_p109c_346m_route_pair as pair


AUTHORIZED_END = datetime.fromisoformat("2026-11-25T15:00:00+09:00")
RECIPES = {early_repeat: f"{tag}_chat32" for early_repeat, tag in pair.RECIPES.items()}


def prepare(early_repeat, *curriculum):
    profile, bundle, slots, policy = pair.prepare(early_repeat, *curriculum)
    source = Path(__file__).resolve()
    profile["signature"]["sources"][source.relative_to(pair.integrated.prep.ROOT).as_posix()] = (
        pair.integrated.prep.sha(source)
    )
    profile["tag"] = RECIPES[early_repeat]
    commands, _ = pair.integrated.base.native_commands(bundle, profile["tag"], False)
    if "--chat32-tokenizer" not in commands or "chat32" not in commands[commands.index("--tag") + 1]:
        raise ValueError("the native command must use a distinct Chat32 training tag")
    return profile, bundle, slots, policy


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run"))
    parser.add_argument("--early-repeat", type=int, choices=tuple(RECIPES), required=True)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    evidence = pair.integrated.prep.EVIDENCE
    tag = RECIPES[args.early_repeat]
    profile = evidence / f"{tag}_profile.json"
    if args.mode == "prepare":
        if any((args.profile_sha256, args.record, args.stop_by)):
            parser.error("preparation only writes the new profile")
        sealed, *_ = prepare(args.early_repeat, *pair.FIXED_CURRICULUM)
        pair.integrated.native.publish(profile, sealed)
        print(f"{tag} {pair.integrated.prep.sha(profile)}", flush=True)
        return 0
    if not args.profile_sha256 or not args.record or not args.stop_by:
        parser.error("provide the new profile digest, fresh record and cutoff")
    record = args.record.absolute()
    if (record.parent != evidence or not record.name.startswith(f"{tag}_run")
            or record.exists() or record.is_symlink()):
        parser.error("use a fresh evidence directory for the chosen arm")
    if os.sched_getaffinity(0) != pair.TRAINING_CPUS or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        parser.error("use CPU 0–13 and card 0")
    if args.stop_by.tzinfo is None or not datetime.now().astimezone() < args.stop_by <= AUTHORIZED_END:
        parser.error("the requested stop must be inside the authorized interval")
    worker = partial(pair.integrated.worker, None, make_profile=partial(prepare, args.early_repeat))
    return pair.integrated.supervisor.supervise(worker, profile, args.profile_sha256, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
