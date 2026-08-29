@echo off
REM =============================================================================
REM  P073 stage 3  -  the missing 20-layer CLA twin, and the first body designed
REM                   for the KV budget.  about 1.7 hours.
REM
REM  WHY  (KV accounting, 2026-08-29)
REM    Two things point at the same missing run.
REM    1. Plan P073 says the 36-layer cla1-cla2 pair exists but there is no
REM       20-layer twin. Result 058 s12.2 measured CLA at 36 layers only.
REM    2. REVIEW3 s18 put KV in the residency formula and cla_group is the single
REM       largest KV lever - cla1 doubles the entries. mC_cla1_ag4 has 20 KV
REM       entries (30.0 MiB at seq 1024) against mC_initonly_nc with 10 (15.0).
REM    mC_cla2_ag4 is one flag away from mC_initonly_nc and has never been run.
REM
REM  INDEPENDENT VARIABLE
REM    attn_group 1 to 4 on the standard control. Nothing else changes.
REM    Against mC_cla1_ag4 it is cla_group 1 to 2 (the 20-layer CLA twin).
REM
REM  PREDICTIONS
REM    C1  KV entries 10, same as mC_initonly_nc. cla_group decides KV, not attn.
REM    C2  ternary parameters below mC_cla1_ag4 40.11M - cla2 shares K/V projections.
REM    C3  paired vs mC_initonly_nc between +0.015 and +0.030. Result 058 s12 priced
REM        36-layer 8 to 4 unique attention at +0.0225 with cla2.
REM    C4  paired vs mC_cla1_ag4 between +0.010 and +0.030 - the CLA1 gain at 20
REM        layers with ag4. Result 058 measured -0.0136 at 36 layers ag4.
REM    C5  weights plus KV beats mC_cla1_ag4. That is the whole point.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P073_stage3_cla2_ag4 --note "=============================================================================" "P073 stage 3   mC_cla2_ag4 - the 20-layer CLA twin" "One flag from the standard control. Never run. KV accounting made it urgent." "=============================================================================="

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P073_stage3_cla2_ag4 --note "[1/3] train - attn_group 4 on the default cla_group 2"
python scripts\runlog.py --name P073_stage3_cla2_ag4 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --attn-group 4 --init-from --tag mC_cla2_ag4
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
set TL_WB_TAG=mC_cla2_ag4
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P073_stage3_cla2_ag4 --note "[2/3] paired against both neighbours"
python scripts\runlog.py --name P073_stage3_cla2_ag4 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 mC_cla1_ag4 mC_initonly_nc
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P073_stage3_cla2_ag4 --note "[3/3] residency including KV, and plan B assembled"
python scripts\runlog.py --name P073_stage3_cla2_ag4 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4 mC_cla1_ag4 mC_initonly_nc --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P073_stage3_cla2_ag4 --note "=============================================================================" "READ IN THIS ORDER" "1. C1 - kv_entries must be 10. If it is 20 the cla default did not apply." "2. C4 - the 20-layer CLA1 gain. Result 058 has 36-layer numbers only, so this" "   is the first 20-layer point and B.7.2 gets a row either way." "3. C5 - weights plus KV against mC_cla1_ag4. cla1 buys quality and pays 15 MiB" "   of KV for it. Which side wins is the deployment answer." "4. use the tied ruler 0.0010 (result 039 s8) - both arms are tied models." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
