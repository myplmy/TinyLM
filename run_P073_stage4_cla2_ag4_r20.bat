@echo off
REM =============================================================================
REM  P073 stage 4  -  recursion on the KV-cheap body.  about 3.0 hours.
REM
REM  WHY
REM    Result 047 s13 showed recursion buys -0.0117 for zero weight memory on
REM    mC_cla1_ag4. REVIEW3 s18 then showed cla1 costs 15 MiB of KV cache. If the
REM    same recursion works on a cla2 body, we get the quality without the KV bill:
REM      cla1 + R2  gives 36 KV entries  =  54.0 MiB at seq 1024
REM      cla2 + R2  gives 18 KV entries  =  27.0 MiB   (derived, REVIEW3 s18)
REM
REM  INDEPENDENT VARIABLE
REM    train_repeat 1.0 to 2.0 on mC_cla2_ag4 (P073 stage 3). Nothing else.
REM
REM  DEPENDENCY
REM    None technically - this run does not need stage 3 to finish. But the pair
REM    (stage 3, stage 4) is what makes the number readable, so run stage 3 first
REM    in the queue.
REM
REM  PREDICTIONS
REM    D1  KV entries 18. Half of mC_cla1_ag4_r20. This is the point of the run.
REM    D2  paired vs mC_cla2_ag4 between -0.010 and -0.020 - the recursion gain
REM        was -0.0117 on the cla1 body and -0.0202 on the standard 20-layer body.
REM    D3  weights identical to mC_cla2_ag4 to the decimal. Recursion stores nothing.
REM    D4  weights plus KV below mC_cla1_ag4_r20. If D1 holds this is arithmetic.
REM    D5  visits 36, same decode cost as mC_cla1_ag4_r20 and the standard model.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P073_stage4_cla2_ag4_r20 --note "=============================================================================" "P073 stage 4   recursion on the KV-cheap body" "cla2 halves the KV entries. Does recursion still pay on it." "=============================================================================="

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P073_stage4_cla2_ag4_r20 --note "[1/3] train - attn_group 4, default cla_group 2, train_repeat 2.0"
python scripts\runlog.py --name P073_stage4_cla2_ag4_r20 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --attn-group 4 --train-repeat 2.0 --init-from --tag mC_cla2_ag4_r20
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
set TL_WB_TAG=mC_cla2_ag4_r20
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P073_stage4_cla2_ag4_r20 --note "[2/3] paired - four bodies on one ruler, matched schedules"
python scripts\runlog.py --name P073_stage4_cla2_ag4_r20 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20 mC_cla2_ag4 mC_cla1_ag4_r20 mC_initonly_nc --match-train-repeat
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P073_stage4_cla2_ag4_r20 --note "[3/3] the KV-aware deployment table"
python scripts\runlog.py --name P073_stage4_cla2_ag4_r20 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4_r20 mC_cla2_ag4 mC_cla1_ag4_r20 mC_initonly_nc --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P073_stage4_cla2_ag4_r20 --note "=============================================================================" "READ IN THIS ORDER" "1. D1 - kv_entries 18. If it is 36 the cla default did not apply and D4 is void." "2. D2 - does recursion still pay on a cla2 body. If it does not, recursion and" "   cla1 were interacting and result 047 s13 is narrower than we wrote." "3. D4 - the full deployment number: plan B weights plus KV at seq 1024, against" "   the 36 MiB four-thread budget. This table is what REVIEW3 s18 asked for." "4. tied ruler 0.0010 (result 039 s8)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
