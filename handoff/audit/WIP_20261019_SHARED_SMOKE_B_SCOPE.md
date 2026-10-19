# 공용 격리 스모크 B 구현 범위 감사

- 승인: 2026-10-19 사용자 5번 지시. 과거 분리 저장/검사를 확인하고 총괄 판단으로 B 선택을 허용했다.
- 상태: 구현 전 범위 고정. 기존 실험의 코드·자료·원로그는 불변이다.
- 이력 근거: [과거 실물 검산](WIP_20261019_SHARED_SMOKE_PRIOR_HISTORY_REVIEW.json).
- 현재 과학 실험: 부모1694답 평가 중. 새 공용 도구의 GPU 실행과 겹치지 않는다.

## 변경 허용표

| 경로 | 동작 | 권한·제외 |
|---|---|---|
| scripts/check_smoke_diag.py | 수정 | 공용 판독의 등록·증거 형식 통합. 기존 표준/16·17일 판독은 보존 |
| scripts/test_smoke_diag_freshness.py | 수정 | 기존 정상/실패·호환 회귀 확장. 실제 모델/스모크 실행 없음 |
| scripts/smoke_execution_contract.py | 신설 | 승인된 형식/경로·두 대체·정규 영수증 검증. 새 규약의 코드 소유자 |
| scripts/codex_smoke.py | 신설 | 동일 정본을 실행하는 재사용 격리 실행기. 날짜별 복제 금지 |
| scripts/test_smoke_execution_contract.py | 신설 | pure/temp fixture, 누락·실패·오염 거부와 표준 판정 보존 |
| scripts/test_codex_smoke.py | 신설 | 가짜 프로세스로 쓰기·중단·예외·종료·동일 argv 시험 |
| scripts/flag_whitelist.tsv | 운영 메타데이터 1행 추가 | 승인된 새 실행기의 --deadline-utc 이름/소유자를 등록. 정적 미등록 오류를 우회하지 않으며 학습옵션·합격기준은 불변 |
| 이 감사·관련 새 audit/WIP/현재 결과·계획·COMPASS | 기록 | 범위/실제 결과와 미확인을 분리. root09/환경설정/타WIP는 제외 |

run_smoke_check.bat/sh, tool_smoke.bat, check_smoke.py, summarize_smoke.py,
기존 세 격리 실행기, .agents/.codex, 현재 58035FB1 학생 실험은 수정하지 않는다.
사용자 표준 스모크가 새 실행기를 자동 호출하게 바꾸지 않는다.

## 영향도 5축

- 코드: 기존 판독 호환을 유지하며 새 공통 계획/영수증을 연결한다. 모델·optimizer·생성 함수의 변경은 없다.
- 데이터: 새 세션만 별도 디렉터리에 배타 작성한다. 기존 산출물의 이동/덮어쓰기/삭제는 없다.
- 시험: 실제 GPU 없이 표준·기존2형식·19일 역사 형식·신규 형식과 음성 fixture를 대조한다.
- 문서: 실험 완료와 공용 판독 수리를 분리 기록한다. 현재 75M 재고/조건/판정자는 변경하지 않는다.
- 부채: 새 공통 실행기를 다음 주도 실험에서 재사용한다. 과거 실행기를 소급 개명/변경하지 않는다.

## 공통 API와 필수 계약

공통 모듈은 NEW_SCHEMA, NEW_DRIVER, CODEX_CHECKER와 다음 API를 제공한다.

```python
destinations(repo_root, session_id)
# dict(runtime=Path, evidence=Path, report=Path, log_name=str)
adapt_actions(actions, *, driver, contract_args)
# (adapted_actions, substitutions); exactly document+field-path edits
execution_source_pins(repo_root)
# bounded source-code SHA map; no dataset/checkpoint/model reads
```

신규 schema는 TINYLM_CODEX_SMOKE_EXECUTION_V1, driver는 scripts/codex_smoke.py다.
runtime은 runs/validation/codex_smoke/<session_id>, report는
test_result/evidence/codex_smoke/<session_id>/smoke_report.json이다.
세션 ID는 단일 안전 이름이며 상위/절대/링크 경로·기존 namespace 재사용은 거부한다.

영수증은 schema/profile_id/session_id/source/source_sha256/driver/driver_sha256/
contract_module_sha256/runtime/log_name/log/log_sha256/action_count/child_count/
training_count/action_manifest/substitutions/receipts/summary_command/
summary_returncode/failed_calls/complete/source_pins_before/source_pins_after/
original_synthetic_before/original_synthetic_after/original_synthetic_unchanged/
environment/whole_sec/started_at/finished_at를 보존한다.

- 정본 action과 모든 실제 자식 argv·순서·종료를 독립 대조한다. 실패·누락·중복·추가 호출을 정상으로 간주하지 않는다.
- 실제 합성 학습은 그대로다. Codex 문서 검사와 격리 로그 경로 두 곳만 대체하며 원래 argv도 기록한다.
- 계측은 기존 check_smoke.main을 그대로 호출한다. 필드/값/배치 산식·VRAM 기준을 완화하지 않는다.
- source_pins 전후는 bounded 코드만, original_synthetic 전후는 원래 합성 namespace만 대상으로 한다.
- 공용 판독은 기록된 map과 증거를 검산하며 원래 모델/데이터를 다시 로드·해시하지 않는다.
- 보호 TinyDataset/실제 학습 데이터/HF/비합성 checkpoint는 열지 않는다.
- 기존16/17일 형식은 그대로 지원한다. 19일 형식은 역사 증거에 한정하여 해석하고 미기록 원본 보존을 소급 주장하지 않는다.
- full 실행은 --execute 및 timezone-aware --deadline-utc와 최대 벽시간을 요구한다. 계약 조회는 GPU/모델 실행이 아니다.
- 코드/기존 합성 파일 전후 지문이 다르거나 실행이 미완료면 영수증도 명시 음성으로 남긴다.
- 네트워크·W&B 자동 작업은 끄고 환경 기록은 비밀 없는 허용 변수만 보존한다.
- 새 로그도 20MB 제한을 확인하며 원형을 삭제하지 않는다.
- 별도 stdout 출력 모드는 검토6의 구현 승인이 아니다. full 원로그와 기존 표준 콘솔을 보존하고 총괄의 조회 응답만 요약한다.

## 검증과 비용

기존 canonical 정상·누락·실패 fixture의 판정을 유지하고, 두 기존 실물 영수증을
읽기 검산한다. 신규 receipt의 source/driver/log/순서/종료/분모·경로 오염을 주입해 거부한다.
fake child의 비정상 종료·무출력·예외·시간 종료가 원로그/최종 상태에 보존되는지 확인한다.
전수 codex-safe 정적은 실제 수행하여 남은 오류/NR을 숨기지 않는다.

구현·CPU 검증 3~5시간은 추정이다. 새 전체 격리 스모크가 필요하면 기존 모델 평가가
끝난 뒤 별도로 실행하고, 현재 사용자20일17시의 권한/시간과 재원 예약을 다시 확인한다.
이는 모델 품질 검증이나 현재4eu 조건 변경이 아니다.

## 구현 중 확인한 선결과 최소 범위 보완

전수 정적이 새 운영 옵션 --deadline-utc의 미등록을 검출하여 이름/소유자/실험 등급 한 행을 추가한다. 이는 승인된 B 실행기의 정상 구현 메타데이터이며 새 실행 권한이 아니다. registry.py/runlog.py 수정은 이 보완에 포함하지 않고 별도 사용자 회신을 기다린다. 새 공용 full은 코드 수준의 HOLD8로 차단하고, 배선 내부 시험만 모의 의존성 아래 수행한다. check/contract 조회와 기존 사용자 스모크 경로는 유지한다.
