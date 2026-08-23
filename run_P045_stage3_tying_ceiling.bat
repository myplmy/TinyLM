@echo off
REM =============================================================================
REM  P045 stage 3  -  the MLP tying ceiling ON THE DEPLOYMENT MODEL
REM                   1 training run plus paired eval and residency, about 3.2 h
REM
REM  THE QUESTION
REM    m100R1d has 32 middle layers at mlp_group 16, which is 2 unique middle
REM    MLPs. mlp_group 32 makes it ONE. That is the structural end of the axis -
REM    there is nothing past it.
REM
REM  WHY IT IS NOT A REPEAT OF RESULT 029
REM    029 measured g16 on the 20 LAYER baseline (plus 0.0161). Result 032 s8.3
REM    showed lever price is CONVEX - the same g16 cost 1.57 times more on a
REM    smaller base. So the 20 layer number does not transfer, and the deployment
REM    model is the 36 layer one. This asks the price where we will actually pay.
REM
REM  PREDICTIONS, fixed in advance
REM    B1  worse than mC_d36_ag4_nokd 3.6848 by 0.03 to 0.08. Convexity says the
REM        last halving is the expensive one.
REM    B2  resident drops by roughly the unique middle MLP term, near 40 percent.
REM    B3  the lever price is WORSE than 0.00342 nats per million (the g16 line
REM        in EXPERIMENT_BASELINES B.5), again by convexity.
REM    B4  if B1 lands under plus 0.03 the convexity model is wrong and result
REM        032 s8.3 needs revisiting. That would be the interesting outcome.
REM
REM  WHAT THIS CANNOT DECIDE
REM    Whether g32 is ADOPTED. This is a price measurement. Adoption is REVIEW3.
REM
REM  !! NO --no-ckpt (36 layers does not fit - result 051 stage 2b). The [i] from
REM     lint_bat rule 21 is expected.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P045_stage3_tying_ceiling --note "=============================================================================" "P045 stage 3   mlp_group 32 on the 36 layer model - ONE unique middle MLP" "The structural end of the tying axis, priced on the deployment model." "About 3.2 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P045_stage3_tying_ceiling --note "[1/3] mC_d36_ag4_g32 - one flag different from the standard model"
python scripts\runlog.py --name P045_stage3_tying_ceiling -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --attn-group 4 --mlp-group 32 --ce-chunk 2048 --init-from --tag mC_d36_ag4_g32
if errorlevel 1 echo [WARN] mC_d36_ag4_g32 failed - continuing

python scripts\runlog.py --name P045_stage3_tying_ceiling --note "[wandb] push this run"
set TL_WB_TAG=mC_d36_ag4_g32
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P045_stage3_tying_ceiling --note "[2/3] paired full-val against the standard model"
python scripts\runlog.py --name P045_stage3_tying_ceiling -- python scripts\paired_eval.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_g32 mC_d36_ag4_nokd
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P045_stage3_tying_ceiling --note "[3/3] residency"
python scripts\runlog.py --name P045_stage3_tying_ceiling -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1d --models mC_d36_ag4_g32 mC_d36_ag4_nokd --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P045_stage3_tying_ceiling --note "=============================================================================" "READ IN THIS ORDER" "1. json mlp_group must read 32 AND attn_group must read 4. Both." "2. report() should print ONE unique middle MLP. If it prints 2 the override" "   did not reach the model." "3. paired delta against B1 (plus 0.03 to plus 0.08). Ruler 2 sigma = 0.0034." "4. lever price versus the 0.00342 line. B3 says worse." "IF THE PRICE IS FLAT  convexity is wrong and every price extrapolation in" "  EXPERIMENT_BASELINES 2.2c has to be re-read (B4). That is a bigger finding" "  than the lever itself." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
