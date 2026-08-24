@echo off
REM =============================================================================
REM  P073 stage 1  -  un-confound every attention-tying number we own
REM                   1 training run plus paired eval and residency, about 3.2 h
REM
REM  WHY THIS EXISTS  (result 058, 2026-08-23)
REM    Stage 0 measured cla_group 1 against cla_group 2 on the 20 layer baseline
REM    and found MINUS 0.0268 - past the 0.024 practical resolution. Prediction Z4
REM    said that if the delta were large, every attn_group result is confounded.
REM    It fired.
REM
REM  !! WHAT IS CONFOUNDED
REM    attn_group shares Q, K, V and O between layers. cla_group shares K and V.
REM    They divide the same resource twice. Every number we have for attention
REM    tying - results 044 section 9, 044 section 11, and the 0.00083 nats per
REM    million line in EXPERIMENT_BASELINES B.5 - was measured on top of cla2.
REM    So we do not know the price of attention tying. We know the price of
REM    attention tying ON TOP OF an already halved K/V.
REM
REM  ONE FLAG DIFFERENT FROM THE STANDARD MODEL
REM    --cla-group 1 on mC_d36_ag4_nokd. Nothing else moves.
REM
REM  PREDICTIONS, fixed in advance
REM    Y1  cla1 is BETTER by 0.015 to 0.040. Stage 0 got 0.0268 at 20 layers with
REM        attn_group 1; at 36 layers with attn_group 4 the two mechanisms overlap
REM        more, so the CLA cost should be LARGER, not smaller.
REM    Y2  resident goes UP by about 20 to 45 MiB. Every layer owns its K and V.
REM    Y3  if Y1 lands ABOVE 0.040 the two levers are close to additive and the
REM        attention axis has to be re-priced from scratch.
REM    Y4  if Y1 lands near ZERO the overlap is total - CLA costs nothing once
REM        attn_group 4 is on - and result 058 is a 20-layer-only finding.
REM        THAT IS THE MOST USEFUL OUTCOME because it un-confounds B.5 for free.
REM
REM  !! NO --no-ckpt (36 layers does not fit - result 051 stage 2b). The [i] from
REM     lint_bat rule 21 is expected. NOTE the control mC_d36_ag4_nokd also ran
REM     with checkpointing ON, so this pair has NO grad_ckpt drift - unlike the
REM     20 layer pairs in results 030, 045 and 058.
REM
REM  WHAT THIS CANNOT DECIDE
REM    The optimal cla_group. Only 1 versus 2, and only at attn_group 4.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P073_stage1_cla_on_d36 --note "=============================================================================" "P073 stage 1   cla_group 1 on the 36 layer standard model" "Result 058 fired Z4 - every attn_group number we own sits on top of cla2." "This is the control that un-confounds them. About 3.2 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P073_stage1_cla_on_d36 --note "[1/3] mC_d36_ag4_cla1 - one flag different from the standard model"
python scripts\runlog.py --name P073_stage1_cla_on_d36 -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --attn-group 4 --cla-group 1 --ce-chunk 2048 --init-from --tag mC_d36_ag4_cla1
if errorlevel 1 echo [WARN] mC_d36_ag4_cla1 failed - continuing

python scripts\runlog.py --name P073_stage1_cla_on_d36 --note "[wandb] push this run"
set TL_WB_TAG=mC_d36_ag4_cla1
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P073_stage1_cla_on_d36 --note "[2/3] paired full-val against the standard model"
python scripts\runlog.py --name P073_stage1_cla_on_d36 -- python scripts\paired_eval.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_cla1 mC_d36_ag4_nokd
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P073_stage1_cla_on_d36 --note "[3/3] residency - the denominator of the lever price"
python scripts\runlog.py --name P073_stage1_cla_on_d36 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1d --models mC_d36_ag4_cla1 mC_d36_ag4_nokd --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P073_stage1_cla_on_d36 --note "=============================================================================" "READ IN THIS ORDER" "1. json cla_group must read 1 AND attn_group must read 4. Both, or this run" "   is a reseed of the standard model (trap 37)." "2. paired delta against Y1. Ruler is 2 sigma = 0.0034 - this is a no-KD pair" "   and the tool prints the dense 0.024." "3. THIS PAIR HAS NO grad_ckpt DRIFT. Both ran with checkpointing on. The" "   20 layer pairs in results 030, 045 and 058 all carry minus 0.0016." "4. resident delta. Lever price = quality divided by MiB. Compare against" "   0.000447 (g16) and 0.001191 (cla2 at 20 layers, result 058)." "IF THE DELTA IS NEAR ZERO  CLA is free once attn_group 4 is on, and every" "  number in EXPERIMENT_BASELINES B.5 stands as written. Best outcome (Y4)." "IF IT IS LARGE  attention tying has to be re-priced from scratch (Y3)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
