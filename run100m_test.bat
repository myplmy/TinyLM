@echo off
REM ===== P017 Skip-Forward / Dynamic KD : K=2, K=4, Dynamic  (300M, accum16) =====
REM DONE - recorded as result 005. Verdict: static k4 is best on both quality and time.
REM ERRORLEVEL POLICY: the three runs are independent (all reuse an existing dense), so a
REM   failure only warns and the batch keeps going.

echo [1/3] P017-1: t_kd_g8_k2 (Static K=2)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 2 --tag t_kd_g8_k2
if errorlevel 1 echo [WARN] [1/3] k2 failed - continuing

echo [2/3] P017-2: t_kd_g8_k4 (Static K=4)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 4 --tag t_kd_g8_k4
if errorlevel 1 echo [WARN] [2/3] k4 failed - continuing

echo [3/3] P017-3: t_kd_g8_dyn4 (Dynamic K 1-to-4)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --kd-every 4 --kd-dynamic --tag t_kd_g8_dyn4
if errorlevel 1 echo [WARN] [3/3] dyn4 failed - continuing

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