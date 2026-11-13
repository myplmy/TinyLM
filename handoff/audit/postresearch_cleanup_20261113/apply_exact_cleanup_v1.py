"""사용자 승인·고정 SHA의 명시 파일만 삭제한다. 기본은 전량 사전검증이다."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_exact_cleanup_v1 import OUT, ROOT, digest, identity, module, read, save


def space():
    result = {}
    for name, path in (("wsl", ROOT), ("mounted_z", Path("/mnt/z"))):
        if path.is_dir():
            info = os.statvfs(path)
            result[name] = dict(path=str(path), available_bytes=info.f_bavail * info.f_frsize,
                                total_bytes=info.f_blocks * info.f_frsize)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = OUT / "EXACT_CLEANUP_PLAN_v2.json"
    assert digest(path) == args.plan_sha256.upper()
    plan = json.loads(path.read_text(encoding="utf-8"))
    targets = plan["checkpoints"] + plan["launchers"]
    assert len(targets) == len({r["path"] for r in targets}) == 306
    assert len(plan["protected39"]) == 39
    registry = ROOT / "checkpoints.tsv"
    registry_sha = digest(registry)
    status = {}
    for line in registry.read_text(encoding="utf-8").splitlines():
        cells = line.split("\t")
        if len(cells) > 1 and cells[0] in ("keep", "hold", "delete"):
            status[cells[1]] = cells[0]
    preserved_paths = {r["path"] for r in plan["preserve_root_metadata"]}
    for row in targets:
        rel = Path(row["path"])
        assert not rel.is_absolute() and ".." not in rel.parts
        assert row["path"] not in preserved_paths
        if row in plan["checkpoints"]:
            assert rel.suffix == ".pt"
            assert str(rel).startswith(("runs/ckpt/", "runs/validation/codex_smoke/"))
            assert rel.name not in plan["protected39"] and rel.name not in plan["preserve9"]
            if row["kind"] == "RETIRED_INTERMEDIATE_EPOCH":
                assert status[rel.name] == "delete"
        else:
            assert len(rel.parts) == 1 and rel.name.endswith(("-done.sh", "-cancel.sh", "-done.bat", "-cancel.bat"))
        assert identity(ROOT / rel) == row["identity"], rel
        assert digest(ROOT / rel) == row["sha256"], rel
    cleaner = module("apply_isolated_cleaner", "scripts/cleanup_isolated_ckpt.py")
    sessions = sorted({r["session_id"] for r in plan["checkpoints"] if "session_id" in r})
    busy = cleaner.busy_sessions(ROOT, sessions,
        [(r.get("session_id", "root"), r["identity"]) for r in targets])
    assert not busy, busy
    assert digest(registry) == registry_sha
    print("사전검증", len(targets), "개 통과; apply", args.apply)
    if not args.apply:
        return
    receipt = dict(schema="NOV13_EXACT_CLEANUP_RECEIPT_V1", status="PARTIAL_ERROR",
                   plan_sha256=args.plan_sha256.upper(), registry_sha256=registry_sha,
                   started_utc=datetime.now(timezone.utc).isoformat(), space_before=space(),
                   deleted=[], gpu=0, model_loads=0)
    try:
        with (OUT / "DELETE_JOURNAL_v1.jsonl").open("x", encoding="utf-8") as journal:
            for row in targets:
                rel = Path(row["path"])
                journal.write(json.dumps(dict(event="INTENT", path=row["path"], sha256=row["sha256"])) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
                with cleaner.parent_fd(ROOT, rel) as fd:
                    assert identity(Path(f"/proc/self/fd/{fd}") / rel.name) == row["identity"]
                    os.unlink(rel.name, dir_fd=fd)
                receipt["deleted"].append(dict(path=row["path"], bytes=row["identity"]["size"],
                                               allocated=row["identity"]["blocks_bytes"]))
                journal.write(json.dumps(dict(event="DELETED", path=row["path"])) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
        assert all(not (ROOT / r["path"]).exists() for r in targets)
        for row in plan["preserve_root_metadata"]:
            actual = identity(ROOT / row["path"])
            assert actual == dict(dev=row["dev"], ino=row["ino"], size=row["bytes"],
                mtime_ns=row["mtime_ns"], ctime_ns=row["ctime_ns"], blocks_bytes=row["allocated"])
        for relative, expected in plan["preserve_exact_identities"].items():
            assert identity(ROOT / relative) == expected, relative
        receipt.update(status="COMPLETE", preserved_root=339, protected39=39,
                       preserved_exact_identity_count=len(plan["preserve_exact_identities"]))
    finally:
        receipt["finished_utc"] = datetime.now(timezone.utc).isoformat()
        receipt["space_after"] = space()
        receipt["deleted_logical_bytes"] = sum(r["bytes"] for r in receipt["deleted"])
        receipt["deleted_allocated_bytes"] = sum(r["allocated"] for r in receipt["deleted"])
        save("DELETE_RECEIPT_v1.json", receipt)
    print(receipt["status"], "deleted", len(receipt["deleted"]),
          "logical_GiB", receipt["deleted_logical_bytes"] / 2**30,
          "wsl_available_delta", receipt["space_after"]["wsl"]["available_bytes"] - receipt["space_before"]["wsl"]["available_bytes"])


if __name__ == "__main__":
    main()
