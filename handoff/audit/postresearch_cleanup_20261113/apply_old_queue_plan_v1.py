"""Retire only the sealed completed queue and hold the distinct fresh router."""
from pathlib import Path
import argparse
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_exact_cleanup_v1 import ROOT, OUT, digest, identity, read, save, module

parser = argparse.ArgumentParser()
parser.add_argument("--plan-sha256", required=True)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
assert digest(OUT / "OLD_QUEUE_LAUNCHER_PLAN_v2.json") == args.plan_sha256.upper()
plan = read("handoff/audit/postresearch_cleanup_20261113/OLD_QUEUE_LAUNCHER_PLAN_v2.json")
rows = plan["launchers"] + plan["holds"]
assert len(rows) == 31
for row in rows:
    assert Path(row["source"]).name == row["source"]
    assert digest(ROOT / row["source"]) == row["sha256"]
    assert identity(ROOT / row["source"]) == row["identity"]
    assert not (ROOT / row.get("hold_target", row["target"])).exists()
    for log in row["logs"]:
        assert digest(ROOT / log["path"]) == log["sha256"]
cleaner = module("queue_cleanup_guard", "scripts/cleanup_isolated_ckpt.py")
assert not cleaner.busy_sessions(ROOT, [], [("queue", row["identity"]) for row in rows])
print("checked", len(rows), "apply", args.apply)
if args.apply:
    receipt = dict(schema="NOV13_OLD_QUEUE_RETIREMENT_RECEIPT_V1", status="PARTIAL_ERROR",
                   plan_sha256=args.plan_sha256.upper(), renamed_done=[], deleted=[], held=[])
    try:
        fd = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for row in rows:
                source = row["source"]
                target = row.get("hold_target", row["target"])
                assert identity(ROOT / source) == row["identity"]
                os.rename(source, target, src_dir_fd=fd, dst_dir_fd=fd)
                assert identity(ROOT / target) == row["identity"]
                if "hold_target" in row:
                    receipt["held"].append(target)
                else:
                    receipt["renamed_done"].append(dict(source=source, target=target, sha256=row["sha256"]))
                    os.unlink(target, dir_fd=fd)
                    receipt["deleted"].append(dict(source=source, done_name=target, bytes=row["identity"]["size"]))
        finally:
            os.close(fd)
        receipt["status"] = "COMPLETE"
    finally:
        save("OLD_QUEUE_DELETE_RECEIPT_v1.json", receipt)
    print(receipt["status"], "deleted", len(receipt["deleted"]), "held", receipt["held"])
