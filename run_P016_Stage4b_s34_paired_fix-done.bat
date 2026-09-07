@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P016_Stage4b_s34_paired_fix.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage4 exited 2. paired_eval could not resolve the checkpoints because
REM     --tokens names BOTH the val cache size AND the checkpoint filename, and
REM     the held-out rule wants 600M while the file is named 300M (trap 28).
REM     --ckpt-tokens now splits the two roles. This arm is the same judgement
REM     with that one flag added.
REM
REM   PRE-REGISTERED, unchanged from Stage3 (result 008 section 9.3)
REM     at or below +0.01607   inside the lever line
REM     +0.01607 to +0.0364    grey, 40 MiB budget only
REM     above +0.0364          the axis stays closed
REM
REM   READ THIS FIRST: which ruler the tool printed. Both arms are dense with
REM     --train-repeat 2.0 so it should pick the recursion ruler 0.0018.
REM
REM   NO TRAINING. COST: about 0.1h.   PLAN: test_plan/P016 Stage4b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P016_stage4b_s34_paired_fix --note "[1/1] paired_eval with --ckpt-tokens - the flag Stage4 was missing"
python scripts\runlog.py --name P016_stage4b_s34_paired_fix -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_r20 d12_cla2_r20_s34 --match-train-repeat
if errorlevel 1 echo [WARN] paired_eval failed - read the ckpt resolution lines first - continuing

python scripts\runlog.py --name P016_stage4b_s34_paired_fix --note "DONE. Compare the delta with the three rows in this batch header. Do not invent a threshold after seeing the number."

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
