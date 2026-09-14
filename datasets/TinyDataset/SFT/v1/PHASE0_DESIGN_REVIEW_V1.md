# SFT용 Fresh 코퍼스 v1 — Phase 0 설계 검토

작성일: 2026-09-09  
상태: `PHASE0_COMPLETE` / Phase 1 작성 승인 범위 내 진행

## 1. 적용 결정

사용자의 최신 명시적 요청을 실행 게이트로 삼아 Phase 0과 Phase 1만 수행한다. 인용된 검토용 프롬프트 안의 `REVIEW_ONLY` 문구는 이전 게이트이며, 최신 요청이 Phase 0·1 수행을 명시적으로 승인했다. Phase 2, 학습, 모델 로드, GPU, 체크포인트, 모델 평가는 승인 범위 밖이다.

| 항목 | 적용값 |
|---|---|
| 데이터셋 표시명 | `SFT용 Fresh 코퍼스 v1` |
| 출력 디렉터리 | `Z:\TinyLM\datasets\TinyDataset\SFT` |
| dataset version | `v1` |
| canonical schema | TinyLM canonical v1 (`CANONICAL_VERSION=1`) |
| serializer | TinyLM v1 `chatml` |
| canonical 코드 SHA-256 | `8A514B69CC6C12519166DEFC059C74BF685DEFC85F20461A0E7CB52D092156BC` |
| serializer 코드 SHA-256 | `F67F8DB7760BE9C1BAE9102692C819E2444C8780A2906179C4C468451926D4C8` |
| held-out 기준 | v2.7, SHA-256 `360F486830EF7BE675A4DED2E84DE16DE3C160E97F21D5849B030F2F80D91328` |
| 생성 모델 표기 | `gpt-5` / Codex desktop agent |
| Phase 1 batch | `SFT-FRESH-V1-PILOT-20260909` |

정확한 배포 내부 식별자는 에이전트에 노출되지 않으므로 공개된 모델 식별자 `gpt-5`와 실행 환경을 함께 기록한다. 이를 더 구체적인 내부 ID로 추정해 쓰지 않는다.

## 2. 보호 범위

`SFT` 이외의 현재 작업 디렉터리 하위 전체를 보호 대상으로 고정한다. 특히 기존 미커밋 변경과 신규 `held-out_v2.8`은 수정·이동·삭제하지 않는다. 보호 자산은 패키징 시작 시 파일별 경로, 크기, SHA-256을 inventory로 동결하고, 종료 시 동일 여부를 확인한다.

held-out v2.7 전문은 학습 원고 작성 재료로 사용하지 않는다. 감사 도구만 다음 파생 정보와 정규화 해시를 만든다.

- `unseen_concept` 문항의 추출 주어와 문자열 alias
- 금지 concept＋controlled relation 조합
- prompt, answer, candidates의 정규화 SHA-256
- 공백 기준 8-token 연속 n-gram SHA-256

신규 평가는 train 작성 원고와 다른 topic 및 source family에 예약하며, 평가 원문은 학습 파일에 포함하지 않는다.

## 3. semantic task 정의

| task | 판정 대상 | 대표 controlled relation |
|---|---|---|
| `identity` | 문맥이 정의한 대상의 종류·명칭·분류 | `is_a`, `subclass_of`, `classification` |
| `attribute` | 대상에 귀속된 색·수량·상태·조건 | `attribute`, `state` |
| `function` | 도구·구성요소·담당자의 용도나 역할 | `function`, `role` |
| `relation` | 둘 이상의 대상 사이 포함·순서·비교·과정 관계 | `part_of`, `process`, `comparison` |
| `boundary` | 적용 범위, 임계, 허용·금지 구획 또는 조건 | `boundary`, `contrast`, `state` |
| `counterexample` | 일반 규칙을 만족하지 않는 명백한 사례 | `contrast`, `boundary`, `other` |

관계 라벨은 승인된 13개만 사용한다: `is_a`, `subclass_of`, `part_of`, `classification`, `boundary`, `contrast`, `comparison`, `function`, `role`, `process`, `state`, `attribute`, `other`.

Phase 1 train 배정은 1,000건을 `167/167/167/167/166/166`으로 나눈다. 평가 300건은 task별 50건으로 고정한다.

## 4. response type 정의

| response type | 출력 계약 | 주 채점 방식 |
|---|---|---|
| `grounded_qa` | 직접 답 1문장과 문맥 근거 1문장 | 필수 요소 포함＋금지 요소 부재 |
| `exact_short` | 명칭·수치·상태를 짧게 1문장 | 정규화 exact set |
| `choice_with_reason` | 제시 후보 하나와 근거 | 선택 exact＋근거 필수 요소 |
| `constraint_response` | 지정된 한 문장·형식·포함 조건 준수 | 답 요소＋문장/형식 규칙 |
| `open_explanation` | 자연스러운 2~3문장 설명 | 진단용 rule set, 서열 결정 제외 |

train은 response type별 200건, 평가는 response type별 60건을 예약한다. semantic task와 response type은 독립 필드로 유지한다.

## 5. ID와 split 예약

| 용도 | ID 범위 | source ID 범위 | split |
|---|---|---|---|
| Phase 1 train | `SFTF-V1-000001`~`SFTF-V1-001000` | `SFTF-V1-SRC-000001`~`SFTF-V1-SRC-001000` | `train` |
| Phase 1 eval | `SFTF-V1-EVAL-000001`~`SFTF-V1-EVAL-000300` | `SFTF-V1-EVAL-SRC-000001`~`SFTF-V1-EVAL-SRC-000300` | `eval` |
| Phase 2 | 미예약 | 미예약 | 미승인 |

train과 eval은 topic label, primary concept, source family를 서로 공유하지 않는다. train topic은 5%를 초과하지 않도록 최소 24개 이상으로 분산한다.

## 6. canonical 및 loss 경계

각 SFT 행은 user text block 하나와 assistant text block 하나만 가진다. `tools=[]`이며 감사 정보는 `meta`에 둔다. TinyLM `serialize.py`의 `chatml` 직렬화를 정적 실행해 canonical 검증과 serialized 문자 길이를 계산한다. serializer의 `loss_spans()` 기준에 따라 assistant 본문과 `<|im_end|>` 경계만 loss 범위로 기록하고, user 및 meta는 loss 대상에서 제외한다.

이 단계는 tokenizer를 호출하지 않으므로 token 수나 optimizer update를 주장하지 않는다.

## 7. 토큰 계측 보류와 확인된 호환성 문제

사용자가 지정한 실제 파일은 `Z:\TinyLM\scripts\diag_dataset_tokens.py`로 확인했다. 사용자 승인 전 실행하지 않는다.

정적 검토 결과 현 스크립트는 그대로는 이번 canonical JSONL을 계측할 수 없다.

1. `json.load()`만 사용하여 JSON Lines를 읽지 않는다.
2. `text_of()`가 최상위 `text` 필드만 읽어 canonical `messages`를 직렬화하지 않는다.
3. 출력문에서 정의되지 않은 변수 `tp`를 참조한다.
4. assistant-loss token을 별도로 세지 않는다.

따라서 Phase 1의 비토큰 감사는 진행하되 상태를 `TOKEN_CALIBRATION_PENDING`으로 둔다. 데이터 작성 후 별도 승인을 받을 때, 원본 스크립트를 수정하지 않는 호환 입력/래퍼와 tokenizer 경로·SHA를 먼저 제안한다.

## 8. 계산 가능한 감사와 한계

자동 계산 항목은 schema, ID, source 1:1, 분포, relation vocabulary, 자연어 한글 여부, 문장 수, exact/5-token/8-token 중복 후보, held-out 문자열 concept 충돌, split 교집합, source-supported key, grading rule 및 meta 직렬화 누출이다.

fuzzy similarity는 word-shingle 후보 검색 후 정규화 유사도를 계산하여 상위 쌍을 공개한다. 자동 검사는 사실성·복수 정답성을 완전히 증명하지 못하므로, 각 원고가 문맥 내부의 단일 명시 사실만 요구하도록 설계하고 key가 source와 output 양쪽에 존재하는지도 검사한다. 모호한 항목은 위반 0으로 숨기지 않고 검토 목록에 남긴다.

