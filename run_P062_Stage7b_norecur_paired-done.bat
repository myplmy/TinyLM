@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage7b_norecur_paired.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage7 trained d12_cla2_norecur for 71 minutes and then its judgement arm
REM     exited 2 on the same defect as P016 Stage4. 1.2h of training produced no
REM     verdict. --ckpt-tokens fixes it.
REM
REM   NO --match-train-repeat HERE. Only one of the two models was trained with
REM     recursion, so each must be evaluated at the schedule it learned. Matching
REM     them would evaluate a function neither model was trained for (trap 39,
REM     pointing the other way). Expect the printed visit counts to DIFFER: 20
REM     for d12_cla2_r20 and 12 for d12_cla2_norecur. That is correct here.
REM
REM   PRE-REGISTERED, unchanged from Stage7  delta = norecur minus recur
REM     at or below +0.0100   drop recursion, buy the speed
REM     +0.0100 to +0.0250    grey, user decision
REM     above +0.0250         recursion earns its keep
REM     The training log said +0.03312, i.e. the third row. Log val is a sample.
REM
REM   NO TRAINING. COST: about 0.1h.   PLAN: test_plan/P062 Stage7b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage7b_norecur_paired --note "[1/1] the judgement Stage7 could not make"
python scripts\runlog.py --name P062_stage7b_norecur_paired -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_r20 d12_cla2_norecur
if errorlevel 1 echo [WARN] paired_eval failed - read the ckpt resolution lines first - continuing

python scripts\runlog.py --name P062_stage7b_norecur_paired --note "DONE. The three pre-registered rows are in this header. Also note which ruler the tool chose - the pair mixes recursion with no recursion, so read the printed family."

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
