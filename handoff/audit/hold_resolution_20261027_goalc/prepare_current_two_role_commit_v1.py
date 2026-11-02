"""Read the WIP and evidence, then write only an audit allowlist and /tmp message."""
from pathlib import Path
import fnmatch
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
names = [
    "CURRENT_TWO_ROLE_SAVE_SCOPE_20261102_V1.md", "CURRENT_TWO_ROLE_SAVE_REPORT_20261102_V1.md",
    "CURRENT_TWO_ROLE_REVIEW_RECEIPT_V1.json", "CURRENT_TWO_ROLE_SUPPORT_TESTS_V1.json",
    "CURRENT_TWO_ROLE_WIP_PRECOMMIT_V1.json", "CURRENT_TWO_ROLE_WIP_PRECOMMIT_V2.json",
    "CURRENT_TWO_ROLE_GIT_GUARD_TESTS_V1.json", "seal_current_two_role_review_v1.py",
    "seal_current_two_role_review_v1.log", "commit_explicit_checkpoint_v1.py",
    "test_explicit_checkpoint_fixture_v1.py", "test_explicit_checkpoint_fixture_v1.log",
    "LOCAL_COMMIT_RECEIPT_V2.json", "resume_goal_and_correct_commit_record_v1.py",
    "resume_goal_and_correct_commit_record_v1.log", "materialize_resume_guard_pairs_v1.py",
    "materialize_resume_guard_pairs_v1.log", "prepare_resume_guard_views_v1.py",
    "prepare_resume_guard_views_v1.log", "RESUME_20261102_SCOPE_V1.md",
    "V27_BIRTH_FIELD_SCOPE_V1.md", "prepare_current_two_role_commit_v1.py",
]
paths = {AUDIT / name for name in names}
ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
paths.add(ledger)
review = json.loads((AUDIT / "CURRENT_TWO_ROLE_REVIEW_RECEIPT_V1.json").read_text(encoding="utf-8"))
paths.update(ROOT / row["archive"]["path"] for row in review["selected_review_and_hold_archives"])
checks = json.loads((AUDIT / "CURRENT_TWO_ROLE_SUPPORT_TESTS_V1.json").read_text(encoding="utf-8"))
paths.update(ROOT / row["log"] for row in checks["rows"])
for name in ["CURRENT_TWO_ROLE_WIP_PRECOMMIT_V1.json", "CURRENT_TWO_ROLE_WIP_PRECOMMIT_V2.json"]:
    paths.add(ROOT / json.loads((AUDIT / name).read_text(encoding="utf-8"))["log"])
excluded = json.loads((ROOT / ".agents/project.json").read_text(encoding="utf-8"))["excludedPaths"]
rows, syntax = [], []
for path in sorted(paths):
    assert path.is_file() and not path.is_symlink(), str(path)
    assert path.is_relative_to(AUDIT) or path == ledger
    name = str(path.relative_to(ROOT))
    assert not any(name.startswith(pattern) if pattern.endswith("/") else fnmatch.fnmatchcase(name, pattern)
                   for pattern in excluded)
    payload = path.read_bytes()
    assert 0 < len(payload) < 20_000_000
    if path.suffix == ".py":
        compile(payload.decode("utf-8"), str(path), "exec")
        syntax.append(name)
    if path.suffix == ".json":
        json.loads(payload)
    rows.append(dict(path=name, sha256=hashlib.sha256(payload).hexdigest().upper(), bytes=len(payload)))
assert subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT) == b""
manifest = AUDIT / "CURRENT_TWO_ROLE_COMMIT_ALLOWLIST_V1.json"
data = dict(status="EXACT_OWNED_PATHS_FOR_BOUNDED_LOCAL_SAVE",
    expected_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    branch=subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
    rows=rows, syntax_checked=syntax, protected_and_data_cache_paths_staged=False,
    whole_goal_complete=False, training_authorized=False)
with manifest.open("x", encoding="utf-8") as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
message = Path("/tmp/tinylm_hold_checkpoint_20261102_v1.message")
with message.open("x", encoding="utf-8") as stream:
    stream.write(chr(10).join([
        "데이터: 두 보조 판독 9건과 HOLD 복구 중단점을 저장한다", "",
        "- 두 역할의 수정5건과 후보유지4건을 원문 구간·SHA·리뷰·별도 보류에 연결한다.",
        "- 원문 재디코딩9건과 EOS·UTF8·순서뷰50개, 생산코드66개 불변을 검산한다.",
        "- CPU 회귀64개와 격리 Git 경합5시나리오를 확인하고 명시 경로만 저장한다.",
        "- 이전 커밋의 소유671/실제681경로 차이를 정정하고 원형과 실패 초안을 보존한다.",
        "- 공식 HOLD160219 및 v26 미채택 초안의 미완 상태와 정확 재개 지점을 남긴다.",
        "- 최종 캐시·추가300M·GPU·모델·학습·push·PR은 수행하지 않는다.", ""]))
print(json.dumps(dict(paths_including_manifest=len(rows) + 1, bytes=sum(row["bytes"] for row in rows),
                      python_syntax_files=len(syntax), expected_head=data["expected_head"]), ensure_ascii=False))
subprocess.run([sys.executable, "-I", "-B", str(AUDIT / "commit_explicit_checkpoint_v1.py"),
    "--manifest", str(manifest), "--message", str(message),
    "--receipt", str(AUDIT / "CURRENT_TWO_ROLE_LOCAL_COMMIT_V1.json")], cwd=ROOT, check=True)
