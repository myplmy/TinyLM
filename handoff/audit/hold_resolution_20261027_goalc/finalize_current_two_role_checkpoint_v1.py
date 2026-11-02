"""Record the verified primary save through the normal WIP API, then prepare its receipt commit."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
receipt_path = AUDIT / "CURRENT_TWO_ROLE_LOCAL_COMMIT_V1.json"
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
primary = receipt["commit"]
assert receipt["whole_changed_path_set_exact"] and receipt["all_committed_bytes_match"]
assert receipt["actual_changed_paths"] == 46 and receipt["remaining_shared_index_count"] == 0
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == primary
manifest = json.loads((ROOT / receipt["manifest"]["path"]).read_text(encoding="utf-8"))
expected = {row["path"] for row in manifest["rows"]} | {receipt["manifest"]["path"]}
actual = {value.decode("utf-8") for value in subprocess.check_output(
    ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", primary], cwd=ROOT).split(bytes([0])) if value}
assert actual == expected
for row in manifest["rows"]:
    assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest().upper() == row["sha256"]

ledger = ROOT / "handoff/WIP_20261027_작업원장.md"
common = [sys.executable, "-I", "-B", str(ROOT / "scripts/wip.py"), "--file", str(ledger)]
subprocess.run(common + ["--done", "4", "--note",
    "두 보조작업의 지정9건을 수정5/후보유지4로 마감하고 원문·EOS·UTF8·SHA/50순서뷰 및 생산66불변을 검산했다. "
    "원문/정제/보류/실패 초안은 로컬 보존하고 소유46경로를 한국어 로컬 커밋 " + primary[:8] +
    "로 실제 저장했다. 커밋 후 전체 실제 변경 경로 집합46개와 모든 Git 바이트 일치 및 index0을 확인했다. "
    "회귀64와 격리Git5가 통과했으며 전체 HOLD 목표와 최종 캐시는 미완으로 사용자 재개 대기다.",
    "--artifact", "handoff/audit/hold_resolution_20261027_goalc/CURRENT_TWO_ROLE_SAVE_REPORT_20261102_V1.md; "
    "handoff/audit/hold_resolution_20261027_goalc/CURRENT_TWO_ROLE_LOCAL_COMMIT_V1.json"], cwd=ROOT, check=True)
capsule = subprocess.run(common + ["--capsule-check"], cwd=ROOT, capture_output=True, text=True)
capsule.check_returncode()
log = AUDIT / "bounded_20261102_test_wip_postcommit.log"
with log.open("xb") as stream:
    result = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "scripts/test_wip.py")], cwd=ROOT,
                            stdout=stream, stderr=subprocess.STDOUT)
result.check_returncode()
whitespace = subprocess.run(["git", "show", "--format=", "--check", primary], cwd=ROOT, capture_output=True, text=True)
assert whitespace.returncode == 2 and whitespace.stdout.count("trailing whitespace.") == 1
assert "resume_goal_and_correct_commit_record_v1.log:2:" in whitespace.stdout
post_json = AUDIT / "CURRENT_TWO_ROLE_WIP_POSTCOMMIT_V1.json"
with post_json.open("x", encoding="utf-8") as stream:
    json.dump(dict(primary_commit=primary, whole_primary_membership_verified=46, all_primary_bytes_match=True,
        WIP_states={"1": "WAIT_USER_RESUME", "2": "DONE", "3": "DONE", "4": "DONE"},
        capsule_exit=0, capsule=capsule.stdout.strip(), test_exit=0,
        test_log=str(log.relative_to(ROOT)), repeated_WIP_tests_not_new_unique_tests=True,
        git_whitespace_exit=whitespace.returncode, git_whitespace_output=whitespace.stdout,
        whitespace_scope="ONE_PRESERVED_RAW_TOOL_LOG_LINE_NOT_ACTIVE_CODE", final_cache_created=False,
        goal_complete=False, training_authorized=False), stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
note = AUDIT / "CURRENT_TWO_ROLE_LOCAL_SAVE_NOTE_20261102_V1.md"
with note.open("x", encoding="utf-8") as stream:
    stream.write(chr(10).join([
        "# 한정 마감의 실제 로컬 저장", "",
        "기본 커밋: `" + primary + "`", "",
        "제목: 데이터: 두 보조 판독 9건과 HOLD 복구 중단점을 저장한다", "",
        "실제 전체 변경46경로가 명시 allowlist와 정확히 같고, 모든 Git 바이트가 저장 시 작업 파일과 일치한다. index는0이다.",
        "두 보조 역할의9건 판독은 수정5·후보유지4로 마감했다. 원문·EOS·UTF8·SHA와 생산66개 불변을 확인했다.",
        "기존 회귀64개와 격리Git5시나리오가 통과했고, 원장 마감 뒤31개 회귀와 캡슐을 다시 확인했다. 반복한31개를 별도 시험 수에 더하지 않는다.",
        "git show --check는 원형 도구 로그2행의 공백 하나를 보고해 종료2였다. 실제 로그를 그대로 보존했으며 활성 코드의 오류나 시험 실패로 계산하지 않는다.", "",
        "후속 문서 커밋은 이 실제 영수증과 정상 API로 갱신한 자기 WIP 및 마감 검산만 저장한다. 외부 push·PR은 없다.",
        "대량 원문·정제 TXT·캐시는 기존 로컬 data_cache에 보존했다. 공식 H160219와 v26 미채택 P77639고유/P122534위치는 그대로다.",
        "전체 목표와 최종 캐시는 미완료다. 사용자의 재개 지시 전에는 새 묶음·생년 충돌 코드·전량 실행을 시작하지 않는다.",
        "상세 결과: CURRENT_TWO_ROLE_SAVE_REPORT_20261102_V1.md / CURRENT_TWO_ROLE_REVIEW_RECEIPT_V1.json.", ""]))
post_paths = [ledger, receipt_path, log, post_json, note, Path(__file__).resolve()]
post_manifest = AUDIT / "CURRENT_TWO_ROLE_COMMIT_ALLOWLIST_POST_V1.json"
with post_manifest.open("x", encoding="utf-8") as stream:
    json.dump(dict(expected_head=primary, branch=subprocess.check_output(["git", "branch", "--show-current"],
        cwd=ROOT, text=True).strip(), rows=[dict(path=str(path.relative_to(ROOT)),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper(), bytes=path.stat().st_size) for path in post_paths],
        scope="ACTUAL_PRIMARY_RECEIPT_AND_NORMAL_WIP_CLOSURE_ONLY"), stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
message = Path("/tmp/tinylm_hold_checkpoint_20261102_post_v1.message")
with message.open("x", encoding="utf-8") as stream:
    stream.write(chr(10).join(["문서: 한정 마감 커밋 검산과 재개 지점을 기록한다", "",
        "- 실제 기본 커밋 " + primary[:8] + "의 전체46경로 및 Git 바이트 일치 영수증을 저장한다.",
        "- 두 보조작업 마감과 기존 회귀64/Git5, 원장31 재확인 및 캡슐 근거를 남긴다.",
        "- 전체 HOLD 목표는 미완료로 사용자 재개 대기하며 원형 로그와 캐시를 보존한다.", ""]))
subprocess.run([sys.executable, "-I", "-B", str(AUDIT / "commit_explicit_checkpoint_v1.py"),
    "--manifest", str(post_manifest), "--message", str(message),
    "--receipt", str(AUDIT / "CURRENT_TWO_ROLE_LOCAL_COMMIT_POST_V1.json")], cwd=ROOT, check=True)
print(json.dumps(dict(primary=primary, post_paths=7, capsule=capsule.stdout.strip(), WIP_test_exit=0)))
