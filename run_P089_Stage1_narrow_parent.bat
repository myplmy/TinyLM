@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P089_Stage1_narrow_parent.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage0a passed: dim 512 at 28 layers is 31.1 MiB and 15.55 tok/s, so the
REM     same 32 MiB budget buys twice the depth AND clears the speed floor.
REM     Quality is still zero runs, and Stage2 cannot be fair without a parent -
REM     our only dense parent is dim 768 and the matrices do not line up
REM     (Stage0a ran with no --init-from at all).
REM
REM   READ IN THIS ORDER
REM     1. This is a PARENT, so there is no --init-from. It trains from scratch.
REM     2. Tag it. The child in Stage2 must use --init-from-tag w512_d20_parent.
REM        Without the tag the global checkpoint search can pick the dim 768 parent
REM        and the width comparison silently becomes something else.
REM     3. Preset m100w512s16 is dim 512, 20 layers - the same depth as our existing
REM        dense parent, so the two parents differ in width only.
REM     4. val here is comparable to other 600M-pool runs, but the SHAPE is new -
REM        do not rank it against dim 768 runs. It exists to be initialised from.
REM
REM   COST: about 2.0h.   PLAN: test_plan/P089 stage1
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P089_stage1_narrow_parent --note "[1/1] narrow dense parent - dim 512, 20 layers, from scratch"
timeout /t 15 /nobreak
python scripts\runlog.py --name P089_stage1_narrow_parent -- python run100m.py train --preset m100w512s16 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag w512_d20_parent
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=w512_d20_parent
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P089_stage1_narrow_parent --note "DONE. Stage2 must pass --init-from-tag w512_d20_parent. Do not rank this val against dim 768."

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
