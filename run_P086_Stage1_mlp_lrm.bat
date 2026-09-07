@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P086_Stage1_mlp_lrm.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     mlp_lrm has been implemented and smoked since 2026-09-05 and its quality has
REM     never been measured. User instruction 4A reopened the mlp_group axis, and this
REM     is the only implemented lever that targets the tying penalty directly.
REM     Both arms are new so the pair is clean - the old d16_g4 is from another session.
REM
REM   READ IN THIS ORDER
REM     1. Arm 2 minus arm 1 is the whole experiment. Same session, same code.
REM     2. The tied ruler is 0.0006, so even -0.002 is significant.
REM     3. Significant is not the same as worth it - the bar is one depth step, -0.0115.
REM     4. mlp_lrm carries weight decay 0.01. Check grad_max does not drift.
REM
REM   COST: about 3.0h.   PLAN: test_plan/P086 stage1
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P086_stage1_mlp_lrm --note "[1/2] tied g4 at depth 16 - the control, no lrm"
timeout /t 15 /nobreak
python scripts\runlog.py --name P086_stage1_mlp_lrm -- python run100m.py train --preset m100s12 --arch tied --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --mlp-group 4 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_g4_base
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d16_g4_base
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P086_stage1_mlp_lrm --note "[2/2] tied g4 at depth 16 plus per-layer scale"
timeout /t 15 /nobreak
python scripts\runlog.py --name P086_stage1_mlp_lrm -- python run100m.py train --preset m100s12 --arch tied --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --mlp-group 4 --mlp-lrm --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_g4_lrm
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d16_g4_lrm
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P086_stage1_mlp_lrm --note "DONE. mlp_lrm carries weight decay 0.01. Check grad_max does not drift."

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
