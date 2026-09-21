# `handoff/audit/` — 세션별 정적검사 감사 기록

이 디렉터리는 `check_static_all.py --profile codex-safe --json ... --wip ...`가 만든
`TINYLM_STATIC_AUDIT_V1` JSON을 보존한다. handoff에는 검사 전문을 복사하지 않고 정확한 파일을
링크한다. WIP close는 새 계약이 표시된 원장에서 같은 WIP·session의 오류 0·조치경고 0 evidence를
요구한다.

이 기록은 프로젝트 smoke·GPU·모델 E2E가 아니다. 보호 데이터 때문에 제외한 검사는 `NOT_RUN`과
사유로 남으며 `codex-safe` PASS를 `project-full` PASS로 승격하지 않는다.
