@echo off
REM =============================================================================
REM  P053 (T-2)  -  chunked KD loss   (250-step VRAM triple, about 60 min)
REM
REM  WHAT AND WHY
REM    docs/methods/09_training_memory.md: the single largest training VRAM item
REM    is not the model, it is the KD loss over the full vocabulary - +5.48 GiB
REM    allocated, of which the teacher's own parameters are only 945 MB.
REM    At mb8 x seq1024 x vocab 32768 an fp32 tensor is exactly 1024 MiB, and
REM    several of them are alive at once:
REM        logits/T   log_softmax(...)   tlog/T   softmax(tlog/T)
REM
REM    --kd-chunk N computes the KL N rows at a time. The teacher-side tensors
REM    need no grad and are freed per chunk.
REM
REM  !! HONEST EXPECTATION
REM    Chunking CANNOT free what backward must keep (the student log_softmax).
REM    It frees the simultaneous temporaries. Expect about -2 to -3 GiB, not the
REM    whole 5.48. If the batch shows more than that, suspect the measurement.
REM
REM  !! NOT BIT IDENTICAL WHEN ON
REM    Summation order changes. chunk=0 takes the old expression untouched, so
REM    OFF is bit identical; ON is not. The 250-step val is NOT how we check
REM    that - it is checked by the loss curve of the first steps matching to
REM    about 1e-3, which is what the third run below is for.
REM
REM  !! THIS EXPERIMENT MAY BE POINTLESS
REM    Result 038 says removing KD entirely frees 7.41 GiB at no quality cost.
REM    If REVIEW2 drops KD from the standard condition, there is no KD loss left
REM    to chunk. ***Run this only if REVIEW2 keeps KD.***
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo =============================================================================
echo  P053   KD loss chunking   3 x 250 steps   about 60 minutes
echo.
echo  !! Has REVIEW2 decided to KEEP KD in the standard condition?
echo    If not, stop here - result 038 makes this measurement moot.
echo =============================================================================
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P053_kd_chunk --note "[P053/T-2] KD KL chunking VRAM triple. chunk 0 (off) vs 2048 vs 1024. Expect -2 to -3 GiB, not -5.48."

python scripts\runlog.py --name P053_kd_chunk -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --compile --init-from --kd --kd-every 4 --kd-chunk 0 --tag mC_kdc_off250
if errorlevel 1 echo [WARN] chunk off run returned an error - continuing

echo.
echo [queue] settling 15 s - WDDM holds VRAM after a process exits (result 037 s7)
timeout /t 15 /nobreak

python scripts\runlog.py --name P053_kd_chunk -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --compile --init-from --kd --kd-every 4 --kd-chunk 2048 --tag mC_kdc_2048_250
if errorlevel 1 echo [WARN] chunk 2048 run returned an error - continuing

echo.
echo [queue] settling 15 s
timeout /t 15 /nobreak

python scripts\runlog.py --name P053_kd_chunk -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --compile --init-from --kd --kd-every 4 --kd-chunk 1024 --tag mC_kdc_1024_250
if errorlevel 1 echo [WARN] chunk 1024 run returned an error - continuing

echo.
echo =============================================================================
echo  Read from runs\logs\*.json:
echo    peak_reserved_gib   off vs 2048 vs 1024    expect -2 to -3, not -5.48
echo    kd_chunk            0 / 2048 / 1024        else the flag did nothing
echo    ms_step_median      smaller chunk = more python loop iterations = slower
echo    the first eval loss of the three runs should agree to about 1e-3
echo      - that is the numerical equivalence check, not the 250-step val
echo  Do NOT read val as quality. 250 steps decides nothing (baselines s2.3).
echo =============================================================================
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
