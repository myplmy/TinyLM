@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage3_d16_tokens600m.bat -- the token axis on the bigger body
REM ==========================================================================
REM
REM   THE QUESTION
REM     Stage1 asks whether 600M unique tokens beat 300M on d12, our 32 MiB
REM     winner. This arm asks the same of d16_cla2_r20, the 40 MiB winner.
REM     Both matter because result 071 found that our memory levers all sit on
REM     one efficiency line and the BIGGER step is the cheaper one:
REM       no-cla-edges  +1.61 MiB  0.00465 nats/MiB
REM       third visit   +3.00 MiB  0.00493
REM       depth 12 to 16  +7.80 MiB  0.00531
REM     If the token axis also pays more on the bigger body, then depth and
REM     tokens compound and the 40 MiB budget is where to spend both.
REM     If it pays LESS, the small body is the better place to buy tokens and
REM     that reverses how we would spend the next 20 GPU hours.
REM
REM   WHY IT COSTS NOTHING AT DEPLOY TIME
REM     more training tokens change no tensor shape. Residency stays 38.5 MiB.
REM
REM   CONTROL
REM     d16_cla2_r20 already exists but it used the 600M pool, and this arm
REM     needs the 1.2B pool to keep the pool-at-least-twice-tokens rule. So the
REM     control is the t300 arm of Stage1 in spirit, not in fact - it is a
REM     different body. The honest comparison is:
REM       within this batch      no control, one arm
REM       across Stage1          d12 t300 to t600 delta versus this delta
REM     That cross-batch read is valid because both use the same 1.2B pool and
REM     the same token counts. Only the body differs, which is the variable.
REM
REM   VRAM
REM     d16_cla2_r20 at --no-ckpt measured 12.32 GB reserved. Visits are
REM     2 + 12*2 + 2 = 28, so M x visits = 8192 x 28 = 229,376, under the
REM     confirmed ceiling of 294,912. Safe.
REM
REM   COST: about 4.2h at the measured 3293 ms/step.
REM   PLAN: test_plan/P088 (Korean filename) Stage3
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

timeout /t 15 /nobreak

python scripts\runlog.py --name P088_stage3_d16_tokens600m --note "[1/1] d16 with 600M tokens over the 1.2B pool"
python scripts\runlog.py --name P088_stage3_d16_tokens600m -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 4578 --tokens 300M --pool-tokens 1200M --exact-cache --tag d16_cla2_r20_p12_t600
if errorlevel 1 echo [WARN] d16 t600 arm failed - continuing

set TL_WB_TAG=d16_cla2_r20_p12_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

echo.
python scripts\runlog.py --name P088_stage3_d16_tokens600m --note "=================================================================" "READ IN THIS ORDER" "1. this arm has no control inside the batch. Read it against the Stage1" "   t300 to t600 delta on d12, same pool and same token counts." "2. if the d16 delta is LARGER, depth and tokens compound and the next" "   hours go to the 40 MiB budget." "3. if it is SMALLER, buy tokens on the small body instead." "4. residency is unchanged at 38.5 MiB. Whatever this buys is free." "5. val minus train_ce first, as always. Baselines sit near +0.10." "================================================================="

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
