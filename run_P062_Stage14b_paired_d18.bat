@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage14b_paired_d18.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage14 and Stage16 produced four numbers and NONE of them is on the
REM     authoritative scale. Both logs contain training arms only - no paired_eval.
REM     The same checkpoint reads 3.5139 in the training log and 3.5389 on the
REM     deterministic full-val: a gap of 0.0250, which is 10.4x the norecur ruler.
REM     So the 40-budget ordering written in result 047 section 18.4 rests on a
REM     ruler that can flip signs (result 040 section 2).
REM
REM   READ IN THIS ORDER
REM     1. Arm 1 puts the three depth-18 checkpoints on the full-val scale.
REM        The seed pair also becomes a real ruler point (the log-val 0.0001 is not one).
REM     2. Arm 2 puts the recursive Muon winner next to the norecur Muon twin.
REM     3. Cross-preset pairs (d18 vs d16) are NOT valid inside one paired_eval call.
REM        Use scripts\paired_join.py afterwards if you need that comparison.
REM     4. --ckpt-tokens 300M is mandatory: checkpoints are named 300M, the val
REM        cache is 600M. Without it paired_eval exits 2 (trap 28, sixth face).
REM
REM   COST: about 0.1h, no training.   PLAN: test_plan/P062 stage14b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage14b_paired_d18 --note "[1/2] depth 18 - three checkpoints onto the deterministic full-val scale"
python scripts\runlog.py --name P062_stage14b_paired_d18 -- python scripts\paired_eval.py --preset m100s14 --data ko-en --tokens 600M --ckpt-tokens 300M --models d18_cla2_norecur d18_cla2_norecur_s2 d18_cla2_norecur_muon15
if errorlevel 1 echo [WARN] arm 1 failed - continuing

python scripts\runlog.py --name P062_stage14b_paired_d18 --note "[2/2] depth 16 - recursion with Muon against the norecur Muon twin"
python scripts\runlog.py --name P062_stage14b_paired_d18 -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 600M --ckpt-tokens 300M --models d16_cla2_r20_muon15 d16_cla2_norecur_muon15 d16_cla2_norecur
if errorlevel 1 echo [WARN] arm 2 failed - continuing

python scripts\runlog.py --name P062_stage14b_paired_d18 --note "DONE. Read the seed pair first - it is the depth-18 ruler and it decides how to read the rest."

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
