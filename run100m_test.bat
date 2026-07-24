@echo off
REM ===== (A) offline-KD validation on tiny  +  (B) t_kd_g16 (extreme tying) =====

echo =========================================
echo (A) offline-KD validation (tiny, ~2min)
echo =========================================
echo   a) tiny dense teacher
python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 40 --micro-bs 4 --seq 128 --accum 2 --eval-every 20
if errorlevel 1 goto ERROR
echo   b) build KD cache (top32)
python run100m.py kdcache --tiny --data synthetic --tokens 2M --steps 40 --micro-bs 4 --seq 128 --accum 2 --kd-topk 32
if errorlevel 1 goto ERROR
echo   c) online KD  (tag kc_online)
python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 40 --micro-bs 4 --seq 128 --accum 2 --eval-every 20 --init-from --kd --tag kc_online
if errorlevel 1 goto ERROR
echo   d) offline KD (tag kc_offline)
python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 40 --micro-bs 4 --seq 128 --accum 2 --eval-every 20 --init-from --kd-cache --kd-topk 32 --tag kc_offline
if errorlevel 1 goto ERROR
echo   CHECK: kc_online vs kc_offline final loss should be CLOSE (top-k approx). If very different, offline KD has a bug.
pause

echo =========================================
echo (B) t_kd_g16 : g=16 extreme tying + KD + parent-init (online KD)
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --mlp-group 16 --init-from --kd --tag t_kd_g16
if errorlevel 1 goto ERROR
python run100m.py compare --tag t_kd_g16
python run100m.py compare --tag t_kd_g8 --vs t_kd_g16
echo done. Speed up KD later: kdcache (m100) then train --kd-cache.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause
