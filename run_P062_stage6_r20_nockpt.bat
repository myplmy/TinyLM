@echo off
REM =============================================================================
REM  P062 stage 6  -  remove the grad-checkpoint confound from the recursion win
REM                   about 2.7 hours.
REM
REM  WHY  (result 047 s13.2.1)
REM    mC_cla1_ag4_r20 beat the standard control by -0.0012 and beat its own
REM    non-recursive twin by -0.0117. Both numbers carry a confound: the r20 run
REM    was the ONLY one with grad checkpointing ON, because recursion plus
REM    --no-ckpt had never been measured for VRAM. Result 051 stage 3 priced that
REM    drift at +0.0014 against the ckpt arm, so correcting it makes the gaps
REM    larger - the conclusion is conservative. But it is still a confound.
REM
REM    The r20 run reported reserved 5.13 GiB WITH checkpointing. That is far from
REM    the 16 GB ceiling. Result 051 s2b found 36-layer recursion did not fit, but
REM    this is 20 layers. There is room to try.
REM
REM  INDEPENDENT VARIABLE
REM    grad checkpointing OFF. Everything else identical to mC_cla1_ag4_r20.
REM
REM  PREDICTIONS
REM    R1  reserved below 12 GiB. If it OOMs, the batch keeps going and we keep
REM        the ckpt number with the confound stated.
REM    R2  wall clock about 20 percent below 197.3 min - result 051 measured that.
REM    R3  paired vs mC_cla1_ag4_r20 is about -0.0014, the ckpt drift, and NOT
REM        larger. A larger gap means the drift is condition dependent.
REM    R4  paired vs mC_initonly_nc is about -0.0026 - the corrected number that
REM        result 047 s13.2.1 predicted. This is the real test.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P062_stage6_r20_nockpt --note "=============================================================================" "P062 stage 6   recursion on the minimum body, without grad checkpointing" "The only confound left in result 047 s13. Also -20 percent wall clock." "=============================================================================="

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage6_r20_nockpt --note "[1/3] train - same as mC_cla1_ag4_r20 but --no-ckpt"
python scripts\runlog.py --name P062_stage6_r20_nockpt -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --cla-group 1 --attn-group 4 --train-repeat 2.0 --init-from --tag mC_cla1_ag4_r20nc
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
set TL_WB_TAG=mC_cla1_ag4_r20nc
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P062_stage6_r20_nockpt --note "[2/3] paired - match the trained schedule, trap 39"
python scripts\runlog.py --name P062_stage6_r20_nockpt -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20nc mC_cla1_ag4_r20 mC_cla1_ag4 mC_initonly_nc --match-train-repeat
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P062_stage6_r20_nockpt --note "[3/3] residency with KV"
python scripts\runlog.py --name P062_stage6_r20_nockpt -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla1_ag4_r20nc mC_cla1_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P062_stage6_r20_nockpt --note "=============================================================================" "READ IN THIS ORDER" "1. did it fit. reserved and skip 0. If it OOMed, say so and keep the ckpt arm." "2. R3 - the ckpt drift. About -0.0014 confirms result 051 stage 3 in a new" "   condition. Much larger means the drift is not a constant and B.7.2 needs a" "   caveat next to the -0.0014 row." "3. R4 - the corrected gap against the standard control. This is what result" "   047 s13 predicted and could not measure." "4. tied ruler 0.0010 (result 039 s8)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
