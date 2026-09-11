# TinyLM Stage 1 High-Density v2 설계서 — 준비본

- 상태: `PREPARATION_ONLY`
- 기준일: 2026-09-10 KST
- 상태 의미: 폴더·원장 형식만 준비했다. v2 데이터, source, ID, audit script, audit 판정은 아직 만들거나 확정하지 않았다.

## 1. 목적과 불변 경계

v2의 목적은 Stage 1 v1의 자연성·용어 출처·관계형 primary 표현을 **별도 기준으로 검토한 뒤**, 필요할 때 직접 재작성한 독립 dataset을 만드는 것이다.

- v1은 `../stage1_highdensity_dataset/`에 보존하며 수정하지 않는다.
- v2는 v1의 덮어쓰기, 이름 변경, in-place repair가 아니다.
- v1의 구조 감사 PASS와 v2의 naturalness/provenance 판정은 별개다.
- v2의 `text` 외 metadata는 기본 학습 입력에 섞지 않는다. term registry는 source-side 검토 증거다.

## 2. 생성 전 승인 필요 결정

다음은 준비만 되었고 아직 결정되지 않았다.

| 결정 항목 | 후보 | 확정 조건 |
|---|---|---|
| v2 범위 | 전체 Stage 1 또는 naturalness review가 필요한 영역 우선 | v1 inventory 결과와 사용자 승인 |
| primary 표현 | 자연스러운 명사구를 `concepts[0]`에 literal로 유지 | 현행 schema를 유지할 때 |
| 관계형 목표의 schema | 자연어 anchor concept와 관계 서술을 분리 | 현행 primary literal 규약 변경 승인 |
| ID | v2 전용 prefix와 새 전역 연속 ID | v1 ID 재사용 금지 |
| train/val | 의미 객체·관계 조합 기준으로 새로 분리 | split leakage 기준 확정 |

## 3. v2 source-side term registry 초안

각 primary마다 다음 정보를 source-side registry에 기록한다. registry는 검토와 재현을 위한 것이며 training JSON에 자동 병합하지 않는다.

| 필드 | 의미 |
|---|---|
| `term_id` | v2 내부의 안정된 용어 식별자 |
| `primary_display` | text에 실제로 쓸 자연스러운 표현 |
| `term_kind` | `common_term`, `technical_term`, `constructed_scenario`, `internal_defined` 중 하나 |
| `definition` | 무엇을 뜻하는지의 짧은 정의 |
| `provenance_kind` | 공식·표준·도메인 문서·내부 정의 중 근거 유형 |
| `provenance_ref` | 재검토 가능한 참조 또는 내부 정의 위치 |
| `domain`, `entity`, `event_or_state`, `agent`, `condition` | 의미 slot; 자동 생성이 아닌 검토 보조 정보 |
| `review_status` | `approved`, `rewrite`, `hold`, `rejected` |
| `review_note` | 판정 근거 |

자동 형태소 분석이나 X1/X2 분해는 flag 보조로만 허용할 수 있으며, term 생성·재서술·승인 판단을 대신할 수 없다.

## 4. v2 품질 gate 초안

| gate | 최소 판정 |
|---|---|
| structural | JSON/schema/ID/controlled relations/literal/duplicate/split leakage 통과 |
| diversity | 반복 5어절·도입부·masked similarity 및 상위 pair 사람 검토 |
| provenance | 모든 primary에 검토 가능한 출처 또는 내부 정의·승인 상태 존재 |
| naturalness | 고위험 primary 전수, 그 밖의 primary도 family 사전 검토 완료 |
| migration | v1→v2의 유지·재작성·제외·새 작성 결정이 추적 가능 |

`PASS_STRUCTURAL`만으로는 v2 포장이나 자연어 품질 PASS를 선언하지 않는다.

### 4.1 v1 primary+은/는 retrospective signal과 향후 보정

2026-09-11 읽기 전용 전수 집계에서 Stage1 v1의 `text`가 `concepts[0]` 직후 `은/는`으로 시작한 비율은 train 26,066/34,000=`76.6647%`, validation 3,584/4,200=`85.3333%`, 전체 29,650/38,200=`77.6178%`다. 이 값은 정의형 도입부 집중도이지 문법 오류율이나 v1의 소급 재작성 근거가 아니다.

- v2 수정 또는 source 생성 권한이 승인되면, 먼저 area·family별 층화 사람 검토로 이 형식이 정상 설명인지 반복 template인지 판단한다.
- v2는 term registry 사전 승인, 자동 합성어·숫자 suffix·기계적 X1/X2 결합 금지, family별 도입부 다양성 계획, masked similarity·반복 5어절·조사·출처 검토를 함께 적용 후보로 둔다.
- Stage2의 30%/45% 임시 signal을 v2의 자동 HOLD 또는 수치 상한으로 복사하지 않는다. v1/Stage2 층화 검토와 사용자 승인을 거친 뒤에만 v2의 수치 기준을 보정·확정한다.
- 이 절은 `PENDING_USER_REVIEW_BEFORE_V2_REWRITE`이며, v1과 v2의 실제 record·ID·schema를 변경하라는 지시가 아니다.

## 5. 예정 작업 순서

1. v1의 파일 목록·record count·SHA-256을 읽기 전용 inventory로 고정한다.
2. v1 primary를 natural / technical-verified / constructed-but-acceptable / rewrite / hold 후보로 분류한다.
3. 범위와 schema 방식을 승인받는다.
4. 새 v2 term registry와 concept-family 예약표를 확정한다.
5. train과 validation source를 직접 작성하고, 새 ID와 split 경계를 적용한다.
6. 모든 gate를 실행·검토한 뒤에만 JSON을 포장하고 release manifest를 만든다.

## 6. 명시적 비목표

- 공백 삽입, suffix 제거, 동의어 치환 같은 일괄 변환으로 v2를 만드는 일
- v1의 복합 label을 자동 X1/X2 문장으로 바꾸는 일
- 외부 용어 검색 결과 수만으로 자연성을 확정하는 일
- 이 준비 문서를 근거로 v1 또는 Stage2 source를 수정하는 일
