@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage13_block_recursion.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     config.REPEAT_MODES has four modes. Across ALL 51 recursion runs we have used
REM     uniform 49 times and inplace twice. block and progressive have ZERO runs.
REM     User instruction 4B named exactly this: recursion on SOME layers only.
REM     It matters because uniform R2 doubles visits and the speed floor caps visits at 19,
REM     while block repeats one group and only adds a few visits.
REM
REM   READ IN THIS ORDER
REM     1. Read the visit_schedule line FIRST. The predicted visit counts are estimates.
REM     2. Any arm above 19 visits fails the speed floor - that is an answer too.
REM     3. Pre-registered thresholds are in the plan. Do not invent one after seeing the number.
REM     4. Each arm pairs with the no-recursion run at the SAME depth.
REM     5. repeat_block default decides which group repeats - do not generalise from one setting.
REM
REM   COST: about 5.5h.   PLAN: test_plan/P062 stage13
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage13_block_recursion --note "[1/3] depth 14 block recursion R2 - repeat one MLP group only"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage13_block_recursion -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --repeat-mode block --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d14_cla2_blockr2
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d14_cla2_blockr2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage13_block_recursion --note "[2/3] depth 16 block recursion R2"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage13_block_recursion -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --repeat-mode block --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_cla2_blockr2
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d16_cla2_blockr2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage13_block_recursion --note "[3/3] depth 14 progressive recursion R2 - deeper layers repeat more"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage13_block_recursion -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --repeat-mode progressive --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d14_cla2_progr2
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d14_cla2_progr2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage13_block_recursion --note "DONE. repeat_block default decides which group repeats - do not generalise from one setting."

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
