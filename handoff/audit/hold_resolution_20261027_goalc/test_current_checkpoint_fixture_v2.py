"""Repeat the real save guard in an isolated, preserved Git repository."""
from contextlib import redirect_stdout
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys

SOURCE = Path(__file__).with_name("commit_explicit_checkpoint_v2.py")
REPORT = SOURCE.with_name("CURRENT_BIRTH_SCOPE_GIT_CHECKS_V2.json")
FIXTURE = Path("/tmp/tinylm_hold_current_save_git_fixture_20261102_v2")
assert not FIXTURE.exists() and not REPORT.exists()
FIXTURE.mkdir()
audit = FIXTURE / "handoff/audit/hold_resolution_20261027_goalc"
audit.mkdir(parents=True)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=FIXTURE, stderr=subprocess.STDOUT)


git("init", "-q")
git("config", "user.name", "Current save fixture")
git("config", "user.email", "fixture@example.test")
(audit / "baseline.md").write_text("baseline" + chr(10), encoding="utf-8")
git("add", "--", "handoff/audit/hold_resolution_20261027_goalc/baseline.md")
git("commit", "-qm", "fixture baseline")
loader = dict(__name__="current_save_fixture", __file__=str(SOURCE))
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), loader)
namespace = loader["scope"]
namespace.update(ROOT=FIXTURE, AUDIT=audit)
saved = audit / "saved.md"
saved.write_text("saved bytes" + chr(10), encoding="utf-8")
foreign = audit / "foreign.md"
foreign.write_text("foreign fixture bytes" + chr(10), encoding="utf-8")
scripts = FIXTURE / "scripts"
scripts.mkdir()
owned_name = sorted(namespace["OWNED_SCRIPTS"])[0]
owned = FIXTURE / owned_name
owned.write_text("# owned fixture" + chr(10), encoding="utf-8")
other = scripts / "not_authorized.py"
other.write_text("# foreign fixture" + chr(10), encoding="utf-8")
message = FIXTURE / "message.txt"
message.write_text("시험: 명시 경로만 로컬 저장" + chr(10), encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def make_manifest(name, paths):
    manifest = audit / name
    data = dict(expected_head=git("rev-parse", "HEAD").decode().strip(),
        branch=git("branch", "--show-current").decode().strip(),
        rows=[dict(path=str(path.relative_to(FIXTURE)), sha256=digest(path)) for path in paths])
    with manifest.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False)
    return manifest


manifest = make_manifest("allowlist.json", [saved, owned])
receipt = audit / "receipt.json"
output = io.StringIO()
checks = []


def invoke(manifest_path=manifest, receipt_path=receipt, commit=False, error=None):
    before = sys.argv
    sys.argv = [str(SOURCE), "--manifest", str(manifest_path), "--message", str(message),
                "--receipt", str(receipt_path)] + (["--commit"] if commit else [])
    try:
        with redirect_stdout(output):
            namespace["main"]()
    except AssertionError as caught:
        assert error is not None and error in str(caught), str(caught)
    else:
        assert error is None, "expected rejection did not occur"
    finally:
        sys.argv = before


invoke()
assert git("diff", "--cached", "--name-only", "-z") == b"" and not receipt.exists()
checks.append("dry_run_leaves_index_and_HEAD_unchanged")
assert owned_name in namespace["OWNED_SCRIPTS"]
checks.append("exact_owned_recovery_script_is_allowed")
wrong_scope = make_manifest("wrong_scope.json", [other])
invoke(wrong_scope, error="")
checks.append("another_scripts_path_is_rejected")
linked = audit / "linked.md"
linked.symlink_to(saved)
linked_scope = make_manifest("linked_scope.json", [linked])
invoke(linked_scope, error="")
checks.append("symlink_is_rejected")
wrong = make_manifest("wrong_digest.json", [saved])
data = json.loads(wrong.read_text())
data["rows"][0]["sha256"] = "0" * 64
wrong.write_text(json.dumps(data), encoding="utf-8")
invoke(wrong, error="working evidence changed")
checks.append("changed_evidence_is_rejected")
original_git = namespace["git"]


def concurrent_stage(*args, **kwargs):
    if args[0] == "commit":
        git("add", "--", str(foreign.relative_to(FIXTURE)))
    return original_git(*args, **kwargs)


namespace["git"] = concurrent_stage
invoke(commit=True)
namespace["git"] = original_git
record = json.loads(receipt.read_text())
assert record["whole_changed_path_set_exact"] and record["all_committed_bytes_match"]
assert record["actual_changed_paths"] == 3 and record["remaining_shared_index_count"] == 1
assert git("diff", "--cached", "--name-only", "-z") == str(foreign.relative_to(FIXTURE)).encode() + bytes([0])
checks.append("concurrent_foreign_staging_is_excluded_and_preserved")
next_manifest = make_manifest("next_allowlist.json", [saved])
invoke(next_manifest, audit / "next_receipt.json", commit=True, error="shared index already in use")
checks.append("preexisting_foreign_index_is_left_untouched")
invoke(commit=True, error="immutable receipt already exists")
checks.append("existing_receipt_is_preserved")
with REPORT.open("x", encoding="utf-8") as stream:
    json.dump(dict(status="EIGHT_ISOLATED_GIT_CHECKS_PASS", checks=checks,
        fixture=str(FIXTURE), fixture_preserved=True, actual_repository_git_writes=0,
        procedure_sha256=digest(SOURCE), reused_procedure_sha256=digest(loader["SOURCE"]),
        fixture_stdout=output.getvalue()), stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(checks=len(checks), status="PASS", fixture=str(FIXTURE))))
