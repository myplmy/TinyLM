# P025B — 2:4 동적 희소 프리트레이닝과 sparse-master

> **승인 2026-09-13.** 정본 제안서: [`20260913_TinyLM-2대4-동적희소-프리트레이닝-sparse-master-제안서-approved.md`](../proposal/done/20260913_TinyLM-2대4-동적희소-프리트레이닝-sparse-master-제안서-approved.md)  
> P025의 고정 2:4 개념을 대체하지 않고, native kernel·topology·dense/sparse master를 분리하는 후속 계획이다.  
> **현재 상태(2026-09-19):** Windows Stage0b는 import를 통과했지만 RTX 4070 Ti SUPER
> `sm_89`·PyTorch 2.10.0 환경에서 `cuSPARSELt not supported`로 첫 native 호출이 거부됐다
> ([결과 082 §6](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)).
> WSL Stage0bW의 `operation is not supported`는 backend 불가가 아니라, one-way
> `to_sparse_semi_structured` 결과(`packed_t=None`)로 input-gradient를 호출한 진단 구현 결함으로
> 재분류했다([결과 082 §7](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#7-stage0bw-wsl-재탐지2026-09-18--판정-철회와-진단-구현-오류)).
> Stage0bWb 보존 로그에서 inference forward와 bidirectional training-pack
> forward/input-gradient·tile 계약은 PASS했다. 단 `M=8192`의 training-pack forward는
> 두 형상에서 dense 대비 **0.759×/0.820×**로 느려 1.25× 게이트가 음성이었다
> ([결과 082 현재 판정](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#현재-판정2026-09-19--stage0bwb-정합성-pass-훈련-형상-속도-음성)).
> 이 수치는 training-oriented pack·training-shaped M만 측정했으므로 inference pack,
> decode/prefill, 학습 후 실제 모델 추론 축은 닫지 않는다.

## 1. 왜 — 0을 넣는 것과 실제 희소 학습은 다르다

기존 `--sparse34`는 3:4 삼진 품질·패킹 축이며 native GPU 2:4 학습 커널이 아니다.
2:4에서도 dense tensor에 mask만 곱하면 연산·optimizer state가 줄지 않는다. 따라서
native 속도, dense-master 품질, inactive state를 제거한 sparse-master, topology churn을 순서대로 재야 한다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 현 Ada/PyTorch에서 768↔2048·2048→768이 native 2:4 forward·input-grad를 실행하는가 | 속도 축의 0단계 선결 |
| Q2 | dense-master 2:4에서 엄격 2-of-4와 STE가 안정적인가 | topology 축을 열기 전 기준선 |
| Q3 | sparse-master가 dense inactive weight·Adam state 없이 품질·VRAM을 유지하는가 | 실제 메모리 절감의 핵심 |
| Q4 | churn annealing/adaptive freeze가 재생 이득은 유지하고 후반 비용을 줄이는가 | 동적 topology의 가치 분리 |

## 3. ★예측 — 정직하게

- 순수 sparse GEMM은 빠를 수 있지만 소형 TLinear 전체에서 end-to-end 1.10×를 넘지 못할 수 있다.
- 50% 구조 제약은 기존 3:4보다 공격적이므로 품질 대가가 큰 것이 더 가능성 있다.
- sparse-master가 dense-master와 동급이면 큰 메모리 가치가 있지만, hidden dense temporary/state가 남으면 그 주장을 철회한다.

## 4. 단계 설계

| 단계 | 무엇 | 계속 조건 | GPU-h |
|---|---|---|---:|
| **Stage0a ⚠️ 무효** | 실제 MLP 형상 native 2:4 진단 최초 시도 | `tinylm` import 전에 종료; 과학적 결과 `NOT_RUN`([082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)) | 0.1 미만 |
| **Stage0b-Win 🚫** | import는 통과. 첫 실제 MLP 형상에서 Windows runtime의 cuSPARSELt가 native forward 전 거부([082 §6](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)) | Windows 가속 분기 종료 | 진입 시간만 |
| **Stage0bW ⚠️ 무효** | WSL CUDA runtime 최초 재probe | one-way pack의 dgrad를 backend 첫 matmul 실패로 합친 진단 구현 오류; 원본 로그도 로깅 코드 오류로 부재([082 §7](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#7-stage0bw-wsl-재탐지2026-09-18--판정-철회와-진단-구현-오류)) | 진입 시간만 |
| **Stage0bWb ⚠️ 혼합** | inference pack forward + bidirectional training pack forward/dgrad·M8192 속도 | 정합성 PASS; training-pack 속도 0.759×/0.820×로 1.25× 미달([082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#현재-판정2026-09-19--stage0bwb-정합성-pass-훈련-형상-속도-음성)) | GPU 진단 0.1h 미만 |
| **Stage0bWc 실행 대기** | one-way inference pack vs training pack, M=1/16/128/1024/8192 정합·속도·peak allocation; pack 시간 제외 | prefill M≤1024 중 최소 하나가 ≥1.10×; decode 지원/속도는 별도 기술 | GPU 진단 0.1h 미만, 학습 0 |
| **Stage0c ⏸** | dense vs 2:4 whole primitive forward/backward | Stage0bWc로 pack 속도 귀속 후 학습가속 분기를 재판단 | 0.2 |
| **Stage1a ⏸** | dense-master 2:4, 250 step | sparse-master 메모리 트랙 별도 재승인 | 0.25 |
| **Stage1b** | flip/death/birth/resurrection 계측 | active count·birth/death 보존 | 0.25 |
| **Stage1c** | sparse-master 250 step | hidden dense state 없음, invariant 100% | 0.3 |
| **Stage2** | 100M D/S1/S2/S3 4팔 | 최소 한 sparse-master가 후속 가치 | 2.5 |
| **Stage2i** | Stage2 호환 checkpoint의 dense 대비 실제 모델 prefill/decode·peak allocation·텍스트 동등성 | Stage2 sparse 팔이 유효 checkpoint를 만들고, 같은 tokenizer·prompt·sampling 조건에서 비교 가능 | 별도 계측, SH 미작성 |
| **Stage3a** | 300M control/dense-master/sparse-master | paired/full-val 확보 | 6.0 |
| **Stage3b** | churn cosine/adaptive freeze | Stage3a에서 sparse-master 비탈락 | 2~4 |
| **Stage4** | seed/재생성 | 분해능 근처일 때만 | 3~5 |

Stage0bWb의 `scripts/diag_sparse24_backend.py`는 magnitude top-2 inference mask와
`to_sparse_semi_structured`의 one-way pack 상태를 먼저 기록한다. 이어 PyTorch 2.10의
`SparseSemiStructuredTensorCUSPARSELT.prune_dense_static_sort`로 원본·전치 `packed`를 함께
만들어 4×4 tile의 row/column 양방향 ≤2/4, forward·input-gradient의 dense 수치 일치,
동일 세션 median을 검사한다. training pruner는 일부 tile에서 8개가 아니라 7개만 남길 수 있으므로
`정확히 2/4`를 강제하지 않는다.
weight-gradient·whole-step은 Stage0c 이후 소유로 남긴다.

## 5. 판정 기준

| 축 | 성공 후보 기준 |
|---|---|
| 속도 | end-to-end step ≥1.10×; Stage0a 순수 MLP 게이트는 ≥1.25× |
| 메모리 | peak training VRAM ≥10% 절감 또는 optimizer+parameter state ≥25% 절감 |
| 품질 | 현 계열 `scripts/_rulers.py` 판정선 안; 고정 σ 복사 금지 |
| topology | 모든 4-block에 정확히 2 active, dynamic update의 births=deaths |
| 재현 | 필요 Stage4에서 seed/재생성 방향 유지 |

Stage0bWb의 훈련 형상 속도 음성은 그 pack에 한정한다. Stage0bWc가 inference pack도
음성이면 native cuSPARSELt 추론가속 분기를 닫는다. 하지만 sparse-master 메모리 축과
학습 후 실제 checkpoint의 end-to-end 추론 축은 별도 판정 전에 종결하지 않는다.

## 6. 비용

| 경로 | 누적 GPU-h |
|---|---:|
| 유효한 Stage0b 재실행에서 종료 | 0.1(무효 Stage0a의 진입 시간 제외) |
| Stage2까지 | 3.6 |
| 전 게이트 통과 최대 | **12.6~18.6** |

### 6.1 Stage0bWc preflight

| 점검 | 결과 |
|---|---|
| 독립변수 | 같은 WSL·dtype·K/N에서 sparse pack 종류와 M만 바꾸며 packing은 timing에서 제외 |
| registry 유사 런 | `check_run_registry --plan`에서 exact-2:4 inference decode/prefill 귀속 런 없음 |
| 태그 충돌 | `P025B_Stage0bWc_wsl_sparse24_inference_attribution` 저장 로그 없음 |
| 데이터·토큰 | 합성 kernel 진단이라 pool/tokenizer/steps 해당 없음; 학습 0 |
| 판정 | inference prefill M16~1024 중 하나가 ≥1.10×면 후보, 아니면 exit 8 음성; decode는 별도 기술 |
| 비용·자원 | 사용자 GPU 진단 약 0.1h, 단독 실행; 모델·체크포인트 없음 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 7. 실행 진입점

- 무효 완료: `run_P025B_Stage0a_sparse24_backend-done.bat` — import 실패로 과학적 게이트 `NOT_RUN`([결과 082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)).
- 완료(Windows 역사): `run_P025B_Stage0b_sparse24_backend-done.bat` — 해당 runtime의 native
  cuSPARSELt 지원 불가로 음성 게이트 종료([결과 082 §6](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)).
- 무효(WSL, 콘솔 증거): `run_P025B_Stage0bW_wsl_sparse24_backend-done.sh` — one-way pack의
  dgrad 실패를 첫 backend matmul 실패로 오분류했다. **로깅 프로그램 코드 오류**로 원본 로그도 없다.
- 완료: `run_P025B_Stage0bWb_wsl_sparse24_training_pack-done.sh` — 정합성 PASS,
  M8192 training-pack 속도 음성([082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#현재-판정2026-09-19--stage0bwb-정합성-pass-훈련-형상-속도-음성)).
- 실행 대기: `run_P025B_Stage0bWc_wsl_sparse24_inference_attribution.sh` — inference/training
  pack과 decode/prefill/training M을 분리하는 속도 귀속 게이트. GPU 실행은 `NOT_RUN`.
- 미작성: Stage0c~Stage4와 Stage2i 학습 후 checkpoint end-to-end 추론. 실행 가능한
  sparse 학습 모델과 앞 게이트 없이 placeholder SH를 만들지 않는다.

## 8. 한계

- Stage0b 진단은 sparse weight-gradient, optimizer, TLinear/STE 통합을 증명하지 않는다.
- exact 2:4 mask와 `SparseSemiStructuredTensor` 타입 확인만으로 전체 학습 가속을 주장하지 않는다.
- P092의 자유 unstructured connectivity·ERK·25/12.5% density는 이 계획에 넣지 않는다.
- 공통 계측 계약을 공유하지만 두 계획의 판정을 합치지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-13: 제안서 승인, P025B 배정. 공통 계측 계약·exact-N:M primitive·Stage0a backend 배치 작성. 실행 `NOT_RUN`.
- 2026-09-13: Stage0a는 `ModuleNotFoundError: tinylm`으로 첫 희소 연산 전에 종료([결과 082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)). 저장소 루트 bootstrap을 추가했고 정적 검사만 PASS했다. 방법론 예측은 대조되지 않았으며 Stage0b 재실행이 필요하다.
- 2026-09-14: Stage0b는 import 후 첫 `M=8192,K=768,N=2048` native 호출에서
  `cuSPARSELt not supported on your machine`으로 종료했다. forward·input-grad·속도·품질은
  `NOT_RUN`; Windows runtime 가속 분기는 사전등록 규칙에 따라 닫았다([결과 082 §6](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)).
- 2026-09-18: WSL 이관을 별도 environment stratum으로 사전등록하고 Stage0bW 진단 코드·`.sh`를
  정적 검증했다.
- 2026-09-18: 사용자 queue의 Stage0bW는 `operation is not supported`로 종료했고 당시에는
  WSL backend 불가로 오판했다. 원본 로그는 WSL launcher의 로깅 프로그램 코드 오류로 부재한다.
- 2026-09-19: PyTorch 2.10 소스와 실행 순서를 재대조했다. 일반 변환은 `packed_t=None`이고
  정확한 오류는 transpose된 sparse 객체의 `packed is None`일 때 발생하므로, 실패는 dgrad용
  양방향 패킹 누락으로 재분류했다. 학습용 양방향 pack과 단계별 출력의 Stage0bWb를 구현·정적
  검증했으며 실제 GPU 판정은 `NOT_RUN`이다.
- 2026-09-19: Stage0bWb 보존 로그를 회수했다. bidirectional pack 정합성은 PASS,
  training-shaped forward는 0.759×/0.820×로 음성이었다. 훈련 pack의 속도를 추론으로
  외삽하지 않도록 Stage0bWc 귀속 진단·SH를 구현했고 GPU 결과는 `NOT_RUN`이다.
