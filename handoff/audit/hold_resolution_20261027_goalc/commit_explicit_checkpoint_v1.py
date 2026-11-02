"""Save only a pinned local allowlist and verify the entire resulting commit."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
WIP = "handoff/WIP_20261027_작업원장.md"


def git(*args, data=None):
    result = subprocess.run(["git", "--literal-pathspecs", *args], cwd=ROOT,
                            input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def names(payload):
    return {value.decode("utf-8") for value in payload.split(bytes([0])) if value}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--message", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    manifest_path = (ROOT / args.manifest).resolve()
    receipt_path = (ROOT / args.receipt).resolve()
    assert manifest_path.is_relative_to(AUDIT) and receipt_path.is_relative_to(AUDIT)
    assert not receipt_path.exists(), "immutable receipt already exists"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest["rows"]
    paths = [row["path"] for row in rows] + [str(manifest_path.relative_to(ROOT))]
    assert len(paths) == len(set(paths)) and paths
    for name in paths:
        path = ROOT / name
        assert name == WIP or (path.resolve().is_relative_to(AUDIT) and not path.is_symlink())
        assert path.is_file() and 0 < path.stat().st_size < 20_000_000
    for row in rows:
        assert digest(ROOT / row["path"]) == row["sha256"], "working evidence changed"
    manifest_sha = digest(manifest_path)
    before = git("rev-parse", "HEAD").decode().strip()
    assert before == manifest["expected_head"], "HEAD changed before save"
    assert git("branch", "--show-current").decode().strip() == manifest["branch"]
    assert git("diff", "--cached", "--name-only", "-z") == b"", "shared index already in use"
    file_blobs = git("hash-object", "--no-filters", "--stdin-paths",
                     data=(chr(10).join(paths) + chr(10)).encode("utf-8")).decode().splitlines()
    assert len(file_blobs) == len(paths)
    print(json.dumps(dict(stage="PREPARED", paths=len(paths), expected_head=before,
                          actual_commit_requested=args.commit), ensure_ascii=False), flush=True)
    if not args.commit:
        return

    git("add", "--", *paths)
    assert names(git("diff", "--cached", "--name-only", "-z")) == set(paths), "staged membership changed"
    assert git("rev-parse", "HEAD").decode().strip() == before, "HEAD changed during staging"
    indexed = git("ls-files", "--stage", "-z", "--", *paths)
    indexed_blobs = {item.split(bytes([9]), 1)[1].decode("utf-8"): item.split(bytes([9]), 1)[0].split()[1].decode()
                     for item in indexed.split(bytes([0])) if item}
    assert indexed_blobs == dict(zip(paths, file_blobs)), "index bytes differ from working evidence"
    # --only prevents a concurrently staged foreign file from entering this commit.
    output = git("commit", "--only", "--file", str(Path(args.message).resolve()), "--", *paths)
    commit = git("rev-parse", "HEAD").decode().strip()
    actual = names(git("diff-tree", "--no-commit-id", "--name-only", "-z", "-r", commit))
    assert actual == set(paths), "whole actual commit membership differs"
    assert git("show", "-s", "--format=%P", commit).decode().strip() == before, "commit parent changed"
    tree = git("ls-tree", "-rz", "--full-tree", commit, "--", *paths)
    tree_blobs = {item.split(bytes([9]), 1)[1].decode("utf-8"): item.split(bytes([9]), 1)[0].split()[2].decode()
                  for item in tree.split(bytes([0])) if item}
    assert tree_blobs == dict(zip(paths, file_blobs)), "committed bytes differ"
    assert digest(manifest_path) == manifest_sha
    for row in rows:
        assert digest(ROOT / row["path"]) == row["sha256"], "evidence changed during commit"
    assert git("diff", "--name-only", commit, "--", *paths) == b"", "own committed paths changed"
    receipt = dict(status="ACTUAL_LOCAL_COMMIT_WHOLE_MEMBERSHIP_AND_BYTES_VERIFIED", commit=commit,
        parent=before, branch=manifest["branch"], expected_paths=len(paths), actual_changed_paths=len(actual),
        whole_changed_path_set_exact=True, all_committed_bytes_match=True, own_saved_scope_dirty=0,
        remaining_shared_index_count=len(names(git("diff", "--cached", "--name-only", "-z"))),
        manifest=dict(path=str(manifest_path.relative_to(ROOT)), sha256=manifest_sha),
        procedure_sha256=digest(Path(__file__)), git_output=output.decode("utf-8", errors="replace"),
        original_data_modified=False, push_runs=0, PR_changes=0, final_cache_created=False,
        goal_complete=False, training_authorized=False)
    with receipt_path.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))
    print(json.dumps(dict(commit=commit, verified_paths=len(actual), shared_index_count=receipt["remaining_shared_index_count"])))


if __name__ == "__main__":
    main()
