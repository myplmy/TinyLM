@echo off
REM ===== P021B : micro_bs re-sweep BELOW the spill wall (result 007 additional check B) =====
REM   Follow-up to result 007. Template reused from run100m_P021.bat, different file so the
REM   original P021 record stays untouched.
REM
REM THE CONFOUND WE ARE REMOVING
REM   Result 007 concluded "micro_bs up gives zero gain, we are compute bound". The evidence:
REM     mb8  / accum16 / seq1024  -^> 2467 ms/step, 13.5GB
REM     mb10 / accum13 / seq1024  -^> 2481 ms/step, 15.2GB  (minus 0.9pct per token = noise)
REM     mb12 / accum11 / seq1024  -^> OOM (needs 16.8-17GB)
REM   But 15.2GB is ALREADY ABOVE the WDDM spill wall (13-14GB). So we could not tell
REM   "no gain because compute bound" apart from "no gain because it was spilling".
REM
REM THE FIX: cut seq to 512 so VRAM drops, then raise micro_bs INSIDE the safe zone.
REM   Effective batch is held at 131,072 tokens/step in every run (mb x accum x seq), so
REM   ms/step is directly comparable without per-token renormalisation.
REM     B1  mb8  x accum32 x seq512 = 131,072
REM     B2  mb16 x accum16 x seq512 = 131,072
REM     B3  mb24 x accum11 x seq512 = 135,168  (about 3pct high, renormalise if it survives)
REM
REM   B1 vs B2 is the clean test. If B2 is not faster than B1 while both stay under 14GB,
REM   micro_bs is dead for good. If B2 IS faster, then "compute bound" was wrong and the real
REM   limit is VRAM, which changes what seq-warmup (P013) is worth.
REM
REM WHAT THIS BATCH DOES NOT TELL YOU
REM   seq512 halves the attention cost per token, so these ms/step values are NOT comparable to
REM   the seq1024 numbers in result 007. Only compare B1/B2/B3 with each other.
REM   And 250-step runs say NOTHING about quality (result 007 section 2-(4)) - do not read val.
REM
REM RECORD nvidia-smi VRAM for every run. Without it the whole point is lost.
REM
REM COST: 3 runs x about 12min = about 36min. Cheap.
REM ERRORLEVEL POLICY: all runs independent, failures only warn (that is the result 007 lesson).

echo === [1/3] B1 baseline: mb8 x accum32 x seq512 ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 250 --micro-bs 8 --accum 32 --seq 512 --lr 1e-3 --eval-every 999 --compile --no-ckpt --tag spb_mb8_s512
if errorlevel 1 echo [WARN] B1 failed - continuing

echo === [2/3] B2 the actual test: mb16 x accum16 x seq512 ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 250 --micro-bs 16 --accum 16 --seq 512 --lr 1e-3 --eval-every 999 --compile --no-ckpt --tag spb_mb16_s512
if errorlevel 1 echo [WARN] B2 failed - continuing

echo === [3/3] B3 push further: mb24 x accum11 x seq512 (may OOM, that is fine) ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 250 --micro-bs 24 --accum 11 --seq 512 --lr 1e-3 --eval-every 999 --compile --no-ckpt --tag spb_mb24_s512
if errorlevel 1 echo [WARN] B3 failed or OOM - that is a valid result, continuing

echo.
echo ================================================================
echo HOW TO READ (speed only, quality is meaningless at 250 steps):
echo.
echo 1. Convert every run to STEADY STATE first. The printed ms/step is a RUNNING AVERAGE that
echo    still contains the multi-second compile step:
echo        steady = (printed_avg x 250 - step0_ms) / 249
echo.
echo 2. B1 vs B2, both at effective batch 131,072 - compare steady ms/step directly.
echo        B2 not faster, both under 14GB  -^> micro_bs is FINALLY dead. Compute bound confirmed
echo                                           with the spill confound removed. Close P021B.
echo        B2 faster                       -^> "compute bound" was wrong. The mb10 result was a
echo                                           spill artifact. Revisit seq-warmup (P013) and
echo                                           reconsider mb for the tied+KD line too.
echo.
echo 3. B3 is at 135,168 tokens/step, so divide its ms/step by 1.031 before comparing.
echo    If B3 OOMs, write down the VRAM it asked for - that is the ceiling for seq512.
echo.
echo 4. WRITE DOWN nvidia-smi VRAM per run. A run above 14GB is spilling and its timing is
echo    not evidence about compute.
echo.
echo NOTE ON SIGMA: the reproduction-noise run that used to live here as check A has MOVED into
echo   run100m_REVIEW1.bat as run [1] (p6d_s2, seed 2024). It is measured on the 2289-step
echo   baseline that REVIEW1 actually compares against, which is where the number is needed.
echo   A same-seed repeat (numeric nondeterminism alone, without seed variance) is only worth
echo   running if REVIEW1 reports a surprisingly large sigma - it would tell us whether the
echo   spread comes from kernel nondeterminism or from initialisation and data order.
echo ================================================================
echo done.
pause
