#!/usr/bin/env python3
"""Stage only the reviewed allowlist, then verify every index byte."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent

def git(*args, **kwargs):
    return subprocess.run(["git", *args], cwd=ROOT, **kwargs)

def main():
    manifest_path = BASE / "closed_milestone_stage_v3.json"
    manifest = json.loads(manifest_path.read_text())
    paths = []
    for row in manifest["files"]:
        name, path = row["path"], ROOT / row["path"]
        if row.get("deleted_after_source_archive"):
            if path.exists():
                raise ValueError("deletion changed: " + name)
        elif hashlib.sha256(path.read_bytes()).hexdigest().upper() != row["sha256"]:
            raise ValueError("closed source changed: " + name)
        paths.append(name)
    paths.extend([str(manifest_path.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT))])
    paths = list(dict.fromkeys(paths))
    staged = set(git("diff", "--cached", "--no-renames", "--name-only", "-z", stdout=subprocess.PIPE, check=True).stdout.decode().split(chr(0))) - {""}
    if not staged.issubset(set(paths)):
        raise ValueError("preserve unrelated existing index entries")
    pending = [name for name in paths if (ROOT / name).exists() or name not in staged]
    if pending:
        git("add", "--", *pending, check=True)
    actual_names = set(git("diff", "--cached", "--no-renames", "--name-only", "-z", stdout=subprocess.PIPE, check=True).stdout.decode().split(chr(0))) - {""}
    if actual_names != set(paths):
        raise ValueError("index differs from explicit allowlist")
    verified, deletions = 0, 0
    for name in paths:
        path = ROOT / name
        blob = git("show", ":" + name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if path.exists():
            if blob.returncode or blob.stdout != path.read_bytes():
                raise ValueError("index bytes differ: " + name)
            verified += 1
        elif blob.returncode == 0:
            raise ValueError("deletion not staged: " + name)
        else:
            deletions += 1
    source = [name for name in paths if not name.startswith(("test_result/evidence/", "smoketest_logs/"))
              and "_log_" not in name and "/launcher_archive/" not in name
              and not name.endswith(".txt")]
    strict = git("diff", "--cached", "--check", "--", *source, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = strict.stdout.decode(errors="replace").splitlines()
    if strict.returncode and not all(line.endswith("new blank line at EOF.") for line in lines):
        raise ValueError("unexpected source whitespace error: " + strict.stdout.decode(errors="replace"))
    check = git("-c", "core.whitespace=blank-at-eol,space-before-tab", "diff", "--cached", "--check", "--", *source,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = {"schema": "TINYLM_CLOSED_INDEX_VERIFICATION_V1", "files": verified, "deletions": deletions,
        "all_index_bytes_match": True, "source_whitespace_exit": check.returncode,
        "source_whitespace_output": check.stdout.decode(errors="replace"),
        "strict_source_whitespace_exit": strict.returncode,
        "strict_eof_blank_findings_preserved": lines,
        "frozen_source_bytes_not_rewritten": True,
        "explicit_paths": paths, "protected_paths": 0, "oversized_files": 0,
        "excluded_live_paths": manifest["excluded_live_or_unrelated"], "commit_executed": False}
    with (BASE / "closed_index_verification_v2.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps({key:value for key,value in result.items() if key not in ("explicit_paths", "excluded_live_paths")},ensure_ascii=False))
    if check.returncode:
        raise SystemExit(check.returncode)

if __name__ == "__main__":
    main()
