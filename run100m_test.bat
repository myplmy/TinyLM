@echo off
chcp 65001 > nul
REM ================= P003: KD + g 스윕 (더 공격적 타잉으로 메모리 추가 감축) =================
REM 기존 dense 교사(m100_ko-en_300M_dense.pt) 재사용. 핵심 질문: KD가 g=8 격차도 닫는가?

echo =========================================
echo (1/2) g=8 단독 (KD 없음) - g8 raw 격차 기준
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --no-ckpt --mlp-group 8 --tag t_g8
if errorlevel 1 goto ERROR

echo =========================================
echo (2/2) g=8 + KD + 부모초기화 - KD가 g8 격차를 닫는가?
echo =========================================
REM KD는 교사가 VRAM에 올라가므로 --no-ckpt 제외
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --mlp-group 8 --init-from --kd --tag t_kd_g8
if errorlevel 1 goto ERROR

echo =========================================
echo 비교
echo =========================================
REM 각 조건 vs dense(3.8241). g8 목표 감축 ~2.08x.
python run100m.py compare --tag t_g8
python run100m.py compare --tag t_kd_g8
REM KD 효과(같은 g8에서 KD 유무)
python run100m.py compare --tag t_g8 --vs t_kd_g8

echo =========================================
echo P003 완료 (판정: t_kd_g8 격차가 +0.07 이내면 g=8 채택 -> 2.08x)
echo =========================================
pause
exit /b 0

:ERROR
echo [경고] 중단됨: 학습 중 에러 발생.
pause
