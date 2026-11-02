"""Build immutable primary/post save lists from the bounded owned scope."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
WIP = ROOT / "handoff/WIP_20261027_작업원장.md"
SAVED_HEAD = "af3ae60209545e537d5411503b1cf9b78de9cbc8"
OWNED_SCRIPTS = ["scripts/p106b_hold_resolution_birth_conflicts_v1.py",
    "scripts/test_p106b_hold_resolution_birth_conflicts_v1.py",
    "scripts/p106b_hold_resolution_author_output_bindings_v1.py",
    "scripts/test_p106b_hold_resolution_author_output_bindings_v1.py"]
parser = argparse.ArgumentParser()
parser.add_argument("--phase", choices=["primary", "post"], required=True)
args = parser.parse_args()
out = AUDIT / ("CURRENT_BIRTH_SCOPE_" + args.phase.upper() + "_ALLOWLIST_V1.json")
assert not out.exists()


def git(*argv, data=None):
    return subprocess.check_output(["git", "--literal-pathspecs", *argv], cwd=ROOT, input=data)


head = git("rev-parse", "HEAD").decode().strip()
assert git("diff", "--cached", "--name-only", "-z") == b"", "shared index in use"
excluded = json.loads((ROOT / ".agents/project.json").read_text())["excludedPaths"]
deferred = []
if args.phase == "primary":
    assert head == SAVED_HEAD
    since = int(git("show", "-s", "--format=%ct", SAVED_HEAD))
    paths = {WIP, *(ROOT / name for name in OWNED_SCRIPTS)}
    for path in AUDIT.iterdir():
        if not path.is_file() or path.stat().st_mtime < since:
            continue
        if path.stat().st_size > 2_000_000 and path.name not in {
            "ROOT_BIRTH_BODY_SELECTIONS_V1.json", "CURRENT_BIRTH_SCOPE_LOCAL_ARTIFACTS_V1.json"}:
            deferred.append(dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(),
                reason="LARGE_METADATA_PRESERVED_LOCALLY_WITH_PIN"))
            continue
        paths.add(path)
    paths.update((AUDIT / "current_scope_review_archive_20261102_v1").glob("*.md"))
else:
    paths = {WIP, *(AUDIT / name for name in ["CURRENT_BIRTH_SCOPE_LOCAL_COMMIT_V1.json",
        "CURRENT_BIRTH_SCOPE_POST_CHECKS_V1.json", "current_birth_scope_wip_post_v1.log",
        "CURRENT_BIRTH_SCOPE_POST_COMMIT_MESSAGE_V1.txt", "CURRENT_BIRTH_SCOPE_LOCAL_SAVE_RESULT_V1.md"])}
names = []
for path in sorted(paths):
    assert path.is_file() and not path.is_symlink()
    assert 0 < path.stat().st_size < 20_000_000
    name = str(path.relative_to(ROOT))
    assert path == WIP or name in OWNED_SCRIPTS or path.resolve().is_relative_to(AUDIT)
    assert not any(name.startswith(value.rstrip("/")) for value in excluded if "*" not in value)
    names.append(name)
tree = git("ls-tree", "-rz", "--full-tree", "HEAD", "--", *names)
old = {item.split(bytes([9]), 1)[1].decode(): item.split(bytes([9]), 1)[0].split()[2].decode()
       for item in tree.split(bytes([0])) if item}
blobs = git("hash-object", "--no-filters", "--stdin-paths",
    data=(chr(10).join(names) + chr(10)).encode()).decode().splitlines()
rows = [dict(path=name, bytes=(ROOT / name).stat().st_size,
    sha256=hashlib.sha256((ROOT / name).read_bytes()).hexdigest().upper(), git_blob=blob)
    for name, blob in zip(names, blobs) if old.get(name) != blob]
assert len(blobs) == len(names) and rows
record = dict(status="EXACT_OWNED_LOCAL_COMMIT_ALLOWLIST", phase=args.phase,
    expected_head=head, branch=git("branch", "--show-current").decode().strip(),
    rows=rows, manifest_itself_additionally_included=True,
    expected_changed_paths_including_manifest=len(rows) + 1,
    selected_file_bytes=sum(row["bytes"] for row in rows),
    large_metadata_preserved_locally=deferred, excluded_paths=excluded,
    unrelated_work_included=False, data_cache_staged=False, push=False, PR=False,
    final_cache_created=False, goal_complete=False, training_authorized=False)
payload = json.dumps(record, ensure_ascii=False, indent=2) + chr(10)
assert len(payload.encode()) < 20_000_000
with out.open("x", encoding="utf-8") as stream:
    stream.write(payload)
print(json.dumps({key: record[key] for key in ["phase", "expected_head", "branch", "expected_changed_paths_including_manifest", "selected_file_bytes"]}))
