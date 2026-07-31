@echo off
REM ===== P026 stage 5 : the missing cell - wsd WITHOUT alignment at the cut step count =====
REM   Plan: test_plan\P026 (stage 5)    Previous result: test_result\015
REM
REM ***** THE ONE QUESTION *****
REM   Result 015 showed the 15 percent step cut lands on the cosine baseline:
REM     qb_wsd80_s85 (wsd, anneal 0.80, 1946 steps)  minus  qb_cos (cosine, 2289 steps)
REM       equals plus 0.0050, which is 0.4 sigma - a tie.
REM   But the alignment ITSELF was not detectable at full steps:
REM     qb_wsd80 minus qb_wsd60 equals minus 0.0128, which is 1.1 sigma - below the
REM     0.024 resolution, so no ranking is allowed.
REM   So we cannot say whether the step cut is bought by wsd or by the alignment.
REM   This run fills the empty cell: wsd, anneal 0.60 (NOT aligned), 1946 steps.
REM
REM   INDEPENDENT VARIABLE: --anneal-end only. 0.80 becomes 0.60. Everything else is
REM   byte-identical to qb_wsd80_s85 - same pool, same seed, same steps, same batch.
REM
REM ***** PREFLIGHT (docs\EXPERIMENT_BASELINES.md) *****
REM   train tokens  1946 x 8 x 16 x 1024 = 255,066,112. Matches qb_wsd80_s85 exactly.
REM                 This is deliberately NOT 300M - it must match its comparand, not the
REM                 standard budget.
REM   pool          600M with --exact-cache. Over 2x the train tokens. Same pool as all
REM                 four runs in result 015, so the comparison is valid.
REM   tag           qb_wsd60_s85 - not present in runs\logs, no collision, does not touch
REM                 the canonical dense or tied names.
REM   grad ckpt     off on both sides, so no checkpoint drift is mixed in.
REM   VRAM          12.69GB reserved measured on the identical config. Under the spill wall.
REM   time          about 82 minutes, single run.
REM
REM ***** A NOTE ON THE MISSING [sched] LINE *****
REM   trainer prints the [sched] diagnostic ONLY when anneal_end is not 0.60 or decay_frac
REM   is not 0.2. This run uses both defaults, so the line will NOT appear. That absence is
REM   the confirmation, not a bug. The json records anneal_end and decay_frac either way.
REM
REM ERRORLEVEL POLICY: prepare is a hard stop - everything depends on the cache being the
REM   same 600M pool. The compares only warn.

echo ============================================================
echo [P026 stage 5] qb_wsd60_s85 : wsd, anneal 0.60, 1946 steps
echo ============================================================

echo.
echo [prep] making sure the 600M exact pool is the one being used
python run100m.py prepare --data ko-en --tokens 600M --exact-cache
if errorlevel 1 goto ERROR

echo.
echo ============================================================
echo [1/2] TRAIN  wsd, anneal-end 0.60 (NOT aligned), 1946 steps
echo ============================================================
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 1946 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --pool-tokens 600M --exact-cache --sched wsd --anneal-end 0.60 --decay-frac 0.2 --tag qb_wsd60_s85
if errorlevel 1 echo [WARN] qb_wsd60_s85 failed - the compares below will be empty

echo.
echo ============================================================
echo [2/2] COMPARES
echo ============================================================
echo --- the deciding one : alignment at the cut step count ---
python run100m.py compare --tag qb_wsd80_s85 --vs qb_wsd60_s85
if errorlevel 1 echo [WARN] compare failed - continuing
echo --- does wsd alone also reach the cosine baseline with 15 percent fewer steps ---
python run100m.py compare --tag qb_cos --vs qb_wsd60_s85
if errorlevel 1 echo [WARN] compare failed - continuing
echo --- what the 15 percent cut costs under wsd60 ---
python run100m.py compare --tag qb_wsd60 --vs qb_wsd60_s85
if errorlevel 1 echo [WARN] compare failed - continuing

echo.
echo ================================================================
echo READ IN THIS ORDER - and use the FINAL val, never best
echo   best comes from a 50-iteration eval and is the minimum of 20-plus draws, so it is
echo   biased low by an amount that depends on how many evals ran. final uses 100
echo   iterations. In result 015 reading best flipped the sign of the verdict.
echo.
echo   1. qb_wsd60_s85 vs qb_wsd80_s85 - this is the answer
echo        difference within 0.024   ALIGNMENT IS NOT NEEDED. wsd alone did it.
echo                                  Standard condition becomes sched wsd, anneal-end
echo                                  stays 0.60. Nothing else changes.
echo        qb_wsd80_s85 clearly lower ALIGNMENT MATTERS at short budgets. Standardise
echo                                  sched wsd together with anneal-end 0.80.
echo        qb_wsd60_s85 clearly lower ALIGNMENT HURTS at short budgets. Unexpected -
echo                                  record it and do not standardise either way yet.
echo   2. qb_cos vs qb_wsd60_s85 - a second, independent check of the same thing
echo   3. qb_wsd60 vs qb_wsd60_s85 - the price of the cut under wsd60, to compare against
echo        the plus 0.0933 that qb_wsd80 paid for the same cut
echo.
echo REFERENCE (result 015, final val, same pool, same seed)
echo   qb_cos 3.7030   qb_wsd60 3.6275   qb_wsd80 3.6147   qb_wsd80_s85 3.7080
echo   sigma is 0.012, so the resolution is 0.024. Do not rank anything closer than that.
echo.
echo AFTER THIS RUN
echo   Update docs\EXPERIMENT_BASELINES.md section 1 schedule row. It was deliberately
echo   left as cosine after result 015 so that a wrong reason would not get recorded.
echo ================================================================
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: prepare failed, so the data pool is not guaranteed to be the same
echo        600M exact cache the result 015 runs used. Comparing against them would be
echo        invalid, so nothing was trained.
pause
exit /b 1
