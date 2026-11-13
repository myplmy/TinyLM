"""Build an explicit owned Git allowlist and a refreshed scoped static manifest."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
REL = OUT.relative_to(ROOT).as_posix()
VERSION = sys.argv[1] if len(sys.argv) == 2 else "v1"
assert VERSION in ("v1", "v2", "v3", "v4", "v5")
VOLATILE = {"tmp/COORD_EXPERIMENT_01a0b33b.md"}
SNAPSHOT_AUDIT = json.loads((OUT / "SNAPSHOT_LINK_BASE_AUDIT_v2.json").read_text())
assert SNAPSHOT_AUDIT["status"] == "ORIGINAL_BASE_VERIFIED"
IMMUTABLE_COPIES = {row["snapshot"]: row["sha256"] for row in SNAPSHOT_AUDIT["snapshots"]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def excluded(name):
    return name.startswith((".git/", ".claude/", ".agents/", ".codex/", "HF/", "data_cache/",
        "runs/", "smoketest_logs/", "datasets/TinyDataset/", "handoff/audit/hold_resolution_",
        "handoff/audit/hold_recovery_", "handoff/audit/source_cleanup_")) or name in (
        "CLAUDE.md", "scripts/flag_whitelist.tsv", "handoff/WIP_20261027_작업원장.md", "train-logs.txt")


old = json.loads((ROOT / "handoff/audit/nov13_value_edit/STATIC_INPUTS_v46_final.json").read_text())
owned = {row["path"] for row in old["inputs"] if row["role"] == "owned" and not excluded(row["path"])}
prefixes = {"/".join(Path(name).parts[:3]) for name in owned
            if name.startswith(("handoff/audit/", "test_result/evidence/"))}
prefixes.add(REL)
for prefix in prefixes:
    for path in (ROOT / prefix).rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            name = path.relative_to(ROOT).as_posix()
            assert not path.is_symlink(), name
            owned.add(name)
owned.update(("docs/methods/07_corpus_selection.md", "docs/methods/10_benchmarks.md",
    "docs/research/20261101_KoBEST5_공식평가_준비범위.md",
    "docs/research/20261113_주도실험_채택재검토와_정리결과.md",
    "run_P078_Stage3Wc_prefix_router_full.sh", "run_P078_Stage3Wc_prefix_router_full-hold.sh"))
deleted = json.loads((OUT / "EXACT_CLEANUP_PLAN_v2.json").read_text())["launchers"]
owned.update(r["path"] for r in deleted)
retired = json.loads((OUT / "OLD_QUEUE_LAUNCHER_PLAN_v2.json").read_text())
owned.update(r["source"] for r in retired["launchers"])
assert not any(excluded(name) for name in owned)
status = subprocess.run(["git", "status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames", "--", *sorted(owned)],
    cwd=ROOT, capture_output=True, check=True).stdout
changes = []
for entry in status.split(bytes([0])):
    if entry:
        text = entry.decode("utf-8")
        changes.append(dict(status=text[:2], path=text[3:]))
paths = sorted({row["path"] for row in changes})
assert paths and not any(excluded(name) for name in paths)
sizes = {}
for name in paths:
    path = ROOT / name
    if path.is_file():
        assert not path.is_symlink() and path.stat().st_size < 20_000_000, name
        sizes[name] = path.stat().st_size
controls = [f"{REL}/COMMIT_SCOPE_{VERSION}.json", f"{REL}/COMMIT_ALLOWLIST_{VERSION}.paths",
            f"{REL}/STATIC_INPUTS_{VERSION}.json"]
paths = sorted(set(paths + controls))
write_new(OUT / f"COMMIT_SCOPE_{VERSION}.json", dict(schema="NOV13_EXPLICIT_OWN_COMMIT_SCOPE_V1",
    head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    paths=paths, changes=changes, bytes_existing=sum(sizes.values()), files_existing=len(sizes),
    new_control_files=controls, max_file_bytes=max(sizes.values()),
    excluded_foreign=["scripts/flag_whitelist.tsv", "handoff/WIP_20261027_작업원장.md"],
    note="명시 소유 목록. 다른 세션/보호/가중치/캐시는 저장하지 않는다. 자기 제어파일 hash의 자기참조는 하지 않는다."))
with (OUT / f"COMMIT_ALLOWLIST_{VERSION}.paths").open("xb") as stream:
    stream.write(bytes([0]).join(name.encode("utf-8") for name in paths) + bytes([0]))
for name, digest in IMMUTABLE_COPIES.items():
    assert sha(ROOT / name) == digest, name
inputs = {}
for row in old["inputs"]:
    path = ROOT / row["path"]
    if path.is_file() and row["path"] not in VOLATILE and row["path"] not in IMMUTABLE_COPIES:
        inputs[row["path"]] = dict(path=row["path"], role=row["role"], sha256=sha(path))
for name in owned:
    path = ROOT / name
    if path.is_file() and name not in VOLATILE and name not in IMMUTABLE_COPIES and not name.endswith((".paths", ".pyc")):
        inputs[name] = dict(path=name, role="owned", sha256=sha(path))
manifest = dict(old)
manifest["exclusions"] = list(old["exclusions"]) + sorted(VOLATILE) + sorted(IMMUTABLE_COPIES)
manifest["immutable_snapshot_audit"] = f"{REL}/SNAPSHOT_LINK_BASE_AUDIT_v2.json"
manifest["inputs"] = [inputs[k] for k in sorted(inputs)]
manifest["parent_manifest"] = "handoff/audit/nov13_value_edit/STATIC_INPUTS_v46_final.json"
manifest["note"] = "삭제 영수증 이후 현재 존재하는 소유 코드/문서만 검증한다. 가변 공개 조정문과 원래 기준경로를 별도 검증한 불변 계획 사본7개는 제외한다. 사본은 Git 저장하며 공용 검사기는 바꾸지 않는다. 전역 판정 아님."
scope = OUT / f"STATIC_INPUTS_{VERSION}.json"
write_new(scope, manifest)
print(json.dumps(dict(scope=str(scope.relative_to(ROOT)), sha256=sha(scope), paths=len(paths),
    bytes=sum(sizes.values()), max_file=max(sizes.values()), inputs=len(inputs)), ensure_ascii=False))
