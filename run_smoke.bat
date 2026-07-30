@echo off
REM ===== SMOKE : verify the instrumentation contract before spending GPU hours =====
REM
REM WHY THIS EXISTS
REM   P021B asked the operator to write down nvidia-smi VRAM per run. It was not written down,
REM   and the numbers are gone - you cannot recover a peak after the process exits.
REM   Root cause was NOT operator error:
REM     (a) the trainer never measured VRAM at all, so it depended entirely on a human watching
REM     (b) the instruction lived in the batch TAIL echo, which prints AFTER every run finishes
REM     (c) the REM header is invisible under @echo off
REM   Fix: the trainer now records vram_alloc_gb / vram_reserved_gb into the result json and
REM   prints them on the final line. THIS batch proves that the recording actually works.
REM
REM WHAT IT COVERS - one short run per new/risky flag, so a broken contract surfaces in minutes
REM   [1] sm_base    defaults (seed 1337, anneal 0.60, grad-ckpt ON)
REM   [2] sm_seed    --seed 4242            (seed plumbed to weights AND train crops)
REM   [3] sm_s34     --sparse34             (1.25bpw path + deploy_mb split)
REM   [4] sm_sched   --sched wsd --anneal-end 0.80  (P026 alignment print)
REM   [5] sm_nockpt  --no-ckpt              (grad_ckpt flag recorded)
REM   [6] sm_kd      --kd --init-from --kd-every 4  (teacher path + kd fields)
REM
REM COST: tiny preset on synthetic data, 30 steps each. A few minutes total, tiny VRAM.
REM   Synthetic data means compare() will refuse to judge quality - that is intended.
REM   THIS BATCH SAYS NOTHING ABOUT MODEL QUALITY. It only checks that we RECORD things.
REM
REM ERRORLEVEL POLICY: every run is independent, failures only warn.

echo ============================================================
echo [SMOKE] instrumentation contract check (tiny preset, synthetic)
echo ============================================================
echo.
echo [pre] static attribute check - catches cfg.WRONG_NAME without loading torch
REM   Added after the P029 incident: scripts\probe_prompts.py used cfg.seq_len (real field is
REM   max_seq_len). Python only fails at that line, which ran AFTER loading a model on the GPU,
REM   so the batch had to be run before anyone found out. This check is seconds and needs no GPU.
python scripts\check_attrs.py
if errorlevel 1 echo [WARN] attribute check found problems - FIX THEM FIRST

echo.
echo === [1/6] defaults ===
python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --tag sm_base
if errorlevel 1 echo [WARN] sm_base failed - continuing

echo === [2/6] --seed 4242 ===
python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --seed 4242 --tag sm_seed
if errorlevel 1 echo [WARN] sm_seed failed - continuing

echo === [3/6] --sparse34 ===
python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --sparse34 --tag sm_s34
if errorlevel 1 echo [WARN] sm_s34 failed - continuing

echo === [4/6] --sched wsd --anneal-end 0.80  (expect the [sched] aligned line) ===
python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --tag sm_sched
if errorlevel 1 echo [WARN] sm_sched failed - continuing

echo === [5/6] --no-ckpt ===
python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --no-ckpt --tag sm_nockpt
if errorlevel 1 echo [WARN] sm_nockpt failed - continuing

echo === [6/6] --kd --init-from --kd-every 4  (needs a tiny dense parent first) ===
python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15
if errorlevel 1 echo [WARN] tiny dense parent failed - sm_kd will be skipped
python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --kd --init-from --mlp-group 4 --kd-every 4 --tag sm_kd
if errorlevel 1 echo [WARN] sm_kd failed - continuing

echo.
echo ============================================================
echo [VERIFY] checking that every instrumentation field was recorded
echo ============================================================
python scripts\check_smoke.py

echo.
echo ============================================================
echo WHAT TO LOOK FOR
echo   1. every run printed a final line ending with VRAM x.xxGB(reserved)
echo   2. run [4] printed a [sched] line saying aligned
echo   3. run [3] printed the sparse34 banner and a 1.25bpw weight row
echo   4. check_smoke.py reported 0 errors
echo.
echo IF check_smoke REPORTS ERRORS, FIX THEM BEFORE RUNNING ANYTHING LONG.
echo   A missing field costs nothing here and costs a whole run later.
echo.
echo LIMIT: synthetic data, 30 steps, tiny preset. This proves the RECORDING works.
echo   It proves nothing about quality, speed, or whether the VRAM number is physically
echo   right - compare vram_reserved_gb against nvidia-smi once on a real run
echo   (expect nvidia-smi to be higher by the CUDA context, roughly 0.4-0.8GB).
echo ============================================================
echo done.
pause
