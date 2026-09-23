# `handoff/audit/` — 세션별 정적검사 감사 기록

이 디렉터리는 `check_static_all.py --profile codex-safe --json ... --wip ...`가 만든
`TINYLM_STATIC_AUDIT_V1` JSON을 보존한다. handoff에는 검사 전문을 복사하지 않고 정확한 파일을
링크한다. WIP close는 새 계약이 표시된 원장에서 같은 WIP·session의 오류 0·조치경고 0 evidence를
요구한다.

이 기록은 프로젝트 smoke·GPU·모델 E2E가 아니다. 보호 데이터 때문에 제외한 검사는 `NOT_RUN`과
사유로 남으며 `codex-safe` PASS를 `project-full` PASS로 승격하지 않는다.

## 진행 중 큐 잠금의 부분 기록

사용자가 실험 원본 로그·런처를 읽지 말라고 한 세션에서는
`check_static_all.py --profile codex-safe`가 그 파일들에 접근할 수
있으므로 실행하지 않는다. 그 대신 명시한 비보호 코드·문서만
검사했다면 같은 폴더에 `TINYLM_STATIC_AUDIT_V1` JSON을
`profile=queue-locked-scoped`, `status=PARTIAL`,
`wip_close_eligible=false`로 기록할 수 있다. 파일명과 handoff
링크가 같아도 이 기록은 **전체 codex-safe PASS가 아니며
원장 --close에 전달하면 거부되어야 한다**.

기록에는 검사마다 대상·PASS/FAIL/NOT_RUN과 제외 이유를 적고,
실험 결과 로그·런처·보호 데이터를 열지 않은 범위를 함께 쓴다.
큐 종료·잠금 해제 후에만 전체 감사와 실제 결과 회수를 새로 수행한다.
