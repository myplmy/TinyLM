@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P038_wsd_recheck.bat  --  R7 : re-run the two candidates on the NEW
REM                                 standard schedule (--sched wsd)
REM  Roadmap: R7    Related plans: P026 (schedule), REVIEW1
REM =============================================================================
REM
REM WHY
REM   REVIEW1 compared mA and mC under the OLD standard schedule (cosine). The
REM   standard is now --sched wsd (CLAUDE.md). Relative comparisons stay valid
REM   under a shared schedule, so this is not urgent - but every future run will
REM   be wsd, and having the candidates only in cosine means every later
REM   comparison needs a footnote. This removes the footnote.
REM
REM CONDITIONS - do not change these without re-reading EXPERIMENT_BASELINES
REM   300M training tokens = steps x micro_bs x accum x seq
REM     2289 steps x 8 x 16 x 1024 = 300M     (effective batch 131k)
REM   --pool-tokens 600M --exact-cache   (result 006: a 300M pool costs 0.12)
REM   --lr 1e-3                          (result 017, confirmed for accum 16)
REM   --sched wsd --anneal-end 0.80 --decay-frac 0.2   (P026 alignment)
REM   --seed 1337                        (the standard seed; do not vary here)
REM   Presets carry the architecture: m100R1a = g4 + 3:4, m100R1c = g8.
REM   KD and parent init come from the command line, not the preset.
REM
REM READ THE 'final' NUMBER, NOT 'best'
REM   Result 015: reading 'best' flipped the sign of a verdict. best.pt selects a
REM   checkpoint, it does not judge a run. Periodic eval uses 50 iters and final
REM   uses 100 - they are different estimators.
REM
REM COST: about 4.3 hours of GPU for the pair.
REM ERRORLEVEL POLICY: the two runs are independent - a failure warns and the
REM   second still runs (result 007: one failure used to kill the whole sweep).
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [R7] wsd re-check of the two REVIEW1 candidates
echo =============================================================

echo.
echo =============================================================
echo [1/3] data pool - shared by both runs, so do this once
python scripts\runlog.py --name P038-wsd --note "[1/3] data pool - shared by both runs, so do this once"
echo =============================================================
python scripts\runlog.py --name P038-wsd -- python run100m.py prepare --data ko-en --tokens 600M --exact-cache
if errorlevel 1 goto DATABAD

echo.
echo =============================================================
echo [2/3] candidate C : m100R1c (g8, no 3:4) on wsd
python scripts\runlog.py --name P038-wsd --note "[2/3] candidate C : m100R1c (g8, no 3:4) on wsd"
echo =============================================================
python scripts\runlog.py --name P038-wsd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --kd --kd-every 4 --init-from --tag mC_wsd
if errorlevel 1 echo [WARN] mC_wsd failed - continuing to the next run

echo.
echo =============================================================
echo [3/3] candidate A : m100R1a (g4 + 3:4) on wsd
python scripts\runlog.py --name P038-wsd --note "[3/3] candidate A : m100R1a (g4 + 3:4) on wsd"
echo =============================================================
python scripts\runlog.py --name P038-wsd -- python run100m.py train --preset m100R1a --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --kd --kd-every 4 --init-from --tag mA_wsd
if errorlevel 1 echo [WARN] mA_wsd failed - read the traceback above

echo.
echo =============================================================
echo [post] paired comparison of the two new checkpoints
python scripts\runlog.py --name P038-wsd --note "[post] paired comparison of the two new checkpoints"
echo =============================================================
python scripts\runlog.py --name P038-wsd -- python scripts\paired_eval.py --models mA_wsd mC_wsd --seq 1024 --micro-bs 8
if errorlevel 1 echo [WARN] paired eval failed - the training logs still stand

echo.
echo =================================================================
echo WHAT TO RECORD
echo   1. final val loss for each run - the 'final' line, never 'best'
echo   2. grad_max from the json, not the printed 10-step sample
echo   3. packed_mb and runtime_mb for each (both, never one alone)
echo   4. the paired mean difference and SE from the post step
echo.
echo HOW TO READ IT
echo   gap within 0.024  -^> indistinguishable. Keep both candidates; the choice
echo       must then be made on memory and on R8, not on quality.
echo   gap over 0.024    -^> the first quality separation we have. Compare it
echo       against the cosine numbers in result 012 before concluding, because a
echo       schedule change can move both runs together.
echo.
echo LIMITS: one seed per arm, so this decides these two RUNS. Sigma is 0.012 and
echo   the resolution is 0.024 - do not rank differences below that.
echo =================================================================
echo done.
pause
exit /b 0

:DATABAD
echo.
echo =================================================================
echo [STOP] data preparation failed. Both runs depend on it, so nothing
echo   downstream was started.
echo =================================================================
pause
exit /b 1

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
