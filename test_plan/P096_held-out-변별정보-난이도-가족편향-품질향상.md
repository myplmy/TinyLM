# P096 — held-out 변별정보·실측 난이도·가족편향 품질향상

> **승인 2026-09-18.** 권장안 B를 승인했다. 정본 제안서:
> [`20260914_held-out-변별정보-난이도-가족편향-품질향상-제안서-approved-on-going.md`](../proposal/20260914_held-out-변별정보-난이도-가족편향-품질향상-제안서-approved-on-going.md)
>
> **현재 상태:** Q0 동일패널 원인분리는 기존 [결과 074 §27](../test_result/074_20260904_P085-정답CE는-9쌍-전부-맞고-정확도는-끝까지-못-가른다.md)로
> 완료됐다. Q1a 최소 계약에 이어 Q1b의 8 relation·32 subtype·320 synthetic fixture,
> difficulty-knob 정합, family/template 5% cap과 proof-path negative fixture를 사용자 보존
> 로그에서 exit 0으로 확인했다([결과 085](../test_result/085_20260919_P096-Q1b-taxonomy-계약은-통과했고-실문항은-남았다.md)).
> Q2a bounded candidate/provenance contract도 사용자 로그에서 PASS했다([085 §4](../test_result/085_20260919_P096-Q1b-taxonomy-계약은-통과했고-실문항은-남았다.md#4-q2a-bounded-canary-candidate-계약2026-09-19)). 팀 의미검토,
> 실제 보호 data/GPU는 `NOT_RUN`이며 다른 세션 소유 원본을 수정하지 않는다.

## 1. 왜 — 정적 문체 proxy가 아니라 실제 변별정보를 최적화한다

v3.0은 같은 seed2 여섯 모델 패널에서도 v2.9보다 D9가 22.9→19.0%, 정보 0이
54.1→65.2%, 총 정보량이 1,645.5→1,271.7 bit로 함께 악화했다. 따라서 전면 문장 재작성이나
표면 균형만으로는 품질이 보장되지 않는다. 동시에 v2.9도 합격판이 아니므로 단순 복귀가 답은 아니다.

P096은 정답을 결정하는 형식 의미 구조를 먼저 고정하고, 기존 유효 ID를 보존한 최대 두 후보를
설계 패널에서 계측해 정보량·모델쌍 불일치·실측 난이도·관계 하위가족을 함께 만족하는 항목만
bounded canary로 선별한다.

## 2. 질문

| # | 질문 | 답이 필요한 이유 |
|---|---|---|
| Q1 | `gold_proof`와 distractor 오류형으로 정답 유일성·오답 거짓을 기계 검증할 수 있는가 | entropy가 애매한 문항을 보상하는 것을 막는다 |
| Q2 | 정보 0을 줄이면서 총 bit와 15개 모델쌍 최소 discordance를 함께 늘릴 수 있는가 | 일부 모델쌍 편식을 막는다 |
| Q3 | empirical easy/mid/hard와 생성 knob를 분리해 봉인 final에서도 단조성을 재현하는가 | 같은 패널 순환논리를 막는다 |
| Q4 | relation×subtype×family에서 기존 좋은 문항을 보존하며 바닥 가족을 개선하는가 | 상위 relation 균형의 착시를 없앤다 |
| Q5 | canary 2회·full 1회·final 1회 안에 성공하거나 명시적으로 중단할 수 있는가 | 무한 재작성 방지 |

## 3. ★사전 예측

- 의미 schema와 solver는 정적 계약으로 만들 수 있지만, 실제 패널 변별정보까지 좋아지는지는
  불확실하다.
- 정보 0 비율은 낮출 수 있어도 total bit만 최대화하면 특정 모델쌍·가족에 편중될 수 있다.
- empirical difficulty를 설계 패널에서 만들면 그 패널에서는 단조성이 생기므로, 새 봉인 final에서
  무너질 가능성을 별도 실패로 보존해야 한다.
- v3.0의 전면 교체보다 기존 유효 ID 보존형 canary가 회귀 폭과 사람 감사 비용을 줄일 가능성이 높다.

## 4. 의미·선별 계약

Q1에서 다음 필드와 소유권을 먼저 고정한다.

| 필드 | 역할 |
|---|---|
| `relation` / `relation_subtype` | 상위 관계와 의미 하위형 |
| `family_id` / `template_id` | 논리 골격 재표집 단위와 표면 문장 틀 |
| `gold_proof` | 전제에서 유일한 정답까지의 기계 검증 경로 |
| `distractor_error_type` | 역관계·필요충분 혼동·시간 역전·인과/상관 등 |
| `difficulty_target` | 생성 전 hop·명시성·경쟁 단서·오답 근접도 목표 |
| `difficulty_empirical` | 설계 패널 정답 모델 수로 얻은 사후 라벨 |

선별은 다음 사전순서를 바꾸지 않는다.

1. 의미 유효성·오염·중복·정답 균형 hard constraint
2. 정보 0 후보 제거
3. relation×subtype×difficulty quota
4. 총 이진 entropy `H(p)` 최대화
5. 아직 부족한 15개 모델쌍 최소 discordance 우선
6. 동률이면 family/template 중복 최소화

## 5. 단계와 중단 게이트

| 단계 | 무엇 | 다음 단계 조건 | 비용 |
|---|---|---|---:|
| **Q0 ✅** | P085 Stage10c로 v2.9/v3.0 같은 seed2 패널 전이 분해 | ✅ `CORE_REGRESSION`; paired JSON·skip 0 | 완료, ⚙0.9 GPU-h 역사값 |
| **Q1a ✅** | 최소 schema·direct/transitive solver·negative synthetic fixture | 정답 유일성·오답 미증명·필드/ID 오류 검출 | `STATIC_ONLY`, GPU 0 |
| **Q1b ✅ 보존 로그** | 전체 relation/family taxonomy·difficulty knob 생성/검증 계약 | 8 relation·32 subtype·320 fixture 기계검증 exit 0; 팀 의미검토는 `NOT_RUN`([085](../test_result/085_20260919_P096-Q1b-taxonomy-계약은-통과했고-실문항은-남았다.md)) | CPU/GPU 0 |
| **Q2a ✅ 완료** | 보호 데이터 독립 synthetic fixture에서 450 slot·slot당 최대 2후보·provenance·preservation 계약 | baseline/candidate 각 320, cap·source/candidate ID·semantic contract PASS | [085 §4](../test_result/085_20260919_P096-Q1b-taxonomy-계약은-통과했고-실문항은-남았다.md#4-q2a-bounded-canary-candidate-계약2026-09-19) |
| **Q2b ⏸** | 기존 유효 ID 보존, 실제 10% canary 450자리×최대 2후보 생성 | Q2a PASS 뒤 데이터팀 소유 입력·사람 의미검토 | 데이터팀 1회 |
| **Q3** | 설계 패널 응답행렬과 제약 기반 450개 선별 | 정보 0↓, bit↑, 최소 쌍 coverage↑, 관계 비퇴행 | ⚙0.3 GPU-h/회, 최대 2회 |
| **Q4** | 사람 의미감사와 canary paired 판정 | 의미 오류 0, 사전등록 벡터 통과 | 사람 표본 1회 |
| **Q5** | 통과 규칙만 full에 1회 적용 | 정적·설계패널 paired 모두 통과 | 팀 1회 + ⚙1.2 GPU-h 상한 |
| **Q6** | 새 독립 6모델 봉인 final 1회 | D9·정보0·bit·단조성·가족 비퇴행 동시 통과 | ⚙0.9 GPU-h |
| **Q7** | 실패 보존·HOLD | 새 가설·패널·비용 승인 전 재작성 금지 | 0 |

Q3가 두 번 실패하면 문구를 더 고치지 않고 가설을 닫는다. Q6 결과를 다음 판 설계에 사용한
순간 그 패널은 설계군으로 강등하며, 새 봉인 패널 없이는 `FINAL_NOT_RUN`이다.

## 6. 판정·비용

- 설계 패널에서 정보 0은 0을 목표로 하되, 봉인 final은 paired baseline 대비 비증가와 절대
  비율을 함께 보고한다.
- easy/mid/hard는 여섯 모델 기준 4/6·3/6·2/6 정답 대역으로 설계하되 final에서 재검증한다.
- relation마다 최소 4 subtype, family/template 단일 점유율 5% 이하를 목표 계약으로 두고
  family cluster bootstrap·leave-one-family-out 방향을 함께 본다.
- 총 GPU 상한은 기존 Q0를 포함해 ⚙3.6h이며, 새 실행분을 기존 72h hard cap에 자동 편성하지 않는다.

## 7. 우선순위와 실행 경계

현재 우선순위는 **A1(과학적 판정 인프라)**이다. 6차 baseline 후보와 새 architecture가 좋아도
held-out 판본이 모델 서열을 안정적으로 가르지 못하면 “지능 향상”을 판정할 수 없다. Q1b의
기계 계약은 구현했으며, 실제 canary 전에 팀이 taxonomy 의미와 family 독립성을 검토해야 한다.

사용자는 Q1a synthetic 기능 gate 구현과 WSL 계약 진입점까지 승인했다. `datasets/TinyDataset/**`
열거·읽기·수정, 후보 생성, Q2 이후 도구, 사람 감사, GPU census와 새 판본 승격은 별도 범위·
데이터팀 소유권·사용자 승인이 필요하다. 현행 v2.9나 v3.0을 자동으로 교체하지 않는다.

후속 승인으로 `run_P096_Q2_canary_candidate_contract.sh`를 작성했다. Q2a는 synthetic Q1b
items로 hard cap·provenance·ID preservation·semantic solver 계약만 검증하며 실제 문항을 읽지 않는다.

## 8. 한계와 위험

| 위험 | 영향 | 완화 |
|---|---|---|
| 설계 패널 과적합 | final 붕괴 | 설계/봉인 패널 분리와 1회 final |
| entropy가 애매함 보상 | 변별정보처럼 보이는 오류 | `gold_proof`와 사람 감사 선행 |
| 모델쌍 편식 | 일부 쌍만 잘 가름 | 15개 쌍 최소 coverage 함께 최적화 |
| family 이름만 증가 | 유효 표본 착시 | proof·오답형·template fingerprint 감사 |
| 좋은 문항 손실 | 다른 관계 회귀 | 기존 유효 ID 보존, 실패 자리만 교체 |
| GPU·재작성 팽창 | 끝없는 튜닝 | 후보·canary·full·final hard stop |
| 새 final 미확보 | 승격 근거 없음 | `CALIBRATED / FINAL_NOT_RUN`으로 보존 |

## 9. preflight와 이력

| 점검 | 결과 |
|---|---|
| 유사 실험 조회 | P085 Q0 근거는 재사용; 같은 Pareto 선별 실험은 없음 |
| 중복 | 품질저하 방지 gate는 기존 승인안, P096은 실제 품질향상 방법만 소유 |
| 비용 | Q0 완료값과 Q1~Q6 신규 비용을 분리; 반복 상한 고정 |
| 태그·진입점 | `run_P096_Q1b_taxonomy_difficulty_contract-done.sh`가 Q1a 회귀와 Q1b를 보존 로그로 기록했다([085](../test_result/085_20260919_P096-Q1b-taxonomy-계약은-통과했고-실문항은-남았다.md)) |
| 보호 경계 | 이번 계획 작성에서 보호 데이터 접근 0 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

- 2026-09-18: 권장안 B 승인으로 P096을 신설했다. Q0은 기존 결과로 완료, Q1 이후는
  `NOT_RUN`이며 데이터·GPU 권한은 열지 않았다.
- 2026-09-18: Q1a 합성 schema/solver의 정상·모호·오답·필드누락·중복 ID CPU fixture PASS.
  전체 taxonomy와 실제 문항 품질은 `NOT_RUN`이다.
- 2026-09-18: WSL queue 진입점에서도 `[PASS] P096 Q1`을 관찰했지만 launcher 로그 결함으로
  `test_result/` 원본이 남지 않았다. underlying Q1a 판정은 변하지 않으며, 교정 후 재실행 전에는
  “보존 로그를 갖춘 E2E”로 승격하지 않는다.
- 2026-09-19: Q1b taxonomy·difficulty 계약을 구현했다. 보호 데이터 없이 8 relation,
  relation당 4 subtype, family당 복수 template, 단일 family/template 5% cap, easy/mid/hard와
  proof path negative fixture를 합성 320건으로 확인했다. 직접 CPU fixture는 PASS했지만 새 SH의
  사용자 실행·팀 의미검토·실제 문항은 `NOT_RUN`이다.
- 2026-09-19: Q1b SH 보존 로그를 회수해 exit 0을 확인했다([결과 085](../test_result/085_20260919_P096-Q1b-taxonomy-계약은-통과했고-실문항은-남았다.md)).
  팀 의미검토·실문항·보호 데이터·GPU panel은 계속 `NOT_RUN`이다.
- 2026-09-19: Q2a bounded-canary contract를 구현했다. baseline slot≤450, source slot당 후보≤2,
  provenance/source ID/candidate ID, preserved item semantic identity와 generated item proof solver를
  검사한다. 실제 보호 문항·텍스트 생성·팀 의미감사·panel은 `NOT_RUN`이다.
- 2026-09-19: 사용자 Q2a 로그가 synthetic baseline/candidate 각 320과 cap·provenance·ID
  보존 계약을 통과했다. 실제 보호 문항과 팀 의미검토 전에는 Q2b를 열지 않는다.
