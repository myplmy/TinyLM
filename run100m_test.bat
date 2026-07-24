@echo off
REM ===== P003: KD + g-sweep (more aggressive tying, extra memory reduction) =====
REM Reuse existing dense teacher m100_ko-en_300M_dense.pt.
REM Question: does KD close the g=8 gap too? (target reduction ~2.08x)

echo =========================================
echo (1/2) g=8 only, no KD  [raw g8 gap baseline]
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --no-ckpt --mlp-group 8 --tag t_g8
if errorlevel 1 goto ERROR

echo =========================================
echo (2/2) g=8 + KD + parent-init  [no --no-ckpt: teacher on GPU]
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --mlp-group 8 --init-from --kd --tag t_kd_g8
if errorlevel 1 goto ERROR

echo =========================================
echo compare (each vs dense 3.8241; and t_g8 vs t_kd_g8)
echo =========================================
python run100m.py compare --tag t_g8
python run100m.py compare --tag t_kd_g8
python run100m.py compare --tag t_g8 --vs t_kd_g8

echo =========================================
echo P003 done. Verdict: if t_kd_g8 gap within +0.07, adopt g=8 (2.08x memory)
echo =========================================
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during training.
pause
