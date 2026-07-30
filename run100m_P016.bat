@echo off
REM ===== P016 3:4 sparse ternary (Sherry 1.25bpw) : g8_s34, g4_s34  (300M, accum16) =====
REM Requires existing dense + t_kd_g8 baselines (reused). Student = sparse34, teacher = dense.
REM sparse34 uses standard F.linear path only (NOT the custom triton kernel).
REM ERRORLEVEL POLICY (result 007 lesson): both runs reuse an EXISTING dense, so they are
REM   independent - a failure only warns and the next run still executes.

echo [1/2] P016-1: t_kd_g8_s34 (3:4 sparse ternary 1.25bpw, g8)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --sparse34 --tag t_kd_g8_s34
if errorlevel 1 echo [WARN] g8_s34 failed - continuing

echo [2/2] P016-2: t_kd_g4_s34 (3:4 sparse ternary, conservative tying g4)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 4 --sparse34 --tag t_kd_g4_s34
if errorlevel 1 echo [WARN] g4_s34 failed - continuing

echo [Compare] vs dense baseline (memory ratio now reflects 1.25bpw)
python run100m.py compare --tag t_kd_g8_s34
python run100m.py compare --tag t_kd_g4_s34
echo [Compare] sparse loss decomposition: g8 (1.95bpw) vs g8_s34 (1.25bpw)
python run100m.py compare --tag t_kd_g8 --vs t_kd_g8_s34
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause
