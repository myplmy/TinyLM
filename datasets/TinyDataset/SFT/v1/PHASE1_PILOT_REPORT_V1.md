# SFT용 Fresh 코퍼스 v1 — Phase 1 파일럿 결과

작성일: 2026-09-09  
범위: 승인된 Phase 0 및 Phase 1만 수행  
결론: `PILOT_GENERATED` / `STATIC_AUDIT_PASS` / `TOKEN_CALIBRATION_PENDING`

## 1. 산출 결과

| 구분 | 건수 | 비고 |
|---|---:|---|
| Fresh train source ledger | 1,000 | 학습 입력에서 제외 |
| canonical positive train | 1,000 | `messages`만 직렬화 대상 |
| source-disjoint eval source ledger | 300 | 학습 입력에서 제외 |
| canonical 자동채점 eval | 300 | `open_explanation`은 서열 결정 제외 |

Train semantic task는 `identity/attribute/function/relation=각 167`, `boundary/counterexample=각 166`이다. Train response type은 다섯 종류가 각각 200건이다. Eval은 semantic task별 50건, response type별 60건이다.

Train primary concept는 1,000개 모두 고유하고 정규화 source 문장도 1,000개 모두 고유하다. train과 eval 사이 primary concept, topic label, source family 교집합은 0이다. 한 train topic이 50건을 넘는 경우도 없다.

## 2. 작성 방식과 provenance

- train 267건: 개별 직접 작성
- train 733건: 이 코퍼스 전용 fact bank와 task별 표현 규칙을 코드에 직접 작성한 구조적 직접 합성
- eval 300건: 개별 직접 작성
- 보호 코퍼스 문장 또는 레코드를 source 재료로 사용한 건수: 0
- `rejected` 및 `rejected_reason`: 생성하지 않음

구조적 일괄 작성 여부는 source ledger의 `provenance.method_detail`과 manifest에 공개했다. 이는 기존 코퍼스 문장에서 개념명만 바꾼 파생 방식이 아니지만, 구조 반복 자체는 별도 fuzzy 측정 대상으로 남겼다.

## 3. canonical 및 정적 직렬화 확인

- canonical version: 1
- serializer: TinyLM v1 `chatml`
- canonical schema SHA-256: `8a514b69cc6c12519166defc059c74bf685defc85f20461a0e7cb52d092156bc`
- serializer SHA-256: `f67f8db7760be9c1bae9102692c819e2444c8780a2906179c4c468451926d4c8`
- train serialized 문자 합계: 190,846
- train assistant-loss 문자 합계: 49,098
- eval serialized 문자 합계: 49,184
- eval assistant-loss 문자 합계: 12,459

위 값은 실제 tokenizer token 수가 아니다. serializer의 문자 결과와 assistant loss span 경계만 확인했다. meta, source ID 및 dataset name이 직렬화 문자열에 섞이지 않는 것도 전수 검사했다.

## 4. 보호 자산 및 오염 감사

`SFT` 이외의 TinyDataset 파일 1,425개를 파일별 크기와 SHA-256 inventory로 기록했다. 총 바이트와 inventory digest는 동시 작업으로 변할 수 있어 최종 manifest의 동결 스냅샷을 정본으로 삼는다. 최종 통과 빌드의 전후 inventory SHA-256은 같아 그 실행 중 보호 자산 변경은 0건이다.

하드 실패 항목은 모두 0건이다.

- JSON/canonical schema 및 ID/source ID 오류: 0
- source 1:1, 정규화 동일 source, primary concept 중복: 0
- held-out v2.7 unseen concept·alias 및 금지 concept＋relation 충돌: 0
- held-out exact 또는 8-token 연속 일치: 0
- train–eval source family 교집합 또는 8-token 연속 일치: 0
- 허용되지 않은 relation, response 문장 수 계약, answer key 지지 오류: 0
- 보호 코퍼스 exact source, 5-token 및 8-token 후보: 0

보호 코퍼스 fuzzy 후보는 상위 186쌍을 기록했다. 최고 후보도 자동 실패로 처리하지 않았으며 locator와 발췌문을 후보 JSONL에 남겼다.

## 5. 평가 예약 교정 이력

초기 eval 원고는 train 작성 전에 SHA-256 `38775ab6...e7478`로 동결했다. 이후 held-out exclusion 감사에서 `붓`, `주머니`, `차례`와 충돌하는 eval 6건을 발견했다. 이를 숨기지 않고 의미 관계와 분포는 유지한 채 금지 어휘만 교정했으며, revision 2 SHA-256 `3a785b9e...fe2d`로 최종 패키징 전에 재동결했다.

구조적 직접 작성 train 733건은 revision 2 동결 후 다시 작성했다. 기존 개별 작성 train 267건도 수정된 eval과 다시 격리 검사했다. 변경 ID와 전후 SHA는 `audit/eval_reservation_v1_amendment_001.json`에 있다.

## 6. 내부 반복 측정과 해석

Fresh source 내부 fuzzy 상위 200쌍을 별도로 기록했으며 최고 유사도는 `0.948718`이다. 이는 동일 source 재사용이나 보호 코퍼스 복사는 아니지만, task별 fact bank를 여러 response type에 배치한 구조적 반복의 흔적이다.

파일럿 전에 합의한 대로 이 수치에 임의의 자동 탈락 문턱을 사후 적용하지 않았다. 따라서 `STATIC_AUDIT_PASS`는 하드 규칙과 오염 검사를 통과했다는 뜻이지, 반복 다양성이 학습에 충분하다는 뜻은 아니다. 실제 학습 전에는 내부 fuzzy 분포와 표본 문장에 대한 사용자 검토를 거쳐 Phase 2의 표현 다양성 기준을 정해야 한다.

## 7. 토큰 계측 보류

사용자가 지정한 `Z:\TinyLM\scripts\diag_dataset_tokens.py`는 실행하지 않았다. 현재 스크립트는 다음 이유로 canonical JSONL과 assistant-loss token을 그대로 셀 수 없다.

1. `json.load()` 기반이라 JSONL을 읽지 않는다.
2. 최상위 `text`만 읽고 canonical `messages`를 `chatml`로 직렬화하지 않는다.
3. 출력 단계에서 정의되지 않은 `tp`를 참조한다.
4. 전체 serialized token과 assistant-loss token을 분리하지 않는다.

다음 단계에는 사용자 명시적 승인이 필요하다. 원본 스크립트는 수정하지 않고 SFT 로컬 호환 계측기를 추가할지, 그리고 기본 `ko-en` tokenizer를 쓸지 또는 명시적 `tokenizer.json` 경로와 SHA-256을 사용할지를 먼저 확정해야 한다.

## 8. 상태 경계

- `PILOT_GENERATED`
- `STATIC_AUDIT_PASS`
- `TOKEN_CALIBRATION_PENDING`
- `SCALE_UP_NOT_AUTHORIZED`
- `TRAINING_NOT_STARTED`
- `EVALUATION_NOT_STARTED`

이 결과는 `EXPERIMENT_READY`가 아니다. Phase 2 확장, 모델 load, GPU, 학습, checkpoint 생성 및 모델 평가는 수행하지 않았다.
