"""Resume the single rename safely; preserve the original failed receipt."""
from pathlib import Path
import argparse
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_exact_cleanup_v1 import ROOT, OUT, digest, identity, read, save, module


def renamed_matches(actual, before):
    return all(actual[k] == v for k, v in before.items() if k != "ctime_ns")


parser = argparse.ArgumentParser()
parser.add_argument("--plan-sha256", required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
assert digest(OUT / "OLD_QUEUE_LAUNCHER_PLAN_v2.json") == args.plan_sha256.upper()
plan = read("handoff/audit/postresearch_cleanup_20261113/OLD_QUEUE_LAUNCHER_PLAN_v2.json")
previous = read("handoff/audit/postresearch_cleanup_20261113/OLD_QUEUE_DELETE_RECEIPT_v1.json")
assert previous["status"] == "PARTIAL_ERROR" and not previous["deleted"]
rows = plan["launchers"] + plan["holds"]
resumed = []
for index, row in enumerate(rows):
    source = ROOT / row["source"]
    target = ROOT / row.get("hold_target", row["target"])
    if source.exists():
        assert not target.exists() and identity(source) == row["identity"]
        path = source
    else:
        assert index == 0 and target.exists()
        assert renamed_matches(identity(target), row["identity"])
        resumed.append(dict(source=row["source"], target=target.name,
                            before=row["identity"], after=identity(target)))
        path = target
    assert digest(path) == row["sha256"]
    for log in row["logs"]:
        assert digest(ROOT / log["path"]) == log["sha256"]
assert len(resumed) == 1
cleaner = module("queue_cleanup_v2_guard", "scripts/cleanup_isolated_ckpt.py")
assert not cleaner.busy_sessions(ROOT, [], [("queue", row["identity"]) for row in rows])
print("checked", len(rows), "prior_rename", len(resumed), "apply", args.apply)
if args.apply:
    receipt = dict(schema="NOV13_OLD_QUEUE_RETIREMENT_RECEIPT_V2", status="PARTIAL_ERROR",
                   plan_sha256=args.plan_sha256.upper(), resumed_rename=resumed,
                   previous_receipt_sha256=digest(OUT / "OLD_QUEUE_DELETE_RECEIPT_v1.json"),
                   renamed_done=[], deleted=[], held=[])
    try:
        fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for index, row in enumerate(rows):
                source = row["source"]
                target = row.get("hold_target", row["target"])
                if index != 0:
                    assert identity(ROOT / source) == row["identity"]
                    os.rename(source, target, src_dir_fd=fd, dst_dir_fd=fd)
                current = identity(ROOT / target)
                assert renamed_matches(current, row["identity"])
                assert digest(ROOT / target) == row["sha256"]
                if "hold_target" in row:
                    receipt["held"].append(target)
                else:
                    receipt["renamed_done"].append(dict(source=source, target=target, identity=current))
                    os.unlink(target, dir_fd=fd)
                    receipt["deleted"].append(dict(source=source, done_name=target, bytes=row["identity"]["size"]))
        finally:
            os.close(fd)
        receipt["status"] = "COMPLETE"
    finally:
        save("OLD_QUEUE_DELETE_RECEIPT_v2.json", receipt)
    print(receipt["status"], "deleted", len(receipt["deleted"]), "held", receipt["held"])
