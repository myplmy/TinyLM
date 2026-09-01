# Stage2 pilot 의미 교정 후 재감사 보고서

> 최종 판정: **PASS**  
> 정본 source를 직접 고친 뒤 네 JSON을 source에서 다시 포장하고 전수 구조 감사와 표본 의미 감사를 수행했다.

## 교정 내역

- `S2-CSH-00130`: 현상과 반대였던 `로컬 캐시 명령 억제`를 `로컬 캐시의 이전 명령 재전송`으로 고쳐 concept와 text의 방향을 맞췄다.
- `S2-CSV-00030`: 재감사 TF-IDF 상위쌍에서 `S2-CSH-00037`과 발전기 전환 사건이 실질적으로 겹침을 발견했다. validation 행을 `진공 포장의 산소 농도 저하 경로`라는 문화재 보존 사례로 전면 교체했다. 정렬 relation-set과 `unseen_relation: false` 조건은 유지했다.

## 최종 감사

- 4파일 × 150 = 600 records, source 대응 600/600
- validation 18 true / 132 false = 12.0%; true의 train 관측 set 0, false의 train 미관측 set 0, train 미관측 개별 label 0
- ID·concept·text·concept+relation-set exact duplicate 0
- 내부·Stage1 고밀도 교차 반복 5어절 0, 반복 4어절 문두 0
- train-val exact concept/text 0
- character 3~5 gram TF-IDF 최고값: 내부 0.276059, train-val 0.192605, 기준 0.72 미만
- concept 문두 11/0/0/1, 2문장 이상 각 150, lag6 56/70/54/41
- 알려진 조사·호응·연속 동일어 오류 패턴 0
- 보호 baseline 371개 SHA 불일치·누락 0

## Relations 분포

| relation | count | relation | count |
|---|---:|---|---:|
| is_a | 0 | subclass_of | 0 |
| part_of | 40 | classification | 3 |
| boundary | 285 | contrast | 0 |
| comparison | 60 | function | 7 |
| role | 122 | process | 514 |
| state | 534 | attribute | 210 |
| other | 72 |  |  |

`other` 상위 유형은 희귀 단일 사례 2, 기록 결측 1, 동시 개입 1, 측정 척도 변경 1, 관측되지 않은 조작 1이다. 모두 12개 관계로 정확히 표현하기 어려운 인과 판정 잔여 의미다.

세부 SHA와 파일별 구조 수치는 [machine report](machine/TinyLM_Stage2_Pilot_Reaudit_2026-09-02.json)에 기록했다.
