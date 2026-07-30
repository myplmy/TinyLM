@echo off
REM ===== P021 GPU-optimized training-speed bench (ms/step + VRAM only, NOT quality) =====
REM Short 250-step runs. Watch ms/step (steady-state) and nvidia-smi VRAM for spill (13-14GB wall).
REM All runs tagged sp_* so they do NOT overwrite real dense/tied checkpoints or logs.
REM Effective batch kept ~131K (mbs*accum*seq) to match 300M-line optimization regime.
REM ERRORLEVEL POLICY: all four runs are independent, so a failure only warns.
REM   (In the first execution [3] hit OOM and goto ERROR killed [4], which had to be run by
REM    hand. That is the reason this policy exists - see result 007 section 2-(5).)

echo [1/4] baseline dense (default, grad-checkpoint ON)
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 999 --compile --tag sp_base
if errorlevel 1 echo [WARN] [1/4] baseline failed - continuing

echo [2/4] dense --no-ckpt (grad-checkpoint OFF: recompute removed)
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 999 --compile --no-ckpt --tag sp_nockpt
if errorlevel 1 echo [WARN] [2/4] no-ckpt failed - continuing

echo [3/4] dense --no-ckpt ^+ micro-bs 12 (SM utilization; accum 11 keeps eff-batch ~135K)
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 250 --micro-bs 12 --accum 11 --seq 1024 --lr 1e-3 --eval-every 999 --compile --no-ckpt --tag sp_nockpt_mb12
if errorlevel 1 echo [WARN] [3/4] mb12 failed - continuing

echo [4/4] tied KD combo: k4 skip-forward ^+ compressed teacher(t_kd_g8) ^+ no-ckpt
REM requires existing dense.pt (init/teacher fallback) and t_kd_g8 checkpoint (compressed teacher)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 999 --compile --no-ckpt --kd --init-from --mlp-group 8 --kd-every 4 --kd-teacher-tag t_kd_g8 --tag sp_kd_k4_comp
if errorlevel 1 echo [WARN] [4/4] KD combo failed - continuing

echo ================================================================
echo Read steady-state ms/step from each run above (ignore step 0 = compile).
echo Compare: [1] base vs [2] no-ckpt vs [3] ^+mb12  (dense-step lever)
echo          [4] KD combo vs P017 full-KD ms/step   (teacher-overhead lever)
echo Also watch nvidia-smi: keep VRAM under ~13-14GB (WDDM spill wall).
echo ================================================================
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause
