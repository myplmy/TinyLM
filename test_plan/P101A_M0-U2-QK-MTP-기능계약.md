# P101A — M0 기반 U2 E384·QK gain·MTP 기능 게이트

> 제안 계기: [승인된 A안](../proposal/20260923_TinyLM-M0-C0-E384-QK-MTP-지능향상-제안서-approved-on-going.md) 10절. 독립 계획으로 분리해 기존 P006/P030 본문을 소급 수정하지 않는다. MTP 효과의 정본 번호는 여전히 P006이며 본 계획은 **A 결합의 기능 계약**만 소유한다. 2026-09-24 정적 코드·CPU 수학 fixture PASS, 실제 모델 gate와 GPU·품질 NOT_RUN.

## 1. 왜

기존 `--emb-rank`는 E를 바꿀 수 있지만 M0 체크포인트의 함수 보존 이식기는 없었다. 현재는 순수 상태사전의 E-rank 확장·QK gain exact-key helper까지 구현했고, 실제 M0 checkpoint 로드·계속학습 경로는 아직 없다. 기존 QK RMSNorm에는 학습 gain이 없었다. MTP는 S+1 crop에서 미래 타깃·EOS 문서경계를 맞춰야 하며, head·trainer 결합은 아직 없다. 신규 C0 1.2B는 한국어/풀 gate HOLD이므로 이 실험에는 넣지 않는다.

## 2. 질문

| # | 질문 | 증거 |
|---|---|---|
| Q1 | E256→E384 선형 입력·출력 함수가 실수 산술에서 보존되고 새 U가 gradient를 받나 | max_abs·gradient |
| Q2 | QK gain off가 기존 모델이고 on의 초기 τ=1이 logits를 유지하나 | tiny model logits, missing key exact, gain gradient·WD0/LR0.1 |
| Q3 | horizon2/4 타깃이 EOS 뒤 문서로 새지 않나 | S+1 crop·타깃/마스크 fixture |

## 3. 예측

Q1은 실수 산술에서 정확히 같을 수 있다. BF16/quantized export는 shape에 따른 반올림으로 다를 수 있다. Q2는 초기 logits가 매우 가깝지만 kernel shape·dtype 변화는 비트 동일성을 보장하지 않는다. Q3의 범위를 넘어 assistant 메시지 경계나 실제 품질을 주장하지 않는다.

## 4. 단계 설계

### Stage0W — 함수·수학 계약, 사용자 실행용 SH

[CPU 수학 게이트](../scripts/diag_p101a_math_contract.py)는 E 확장·gradient·strict target key/shape·원본 및 전역 RNG 불변·QK gain 초기 τ=1과 EOS horizon2/4 target을 검사한다. [QK 작은 모델 게이트](../scripts/diag_p101a_qk_gain.py)는 새 exact-key helper로 strict load한 모델의 초기 함수·parameter group을 검사한다. 두 코드는 [실물 SH](../run_P101A_Stage0W_u2_mtp_function_gate.sh)로 한 로그에 기록한다. QK는 `attn_group=1`에서만 per-layer/head 구현을 허용한다.

### Stage1W — 실제 M0 계속학습 전 선결, 현재 미작성

M0 원본 checkpoint hash, 동일 tokenizer/cache, 어닐·optimizer 이력과 새 상태이식 helper를 실제 model path에서 검사한다. helper의 예상외/missing key 거부는 CPU fixture PASS지만 실제 checkpoint 함수 보존은 `NOT_RUN`이다. MTP aux head·assistant 경계·gradient/배포 제거와 trainer opt-in은 아직 미구현이다. 이 단계의 SH는 **작성하지 않는다**. Stage0W가 PASS해도 100M 학습이 열리지 않는다.

### Stage2W — 100M 이하 분리 학습, 별도 사용자 승인

B0/E-only/QK-only/MTP-only의 parent·draw·eval 경로를 맞추고 P006 후속으로 MTP 결과를 귀속한다. 600M 이상과 C0 신규1.2B는 현재 금지. 품질·상주·속도는 고정 질문 및 동일 배포 경로에서 판정한다.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| Stage0 math max_abs>1e-6, EOS 누출 또는 gain parameter/migration 불일치 | 기능 FAIL, Stage1 진행 금지 |
| Stage0 τ=1 logits max_abs≤1e-5와 gain gradient 비영 | 작은 기능 계약만 PASS, 실제 M0 효과 NOT_RUN |
| Stage1 model/parent/tokenizer hash 불일치 | 비교 불가, 학습 명령 금지 |
| 100M 짧은 loss 개선 | 축 방향만 기록, 한국어 지능·배포 채택 아님 |

## 6. 비용

| 단계 | 예상 | 자원 |
|---|---:|---|
| Stage0W | 약0.1h | CPU 작은 모델, 사용자 실행 |
| Stage1W | 구현·검증 별도 | GPU/모델 사용자 실행 |
| Stage2W | 100M 팔당 기존 M0 후속 길이로 재산정 | 별도 승인 |

## 7. 실행 파일

`run_P101A_Stage0W_u2_mtp_function_gate.sh` 하나만 현재 작성. log 번호092, 실패하면 첫 실패 종료코드 반환. 실제 학습 런처 0개. `P006`·기준표 조건이 정본이며 새 태그·풀 예산은 학습 단계에서 preflight한다.

## 8. 한계

E384의 checkpoint 실물 이식, MTP head·trainer·배포 제거, 실제 모델 품질, GPU 속도는 미실행/미구현이다. 새 QK gain은 기본 off로만 안전하다. 사용자 실행 Stage0W의 PASS를 A 권장안 구현 완료로 승격하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-24: `tinylm/train/p101a_contract.py`, QK gain config/Attention/optimizer opt-in과 CPU 수학 fixture를 구현. E/MTP fixture와 E256→E384 state-dict strict-key·local RNG·tau1 거부 fixture는 PASS. 작은 모델·실제 M0 checkpoint gate는 사용자 실행 전 `NOT_RUN`.
