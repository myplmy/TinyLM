# Stage2~4 pilot 독립 의미감사 최종 보고서

> 최종 판정: **PASS**  
> 감사일: 2026-09-02 KST  
> 감사자는 Stage2~4 원고 작성과 교정에 참여하지 않았으며, 이번 감사에서 해당 corpus/source/JSON을 수정하지 않았다.

## 1. 감사 범위와 방법

Guide와 Design Spec의 Stage2~4 교육목표를 기준으로 최초 고정 층화 371건을 직접 판독했다.

- train 3개 파일: 각 파일의 1~5, 10·20·…·150, 73~77, 148~150
- validation: 같은 고정 층화와 `unseen_relation: true` 18건 전부의 합집합
- 희소 relation 보강: Stage2의 `classification` 3건 전부
- 확인 항목: 교육목표 정합, primary concept-text 정합, relation 의미, `other` 정당성, 한국어 문법·자연성, validation 의미 독립성, relation-set을 맞추기 위한 인공 문구 여부

| Stage | train 판독 | val 판독 | 희소 relation 추가 | 최초 직접 판독 합계 |
|---|---:|---:|---:|---:|
| Stage2 | 81 | 41 | 3 | 125 |
| Stage3 | 81 | 42 | 0 | 123 |
| Stage4 | 81 | 42 | 0 | 123 |
| **합계** | **243** | **125** | **3** | **371** |

교정 뒤에는 최초 지적 15건, 원 작성자가 추가 발견한 train-val 의미 누출 쌍 2건, 통합 문장 도입부 검사에서 추가 교정한 `S4-DSH-00067`, Stage2~4 validation true 54건 전부를 다시 읽었다. 또한 12개 canonical PSV와 대응 JSON의 1,800행을 독립 비교하여 concept, text, relations, validation의 `unseen_relation` 불일치가 0건임을 확인했다.

## 2. 최초 감사에서 발견한 문제와 교정 확인

### 2.1 Stage2

`S2-CSH-00130`은 오래된 로컬 캐시가 이전 명령을 다시 보낸 현상을 설명하면서 primary가 명령 억제라고 되어 방향이 반대였다. 교정본은 concept와 본문 literal을 `로컬 캐시의 이전 명령 재전송`으로 맞췄으며 `process, state, boundary`의 의미도 실제 문장에 남아 있다.

원 작성자는 재감사 상위쌍에서 `S2-CSH-00037`과 기존 `S2-CSV-00030`이 같은 전원 전환 사건을 공유하는 train-val 의미 누출을 추가 발견했다. 현재 validation `S2-CSV-00030`은 문화재 진공 포장에서 봉투 압력, 산소 지시약, 밀봉 상태를 연결하는 `진공 포장의 산소 농도 저하 경로`로 전면 교체됐다. 발전기 재기동을 다루는 train `S2-CSH-00037`과 객체, 사건, 판단 근거가 모두 분리됐다.

Stage2의 조건·원인 구조, 시간 선후, 다중 관계 경로 교육목표와 문화재 수장고 validation의 도메인 독립성은 유지됐다.

### 2.2 Stage3

`S3-GAV-00073`의 불안정한 한영 혼용 표현 `오염 plume 경계 추적`은 concept와 본문에서 모두 `오염 확산띠 경계 추적`으로 교정됐다. 여러 깊이에서 색과 탁도가 바뀌는 선을 따라가며 한 지점의 혼탁을 해역 전체로 확대하지 않는다는 문장이 `boundary, process`를 구체적으로 뒷받침한다.

목표·행동 연결, 계획 분해, 실행 감시·복구의 세 pilot 목표와 수중 다큐멘터리 validation의 독립성에는 추가 문제가 없었다.

### 2.3 Stage4

명확한 의미 문제 2건과 relation label을 문구에 끼워 넣은 true slice 12건을 합친 고유 13건을 직접 자연화한 결과를 재판독했다.

- `S4-DRV-00028`: 서쪽으로 성급히 확정하던 지시 대상을 `그 뒤의 공간적 지시 범위`로 바꾸고, 시선 방향을 확인할 때까지 봉분 너머와 서쪽 공간을 후보로 남겼다.
- `S4-DRV-00051`: 음식 흔적이라는 직접 단서로 나무 주걱을 식별하고, `그 도구가 마르지 않게 물에 담갔어요`로 피보존 대상을 명시했다.
- `S4-DRV-00058/00063/00068/00076/00088`: 화재층·복구층, 큰 항아리·작은 병, 주민 약도·발굴 실측도, 면사무소 회의록, 토지 소유자의 의견을 실제 참조 단서와 상태·대비·비교·분류·역할에 연결했다.
- `S4-DRV-00105/00113/00121/00129/00136/00143`: 통역자 손자, 옛 측량 기사, 마을 길잡이, 이장과 토지 소유자, 원로와 젊은 주민, 생활 유물과 의례 유물을 구체적 발화·행동·사용 맥락으로 식별했다.

교정본에서는 `비교 상태가 뜻하는`, `담당 역할이 지칭하는` 같은 통제 label 노출형 primary가 제거됐다. true 18건 전부를 다시 읽은 결과, relation은 문장 의미에 실제로 나타나고 참조 해소·대화 문맥이라는 Stage4 교육목표에서 벗어난 정의문도 남지 않았다.

통합 문장 도입부 검사에서 `S4-DSH-00066/00067`의 두 번째 문장 골격이 겹친다는 추가 지적도 재확인했다. 원 작성자는 `S4-DSH-00067`을 `이 면담 시간 변경 제안의 철회로 내담자의 이전 수락은 실행 가능한 약속으로 남지 않는다`로 직접 재서술했다. 수락은 약속 시각을 갱신하고 철회는 그 수락의 실행 가능성을 없앤다는 서로 다른 대화 상태 전이가 자연스럽게 드러나며, 수정 뒤 문장 단위 4어절 도입부 반복도 0건이다.

최종 `stage4_(3)dialogue_state_high_density_train_v01.json` SHA-256은 `df124f863e2e69eaf592206f34165af1f23c1fe334182ee1644bf1d31b0ac4f7`, 대응 canonical source SHA-256은 `6ac0fbe569dfd6532f03006aca8d1bd823b05b6559344cba5ecdfbc144935e84`다.

## 3. validation 분리규칙 독립 재검증

관계 조합은 순서가 아니라 정렬된 relation-set으로 비교했다.

| Stage | true | false | true 비율 | true set의 train 관측 | false set의 train 미관측 | val label의 train 미출현 |
|---|---:|---:|---:|---:|---:|---:|
| Stage2 | 18 | 132 | 12.0% | 0 | 0 | 0 |
| Stage3 | 18 | 132 | 12.0% | 0 | 0 | 0 |
| Stage4 | 18 | 132 | 12.0% | 0 | 0 | 0 |

각 Stage의 true는 train에 없던 정렬 relation-set만 사용하고, false는 train 관측 set만 사용한다. true와 false 모두 개별 relation label은 해당 Stage train에서 최소 1회 관측됐다. relations 길이 2~5, 레코드 내부 중복 0, 13개 통제어휘 밖 값 0도 독립 계산으로 확인했다.

## 4. 교정 후 기계 재감사 대조

원 작성자의 post-correction reaudit와 현행 파일을 대조했다.

| 항목 | Stage2 | Stage3 | Stage4 |
|---|---:|---:|---:|
| records / source rows | 600 / 600 | 600 / 600 | 600 / 600 |
| ID·concept·text·concept+relation-set exact duplicate | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 |
| 반복 5어절 / 반복 4어절 도입부 | 0 / 0 | 0 / 0 | 0 / 0 |
| train-val exact text / exact concept | 0 / 0 | 0 / 0 | 0 / 0 |
| Stage1 고밀도 교차 5어절 | 0 | 0 | 0 |
| 내부 TF-IDF cosine 최대 | 0.276059 | 0.228931 | 0.208237 |
| train-val TF-IDF cosine 최대 | 0.192605 | 0.107500 | 0.239433 |
| 자동 문법 패턴 hit | 0 | 0 | 0 |
| 보호 baseline 검사 / 불일치 | 371 / 0 | 371 / 0 | 371 / 0 |

모든 cosine 최대값은 0.72 기준보다 낮다. Stage2의 교정 전 의미 누출 상위쌍은 새 문화재 진공 포장 사례로 교체되어 현재 train-val 상위 유사도에서도 해소됐다.

재감사 보고서:

- `stage2_highdensity_dataset/audit_reports/TinyLM_Stage2_Pilot_Reaudit_2026-09-02.md`
- `stage3_highdensity_dataset/audit_reports/TinyLM_Stage3_Pilot_Reaudit_2026-09-02.md`
- `stage4_highdensity_dataset/audit_reports/TinyLM_Stage4_Pilot_Reaudit_2026-09-02.md`

## 5. 최종 판정

| Stage | 최종 판정 | 근거 |
|---|---|---|
| Stage2 | **PASS** | concept-text 방향 오류와 추가 train-val 의미 누출이 해소됐고 분리·구조·유사도 게이트를 유지했다. |
| Stage3 | **PASS** | 한영 혼용 표현을 자연화했고 교육목표·relation 의미·validation 독립성을 유지했다. |
| Stage4 | **PASS** | 의미 오류 2건과 true slice 인공 primary 및 문장 도입부 중복 1건을 직접 자연화했으며 true 18건 전수 판독과 분리규칙 재검증을 통과했다. |

이번 독립 재감사에서 Stage2~4 corpus/source/JSON 수정은 **0건**이다. 최종 보고서 확정을 위해 이전 WORKING 문서는 이 파일로 대체했다.
