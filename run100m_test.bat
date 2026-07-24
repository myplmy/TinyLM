@echo off
REM ===== t_kd_g16 : g=16 extreme tying + KD (online) =====
REM (offline KD removed: top-k KD under-distills for our high-entropy teacher, see test_result/004)

echo =========================================
echo t_kd_g16 : g=16 + KD + parent-init (online KD)
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --mlp-group 16 --init-from --kd --tag t_kd_g16
if errorlevel 1 goto ERROR

echo =========================================
echo compare
echo =========================================
python run100m.py compare --tag t_kd_g16
python run100m.py compare --tag t_kd_g8 --vs t_kd_g16

echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause
