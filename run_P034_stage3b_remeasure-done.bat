@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P034_stage3b_remeasure.bat  --  P034 STAGE 3B : clean re-measurement
REM  Prior: result 016 sections 10 and 11
REM =============================================================================
REM
REM WHY THIS EXISTS
REM   The stage 3 speed numbers (result 016 section 10) were taken while P037
REM   stage 2B was running on the same machine - 04:08:47-04:12:14 against
REM   04:07:56-04:12:04, almost complete overlap. Result 015 had already measured
REM   that co-running costs about 14 percent; here it cost up to 21.7 percent, and
REM   it hit the int8 rows hardest.
REM
REM   Result 014 section 11 (P030 stage 4, run alone) already re-measured the two
REM   conditions that mattered at R=1.0, so the headline numbers ARE corrected in
REM   result 016 section 11.1. THIS BATCH IS THEREFORE OPTIONAL. It exists to put
REM   every condition - cpu and cuda, stage 2 and stage 2+3 - in ONE clean log so
REM   later citations do not have to cross-reference two documents.
REM
REM ***RUN THIS ALONE.***
REM   Close other training, inference and diagnostic jobs first. Speed numbers
REM   taken next to another job are not comparable to anything, including
REM   themselves. That is the entire reason this batch exists.
REM
REM COST: inference only, minutes.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P034-3B] clean re-measurement - RUN THIS WITH NOTHING ELSE RUNNING
echo =============================================================
python scripts\runlog.py --name P034-stage3b --note "[P034-3B] clean re-measurement - RUN THIS WITH NOTHING ELSE RUNNING"

echo.
echo [pre] machine load check - if anything heavy is running, stop and rerun later
python scripts\runlog.py --name P034-stage3b --note "[pre] machine load check"
python -c "import os;print('  CPU count', os.cpu_count())"

echo.
echo =============================================================
echo [1/4] CPU stage 2 (latent released)
echo =============================================================
python scripts\runlog.py --name P034-stage3b --note "[1/4] CPU stage 2 (latent released)"
python scripts\runlog.py --name P034-stage3b -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent
if errorlevel 1 echo [WARN] failed - continuing

echo.
echo =============================================================
echo [2/4] CPU stage 2 + 3 (int8)
echo =============================================================
python scripts\runlog.py --name P034-stage3b --note "[2/4] CPU stage 2 + 3 (int8)"
python scripts\runlog.py --name P034-stage3b -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] failed - continuing

echo.
echo =============================================================
echo [3/4] CUDA, both conditions - never measured cleanly for int8
echo =============================================================
python scripts\runlog.py --name P034-stage3b --note "[3/4] CUDA, both conditions"
python scripts\runlog.py --name P034-stage3b -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --drop-latent
if errorlevel 1 echo [WARN] failed - continuing
python scripts\runlog.py --name P034-stage3b -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] failed - continuing

echo.
echo =============================================================
echo [4/4] memory - unchanged by co-running, included only for one-log citation
echo =============================================================
python scripts\runlog.py --name P034-stage3b --note "[4/4] memory - unchanged by co-running, included for one-log citation"
python scripts\runlog.py --name P034-stage3b -- python scripts\mem_runtime.py --device cpu --max-new 32 --drop-latent --int8-store
if errorlevel 1 echo [WARN] failed - continuing

python scripts\runlog.py --name P034-stage3b --note "=================================================================" "WHAT TO RECORD" "  1. tok/s for every (device, condition). Compare against result 016 section" "     11.1 - the corrected column, not the section 10 column." "  2. whether the cpu numbers reproduce 36.78 / 45.01 / 42.48 (stage 2) and" "     14.20 / 14.89 / 15.08 (int8) from result 014 section 11." "  3. cuda int8 - this is the first clean measurement of it." "" "IF THE NUMBERS DIFFER FROM RESULT 014 SECTION 11 BY MORE THAN A FEW PERCENT" "  something else was running, or thermal state differs. Do not average the" "  two - find out which run was clean and use that one." "=================================================================" 
echo done.
pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
