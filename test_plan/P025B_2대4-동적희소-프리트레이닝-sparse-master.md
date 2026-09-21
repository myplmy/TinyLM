# P025B — 2:4 동적 희소 프리트레이닝과 sparse-master

> **승인 2026-09-13.** 정본 제안서: [`20260913_TinyLM-2대4-동적희소-프리트레이닝-sparse-master-제안서-approved.md`](../proposal/done/20260913_TinyLM-2대4-동적희소-프리트레이닝-sparse-master-제안서-approved.md)  
> P025의 고정 2:4 개념을 대체하지 않고, native kernel·topology·dense/sparse master를 분리하는 후속 계획이다.  
> **현재 상태(2026-09-21):** Windows Stage0b는 import를 통과했지만 RTX 4070 Ti SUPER
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
> decode/prefill, 학습 후 실제 모델 추론 축은 닫지 않는다. Stage0bWc는 둘째 형상
> `M=128`에서 elementwise `rtol/atol` 문턱으로 exit 4가 나고 이후 형상을 생략했다
> ([결과 082 §8](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#8-stage0bwc-wsl-inference-attribution2026-09-19--정합-문턱에서-중단-측정된-속도는-전부-음성)).
> 이는 backend 결론이 아니라 **절대오차 단독 gate와 fail-fast 설계 결함**이 섞인 결과다.
> **현재 후속(2026-09-21):** Stage0bWe/Wf/Wg를 완주했다. Wg에서 We의
> pre-replay 구현 결함을 닫고 graph 8행을 모두 통과했다. M=1 graph는
> 0.079~0.369×로 음성이지만 M=8192 graph는 1.400~2.342× 후보다. 반면
> 일반 PyTorch wall은 0.771~0.802×로 여전히 느리다([082 §12](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#12-stage0bwg-cuda-graph-복구2026-09-21--구현-오류는-닫혔고-큰-m의-replay-후보는-성립했다)).
> 따라서 Stage0c whole primitive를 열되 whole-step/TLinear/품질은 아직 `NOT_RUN`이다.

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
| **Stage0bWc ⚠️ 계측 미완결** | one-way inference pack vs training pack, M=1/16/128/1024/8192 정합·속도·peak allocation | 둘째 형상 M128의 elementwise 문턱 실패로 이후 행 생략; 측정 행은 모두 ≤0.790× | [082 §8](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#8-stage0bwc-wsl-inference-attribution2026-09-19--정합-문턱에서-중단-측정된-속도는-전부-음성) |
| **Stage0bWd ✅ 정합 PASS·속도 음성** | normalized RMS·max-abs/reference RMS·cosine으로 모든 행 완주 | 정합 전 행 PASS; decode 0.085~0.088×·prefill 최대 0.364×·전체 최대 0.820×로 inference 가속 음성 | [082 §9](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#9-stage0bwd-scale-aware-완주2026-09-19--정합-pass속도-음성) |
| **Stage0bWe ⚠️ 부분 유효** | wall-sync·CUDA Event·host enqueue·M1 padding·profiler·CUDA Graph를 같은 pack에서 분리 | 정합·wall/event/host/profiler 유효; graph는 pre-replay 비교 결함으로 전 행 무효 | [082 §11](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#11-stage0bwewf-실제-귀속2026-09-21--gpu-op-후보는-m8192뿐-host-wall은-전부-음성) |
| **Stage0bWf ✅ 부분 후보** | 공개 `_cslt_sparse_mm`의 `alg_id`·Split-K를 탐색과 확인 측정으로 분리 | M8192 event 1.244/1.390×, wall 0.778/0.841×; 비기본 alg tuning 이득 없음 | [082 §11](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#11-stage0bwewf-실제-귀속2026-09-21--gpu-op-후보는-m8192뿐-host-wall은-전부-음성) |
| **Stage0bWg ✅ graph 복구** | We의 graph pre-replay 결함만 M1/M8192 inference/training에서 재검증 | 8행 모두 OK; M8192 graph 1.400~2.342× 후보, M1 음성 | [082 §12](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#12-stage0bwg-cuda-graph-복구2026-09-21--구현-오류는-닫혔고-큰-m의-replay-후보는-성립했다) |
| **Stage0c 🔄** | dense vs 2:4 whole primitive forward/backward/pack-update | graph 후보가 전체 primitive에서 ≥1.10× 또는 메모리 가치를 남김 | 0.2 |
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

### 6.1 Stage0bWd preflight

| 점검 | 결과 |
|---|---|
| 독립변수 | 같은 WSL·dtype·K/N에서 sparse pack 종류와 M만 바꾸며 packing은 timing에서 제외 |
| registry 유사 런 | `check_run_registry --plan`에서 exact-2:4 inference decode/prefill 귀속 런 없음 |
| 태그 충돌 | Wc 로그는 보존하고 새 이름 `P025B_Stage0bWd_wsl_sparse24_inference_attribution` 사용 |
| 데이터·토큰 | 합성 kernel 진단이라 pool/tokenizer/steps 해당 없음; 학습 0 |
| 판정 | normalized RMS≤0.001, max_abs/reference RMS≤0.01, cosine≥0.999999; legacy elementwise assert는 경고. 정합 후 inference prefill M16~1024 중 하나가 ≥1.10×면 후보, 아니면 exit 8 음성 |
| 비용·자원 | 사용자 GPU 진단 약 0.1h, 단독 실행; 모델·체크포인트 없음 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 6.2 Stage0bWe/Wf preflight와 지시서 비판적 검토

| 항목 | 판정 | 근거·구현 경계 |
|---|---|---|
| wall-sync와 GPU 시간 분리 | 타당·구현 | 기존 두 진단은 반복마다 `perf_counter`+`cuda.synchronize`; 새 진단은 wall/event/host/profiler를 별도 열로 둔다 |
| CUDA Event=순수 GEMM | 부정 | padding·allocation·부가 kernel이 포함될 수 있어 `event_batch_ms`로만 표기하고 profiler 행만 kernel 귀속에 쓴다 |
| M=1→8 padding | 타당·구현 | local torch 2.10 `SparseSemiStructuredTensor._pad_dense_input()`의 FP16 dense 최소 행 8; M1 dispatch·명시 pad+slice·M8을 분리 |
| alg-id/Split-K | 부분 타당·구현 | `_cslt_sparse_mm` schema에 `alg_id/split_k/split_k_mode`가 있다. 다만 cuSPARSELt 0.8.0은 `get_max_alg_id()`가 `None`이라 지원 집합을 자동 확정할 수 없다. Wf는 보수적 0~4를 probe하고 unsupported를 기록 |
| 압축 재생성 | 현 공개 경로에는 불필요 | alg-id/Split-K는 기존 `packed`를 재사용한다. packing 시간은 별도 기록 |
| CUDA Graph=plan 재사용 | 부정·분리 | Graph replay는 launch/반복 경로 후보일 뿐 descriptor/plan 객체 재사용과 동일하지 않다 |
| 저수준 plan cache | 미구현 | NVIDIA C API에는 반복 실행 가능한 plan이 있으나 PyTorch public Python API는 plan handle을 노출하지 않는다. We에서 host/setup 병목이 확인될 때 C++ extension 별도 승인으로 연다 |
| dense→sparse 고정 순서 | 결함·교정 | 3 round에서 짝수는 선언 순서, 홀수는 역순으로 측정하고 median+MAD를 기록 |

공식 cuSPARSELt workflow는 descriptor·algorithm selection·plan·workspace 뒤 matmul을 반복하는
구조다. 이는 “재사용할 수 있다”는 C API 사실이지 현재 PyTorch wrapper가 이미 재사용한다는
증거가 아니다. 따라서 지시서의 “PyTorch가 매 호출 모두 구성·해제한다”는 주장은 local Python
surface와 공식 API만으로 확정하지 않고 **검증 가설**로 낮춘다.

독립변수: We는 측정 경로만, Wf는 같은 pack/input에서 alg-id/Split-K만 바꾼다. 데이터·토크나이저·
학습토큰은 합성 진단이라 해당 없음. search 측정은 최종 판정에 재사용하지 않는다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 7. 실행 진입점

- 무효 완료: `run_P025B_Stage0a_sparse24_backend-done.bat` — import 실패로 과학적 게이트 `NOT_RUN`([결과 082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)).
- 완료(Windows 역사): `run_P025B_Stage0b_sparse24_backend-done.bat` — 해당 runtime의 native
  cuSPARSELt 지원 불가로 음성 게이트 종료([결과 082 §6](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)).
- 무효(WSL, 콘솔 증거): `run_P025B_Stage0bW_wsl_sparse24_backend-done.sh` — one-way pack의
  dgrad 실패를 첫 backend matmul 실패로 오분류했다. **로깅 프로그램 코드 오류**로 원본 로그도 없다.
- 완료: `run_P025B_Stage0bWb_wsl_sparse24_training_pack-done.sh` — 정합성 PASS,
  M8192 training-pack 속도 음성([082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#현재-판정2026-09-19--stage0bwb-정합성-pass-훈련-형상-속도-음성)).
- 완료·계측 미완결: `run_P025B_Stage0bWc_wsl_sparse24_inference_attribution-done.sh` —
  elementwise 정합 문턱에서 exit 4, 이후 행 생략([082 §8](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#8-stage0bwc-wsl-inference-attribution2026-09-19--정합-문턱에서-중단-측정된-속도는-전부-음성)).
- 완료: `run_P025B_Stage0bWd_wsl_sparse24_inference_attribution-done.sh` — Wc false-negative를
  해소하고 전 행 정합 PASS·합성 inference 속도 음성을 확정했다.
- 완료·graph 부분 무효: `run_P025B_Stage0bWe_wsl_sparse24_path_attribution-done.sh` —
  wall/event/host/padding/profiler 유효, graph는 진단 구현 결함.
- 완료: `run_P025B_Stage0bWf_wsl_sparse24_algorithm_sweep-done.sh` — explicit alg-id/Split-K
  probe와 fresh confirmation. low-level event만 M8192 후보, wall과 algorithm tuning은 음성.
- 완료: `run_P025B_Stage0bWg_wsl_sparse24_graph_recovery-done.sh` — capture 뒤 첫 replay를
  보장하고 graph 8행을 전부 회수했다([082 §12](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#12-stage0bwg-cuda-graph-복구2026-09-21--구현-오류는-닫혔고-큰-m의-replay-후보는-성립했다)).
- 실행 대기: `run_P025B_Stage0cW_sparse24_whole_primitive.sh` — M8192에서
  forward+input-gradient+dense weight-gradient와 optimizer-step pack 비용을 accum16으로 상각해
  eager event/wall/graph을 분리한다.
- 미작성: Stage1a~Stage4와 Stage2i 학습 후 checkpoint end-to-end 추론. Stage0cW의
  전체 primitive가 음성이면 가속 분기를 자동 열지 않고 sparse-master 메모리 축을 별도 판정한다.

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
- 2026-09-19: Stage0bWc는 `(K,N,M)=(2048,768,128)`에서 elementwise tolerance가
  `max_abs=0.125`, RMS 0.0114로 실패해 exit 4였고 이후 형상을 생략했다. 측정 완료 행은
  모두 dense보다 느렸지만 전체 speed gate는 미완결이다. 절대오차를 출력 규모와 무관한
  단독 gate로 쓴 것과 fail-fast를 설계결함으로 분류해 Stage0bWd를 신설했다.
- 2026-09-19: Stage0bWd는 Wc 실패 행을 NRMS 0.000271·cosine 0.999999881로 통과시키고
  두 형상 전 행을 완주했다. 모든 sparse 호출이 dense보다 느려 이 runtime의 synthetic
  inference 가속 분기는 음성이다. sparse-master·whole-step·실제 checkpoint는 별도다.
- 2026-09-20: 사용자 후속 지시를 local torch 2.10 Python source와 공식 cuSPARSELt workflow에
  대조했다. M1 padding·계측분리·alg-id/Split-K·교차순서는 타당해 We/Wf로 구현했다. CUDA
  Graph와 plan reuse는 다른 최적화이며 public Python plan handle이 없으므로 후자는 선제 구현하지
  않았다.
- 2026-09-21: We 정합과 wall/event/host/profiler는 완주했다. M≤128은 sparse event가 dense의
  0.031~0.094×, M8192만 1.137~1.295×였고 wall은 전 행 0.084~0.831×로 음성이다. graph는
  replay 전 output 비교로 전 행 false failure라 Wg로 분리했다. Wf는 M8192 event 1.244/1.390×를
  보였지만 wall은 0.778/0.841×이고, 비기본 algorithm이 alg0를 이긴 후보는 없다. raw GPU-op
  후보를 TLinear/whole-step 후보로 승격하지 않는다.
- 2026-09-21: Wg는 graph 8행을 모두 `OK`로 회수했다. M8192 replay는
  1.400~2.342×로 빠르고 M1은 0.079~0.369×로 느리다. 일반 wall 음성은 불변이며
  실제 GPU whole primitive·TLinear·학습 병목은 Stage0c 전 `NOT_RUN`이다.
