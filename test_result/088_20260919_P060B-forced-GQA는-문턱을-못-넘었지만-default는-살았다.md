# 결과 088 — P060B default GQA는 실제 모델에서 11% 빨랐고 forced 지원은 backend별로 갈렸다

- **파일명 역사 보존**: 최초 단계의 이름을 인용한 완료 WIP는 불변이므로 파일은 개명하지 않는다. 현재 판정은 H1과 최신 실행 절이 소유한다.

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

## 6. Stage0aWb + Stage0bW 실제 후속(2026-09-19)

### 6.1 Wb micro gate

- **로그**: `088_log_20260919_P060B_Stage0aWb_wsl_sdpa_gqa_backend.txt`
- **종료**: exit 0 · 실행 가능한 default practical candidate 계약 PASS

| 형상 | default | forced CUDNN | forced FLASH | EFFICIENT |
|---|---|---|---|---|
| B8/T1024 | 1.018×, memory −37.2% | 1.051×, −38.0% | **1.031×, −37.2%** | unavailable |
| B1/T128 | **0.879×, −37.2%** | **1.046×, −37.9%** | 1.190×, −37.2% | unavailable |

exit 0으로 default practical candidate를 재현했고 주 형상에서는 FLASH도 +5% 이내 후보가 됐다.
이는 같은 20회 측정의 session noise 때문에 Wa의 FLASH 1.058×와 문턱 양쪽에 놓인 결과이므로
“항상 FLASH가 빠르다”가 아니라 **경계 후보**로 읽는다.

로그의 긴 경고는 지원된 FLASH/CUDNN 실패가 아니다. `sdpa_kernel(EFFICIENT_ATTENTION)`가
다른 backend를 강제로 끈 상태에서 local torch 2.10 runtime이 Q 12/KV 3 head GQA를 지원하지
못해, 왜 FLASH·cuDNN으로 fallback할 수 없는지를 함께 열거한 뒤 `No available kernel`을 낸
것이다. 이전 판독은 EFFICIENT unavailable을 기록했지만 raw warning의 범위와 의미를 설명·정리하지
않은 **보고 및 진단 출력 누락**이었다. 진단기는 warning을 variant별로 포착해 한 줄의 structured
UNAVAILABLE reason으로 남기고, timing 반복에서는 같은 warning을 억제한다. 또한 PyTorch 경고가
제안한 singleton grouped broadcast를 `on_efficient_broadcast`로 별도 추가했다. 이는 K/V를 물리
repeat하지 않는 zero-stride view이며 CPU math 경로에서 manual-repeat와 동등하고 physical storage가
더 작음을 확인했다. local torch 2.10 GPU kernel의 실제 지원·속도·working memory는 Wc 전까지
`NOT_RUN`이다. 공식 main 문서는 forced fused kernel이 불가하면 이유를 warning으로 낸다고 하며
GQA를 실험 기능으로 설명하므로 버전별 지원을 구분한다:
[PyTorch SDPA](https://docs.pytorch.org/docs/main/generated/torch.nn.functional.scaled_dot_product_attention.html).

### 6.2 actual d14 checkpoint model path

- **로그**: `088_log_20260919_P060B_Stage0bW_model_gqa_integration.txt`
- **종료**: exit 0 · 정합 PASS; 속도 후보이며 품질·학습 PASS 아님

- full forward, cache prefill, cache decode: `max_abs=0`, `NRMS=0`, cosine≈1
- median: off **11.1354 ms**, on **9.8974 ms** = on/off **0.889×**, 약 **11.1% 빠름**
- peak allocation: 9.568/9.568 MiB, 측정된 감소 **0%**

따라서 WSL default `enable_gqa`는 actual model forward에서도 정합과 속도 후보를 통과했다.
다만 seq256·B1 한 형상이고 peak allocation이 줄지 않았으며 backward·training step·실제 생성
품질은 `NOT_RUN`이다. CLI 기본값은 계속 off로 보존한다.

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage0bW_model_gqa_integration-done.sh` 추출, 2026-09-19)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" scripts/diag_sdpa_gqa_model_path.py --ckpt "$ckpt" --arch dense    --seq 256 --warmup 3 --iters 10 --max-nrms 0.001 --min-cosine 0.999999
```

## 7. Stage0aWc backend 귀속(2026-09-20) — **default/CUDNN/FLASH 후보, EFFICIENT만 불가**

> 로그: `088_log_20260920_P060B_Stage0aWc_wsl_sdpa_gqa_backend.txt` · 종료코드 0

| 형상 | default GQA | forced CUDNN | forced FLASH | direct EFFICIENT | grouped EFFICIENT(Wc) |
|---|---|---|---|---|---|
| B8/T1024 | 0.993×, working −37.2% | 0.990×, −38.0% | 1.001×, −37.2% | unavailable | unavailable(5-D) |
| B1/T128 | 0.993×, −15.5% | 1.151×, −16.5% | 1.127×, −15.5% | unavailable | unavailable(5-D) |

B8/T1024에서는 default·CUDNN·FLASH가 모두 속도 +5% 이내와 working-memory −10% 이상을
충족했다. 작은 B1/T128에서는 default만 문턱을 통과했다. 따라서 **GQA 때문에 SDPA를 못 쓴다**는
결론은 틀리며, 현 runtime의 실용 경로는 dispatcher default다. forced EFFICIENT의 실패를
FLASH/CUDNN 실패로 확대하지 않는다.

Wc가 추가한 grouped-broadcast는 수학적으로는 repeat와 같지만 `[B,Hkv,G,T,D]` 5-D를 그대로
SDPA에 전달했다. fused kernel은 4-D를 요구하므로 `All fused kernels requires ... 4
dimensional`로 실패했다. 이는 EFFICIENT 자체의 최종 음성이 아니라 **후속 후보 구현의 형상
결함**이다.

## 8. Stage0aWd 4-D grouped-broadcast 교정 — **정적 완료·GPU NOT_RUN**

`_grouped_broadcast_inputs()`는 이제 Q를 `[B×Hkv,G,T,D]`, K/V를 zero-stride
`[B×Hkv,G,T,D]`로 만들고 결과를 원래 `[B,Hq,T,D]`로 되돌린다. CPU math 동등성,
4-D shape, K/V group stride 0, physical storage 비중복 회귀는 통과했다.

새 `run_P060B_Stage0aWd_wsl_sdpa_gqa_backend.sh`가 EFFICIENT GPU 지원·속도·메모리를
재검증한다. 이 팔은 default GQA 채택의 선결이 아니라 backend attribution 후속이다. actual model
forward의 11.1% 후보와 micro working-memory 절감은 유지되며 backward·학습·장문 decode 품질은
계속 `NOT_RUN`이다.

### 8.1 Stage0aWc 재현 명령 정본

```bash
"$python_bin" scripts/diag_sdpa_wsl_gqa.py --require-wsl --warmup 5 --iters 20 \
  --max-speed-ratio 1.05 --min-memory-reduction 0.10
```
