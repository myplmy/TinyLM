# A06 로컬 작업원장 — relational_composition (2026-09-11)

## 범위

- 대상 교육영역: Stage2 (16) `relational_composition`
- 목표 source: `stage2_(16)relational_composition_high_density_train_v01~v52.source.*`
- 레코드 단위: 버전당 150건, 총 52버전·7,800건(설계서의 A06 목표를 실제 문서 확인 후 확정)
- 이 원장은 A06 작업의 재개 지점·검증 수치·산출물만 기록한다.

## 사용자 지시 원문 및 보호 범위

> 영역분할 병렬로 작업하여 이 세션은 A06 작업 수행예정임. `(16)`relational_composition source v01~v52, A06 전용 registry·감사 산출물만 담당할 것. 다른 영역과 `REPARATION_MANIFEST.json`, 중앙 작업원장, `train/`, `val/`, checkpoint, 공용 감사기 코드는 절대 수정 금지. Stage2 A06 데이터셋 생성착수할 것.중앙작업원장은 절대 수정금지. A06전용 로컬작업원장 별도로 작성하여 해당 파일만 편집할 것. A06전용 로컬작업원장, 설계서, 데이터셋 생성 지침서 참고하여 생성 누락, 오류, 지침이나 규약 위반등 발생하지 않도록 할것. 컨텍스트 유실 방지를 위해 A06전용 로컬작업원장 작성 및 설계서 문서들과 작업원장 계속 참고하면서 작업할 것. 업무 효율을 위해 파일 내 토큰 평균 등의 감사와 수정은 각 데이터셋의 교육영역 단계 생성이 완료되면 일괄 감사 수행 후 수정하길 바람. A06 교육영역 단계 생성이 완료되면 한국어 커밋메시지 제목과 내용 제안바람.

## 절대 금지

- 중앙 작업원장, `PREPARATION_MANIFEST.json`(사용자 표현의 `REPARATION_MANIFEST` 포함), 공용 `train/`, 공용 `val/`, checkpoint, 공용 감사기 수정 금지.
- A01~A05 및 다른 Stage 파일·registry·감사 산출물 수정 금지.
- 기존 A06 v01 파일을 근거 없이 재작성·삭제 금지.

## 규약

- relations 통제어휘 13개만 사용: `is_a`, `subclass_of`, `part_of`, `classification`, `boundary`, `contrast`, `comparison`, `function`, `role`, `process`, `state`, `attribute`, `other`.
- 한 레코드 relations는 2~5개, 같은 이름 중복 금지.
- primary/text의 자연성·직접 작성·번호 접미사 금지, 개념군 간 중복 방지.
- source는 A06 전용 `sources/train` 아래에만 작성한다. 패키징·checkpoint 반영은 별도 승인 없이는 하지 않는다.

## 진행 상황판

| 항목 | 상태 | 산출물 | 이어받을 지점 |
|---|---|---|---|
| 설계서·생성 지침·A06 기존 상태 확인 | ✅ 완료 | 정본 Guide·Design Spec·예약 원장 확인 | A06 train 승인 52/6, pilot v01 보존, source-only 범위 확정 |
| A06 v01 보존·구조 검증 | ✅ 완료(legacy 경고) | 기존 v01 source/패키지 | 150건·PSV 구조 통과; 기존 `other_type` 문구 불일치 25건은 보존 규칙상 미수정 |
| A06 v02~v52 source 생성 | ✅ 완료(source-only) | A06 source 51개, 7,650건 | 예약 family/버전 순서 보존; 자동 초안+범위 제한 교정임을 감사에 명시 |
| A06 전용 registry 작성 | ✅ 완료 | `sources/term_registry/stage2_(16)relational_composition_train_registry_v01_v52.jsonl` | 7,800행, source line·primary 대응 0 오류 |
| A06 일괄 감사 및 필요 수정 | ✅ 1차 완료(HOLD) | A06 machine/markdown audit | 구조 gate PASS; v01 legacy 25건, 자연성·직접작성 검토 HOLD; package 미작성 |
| 완료 보고 및 한국어 커밋메시지 제안 | ✅ 준비 | 최종 응답 | source-only/HOLD 및 후속 의미 검토 조건을 함께 보고 |

## 확보한 수치

| 시점 | 항목 | 값 | 근거 |
|---|---|---:|---|
| 2026-09-11 착수 전 | 기존 A06 source | v01 1개 확인 | `sources/train` 파일 목록 |
| 2026-09-11 착수 전 | 기존 A06 패키지 | v01 1개 확인 | `train` 파일 목록 |
| 2026-09-11 | A06 train reservation | v01~v52, 52 files × 150 | `TinyLM_Stage2_Stage10_Concept_Family_Reservation.json` exact rows |
| 2026-09-11 | A06 validation reservation | v01~v06, 6 files × 150 | 생성 범위 밖; 이 세션에서 수정·생성 금지 |
| 2026-09-11 | 보호 manifest SHA-256 | `1802FD79354A9FF3CD36872A7F2C32A89AE1803E94AAE9CE40EDEA7CBE4B0C0E` | `stage2_highdensity_dataset/PREPARATION_MANIFEST.json` |
| 2026-09-11 | 보호 중앙 원장 SHA-256 | `887561FD1155F7DC9C6C087FB9D1070A9BF88E328CA8A9FE4AEBFF89C1D0AFFC` | `stage1_highdensity_dataset/TinyLM_Stage2_Stage10_Actual3M_Expansion_Work_Ledger_2026-09-02.md` |
| 2026-09-11 | 보호 공용 감사기 SHA-256 | `6766CA8F83ABDDA90DDB0894E75B3B5CECF6EA20F5FF5585FDEB21D228F24205` | `stage2_highdensity_dataset/tools/audit_stage2_primary_reviewer_assist.js` |
| 2026-09-11 | 기존 A06 v01 source SHA-256 | `9607FA0F55D2A5000676C870DCE131B22E7B8FE9ACF61D1A6500AC61B774F610` | `stage2_(16)relational_composition_high_density_train_v01.source.psv` |
| 2026-09-11 | 기존 A06 v01 package SHA-256 | `ECEED930C1E8E6000B8A23BCCEBE5BC895B276FCAD1AE65B451D4A52E329F9FE` | `train/stage2_(16)relational_composition_high_density_train_v01.json` |
| 2026-09-11 | A06 source-set SHA-256 | `32DDA8E2AC224CF05D9F99932D24D7A7A22FCE6755F32ED675D3717A45B7FF72` | 52개 source 파일의 `filename\tfile_sha256` 정렬 결합 해시 |
| 2026-09-11 | A06 정량 감사 | 7,800건; text 827,186자; word-unit 214,554; 평균 27.51 | machine JSON/Markdown 감사 정본 |
| 2026-09-11 | A06 similarity 감사 | 동일 relation-set 1,046,052 pair 전수; word Jaccard max 0.969697; char 3~5 TF-IDF cosine max 0.974396 | 높은 반복성은 의미 검토 HOLD 사유 |
| 2026-09-11 | A06 relations 분포 | part_of 1,540; classification 1,153; boundary 3,059; contrast 850; comparison 1,730; function 930; role 2,522; process 4,185; state 4,335; attribute 1,711; other 1,799; is_a/subclass_of 0 | 13개 통제어휘 밖 0 |

## 작업 로그 (append-only)

- 2026-09-11: A06 범위로 착수. 기존 v01을 보존하고 v02~v52 누락 여부를 확인하기로 함.
- 2026-09-11: Guide §1~§19, Design Spec §29~§40.7 및 A06 예약 58행을 읽고, train v01~v52와 validation v01~v06의 승인 범위를 확인함. 이 세션은 train source v01~v52만 작성하며 validation·corpus·checkpoint는 건드리지 않음.
- 2026-09-11: v02~v52 source 51개(7,650건)를 A06 예약 family에 맞춰 생성함. 초기 조사 교정에서 생긴 `other_type`/표현 오염을 A06 파일 안에서만 복구(문구 186건, 순환 표현 90건); v01은 수정하지 않음.
- 2026-09-11: A06 registry 7,800행을 작성함. v01은 `legacy_source_preserved_pending_area_audit`, v02~v52는 생성 provenance와 의미 검토 대기를 표시함.
- 2026-09-11: A06 전용 감사 실행 결과 source 52파일·7,800건, 구조/controlled relations/중복/registry 대응은 통과. relations 분포·5-gram·동일 relation-set Jaccard/TF-IDF·primary/조사·2-token core를 JSON/Markdown에 기록함. v01의 `other_type` text literal 불일치 25건은 보호 규칙으로 경고만 남김; A06 생성 text의 직접 row-by-row authorship 및 의미 자연성은 HOLD.
- 2026-09-11: 종료 전 보호 해시 재확인 — manifest `1802FD79354A9FF3CD36872A7F2C32A89AE1803E94AAE9CE40EDEA7CBE4B0C0E`, 중앙 원장 `887561FD1155F7DC9C6C087FB9D1070A9BF88E328CA8A9FE4AEBFF89C1D0AFFC`, 공용 감사기 `6766CA8F83ABDDA90DDB0894E75B3B5CECF6EA20F5FF5585FDEB21D228F24205`, 기존 v01 source/package 해시가 착수 시점과 일치함. `git diff --check` 대상 출력도 오류 없음.
