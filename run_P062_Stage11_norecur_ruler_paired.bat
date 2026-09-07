@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage11_norecur_ruler_paired.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage10 measured the no-recursion ruler from TRAINING LOG val: 0.00133 / 0.00221 / 0.00264.
REM     Every ruler in scripts/_rulers.py comes from paired_eval deterministic full-val.
REM     Log val is a random crop sample and OVERSTATES the ruler (R10). Do not mix the two.
REM     Until this batch runs, 0.00264 is provisional and must be quoted as log-val based.
REM
REM   READ IN THIS ORDER
REM     1. The paired ruler should be SMALLER than the log-val one. 0.0008 to 0.0020 expected.
REM     2. If it comes out above 0.0030, some depth verdicts fall inside the ruler.
REM     3. Three separate calls because paired_eval takes one preset.
REM     4. --ckpt-tokens 300M: the models trained on a 600M pool but the file says 300M.
REM
REM   COST: about 0.4h, no training.   PLAN: test_plan/P062 stage11
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage11_norecur_ruler_paired --note "[1/3] depth 12 seed pair"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage11_norecur_ruler_paired -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_norecur d12_cla2_norecur_s2
if errorlevel 1 echo [WARN] arm 1 failed - continuing

python scripts\runlog.py --name P062_stage11_norecur_ruler_paired --note "[2/3] depth 14 seed pair"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage11_norecur_ruler_paired -- python scripts\paired_eval.py --preset m100s10 --data ko-en --tokens 600M --ckpt-tokens 300M --models d14_cla2_norecur d14_cla2_norecur_s2
if errorlevel 1 echo [WARN] arm 2 failed - continuing

python scripts\runlog.py --name P062_stage11_norecur_ruler_paired --note "[3/3] depth 16 seed pair - this one gave the largest log-val gap"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage11_norecur_ruler_paired -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 600M --ckpt-tokens 300M --models d16_cla2_norecur d16_cla2_norecur_s2
if errorlevel 1 echo [WARN] arm 3 failed - continuing

python scripts\runlog.py --name P062_stage11_norecur_ruler_paired --note "DONE. --ckpt-tokens 300M: the models trained on a 600M pool but the file says 300M."

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
