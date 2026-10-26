# 종합 감사 자동 수집의 범위 이탈과 후속 제한

2026-10-26 두 PRECOMMIT 감사는 기존 `check_static_all.py --profile codex-safe --json ...`를 그대로 사용했다. 첫 실행은 시스템 Python의 패키지 부재3건과 새 CPU 플래그 미등록5개에 따른 게이트1건으로66PASS/4ERROR/6NOT_RUN이었다. 플래그 다섯 개를 exp로 등록하고 기존 tlm_torch 환경에서 다시 실행한 결과는 실제70PASS/0ERROR/6NOT_RUN이다. 원래 실패 감사는 보존한다.

그 뒤 감사 JSON의 worktree_manifest를 읽으며 다음 범위 이탈을 확인했다. codex-safe는 보호 TinyDataset/기존 runtime 데이터는 제외하지만 다른 세션의 열린 WIP·P102A 전용 audit/evidence 경로를 제외하지 않는다. manifest 수집은 이들의 본문을 읽어 SHA를 계산했고, 제어문자 검사도 handoff/test_result 아래를 재귀적으로 읽었다. 따라서 초기의 ‘타 세션 전용 경로 접근0’ 주장은 이후 실제 상태에 맞지 않는다. 해당 파일을 수정·이동·삭제·staging하거나 그 내용을 정제 데이터/결과의 채택 근거로 사용하지는 않았다. 이번 goal의 접근 경계를 지키지 못한 도구 사용 사고로 기록하며 사후 승인으로 바꾸지 않는다.

후속 `run_scoped_static.py`는 공유 환경 정책/검사기를 수정하지 않는 세션 전용 어댑터다. 원래 codex-safe 게이트 명령·판정은 유지하고 두 수집기만 명시한 이번 작업 파일 목록으로 제한한다. 제어문자 판정 함수는 원형을 재사용하고 새 파일도 실제 바이트로 읽는다. 최종 감사는 어댑터/원형 소스SHA·정확 allowlist SHA와 이 범위를 기록한다. 이를 저장소 전체 clean 또는 OS 격리 검증으로 설명하지 않는다. 공유 계획·결과·기준표와 launcher 레지스트리의 정합 검사는 기존 codex-safe 범위로 유지한다.

GPU/가중치/교사/학생/전체 GPU 스모크/설치/다운로드/push/PR은0, 기존 원형/캐시/로그/checkpoint 덮기·삭제0, 보호 TinyDataset 접근0이다. 다른 세션의 변경은 최종 커밋 allowlist에서 제외한다. 이후 동일 goal에서는 기본 재귀 수집기를 다시 호출하지 않는다. 다른 세션의 -done 두 런처도 감사가 표시한 재고 사실만 보존하며 삭제·실행 권한을 승계하지 않는다.
