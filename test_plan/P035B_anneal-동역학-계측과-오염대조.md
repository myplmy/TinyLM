# P035B — anneal 동역학 계측과 audit 오염 대조

> **승인 계보:** 사용자가 2026-09-15 승인한
> [`anneal 스케줄 분해·계측 우선 제안`](../proposal/done/20260915_anneal-스케줄-분해와-계측우선-개선-approved.md)의
> A3를 정식 실험으로 옮긴다. P035의 형태 비교를 반복하는 계획이 아니라, P035에서 보지 못한
> quantization distance·code flip·grid margin과 계측 오염을 확인하는 후속 계획이다.
>
> **현재 상태(2026-09-15):** Stage1 A3 완료([결과 084](../test_result/084_20260915_P035B-감사오염은-없고-후반궤적차도-지속되지-않았다.md)).
> G0·G1은 PASS했으나 G2의 지속 후반 궤적차는 불성립했다. A4 adaptive/freeze 후보를 열 근거가
> 생기지 않았고 A5 기본값 변경은 미승인이다.

## 1. 왜 — raw 명령이 아니라 실험 계약이 필요하다

승인 제안서에는 같은 초기 상태에서 시작하는 0.60/0.80 trajectory와 0.80 audit-off 대조가
있었지만, 이전 작업은 이를 계획번호·조건표·태그·배치·중단선 없이 사용자에게 세 명령으로만
요청했다. 실제 GPU 학습을 계획·배치 승인 범위 밖이라고 임의로 좁힌 판단 오류였다.

P026/P035는 final loss에서 ternary anneal end와 shape의 우월성을 검출하지 못했다. 이번 A3의
질문은 다시 품질 순위를 매기는 것이 아니라 다음 둘이다.

1. 0.60과 0.80이 실제 ternary weight의 거리·flip·점유·경계여유에 다른 후반 이력을 남기는가.
2. audit를 켠 행위 자체가 학습 궤적·시간·메모리를 허용 범위 밖으로 바꾸는가.

## 2. 계보와 중복 감사

| 선행 | 이미 답한 것 | 이번에 반복하지 않는 것 | P035B의 새 정보 |
|---|---|---|---|
| P026 / 결과 015 | WSD가 cosine보다 좋음; end 0.60↔0.80 final loss 차이는 1.07σ 이내 | 2289-step 품질 재대결 | 짧은 실행의 weight-level 동역학 |
| P035 / 결과 022 | linear↔step 2×2는 검출 불가; step은 grad spike가 더 큼 | step shape 재실행 | linear 내부의 거리·flip·margin |
| 승인 제안 A0~A2 | 스케줄 단일원천, opt-in audit, CPU fixture | 수식 fixture 반복 | 실제 CUDA 학습 경로와 audit on/off 오염 |

`check_run_registry.py`의 조건 검색에서는 유사한 m100s8 Muon 런과 250-step optimizer probe가
나왔지만, `--anneal-audit` JSONL과 같은-seed audit on/off 쌍은 없었다. 따라서 기존 결과로
대체할 수 없다.

## 3. Stage1 = 승인 제안 A3

### 3.1 세 팔과 독립변수

| 팔 | tag | quant anneal end | audit | 역할 |
|---|---|---:|---|---|
| E60-on | `p35b_a3_e60` | 0.60 | 매 10 step, 최대 8 TLinear | 이른 완전삼진 trajectory |
| E80-on | `p35b_a3_e80` | 0.80 | 매 10 step, 최대 8 TLinear | 늦은 완전삼진 trajectory |
| E80-off | `p35b_a3_off80` | 0.80 | 꺼짐 | E80-on의 계측 오염 대조 |

유효한 비교는 `E60-on ↔ E80-on`의 동역학과 `E80-on ↔ E80-off`의 오염 대조뿐이다.
E60-on과 E80-off를 직접 비교해 효과를 섞지 않는다.

### 3.2 고정 조건 서명

| 축 | 고정값 | 근거·주의 |
|---|---|---|
| preset / 구조 | `m100s8`, `dense`, `cla_group=2` | 작은 d12 진단 셀. 표준 m100의 품질 대조가 아님 |
| 부모 | `runs/ckpt/m100_ko-en_300M_dense.pt` | `PRESET_PARENT[m100s8]=m100`; `--depth-init role`로 얕은 모델에 이식 |
| 시작 | fresh run, `--init-from`, resume 금지 | 서로 다른 앞선 anneal 이력을 가진 late checkpoint 재생은 무효 |
| seed / data order | `1337`, 세 팔 동일 | 초기화와 crop 순서를 함께 고정 |
| 데이터 | `ko-en`, 600M exact pool | 32.8M 학습토큰의 18.3배 풀; 풀 결핍 없음 |
| 학습량 | 250 × 8 × 16 × 1024 = **32,768,000 토큰** | `--tokens 300M`은 캐시/경로 namespace이며 학습량이 아님 |
| optimizer | Muon, RMS scale ×4, LR `1e-3` | 세 팔 동일 |
| LR schedule | WSD, `decay_frac=0.2` | quant anneal end만 바꾸고 LR knob는 바꾸지 않음 |
| quant shape/start | linear, start 자동값 | 명시하지 않은 기본을 contract JSON에 실제값으로 기록 |
| compile / grad checkpoint | `--compile` / `--no-ckpt` | 현 무KD dense 표준을 따르며 세 팔 동일; audit의 실제 운용 경로를 검사 |
| 평가 | `eval_every=250` | final 1점은 생존 확인용; 250-step 품질 판정 금지 |

표준조건 중 preset `m100`과 2289 steps에서 벗어난 이유는 **A2 계측기의 최초 저비용 E2E와
오염 분리**다. compile·무KD dense의 no-ckpt·유효배치·pool·LR·WSD는 현 표준을 따른다. 이
결과의 ms/step이나 val_loss를 표준 학습 성능으로 옮기지 않는다.

## 4. 사전 예측과 판정 규칙

### 4.1 실행 건전성 G0

세 팔 모두 다음을 만족해야 A3 자료로 보존한다.

- exit 0, 250 steps 완료, NaN/Inf·skip 0.
- 계약 JSON의 preset·부모·seed·pool·유효배치·optimizer·LR·WSD가 표와 일치.
- E60-on/E80-on은 JSONL과 `.contract.json`을 exclusive-create로 남기며 기존 파일을 덮지 않음.
- audit row는 step 0부터 10-step 간격으로 존재하고 선택 모듈 수는 1~8개.

한 팔이 실패해도 나머지 독립 팔은 수집하되 배치는 최종 nonzero로 끝낸다. 실패 팔은 같은
파일을 지우거나 `-done`을 되돌리지 않고 원인 수정 뒤 새 Stage1b로만 재실행한다.

### 4.2 audit 오염 G1

`E80-on ↔ E80-off`만 비교한다.

- 설정 차이는 audit 세 플래그와 출력 경로뿐이어야 한다.
- step 수·skip·비유한 값이 같아야 한다.
- on의 정상상태 median ms/step 증가는 off 대비 **15% 이하**, peak reserved 증가는
  **0.5 GiB 이하**여야 한다. 초과하면 A2의 sampling/every 구현을 먼저 줄이고 A4를 열지 않는다.
- 같은 seed CUDA 실행이 비트 동일하지 않다면 그 사실을 그대로 기록한다. final loss 차이는
  현재 조건의 ruler 안이어야 하며, 그 사실만으로 “오염 없음”을 확정하지 않는다.

### 4.3 동역학 발견 G2

`E60-on ↔ E80-on`은 같은 progress의 같은 모듈끼리만 비교한다. quant distance,
code flip, occupancy, grid margin, gradient/update RMS를 층별과 원소수 가중 집계로 각각 본다.

- progress 0.60~0.80 차이는 스케줄 정의상 생기는 기계적 차이로만 기록한다.
- 둘 다 완전삼진인 progress 0.80 이후에도 flip·grid margin·update/weight의 방향 차이가
  여러 연속 샘플과 여러 모듈에서 유지되는지를 A4 필요성의 관측 근거로 쓴다.
- 한 seed·한 250-step trajectory는 재현성 증거가 아니다. 차이가 보이면 A4 후보 설계의
  입력이 될 뿐이며, 차이가 없으면 복잡한 adaptive/freeze 후보를 열 근거가 약해진다.

### 4.4 금지 판정

- final/best loss로 0.60 또는 0.80을 기본값으로 승격하지 않는다.
- audit-on ms/step을 학습 속도로 인용하지 않는다.
- 선택한 최대 8개 TLinear를 전체 층 분포라고 부르지 않는다.
- A3 통과를 A4 구현·배치 또는 A5 기본값 변경 승인으로 간주하지 않는다.

## 5. 실행 파일과 사용자 절차

정본 배치: [`run_P035B_Stage1_anneal_a3_trajectories.bat`](../run_P035B_Stage1_anneal_a3_trajectories.bat)

1. 현재 코드 변경 뒤 `run_smoke_check.bat`를 사용자가 실행해 실패 팔 0,
   exit-0 오류표지 0, 계측 계약 오류 0을 확인한다.
2. GPU가 유휴이고 체크포인트 여유가 최악 약 5.6 GiB 이상일 때 저장소 루트에서 정본 배치를
   실행한다. 세 팔 합계 예상 시간은 ⚙0.3~0.8 GPU-h다.
3. 배치 종료코드 0과 `runs/audit/p35b_a3_e{60,80}.{jsonl,contract.json}`,
   세 `runs/logs/m100s8_ko-en_300M_p35b_a3_*.json`, 통합 runlog 경로를 회신한다.
4. Codex는 `log-to-result` 범위를 새 WIP로 고정한 뒤 G0→G1→G2 순서로 판독한다.

Codex는 GPU·모델·학습·스모크를 실행하지 않는다. 체크포인트와 audit 산출물 삭제도 별도 사용자
승인 전 수행하지 않는다.

## 6. 정적 preflight (2026-09-15)

| 검사 | 결과 |
|---|---|
| 전역 계획번호 | P035B 미사용 확인; P035 후속 계보로 배정 |
| 토큰 계산 | 131,072 토큰/step, 250 steps = 32.8M |
| 풀 | 600M exact = 학습량의 18.3배 |
| 태그 | `p35b_a3_e60`, `p35b_a3_e80`, `p35b_a3_off80` 기존 로그 충돌 0 |
| 유사 런 | m100s8 Muon 및 250-step probe 존재; anneal audit/on-off 질문은 중복 0 |
| 부모 | `m100_ko-en_300M_dense.pt`가 체크포인트 정본에서 `keep`; m100s8 부모 매핑 확인 |

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 7. 결과 연쇄 갱신

A3 로그가 회신되기 전에는 결과 문서를 만들지 않는다. 회신 뒤에는 새 결과 문서와 함께 다음을
대조·갱신한다.

- 이 계획의 G0/G1/G2 상태와 실행 조건 서명
- `test_plan/실험계획목록.md`
- `test_result/실험목록.md`와 `docs/EXPERIMENT_BASELINES.md`의 런 레지스트리
- 승인 제안서의 A3 상태
- A4 개방 여부를 결정하는 사용자 승인 요청

## 8. 이력

- 2026-09-15: 승인 제안 A3를 P035B Stage1로 정식 등록. 계획·배치·태그·중단선 작성,
  GPU 실행은 `NOT_RUN`.

- 2026-09-15: Stage1 세 팔 모두 250 step·skip 0·exit 0. E80 audit-on/off는 중앙 ms/step
  −0.045%, wall +0.75%, reserved 차 0 GiB, final val 동일로 G1 통과. E60/E80은 step 200 뒤
  flip·qdist·margin 차의 부호가 뒤집히거나 섞여 G2 지속성 불성립. 250-step loss로 endpoint를
  선택하지 않으며 A4를 열지 않는다([결과 084](../test_result/084_20260915_P035B-감사오염은-없고-후반궤적차도-지속되지-않았다.md)).
