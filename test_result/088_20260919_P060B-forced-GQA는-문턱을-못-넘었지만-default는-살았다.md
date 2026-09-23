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

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage1W_sdpa_gqa_training_gate-done.sh` 추출, 2026-09-21)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en    --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8    --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20    --eval-every 250 --optimizer muon --muon-scale rms --muon-lr-mult 4    --matrix-weight-decay 0 --cla-group 2 --no-ckpt --compile --seed 1337    --tag p060b_s1w_off250
   "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en    --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8    --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20    --eval-every 250 --optimizer muon --muon-scale rms --muon-lr-mult 4    --matrix-weight-decay 0 --cla-group 2 --sdpa-gqa --no-ckpt --compile --seed 1337    --tag p060b_s1w_on250
   "$python_bin" scripts/diag_sdpa_gqa_training_pair.py    --off-tag p060b_s1w_off250 --on-tag p060b_s1w_on250    --max-speed-ratio 1.05 --min-memory-reduction 0.10
```

## 9. Stage0aWd·Stage1W 실제 결과(2026-09-20~21) — **default micro 후보, 학습 memory gate 음성**

### 9.1 Wd backend 귀속

| 형상 | default GQA | forced FLASH | grouped EFFICIENT | 판정 |
|---|---|---|---|---|
| B8/T1024 | 0.995×, working −37.2% | 1.034×, −37.2% | 1.232×, −13.2% | default·FLASH 후보 |
| B1/T128 | 1.003×, working −37.2% | 1.203×, −37.2% | 1.639×, −13.3% | default만 후보 |

4-D grouped-broadcast는 실제 실행돼 Wc의 형상 결함은 해소됐지만 EFFICIENT는 두 형상 모두 느리다.
direct EFFICIENT의 `No available kernel`은 여전히 Q-head 12/KV-head 3 native GQA 미지원이며,
FLASH/cuDNN 실패로 확대하지 않는다. 실용 경로는 dispatcher default다.

### 9.2 Stage1W 학습 gate

| 팔 | median ms/step | reserved VRAM | final val | `grad_max` | skip |
|---|---:|---:|---:|---:|---:|
| off | 1752.714 | 8.852GB | 4.9450 | 1.0155 | 0 |
| on | 1757.069 | 8.676GB | 4.9425 | 0.9561 | 0 |

속도 on/off는 **1.0025×**로 +5% 이내지만 reserved 절감은 **1.986%**라 10% 문턱에 크게
못 미친다. 따라서 `enable_gqa`는 isolated working-memory를 줄여도 현재 전체 training reserved
memory의 유효 레버가 아니며 Stage1W는 exit8 과학적 음성이다. 32.768M probe의 val 차이는 품질
판정에 쓰지 않고 W&B에도 올리지 않는다. CLI 기본값은 off를 유지한다.

<!-- TINYLM_CONDITION_SIGNATURE_V1 id=P060B-stage1W-training-gqa -->
| field | arm_a | arm_b | evidence |
| --- | --- | --- | --- |
| pool_id | ko-en_600000000 | ko-en_600000000 | exact cache |
| actual_pool_tokens | 597000000 | 597000000 | cache 계약 |
| pool_override | exact 600M | exact 600M | launcher |
| steps | 250 | 250 | JSON |
| micro_bs | 8 | 8 | JSON |
| accum | 16 | 16 | JSON |
| seq | 1024 | 1024 | JSON |
| actual_draw_tokens | 32768000 | 32768000 | 계산·JSON |
| sampler_with_replacement | true | true | loader 계약 |
| expected_unique_tokens | about 31.9M | about 31.9M | 복원추출 모형 |
| sequential_epoch_claim | false | false | epoch 주장 없음 |
| scheduler | wsd | wsd | JSON |
| warmup | same trainer rule | same trainer rule | 동일 코드 |
| anneal_start | same | same | JSON |
| decay_fraction | 0.20 | 0.20 | JSON |
| absolute_schedule_horizon | 250 | 250 | JSON |
| train_language_expected | ko/en 50:50 | ko/en 50:50 | cache recipe |
| train_language_observed | same cached sample order | same cached sample order | same seed |
| eval_dataset | same internal val | same internal val | JSON |
| eval_language | ko/en | ko/en | same cache |
| tokenizer | tok-ko-en-32768 | tok-ko-en-32768 | same data |
| grad_ckpt | false | false | JSON |
| representation | repeated K/V off | enable_gqa true | 독립변수 |
| comparator_tag | p060b_s1w_off250 | p060b_s1w_on250 | JSON |
| matched_axes | pool_id,actual_pool_tokens,pool_override,steps,micro_bs,accum,seq,actual_draw_tokens,sampler_with_replacement,expected_unique_tokens,sequential_epoch_claim,scheduler,warmup,anneal_start,decay_fraction,absolute_schedule_horizon,train_language_expected,train_language_observed,eval_dataset,eval_language,tokenizer,grad_ckpt | same | representation 외 고정 |
| changed_axes | representation | representation | CLI flag |
| unmeasured_axes | NONE | NONE | speed/memory pair complete |
| not_run_claims | FULL_QUALITY,LONG_CONTEXT,DEPLOY_GENERATION | same | 250-step 범위 |
| permitted_claim | DIRECT_PAIRED | DIRECT_PAIRED | 같은 학습조건 speed/reserved 비교 |
<!-- /TINYLM_CONDITION_SIGNATURE_V1 -->


<a id="31-최신-누적-판정-stage2wstage3w2026-09-22--품질은-실무상-동급-cache-배포-정합은-미통과"></a>
## 10. 최신 누적 판정: Stage2W·Stage3W(2026-09-22) — **품질은 실무상 동급, cache 배포 정합은 미통과**

<a id="311-stage2w-cache-deploy--seq128-decode에서-조기-중단"></a>
### 10.1 Stage2W cache deploy — seq128 decode에서 조기 중단

> 로그: `088_log_20260922_P060B_Stage2W_gqa_deploy_cache.txt` · exit 4.

seq128 prefill 정합 검사는 조기 반환을 발생시키지 않았지만, 이어진 cache decode에서
`NRMS=0.0044894`, `cosine=0.9999901`로 사전등록 문턱 `NRMS<=0.001`,
`cosine>=0.999999`를 모두 못 넘었다. 이는 backend 미지원 예외가 아니라 off의
K/V 물리 복제와 on의 `enable_gqa=True` 결과가 cache를 포함한 전체 모델에서 쌓인
수치 차이다.

진단이 fail-fast로 정지했으므로 seq512/1024, prefill/decode timing, peak allocation,
3개 greedy text는 **NOT_RUN**이다. 즉 “cache GQA가 느리다”나 “text가 달라졌다”가
이 로그의 결론이 아니다. 문턱을 사후에 느슨하게 바꿔 PASS로 만들지 않았고,
Stage2W는 배포 정합 게이트 **음성·후속 계측 미완결**로 보존한다.

<a id="312-stage3w-300m-3-seed-품질-panel"></a>
### 10.2 Stage3W 300M 3-seed 품질 panel

> **원본 로그(7건)**:
> `088_log_20260922_P060B_Stage3aW_gqa_quality_off_s1337.txt`,
> `088_log_20260922_P060B_Stage3aW_gqa_quality_on_s1337.txt`,
> `088_log_20260922_P060B_Stage3aW_gqa_quality_off_s2024.txt`,
> `088_log_20260922_P060B_Stage3aW_gqa_quality_on_s2024.txt`,
> `088_log_20260922_P060B_Stage3aW_gqa_quality_off_s31415.txt`,
> `088_log_20260922_P060B_Stage3aW_gqa_quality_on_s31415.txt`,
> `088_log_20260922_P060B_Stage3bW_gqa_quality_pair.txt`.
> 학습 6팔·paired 3회 모두 exit 0, 전 팔 `n_skip=0`, W&B post-run sync PASS.

| seed | off full-val | on full-val | off−on | paired 판정 | on/off ms/step |
|---:|---:|---:|---:|---|---:|
| 1337 | 3.6346 | **3.6344** | +0.0001 | 구분 불가 | 0.9898× |
| 2024 | **3.6362** | 3.6366 | -0.0004 | 구분 불가 | 1.0123× |
| 31415 | **3.6387** | 3.6448 | -0.0062 | 통계적 유의·실무 분해능 0.024 미만 | 0.9943× |
| 평균 | **3.6365** | 3.6386 | -0.0021 | 방향 불일치·실무상 동급 | 0.9988× |

on은 reserved VRAM 8.852→8.676 GiB(**-1.986%**), allocated 8.009→7.886 GiB
(**-1.536%**)로 세 seed 모두 같은 절감을 남겼다. 하지만 ms/step은 빠름/느림/빠름이
갈렸고 평균 비율 0.9988×로 중립이다. paired full-val도 한 seed는 on 우세,
두 seed는 off 우세라 사전등록한 “세 seed 방향 일치”는 통과하지 못했다.
모든 차이가 현 계열의 실무 분해능 안이므로 **품질 비퇴행 후보**는 남지만,
Stage1의 10% 메모리 문턱 미달과 Stage2 cache 정합 실패를 넘어 기본 on으로 승격할 근거는 아니다.

JSON 학습-마지막 val은 off/on 평균 3.5820/3.5842였지만, 이 판정은 동일 크롭
full-val을 정본으로 쓴다. 로그의 W&B `reinit` deprecation은 upload 실패가 아니며
전 팔 `[wandb-auto] PASS`를 확인했다. 후속 코드는 `finish_previous`로 교정했다.

<!-- TINYLM_CONDITION_SIGNATURE_V1 id=P060B-stage3W-gqa-quality-panel -->
| field | arm_a | arm_b | evidence |
| --- | --- | --- | --- |
| pool_id | ko-en exact 600M | ko-en exact 600M | launcher·JSON |
| actual_pool_tokens | 597000000 | 597000000 | exact cache, val 제외 |
| pool_override | true | true | `--pool-tokens 600M` |
| steps | 2289 | 2289 | launcher·JSON |
| micro_bs | 8 | 8 | launcher·JSON |
| accum | 16 | 16 | launcher·JSON |
| seq | 1024 | 1024 | launcher·JSON |
| actual_draw_tokens | 300023808 | 300023808 | 2289×8×16×1024 |
| sampler_with_replacement | true | true | Loader 계약 |
| expected_unique_tokens | 235824254 | 235824254 | 복원추출 공식 |
| sequential_epoch_claim | false | false | epoch 주장 없음 |
| scheduler | wsd | wsd | launcher |
| warmup | 100 | 100 | trainer 계약 |
| anneal_start | same trainer rule | same trainer rule | 동일 2289-step 지평선 |
| decay_fraction | 0.20 | 0.20 | launcher |
| absolute_schedule_horizon | 2289 steps | 2289 steps | launcher |
| train_language_expected | ko/en about 50/50 legacy pool | ko/en about 50/50 legacy pool | 동일 cache |
| train_language_observed | not logged; seed-matched pair | not logged; seed-matched pair | seed 1337,2024,31415 |
| eval_dataset | 300M paired full-val | 300M paired full-val | 1464 same crops per seed |
| eval_language | same ko-en val cache | same ko-en val cache | paired_eval |
| tokenizer | ko-en BPE 32768 | ko-en BPE 32768 | cache |
| grad_ckpt | false | false | launcher |
| representation | repeated K/V off | dispatcher enable_gqa on | `--sdpa-gqa` 단일 변경 |
| seed | 1337,2024,31415 | 1337,2024,31415 | seed 내 직접 짝 |
| comparator_tag | `p060b_q_off_s*` three runs | `p060b_q_on_s*` three runs | JSON·paired log |
| matched_axes | pool_id,actual_pool_tokens,pool_override,steps,micro_bs,accum,seq,actual_draw_tokens,sampler_with_replacement,expected_unique_tokens,sequential_epoch_claim,scheduler,warmup,anneal_start,decay_fraction,absolute_schedule_horizon,train_language_expected,train_language_observed,eval_dataset,eval_language,tokenizer,grad_ckpt,seed | same | representation 외 고정 |
| changed_axes | representation | representation | off 대 on |
| unmeasured_axes | NONE | NONE | 품질 panel 완주 |
| not_run_claims | CACHE_DEPLOY_ADOPTION,OTHER_ARCHITECTURES,DOWNSTREAM_BENCH | CACHE_DEPLOY_ADOPTION,OTHER_ARCHITECTURES,DOWNSTREAM_BENCH | Stage2 미통과·d14 300M 한계 |
| permitted_claim | DIRECT_PAIRED | DIRECT_PAIRED | seed 내 off/on 품질·시간·VRAM |
<!-- /TINYLM_CONDITION_SIGNATURE_V1 -->

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage2W_gqa_deploy_cache-done.sh` 추출, 2026-09-22)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" scripts/diag_sdpa_gqa_deploy.py      --ckpt "$ckpt" --arch dense --data ko-en --seqs 128,512,1024      --max-new 32 --warmup 2 --iters 5 --max-nrms 0.001      --min-cosine 0.999999 --max-slowdown 1.05 --min-benefit 0.05
```

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage3aW_gqa_quality_off_s1337-done.sh` 추출, 2026-09-22)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en      --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8      --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20      --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms      --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --no-ckpt --compile      --seed 1337 --tag p060b_q_off_s1337
```

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage3aW_gqa_quality_off_s2024-done.sh` 추출, 2026-09-22)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en      --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8      --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20      --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms      --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --no-ckpt --compile      --seed 2024 --tag p060b_q_off_s2024
```

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage3aW_gqa_quality_off_s31415-done.sh` 추출, 2026-09-22)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en      --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8      --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20      --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms      --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --no-ckpt --compile      --seed 31415 --tag p060b_q_off_s31415
```

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage3aW_gqa_quality_on_s1337-done.sh` 추출, 2026-09-22)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en      --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8      --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20      --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms      --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --sdpa-gqa --no-ckpt --compile      --seed 1337 --tag p060b_q_on_s1337
```

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage3aW_gqa_quality_on_s2024-done.sh` 추출, 2026-09-22)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en      --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8      --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20      --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms      --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --sdpa-gqa --no-ckpt --compile      --seed 2024 --tag p060b_q_on_s2024
```

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage3aW_gqa_quality_on_s31415-done.sh` 추출, 2026-09-22)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" run100m.py train --arch dense --preset m100s10 --data ko-en      --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8      --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.20      --eval-every 100 --save-every 500 --optimizer muon --muon-scale rms      --muon-lr-mult 4 --matrix-weight-decay 0 --cla-group 2 --sdpa-gqa --no-ckpt --compile      --seed 31415 --tag p060b_q_on_s31415
```

---

## ★부록 — 재현 명령 정본 (`run_P060B_Stage3bW_gqa_quality_pair-done.sh` 추출, 2026-09-22)

> ★**이 절이 있어야 launcher를 지울 수 있다**(`sync_experiments_tsv.py`).
> 명령은 **launcher에서 기계로 뽑았다** — 손으로 옮겨 적지 않았다.

```
   "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en --tokens 300M      --models p060b_q_off_s1337 p060b_q_on_s1337      --dump-crops runs/logs/p060b_gqa_quality_s1337.json || exit $?
   "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en --tokens 300M      --models p060b_q_off_s2024 p060b_q_on_s2024      --dump-crops runs/logs/p060b_gqa_quality_s2024.json || exit $?
   "$python_bin" scripts/paired_eval.py --preset m100s10 --data ko-en --tokens 300M      --models p060b_q_off_s31415 p060b_q_on_s31415      --dump-crops runs/logs/p060b_gqa_quality_s31415.json
```
