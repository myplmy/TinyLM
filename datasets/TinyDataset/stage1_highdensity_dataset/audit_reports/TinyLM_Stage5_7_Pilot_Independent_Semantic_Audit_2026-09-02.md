# Stage5~7 pilot 독립 교차 의미감사 확정 보고서

> 감사일: 2026-09-02 (KST)  
> 최종 판정: **Stage5 PASS / Stage6 PASS / Stage7 PASS**  
> 독립성: 감사자는 Stage5~7 corpus의 source·JSON을 작성하거나 수정하지 않았다. 교정은 원 작성자가 canonical PSV를 직접 편집해 수행했고, 감사자는 교정 전후 판독과 기계 보고서 대조만 수행했다.

## 1. 감사 범위

각 Stage의 최종 4파일에서 다음 층화 표본을 읽었다.

- 파일별 rows 1~5, 10·20·…·150, 73~77, 148~150
- validation `unseen_relation: true` 18건 전부
- 사용 relation label별 최소 1건
- 최초 지적 ID, 원 작성자가 보고한 모든 교정 ID, 기계 유사도 상위쌍
- Stage7 A03는 150건 문장수·문두 분포와 5문장 레코드 전부를 별도 확인

최초 직접 판독은 Stage5 120건, Stage6 120건, Stage7 123건으로 총 363건이다. 이후 최초 지적, 잔여 표면 교정 32건, 추가 도입부·띄어쓰기 4건을 최신 JSON에서 다시 읽었다. 검토 축은 교육목표, primary concept/text, relation 의미, `other`, 한국어 조사·호응·띄어쓰기, 보일러플레이트, train/validation 독립성이다.

## 2. Stage5 교정 및 재검증

Stage5는 관찰 표본에서 제한적 규칙을 도출하고, 진짜 반례와 범위 밖 사례를 분리하며, 규칙 구조를 다른 표현에 전이하는 교육목표를 유지한다.

최초 감사에서 발견한 validation true slice의 `other` 의존, 인공 합성 primary, 구조 전이 파일의 불필요한 `other`를 원 작성자가 직접 교정했다.

- true 18건을 파일 전역에 분산하고, 관찰 부재·속성 결측·경계·잠정 갱신을 실제 `boundary/attribute/classification/comparison` 의미로 다시 썼다.
- `S5-STH-00005/00077/00149`의 불필요한 `other`를 제거했다.
- `S5-INH-00149`, `S5-CGH-00040/00060/00080`, `S5-INV-00030/00050/00075/00077/00100/00120`의 무공백 결합과 `-례`형 이름을 자연 명사구로 고쳤다.
- 최종 표본에서 외삽 제한, 선택·생존 편향, 진짜 반례와 범위 밖 사례의 경계가 일관되며 primary와 text가 반대 결론을 내는 행은 없다.

판정: **PASS**.

## 3. Stage6 교정 및 재검증

Stage6는 장문맥에서 최신 문서·위치·역할을 추적하고, 강제 제약을 선호보다 우선하며, 미측정값을 0으로 채우지 않는 교육목표를 유지한다.

- `S6-LCH-00076`에 제방 쪽 우회 표지라는 선행 근거를 추가해 최신 경로 결론을 뒷받침했다.
- validation true 18건을 파일 전역에 분산했다.
- false slice의 역할 인계 반복 골격을 판본 충돌, 동일 코드 충돌, 부분 상태, 출처 위계, 기록 공백으로 다양화했다.
- `S6-LCV-00064`는 오전 회의 수정과 후속 기상 보고를 거쳐 제12판이 최신이 되는 독립 3문장 흐름으로 바꿔 반복 도입부를 없앴다.
- `S6-CSH-00070`, `S6-UMH-00130`, `S6-LCV-00001/00018/00020/00050/00073/00090/00120/00130/00150`의 합성어·역할명·조사 호응을 자연화했다.
- 최종 표본에서 최신 상태와 폐기 상태, 검산자와 승인자, 미측정과 관측값의 경계가 relation과 일치한다.

판정: **PASS**.

## 4. Stage7 교정 및 재검증

Stage7은 명령의 목표·금지·범위·완료 조건을 추출하고, 다턴 수정의 최신 상태를 유지하며, 실제 task의 준비·실행·검증·보고를 구분한다.

### 4.1 다턴 구조

A03의 최종 문장수 분포는 3문장 93건, 4문장 53건, 5문장 4건이다. 첫 문장 첫 토큰 `첫`은 24건에서 5건으로 줄었다. 최초에 의미가 가까웠던 `S7-MDH-00010/00040`, `00020/00073`, `00045/00075`는 서로 다른 승인·취소·접근권 충돌로 재작성됐다.

`S7-MDH-00034`는 `다음 턴`이라는 메타 슬롯 표현을 없애고, 교대 직전 기록에서 야간 담당자에게 변경 로그가 승계되는 자연스러운 시간 흐름으로 고쳤다. 최종 표본의 3~5문장은 문장 수 패딩이 아니라 초기 상태, 수정·새 정보, 현재 적용 상태, 다음 행동을 각각 담당한다.

### 4.2 validation 독립성과 완료 조건

- `S7-IIV-00042`는 train의 세 파일 납품 조건과 대응되던 사건을 폐기하고 봉인 유물 점검 제외 과제로 교체했다.
- `S7-IIV-00048/00055/00110/00116/00130`은 누락·상충 지시·비해당·승인 보류·분쟁 처리라는 서로 다른 완료 판단 구조로 다양화했다.
- validation true 18건은 전역에 분산됐고, true는 미관측 relation-set, false는 train 관측 set이라는 규칙을 유지한다.

### 4.3 관계·한국어

역할 주체가 없던 `role`, 상태가 중심인데 빠졌던 `state`, 과정이 중심인데 쓰인 `classification`을 의미에 맞게 교정했다. `other`는 미해결 질문·입력 대기·결정 미지정·미실행·첨부 누락처럼 다른 12개 관계로 직접 표현하기 어려운 의미에 남겼다.

잔여 표면 11건 `S7-IIH-00070/00100/00149/00150`, `S7-PTH-00120`, `S7-IIV-00003/00041/00073/00100/00120/00148`과 추가 `S7-IIV-00011/00134`를 재판독했다. `자료 소유자`, `완료 조건`, `사진 번호·상자 번호`, `비상 대응`, `보존 담당자` 등이 자연스럽게 교정됐고 relation 의미도 유지됐다.

판정: **PASS**.

## 5. 최종 기계 감사 수치

| 항목 | Stage5 | Stage6 | Stage7 |
|---|---:|---:|---:|
| records (train / val) | 600 (450 / 150) | 600 (450 / 150) | 600 (450 / 150) |
| validation true / false | 18 / 132 | 18 / 132 | 18 / 132 |
| true set가 train에 관측됨 | 0 | 0 | 0 |
| false set가 train에 없음 | 0 | 0 | 0 |
| validation 개별 label train 누락 | 0 | 0 | 0 |
| exact ID / primary / text duplicate | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| train/validation primary+relation-set 누출 | 0 | 0 | 0 |
| 내부 5어절 반복 | 0 | 0 | 0 |
| 문장 4어절 도입부 반복 | 0 | 0 | 0 |
| Stage1 교차 5어절 | 0 | 0 | 0 |
| 실제 조사·문법 오류 | 0 | 0 | 0 |
| 보호 기준 일치 / mismatch | 369 / 0 | 369 / 0 | 369 / 0 |
| 내부 cosine 최대 | 0.301044 | 0.355563 | 0.303907 |
| train/validation cosine 최대 | 0.226005 | 0.136250 | 0.134552 |

모든 cosine 값은 0.72 gate 미만이다. machine report 원본은 각 Stage의 `audit_reports/machine/TinyLM_Stage*_Pilot_Corpus_Audit_2026-09-01.json`이다.

## 6. Relations 분포

| relation | Stage5 | Stage6 | Stage7 |
|---|---:|---:|---:|
| is_a | 0 | 0 | 0 |
| subclass_of | 0 | 0 | 0 |
| part_of | 0 | 0 | 0 |
| classification | 369 | 160 | 149 |
| boundary | 512 | 463 | 258 |
| contrast | 75 | 0 | 0 |
| comparison | 166 | 146 | 0 |
| function | 103 | 0 | 249 |
| role | 0 | 125 | 252 |
| process | 131 | 0 | 212 |
| state | 102 | 506 | 245 |
| attribute | 248 | 175 | 0 |
| other | 104 | 105 | 112 |

사용하지 않은 relation을 억지로 삽입하지 않았으며, validation에서 실제 사용하는 label은 각 Stage train에 의미 있는 사례가 있다.

`other` 상위 5개 유형은 다음과 같다.

| Stage | 유형 5개 |
|---|---|
| Stage5 | 관찰 기간 제한 2, 출처 불명 2, 구간 검열 2, 추론 구조 2, 미관측 변수 1 |
| Stage6 | 일정 불확실성 3, 관측 결측 3, 시간 정보 결측 3, 일정 미확정 2, 수요 결측 2 |
| Stage7 | 미해결 질문 2, 맥락과 지시 구분 1, 결정 미지정 1, 예시와 결과 구분 1, 요구 미정 1 |

## 7. 최종 파일 무결성

| Stage | 파일 | JSON SHA-256 | canonical source SHA-256 |
|---|---|---|---|
| 5 | `stage5_(1)induction_high_density_train_v01.json` | `b2225c1bdfdb6c0a7f4eb78f3d86b82dc74aabaab8296187cfe90d58b3ed48fc` | `665f473d9b6eb800ce1dee82301c6385f70885dca1f95651ee15403b06be4765` |
| 5 | `stage5_(1)induction_high_density_val_v01.json` | `330f73a7b74723c02314ca338826637be9834fa46183772d79b2f7988c31d0b3` | `3001e40669e21b96be06d324b83102f9d6a82b9c37d77ecf1c914374ec2f18f6` |
| 5 | `stage5_(3)counterexample_generalization_high_density_train_v01.json` | `7625529f41f252517af94855b7196ba5d6534b0264f83f913146916fa1c7e66f` | `0c720aff327613f95f14715250c2a4cd54f46a351115aff2ca3895ed838840a6` |
| 5 | `stage5_(6)structural_transfer_high_density_train_v01.json` | `e1bdb12802018c84181febe13100de088360033f21e6992a3c31ba1e7f1da853` | `8717c2796d9213ab37bfbe3e3ba2c67c80e1b3166adedd1d3117a7bff3af3e0f` |
| 6 | `stage6_(1)long_context_high_density_train_v01.json` | `72a7b0a3e79d0044166e48700ef5ebc1463ae2e996a7d5062757d2560b43e68b` | `5b35b096702658f496c3fb3cca57d31d787a67b288c189a422ba6fc87777a2b8` |
| 6 | `stage6_(1)long_context_high_density_val_v01.json` | `54ef44059631419b401de6b2103df15b872b927ca09206dab97990b2241d5336` | `5838bdcc96639f23831d2d606009ad4e157ff089b2a9ec0a57c820505b6467d3` |
| 6 | `stage6_(3)constraint_satisfaction_high_density_train_v01.json` | `2f20a95c6bd4c984cddbc06ea0da5801d34947330018bde6b6b7ed168075c7af` | `d6ed67e0ee5aabb6f649b1532f0f34bf988ade293e253b220dfc555ecc5382ca` |
| 6 | `stage6_(6)uncertainty_management_high_density_train_v01.json` | `2aa6b3ed6efd33f91bd091a7c1b6f892e5344d5c7c34aa53df8f62b0f6bb7b2f` | `e0be32e22085302c5a8cc631682d3f68f646a2a1a467d936006e7354b9b565b8` |
| 7 | `stage7_(1)instruction_intent_high_density_train_v01.json` | `3106665d143c7ca3400885dd4761ca478dafbfc82f30731ee59be6b1cda05699` | `ea42dfe93d4ca93a7ea73e2e25f98bdf11532e0124b88a7e3b2e8b2e022852c1` |
| 7 | `stage7_(1)instruction_intent_high_density_val_v01.json` | `09a746039d0f0e14ba7059fbf80e6ef167dd7264d25cb6a906460db11d848190` | `56c0bcff3301bce325dea26fa2023f9f860663414134e4789136308f1fe90dcc` |
| 7 | `stage7_(3)multiturn_dialogue_high_density_train_v01.json` | `35e9eddcbe736fcb1e7f043c2614361bf50317bac88bc849b9d9c10de443a7a2` | `3ed8d24cb0fbed2d3b727f7c8b33f1aeff85efc5c172b3c8ff5393da33564e74` |
| 7 | `stage7_(6)practical_task_high_density_train_v01.json` | `c8001c60ee64c688e7639627b8dcacd18e8be6fd13ec3ce62274724c0b9b8918` | `eefa0388104ac987633e545d2146fc60f866404e213e79b7a9fc8b73b9a2facc` |

## 8. 결론

Stage5~7의 12개 pilot 파일은 교정본 기준으로 교육목표·concept/text·relations·한국어·validation 분리·중복/유사도·보호 무결성 gate를 모두 통과했다. 미해결 지적은 **0건**이며, 독립 감사 과정에서 corpus/source/JSON을 수정한 건수도 **0건**이다.
