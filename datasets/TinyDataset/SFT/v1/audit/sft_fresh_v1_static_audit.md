# SFT용 Fresh 코퍼스 v1 — Phase 1 정적 감사

- 상태: `STATIC_AUDIT_PASS`
- hard failure 합계: `0`
- 토큰 계측: `TOKEN_CALIBRATION_PENDING` (사용자 승인 전 미실행)
- 학습/평가: 미실행

## 산출물 수

- train source ledger: 1000건
- canonical positive train: 1000건
- eval source ledger: 300건
- source-disjoint eval: 300건

## 하드 실패

- 없음

## 측정 후보 — 자동 실패 아님

- 보호 코퍼스 5-token 후보: 0건
- 보호 코퍼스 8-token 후보: 0건
- fuzzy 상위 보고 쌍: 186건
- Fresh source 내부 fuzzy 상위 보고 쌍: 200건
- Fresh source 내부 fuzzy 최고 유사도: 0.948718

후보 전수와 locator는 `sft_fresh_v1_overlap_candidates.jsonl`에 기록한다. 공통 표현 후보는 숨기지 않으며, 후보라는 이유만으로 자동 폐기하지 않는다.

## 상태 경계

- `PILOT_GENERATED`
- `STATIC_AUDIT_PASS`
- `TOKEN_CALIBRATION_PENDING`
- `SCALE_UP_NOT_AUTHORIZED`
- `TRAINING_NOT_STARTED`
- `EVALUATION_NOT_STARTED`
