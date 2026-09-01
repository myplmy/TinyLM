# Stage3 pilot 의미 교정 후 재감사 보고서

> 최종 판정: **PASS**

## 교정 내역

- `S3-GAV-00073`: 한글 문장에 삽입된 `오염 plume 경계 추적`을 `오염 확산띠 경계 추적`으로 고쳐 primary와 본문 literal을 통일했다.
- 나머지 source는 의미를 바꾸지 않았으며 네 JSON은 정본 source에서 다시 포장했다.

## 최종 감사

- 4파일 × 150 = 600 records, source 대응 600/600
- validation 18 true / 132 false = 12.0%; true·false relation-set과 개별 label 조건 오류 0
- ID·concept·text·concept+relation-set exact duplicate 0
- 내부·Stage1 고밀도 교차 반복 5어절 0, 반복 4어절 문두 0
- train-val exact concept/text 0
- character 3~5 gram TF-IDF 최고값: 내부 0.228931, train-val 0.107500
- concept 문두 전 파일 0, 2문장 이상 각 150, lag6 16/12/29/10
- 알려진 조사·호응·연속 동일어 오류 패턴 0
- 보호 baseline 371개 SHA 불일치·누락 0

## Relations 분포

| relation | count | relation | count |
|---|---:|---|---:|
| is_a | 0 | subclass_of | 0 |
| part_of | 54 | classification | 30 |
| boundary | 198 | contrast | 7 |
| comparison | 45 | function | 280 |
| role | 36 | process | 397 |
| state | 509 | attribute | 166 |
| other | 57 |  |  |

`other` 상위 유형은 재제작 정보 보존, 재료 이력 보존, 사용자 치수 미확정, 설치 조건 미확정, 현장 조건 확인이 각 1건이다. 세부 SHA는 [machine report](machine/TinyLM_Stage3_Pilot_Reaudit_2026-09-02.json)에 기록했다.
