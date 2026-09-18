# P095 — Scout + 1 MiB LTM의 기능적 학습가능성

> **승인 2026-09-18.** 권장안 A를 승인했다. 정본 제안서:
> [`20260916_Scout-1MiB-장기기억-학습가능성-검증-제안서-approved-on-going.md`](../proposal/20260916_Scout-1MiB-장기기억-학습가능성-검증-제안서-approved-on-going.md)
>
> **현재 상태:** `DESIGNED`. S0 causal-isolation·shape·물리 회계 계약부터 시작하며,
> 구현·모델 로딩·GPU·배치·기능·일반 LM 품질은 모두 `NOT_RUN`이다.

## 1. 왜 — 기능 성립과 동예산 최적화를 섞지 않는다

이 계획은 기존 TinyLM backbone을 줄이지 않고 작은 causal Scout와 논리적 payload 1 MiB의
explicit long-term memory(LTM)를 추가해, 새로운 episodic fact를 쓰고 지연 뒤 찾아 실제 출력에
사용하는 회로가 학습 가능한지 먼저 묻는다. 처음부터 KV 축소·MLP tying·layer 감소로 1 MiB를
상쇄하면 memory 실패와 기존 압축 손실이 교락된다.

따라서 “32/40 MiB에서 최적인가”보다 “memory가 실제로 기능하는가”가 선행한다. 기능이 성립한
뒤에만 weight/KV/LTM 동예산 배분을 별도 후속 질문으로 연다.

## 2. 질문

| # | 질문 | 답이 필요한 이유 |
|---|---|---|
| Q1 | main context shortcut과 oracle 미래정보 누출 없이 write→retrieve→use를 학습하는가 | 기능적 학습가능성의 최소 조건 |
| Q2 | REMOVE/SHUFFLE/NULL에서 성능이 무너져 출력이 memory에 인과 의존하는가 | 단순 parameter 증가 효과 배제 |
| Q3 | unseen entity·relation과 delay, 충돌·퇴거에서 회수 가능한가 | weight 암기와 단일 fact overfit 배제 |
| Q4 | oracle WRITE 뒤 source-disjoint learned WRITE와 hint 제거가 가능한가 | 실제 기록 정책의 학습성 |
| Q5 | KV 후보를 LTM으로 consolidation하고 working KV를 줄여도 되는가 | long-context 비용과 연결 |
| Q6 | 논리 1 MiB가 physical RSS·latency·metadata까지 포함해 값어치가 있는가 | 배포 주장과 기능 주장을 분리 |

## 3. ★사전 예측

- oracle WRITE/read는 작은 synthetic task에서 학습될 가능성이 높지만, learned WRITE와 conflict
  resolution에서 급격히 무너질 가능성이 있다.
- ordinary context에 fact가 남아 있으면 BASE도 풀 수 있으므로 S0 격리가 가장 먼저 실패를
  찾아낼 가능성이 높다.
- 3.5K 안팎 slot의 exact scan은 기능 검증에는 충분하지만 tap 수를 곱한 CPU latency가 1 MiB
  payload보다 큰 배포 비용이 될 수 있다.
- 기능이 성립해도 일반 LM full-val 개선은 보장되지 않는다. memory task 향상과 일반 LM
  non-inferiority를 별도 축으로 판정한다.

## 4. 최소 구조와 대조군

첫 계약의 설계값은 실행 tag가 아니라 shape/accounting ID다.

| 구성요소 | 초기 계약 |
|---|---|
| main path | 기존 backbone과 causal LM 경로 유지 |
| Scout | shared RMSNorm, `768→96`, 96-d shared causal cell, 64-d query |
| LTM token arena | raw token ID와 provenance offset/length |
| LTM semantic arena | 64-d key, 128-d value, utility/age/confidence/version/flags |
| 검색 | 약 3.5K slot exact scan, top-8→top-2~4 read |
| fusion | coda 전 low-rank gated residual; no-memory fallback은 main path |
| 용량 | **payload 논리 1 MiB**; metadata·alignment·Scout parameter·scratch·RSS는 별도 |

| 팔 | Scout | LTM | 목적 |
|---|---|---|---|
| `BASE` | 없음 | 없음 | backbone 대조 |
| `S` | 있음 | 없음 | Scout parameter 효과 |
| `M` | 있음 | 정상 | 정상 memory |
| `M-REMOVE` | 있음 | 정답 제거 | causal ablation |
| `M-SHUFFLE` | 있음 | key/value shuffle | 정보 없는 memory control |
| `M-NULL` | 있음 | 관련 memory 없음 | false retrieval/unknown |

## 5. 단계와 중단 게이트

| 단계 | 무엇 | 다음 단계 조건 | 비용 |
|---|---|---|---:|
| **S0 causal isolation** | shape·mask·reset·determinism·logical/physical byte·latency 계약, fact context 제거와 oracle 누출 fixture | BASE가 chance 부근, 미래/label 누출 0, fallback 동일 | GPU 0 |
| **S1 oracle memory** | oracle WRITE에서 READ/retrieval/fusion overfit과 unseen episode | train QA≥99%, recall@4≥99%; unseen에서 M이 controls보다 CI 하한 기준 우세 | ≤0.05 H300 |
| **S2 capacity/conflict** | 25/50/100/120% occupancy, duplicate, update, conflict, tombstone, eviction | exact duplicate<1%, capacity 증가에도 원인불명 collapse 없음 | ≤0.10 H300 |
| **S3 learned WRITE** | explicit hint→100/50/20/0% anneal, source-disjoint eval | WRITE F1≥95%, hint 0에서 oracle 성능의 ≥80% | ≤0.08 H300 |
| **S4 consolidation** | KV chunk candidate와 KEEP/CONSOLIDATE/DISCARD, working KV 20~25% 축소 | eviction-only보다 명확 우세, full-KV 대비 memory task 저하≤5pp | ≤0.18 H300 |
| **S5 일반 LM** | 30M BASE/S/M/SHUFFLE 뒤 100M 생존 2~3팔 | memory task만 인과 향상하고 일반 LM catastrophic regression 없음 | ⚙1.0~1.8 H300 누적 |
| **S6 규모·재현** | 기능·일반 LM 생존 후보만 300M와 최소 2 seed | 당시 ruler non-inferior와 memory 효과 재현 | 별도 GPU 예산 승인 |
| **S7 동예산 Pareto** | 그 뒤에만 KV/weight/depth와 1 MiB 교환 | 32/40 MiB physical 경로에서 품질·속도 Pareto | 별도 계획 |

S0가 실패하면 architecture implementation을 열지 않는다. S1에서 REMOVE/SHUFFLE/NULL이 정상
memory와 같으면 “memory를 사용하지 않았다”로 종료한다. S5 전까지 32/40 MiB 우승을 주장하지 않는다.

## 6. 판정·계측

- episode마다 nonce 관계를 새로 만들고 train/eval entity·template source를 분리한다.
- `MEM_FOUND/MEM_ABSENT/MEM_SIMILAR/MEM_CONFLICT`와
  `ANSWERABLE/AMBIGUOUS/UNKNOWN`을 같은 상태로 합치지 않는다.
- recall@1/4/8, slot ID, gate, answer CE/accuracy, no-match, occupancy, age, duplicate, encoder
  version, physical RSS와 p50/p95 latency를 함께 기록한다.
- 점 추정량만 보지 않고 chance 및 각 causal control 대비 CI 하한을 쓴다.
- 100M 이후 주장은 최소 2 seed 방향 일치가 필요하다.

## 7. 비용·우선순위와 실행 경계

최초 기능 경로의 조건부 비용은 ⚙1.0~1.8 H300, 구현은 ⚙8~16 engineer-h로 본다. S6와 S7은
이 상한에 포함하지 않으며 기존 72h hard cap에 자동 편성하지 않는다.

현재 우선순위는 **신규 아키텍처 C**다. P096의 벤치 계약, P093의 GPU 0 회계, P091의 흡수
계약처럼 현재 의사결정을 직접 닫는 싼 단계 뒤에 둔다. 다만 S0는 GPU 0이므로 구현 범위가
별도 승인되면 독립적으로 먼저 반증할 수 있다.

사용자 승인은 계획의 승인이다. Scout/LTM 코드, synthetic data generator, 모델 로딩, smoke,
GPU, 배치, KV 축소, 기본 프리셋 변경은 이번 범위가 아니다.

## 8. 한계와 위험

| 위험 | 영향 | 완화 |
|---|---|---|
| context shortcut | LTM 없이도 정답 | fact 제거/창 밖 delay와 BASE chance gate |
| oracle 미래정보 누출 | 가짜 학습가능성 | 현재 관측과 사전 write 위치만 허용 |
| logical 1 MiB 과장 | 실제 RSS·latency 예산 초과 | payload/metadata/scratch/parameter/RSS 분리 |
| activation staleness | 오래된 value가 현재 encoder와 불일치 | token provenance와 encoder version, refresh 대조 |
| 패널 암기 | unseen 기능 주장 무효 | entity/relation/template source-disjoint split |
| ANN 과설계 | 작은 slot에서 복잡도만 증가 | 첫 단계 exact scan 고정 |
| 일반 LM 회귀 | memory task만 좋아짐 | S5에서 별도 non-inferiority gate |

## 9. preflight와 이력

| 점검 | 결과 |
|---|---|
| 유사 실험 조회 | 같은 Scout+1 MiB dual-arena causal LTM 런 없음 |
| 중복·교락 | KV 압축·MLP tying·depth 교환은 S7 전 금지 |
| 계산 | H300 상대비만 사용; 실제 baseline wall을 S0 뒤 기록 |
| 태그·배치 | 미배정·미작성 |
| 보호 경계 | 데이터·모델·GPU·smoke 접근 없음 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

- 2026-09-18: 권장안 A 승인으로 P095를 신설했다. S0 이후 구현·기능·품질은 `NOT_RUN`이다.
