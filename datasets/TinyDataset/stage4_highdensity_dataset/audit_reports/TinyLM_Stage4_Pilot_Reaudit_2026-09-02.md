# Stage4 pilot 의미 교정 후 재감사 보고서

> 최종 판정: **PASS**

## 교정 내역

- `S4-DRV-00028`: 확인되지 않은 서쪽 공간을 미리 확정하지 않고 `그 뒤의 공간적 지시 범위`로 유보했다.
- `S4-DRV-00051`: 음식 흔적이라는 직접 단서를 주걱에 연결하고 `그 도구가 마르지 않게`로 피보존 대상을 바로잡았다.
- true slice의 relation-slot형 primary 11건을 참조 단서 중심으로 직접 자연화했다: `00058`, `00063`, `00068`, `00076`, `00088`, `00105`, `00113`, `00121`, `00129`, `00136`, `00143`.
- `S4-DSH-00067`: `00066`과 겹치던 두 번째 문장의 `면담 시간 변경 제안의` 도입부를 `이 면담 시간 변경 제안의 철회로`로 재서술해 문장 단위 4어절 opener 중복을 제거했다.
- 각 행의 기존 relation-set은 새 문장 안에서 실제로 contrast·comparison·role·function·classification 등을 설명하도록 다시 썼다.

## 최종 감사

- 4파일 × 150 = 600 records, source 대응 600/600
- validation 18 true / 132 false = 12.0%; true의 train 관측 set 0, false의 train 미관측 set 0, 개별 label coverage 오류 0
- ID·concept·text·concept+relation-set exact duplicate 0
- 내부·Stage1 고밀도 교차 반복 5어절 0, 반복 4어절 문두 0
- train-val exact concept/text 0
- character 3~5 gram TF-IDF 최고값: 내부 0.208237, train-val 0.239433
- concept 문두 전 파일 0, 2문장 이상 각 150, lag6 29/24/22/29
- 알려진 조사·호응·연속 동일어 오류 패턴 0
- 보호 baseline 371개 SHA 불일치·누락 0

## Relations 분포

| relation | count | relation | count |
|---|---:|---|---:|
| is_a | 0 | subclass_of | 0 |
| part_of | 0 | classification | 289 |
| boundary | 351 | contrast | 47 |
| comparison | 14 | function | 24 |
| role | 194 | process | 126 |
| state | 552 | attribute | 96 |
| other | 89 |  |  |

`other` 상위 유형은 시간이 다른 자기 지시 2, 대화 참여자 밖 집단 1, 기간 단위 참조 1, 회상 공간 참조 1, 현장 공간 지시 1이다. 세부 SHA는 [machine report](machine/TinyLM_Stage4_Pilot_Reaudit_2026-09-02.json)에 기록했다.
