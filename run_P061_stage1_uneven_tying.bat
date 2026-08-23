@echo off
REM =============================================================================
REM  P061 stage 1  -  uneven tying, TRAINED this time
REM                   3 training runs plus paired eval, about 5.6 hours
REM
REM  WHY THIS EXISTS
REM    Stage 0 (result 045) measured step0 CE for three shapes and the verdict was
REM    WITHDRAWN on 2026-08-14 under decision trap D13: step0 is a binary gate for
REM    "did the transplant work", not a size or ranking predictor. The measured
REM    step0-to-trained ratio in this repo spans 1/20.6 to 2.22x - a factor of 46.
REM    So the axis is still open and only a trained run can close it.
REM
REM  WHY IT IS WORTH 5.6 HOURS
REM    The number of unique middle MLPs is FIXED at 2 in all three shapes, so
REM    packed size, resident size and FLOPs are IDENTICAL to mC_initonly. If any
REM    shape wins, it is a free lever - the only kind this project has found twice
REM    (recursion, depth) and the kind REVIEW3 s4 is built on.
REM
REM  THE SHAPES  (--mlp-split N puts the boundary after middle layer N)
REM    mC_sp12_4   12 + 4    front group heavy   result 045 step0 6.8447 (worst)
REM    mC_sp4_12    4 + 12    back group heavy    result 045 step0 6.7312 (best)
REM    mC_sp2_14    2 + 14    extreme             not measured at all
REM    control      8 + 8     = mC_initonly, already on disk, not trained again
REM
REM  PREDICTIONS, fixed in advance
REM    D1  all three land within plus or minus 0.010 of mC_initonly 3.6776. The
REM        step0 spread was 0.11 nats and D13 says that does not carry over.
REM    D2  IF anything separates, 4+12 wins - that is the step0 direction and
REM        direction held 2 out of 2 in this repo even when size did not.
REM    D3  deploy_mb IDENTICAL across all three and equal to mC_initonly. A
REM        difference here is an accounting bug, not a finding.
REM    D4  ms/step identical. mlp_split does not change the number of forward
REM        passes, only which weights they share.
REM
REM  WHAT THIS CANNOT DECIDE
REM    The optimal boundary. Three points on a 15 point axis. And nothing here
REM    transfers to the 36 layer model, which has 32 middle layers.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P061_stage1_uneven_tying --note "=============================================================================" "P061 stage 1   uneven tying, trained. Memory is IDENTICAL in all three arms." "Stage 0 was a step0 measurement and its verdict was withdrawn (D13)." "About 5.6 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P061_stage1_uneven_tying --note "[1/5] mC_sp12_4 - front group heavy, the step0 loser"
python scripts\runlog.py --name P061_stage1_uneven_tying -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --mlp-split 12 --init-from --tag mC_sp12_4
if errorlevel 1 echo [WARN] mC_sp12_4 failed - continuing
python scripts\runlog.py --name P061_stage1_uneven_tying --note "[wandb] push arm 1"
set TL_WB_TAG=mC_sp12_4
call scripts\batch\tool_wandb_push.bat

echo.
timeout /t 15 /nobreak

python scripts\runlog.py --name P061_stage1_uneven_tying --note "[2/5] mC_sp4_12 - back group heavy, the step0 winner"
python scripts\runlog.py --name P061_stage1_uneven_tying -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --mlp-split 4 --init-from --tag mC_sp4_12
if errorlevel 1 echo [WARN] mC_sp4_12 failed - continuing
python scripts\runlog.py --name P061_stage1_uneven_tying --note "[wandb] push arm 2"
set TL_WB_TAG=mC_sp4_12
call scripts\batch\tool_wandb_push.bat

echo.
timeout /t 15 /nobreak

python scripts\runlog.py --name P061_stage1_uneven_tying --note "[3/5] mC_sp2_14 - the extreme, never measured at any depth"
python scripts\runlog.py --name P061_stage1_uneven_tying -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --mlp-split 2 --init-from --tag mC_sp2_14
if errorlevel 1 echo [WARN] mC_sp2_14 failed - continuing
python scripts\runlog.py --name P061_stage1_uneven_tying --note "[wandb] push arm 3"
set TL_WB_TAG=mC_sp2_14
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P061_stage1_uneven_tying --note "[4/5] paired full-val - four shapes at identical memory"
python scripts\runlog.py --name P061_stage1_uneven_tying -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_sp12_4 mC_sp4_12 mC_sp2_14 mC_initonly
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P061_stage1_uneven_tying --note "[5/5] residency - D3 says all four are the same number"
python scripts\runlog.py --name P061_stage1_uneven_tying -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_sp12_4 mC_sp4_12 mC_sp2_14 mC_initonly --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P061_stage1_uneven_tying --note "=============================================================================" "READ IN THIS ORDER" "1. json mlp_split must read [12], [4], [2]. If any reads [] that arm is a" "   reseed of mC_initonly and its delta is seed noise (trap 37)." "2. step [5] first. If deploy_mb differs across arms, STOP - the accounting is" "   wrong and no quality number can be attributed (D3)." "3. paired deltas against D1. Ruler 2 sigma = 0.0034, and this comparison IS" "   the no-KD condition so 0.024 is the wrong ruler." "4. compare the ORDER against D2 (4+12 best). Direction held 2/2 historically" "   even when magnitude did not - a reversal here is worth its own note." "IF ALL THREE ARE INSIDE 0.0034  the axis closes: shape does not matter and" "  045's withdrawn conclusion was right for the wrong reason." "IF ONE WINS BY MORE  we have a third free lever and REVIEW3 s4 gains a row." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
