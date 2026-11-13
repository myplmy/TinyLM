"""Read-only post-deletion identity, command archive, and foreign-work verification."""
from pathlib import Path
import hashlib
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_exact_cleanup_v1 import ROOT, OUT, digest, identity, save

plan = json.loads((OUT / "EXACT_CLEANUP_PLAN_v2.json").read_text())
queue = json.loads((OUT / "OLD_QUEUE_LAUNCHER_PLAN_v2.json").read_text())
deleted = plan["checkpoints"] + plan["launchers"]
assert all(not (ROOT / row["path"]).exists() for row in deleted)
assert all(not (ROOT / row["source"]).exists() and not (ROOT / row["target"]).exists()
           for row in queue["launchers"])
for row in plan["launchers"] + queue["launchers"]:
    assert hashlib.sha256(row["command_text"].encode()).hexdigest().upper() == row["sha256"]
    logs = row.get("raw_logs", row.get("logs", []))
    for log in logs:
        assert digest(ROOT / log["path"]) == log["sha256"]
for row in plan["preserve_root_metadata"]:
    assert identity(ROOT / row["path"]) == dict(dev=row["dev"], ino=row["ino"], size=row["bytes"],
        mtime_ns=row["mtime_ns"], ctime_ns=row["ctime_ns"], blocks_bytes=row["allocated"])
for name, expected in plan["preserve_exact_identities"].items():
    assert identity(ROOT / name) == expected, name
for name in plan["protected39"]:
    assert (ROOT / "runs/ckpt" / name).is_file(), name
for row in plan["launcher_holds"]:
    assert identity(ROOT / row["path"]) == row["identity"]
for row in plan["synthetic_holds"]:
    assert (ROOT / row["path"]).is_file()
for row in queue["holds"]:
    assert digest(ROOT / row["hold_target"]) == row["sha256"]
foreign = "scripts/flag_whitelist.tsv"
assert digest(ROOT / foreign) == "1718411C3FF9A88712CDF3D4C00F47F4E6CCE918F18CB5042E5525C7B77D98E5"
value = dict(schema="NOV13_CLEANUP_CLOSURE_V1", status="VERIFIED",
    checkpoints_deleted=len(plan["checkpoints"]), launchers_deleted=len(plan["launchers"])+len(queue["launchers"]),
    root_models_preserved=len(plan["preserve_root_metadata"]), protected_models_preserved=len(plan["protected39"]),
    exact_preserved_identities=len(plan["preserve_exact_identities"]), launchers_held=len(plan["launcher_holds"]),
    synthetic_held=len(plan["synthetic_holds"]), fresh_router_held=len(queue["holds"]),
    foreign_sha256=digest(ROOT / foreign), gpu_runs=0, model_loads=0)
save("CLEANUP_CLOSURE_v1.json", value)
print(json.dumps(value))
