@echo off
REM ===== P017 Skip-Forward / Dynamic KD : K=2, K=4, Dynamic  (300M, accum16) =====

echo [1/3] P017-1: t_kd_g8_k2 (Static K=2)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 2 --tag t_kd_g8_k2
if errorlevel 1 goto ERROR

echo [2/3] P017-2: t_kd_g8_k4 (Static K=4)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 4 --tag t_kd_g8_k4
if errorlevel 1 goto ERROR

echo [3/3] P017-3: t_kd_g8_dyn4 (Dynamic K 1-to-4)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 4 --kd-dynamic --tag t_kd_g8_dyn4
if errorlevel 1 goto ERROR

echo [Compare] vs dense baseline
python run100m.py compare --tag t_kd_g8_k2
python run100m.py compare --tag t_kd_g8_k4
python run100m.py compare --tag t_kd_g8_dyn4
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause