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
