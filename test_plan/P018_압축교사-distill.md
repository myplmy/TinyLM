# P018 — 압축 교사 distill (온라인 KD 가속 + 교사 메모리 절감)

## 목적
교사가 **dense 132.5M** 이라 forward가 비싸다(KD ~2×). 이미 dense 품질에 도달한 **압축 tied
체크포인트(예: t_kdinit g4, 72.9M)를 교사로** 쓰면 교사 forward가 ~0.55×로 싸진다. 질문:
**압축 교사로 distill 해도 학생 품질이 dense-교사와 동등한가?**(교사 상한 = 압축 교사 품질)

## 구현 (완료, 바로 실행 가능)
- `init_utils.load_dense` 는 체크포인트의 **cfg로 복원** → tied 교사도 그대로 로드(범용). 교사는
  `set_anneal(1.0)` 로 완전 삼진(배포 모드) forward.
- `cli.py`: `--kd-teacher-tag TAG` → 교사 경로를 `{base}_{TAG}.pt` 로(기본 dense 대신). KD/skip-forward
  플래그와 조합 가능.

## 전제
- 교사로 쓸 압축 모델이 먼저 있어야 함: 예 `t_kdinit`(g4, dense KD로 학습해 dense≈품질). 없으면 먼저 학습.
- 교사 상한 원칙: **압축 교사 품질 ≤ dense** 이면 학생도 그 이하. t_kdinit 이 dense와 동등(+0.001)일 때만 유효.

## 실험 매트릭스 (m100, ko-en, 300M, 학생 g8)
| 태그 | 교사 | 교사 forward 비용 | 기대 |
|---|---|---|---|
| t_kd_g8 (기존) | dense 132.5M | 1.00× | 격차 +0.005 기준 |
| t_kd8_ct | 압축 t_kdinit 72.9M | ~0.55× | 격차 유지 & 시간↓? |
| t_kd8_ct_k2 | 압축 교사 + `--kd-every 2` | ~0.27× | P017 결합 상한 |

판정: `compare`(dense 기준) 격차 ≤ +0.07 유지하며 wall_sec 감소. 압축교사 격차가 dense교사보다
크게 벌어지면 "교사 상한" 확인(압축 교사 자체 품질이 병목).

## 실행 (사용자 대리 수행)
> 토큰 예산: `--accum 16`(유효배치 131K) = 300M. 생략(accum8)하면 150M만 학습되니 주의(P017 005 교훈).
```
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 ^
  --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-teacher-tag t_kdinit --tag t_kd8_ct
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 ^
  --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-teacher-tag t_kdinit --kd-every 2 --tag t_kd8_ct_k2
python run100m.py compare --tag t_kd8_ct
python run100m.py compare --tag t_kd8_ct_k2
```

### run100m_test.bat (순수 ASCII)
```
@echo off
REM ===== P018 compressed-teacher distill (teacher = t_kdinit tied ckpt) =====
echo [1/2] t_kd8_ct (compressed teacher, full KD)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-teacher-tag t_kdinit --tag t_kd8_ct
if errorlevel 1 goto ERROR
echo [2/2] t_kd8_ct_k2 (compressed teacher + skip-forward K=2)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-teacher-tag t_kdinit --kd-every 2 --tag t_kd8_ct_k2
if errorlevel 1 goto ERROR
python run100m.py compare --tag t_kd8_ct
python run100m.py compare --tag t_kd8_ct_k2
echo done.
pause
exit /b 0
:ERROR
echo [WARN] stopped: error during run.
pause
```

## 비판/리스크
- **순환성**: 압축 교사도 원래 dense KD로 만든 것 → dense 교사 학습 비용은 이미 한 번 지불. 이득은
  "이후 여러 학생을 값싼 교사로" 재사용할 때. 1회성이면 이득 없음.
- 삼진 교사 forward를 **삼진 커널로 더 빠르게?** → GPU에선 커널이 cuBLAS보다 느림(P014/003 참조).
  따라서 압축 교사도 GPU에선 일반 F.linear(bf16) forward가 최적. 커널 이점은 CPU 배포뿐.
