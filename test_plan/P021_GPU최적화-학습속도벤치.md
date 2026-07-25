# P021 — GPU 최적화 학습속도 벤치 (기존 기능 조합, 신규코드 최소)

## 목적
현재 KD-init ≈ 4000ms/step, dense ≈ 2500ms/step. **이미 구현된 기능들의 조합**으로 벽시계를
얼마나 줄일 수 있는지 벤치. 목표는 "ms/step 반감"의 착시가 아니라 **tokens/sec·목표loss까지
벽시계** 최적점 찾기.

> **중요 개념**: 이 코드에서 1 step = accum micro-batch 묶음이라 ms/step은 accum에 ~선형이다.
> accum을 줄이면 ms/step은 주지만 step당 토큰도 줄어 **고정 토큰까지 총 벽시계는 거의 불변**
> (연산 바운드). 따라서 accum/steps "조정으로 step 반감"은 총시간 이득이 아니다. 실이득 레버는
> 아래 (a)~(d).

## 측정 레버 (모두 기존 플래그, 신규코드 없음)
- **(a) `--no-ckpt`**: gradient checkpointing off → 활성 재계산 제거. 예상 step 15~30%↓.
  **단일 최대 레버.** VRAM 스필벽(13~14GB) 아래인지 nvidia-smi로 확인하며.
- **(b) micro_bs 스윕(8→12)**: 소형모델 SM 활용↑ → tokens/sec↑. mb16은 스필 주의.
- **(c) KD 오버헤드 제거**: `--kd-every 4 --kd-dynamic`(P017 dyn4) + `--kd-teacher-tag`(P018
  압축교사) 결합 → 교사 forward 연산 대폭↓. KD-step을 dense-step 근처로.
- **(d) seq-warmup(P013)**: 별도 계획(초반 짧은 seq). 여기선 (a)~(c)만.

## 벤치 매트릭스 (m100, ko-en, 300M, 짧은 steps로 ms/step만 측정 — 품질 아님)
각 조합 200~300 step만 돌려 안정 ms/step·VRAM 기록(품질 무관, 속도 프로파일용):

| 태그 | 플래그 | 측정 |
|---|---|---|
| base_dense | (현행) | 기준 2500ms |
| dense_nockpt | --no-ckpt | (a) 효과 |
| dense_nockpt_mb12 | --no-ckpt --micro-bs 12 --accum 11 | (a)+(b), 유효배치≈300M 유지 |
| kd_dyn4_comp | --kd --kd-every 4 --kd-dynamic --kd-teacher-tag t_kd_g8 --no-ckpt | (a)+(c) KD 종합 |

> 유효배치=micro_bs×accum×seq 를 131K(300M/2289step)에 맞춰 accum 조정(mb12→accum11).

## 판정
- dense: `--no-ckpt`(+mb12)로 step 몇 %↓ 및 스필 없는지. 스필 시 mb 되돌림.
- KD: dyn4+압축교사+no-ckpt 로 KD-step이 dense-step 대비 몇 %까지 근접하는지.
- **정직한 목표 설정**: 연산 바운드·이론하한 ~2.2s이라 dense step <1250 반감은 비현실적.
  달성 가능 실익 = KD 오버헤드 소거(≈dense) + no-ckpt 15~30%↓ + (P012 데이터효율로 토큰↓).

## 비고
- 결과는 `docs/methods/05_training_speed.md` 표에 실측치로 갱신.
- 근본적 추가 가속(FP8 텐서코어)은 **P022** 로 분리(신규 의존성·구현 필요).
