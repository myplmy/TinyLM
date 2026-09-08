@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage14_depth18.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     No-recursion residency is 9.0 + 1.585 x L so 40 MiB allows L up to 19.6, and the
REM     speed floor allows up to 19 visits. 18 layers is the deepest even depth that
REM     satisfies both: 37.5 MiB and about 15.6 tok/s predicted.
REM     The preset m100s14 is new. Depth curve says 16 to 18 buys about -0.019.
REM
REM   READ IN THIS ORDER
REM     1. grad_max and n_skip first. 18 layers is the deepest we have trained no-recursion.
REM     2. Arm 1 minus d16_cla2_norecur 3.55016 is the depth step.
REM     3. Arm 2 minus arm 1 is Muon on the deepest shape.
REM     4. Arm 3 is the seed replica - it gives the ruler AT THIS DEPTH.
REM     5. The predicted 15.6 tok/s is a MODEL. P085 Stage8 measures it.
REM
REM   COST: about 4.8h.   PLAN: test_plan/P062 stage14
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage14_depth18 --note "[1/3] depth 18 no recursion - preset m100s14, new"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage14_depth18 -- python run100m.py train --preset m100s14 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d18_cla2_norecur
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d18_cla2_norecur
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage14_depth18 --note "[2/3] depth 18 plus muon x15 - predicted best 40 MiB model we would have"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage14_depth18 -- python run100m.py train --preset m100s14 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d18_cla2_norecur_muon15
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d18_cla2_norecur_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage14_depth18 --note "[3/3] depth 18 seed replica 2024 - the ruler at this depth"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage14_depth18 -- python run100m.py train --preset m100s14 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d18_cla2_norecur_s2
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d18_cla2_norecur_s2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage14_depth18 --note "DONE. The predicted 15.6 tok/s is a MODEL. P085 Stage8 measures it."

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
