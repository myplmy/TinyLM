"""Resume the sealed Bonsai HellaSwag prefix without replaying scored rows."""

import argparse
from datetime import datetime, timedelta
import fcntl
import hashlib
import json
from pathlib import Path
import re

from scripts.p106b_shards import verify as verify_shards


EVIDENCE = Path(__file__).resolve().parents[1] / "test_result/evidence"
ANCHOR = EVIDENCE / (
    "p106b_bonsai_hellaswag_exact_prefix_last_interval_20261118/readback/"
    "BONSAI_HELLASWAG_INTERVALS_COMBINED_CPU_READBACK_v1.json"
)
ANCHOR_SHA = "B4DAF1268A8128F2E2FC642F90EFF3E780A4035B4756E6D89D049B076990BEF0"
TAG_PREFIX = "p106b_bonsai_hellaswag_exact_suffix_"
BINDING_KEYS = ("official", "route", "rows_total", "sources", "previous_tasks_reused")
PRIOR_DEADLINE = datetime.fromisoformat("2026-11-18T17:00:00+09:00")
INTERVAL_SIZE = 256
CAP_SECONDS = 610


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read(path):
    return json.loads(path.read_bytes())


def binding(profile):
    return {key: profile[key] for key in BINDING_KEYS}


def closed_window(directory, profile, state, cursor):
    require(state["profile_sha256"] == digest(directory / "profile.json"), f"changed profile in {directory.name}")
    require(state["exit"] in (0, 8) and state["handles_closed"]
            and state["release"]["competing_compute_pids"] == [], f"unreconciled stop in {directory.name}")
    recorded = {f"rows_{record['first']:05}_{record['end_exclusive']:05}" for record in state["intervals"]}
    require({place.name for place in directory.glob("rows_*")} == recorded,
            f"unreconciled interval directory in {directory.name}")
    start = cursor
    require(len(state["intervals"]) <= len(profile["ranges"]), f"extra interval in {directory.name}")
    for index, record in enumerate(state["intervals"]):
        first, end = profile["ranges"][index]
        rows = record["rows"]
        require((record["first"], record["end_exclusive"]) == (first, end)
                and cursor == first and 0 <= rows <= end - first,
                f"unexpected interval bounds in {directory.name}")
        require(bool(record["complete_interval"]) == (rows == end - first)
                and (record["complete_interval"] or index == len(state["intervals"]) - 1),
                f"unexpected interval completion in {directory.name}")
        if rows == 0:
            continue
        place = directory / f"rows_{first:05}_{end:05}"
        manifest = record["manifest"]
        require(record == read(place / "interval.json") and record["source_prefix_matches"]
                and manifest == read(place / "hellaswag_shards_manifest.json") and manifest["rows"] == rows
                and manifest["lineage"]["route"] == profile["route"]
                and manifest["lineage"]["evaluation_only"], f"unsealed interval in {place}")
        verify_shards(place, manifest)
        cursor += rows
    require(cursor - start == state["exact_rows"], f"unexpected row total in {directory.name}")
    return cursor


def history():
    require(digest(ANCHOR) == ANCHOR_SHA, "the final independent CPU readback changed")
    anchor = read(ANCHOR)
    fixed = binding(read(ANCHOR.parents[1] / "profile.json"))
    require(fixed["official"] == anchor["source"], "official HellaSwag request revision changed")
    for relative_path, sha in fixed["sources"].items():
        require(digest(EVIDENCE.parents[1] / relative_path) == sha, f"historical source changed: {relative_path}")
    cursor = 0
    for child in anchor["children"]:
        directory = EVIDENCE / child["tag"]
        terminal = directory / "terminal.json"
        profile, state = read(directory / "profile.json"), read(terminal)
        require(digest(terminal) == child["terminal_sha256"] and binding(profile) == fixed
                and state["exit"] == 0 and state["complete_intervals"], f"changed CPU-verified window: {directory.name}")
        cursor = closed_window(directory, profile, state, cursor)
    require(cursor == anchor["next_official_ordinal"], "the CPU-verified prefix length changed")

    closed = []
    for directory in sorted(EVIDENCE.glob(f"{TAG_PREFIX}*")):
        if not directory.is_dir():
            continue
        require(not directory.is_symlink(), f"linked run directory: {directory.name}")
        terminal = directory / "terminal.json"
        if not terminal.exists():
            require(not any(directory.glob("rows_*")), f"recover unfinished receipts in {directory.name}")
            continue
        profile, state = read(directory / "profile.json"), read(terminal)
        require(binding(profile) == fixed and profile["cpu_readback_sha256"] == ANCHOR_SHA,
                f"official scoring lineage differs in {directory.name}")
        if state["exact_rows"]:
            closed.append((profile["ranges"][0][0], directory, profile, state))
        else:
            closed_window(directory, profile, state, profile["ranges"][0][0])

    receipts = {}
    for first, directory, profile, state in sorted(closed):
        require(first == cursor, f"hole or duplicate at {first} in {directory.name}, expected {cursor}")
        cursor = closed_window(directory, profile, state, cursor)
        receipts[directory.name] = digest(directory / "terminal.json")
    require(cursor <= fixed["rows_total"], "stored intervals run past the official task")
    return fixed, cursor, receipts


def plan(fixed, cursor, receipts, count=None):
    total = fixed["rows_total"]
    ranges = [[first, min(first + INTERVAL_SIZE, total)] for first in range(cursor, total, INTERVAL_SIZE)]
    return dict(next_official_ordinal=cursor, remaining=total - cursor, ranges=ranges[:count],
                route=fixed["route"], cpu_readback_sha256=ANCHOR_SHA, prior_suffix_receipts=receipts)


def run(args, deadline):
    fixed, cursor, receipts = history()
    planned = plan(fixed, cursor, receipts, args.count)
    require(planned["ranges"], "the official row set is already complete")
    from scripts import diag_p106b_bonsai_hellaswag_exact_intervals as exact

    original_fingerprint = exact.fingerprint
    exact.TAG = TAG_PREFIX + args.run_id
    exact.OUT = EVIDENCE / exact.TAG
    exact.PROFILE = exact.OUT / "profile.json"
    exact.RANGES = tuple(tuple(pair) for pair in planned["ranges"])
    exact.CAP = args.interval_seconds
    exact.core.CUTOFF = deadline.timestamp()

    def fingerprint():
        profile, previous, native = original_fingerprint()
        require(binding(profile) == fixed, "prepared scorer or source differs from the original")
        profile.update(planned, cutoff_KST=deadline.isoformat(), approval_ref=args.approval_ref,
                       launcher_sha256=digest(Path(__file__)))
        return profile, previous, native

    exact.fingerprint = fingerprint
    if args.mode == "prepare":
        return exact.prepare()
    require(not (exact.OUT / "terminal.json").exists(), "this run ID already has a terminal receipt")
    return exact.actual()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "prepare", "actual"))
    parser.add_argument("--run-id", help="unique suffix for the approved window")
    parser.add_argument("--before", type=datetime.fromisoformat, help="approved KST cutoff with +09:00 offset")
    parser.add_argument("--approval-ref", help="reference to the user's approval for the specified window")
    parser.add_argument("--count", type=int, help="maximum intervals in this window")
    parser.add_argument("--interval-seconds", type=int, default=CAP_SECONDS, help="wall cap for each interval")
    args = parser.parse_args()
    if args.count is not None and args.count < 1:
        parser.error("--count must be positive")
    if args.interval_seconds < 1:
        parser.error("--interval-seconds must be positive")
    if args.mode == "plan":
        print(json.dumps(plan(*history(), count=args.count), indent=2))
        return 0
    cutoff = args.before
    if (not args.run_id or not re.fullmatch(r"[a-z0-9][a-z0-9_]{0,31}", args.run_id)
            or not args.approval_ref or not args.approval_ref.strip()):
        parser.error("a valid --run-id and --approval-ref are required")
    if (cutoff is None or cutoff.utcoffset() != timedelta(hours=9)
            or cutoff <= max(PRIOR_DEADLINE, datetime.now().astimezone())):
        parser.error("--before must be a new future authorized cutoff in KST")
    if args.mode == "prepare":
        return run(args, cutoff)
    with (EVIDENCE / f"{TAG_PREFIX}run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return run(args, cutoff)


if __name__ == "__main__":
    raise SystemExit(main())
