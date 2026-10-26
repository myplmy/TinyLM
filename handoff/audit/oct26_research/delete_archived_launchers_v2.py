#!/usr/bin/env python3
"""Delete only five explicitly archived and closed root launchers."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import sync_experiments_tsv as canonical

def need(value, message):
    if not value:
        raise ValueError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main():
    base = Path(__file__).resolve().parent
    manifest_path = base / "launcher_retirement_manifest_v2.json"
    manifest = json.loads(manifest_path.read_text())
    rows = manifest["entries"]
    need(len(rows) == 5 and len({row["path"] for row in rows}) == 5, "exact five launchers required")
    with contextlib.redirect_stdout(io.StringIO()):
        eligible = set(canonical.report_done(canonical.result_corpus()))
    names = {row["path"] for row in rows}
    need(names.issubset(eligible), "reproduction commands missing from result")
    links = []
    for top in ("docs", "test_plan", "test_result", "handoff"):
        for path in (ROOT / top).rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for name in names:
                if re.search(r"\]\([^\r\n)]*" + re.escape(name) + r"[^\r\n)]*\)", text):
                    links.append(str(path.relative_to(ROOT)))
    need(not links, "active Markdown file links remain")
    for row in rows:
        name = row["path"]
        source, archive = ROOT / name, ROOT / row["archive"]
        need(Path(name).parent == Path(".") and name.startswith("run_") and name.endswith("-done.sh"), "wrong root path")
        need(source.is_file() and not source.is_symlink() and archive.is_file() and not archive.is_symlink(), "nonregular source")
        need(sha(source) == sha(archive) == row["sha256"] and source.stat().st_size == row["bytes"], "archive bytes differ")
        need((source.stat().st_mode & 0o777) == row["mode"], "source permissions changed")
    deleted = []
    try:
        for row in rows:
            source = ROOT / row["path"]
            need(sha(source) == row["sha256"], "source changed before unlink")
            source.unlink()
            deleted.append(row["path"])
    finally:
        receipt = {"schema": "TINYLM_CLOSED_LAUNCHER_DELETION_V2", "manifest_sha256": sha(manifest_path),
            "deleted": deleted, "deleted_count": len(deleted), "archives_retained": len(rows),
            "active_markdown_links": links, "logs_deleted": 0, "models_deleted": 0, "datasets_deleted": 0,
            "active_normuon_launcher_deleted": False}
        with (base / "launcher_deletion_receipt_v2.json").open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps(receipt))

if __name__ == "__main__":
    main()
