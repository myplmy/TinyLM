@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P087_Stage3_tokens_x_repeat.bat -- do the two free axes add up?
REM ==========================================================================
REM
REM   THE CLAIM THIS TESTS
REM     REVIEW3 v2 plan B says the 32 MiB winner can be improved by about
REM     -0.18 nats without spending one byte of residency, by stacking two
REM     measured results:
REM       double the steps      -0.107   (result 075, 1.2B pool)
REM       four epochs on top    -0.074   (result 073, 300M pool)
REM     Those were measured on DIFFERENT pools and were never stacked. If
REM     they overlap, plan B's number is wrong and the review has to be
REM     rewritten before anyone spends 20 GPU hours on it.
REM
REM   DESIGN - one arm, because the three comparison points already exist
REM     600M pool, 1200M tokens = 2.0 epochs over a pool twice the standard.
REM     Against the existing points:
REM       d12_cla2_r20              600M pool,  300M tokens, 0.5 epoch
REM       d12_cla2_r20_p300_e2      300M pool,  600M tokens, 2.0 epochs
REM       d12_cla2_r20_p12_t600    1200M pool,  600M tokens, 0.5 epoch
REM     This arm is the first point that has BOTH a large pool AND repeated
REM     exposure. Its own val.bin is the 600M cache, same as the standard
REM     baseline, so the comparison against d12_cla2_r20 needs no caveat.
REM
REM   WHAT ADDITIVITY WOULD LOOK LIKE
REM     against d12_cla2_r20 the additive prediction is about -0.18.
REM     much smaller  gives the axes overlap, plan B is optimistic
REM     about -0.18   gives plan B stands and the next hours go to more steps
REM     Ruler is the dense series, 0.0021, so anything above 0.02 is decisive.
REM
REM   COST: about 6.8h at the measured 2531 ms/step for 9156 steps.
REM   PLAN: test_plan/P087 (Korean filename) Stage3
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

timeout /t 15 /nobreak

python scripts\runlog.py --name P087_stage3_tokens_x_repeat --note "[1/1] 1200M tokens over the 600M pool = 2.0 epochs on a doubled pool"
python scripts\runlog.py --name P087_stage3_tokens_x_repeat -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 9156 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_p6_t1200
if errorlevel 1 echo [WARN] arm failed - continuing

set TL_WB_TAG=d12_cla2_r20_p6_t1200
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

echo.
python scripts\runlog.py --name P087_stage3_tokens_x_repeat --note "=================================================================" "READ IN THIS ORDER" "1. val minus train_ce tail average. Every arm so far sat under 0.11." "   Four epochs did not overfit; this is 2 epochs on a bigger pool." "2. this arm versus d12_cla2_r20 with paired_eval. SAME 600M pool," "   so --tokens 600M is the right eval cache, NOT the 300M default." "   Using 300M would score it on data it trained on (result 075 6)." "3. additive prediction is about -0.18. Compare." "4. unique coverage here is 1-exp(-2) = 86.5 percent of a 600M pool" "   = 519M unique tokens, the most any run of ours has seen." "5. residency is 30.7 MiB, unchanged. Everything won here is free." "================================================================="

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
