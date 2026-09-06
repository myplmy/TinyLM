# PM001__MOONSHOT__TERNARY_TRITON_AND_SPARSE34_CPU_LUT

> 상태: **구현·정적 검증 완료 · Stage0/Stage1/Stage2 사용자 실행 대기**
>
> 실행 주체: 사용자. AI는 이 계획의 `.bat`, torch import, C++ 확장 빌드, CUDA, 모델
> forward/backward, 학습, 평가를 실행하지 않는다.

## 0. 격리와 목적

이 계획은 `moonshot` 브랜치의 PM 전용 계보다. 일반 `test_plan/`, `test_result/`,
`experiments.tsv`, 일반 W&B/체크포인트 namespace에 기록하지 않는다. main으로 merge·rebase·
cherry-pick·push하지 않는다. 성능이 별도 검증된 구성만 사용자가 나중에 main 작업에서 선택한다.

목적은 둘이다.

1. Windows에서 과거 삼진 Triton 실패가 라이브러리 문제였는지 구현 문제였는지를 증거로 분리하고,
   현재 사용자 Python 환경에서 실제 Triton 호출 여부를 폴백 없이 재검증한다.
2. 학습 경로에서 소비되지 않는 5-bit 패킹에 학습 가속을 잘못 귀속하지 않고, 그 포맷을 직접
   소비하는 3:4 전용 CPU LUT 추론 커널을 만든다.

## 1. 기존 증거의 결론

### 1.1 Triton: Windows 라이브러리 장애가 아니라 구현·통합 결함이었다

`test_result/003_20260725001000_P014-커널-어닐버그.md`와 당시 사용자 로그가 정본이다.

| 관측 | 원인 | 판정 |
|---|---|---|
| 최초 reference loss 불일치 | kernel이 `wq + (1-a)(w-wq)` anneal을 누락 | **구현 오류** |
| anneal=1 도달 시 JIT 실패 | `tl.arange(0,G)`의 `G`를 runtime arg로 전달 | **구현 오류** (`tl.constexpr` 계약 위반) |
| 수정 후 k_triton loss 9.3181 | k_off 9.3181, k_ref 9.3169, fallback 경고 0 | Windows에서 **Triton 실제 컴파일·실행 성공** |
| `--compile` 동반 5~7초/step | Python anneal guard로 Dynamo 재컴파일 폭주 | **통합 오류** |
| compile 제거 160~250ms/step | tiny baseline과 큰 차이 없음 | 10배 지연은 Triton library 일반 실패가 아님 |

따라서 과거 증거로는 “Windows라 Triton이 작동하지 않았다”가 기각된다. 다만 현재 Codex
interpreter에는 torch/Triton/MSVC/Ninja가 설치돼 있지 않고, 사용자가 `.bat`을 실행하는 Python과
동일 환경이라는 보장이 없다. Stage0가 **현재 사용자 interpreter**를 다시 판별한다.

### 1.2 5-bit 패킹은 학습시간을 줄이지 않는다

사용자 신규 스모크 `202609061405_smoke_fdce364.txt`에서 `diag_sparse34_pack.py`는
1,000,000가중치 왕복 불일치 0, tail/codebook 통과, 정확히 1.250000bpw, 잘못된 입력 거부를
모두 통과했다. 이는 저장 포맷의 동적 증거다.

하지만 학습은 `_TernarySTE`가 3:4 mask를 만든 뒤 dense `F.linear`를 호출한다.
`pack_sparse34()` 호출자는 배포 진단뿐이고 train forward에는 없다. 기존 같은-g 실측도
sparse34가 약 `+0.6%`였으므로, 5-bit 패킹 버그 수정은 **학습시간 단축에 기여할 호출기회가 0**이다.
이 조건이 성립했으므로 사용자 지시 (2)에 따라 CPU LUT 커널로 진행한다.

## 2. 구현안 비교와 선택

| 안 | 장점 | 한계 | 선택 |
|---|---|---|---|
| A. PyTorch `einsum+gather` | 이식·검증 쉬움 | gather/copy 물질화, 기존 profile에서 LUT가 fp32보다 느림 | 정확성 oracle만 |
| **B. PyTorch C++ 지연 확장** | packed 직접 소비, PyTorch tensor ABI, 소스 단위 이식 용이 | 사용자 PC에 C++ toolchain 필요 | **선택** |
| C. 사전 빌드 DLL/ctypes | 배포 시 compile 불필요 | Python·Torch·MSVC ABI별 binary 관리 필요 | 보류 |

선택 B는 `native`와 `reference` backend를 명시적으로 나눈다. native 빌드나 호출이 실패하면
reference로 조용히 떨어지지 않는다. 빌드 실패와 느린 커널을 같은 결과로 기록하지 않기 위해서다.

## 3. 3:4 CPU LUT 수학·메모리 계약

4개 가중치에 0이 정확히 하나이고 나머지 셋은 부호이므로 상태 수는
`4 * 2^3 = 32 = 2^5`다. code는 `zero_pos * 8 + sign_bits`이고 8 code를 5바이트에 담는다.
`1.25bpw`는 **code stream만**의 값이다. g128 fp32 alpha는 가중치당 `32/128=0.25bit`를
추가하므로 행 tail이 없는 대표 shape의 영구 상주는 합계 `1.50bpw`다. latent나 `(O,I)`
int8/fp32 복원 사본은 포함하지 않지만 호출 중 활성 LUT workspace는 별도로 센다.

입력 4블록 `x_j`마다 32개 값을 한 번 만든다.

`LUT[j,c] = sum_{k=0..3} pattern[c,k] * x[j,k]`

출력행의 packed code를 직접 읽어 `LUT[j,code[o,j]]`를 조회하고, `micro_group/4` 블록마다
학습 당시 alpha를 곱해 누산한다. 일반 g=5 LUT와 달리 4가 128을 나누므로 per-row alpha
재추정이 없고 g128 scale을 보존한다.

대표 I=768에서 활성 LUT 항목은 `(768/4)*32 = 6,144`개다. 일반 g=5는
`ceil(768/5)*243 = 37,422`개로 약 6.09배다. native workspace는
`B * (I/4) * 32 * 4 bytes`; B=1, I=768이면 24KiB다. 이것은 영구 상주가 아닌 호출 중
활성 workspace다.

## 4. 구현 경계와 main 이식 단위

| 단위 | 파일 | 책임 |
|---|---|---|
| Triton 계약 | `ternary_kernel.py`, `config.py`, `trainer.py`, `cli.py` | import/launch 원인 분류, backend counter, strict 실패, 죽은 단독 flag 거부 |
| 3:4 행 포맷 | `lut.py` | 행 경계를 보존한 pack/unpack, 5-bit code decode |
| native CPU kernel | `sparse34_cpu.py`, `csrc/sparse34_lut_cpu.cpp` | 지연 빌드, 32-state LUT, packed 직접 decode, g128 alpha |
| 모델 연결 | `ternary.py`, `transformer.py`, `infer/generate.py` | 비가역 배포 변환, latent 제거 강제, 상주 회계 |
| 검증 외피 | `diag_pm001_*.py`, `moonshot_batch/run_PM001__*` | 사용자 실행 계약·benchmark |

핵심 native 모듈은 PM000 알고리즘이나 일반 훈련 로직을 import하지 않는다. main에서 채택할 때
위 단위를 순서대로 검토할 수 있고, PM 문서·배치는 가져가지 않아도 된다.

## 5. Stage0 — 현재 Windows Triton strict 계약

배치: `moonshot_batch/run_PM001__MOONSHOT__Stage0_triton_contract.bat`

합성 CUDA 텐서로 fp32와 bf16을 각각 검사한다.

| 게이트 | 사전 기준 |
|---|---|
| T0 | 해당 Python에서 Triton import 성공, CUDA 사용 가능 |
| T1 | anneal=0.5 reference output/x-grad/w-grad 상대오차 FP32 `<1e-5`, BF16 `<5e-3` |
| T2 | anneal=1 Triton `attempts>=1`, `successes>=1`, `fallbacks=0` |
| T3 | Triton output/x-grad/w-grad 상대오차 `<5e-3` |

실패 로그의 범주는 `environment_import`, `device_contract`,
`implementation_compile_contract`, `compile_integration`, `environment_runtime`,
`runtime_unknown` 중 하나다. 범주는 자동 결론이 아니라 조사 라우팅이다. strict라 실패한 호출은
reference PASS로 바뀌지 않는다.

## 6. Stage1 — 3:4 native CPU 정확성·통합 계약

배치: `moonshot_batch/run_PM001__MOONSHOT__Stage1_sparse34_cpu_contract.bat`

최초 호출에서 C++ 확장을 빌드한다. 체크포인트와 학습 데이터는 사용하지 않는다.

| 게이트 | 사전 기준 |
|---|---|
| C1 | 행별 pack 왕복 불일치 0, 정확히 1.250000bpw |
| C2 | PyTorch 32-state reference vs dense 상대오차 `<3e-5` |
| C3 | native build 성공, native vs dense/reference 모두 `<3e-5` |
| C4 | TLinear 변환 후 latent·`_wq`·`_i8` 없음, packed forward 사용 |

Stage1 PASS는 현재 toolchain에서 빌드와 수학·호출경로가 맞다는 뜻뿐이다. 속도 증거가 아니다.

## 7. Stage2 — CPU microbenchmark

배치: `moonshot_batch/run_PM001__MOONSHOT__Stage2_sparse34_cpu_benchmark.bat`

Stage1 PASS 뒤 실행한다. shape `768x768`, `2048x768`, `768x2048`, 행수 M=1/8에서 median
ms/call을 잰다. C++ build 시간은 제외하고 다음 세 경로를 같은 호출에서 비교한다.

- fp32 dense weight가 이미 상주한 `F.linear`
- 일반 1.6bpw g=5 PyTorch LUT
- 신규 1.25bpw 3:4 native CPU LUT

Stage2 자체는 느리다는 이유로 비정상 종료하지 않는다. 관측 후 다음처럼 판정한다.

- native가 일반 g=5 LUT보다 느리거나 비슷하면 구현 최적화 대상으로 남긴다.
- M=1 대표 3 shape에서 native가 dense를 일관되게 이기지 못하면 **속도 채택 근거 없음**이다.
- microbenchmark 승리만으로 모델 채택하지 않는다. 실제 sparse34 checkpoint를 고른 뒤 별도
  end-to-end cached decode에서 tok/s, RSS/peak, 출력 정합성을 함께 재야 한다.

## 8. Stage3 — 실제 모델 end-to-end (HOLD, 배치 없음)

Stage1 정확성과 Stage2 유의미한 신호가 모두 있어야 계획을 갱신한다. 어느 sparse34 checkpoint를
쓸지는 현재 요청에서 정해지지 않았고, 모델 로드는 사용자 실행 경계이므로 미리 배치를 만들지 않는다.
성공 조건은 matched CPU 세션에서 일반 LUT 대비 tok/s 개선, 1.25bpw 상주 유지, 결정적 출력
허용오차 통과를 동시에 만족하는 것이다.

## 9. Preflight

**독립변수**: Stage0는 동일 삼진 수학에서 strict Triton backend 실제 사용 여부, Stage1/2는 동일
3:4 가중치에서 실행 backend와 packed 형식만 바꾼다.

| 항목 | 판정 | 근거 |
|---|---|---|
| 학습토큰·데이터 풀·교사 | N/A | 학습·데이터·checkpoint 0 |
| 태그·체크포인트 덮어쓰기 | 통과 | tag와 checkpoint를 만들지 않음 |
| 중복 | 통과 | 기존 P014는 packed 3:4 native CPU kernel과 strict telemetry가 없음 |
| 비교 유효성 | 통과 | 각 script 한 process 안의 동일 합성 tensor·shape |
| 자원 | 경고 | Stage1 최초 C++ build 시간·RAM은 별도 기록, latency에서 제외 |
| 판정 가능성 | 통과 | T0~T3, C1~C4를 결과보다 먼저 고정 |
| 실행 권한 | 통과 | AI 미실행, 사용자 `.bat` 실행만 |

**중단 사유**: 없음. Stage0와 Stage1은 서로 독립 진단이나 권장 순서는 Stage0→Stage1→Stage2다.

**경고**: 이 plan은 학습 가속 실험이 아니다. native kernel이 느리면 포맷 정확성 PASS와 속도 FAIL을
분리한다. 현재 interpreter/toolchain 차이는 Stage 로그 안의 실행파일·버전·compiler 탐지로 판단한다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 10. 실행 순서와 결과 작성

1. `run_PM001__MOONSHOT__Stage0_triton_contract.bat`
2. `run_PM001__MOONSHOT__Stage1_sparse34_cpu_contract.bat`
3. Stage1 PASS일 때만 `run_PM001__MOONSHOT__Stage2_sparse34_cpu_benchmark.bat`
4. 사용자가 로그를 전달하면 `moonshot_result/PM001__MOONSHOT__...__RESULT.md`에 분석한다.

로그 파일 존재나 exit 0만으로 성능 향상을 선언하지 않는다. backend telemetry, 오차, shape별
median과 메모리 회계를 함께 읽는다.

## 11. 구현 시점 정적 검증 상태

2026-09-06 AI가 torch를 import하지 않는 범위에서 다음을 통과했다.

- 변경 Python 파일 `py_compile`, `git diff --check`
- PM namespace, config attribute, flag-used, import-name, call-kwargs, flag whitelist
- 진단 데이터 계약, PM001 배치 3개의 CRLF/린트

전체 `check_static_all.py --quiet`은 32종 중 29종 통과, 기존 범위 밖 3종 실패다. held-out D6
`E-157/E-205`, 사용자 smoke 산출 런 `dense`의 일반 registry 미등재, 로컬 data-cache 문서 링크
5건 결손이며 PM001 신규 코드가 만든 실패는 아니다. 그렇더라도 branch 전체 green이라고 부르지 않는다.

AI 실행 interpreter `C:\Python311\python.exe`에는 torch, Triton, triton-windows, Ninja가 없고
`cl`도 PATH에서 발견되지 않았다. 사용자의 `.bat` Python과 같은 환경이라는 보장이 없으므로 이 관측으로
사용자 환경의 라이브러리 상태를 판정하지 않는다. C++ 빌드, native 수치, 실제 Triton launch와 성능은
각각 Stage1, Stage0, Stage2의 사용자 실행 전까지 **PENDING**이다.
