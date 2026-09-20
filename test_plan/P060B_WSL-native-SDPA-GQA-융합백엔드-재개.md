# P060B — WSL native SDPA/GQA 융합 백엔드 재개

> **신규 후속 계획 2026-09-19.** [P060](P060_어텐션-활성메모리-축-GQA는-그중-하나였다.md)의
> Windows/PyTorch 결과를 지우지 않고 WSL2·torch `2.10.0+cu130`을 독립 environment
> stratum으로 재개한다. 구 P060의 기본 dispatcher 결론은 유지하며, 새 로그
> 전까지 WSL 결과는 `E2E_NOT_RUN`이다. Stage0aW 보존 로그에서 forced backend는 음성이었지만
> dispatcher-selected `on_default`가 속도 +0.3%·working memory −37.2%로 실용 문턱을 통과했다
> ([결과 088](../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md)).
> **현재 상태(2026-09-20):** Wc에서 B8/T1024 default·CUDNN·FLASH가 모두 실용 문턱을
> 통과했고 actual model default GQA는 11.1% 빠른 후보를 유지한다. direct EFFICIENT는 불가하며,
> Wc grouped 후보는 5-D 형상 결함이었다. 4-D로 교정한 Wd는 정적 PASS·GPU `NOT_RUN`이다.

## 1. 재개 근거와 비재개 경계

P060 A2는 Windows에서 `enable_gqa=True` + CUDNN 강제가 실행 가능하지만,
기본 dispatcher는 MATH로 떨어지는 것으로 해석됐다([결과 046 §12](../test_result/046_20260814_P060-enable_gqa는-디스패처가-MATH를-골라서-느렸다.md#12-단계-a2--우리-학습-경로는-건강하다-그리고-enable_gqa-는-되살릴-수-있다-2026-08-14)).
[PyTorch SDPA 공식 문서](https://docs.pytorch.org/docs/main/generated/torch.nn.functional.scaled_dot_product_attention.html)상
SDPA는 입력에 따라 백엔드를 동적 선택하며 `sdpa_kernel()`로 특정 융합 구현을 강제할 수 있다.
GQA는 query head 수가 KV head 수의 배수이고 K/V head 수가 같아야 한다.

현 WSL 정적 inventory는 torch `2.10.0+cu130`, Triton `3.6.0`, `flash-attn`
미설치다. [Triton 공식 지원표](https://github.com/triton-lang/triton/blob/main/README.md)는
Linux와 NVIDIA compute capability 8.0+를 지원하므로
WSL + `sm_89`는 플랫폼 선결을 만족한다. 패키지 존재는 커널 PASS가 아니다.

- **재개:** P060의 미완 A3, 즉 WSL native FLASH/CUDNN/EFFICIENT에서 forced GQA의
  정합성·속도·working memory.
- **보류:** 외부 `flash-attn`. [공식 요구사항](https://github.com/Dao-AILab/flash-attention/blob/main/README.md?plain=1)은
  Linux·PyTorch 2.2+·CUDA 12+·Ampere/Ada/Hopper와 맞지만 설치·다운로드 승인이 없고
  PyTorch native SDPA가 먼저다.
- **비재개:** P014 삼진 Triton 커널. 종전 결과는 Triton 미설치가 아니라 커널
  경제성·융합 구조에서 나왔으므로 WSL 전환만으로 재개하지 않는다.

## 2. 질문과 사전 예측

| # | 질문 | 사전 예측 |
|---|---|---|
| Q1 | WSL 빌드에 GQA를 받는 native 융합 백엔드가 있는가 | CUDNN 또는 FLASH 중 하나는 살 가능성 |
| Q2 | manual KV repeat 기준과 로짓이 수치 허용오차 안에서 같은가 | bf16 커널 차이만 남을 것 |
| Q3 | B8/T1024 forced GQA가 off-default 대비 속도 +5% 이내이며 working memory를 ≥10% 줄이나 | 메모리는 줄지만 Ada 속도 문턱이 위험 |
| Q4 | B1/T128에서도 방향이 유지되나 | 작은 형상은 launch overhead로 열세 가능 |

## 3. 단계와 중단 게이트

| 단계 | 내용 | 계속 조건 | 비용·상태 |
|---|---|---|---|
| **Stage0aW ✅ 혼합** | off/on default와 on-CUDNN/FLASH/EFFICIENT의 정합성·median forward·working memory | forced 세 경로는 문턱 미달/불가; default는 +0.3%, memory −37.2%로 실용 후보 | [088](../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md) |
| **Stage0aWb ✅ 후보 재현** | dispatcher default와 forced 후보를 별도 판정 | B8/T1024 default 1.018×·FLASH 1.031×, memory 약 −37%; EFFICIENT만 unavailable | [088 §6.1](../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md#61-wb-micro-gate) |
| **Stage0aWc ✅ 혼합** | warning을 variant별 포착하고 direct EFFICIENT와 grouped-broadcast EFFICIENT를 분리 | default/CUDNN/FLASH 후보 재현, direct EFFICIENT unavailable; grouped 팔은 5-D 형상 결함으로 무효 | [088 §7](../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md#7-stage0awc-backend-귀속2026-09-20--defaultcudnnflash-후보-efficient만-불가) |
| **Stage0aWd 실행 대기** | batch×KV-head를 접은 4-D zero-stride grouped-broadcast로 EFFICIENT 재검증 | direct 결과와 분리해 정합·속도·physical storage 출력 | GPU 진단 수 초, 학습 0 |
| **Stage0bW ✅ actual model 후보** | d14 RMS4 checkpoint full/cache prefill/decode | bit-identical, on/off 0.889×로 11.1% 빠름; peak 감소 0% | [088 §6.2](../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md#62-actual-d14-checkpoint-model-path) |
| **Stage1W 구현·실행 대기** | 현 WSL current recipe 250-step off vs default GQA 학습 속도·peak reserved·NaN/skip | memory ≥10% 절감, ms/step 악화 ≤5% | SH·JSON gate 구현, 약 0.5h |
| **Stage2W** | 배포 prefill/decode·장문 생성 정합성 | cache 경로 실제 텍스트와 속도 방향 통과 | 별도 승인·모델 실행 |

Stage0aW exit 8은 forced-only 사전등록 질문에는 유효한 음성이지만, 실용 후보선에서
`on_default`를 제외한 설계 때문에 전체 GQA 음성으로 읽을 수 없다. Stage0aWb는 두 후보군을
분리하고, 그 결과 전에는 기본 SDPA 경로를 바꾸지 않는다.

## 4. preflight·실행 경계

| 점검 | 결과 |
|---|---|
| 유사 런 | registry의 `m100R1c_ko-en_300M_mC_gqa_off250/on250`와 P060 A2는 Windows 학습·가용성 결과. 이번 독립변수는 WSL isolated forward의 forced backend·working memory라 중복 아님 |
| 비교 조건 | 같은 q/k/v·bf16·형상·세션, backend 선택과 KV repeat만 변경 |
| 판정 | B8/T1024 주 게이트, B1/T128은 형상 전이 기술 |
| 태그 | `P060B_Stage0aW_wsl_sdpa_gqa_backend`; registry 충돌 없음 |
| 진입점 | `run_P060B_Stage0aW_wsl_sdpa_gqa_backend.sh` |
| 보호 경계 | 데이터·체크포인트·모델 로딩·학습 0; Codex GPU 실행 금지 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 5. 한계

- isolated forward는 학습 ms/step, backward 결정성, 전체 모델 품질을 증명하지 않는다.
- SDPA 융합 커널은 math reference와 완전 비트 일치할 필요는 없지만 bf16
  허용오차 검사를 먼저 통과해야 한다.
- working memory는 입력 tensor bytes + 호출 peak allocation delta이며 `peak reserved`나
  전체 학습 VRAM으로 부르지 않는다.
- 외부 `flash-attn` 설치는 이 계획의 권한이 아니다.

## 6. 이력

- 2026-09-19: WSL torch/Triton inventory와 P060 미완 A3를 대조해 P060B를 신설했다.
  Stage0aW 진단·SH를 구현했으며 GPU 결과는 `NOT_RUN`이다.
- 2026-09-19: Stage0aW 보존 로그는 forced CUDNN/FLASH가 +7.9%/+5.8%로 5% 문턱을
  못 넘겨 exit 8이었다. 그러나 `on_default`는 +0.3%와 working memory −37.2%를 동시에
  달성했다. forced backend 이름을 실용 목표보다 앞세운 최종 candidate 선정은 설계결함이라
  Stage0aWb에서 default/forced를 별도 보고하고 어느 한쪽이 통과하면 practical candidate로 남긴다.
- 2026-09-19: 기존 `--sdpa-gqa` actual Attention 배선을 재사용해 d14 RMS4 checkpoint의
  full forward·cache prefill·decode 정합, same-session 속도·peak allocation을 한 로그에 남기는
  Stage0bW 진단·SH를 구현했다. 기본값은 off이며 사용자 실행 전 결과는 `NOT_RUN`이다.
- 2026-09-19: Wb는 default practical 후보와 forced FLASH 후보를 재현했고 actual d14 model은
  정합 0 오차·11.1% 속도 이득을 보였다. 긴 warning은 EFFICIENT 강제 probe가 local runtime의
  head-count 제약으로 실패하며 다른 비활성 backend 이유까지 열거한 출력이다. 이전 판독은 이를
  설명·구조화하지 않았고 Wc에서 한 행 reason으로 교정한다. 기본값은 계속 off다.
- 2026-09-20: Wc는 B8/T1024에서 default·CUDNN·FLASH 후보를 모두 재현하고 EFFICIENT만
  unavailable로 분리했다. 그러나 grouped-broadcast를 5-D로 전달해 fused kernel의 4-D 계약을
  위반했다. Q를 `[B×Hkv,G,T,D]`로 접고 K/V를 같은 4-D head 축에 zero-stride expand하는 Wd를
  구현했으며 GPU 결과는 `NOT_RUN`이다. 이 교정은 default GQA 후보를 무효화하지 않는다.

## 7. 2026-09-20 Stage1W 구현·preflight

과거 Windows P060의 `mC_gqa_off250/on250`은 m100R1c tied·구 optimizer 계열에서 on이
약 1.96배 느리고 reserved VRAM도 5.07→6.45GB로 악화됐다. 새 Stage1W는 이를 지우거나
반복하는 것이 아니라 **WSL torch2.10 + m100s10 dense + 현 Muon RMS4** environment/current
recipe stratum에서 default dispatcher 후보가 학습에도 전이하는지 재검증한다.

**독립변수**: 같은 250-step 조건의 `--sdpa-gqa` off/on 하나다. tags는
`p060b_s1w_off250/on250`이며 충돌 0, draw는 32.768M, pool은 exact 600M이다.

- `diag_sdpa_gqa_training_pair.py`가 JSON의 조건 동일성, `sdpa_gqa` 실제값, skip,
  `ms_step_median`, reserved VRAM을 fail-closed로 대조한다.
- on/off≤1.05와 reserved-memory ≥10% 절감을 모두 만족해야 exit0 후보이며, 유효 음성은 exit8이다.
- 50M 미만 속도 probe라 W&B 업로드를 금지한다. 품질은 `NOT_RUN`이다.
- 실행 파일: `run_P060B_Stage1W_sdpa_gqa_training_gate.sh`.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
