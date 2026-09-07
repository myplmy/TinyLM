@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage9_speed_tokens.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     The speed floor pinned depth at 12 to 16. Tokens are the only quality
REM     lever left that costs ZERO deployment residency, and result 075 s14.7
REM     showed a bigger pool beating more epochs at half the GPU time.
REM
REM   THREE ARMS - same 600M training tokens, pool 1200M, ratio 2.0 as the rule
REM     wants. Depth 12, 14, 16 without recursion.
REM
REM   PREREQUISITE: P062 Stage8. Not for the checkpoints - these are fresh runs -
REM     but because spending 8.4h on the token axis before knowing the depth
REM     answer confounds the two.
REM
REM   POOL DIFFERS FROM THE 300M RUNS, so log val is NOT comparable across them.
REM     Read these against each other, and against the 300M runs only through
REM     common_bpb (P088 Stage7 gives that ruler).
REM
REM   READ IN THIS ORDER
REM     1. grad_max and n_skip for all three.
REM     2. within this batch the three are comparable: same pool, same steps.
REM     3. the two-axis law predicts -0.0739 bpb, about -0.224 nats, from 300M
REM        to 600M tokens. That is 3.5 times what four layers of depth buys.
REM     4. if the law misses badly, it does not live in the no-recursion family.
REM        That is a result, not a failure.
REM
REM   COST: about 8.4h.   PLAN: test_plan/P062 Stage9
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage9_speed_tokens --note "[1/3] depth 12, 600M tokens, pool 1200M"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage9_speed_tokens -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 4578 --tokens 600M --pool-tokens 1200M --exact-cache --tag d12_cla2_norecur_t600
if errorlevel 1 echo [WARN] d12 t600 failed - continuing
set TL_WB_TAG=d12_cla2_norecur_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage9_speed_tokens --note "[2/3] depth 14, 600M tokens, pool 1200M"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage9_speed_tokens -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 4578 --tokens 600M --pool-tokens 1200M --exact-cache --tag d14_cla2_norecur_t600
if errorlevel 1 echo [WARN] d14 t600 failed - continuing
set TL_WB_TAG=d14_cla2_norecur_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage9_speed_tokens --note "[3/3] depth 16, 600M tokens, pool 1200M"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage9_speed_tokens -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 4578 --tokens 600M --pool-tokens 1200M --exact-cache --tag d16_cla2_norecur_t600
if errorlevel 1 echo [WARN] d16 t600 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage9_speed_tokens --note "DONE. These three share a pool so they compare to each other. Against the 300M runs use common_bpb only."

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
