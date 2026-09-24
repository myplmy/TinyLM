# P104A — 외부 flash-attn 제외 M4와 M5 소형 dense 교량의 기능 게이트

> 제안 계기: [WSL 이관 제안서](../proposal/20260915_WSL2-Linux-학습환경-단계적-이관-제안서-approved-on-going.md) M4/M5와 사용자 승인. **2026-09-25 현재 Windows Stage1B는 모델 전 Z 드라이브/UNC 경로 오류 exit1; 교정 Stage1Bb는 STATIC_ONLY, Windows/WSL 기능 교량·전체 품질 NOT_RUN.**

## 1. 왜 — backend 지원과 환경 교량을 동적 증거로 구분한다

M4는 torch/CUDA/cuDNN·cuSPARSELt·FP8·PyTorch SDPA·Triton 각각의 import, 실제 호출, 수치 정합, 메모리 계측을 분리한다. [결과082](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md), [081](../test_result/081_20260913_P022C-FP8-backend는-통과했지만-학습이득은-미측정이다.md), [088](../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md)은 부분 실제 증거다. 외부 flash-attn distribution은 **사용자 지시로 이번 M4 범위에서 제외**하지만 PyTorch FLASH SDPA는 남긴다. opt-in Triton 삼진 커널은 코드가 예외를 잡아 reference로 폴백하므로 **직접 호출 확인**이 새 gate다.

M5는 같은 checkpoint에서 Windows와 WSL의 값·시간·VRAM을 분리해야 한다. 이번 소형 dense는 통합 기능 control이지 과거 실험의 품질 이관 완료가 아니다.

## 2. 질문

| # | 질문 | 판별 근거 |
|---|---|---|
| Q1 | WSL Triton 삼진 GEMM이 fallback 없이 실제 실행·정합·peak memory 출력을 내는가 | direct kernel call과 reference NRMS/cosine, allocated |
| Q2 | 양 OS에서 같은 tiny dense checkpoint·코드·입력으로 forward/한 업데이트가 유한한가 | JSON의 SHA와 CE·grad, 별도 종료코드 |
| Q3 | 소형 gate로 M5 전체를 닫을 수 있는가 | 아니오. real checkpoint·검증 풀의 same-condition 품질 별도 |

## 3. 예측 — 성공과 실패

Triton 커널은 sm89에서 direct 호출될 수 있지만 fp32 dot 제약·TF32 수치 차이로 불가/수치 음성이 나올 수 있다. 실패해도 PyTorch 일반 학습 경로가 실패한 뜻은 아니다. 같은 tiny checkpoint의 두 OS loss는 가깝겠지만 CUDA/cuDNN 차이로 비트 일치는 요구하지 않는다. synthetic 한 업데이트로 한국어 품질·과거 모델 순위는 검증할 수 없다.

## 4. 단계 설계

### 단계 0 — 정적·입력 gate

[진단](../scripts/diag_m4_triton_ternary.py)의 --check-only와 [M5 수집기](../scripts/diag_m5_dense_bridge.py)의 --check-only, [비교기](../scripts/check_m5_dense_bridge.py)의 --self-test를 실행한다. 모델·GPU는 0. 두 OS 모두 같은 tracked code SHA와 tiny checkpoint 파일을 사용해야 한다.

### 단계 1 — M4 WSL direct Triton, 사용자 실행

[WSL SH](../run_P104A_Stage0W_m4_triton_ternary.sh)에서 M64/K768/N768/G128의 reference 대 직접 Triton 호출, NRMS≤0.02, cosine≥0.999, CUDA peak allocated를 기록한다. 미설치/미지원은 exit2, 실행됐지만 정합 문턱 실패는 exit8로 구별한다. 이 gate는 다른 M4 축의 역사 수치와 합쳐야 하며, 훈련 whole-step 가속 판정이 아니다.

### 단계 2 — M5 같은 tiny checkpoint의 Windows/WSL 소형 dense 교량

[교정 Windows Stage1Bb BAT](../run_P104A_Stage1Bb_m5_dense_bridge.bat)를 먼저, [WSL SH](../run_P104A_Stage1W_m5_dense_bridge.sh)를 나중에 사용자 실행한다. 둘 다 `runs/ckpt/tiny_synthetic_2M_dense.pt`를 읽고 서로 다른 `runs/bench/p104a_m5_*.json`을 새로 쓴다. 입력은 CPU seed104 고정, 같은 checkpoint와 code SHA를 비교기가 강제한다. 업데이트 전·후 평가 CE, 훈련 전 CE/gradient norm, 업데이트된 실제 파라미터 한 좌표의 절댓값 변화, 평가 wall, peak allocated/reserved를 분리 기록한다. 여기서 SGD는 **교량 기능 control**이며 표준 Muon 학습의 품질 대조가 아니다.

### Stage1B — Windows 소형 dense 수집

사용자 Windows BAT가 같은 tiny checkpoint에서 기능 수치·환경 서명을 먼저 기록한다. V2 JSON에는 optimizer가 실제 바꾼 좌표와 업데이트 후 평가 CE가 반드시 포함된다. 기존 JSON이 있으면 중단하며 자동 덮어쓰지 않는다.

### Stage1Bb — Windows 드라이브/UNC 별칭 교정 재실행

2026-09-24 Stage1B는 CUDA·모델 계산 이전에 `Path(__file__)`의 `Z:` 표기와 `ROOT=Path(__file__).resolve()`의 WSL UNC 표기를 `relative_to`로 섞어 `ValueError` 종료코드1이었다. 수집기의 코드 SHA 키를 명시한 저장소 상대 이름으로 고정하고 모든 파일을 동일 ROOT에서 구성했다. 순수 Windows 드라이브·UNC·POSIX 경로 fixture는 PASS지만 Windows 실제 실행은 `NOT_RUN`이다. 별도 Stage1Bb BAT로 동일 tiny checkpoint/seed104·write-once Windows JSON을 새로 생성하며, 그 성공과 동반 WSL Stage1W 뒤에만 M5 소형 기능을 판정한다. 기존 Stage1B 로그는 실패 이력으로 보존한다.

### Stage1W — WSL 소형 dense 수집·대조

사용자 WSL SH는 Win JSON 존재를 선결로 확인하고 WSL 값을 기록한 뒤 둘의 hash·CE·gradient 차이를 판독한다. 어느 쪽도 Codex가 대신 실행하지 않는다.

### 단계 3 — 전체 M5 품질 교량, 별도 승인과 사용자 실행

same real checkpoint·같은 tokenizer·같은 평가 풀·condition signature로 Windows/WSL paired 품질을 측정한다. 그 계열의 실제 ruler가 없거나 양쪽 자산 hash가 다르면 M5 품질 판정은 `NOT_RUN`이다. 소형 synthetic Stage1만으로 WSL 제안서를 닫지 않는다.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| Stage1 direct Triton 미호출·CUDA 미지원 | UNSUPPORTED/NOT_RUN. reference fallback 성공을 direct PASS로 승격하지 않음 |
| Stage1 수치/peak 모두 기록, 문턱 통과 | 해당 형상의 M4 Triton 기능 PASS; 속도·whole model은 미판정 |
| Stage2 checkpoint/code/input SHA 불일치 | 비교 무효·exit2, 다시 같은 파일/commit에서 실행 |
| Stage2 업데이트 전·후 평가 CE 또는 train CE 절대차>0.01, grad norm 상대차>0.10 | 소형 기능 gate 음성 exit8. 이 수치는 과학적 ruler가 아닌 사전 기능 허용치 |
| Stage2 실제 파라미터 좌표 변화가 0 또는 비유한 | optimizer no-op/실행 오류. V2 수집은 결과 JSON을 쓰지 않고 중단하며 비교기는 exit8/2로 분리 |
| Stage2 통과 | 소형 기능 bridge PASS. M5 real-checkpoint 품질·환경별 속도/VRAM 기준은 여전히 미완 |

## 6. 비용

| 단계 | 예상 | GPU |
|---|---:|---|
| 0 정적 검사 | 0.02h | 없음 |
| 1 M4 Triton direct | 0.1h | 사용자 WSL 1회 |
| 2 M5 tiny dense 양 OS | 각 0.1h 내외, 총0.2h | 사용자 Windows/WSL 각1회 |
| 3 real checkpoint 전체 M5 | 2~4h 별도 재산정 | 별도 승인 |

## 7. 실행 파일과 로그

- `run_P104A_Stage0W_m4_triton_ternary.sh` → 결과번호095의 Stage0W 로그.
- 원본 실패 [Stage1B BAT](../run_P104A_Stage1B_m5_dense_bridge-done.bat)는 보존하고, 현재 재실행은 [Stage1Bb BAT](../run_P104A_Stage1Bb_m5_dense_bridge.bat) / [WSL Stage1W SH](../run_P104A_Stage1W_m5_dense_bridge.sh) 순서다. 플랫폼별 V2 JSON은 기존 출력이 있으면 중단하며 자동 덮어쓰지 않는다.
- 사용자가 실제 실행하기 전 상태는 `E2E_NOT_RUN`. 전체 WSL 제안서 종료는 M4 범위별 실제 판정, M5 실제 품질 교량, 사용자 최종 정본 승인까지 필요하다.

## 8. 한계

외부 flash-attn은 사용자 지시에 따라 제외했고 앞으로 미검증으로 남는다. P025B·FP8·SDPA의 역사 결과는 일부 음성이며 Triton PASS가 이를 뒤집지 않는다. Stage1의 synthetic tiny 모델은 언어 품질·데이터 풀·체크포인트 이동성을 판정하지 않는다. GPU/모델 실행은 Codex가 하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-24: 사용자 승인으로 Stage0/1 구현·런처 준비. CPU 비교기 fixture는 PASS, Windows/WSL GPU 로그 `NOT_RUN`.
- 2026-09-24: 사용자 승인으로 Windows 단계 `Stage1Win`을 `Stage1B`로 개명했다. M5 진단은 업데이트 호출뿐 아니라 실제 파라미터 변화와 후 평가 CE를 V2 JSON으로 기록하도록 보강했다. 소형 checkpoint 실제 실행은 여전히 `NOT_RUN`.

- 2026-09-25 사용자 로그 회수: [결과095](../test_result/095_20260925_P104A-Windows-M5-드라이브-UNC-별칭오류.md)의 Windows Stage1B는 모델 전 `Z:`/UNC `relative_to` ValueError로 exit1이었다. 양 OS CE가 가깝다는 §3 예측은 **시험되지 않았다**. 코드 SHA 키를 동일 ROOT의 명시 상대 이름으로 만들고 Windows 드라이브·UNC·POSIX 순수 경로 fixture PASS; 사용자 Stage1Bb 실제 Windows E2E는 `NOT_RUN`. 원 BAT는 -done 실패 이력, 새 `run_P104A_Stage1Bb_m5_dense_bridge.bat` 성공 뒤 기존 Stage1W와 대조한다. 소형 PASS여도 전체 M5 품질은 남는다.
