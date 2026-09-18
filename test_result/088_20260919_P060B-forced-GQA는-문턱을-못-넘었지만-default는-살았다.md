# 결과 088 — P060B forced GQA는 문턱을 못 넘었지만 default는 살았다

- **계획**: [P060B](../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md)
- **로그**: `088_log_20260919_P060B_Stage0aW_wsl_sdpa_gqa_backend.txt`
- **실행 파일**: `run_P060B_Stage0aW_wsl_sdpa_gqa_backend-done.sh`
- **환경**: WSL2 Ubuntu, RTX 4070 Ti SUPER `sm_89`, torch `2.10.0+cu130`, CUDA 13.0,
  cuDNN 91501, Triton 3.6.0, 외부 `flash-attn` 미설치
- **종료**: exit `8` · 사전등록 `GATE_NEGATIVE`; 실행 장애 아님

## 1. 측정 결과

### B8/T1024 — 주 게이트

| 경로 | median ms | off 대비 | working MiB | 절감 | max abs / RMS | 판정 |
|---|---:|---:|---:|---:|---:|---|
| off default(K/V repeat) | 0.2562 | 1.000× | 48.376 | — | 0.015625 / 0.000254 | 기준 |
| ★on default(`enable_gqa`) | **0.2569** | **1.003×** | **30.376** | **37.209%** | 동일 | 실용 후보 |
| forced CUDNN | 0.2763 | 1.079× | 30.001 | 37.984% | 0.015625 / 0.000253 | +5% 속도문턱 미달 |
| forced FLASH | 0.2710 | 1.058× | 30.376 | 37.209% | 동일 | +5% 문턱을 0.8%p 초과 |
| forced EFFICIENT | — | — | — | — | — | kernel unavailable |

### B1/T128 — 작은 형상 기술

| 경로 | median ms | off 대비 | working MiB | 절감 |
|---|---:|---:|---:|---:|
| off default | 0.0292 | 1.000× | 0.757 | — |
| ★on default | **0.0292** | **1.000×** | **0.476** | **37.161%** |
| forced CUDNN | 0.0356 | 1.217× | 0.470 | 37.935% |
| forced FLASH | 0.0336 | 1.149× | 0.476 | 37.161% |
| forced EFFICIENT | — | — | — | — |

## 2. ★핵심 발견

1. **사전등록 forced-backend 가설은 음성이다.** 주 형상에서 CUDNN은 +7.9%, FLASH는
   +5.8%로 허용 대가 +5%를 넘었다.
2. **WSL default dispatcher는 Windows 역사 결과와 달랐다.** `enable_gqa=True` default는
   B8/T1024에서 +0.3%, B1/T128에서 같은 속도이면서 working memory를 약 37% 줄였다.
   forced kernel 이름을 확정하지는 못해도 실제 제품 질문에는 유효한 후보이다.
3. 모든 실행 경로의 출력은 math/manual-repeat reference와 bf16 허용오차를 통과했다.
4. 이 isolated forward는 backward, 전체 Attention/TinyLM, 학습 ms/step, peak reserved,
   실제 생성 속도와 품질을 증명하지 않는다.

## 3. 판정

- **forced CUDNN/FLASH/EFFICIENT Stage0aW:** `GATE_NEGATIVE`.
- **default `enable_gqa` 실용 경로:** 후속 통합 gate 개방 후보. 기존 Windows의 “default가
  MATH로 떨어져 33.5배 느리다”를 지우지 않고 WSL 독립 환경에서만 정정한다.
- **외부 `flash-attn`:** 설치·실행하지 않았으며 `NOT_RUN`.
- **학습·배포 품질:** `NOT_RUN`.

<!-- TINYLM_CONDITION_SIGNATURE_V1 id=P060B-stage0aW-wsl-sdpa-gqa -->
| field | arm_a | arm_b | evidence |
| --- | --- | --- | --- |
| pool_id | N/A diagnostic | N/A diagnostic | 학습 없음 |
| actual_pool_tokens | N/A diagnostic | N/A diagnostic | 데이터 없음 |
| pool_override | N/A diagnostic | N/A diagnostic | 데이터 없음 |
| steps | N/A diagnostic | N/A diagnostic | isolated forward |
| micro_bs | B=8 and B=1 | B=8 and B=1 | 두 형상 |
| accum | N/A diagnostic | N/A diagnostic | 학습 없음 |
| seq | 1024 and 128 | 1024 and 128 | 로그 |
| actual_draw_tokens | N/A diagnostic | N/A diagnostic | 학습 없음 |
| sampler_with_replacement | N/A diagnostic | N/A diagnostic | 학습 없음 |
| expected_unique_tokens | N/A diagnostic | N/A diagnostic | 학습 없음 |
| sequential_epoch_claim | false | false | 학습 없음 |
| scheduler | N/A diagnostic | N/A diagnostic | 학습 없음 |
| warmup | 5 calls | 5 calls | 로그 명령 |
| anneal_start | N/A diagnostic | N/A diagnostic | 학습 없음 |
| decay_fraction | N/A diagnostic | N/A diagnostic | 학습 없음 |
| absolute_schedule_horizon | 20 timed calls | 20 timed calls | 로그 명령 |
| train_language_expected | N/A diagnostic | N/A diagnostic | 데이터 없음 |
| train_language_observed | N/A diagnostic | N/A diagnostic | 데이터 없음 |
| eval_dataset | synthetic bf16 attention | synthetic bf16 attention | 동일 q/k/v |
| eval_language | N/A diagnostic | N/A diagnostic | 자연어 평가 없음 |
| tokenizer | N/A diagnostic | N/A diagnostic | 토큰화 없음 |
| grad_ckpt | false | false | 모델 학습 없음 |
| representation | manual repeated K/V, enable_gqa false | compact K/V, enable_gqa true default | 독립변수 |
| hardware | WSL2 sm89 torch2.10.0+cu130 | WSL2 sm89 torch2.10.0+cu130 | 로그 |
| comparator_tag | off_default | on_default | 같은 세션 |
| matched_axes | pool_id,actual_pool_tokens,pool_override,steps,micro_bs,accum,seq,actual_draw_tokens,sampler_with_replacement,expected_unique_tokens,sequential_epoch_claim,scheduler,warmup,anneal_start,decay_fraction,absolute_schedule_horizon,train_language_expected,train_language_observed,eval_dataset,eval_language,tokenizer,grad_ckpt,hardware | same | representation 외 고정 |
| changed_axes | representation | representation | K/V repeat와 enable_gqa 직접 비교 |
| unmeasured_axes | NONE | NONE | 미실행 주장은 not_run_claims에 열거 |
| not_run_claims | TRAINING,QUALITY,BACKWARD,WHOLE_MODEL,EXTERNAL_FLASH_ATTN | same | 로그 범위 |
| permitted_claim | DIRECT_PAIRED | DIRECT_PAIRED | 같은 입력·세션의 forward 속도·working-memory 비교 |
<!-- /TINYLM_CONDITION_SIGNATURE_V1 -->

## 4. 후속

먼저 `run_P060B_Stage0aWb_wsl_sdpa_gqa_backend.sh`로 default/forced 후보선 분리를
보존 로그에서 재확인한다. 그 뒤 P060B Stage0bW는 forced backend가 아니라 **default `enable_gqa`**를 실제
`Attention.forward`에 opt-in으로 연결해 off identity, cache/non-cache 그리디·teacher-forced
정합성, prefill/decode working memory와 속도를 먼저 잰다. 통과 전에는 CLI 기본값을 바꾸지 않는다.

## 5. 재현 명령

```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python scripts/diag_sdpa_wsl_gqa.py --require-wsl --warmup 5 --iters 20 --max-speed-ratio 1.05 --min-memory-reduction 0.10
```
