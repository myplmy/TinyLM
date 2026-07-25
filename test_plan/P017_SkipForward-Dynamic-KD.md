# P017 — Skip-Forward / Dynamic KD (온라인 KD 가속)

## 목적
온라인 KD의 병목 = **교사(dense 132.5M) 매 스텝 full forward** → 학습시간 ~2×. 교사 forward를
**K스텝마다 1회**로 줄여(skip-forward) 교사 연산을 1/K로. 동적 스케줄로 초반 촘촘·후반 성김.
질문: **어느 정도 건너뛰어도 KD 격차소멸 효과(t_kd_g8 +0.005)가 유지되는가?**

## 구현 (완료, 바로 실행 가능)
- `trainer.py`: 스텝 진입 시 `kd_this` 판정. `kd_every=K` → `s % K == 0` 인 스텝만 교사 forward+KL,
  나머지는 CE-only. `kd_dynamic` → 간격을 `round(1+(K-1)·s/steps)` 로 1→K 선형 증가(초반 KD 촘촘).
  건너뛴 스텝은 loss=CE. 로그/JSON 에 `kd_fwd_steps`(실제 교사 forward 횟수) 기록, 종료 시 % 출력.
- `cli.py`: `--kd-every K`, `--kd-dynamic`.

## 실험 매트릭스 (m100, ko-en, 300M, --kd --init-from --mlp-group 8, dense 교사 재사용)
| 태그 | 플래그 | 교사 forward | 기대 |
|---|---|---|---|
| t_kd_g8 (기존) | `--kd-every 1` | 100% | 격차 +0.005 기준, 시간 ~2× |
| t_kd_g8_k2 | `--kd-every 2` | 50% | 시간 ~1.5×?, 격차 유지되나 |
| t_kd_g8_k4 | `--kd-every 4` | 25% | 시간 ~1.25×?, 격차 임계점 탐색 |
| t_kd_g8_dyn4 | `--kd-every 4 --kd-dynamic` | 초반多·후반少 | 초기 유도 보존해 격차 최소화 |

판정: `compare`(dense 기준) 손실격차 ≤ +0.07 유지하는 최대 K, 그때 wall_sec 감소폭.
정적 vs 동적 중 같은 forward 예산(25%)에서 어느 쪽이 격차 작은지.

## 실행 (사용자 대리 수행)
```
:: 사전: dense 교사(300M)와 t_kd_g8 기준이 이미 있어야 함
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 ^
  --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 2 --tag t_kd_g8_k2
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 ^
  --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 4 --tag t_kd_g8_k4
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 ^
  --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 4 --kd-dynamic --tag t_kd_g8_dyn4
python run100m.py compare --tag t_kd_g8_k2
python run100m.py compare --tag t_kd_g8_k4
python run100m.py compare --tag t_kd_g8_dyn4
```

### run100m_test.bat
```
@echo off
REM ===== t_kd_g8 experiments : K=2, K=4, Dynamic  =====
REM (teacher forward reduced to 1/K steps, verifying KD loss gap <= +0.07 holds)

echo =========================================
echo [1/3] P017-1: t_kd_g8_k2 (Static K=2)
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 2 --tag t_kd_g8_k2
if errorlevel 1 goto ERROR

echo =========================================
echo [2/3] P017-2: t_kd_g8_k4 (Static K=4)
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 4 --tag t_kd_g8_k4
if errorlevel 1 goto ERROR

echo =========================================
echo [3/3] P017-3: t_kd_g8_dyn4 (K=1-^>4, Dynamic K)
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 4 --kd-dynamic --tag t_kd_g8_dyn4
if errorlevel 1 goto ERROR

echo =========================================
echo [Compare] Comparing Results against Dense Baseline
echo =========================================
python run100m.py compare --tag t_kd_g8_k2
python run100m.py compare --tag t_kd_g8_k4
python run100m.py compare --tag t_kd_g8_dyn4

echo =========================================
echo Comparing Results
echo =========================================
python run100m.py compare --tag t_kd_g8_k2
python run100m.py compare --tag t_kd_g8_k4
python run100m.py compare --tag t_kd_g8_dyn4

echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause
````

## 비판/리스크
- 건너뛴 스텝은 KD 신호 0 → 교사 지식 주입 총량 감소. K가 크면 격차 재확대 예상(임계점 측정이 목적).
- 배치가 매 스텝 달라 교사 출력 재사용 불가(=진짜 건너뜀). 시간 절감은 교사/학생 forward 비중에
  좌우 — 교사(132.5M)>학생이라 K=2도 체감 큼. 단 compile 워밍업·데이터로딩은 불변이라 실측 필요.
