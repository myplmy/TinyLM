@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage16_recur_muon40.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     User instruction 4B: do not close recursion. Correct - and result 076 section 10.2
REM     showed Muon is orthogonal to architecture, so an architecture comparison is only
REM     fair with the optimiser matched. Right now only the no-recursion side has Muon.
REM     This arm is the QUALITY CEILING probe, not a deployment candidate.
REM
REM   READ IN THIS ORDER
REM     1. Against d16_cla2_r20 3.51578. Predicted about 3.480.
REM     2. This model is 10.33 tok/s and FAILS the speed floor - always say so when quoting it.
REM     3. Its value is: what do we get back if LUT, block recursion or narrow width lands.
REM     4. grad_max on a recursive body with Muon has never been seen. Watch n_skip.
REM
REM   COST: about 2.2h.   PLAN: test_plan/P062 stage16
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage16_recur_muon40 --note "[1/1] depth 16 recursion R2 plus muon x15 - the quality ceiling"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage16_recur_muon40 -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_cla2_r20_muon15
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d16_cla2_r20_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage16_recur_muon40 --note "DONE. grad_max on a recursive body with Muon has never been seen. Watch n_skip."

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
