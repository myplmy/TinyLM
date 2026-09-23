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

[CPU 수학 게이트](../scripts/diag_p101a_math_contract.py)는 E 확장·엄격 상태키/로컬 RNG·QK τ=1, EOS horizon2/4, 독립 aux projection+공유 어휘를 쓰는 FP32 3-head loss/모든 gradient·유효타깃 분모를 full-logit 기준과 대조한다. [작은 모델 게이트](../scripts/diag_p101a_qk_gain.py)는 사용자 실행으로 strict 이식·기본 off hidden 경로·MTP head 독립성/gradient·배포 payload에서 aux key 제거 후 주 logits 불변을 본다. 두 코드는 [실물 SH](../run_P101A_Stage0W_u2_mtp_function_gate.sh)로 한 로그에 기록한다. QK는 `attn_group=1`에서만 per-layer/head 구현을 허용한다. Codex는 실제 모델 gate를 실행하지 않는다.

### Stage1W — 실제 M0 계속학습 전 선결, 현재 미작성

M0 원본 checkpoint hash, 동일 tokenizer/cache, 어닐·optimizer 이력과 새 상태이식 helper를 실제 model path에서 검사한다. helper의 예상외/missing key 거부와 두 독립 MTP head의 주 U 복사·배포 payload 제거는 코드/CPU tensor 계약이 있다. 실제 tiny/M0 모델 함수 보존은 사용자 실행 전 `NOT_RUN`이다. 학습 trainer opt-in과 assistant 경계는 아직 미구현이며, 이 단계의 SH는 **작성하지 않는다**. Stage0W가 PASS해도 100M 학습이 자동으로 열리지 않는다.

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

- 2026-09-24 막힘 재감사: Stage0W 모델 로그는 함수·G2 승인 증거이지 기본 off 코딩 금지가 아니다. `mtp_loss_components`/`mtp_weighted_mean`의 S+1 입력·독립 horizon2/4·공유 어휘 gradient·update valid-token 분모가 full-logit CPU fixture와 일치했다. 모델에 독립 aux head·정규화 hidden 반환·배포 payload 제거 코드를 추가하고 작은 사용자 모델 gate를 확장했다. **Codex는 그 모델 gate를 실행하지 않았다.** 실제 M0 이식·전체 trainer·GPU·품질은 NOT_RUN/미구현으로 분리하고 GPT 구현을 계속한다.
