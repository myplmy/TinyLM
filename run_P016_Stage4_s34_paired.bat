@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P016_Stage4_s34_paired.bat -- the verdict tool the last batch forgot
REM ==========================================================================
REM
REM   WHY THIS EXISTS
REM     run_P016_Stage3 printed "judge with paired_eval against d12_cla2_r20"
REM     in its own tail note and then did not contain a paired_eval arm.
REM     So the +0.04203 in result 008 section 6 is a TRAINING-LOG val, which
REM     rule R10 says is a random-crop sample and not the verdict instrument.
REM
REM   IT ALMOST CERTAINLY WILL NOT FLIP
REM     both runs share pool, seed, steps and val crop, and the delta is 20.0x
REM     the dense ruler of 0.0021. But "almost certainly" is not a measurement,
REM     and the pre-registered threshold (+0.0364) sits only 0.0056 below the
REM     observed value, so a small shift matters for which verdict row applies.
REM
REM   BOTH MODELS USED THE 600M POOL
REM     therefore --tokens 600M is the correct eval cache. The 300M val is
REM     INSIDE the 600M train (result 075 section 6) so the default would
REM     score them on their own training data.
REM
REM   --match-train-repeat IS REQUIRED
REM     both were trained with --train-repeat 2.0. Without this flag the
REM     evaluation runs a function that was never trained (trap 39).
REM
REM   NO TRAINING. Inference only. COST: about 0.1h.
REM   PLAN: test_plan/P016 (Korean filename) Stage4
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P016_stage4_s34_paired --note "[1/1] paired_eval on the 600M cache - both models pooled 600M"
python scripts\runlog.py --name P016_stage4_s34_paired -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --models d12_cla2_r20 d12_cla2_r20_s34 --match-train-repeat
if errorlevel 1 echo [WARN] paired_eval failed - continuing

echo.
python scripts\runlog.py --name P016_stage4_s34_paired --note "=================================================================" "READ IN THIS ORDER" "1. which ruler the tool says it used. Both arms are --arch dense" "   with --train-repeat 2.0, so it should pick the recursion ruler" "   0.0018, not the dense 0.0021. Either way the delta is far above." "2. the paired delta. Compare it with the PRE-REGISTERED rows that" "   were written before Stage3 ran:" "     at or below +0.0225  inside the lever line" "     +0.0225 to +0.0364   grey, 40 MiB budget only" "     above +0.0364        close the axis for good" "   The training-log val said +0.04203, i.e. the third row." "3. if paired_eval lands in the grey band instead, say so plainly" "   and reopen - do NOT keep the closed verdict because it is tidier." "4. this does not measure the SAVING. That is arithmetic and is in" "   result 008 section 6.3 (3.027 and 4.035 MiB)." "================================================================="

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
