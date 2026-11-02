"""Inventory only this resumed scope and archive its small author MD records."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
OUT = AUDIT / "CURRENT_BIRTH_SCOPE_LOCAL_ARTIFACTS_V1.json"
ARCHIVE = AUDIT / "current_scope_review_archive_20261102_v1"
assert not OUT.exists() and not ARCHIVE.exists()
ARCHIVE.mkdir()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def pin(path):
    assert path.is_file() and not path.is_symlink()
    size = path.stat().st_size
    assert 0 < size < 20_000_000, str(path)
    return dict(path=str(path.relative_to(ROOT)), bytes=size, sha256=sha(path))


snapshot_path = AUDIT / "supplemental_candidates_snapshot_v51.json"
snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
cohorts = {"resume_guard_independent_20261102_v1", "birth_field_native_counter_v1"}
records = [row for row in snapshot["records"] if row["cohort"] in cohorts]
assert len(records) == 762
directories = [BASE / name for name in ["resume_guard_independent_20261102_v1",
    "birth_field_proof_v1", "birth_field_native_proof_v1", "birth_field_native_counter_v1"]]
role_directories = {ROOT / row["review"]["path"] for row in records}
role_directories = sorted({path.parent for path in role_directories})
assert len(role_directories) == 7
directories.extend(role_directories)
paths = set()
for directory in directories:
    assert directory.resolve().is_relative_to(BASE) and directory.is_dir()
    for path in directory.rglob("*"):
        if path.is_file():
            assert not path.is_symlink()
            paths.add(path)
for row in records:
    for name in [row.get("body"), row["original"]["path"], row["review"]["path"]]:
        if name:
            path = ROOT / name
            assert path.resolve().is_relative_to(BASE)
            paths.add(path)
archives = []
for directory in role_directories:
    for path in sorted(directory.glob("*.md")):
        source = pin(path)
        target = ARCHIVE / (source["sha256"] + ".md")
        if target.exists():
            assert sha(target) == source["sha256"]
        else:
            with target.open("xb") as stream:
                stream.write(path.read_bytes())
        archives.append(dict(original=source, archive=pin(target)))
since = int(subprocess.check_output(["git", "show", "-s", "--format=%ct", "HEAD"], cwd=ROOT))
metadata = [pin(path) for path in sorted(AUDIT.iterdir())
            if path.is_file() and path.stat().st_mtime >= since and path != OUT]
data = [pin(path) for path in sorted(paths)]
report = dict(status="CURRENT_SCOPE_LOCAL_DATA_PRESERVED_SMALL_REVIEW_MD_ARCHIVED",
    exact_data_directories=[str(path.relative_to(ROOT)) for path in directories],
    local_data_files=data, local_data_file_count=len(data),
    local_data_bytes=sum(row["bytes"] for row in data),
    current_top_level_metadata=metadata, author_md_archives=archives,
    author_md_files=len(archives), archive_unique_files=len(list(ARCHIVE.glob("*.md"))),
    snapshot_pin=pin(snapshot_path),
    data_cache_git_staging=False, originals_overwritten=0, deletions=0,
    global_selection_updated=False, final_cache_created=False,
    goal_complete=False, training_authorized=False)
payload = json.dumps(report, ensure_ascii=False, indent=2) + chr(10)
assert len(payload.encode("utf-8")) < 20_000_000
with OUT.open("x", encoding="utf-8") as stream:
    stream.write(payload)
print(json.dumps({key: report[key] for key in ["status", "local_data_file_count", "local_data_bytes", "author_md_files", "archive_unique_files"]}))
