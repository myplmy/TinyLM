# TinyLM Stage2 A04 상태 전이·동역학 train source 영역 일괄 감사 보고서

- 기준 감사일: 2026-09-09 KST (초기 감사); 정본 재감사: 2026-09-10 KST
- 대상: `stage2_(14)state_transition_high_density_train_v01.source.jsonl`~`v69.source.jsonl`
- 정본 tokenizer: `tok-ko-en-32768.json` (SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`)
- 감사 도구: `stage2_highdensity_dataset/tools/audit_stage2_a04_source.js` (read-only)
- 최신 판정: **FOLLOW_UP/HOLD** (§7.14). §7.13의 PASS와 초기 HOLD 수치는 숫자 접미사 정정 전후의 역사적 교정 이력으로 보존한다.
- corpus/checkpoint: 미생성. 이번 요청 범위는 source 재서술·재감사까지이며 포장은 후속 작업으로 남긴다.

## 1. 범위와 예약 정렬

- 예약: `S2-A04-T-001~069`
- source: 69 files, 10,350 records
- ID 예약 범위: `S2-STH-00001~S2-STH-10350`에 대응
- v66 반도체 클린룸, v67 도시 열공급망, v68 해양 부표, v69 병원 수술실 family를 중앙 manifest 그대로 사용
- v66~v69 source의 primary는 예약 ID가 아니라 문장에 나타나는 개념으로 교정
- v64 primary literal 3건, v65 primary literal 1건·동일 text 1건은 직접 수정

## 2. 최소 계약 결과

| 검사 | 결과 |
|---|---:|
| 파일 수 / records | 69 / 10,350 |
| JSON parse·UTF-8·BOM·Unicode escape·빈 줄 | 0 |
| source key/schema 오류 | 0 |
| primary literal 누락 | 0 |
| exact primary / text 중복 | 0 / 0 |
| 정규화 text 중복 | 0 |
| relation 통제어휘 밖 | 0 |
| relation cardinality(2~5) 위반 | 0 |
| record 내부 relation 중복 | 0 |
| Stage2 현행 corpus와 primary/text 교차 중복 | 0 / 0 |
| 예약 validation unseen relation-set 충돌 | 0 |
| known hard grammar 패턴 | 0 |
| primary 직후 조사 불일치 후보 | 0 |

cardinality는 3개 관계 108건, 4개 관계 10,242건이며 5개·2개 관계는 0건이다.

## 3. 분량 실측

정본 ByteLevel BPE에 EOS 1개를 더한 값이다.

- 전체: 480,265 tokens(+EOS), 평균 46.402415459
- record: 최소 28, 최대 74 tokens
- 파일 평균: 최소 38.673333333, 최대 63.233333333
- 파일 평균 허용범위: 37.4625~45.7875
- 허용범위 통과: 36/69; 미통과 33/69
- text 문자: 총 929,946, record 최소 58·평균 89.849855072·최대 128

미통과 version은 `v01,v05,v06,v07,v10,v11,v14,v18,v19,v20,v21,v22,v23,v24,v25,v26,v27,v28,v29,v30,v31,v32,v33,v34,v35,v36,v37,v58,v59,v66,v67,v68,v69`다. 최고 평균은 v34 63.233333333이며 신규 v66~v69는 각각 49.273333333, 50.380000000, 50.100000000, 52.560000000이다.

## 4. 반복·문장 다양성

- 반복 5어절 유형: 4,309
- 반복 5어절 assignments: 10,529
- 반복 4어절 도입부 유형: 10
- 최다 반복: `측정치가 허용 범위 안인 안정` 120회, `허용 범위 안인 안정 상태이다` 120회
- 그 밖에 v49~v65의 공통 종결·보존/변경 문구가 반복됨

이는 단순 exact 중복과 다른 보일러플레이트·유사 골격 문제로, Guide §11.2·§10의 직접 작성/다양화 규칙과 §15 반복 n-gram gate를 통과하지 못한다.

문자 3~5-gram TF-IDF와 word-set Jaccard 전수 유사도는 source gate가 HOLD인 상태에서 정본 재작성 후 재실행하도록 보류했다. 값을 산출하지 않고 미실행으로 기록한다.

## 5. relations 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 1,237 |
| `classification` | 1,975 |
| `boundary` | 6,065 |
| `contrast` | 604 |
| `comparison` | 2,278 |
| `function` | 2,967 |
| `role` | 2,006 |
| `process` | 10,155 |
| `state` | 10,079 |
| `attribute` | 3,926 |
| `other` | 0 |

총 relation occurrence는 41,292회다. `other`가 0이므로 상위 5개 유형은 해당 없음이다.

## 6. 판정과 후속 조치

1. v01~v69 source를 HOLD 상태로 보존한다.
2. 파일 평균 범위 밖 33개 version을 직접 의미 재작성·압축해 37.4625~45.7875로 맞춘다.
3. 반복 5어절·반복 도입부를 직접 재서술하고 hard grammar·조사·primary literal을 재검토한다.
4. 같은 Node read-only 감사와 정본 유사도 감사를 재실행한다.
5. 모든 source gate가 PASS인 경우에만 builder로 69개 corpus를 포장하고 checkpoint·manifest·원장·감사 보고서를 갱신한다.

현재는 구조·관계·누출 계약만 PASS이며, 분량·다양성 gate 미통과로 A04 완료 통계와 Stage2 잔여량에 corpus 완료로 계상하지 않는다.

## 7. 2026-09-10 정본 재감사와 직접 재작성 결과

### 7.1 감사 수행 여부와 수정 범위

기존 보고서의 HOLD 판정을 확인한 뒤, 동일한 read-only Node 감사기 `stage2_highdensity_dataset/tools/audit_stage2_a04_source.js`를 source 전체에 다시 실행했다. 감사 결과에 따라 원문 `text`만 `apply_patch`로 직접 재작성했으며, ID·primary(문장 속 literal을 보장하는 두 건 제외)·relations 배열과 source 파일 수·행 수는 보존했다. corpus와 checkpoint는 만들지 않았다.

- 파일 평균 범위 교정: `v01`, `v05~v07`, `v10~v11`, `v14`, `v18~v37`, `v58~v59`, `v66~v69`의 초과 문장을 조건·전이 의미를 남긴 짧은 문장으로 직접 재서술했다. `v30`, `v31`, `v33`은 낮은 쪽으로 압축되었지만 허용범위 안에 있으며 다음 문장 다양화 검토 대상으로 표시한다.
- 반복 안정 문구 교정: `v66~v69`의 안정 상태 120행에서 `측정치가 허용 범위 안인 안정 상태이다` 보일러플레이트를 서로 다른 측정·기준 표현으로 직접 바꾸었다.
- 반복 도입부 교정: `v08`, `v14`, `v18`, `v28`에서 중복된 4어절 도입부 10개 쌍의 뒤쪽 문장을 직접 재서술했다.
- primary literal 교정: `v19`와 `v23`에서 primary가 text에 없던 2행을 개념을 문장 주어로 넣어 직접 보완했다.

### 7.2 재감사 실측

| 항목 | 2026-09-10 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `62f44e80a6eb10da8de90b9d5ce7457387dcb499586acedca55c9127ebfc8363` |
| tokenizer tokens(+EOS) / 평균 | 452,172 / 43.688115942 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 | 38.673333333~45.733333333 |
| 파일 평균 허용범위 통과 | 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 872,675 / 33·84.316425121·116 |
| 반복 5어절 유형 / assignments | 4,018 / 9,753 |
| 반복 4어절 도입부 | 0 |

JSON parse·UTF-8/BOM/escape/빈 줄·schema, primary literal·exact/정규화 primary·text 중복, 통제어휘·관계 cardinality·관계 내부 중복은 모두 0이다. 예약 validation unseen relation-set 및 기존 Stage2 corpus와의 exact 교차도 0이며, 정본 공통 검사에 정의된 hard grammar 패턴도 0이다. 독립 문자 TF-IDF·word-set Jaccard와 조사 후보의 사람 확인은 반복 5어절 gate가 남아 있어 아직 실행하지 않았다.

### 7.3 relations 분포(재감사)

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 1,237 |
| `classification` | 1,975 |
| `boundary` | 6,065 |
| `contrast` | 604 |
| `comparison` | 2,278 |
| `function` | 2,967 |
| `role` | 2,006 |
| `process` | 10,155 |
| `state` | 10,079 |
| `attribute` | 3,926 |
| `other` | 0 |

총 relation occurrence는 41,292회이고, `other`가 0이므로 자주 나온 `other` 개념 유형 상위 5개는 해당 없음이다. 관계 cardinality는 3개 108행, 4개 10,242행, 2개·5개 0행으로 이전과 같다.

### 7.4 재판정

파일 평균과 구조 계약은 전부 PASS로 회복되었고 4어절 도입부도 0으로 교정되었다. 그러나 5어절 반복이 4,018종·9,753 assignments로 남아 있어 직접 작성 다양화 gate를 통과하지 못한다. 따라서 A04는 **HOLD**를 유지하며 corpus/checkpoint 포장과 완료 집계를 금지한다. 다음 작업은 v49~v65에 남은 공통 보존·변경·승인 문구를 의미별로 다시 쓰고, 그 후 독립 유사도·조사 검토를 포함한 전체 감사를 재실행하는 것이다.

### 7.5 중단 후 재개한 v66~v69 재작성 최종 실측 (2026-09-10)

중단 지점에서 이미 교정 대상으로 지정된 v66~v69의 `text` 600건을 재개 후 직접 재작성했다. 반도체 공정, 도시 열공급, 해양 부표, 수술실 감염통제의 각 30개 세부 주제를 유지하면서 대기→조건 전환→안정 판정→상태 이동→복귀/억제 흐름을 서로 다른 문장으로 압축했다. `primary`, `relations`, 관계 순서·행 수·파일 수는 변경하지 않았고, source 밖의 corpus/checkpoint는 생성하지 않았다.

| 항목 | 최종 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `4e296ab1b791264c87aca85d936b9c006324c54820682622cac44eafc28f5fab` |
| tokenizer tokens(+EOS) / 평균 | 451,716 / 43.644057971 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 | 38.673333333~45.733333333 |
| 파일 평균 허용범위 통과 | 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 871,992 / 33·84.250434783·122 |
| 반복 5어절 유형 / assignments | 4,131 / 12,087 |
| 반복 4어절 도입부 | 0 |

정본 감사기와 별도 JSONL 계약 검사에서 JSON parse·UTF-8/BOM/escape/빈 줄·schema, primary literal·exact/정규화 primary/text 중복, 13개 통제어휘·관계 cardinality·관계 내부 중복, known hard grammar 및 primary 직후 조사 후보는 모두 오류 0이다. 관계 cardinality는 3개 108행, 4개 10,242행, 2개·5개 0행이며 relations 분포는 §7.3과 동일하다.

v66~v69 재작성으로 파일별 분량 gate는 69/69로 유지되었으나, 전역 반복 5어절이 4,131종·12,087 assignments로 남아 다양화 gate는 여전히 HOLD다. 독립 문자 3~5-gram TF-IDF·word-set Jaccard와 사람 조사 검토는 반복 gate 해소 뒤 실행한다. v49~v65의 의미 문장은 이번 재개 범위에서 무리하게 일괄 치환하지 않았으며, 다음 재개 시 공통 보존·변경·승인 문구를 의미별로 선별 재서술한다. 따라서 A04 최종 판정은 **HOLD**이고 corpus/checkpoint 포장 및 완료 집계는 계속 금지한다.

### 7.6 중단 후 재개한 v49~v65 종결구 재서술 최종 실측 (2026-09-10)

7.5에서 지정한 다음 작업점에 따라 v49~v65의 공통 종결구 53건을 primary-특화 문장으로 직접 재서술했다. `primary`, `relations`, 관계 순서, 레코드·파일 수는 보존했고 v59·v62의 경계 초과를 피하도록 해당 7건은 의미를 유지한 짧은 표현으로 다시 압축했다. source-only 범위는 그대로 유지했으며 corpus/checkpoint는 만들지 않았다.

| 항목 | 최종 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `c07f0f8f8088b1ade38b77ac6c7b4f471dc45f397aa50778818f80d1d4975363` |
| tokenizer tokens(+EOS) / 평균 | 451,864 / 43.658357488 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 | 38.673333333~45.780000000 |
| 파일 평균 허용범위 통과 | 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 872,082 / 33·84.259130435·122 |
| 반복 5어절 유형 / assignments | 4,097 / 11,922 |
| 반복 4어절 도입부 | 0 |

정본 감사기의 JSONL parse·UTF-8/BOM/escape/빈 줄·schema, primary literal·exact/정규화 primary·text 중복, 13개 통제어휘·관계 cardinality·관계 내부 중복, known hard grammar 및 primary 직후 조사 후보는 모두 오류 0이다. 관계 cardinality는 3개 108행, 4개 10,242행, 2개·5개 0행이며 relations 분포는 §7.3과 동일하다.

v49~v65 53건 재서술로 반복 5어절은 4,131→4,097 유형, 12,087→11,922 assignments로 감소했지만 다양화 gate는 여전히 HOLD다. 독립 문자 3~5-gram TF-IDF·word-set Jaccard와 사람 조사 검토는 남은 반복 표현을 의미별로 재서술한 뒤 실행한다. 따라서 A04 최종 판정은 계속 **HOLD**이며, 모든 source gate 통과 전 corpus/checkpoint 포장과 완료 집계를 금지한다.

### 7.7 v68 조사 교정 후 정본 실측 (2026-09-10)

재감사에서 v68의 `오염 신호면`·`불일치 신호면` 30건을 실제 조건 표현 오류로 확인하여 각각 `오염이면`·`불일치면`으로 직접 교정했다. `primary`·`relations`·행 수·파일 수는 보존했다.

| 항목 | 최종 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `fe4686e2ef7615d12993ee5614e9f06c13143ee2842a4719a6afe9fbea92a222` |
| tokenizer tokens(+EOS) / 평균 | 451,834 / 43.655458937 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 | 38.673333333~45.780000000 |
| 파일 평균 허용범위 통과 | 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 872,007 / 33·84.251884058·122 |
| 반복 5어절 유형 / assignments | 4,095 / 11,892 |
| 반복 4어절 도입부 | 0 |

JSONL·schema·primary literal·exact/정규화 중복·13개 통제 relations·cardinality·관계 내부 중복·known hard grammar·primary 직후 조사 후보는 모두 오류 0이다. 관계 cardinality는 3개 108행, 4개 10,242행, 2개·5개 0행이며 relations 분포는 §7.3과 동일하다. v68 교정으로 반복 5어절이 4,097→4,095종, 11,922→11,892 assignments로 감소했지만 다양화 gate는 여전히 HOLD다. 독립 TF-IDF/Jaccard·조사 검토 및 corpus/checkpoint 포장은 남은 반복 표현을 직접 재서술한 뒤에만 진행한다.

### 7.8 v66~v69 고정 절 재서술 후 정본 실측 (2026-09-10)

남은 반복 5어절의 주요 원인이었던 과부하 대기·통신 지연 보류·값 비교·대기 기록 절을 v66~v69에서 의미 보존형 단문으로 325건 직접 재서술했다. 레코드의 `primary`·`relations`와 source 행·파일 수는 보존했다.

| 항목 | 최종 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `324a3808d8d829b44f71d06f6d9886911281eccc8587d8db27fcc8ce52f01595` |
| tokenizer tokens(+EOS) / 평균 | 450,079 / 43.485893720 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 | 38.673333333~45.780000000 |
| 파일 평균 허용범위 통과 | 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 868,362 / 33·83.899710145·116 |
| 반복 5어절 유형 / assignments | 4,091 / 11,561 |
| 반복 4어절 도입부 | 0 |

정본 감사기의 JSONL·schema·primary literal·exact/정규화 중복·13개 통제 relations·cardinality·관계 내부 중복과 known hard grammar/primary 조사 후보는 모두 오류 0이다. 관계 cardinality는 3개 108행, 4개 10,242행, 2개·5개 0행이며 relations 분포는 §7.3과 동일하다. v66~v69 단문 재서술로 반복 5어절이 4,095→4,091종, 11,892→11,561 assignments로 줄었고 파일별 길이 gate는 69/69로 유지되었다. 다만 반복 5어절 다양화 gate는 여전히 HOLD이므로 독립 TF-IDF/Jaccard·조사 검토 및 corpus/checkpoint 포장은 계속 보류한다.

### 7.9 v66~v69 조건·전환·비교 절 추가 재서술 후 정본 실측 (2026-09-10)

중단 후 재개 작업의 연속으로 v66~v69에서 `확인 전`, 과부하 대기, 통신 지연 보류, 운전 비교, 연락 후 격리 등 고정 절 230건을 의미 보존형 단문으로 추가 직접 재서술했다. 각 레코드의 `primary`·`relations`·행 수·파일 수는 보존했다.

| 항목 | 최종 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `fb1c718a5d23148e5effc5d6f09ebce8d4dbc90d7c015817e464dbdfac9a62ac` |
| tokenizer tokens(+EOS) / 평균 | 449,909 / 43.469468599 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 | 38.673333333~45.780000000 |
| 파일 평균 허용범위 통과 | 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 867,562 / 33·83.822415459·116 |
| 반복 5어절 유형 / assignments | 4,083 / 11,431 |
| 반복 4어절 도입부 | 0 |

정본 감사기의 JSONL·schema·primary literal·exact/정규화 중복·13개 통제 relations·cardinality·관계 내부 중복과 known hard grammar/primary 조사 후보는 모두 오류 0이다. 관계 cardinality는 3개 108행, 4개 10,242행, 2개·5개 0행이며 relations 분포는 §7.3과 동일하다. 추가 재서술로 반복 5어절이 4,091→4,083종, 11,561→11,431 assignments로 감소했고 파일별 길이 gate는 69/69로 유지되었다. 그러나 다양화 gate는 여전히 HOLD이므로 남은 반복 표현을 의미별로 직접 재작성한 뒤 독립 TF-IDF/Jaccard·조사 검토 및 corpus/checkpoint 포장을 진행한다.

### 7.10 반복 5어절 의미별 직접 재서술과 독립 유사도·조사 검토 (2026-09-10)

7.9 이후 남은 반복 표현을 의미 단위로 다시 선별해 `text`만 직접 재서술했다. 정상범위 기록, 신호 후 운영 전환, 임계·격리 판단, 하락 후 정상 복귀, 보정 후 점검 복귀의 다섯 의미군에서 15건씩(75건)을 문장 구조와 기준 표현을 바꾸어 썼다. 이어 독립 조사 점검에서 확인한 인접 중복 어절 7행(v68 5행, v69 2행)을 교정하고, 독립 유사도 상위 2쌍의 대표 행 2건을 의미 보존형으로 재서술했다. 이번 단계에서 실제로 수정한 source 행은 서로 겹치지 않는 84건이다. 모든 수정은 `primary`, `relations`, 관계 순서, ID·행 수·파일 수를 보존하고 `text`에만 적용했다.

| 항목 | 최신 정본 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `5da5d8467e8c92f544d43f821287a2c1adba28df3a70b1199df96ebff9ab53bd` |
| tokenizer tokens(+EOS) / 평균 | 449,924 / 43.470917874 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 / 허용범위 통과 | 38.673333333~45.786666667 / 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 867,583 / 33·83.824444444·116 |
| 반복 5어절 유형 / assignments | 3,977 / 10,970 |
| 반복 4어절 도입부 | 0 |

정본 감사기의 JSONL parse·UTF-8/BOM/escape/빈 줄·schema, `primary` literal, exact/정규화 primary·text 중복, 13개 통제 relations·cardinality·관계 내부 중복, 기존 Stage2 교차 중복, known hard grammar 및 primary 직후 조사 후보는 모두 오류 0이다. 관계 cardinality는 3개 108행, 4개 10,242행이며 2개·5개는 0행이다. relations 분포는 `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/1237/1975/6065/604/2278/2967/2006/10155/10079/3926/0`으로 재작성 전과 동일하다.

정본 감사기와 코드를 공유하지 않는 별도 Node 감사기(`tools/audit_a04_similarity_independent.js`)로 문자 3~5-gram TF-IDF와 단어 집합 Jaccard를 다시 계산했다. NFKC·소문자화, raw term count, smooth IDF, L2 정규화 및 희소 pair 누적을 사용했다. 문자 TF-IDF 임계값 0.72 이상은 312쌍, 최대 0.921967387이며 최대쌍은 v65 79행 `공항 제빙노즐복귀79`와 129행 `공항 제빙노즐복귀129`이다. 두 문장은 primary의 숫자 접미사를 제외하면 동일한 본문이 남아 있다. 단어 집합 Jaccard 임계값 0.60 이상은 3,434쌍, 최대 0.92이며 최대쌍은 v65 96행 `공항 일일재개96`과 146행 `공항 일일재개146`으로, 역시 숫자 접미사 외 본문이 같다. 독립 조사 검토는 Hangul로 끝나는 primary 7,204행에서 6,428회의 즉시 부착 조사를 확인했으며, 사용 분포는 `는/은/에서/을/으로/로/이/를/에/가/의 = 1891/1802/659/571/558/398/215/119/113/80/22`였다. hard pattern 0, 인접 중복 어절 0, 조사 후보 0이었다(숫자·라틴 문자 접미사는 발음이 확정되지 않아 자동 판정에서 제외). 전체 결과와 대표쌍은 `audit_reports/machine/TinyLM_Stage2_A04_Independent_Similarity_Review_2026-09-10.json`에 고정했다.

반복 5어절 3,977종·10,970 assignments와 위 고유사도 pair가 잔류하므로 다양성 gate는 **HOLD**다. 독립 검토를 완료했다는 것이 통과를 뜻하지 않으며, 잔여 v66~v69 템플릿과 고유사 pair를 의미별로 추가 재서술하고 두 감사기를 반복해야 한다. 5어절·유사도 gate가 모두 통과하기 전에는 corpus/checkpoint를 포장하거나 완료 집계에 편입하지 않는다. 이번 단계에서도 identity·저밀도 데이터셋과 기존 corpus/checkpoint는 수정하지 않았다.

### 7.11 잔여 반복·고유사도 재서술 후 재감사 (2026-09-10, 진행 중)

7.10의 HOLD를 확인한 뒤, v66~v69의 600개 `text`를 30개 직접 의미 문장군으로 다시 썼다. 기존 15-group 순환이 같은 상태 설명을 재사용하던 문제를 끊기 위해, 대기·전환·비교·회복·보정의 근거와 후속 조치를 각 group마다 다르게 구성했다. 이어 독립 감사의 상위 pair를 근거로 v33~v65의 89행을 개별 원인·상태·복귀 문장으로 직접 재서술했다. 두 작업 모두 `text`만 바꾸었고 `primary`, relations, 행 순서·행 수·파일 수는 보존했다.

| 항목 | 최신 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `310ecd59987184bb712fd95d1e7079956dbdcad1f02d50ab56e5c1ea1e0e2cb7` |
| tokenizer tokens(+EOS) / 평균 | 450,532 / 43.529661836 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 / 허용범위 통과 | 38.673333333~45.786666667 / 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 869,741 / 33·84.032946860·116 |
| 반복 5어절 유형 / assignments | 3,694 / 10,255 |
| 반복 4어절 도입부 | 0 |
| 문자 3~5-gram TF-IDF ≥0.72 / 최대 | 71쌍 / 0.807556658 |
| word-set Jaccard ≥0.60 / 최대 | 281쌍 / 0.818181818 |
| hard·인접 중복·primary 조사 후보 | 0 / 0 / 0 |

독립 TF-IDF는 7.10의 312쌍·0.921967387에서 71쌍·0.807556658로, Jaccard는 3,434쌍·0.92에서 281쌍·0.818181818로 감소했다. 별도 구조 검사는 JSON/UTF-8 BOM·schema·primary literal·exact/정규화 text 중복·13개 통제 relations·cardinality·관계 내부 중복을 모두 0건으로 확인했다. relations 분포와 cardinality(3개 108행, 4개 10,242행)는 변하지 않았다.

그러나 반복 5어절 3,694종·10,255 assignments와 임계값 이상 유사 pair가 남아 있으므로 판정은 계속 **HOLD**다. corpus/checkpoint 포장·완료 집계는 하지 않았으며, 다음 단계는 남은 상위 반복군 및 TF-IDF/Jaccard pair를 다시 개별 의미 문장으로 고치는 것이다. identity·저밀도 데이터셋은 수정하지 않았다.

### 7.12 잔여 반복 상위군·고유사 pair 개별 재서술 및 독립 재감사 (2026-09-10)

7.11의 source-set SHA-256을 입력 고정점으로 삼아 잔여 표적을 다시 산정했다. 당시 반복 5어절에 참여한 행은 2,514개였고, 각 반복구를 한 번만 남기기 위한 greedy 휴리스틱의 재서술 후보는 1,508행이었다. 이 가운데 TF-IDF/Jaccard 임계 pair의 greedy vertex cover와 출현 빈도가 높은 반복군을 합친 253행을 우선 선정해, 각 행의 대상·원인·판정 근거·보존값·변경값에 맞는 완전한 문장으로 개별 재서술했다. 뒤이은 토큰·조사·유사도 점검에서 같은 행을 다시 다듬은 경우와 새 고유사 대표행 1개를 합치면 이번 단계에서 수정된 고유 source 행은 254개다. `primary`, `relations`, 관계 순서, 행 순서·행 수·파일 수는 보존했고 `text`만 수정했다.

첫 재감사에서는 문자 TF-IDF 임계 pair가 71→1, word-set Jaccard가 281→0으로 줄었으나 v34·v36·v59·v60 네 파일의 평균 토큰이 상한을 넘었다. 해당 행을 의미 보존형으로 압축하고, 남은 TF-IDF 1쌍의 v54 108행을 직전 복원 실패 원인·시험 로트·양산 복귀 조건이 드러나도록 다시 썼다. 조사 문맥에서 사람이 확인한 숫자 접미사 주변 표현도 개별적으로 정돈한 뒤, v34·v36의 경계 행 네 건을 추가 압축하여 파일 평균 gate를 69/69로 회복했다.

| 항목 | 최종 재감사 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `bdb44662ab77ca9e3b1ae9d20e858fc34cf00bf2ac895aa82adc798f9be6c1d4` |
| 비-`text` projection SHA-256 | `610922537ce1578ee2e04bfa37c86a38534c29dd0f15ef96c4b4e372d3942f7c` |
| tokenizer tokens(+EOS) / 평균 | 451,462 / 43.619516908 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 / 허용범위 통과 | 38.673333333~45.773333333 / 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 871,605 / 33·84.213043478·116 |
| 반복 5어절 유형 / assignments | 2,816 / 7,766 |
| 반복 4어절 도입부 | 0 |
| 문자 3~5-gram TF-IDF ≥0.72 / 최대 | 0쌍 / 0.710384576 |
| word-set Jaccard ≥0.60 / 최대 | 0쌍 / 0.592592593 |
| hard·인접 중복·primary 조사 후보 | 0 / 0 / 0 |

7.11과 비교하면 반복 5어절은 3,694→2,816종(-878종, -23.77%), assignments는 10,255→7,766(-2,489, -24.27%)로 줄었다. TF-IDF 임계 pair는 71→0, Jaccard 임계 pair는 281→0이 되어 두 독립 유사도 gate는 통과했다. 현재 최대 TF-IDF pair는 v52 67행 `터널 경보인지67`과 v54 67행 `클린룸 경보인지67`의 0.710384576이고, 최대 Jaccard pair는 v63 40행 `축사 검사음성40`과 69행 `축사 질병검체69`의 0.592592593으로 각각 문턱 아래다.

독립 구조 감사는 missing/extra version, UTF-8 BOM·replacement, blank line, JSON parse·schema·150행 계약, 빈 필드, primary literal, 통제어휘·relation cardinality·내부 중복, 제어문자, exact/정규화 primary·text 중복, 인접 중복 어절, 기존 Stage2 corpus 교차 중복, 예약 validation unseen relation-set 충돌을 모두 0으로 확인했다. 비-`text` projection SHA-256은 위 값으로 고정되어 이번 수정이 `text`에만 적용됐음을 재확인했다. relations 분포와 cardinality(3개 108행, 4개 10,242행)는 §7.3과 동일하다. 독립 결과는 다음 기계 보고서에 보존했다.

- `audit_reports/machine/TinyLM_Stage2_A04_Independent_Similarity_Review_2026-09-10.json`
- `audit_reports/machine/TinyLM_Stage2_A04_Independent_Structure_Review_2026-09-10.json`

최종 진단에서 임계값 이상 TF-IDF/Jaccard edge는 0이지만, 반복 5어절에는 2,197행이 아직 참여한다. 각 반복구를 한 번만 남기는 greedy 휴리스틱의 다음 재서술 후보는 1,275행이며 v66~v69의 반복 assignment가 상대적으로 크다. 따라서 유사도·조사·구조 gate는 통과했어도 **반복 5어절 gate 하나 때문에 A04 전체 판정은 HOLD**다. 다음 재개점은 이 1,275행 후보 중 출현 빈도가 높은 의미군부터 개별 재서술하는 작업이다. 모든 source gate가 통과하기 전에는 corpus/checkpoint 포장이나 완료 집계를 하지 않으며, identity·저밀도 데이터셋은 수정하지 않았다.

### 7.13 잔여 반복 1,275행 greedy 직접 재서술과 최종 source PASS (2026-09-10)

§7.12에서 고정한 source-set SHA-256 `bdb44662ab77ca9e3b1ae9d20e858fc34cf00bf2ac895aa82adc798f9be6c1d4`와 진단 JSON을 입력 경계로 삼았다. 반복구별 한 행만 남기는 deterministic greedy 대상 1,275행을 정확히 대조한 뒤, 각 primary의 대상·상태·판정 근거·후속 조치가 드러나도록 `text`를 행별로 직접 재서술했다. 자동화는 고정 문안의 대상 일치·적용·감사에만 사용했으며 문장을 조합 생성하지 않았다.

1차 적용 뒤 source-set SHA-256은 `3c732c7d6ad5149bb185a2376ae70f773bf1f8911a16824626a50a95057b2577`였고 반복 5어절은 2,816종·7,766 assignments에서 476종·1,037 assignments로 줄었다. TF-IDF ≥0.72는 0쌍(최대 0.634180643)이었고 Jaccard ≥0.60은 3쌍(최대 0.625)이 남았다. 새 문장이 길어진 영향으로 파일 평균 gate는 58/69가 되어 이 상태를 확정하지 않았다.

남은 반복에 대해 다시 고정한 greedy 219행을 개별 재서술해 반복을 33종·67 assignments로 낮추고 Jaccard 임계 pair를 0으로 만들었다. 마지막 greedy 20행도 서로 다른 의미 구조로 다시 써 반복 5어절을 0종·0 assignments로 제거했다. 이어 평균 상한을 넘은 11개 version에서 긴 문장 56행을 의미 보존형으로 압축하고, v48 3행을 추가 압축해 파일 평균 gate를 69/69로 회복했다.

독립 조사 감사기의 기존 규칙은 숫자로 끝나는 primary를 발음 불명으로 제외했기 때문에 v49~v69의 레코드 구분 숫자 뒤 `은/는` 불일치를 잡지 못했다. A04의 끝 숫자를 식별자로 제거한 뒤 실제 한글 개념명의 받침으로 판정하도록 감사기를 보강하자 21개 파일에서 1,522행·1,522회가 검출됐다. 본문 의미·ID·relations를 유지한 채 `은→는` 958회, `는→은` 564회만 교정했고, 보강된 전수 감사의 최종 불일치 후보는 0이다.

| 항목 | 최종 재감사 결과 |
|---|---:|
| source 파일 / records | 69 / 10,350 |
| 정렬된 source 파일 SHA-256 집합 | `b67df8dd11661bfcc4d1f75e9400c0b270d41e3217fed066550ddf4f63f785e1` |
| 비-`text` projection SHA-256 | `610922537ce1578ee2e04bfa37c86a38534c29dd0f15ef96c4b4e372d3942f7c` |
| tokenizer tokens(+EOS) / 평균 | 455,328 / 43.993043478 |
| record token 최소~최대 | 19~72 |
| 파일 평균 최소~최대 / 허용범위 통과 | 38.960000000~45.760000000 / 69/69 |
| text 문자 총계 / record 최소·평균·최대 | 879,735 / 33·84.998550725·115 |
| 반복 5어절 유형 / assignments | 0 / 0 |
| 반복 4어절 도입부 | 0 |
| 문자 3~5-gram TF-IDF ≥0.72 / 최대 | 0쌍 / 0.574271279 |
| word-set Jaccard ≥0.60 / 최대 | 0쌍 / 0.590909091 |
| hard·인접 중복·primary 조사 후보 | 0 / 0 / 0 |
| 조사 검토 범위 | 10,350행, 숫자-ID primary 3,146행, 즉시 부착 조사 9,603회 |

독립 구조 감사에서는 version 누락·초과, UTF-8 BOM·replacement, blank line, JSON parse·schema·150행 계약, 빈 필드, primary literal, 통제 relations·cardinality·내부 중복, 제어문자, exact/정규화 primary·text 중복, 인접 중복 어절, 기존 Stage2 corpus 교차 중복, 예약 validation unseen relation-set 충돌이 모두 0이다. 비-`text` projection 해시가 §7.12와 같으므로 1,275·219·20행 직접 재서술과 59행 분량 교정, 1,522행 조사 교정에서 `primary`, relations, ID와 행 구조가 보존됐음을 확인했다.

relations 분포는 `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/1237/1975/6065/604/2278/2967/2006/10155/10079/3926/0`으로 변하지 않았고, cardinality도 3개 108행·4개 10,242행이다. `other`가 0회라서 자주 나온 `other` 개념 유형은 없다.

기계 근거는 기존 독립 구조·유사도 보고서와 `audit_reports/machine/TinyLM_Stage2_A04_Residual_Repeat5_Final_2026-09-10.json`에 갱신했다. 모든 source gate가 통과했으므로 A04의 최종 판정은 **PASS_SOURCE_GATES**다. 다만 이번 요청 범위는 잔여 반복 재서술과 재감사였으므로 corpus/checkpoint 포장과 완료 집계는 실행하지 않았다. identity·저밀도 데이터셋도 수정하지 않았다.

### 7.14 숫자 접미사 primary의 의미 정정 (2026-09-10)

사용자가 제기한 `자동차11 자동차11은 ...` 사례를 실제 source에서 역추적했다. A04 v49~v69의 3,146개 primary가 모두 `기본 개념명 + 해당 source 파일의 1-based 행 번호` 형태였으며, 숫자는 의미 개념이나 ID가 아니라 생성 과정의 행 구분자였다. 이 표면형을 그대로 학습시키면 모델이 `자동차`가 아니라 `자동차11`을 별도 개념으로 암기할 수 있으므로 타당하지 않다.

`stage2_highdensity_dataset/tools/repair_a04_numbered_primaries.js`를 기본 미리보기 후 `--apply`로 실행해 숫자 접미사를 제거하고, 제거한 기본명이 같은 파일에서 충돌하는 1,325행에는 기존 text 의미에서 뽑은 짧은 semantic qualifier만 붙였다. 나머지 1,821행은 기본 개념명으로 정리했다. qualifier는 숫자·행 번호가 아니며 primary와 text 양쪽에 동일하게 반영했다. source schema(`primary`, `text`, `relations`), relation 배열·행 순서·행 수·파일 수는 보존했고, source에는 별도 ID 필드가 없으므로 builder가 중앙 예약 manifest에서 부여할 ID도 변경하지 않았다. qualifier 도입 후 생긴 주어 인접 반복 3건은 `repair_a04_post_qualifier_editorial.js`로 의미가 겹치지 않도록 직접 재서술했다.

현재 source 정본은 다음과 같다.

| 항목 | 결과 |
|---|---:|
| 대상 파일 / records | 69 / 10,350 |
| 숫자 suffix 잔존 primary | 0 |
| 파일 내부 primary 중복 | 0 |
| semantic qualifier 적용 | 1,325행 / 21파일 |
| 독립 구조 감사 | PASS (모든 오류 0) |
| primary literal·조사 후보 | 0 / 0 |
| 독립 문자 TF-IDF ≥0.72 | 0쌍 (최대 0.665704324) |
| 독립 word Jaccard ≥0.60 | 1쌍 (최대 0.619047619) |
| 정본 tokenizer tokens(+EOS) / 평균 | 456,099 / 44.067536232 |

대표 행은 v53의 `공항 제설차 대기11`→`공항 제설차 대기`, `공항 항공기 대기31`→`공항 항공기 대기`, `공항 전원대기61`→`공항 전원대기 — 제설설비 대기`, `공항 전원절체62`→`공항 전원절체 — 비상공급 분담`이다. 모두 text의 주어도 새 primary와 일치한다.

숫자 제거로 의미 오류는 해소됐지만, qualifier가 문장을 늘려 기존 파일 평균 목표(37.4625~45.7875)는 63/69파일만 통과하고 v58·v62·v65·v66·v67·v69 6개가 상한을 넘었다. 정본 source 감사의 반복 5어절도 25종·51 assignments로 재검토 대상이며, word-Jaccard 1쌍도 남아 있다. 따라서 이번 변경의 **semantic_numbered_primary_repair와 구조·조사 재감사는 PASS**지만, A04 전체 source gate와 corpus 포장은 길이·잔여 유사도 항목을 별도로 정리할 때까지 **FOLLOW_UP/HOLD**로 둔다. §7.13의 `b67df...` 해시와 PASS 판정은 숫자 접미사 정정 전 역사적 snapshot이며 현재 정본은 `cd580a44f4648fa14af2365754a9a839a11e95bad9ad10c0d827c86d50046ba1`이다.

기계 기록은 `audit_reports/machine/TinyLM_Stage2_A04_NumberedPrimary_SemanticRepair_Audit_2026-09-10.json`, 독립 구조·유사도 기록은 같은 날짜의 `TinyLM_Stage2_A04_Independent_Structure_Review_2026-09-10.json`·`TinyLM_Stage2_A04_Independent_Similarity_Review_2026-09-10.json`에 보존했다. 이전 audit snapshot과 교정 스크립트 fixture 안의 숫자 예시는 변경 전 증거로 남겨 두었으며 학습 경로의 source/train/val 데이터가 아니다. Identity 및 저밀도 데이터셋은 수정하지 않았다.

### 7.15 현재 source 재감사와 수정 필요 범위 (2026-09-11, read-only)

숫자 접미사 의미 정정 후의 현재 source를 다시 전수 검사했다. 이 절의 감사는 **read-only**이며 source/train/val, corpus/checkpoint, A05 파일은 수정하지 않았다. 독립 구조 감사의 현재 source-set SHA-256은 `cd580a44f4648fa14af2365754a9a839a11e95bad9ad10c0d827c86d50046ba1`, 비-`text` projection SHA-256은 `60a4f5ead036871bbd111b04622054df023b4adf845f25a69d961d3b768e84bb`이다. §7.13의 projection과 다른 것은 그 뒤에 primary의 숫자 접미사를 의미 정정한 이력이 있기 때문이며, 과거 PASS snapshot과 동일 파일임을 주장하는 근거로 사용해서는 안 된다.

| 범주 | 현재 결과 | 판정 |
|---|---:|---|
| source 파일 / records | 69 / 10,350 | 통과 |
| JSONL·UTF-8/BOM·schema·150행·빈 필드 | 오류 0 | 통과 |
| primary literal·exact/정규화 primary/text 중복·기존 Stage2 교차 중복 | 오류 0 | 통과 |
| 13개 통제 relations·2~5 cardinality·관계 내부 중복 | 오류 0 | 통과 |
| 제어문자·인접 중복 어절·예약 val unseen relation-set 충돌 | 오류 0 | 통과 |
| tokenizer tokens(+EOS) / 전체 평균 | 456,099 / 44.067536232 | 전체 평균은 범위 안 |
| 파일 평균 목표(37.4625~45.7875) 통과 | 63 / 69 | **HOLD** |
| 반복 5어절 유형 / assignments | 25 / 51 | **HOLD** |
| 반복 4어절 도입부 유형 | 3 | 검토 필요 |
| 독립 TF-IDF >= 0.72 | 0쌍, 최대 0.665704324 | 통과 |
| 독립 word-set Jaccard >= 0.60 | 1쌍, 최대 0.619047619 | **HOLD** |
| primary 조사 불일치·hard pattern·인접 중복 후보 | 0 / 0 / 0 | 통과 |

현재 relations 빈도는 `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/1237/1975/6065/604/2278/2967/2006/10155/10079/3926/0`이다. `other`는 0회이므로 이 범위에서 보고할 빈발 `other` 유형은 없다.

#### 7.15.1 길이·반복·유사도에서 필요한 text 수정

상한을 넘은 파일은 아래 여섯 개다. 각 파일은 150행이므로 목표 상한을 만족하려면 파일당 tokens(+EOS)가 최대 6,868이어야 한다. 현 상태에서 총 **최소 1,484 token**을 의미 보존형으로 압축해야 한다. 단, 단순 삭제가 아니라 대상·상태·원인·판정 근거·후속 조치의 대응 관계를 유지하는 문장 재서술이어야 한다.

| 파일 | 현재 tokens(+EOS) / 평균 | 목표까지 최소 감소량 |
|---|---:|---:|
| v58 | 7,475 / 49.833333333 | 607 |
| v62 | 7,063 / 47.086666667 | 195 |
| v65 | 7,059 / 47.060000000 | 191 |
| v66 | 7,005 / 46.700000000 | 137 |
| v67 | 7,018 / 46.786666667 | 150 |
| v69 | 7,072 / 47.146666667 | 204 |

반복 5어절은 35행이 참여하며, 각 반복을 한 번만 남기기 위한 deterministic greedy 최소 후보는 18행이다. 이는 **자동 재작성 지시가 아니라**, 재서술 범위를 빠짐없이 좁히는 하한 근거다. 현재 후보는 다음과 같다.

| locator | primary |
|---|---|
| v58:73 | 산림 복구판정 — 산불 촉발·억제 |
| v68:55 | 해양부표 클로로필 — 살피 포화 |
| v52:84 | 터널 배수전원 — 온도 촉발·억제 |
| v58:63 | 산림 복구판정 — 재개 촉발·억제 |
| v65:66 | 공항 항공기출발 — 합격 촉발·억제 |
| v56:48 | 해양 부표 수질안정 — 염분·탁도·수온 안정 |
| v52:10 | 터널 배수펌프 — 증가 촉발·억제 |
| v65:83 | 공항 안전복귀 — 결빙 복귀 |
| v65:71 | 공항 활주로검사 — 재시험 촉발·억제 |
| v58:125 | 산림 회복기록 — 뿌리 촉발·억제 |
| v64:63 | 터널 신호이탈 — 지연 촉발·억제 |
| v62:94 | 항만 안전복귀 — 안정 촉발·억제 |
| v62:90 | 항만 교대확인 — 찾 인계 |
| v60:137 | 발효 출하복귀 — 보완 촉발·억제 |
| v59:90 | 전기버스 충전품질 — 지연 촉발·억제 |
| v55:17 | 열공급 배관압력 — 급증 촉발·억제 |
| v55:129 | 열공급 최종확인 |
| v52:82 | 터널 배수전원 — 상승 촉발·억제 |

독립 Jaccard의 유일한 임계 초과쌍은 v49:145 `데이터센터 중간확정`과 v50:135 `항만 중간확정`(0.619047619)이다. 18행과 겹치지 않으므로, Jaccard를 문턱 아래로 내리는 최소 text 수정은 이 두 행 중 하나를 의미별로 다시 쓰는 것이다. 같은 relations만 비교하는 reviewer-assist도 103 relation-set에서 240,764 후보쌍을 cap 없이 점검했고 raw Jaccard 1, raw TF-IDF 0, primary masking 후 Jaccard 4, TF-IDF 1의 검토 신호를 냈다. 이는 독립 전수 점수와 서로 다른 후보 생성·masking 정의를 쓰므로 수치가 충돌한 것이 아니라, primary를 제외해도 남는 문장 골격을 추가 검토하라는 신호다.

#### 7.15.2 자연성·문장 형식 수정 전 판단

`text`가 `primary + 은/는`으로 즉시 시작하는 행은 5,784/10,350(55.884058%)이고, v31~v69의 39파일이 잠정 45% HOLD선을 넘는다. 이 값은 한국어 조사 오류율이 아니라 **도입 형식 집중도**다. 45% 이하를 기계 gate로 적용한다면 적어도 1,127행의 첫 문장을 다른 문형으로 바꾸어야 하지만, 숫자만 맞추기 위한 일괄 치환은 금지한다. 원인·조건절 선행, 질문/대조형 도입, 관찰값 선행, 정의 위치 이동 등 의미에 맞는 family 단위 설계를 먼저 승인해야 한다.

현재 A04에는 term registry가 없어서 출처·실제 사용 여부를 기계적으로 대조할 수 없다. 표본을 직접 읽은 결과 다음은 **명확한 재검토 후보**다.

- `찾 인계`: v62:90, v63:130, v64:84의 세 primary. 동사 `찾`과 명사 `인계`의 결합이 표준 개념명으로 자연스럽지 않다.
- `살피 포화`: v67:90, v68:55의 두 primary. `살피`와 `포화`의 결합이 상태·과정명으로 불명확하다.
- `중간확정`: v49~v56의 9행. 전이 기록의 중간 확정이라는 뜻은 문맥으로 설명되지만, 일반적 현장 용어인지와 primary로 쓸 자연스러운 명칭인지는 registry 또는 사람 검토가 필요하다. v49:145/v50:135의 유사쌍도 이 family에 속한다.

위 세 그룹은 형태 휴리스틱만으로 자동 치환하지 않는다. 특히 `중간확정`은 의미를 살릴 수 있어 명칭 유지·보완 qualifier·새 명칭 중 무엇이 맞는지 domain 기준이 필요하다. 반면 `찾 인계`와 `살피 포화`는 primary와 text를 함께 개별 재서술할 우선 후보이며, 수정 뒤 primary literal·중복·조사·유사도·토큰 gate를 다시 실행해야 한다.

#### 7.15.3 현재 결론과 다음 수정 순서

현재 판정은 **HOLD_SOURCE_PACKAGING**이다. 구조/관계/조사/TF-IDF gate는 통과했지만, 길이 6파일·반복 5어절·Jaccard 1쌍이 남아 있어 corpus/checkpoint 포장이나 완료 집계로 넘길 수 없다. `primary+은/는` 집중도와 용어 자연성은 새로 도입한 잠정 quality signal이므로, 이것만으로 무차별 대량 재작성하지 않고 별도 승인된 문형 목표와 term registry를 먼저 둔다.

수정이 승인될 경우의 안전한 순서는 다음과 같다.

1. `찾 인계` 3행과 `살피 포화` 2행을 primary와 text의 의미 대응이 보이도록 사람이 직접 재서술한다.
2. 위 18행 및 `중간확정` Jaccard 쌍 중 한 행을 각자의 원인·근거·조치가 다른 문장으로 재서술한다.
3. 여섯 파일에서 합계 최소 1,484 token을 압축하되, 1~2과 겹치는 행을 먼저 써서 수정 범위를 불필요하게 넓히지 않는다.
4. source hash를 다시 고정하고 구조·정본 token·반복 5어절·독립 TF-IDF/Jaccard·조사·A04 selector reviewer-assist를 모두 재감사한다.
5. 자연성 registry와 문형 다양성 목표가 승인된 뒤에만 1,127행 이상의 family-level 도입문 재설계를 별도 작업으로 수행한다.

이번 절은 수정 대상을 보고한 것이며, 위 재작성은 아직 적용하지 않았다. Identity·저밀도 데이터셋, Stage1 확정 데이터셋, A05 source는 수정하지 않았다.

### 7.16 직접 재서술·전수 재감사 및 용어 적합성 사용자 검토표 (2026-09-11)

사용자 승인에 따라 §7.15의 보류 항목을 record별로 직접 재서술했다. 숫자 접미사 제거 뒤 남은 명백한 표기 결함과 반복·고유사 문장을 먼저 고쳤고, 고토큰 파일의 문장은 대상·원인·판정·후속 조치가 남도록 압축했다. 총 149회 patch 적용은 같은 행의 재감사 후 미세 조정을 포함하며, 실제로 수정한 고유 source 행은 **142행**이다. 이 중 primary와 text를 함께 바꾼 행은 6행이다.

- v62:90, v63:130: `찾 인계` → `인계 누락 점검`
- v64:84: `찾 인계` → `교대 전 기록 대조`
- v67:90, v68:55: `살피 포화` → `보정 후 재검토`
- v56:103: `염분·탁도·수온 상태` → `복합 수질지표 안정`

행 순서·파일 수·각 파일 150행 계약·relations 배열과 순서는 보존했다. primary가 바뀐 6행 때문에 비-`text` projection 해시는 §7.15와 달라졌으며, 이는 의도한 개념명 정정의 결과다. relations 분포는 전과 동일하다.

| 항목 | 최종 전수 재감사 결과 |
|---|---:|
| 독립 구조 감사 | **PASS** |
| source 파일 / records | 69 / 10,350 |
| source-set SHA-256 | `691c7e563bd7ea39a9f03c884eb1fd0d84b3f09cdaa90311253b44f63ebd7d7e` |
| 비-`text` projection SHA-256 | `8e4d404db49289cbf070494a004f5ccabee5ba39e7f60ce536a1296ae83371f6` |
| 구조·schema·중복·교차 중복·통제 relations 오류 | 0 |
| 정본 tokenizer tokens(+EOS) / 평균 | 454,462 / 43.909371981 |
| record token 최소~최대 | 17~72 |
| 파일 평균 최소~최대 / 목표 범위 통과 | 38.960000000~45.780000000 / **69/69** |
| text 문자 총계 / record 최소·평균·최대 | 880,193 / 31·85.042801932·115 |
| 반복 5어절 유형 / assignments / 참여·greedy 행 | **0 / 0 / 0·0** |
| 반복 4어절 도입부 유형 | **0** |
| 독립 문자 3~5-gram TF-IDF >=0.72 / 최대 | **0쌍 / 0.665507357** |
| 독립 word-set Jaccard >=0.60 / 최대 | **0쌍 / 0.590909091** |
| hard pattern·인접 중복 어절·primary 조사 후보 | **0 / 0 / 0** |

§7.15 기준 456,099 tokens(+EOS)에서 1,637 token을 줄였고, 상한을 넘던 v58/v62/v65/v66/v67/v69는 각각 6,851/6,855/6,867/6,860/6,867/6,847 token으로 모두 범위에 들어왔다. 독립 유사도 최대 pair는 TF-IDF 기준 v60:81 `발효 냉각수대기`–v61:18 `센터 냉각수대기`(0.665507357), Jaccard 기준 v34:28 `저장장치 충전출력상향 조건판정`–v34:53 `저장장치 방전출력상향 조건판정`(0.590909091)이며 각각 문턱 미만이다.

relations 빈도는 `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other = 0/0/1237/1975/6065/604/2278/2967/2006/10155/10079/3926/0`이다. `other`는 0회이므로 이 범위의 빈발 `other` 유형은 없다.

#### 7.16.1 reviewer-assist 잔여 신호

reviewer-assist의 즉시 재서술 대상은 0건이다. 다만 `primary+은/는`으로 시작하는 도입 형식은 5,781/10,350(**55.8550725%**)이고, 잠정 45% HOLD선을 넘는 파일은 39개다. 이는 조사 오류가 아니라 문형 집중도 신호다. 같은 relations 집합에서의 근접 유사도 검토 신호도 3개 남아 있다. 따라서 reviewer-assist는 ChatGPT 검토 대기 43건(문형 집중 40건, relations-set 유사도 3건)을 보고한다.

이 신호만으로 5,000여 행을 일괄 치환하면 의미·도메인 맥락을 훼손할 위험이 있으므로, 이번에는 수정하지 않았다. family별 도입문 다양성 목표와 용어 registry를 승인한 별도 작업에서 다룬다.

#### 7.16.2 사용자 Y/N 용어 검토표

명확한 문법·형태상 후보와 사용자가 지목한 합성어를 별도 TSV로 만들었다.

- `audit_reports/review/TinyLM_Stage2_A04_Term_Appropriateness_User_Review_2026-09-11.tsv`
- `audit_reports/review/README_A04_Term_Appropriateness_User_Review_2026-09-11.md`

총 69행 / 검토 용어 33종이며, `CONNECTIVE_FRAGMENT` 17행, `TRUNCATED_FRAGMENT` 17행, `VERB_STEM_COMPOSITE` 12행, `MEASUREMENT_TERM_REVIEW` 7행, `NEGATION_FRAGMENT` 3행, `SYNTHETIC_COMPOUND_REVIEW` 13행이다. 마지막 범주는 `중간확정` 9행과 `차량통행` 4행을 포함한다. TSV의 마지막 열 `user_decision_Y_or_N`은 현재 모두 `PENDING`이며, 사용자는 다음처럼 입력한다.

- `Y`: primary와 text를 함께 직접 재작성해야 함
- `N`: 현 표현 유지
- `PENDING`: 아직 결정하지 않음

반환 후에는 `Y` 행만 locator·현재 primary·text를 다시 대조해 record별 patch로 바꾸고, 전수 재감사를 다시 수행한다. `N`과 `PENDING`을 근거로 한 자동 수정은 하지 않는다.

결론적으로 구조·길이·반복·유사도·조사라는 객관 source gate는 **PASS**다. 다만 69건 용어 검토와 문형 다양성 policy 신호가 남아 있어 corpus/checkpoint 포장과 완료 집계는 계속 보류한다. A05, packaged train/val, identity·저밀도·Stage1 확정 데이터셋은 수정하지 않았다.

### 7.17 warning-only 자연성 감사 확장·고신뢰 절단표현 재서술·대시 primary 재검토 (2026-09-11)

사용자 지시에 따라 기존 `HARD` 구조 오류와 별개로, AI가 만든 어색한 표현을 수집하는 `ADVISORY_WARNING_ONLY` 규칙 파일을 추가했다. 규칙은 source를 바꾸지 않고 구조 verdict도 바꾸지 않는다. exact match는 **고신뢰 재서술 후보**, prefix·대시·불투명 기록행위는 검토·통계 신호다. 따라서 과거 구조 PASS는 실제로 수행된 감사 결과이지만, 한국어 자연성 전체 PASS를 뜻하지 않았다는 점을 명시한다.

#### 7.17.1 구현과 직접 재서술 범위

- 규칙 파일: `tools/primary_naturalness_warning_rules_v1.json`
- 적용 감사기: `tools/audit_stage2_primary_reviewer_assist.js`, `tools/audit_stage2_a04_source.js`, `tools/audit_a04_structure_independent.js`, `tools/audit_a04_dash_primary_naturalness.js`
- 새 대시 감사는 `primary`의 대시 수, text 첫머리에 primary가 조사와 함께 그대로 복사된 수, core 재사용 fan-out, exact/prefix/불투명 text warning을 분리한다.
- Node syntax 검사와 reviewer-assist·대시 감사기의 in-memory self-test를 통과했다. source 변경·LLM/API 호출·자동 재서술은 감사기 기능에 없다.

확장 목록으로 잡힌 high-confidence 절단·연결어 표현은 처음에 29행이었다. 각 행을 원문의 원인·상태·판정·후속 조치에 맞춰 primary와 text를 함께 직접 재서술했고, relations 배열·행 순서·파일 수는 보존했다. 대상은 `v52:102,105`, `v55:18,33,72,99`, `v57:63`, `v62:149`, `v64:87,137,148`, `v65:121,127,149`, `v66:15,38,58,118,141`, `v67:42,48,86`, `v68:5,19,32,71`, `v69:97,122,125`다. 예를 들어 `사 차단`은 `터널 배수 기록 누락`, `내리 재처리`는 `공항 활주로 재시험 뒤 운항 승인`, `좁히 상태`는 `수술실 출혈 대응 범위 조정`으로 바꿨다.

첫 재감사에서 새 5어절 반복 1종이 발견되어 v57:63의 두 번째 문장만 의미 보존형으로 다시 썼다. 이는 자동 치환이 아니라 해당 행의 `마지막 기록과 누락 시각` 서술을 `마지막 작성 기록과 빠진 시간대`로 구체화한 것이다.

이후 `변경순서를 정한다`에 의존해 실제 판단을 설명하지 못한 5행(v49:131, v52:101, v55:46·150, v56:106)도 고신뢰 semantic 오류로 직접 재서술했다. `터널 배수 상태 기록 대조`처럼 상태값의 대조·불일치 시 조치를 명시했으며, 이로써 불투명 기록행위 warning은 0이 됐다.

#### 7.17.2 최종 전수 재감사

| 항목 | 결과 |
|---|---:|
| 독립 구조 감사 / 오류 합계 | **PASS / 0** |
| source 파일 / records | 69 / 10,350 |
| source-set SHA-256 | `554a3adf2e1b1cc9cc5ee2150db4cbebe91ecb8587477827f3c88f66739b7378` |
| 비-text projection SHA-256 | `a21ac53d8bbcc3fd731211dc25e06978d89f0c0e0174b0f09d9c8a3eccd3f84a` |
| tokenizer tokens(+EOS) / 평균 | 454,150 / 43.879227053 |
| 파일 평균 범위 / 목표 통과 | 38.960000000~45.760000000 / **69/69** |
| 반복 5어절 유형·assignments / 4어절 도입부 | **0·0 / 0** |
| 독립 TF-IDF >=0.72 / 최대 | **0쌍 / 0.666119893** |
| 독립 word-set Jaccard >=0.60 / 최대 | **0쌍 / 0.590909091** |
| hard pattern·인접 중복·primary 조사 후보 | **0 / 0 / 0** |
| 통제 relations 분포 | `0/0/1237/1975/6065/604/2278/2967/2006/10155/10079/3926/0` |

relations 순서는 `is_a/subclass_of/part_of/classification/boundary/contrast/comparison/function/role/process/state/attribute/other`다. `other`는 0회이므로 빈발 `other` 유형은 없다.

#### 7.17.3 대시 primary 자연성 결론 — 구조 PASS와 별도 HOLD

| warning/statistic | 최종 값 |
|---|---:|
| 자연성 warning records / assignments | 1,233 / 1,233 |
| 잔여 `primary_dash_qualifier` | 1,233 records |
| exact·prefix 절단표현 direct rewrite candidate | **0** |
| 불투명 기록행위 text warning | **0 records** |
| 대시 primary 중 text 첫머리에 조사와 함께 그대로 복사 | 1,116 / 1,233 (**90.5109%**) |
| 대시 core group / 재사용 core group | 350 / 341 |
| 재사용 core group에 속한 records | 1,224 |
| reviewer-assist primary+은/는 | 5,760 / 10,350 (**55.6522%**, 39 files diversity HOLD) |

`산림 복구판정 — 충족 촉발·억제`처럼 대시형 라벨을 `…는`의 주어로 복사한 사례와, `산림 복구판정` core에 50개 qualifier를 붙인 사례는 명백히 label-template 성격을 보인다. 다만 대시가 있다고 곧바로 의미가 거짓인 것은 아니므로 1,233행을 기계적으로 삭제하거나 일괄 치환하지 않았다. 남은 1,233건은 모두 `DASH_DELIMITER_REVIEW`다.

따라서 이 시점의 최종 판정은 **구조·중복·토큰·조사 gate PASS, 자연성·문형 다양성 HOLD_SOURCE_PACKAGING**이다. 기존 감사와 재서술은 실행됐지만, 기존 범위가 반복·유사도·조사·명백한 단어 조각에 치우쳐 있어 사용자가 기대한 자연스러운 일상 한국어를 전수 보증하기에는 불충분했다. 이후에는 family별로 자연스러운 개념명과 문장 도입부를 다시 설계하고, 각 레코드를 의미별로 직접 재서술한 뒤 동일 전수 감사를 반복해야 한다.

기계 결과는 `audit_reports/machine/TinyLM_Stage2_A04_Source_Naturalness_Final_2026-09-11.json`, `TinyLM_Stage2_A04_Independent_Structure_Final_2026-09-11.json`, `TinyLM_Stage2_A04_Independent_Similarity_Final_2026-09-11.json`, `TinyLM_Stage2_A04_ReviewerAssist_Naturalness_Final_2026-09-11.json`, `TinyLM_Stage2_A04_DashPrimary_Naturalness_Final_2026-09-11.json`에 보존했다. A05, packaged `train/val`, manifest/checkpoint, identity·저밀도·Stage1 확정 데이터셋은 수정하지 않았다.
