# 제안 — 회전 삼진·민감 부위·직접 패킹을 기존 TinyLM 음성 결과와 단계별로 대조한다

> **작성** 2026-09-25 · **상태** 🔄권장 B안 승인 후 진행 중 · **분류** 실험계획 / 배포구조
> 양식: [proposal/README.md](README.md) §3. [Bonsai 2 분석 §7.1~7.3](../docs/methods/08_paper_review2.md)과 [Hadamard·삼진 선행연구 조사](../docs/20260925_Hadamard-회전과-삼진화-선행연구-적용성-조사.md)를 근거로 한 **실험 제안**이다. 사용자 승인 전 새 모델 경로·캐시·학습 런처는 만들지 않는다.

## 1. 배경 — 왜 지금 이 제안을 하나

우리 [P014D 결과069 §11](../test_result/069_20260902_P014D-디코드-프로파일이-경로이름을-양자화형식으로-넘겨-두-팔-다-죽었다.md)에서 scalar native LUT의 실제 모델 CPU decode native/int8은 1.314×/1.231×로 기존 1.50× 채택선 미달이다. [P025B 결과082 §13](../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md)은 M8192 primitive CUDA event 1.334×/1.377×에도 동기 wall 0.959×/0.926×로 음성이다. 두 결과는 포맷·하드웨어가 달라 합쳐서 하나의 속도 결론을 낼 수 없다. Bonsai 2 백서의 group128 삼진·고정 Hadamard·고정밀 예외·packed 직접 실행은 병목 위치를 다시 물을 설계 단서이지 이 음성을 뒤집은 실측이 아니다.

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

같은 TinyLM checkpoint·토크나이저·입력·평가 조건에서 **(i) 패킹/호출 비용, (ii) 고정 회전의 삼진 재구성 손익, (iii) 제한된 고정밀 예외의 품질 대가**를 별도 독립변수로 측정하고, 실제 CPU 상주·decode p95와 GPU whole-step에 순이득이 있는지만 판정한다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태·판정 범위 |
|---|---|
| 기존 P014D/P025B 병목 분해표 | 같은 형상의 입력변환·pack/unpack·GEMM·host wall·CUDA event/graph와 CPU decode를 분모별로 나눈 로그. 기존 음성값 보존 |
| 층별 삼진 민감도 | TLinear g128의 zero율/scale·weight 및 activation outlier, 무회전/3×256/1024-pad 재구성 오차와 exact FP64/FP32 동치 표 |
| 선택적 예외 회계 | 사전 지정 TLinear/embedding/norm의 FP16/BF16 예외마다 추가 저장 byte·실제 runtime/RSS·품질. Bonsai의 0.0976%는 문턱으로 사용하지 않음 |
| 짝 평가 | 동일 checkpoint·same raw crop·seed에서 full-val와 한국어/영어 형식·정답, 배포 packed/상주/KV·CPU single-core decode p50/p95 |
| 승격/중단 보고 | 채택 조건 실패·비교 무효·NOT_RUN을 별도로 둔 결과문서 및 기존 P014D/P025B와의 차이 |

실험 번호는 이 제안 승인 뒤 `test_plan/실험계획목록.md`를 전수 감사해 suffix로 배정한다. 이 문서에 가상의 `run_P*.sh`를 권장 실물로 적지 않는다.

## 4. 비용

| 항목 | 양과 범위 |
|---|---|
| GPU | 지금 **0h**. 승인 뒤 무학습 동일 checkpoint 수치/메모리 gate ⚙0.2~0.5h, 실제 품질·whole-step 또는 조건부 100M 팔은 gate 통과 뒤 추가 ⚙2~4h로 다시 산정 |
| AI 작업 | gate·독립 fixture·결과 연쇄 구현 ⚙4~8h, 기존 TLinear/default 변경 없음 |
| 사용자가 직접 해야 하는 일 | 정확 checkpoint·평가 pool/권리·회전 seed/예외 tensor 예산 선택, GPU·CPU 실제 실행과 로그 회신 ⚙0.5~1h 감독 |
| 디스크 | 원본 cache/checkpoint 보존; 실험 전 새 packed/진단 사본 ⚙0.5~2GiB 예산 상한 검증. 원본 덮어쓰기 0 |
| 네트워크·보호 데이터 | 기본 0GB. 새 다운로드·`datasets/TinyDataset/**` 접근 0건, 필요 시 별도 승인 |

## 5. 원리·근거

**우리 실측:** P014D의 actual CPU decode는 현재 scalar LUT 경로의 유효 음성이고, P025B는 CUDA GPU work 이득과 host wall 손실이 동시에 참이다. 따라서 packed byte 또는 합성 event 하나만으로 배포 채택을 선언하지 않는다. TinyLM [`TLinear`](../tinylm/model/ternary.py)의 g128 alpha/STE와 기존 3:4는 Bonsai의 PTQ1_0 또는 cuSPARSELt 2:4와 다르다.

**외부 근거:** [Bonsai 2 백서](https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-2-27b-whitepaper.pdf) §2~3은 block1024 고정 회전과 packed 직접 커널을 기술한다. [QuaRot](https://arxiv.org/html/2404.00456) §3~4와 [QuIP#](https://arxiv.org/html/2402.04396) §3은 직교/무작위 Hadamard의 4/2~4-bit PTQ 원리를, [SpinQuant](https://arxiv.org/pdf/2405.16406) §2~3은 회전 seed 변동을 보인다. [CAT-Q](https://arxiv.org/pdf/2606.26650) §2·§3.4의 softened ternarization은 FP pretrained 대형모델 PTQ이며 TinyLM QAT에 즉시 복사할 수 없다. 각 원문의 적용 한계는 위 조사보고서가 소유한다.

## 6. 방법 — 싼 증거가 비싼 단계를 연다

| 단계 | 무엇을 고정·변경하나 | 비용 | 다음으로 가는 조건 |
|---|---|---:|---|
| G0 무학습 수학·회계 | 같은 weight/input에서 R 없음/3×256/1024-pad의 `RᵀR=I`와 회전+역변환, g128 quant 전후 오차; 다른 코드 경로 기본 off | GPU0, ⚙0.1h | FP64 실수 동치와 FP32 허용 오차, pad/seed/부위별 추가 byte를 사전 기준으로 검증. 실패하면 회전 중단 |
| G1 기존 병목 | P014D CPU M1과 P025B M1/M8192의 현 코드·같은 분모 복측정; unpack·온라인 회전·kernel·동기 wall 분리 | 사용자 CPU/GPU ⚙0.2~0.5h | 단일 CUDA event 양성이 아니라 실제 대상 wall·상주 이득 가능 위치가 보여야 G2 |
| G2 고정 회전·예외 분리 | 같은 checkpoint의 무회전·부호회전 3×256·1024-pad, 예외 off/사전선정 on을 **각각** 단독 대조. seed≥3 사전 고정 | 사용자 GPU/CPU ⚙0.5~1h | 정합·full-val/공통 과제 비퇴행과 CPU p95/상주 순이득. 조건 불일치 시 `DESCRIPTIVE_ONLY` |
| G3 조건부 학습/커널 | G2 양성일 때만 learnable rotation 또는 CAT-Q식 threshold/softening 중 **하나**와 직접 packed 커널을 별도 suffix로 검토 | 사용자 GPU ⚙2~4h+ | 기존 기준표의 계열별 자·동일 토큰/풀/optimizer·실제 배포 지표로 재판정 |

먼저 정확한 실물 계획·preflight를 쓰고 그 단계가 **지금 실행 가능할 때만** 사용자용 SH를 만든다. teacher G0/A0와 이 제안의 회전 G0는 서로 다른 연구축이며 결합하지 않는다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 7. 거절하면 못 하는 것

기존 P014D/P025B 음성·TLinear 기본 경로와 별도 SFT/교사 실험은 그대로 유지된다. 다만 Hadamard/선택 예외가 우리 g128 삼진 구조에서 품질·CPU wall 손익을 개선하는지 알 수 없고, Bonsai의 성공 요인을 TinyLM의 재현 가능한 원인으로 분해하지 못한다. 따라서 거절은 현재 운영을 막지 않는다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 잘못된 회전 동치 | `WRᵀRx`를 양자화 뒤에도 exact라 간주; tied head/CLA/RoPE 경계에서 함수 변화 | FP64 원 수학→FP32→g128 삼진 순서로 분리, layer-local부터 시작 |
| 계측 분모 혼선·온라인 transform이 decode를 지배 | M1에서 Hadamard/padding wall이 GEMM 절감보다 큰데 순수 GEMM event만 인용 | CPU p95·GPU 동기 wall과 event를 각각 기록, 회전·pack 비용을 반복 호출에 포함 |
| 고정밀 예외 메모리 누락 | packed bpw만 보고 scale/회전/예외/KV/RSS를 빼먹음 | 실제 runtime/RSS·KV/컨텍스트·byte 단위 분리, 40MiB 목표는 상주로 판단 |
| seed 선택 편향·과최적화 | 양성 seed 하나만 골라 보고 | 사전 고정≥3 seed·실패/음성 전부 기록, sealed 평가를 선택 과정에서 사용 금지 |
| 논문·백서 성능 전이 오해 | 27B/4-bit PTQ 수치를 약100M/QAT/CPU 예상 speedup으로 복사 | 출처별 구조·언어·GPU/CPU·측정 분모와 본 제안 `NOT_RUN` 병기 |
| 사용자 자산 간섭 | 새 cache/packed 사본이 원본을 덮거나 진행 중 큐가 읽는 파일을 교체 | 별도 이름·write-once·정확 SHA, 원본 불변, Codex GPU/모델 실행 금지 |

## 9. 대안

| 안 | 내용 | 장점 | 단점·영향도·수행비용 |
|---|---|---|---|
| A | 기존 native LUT·2:4의 분모와 병목만 재측정하고 회전은 보류 | 기존 음성의 이유를 낮은 비용으로 선명하게 함 | 품질 개선 아이디어는 시험하지 않음; 코드 영향 낮음, ⚙1~2h |
| **B** | A를 선결로, layer-local 고정 회전/선택 예외를 독립 arm으로 검증 | 구조 원인과 배포 손익을 분리해 결론 가능 | 별도 진단·CPU wall·품질 평가 필요; 영향 중간, AI⚙4~8h+사용자 gate |
| C | 학습형 회전·soft ternarization과 새 커널을 처음부터 통합 | 성공 시 큰 구조 개선 여지 | 교락/디버그/모델 재학습 부담 큼; 영향 높음, 비용·검증력 미산정 |

### 권장안과 근거

**B를 조건부 권장**한다. G0/G1이 먼저 실패하면 실제 배포 이득 경로가 없으므로 G2/G3로 진행하지 않는다. 학습형 C는 기존 삼진 QAT·Muon·WD·데이터를 바꾸는 별도 결정을 필요로 한다. 승인 전에는 새로운 `test_plan` 번호·실험 SH·기본 모델 플래그를 만들지 않는다.

### 2026-09-25 승인·착수 범위

사용자가 권장 B안을 승인했다. [P014E 계획](../test_plan/P014E_회전삼진-민감도와-직접패킹-단계게이트.md)과 독립 CPU G0 진단기·WSL SH를 만들었다. G0의 12행 합성 자체시험은 통과했지만 사용자 SH E2E·실제 checkpoint 민감도·CPU/GPU 속도·full-val은 `NOT_RUN`이다. G1은 같은 checkpoint 선택과 G0 사용자 로그, G2는 G1의 실제 wall/상주 가능 위치, G3는 G2의 품질·배포 순이득이 선결이다. 기본 TLinear·데이터·optimizer·P014D/P025B 역사 판정을 바꾸지 않았다. 이 미완료 조건 때문에 제안서는 `-approved-on-going`으로 유지한다.
2026-09-25 후속 상태: 사용자 P014E G0 결과099의 합성 12행은 exit0·문턱 PASS다. 위 승인·착수 단락의 사용자 SH E2E NOT_RUN은 작성 당시 이력으로만 읽는다. 실제 checkpoint의 G1 CPU wall/RSS, G2 품질·상주, G3 조건부 검증은 여전히 NOT_RUN이므로 done 이관하지 않는다.
