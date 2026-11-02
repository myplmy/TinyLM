"""Exercise the save guard in a preserved, isolated /tmp Git fixture."""
from contextlib import redirect_stdout
from pathlib import Path
import hashlib
import io
import json
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent / "commit_explicit_checkpoint_v1.py"
REPORT = SOURCE.parent / "CURRENT_TWO_ROLE_GIT_GUARD_TESTS_V1.json"
FIXTURE = Path("/tmp/tinylm_hold_checkpoint_git_fixture_20261102_v1")
assert not FIXTURE.exists() and not REPORT.exists()
FIXTURE.mkdir()
audit = FIXTURE / "handoff/audit/hold_resolution_20261027_goalc"
audit.mkdir(parents=True)


def fixture_git(*args):
    return subprocess.check_output(["git", *args], cwd=FIXTURE, stderr=subprocess.STDOUT)


fixture_git("init", "-q")
fixture_git("config", "user.name", "Checkpoint fixture")
fixture_git("config", "user.email", "fixture@example.test")
(audit / "baseline.md").write_text("baseline" + chr(10), encoding="utf-8")
fixture_git("add", "--", "handoff/audit/hold_resolution_20261027_goalc/baseline.md")
fixture_git("commit", "-qm", "fixture baseline")
namespace = {"__name__": "checkpoint_fixture", "__file__": str(SOURCE)}
exec(compile(SOURCE.read_text(encoding="utf-8"), str(SOURCE), "exec"), namespace)
namespace["ROOT"] = FIXTURE
namespace["AUDIT"] = audit
saved = audit / "saved.md"
saved.write_text("saved bytes" + chr(10), encoding="utf-8")
foreign = audit / "foreign.md"
foreign.write_text("foreign fixture bytes" + chr(10), encoding="utf-8")
message = FIXTURE / "message.txt"
message.write_text("시험: 명시 경로만 로컬 저장" + chr(10), encoding="utf-8")
manifest = audit / "allowlist.json"
data = dict(expected_head=fixture_git("rev-parse", "HEAD").decode().strip(),
    branch=fixture_git("branch", "--show-current").decode().strip(),
    rows=[dict(path=str(saved.relative_to(FIXTURE)), sha256=hashlib.sha256(saved.read_bytes()).hexdigest().upper())])
with manifest.open("x", encoding="utf-8") as stream:
    json.dump(data, stream, ensure_ascii=False)
receipt = audit / "receipt.json"
args = [str(SOURCE), "--manifest", str(manifest), "--message", str(message), "--receipt", str(receipt)]
output = io.StringIO()
checks = []


def invoke(argv, expected_error=None):
    before = sys.argv
    sys.argv = argv
    try:
        with redirect_stdout(output):
            namespace["main"]()
    except AssertionError as error:
        assert expected_error is not None and expected_error in str(error), str(error)
    else:
        assert expected_error is None, "expected rejection did not occur"
    finally:
        sys.argv = before


invoke(args)
assert fixture_git("diff", "--cached", "--name-only", "-z") == b"" and not receipt.exists()
checks.append("dry_run_does_not_stage_or_commit")
wrong = audit / "wrong_digest.json"
invalid = dict(data, rows=[dict(data["rows"][0], sha256="0" * 64)])
with wrong.open("x", encoding="utf-8") as stream:
    json.dump(invalid, stream)
invoke([str(SOURCE), "--manifest", str(wrong), "--message", str(message), "--receipt", str(receipt)], "working evidence changed")
checks.append("changed_evidence_is_rejected_before_staging")

original_git = namespace["git"]


def concurrent_stage(*argv, **kwargs):
    if argv[0] == "commit":
        fixture_git("add", "--", str(foreign.relative_to(FIXTURE)))
    return original_git(*argv, **kwargs)


namespace["git"] = concurrent_stage
invoke(args + ["--commit"])
namespace["git"] = original_git
record = json.loads(receipt.read_text())
assert record["whole_changed_path_set_exact"] and record["all_committed_bytes_match"]
assert record["actual_changed_paths"] == 2 and record["remaining_shared_index_count"] == 1
assert fixture_git("diff", "--cached", "--name-only", "-z") == str(foreign.relative_to(FIXTURE)).encode() + bytes([0])
checks.append("concurrent_foreign_staging_is_excluded_and_preserved")

next_manifest = audit / "next_allowlist.json"
next_data = dict(data, expected_head=fixture_git("rev-parse", "HEAD").decode().strip())
with next_manifest.open("x", encoding="utf-8") as stream:
    json.dump(next_data, stream)
invoke([str(SOURCE), "--manifest", str(next_manifest), "--message", str(message),
        "--receipt", str(audit / "next_receipt.json"), "--commit"], "shared index already in use")
checks.append("preexisting_foreign_index_is_left_untouched")
invoke(args + ["--commit"], "immutable receipt already exists")
checks.append("existing_receipt_is_not_overwritten")
with REPORT.open("x", encoding="utf-8") as stream:
    json.dump(dict(status="FIVE_ISOLATED_GIT_FIXTURE_CHECKS_PASS", checks=checks, fixture=str(FIXTURE),
        fixture_preserved=True, actual_repository_git_writes=0, procedure_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper(),
        fixture_stdout=output.getvalue()), stream, ensure_ascii=False, indent=2)
print(json.dumps(dict(checks=len(checks), status="PASS", fixture=str(FIXTURE)), ensure_ascii=False))
