@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage9b_speed_tokens_fix.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage9 died three for three. --init-from built the parent filename out of --tokens,
REM     so asking for 600M of data also asked for a 600M parent that does not exist.
REM     --ckpt-tokens 300M splits the two. Design and verdict are Stage9 unchanged.
REM
REM   READ IN THIS ORDER
REM     1. The three arms share a pool so they compare to each other.
REM     2. Against the 300M runs use common_bpb only - the pool differs.
REM     3. Pool over tokens is 2.0 here, inside the standard.
REM     4. Arm 2 minus arm 1 and arm 3 minus arm 2 give the depth step at 600M tokens.
REM
REM   PREREQUISITE
REM     None. The parent m100_ko-en_300M_dense.pt already exists.
REM
REM   COST: about 8.0h.   PLAN: test_plan/P062 stage9b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage9b_speed_tokens_fix --note "[1/3] depth 12, 600M tokens, pool 1200M"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage9b_speed_tokens_fix -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d12_cla2_norecur_t600
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_norecur_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage9b_speed_tokens_fix --note "[2/3] depth 14, 600M tokens, pool 1200M"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage9b_speed_tokens_fix -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d14_cla2_norecur_t600
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d14_cla2_norecur_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage9b_speed_tokens_fix --note "[3/3] depth 16, 600M tokens, pool 1200M"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage9b_speed_tokens_fix -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d16_cla2_norecur_t600
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage9b_speed_tokens_fix --note "DONE. Arm 2 minus arm 1 and arm 3 minus arm 2 give the depth step at 600M tokens."

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
