# P094 — Muon 저정밀 shadow Q/R residual과 동적 정밀도

> **승인 2026-09-18.** 권장안 A를 조건부 연구 경로로 승인했다. 정본 제안서:
> [`20260916_Muon-저정밀-shadow-residual-동적정밀도와-배치환원-제안서-approved-on-going.md`](../proposal/20260916_Muon-저정밀-shadow-residual-동적정밀도와-배치환원-제안서-approved-on-going.md)
>
> **현재 상태:** R0 dependency gate는 사용자 실행에서 예상한 exit8 HOLD를 반환했다
> ([결과 089](../test_result/089_20260919_P094-P022C-shadow-evidence가-없어-residual은-HOLD다.md)). P022C의 실제 packed/masterless low-shadow 출구조건이 충족되지 않았으므로
> R1 residual 구현·모델 로딩·GPU·품질은 `NOT_RUN`이다.

## 1. 왜 — low shadow의 실패와 실제 메모리 절감을 분리한다

[P022C](P022C_FP8-compute-shadow-precision-분리.md)는 compute dtype과 persistent shadow
precision을 분리하지만, 현재 통과한 것은 Stage0a backend뿐이다. fake write-back은 수치 의미를
시험할 수 있어도 FP32 latent가 남아 있으면 VRAM 절감이 아니다. P094는 P022C가 선택한 low-shadow
policy `L`을 고정한 뒤, post-Muon update를 `Q + R`로 저장하는 explicit residual의 순효과와
WSD 후반 정밀도 전환, 실제 persistent storage, microbatch 환원을 차례로 묻는다.

Muon momentum을 저정밀화하거나 FP8 GEMM을 바꾸는 질문은 이 계획의 독립변수가 아니다. 그 축을
섞으면 Newton–Schulz 이후 update 왜곡과 shadow write-back 왜곡을 분리할 수 없다.

## 2. 질문

| # | 질문 | 답이 필요한 이유 |
|---|---|---|
| Q1 | `L only`의 invisible update·ternary disagreement를 R16/R8 residual이 줄이는가 | residual이 필요한지부터 가른다 |
| Q2 | WSD decay에서만 update/ULP와 residual 오차비가 달라져 `R8→R16`이 필요한가 | 일정표를 학습 구간 이름만으로 정하지 않는다 |
| Q3 | 숨은 FP32 master 없이 실제 Q/R persistent storage가 가능한가 | 논리적 byte와 실제 메모리를 분리한다 |
| Q4 | 회수 메모리로 physical microbatch를 늘리되 effective batch 131,072를 유지할 수 있는가 | 메모리 절감을 처리량 이득으로 환원한다 |
| Q5 | shadow Q/R이 Muon-state quantization보다 나은 전체 메모리 Pareto인가 | 부분 최적화를 피한다 |

## 3. ★사전 예측

- P022C `L only`가 수치·품질·실제 storage를 이미 통과하면 explicit residual은 복잡도만 더할
  가능성이 크며 P094는 R0에서 종료될 수 있다.
- R16은 `L only`의 작은 update 소실이 실제로 관측될 때만 이득이 있고, R8은 유효 정밀도가 낮아
  ternary threshold 근처 disagreement에서 먼저 탈락할 가능성이 있다.
- `R8→R16`은 WSD decay 경계 자체가 아니라 `RMS(error)/RMS(post-Muon update)` 분포 변화가
  있어야만 열린다. 변화가 없으면 static precision만 남긴다.
- shadow 절감보다 activation·Muon state·temporary dequant가 크면 다음 microbatch로 못 올라갈 수
  있다. 이 경우 품질 실험과 메모리 결과는 남기되 throughput 주장은 닫는다.

## 4. 대조군·조건 서명

P022C가 확정한 `L`을 그대로 사용하고 다음 항목을 모든 핵심 팔에서 고정한다.

- 모델·풀·token budget·seed·eval 경로
- Muon scale/LR, momentum dtype, matrix weight decay
- WSD/anneal과 ternary quantizer·scale granularity·rounding
- FP8 compute 설정과 effective batch

| ID | persistent shadow | residual | 읽을 수 있는 순효과 |
|---|---|---|---|
| `A-L` | P022C `L` | 없음 | low-shadow control |
| `B-R16` | 같은 `L` | BF16 | residual 존재 효과 |
| `C-R8` | 같은 `L` | 8-bit | residual 정밀도 효과 |
| `D-DYN` | 같은 `L` | stable R8, decay R16 | 관측으로 정당화된 동적 정밀도 |

기존 `A-L`은 위 조건 서명이 전부 같을 때만 재사용한다. 하나라도 다르면 direct control이 아니며,
재사용으로 세지 않는다.

## 5. 단계와 중단 게이트

| 단계 | 무엇 | 다음 단계 조건 | 비용 |
|---|---|---|---:|
| **R0 ✅ dependency HOLD 확인** | machine-readable P022C actual packed/masterless `L`, failure signature, hidden-master 여부 확인 | evidence 파일 부재로 선언된 exit8; residual R1 미개방 | [089](../test_result/089_20260919_P094-P022C-shadow-evidence가-없어-residual은-HOLD다.md) |
| **R1 observer** | 기존 FP32 궤적에서 Q/R simulation; post-Muon update RMS, ULP, `rho`, saturation, ternary disagreement를 WSD 구간별 기록 | R16이 L-only 왜곡을 줄이거나 decay 분포가 사전 문턱을 넘음 | ⚙0.05~0.10 H300 |
| **R2 static residual** | `A-L/B-R16/C-R8` 100M screen | paired CI가 현재 ruler 안, NaN/skip 0, resume 동일 | ⚙0.67 H300 신규 팔 상한 |
| **R3 dynamic precision** | R8 생존 시 static R8 대 decay 시작 R8→R16 | static 대비 품질 또는 최악 phase 메모리 Pareto | ⚙0.33 H300 |
| **R4 storage proof** | persistent FP32 weight·alias 0, Q/R/scale checkpoint round-trip, peak/RSS 측정 | logical byte뿐 아니라 physical peak 감소 | ⚙0.33 H300 |
| **R5 batch 환원** | 같은 131K effective batch에서 microbatch/accum만 교환 | 최악 R16 phase OOM 0, 처리량 증가, 품질 조건 동일 | ⚙0.05~0.15 H300 |
| **R6 규모·seed** | 300M direct baseline과 winner, 채택 후보만 다른 seed | 최소 2 seed 방향 일치 | 최대 ⚙4.0 H300 |

R0가 fake write-back뿐이면 R4까지 가지 않는다. R1에서 decay 특이성이 없으면 D-DYN을 만들지
않는다. 예상 회수 byte가 다음 microbatch 추가 peak의 1.2배 미만이면 R5를 닫는다.

## 6. 판정·비용

수치 비열등 margin은 실행 시점의 [`scripts/_rulers.py`](../scripts/_rulers.py)를 사용하고 paired
CI를 함께 기록한다. 고정 `+0.01`만으로 통과시키지 않는다.

| 경로 | 조건부 비용 |
|---|---:|
| R0에서 종료 | GPU 0 |
| R1 observer까지 | ⚙0.05~0.10 H300 |
| R3까지 | ⚙1.1 H300 이하 |
| R6까지 최대 | ⚙5.5 H300 이하 |
| 코드·계약 | ⚙4~8 engineer-h |
| 임시 산출물 | ⚙5 GiB 이하 |

이 비용은 기존 72h hard cap에 자동 편성하지 않는다. P022C 탈락분이나 다른 계획 잔여 시간을
P094로 옮기지 않는다.

## 7. 우선순위와 실행 경계

현재 우선순위는 **의존성 차단(D)**이다. P022C의 C/S 단계와 actual packed/masterless 출구조건이
선결이므로 residual·storage 구현을 지금 만들지 않는다. 첫 행동은 R0 증거표이며,
그 결과가 residual 필요성을 보여 준 뒤에만 R1 구현 범위를 다시 고정한다.

`run_P094_R0_p022c_dependency_gate.sh`는 `runs/evidence/P022C_shadow_storage.json`의
`p022c.shadow-storage.v1` 계약을 fail-closed로 검사한다. 현재 evidence가 없으므로 예상 결과는
exit 8 `DEPENDENCY HOLD`이며 실행 장애가 아니다.

사용자 승인은 계획과 조건부 연구 경로의 승인이다. GPU 학습, 모델 로딩, smoke, 배치 작성,
기본 optimizer·shadow 정책 변경은 별도 실행 승인과 직전 gate 로그가 필요하다.

## 8. 한계와 위험

| 위험 | 영향 | 완화 |
|---|---|---|
| `Q+R`이 사실상 split master | 메모리 주장 무효 | residual entropy·유효 bit·persistent tensor 전수 감사 |
| post-Muon이 아닌 raw gradient 계측 | 왜곡 원인 오판 | optimizer 적용 직전/직후 delta로만 `rho` 계산 |
| R16 phase OOM | 앞 구간 절감으로 늘린 batch가 후반 실패 | 최악 phase peak로 microbatch를 고정 |
| temporary dequant가 절감을 상쇄 | logical byte만 감소 | persistent/temporary/allocated/reserved/RSS 분리 |
| resume에서 FP32가 재생성 | 재개 후 다른 실험 | Q/R/scale/phase/WSD progress round-trip 계약 |
| Muon-state 대안 누락 | 전체 메모리 Pareto 왜곡 | 같은 회계표에서 경쟁 대안으로 비교 |

## 9. preflight와 이력

| 점검 | 결과 |
|---|---|
| 유사 실험 조회 | 기존 Muon 런은 있으나 같은 Q/R residual 실험은 없음 |
| 중복 계획 | shadow format은 P022C 소유; P094는 그 승자 뒤 residual/storage만 소유 |
| 계산 | 300M 기준 `2289×8×16×1024=300,023,808` token; microbatch 변경 시 accum으로 131K 유지 |
| 태그·배치 | 미배정·미작성 |
| 보호 경계 | 데이터·모델·GPU·smoke 접근 없음 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

- 2026-09-18: 권장안 A 승인으로 P094를 신설했다. P022C actual packed/masterless R0 이전의
  구현·배치·GPU·품질은 `NOT_RUN`이다.
- 2026-09-19: P094 자체 residual을 선제 구현하지 않고 R0 machine-readable dependency gate와
  SH를 작성했다. P022C evidence가 없으면 exit 8로 닫히며 R1 이후는 계속 `NOT_RUN`이다.
- 2026-09-19: 사용자 R0 로그가 evidence 부재를 감지해 exit8 HOLD로 끝났다. compute C1 음성을
  shadow residual need로 대체하지 않으며 actual packed/masterless evidence 전에는 재실행하지 않는다.
