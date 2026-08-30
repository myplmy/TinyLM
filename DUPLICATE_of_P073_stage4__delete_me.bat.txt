@echo off
REM =============================================================================
REM  P073 stage 5  -  recursion on the cheap-KV body.  about 3.0 hours.
REM
REM  WHY  (result 058 s13, result 047 s14.4, result 016 s24)
REM    Two facts collided. Recursion buys -0.0107 of quality for zero weight
REM    memory. And cla_group=2 halves the KV entries for +0.0195 of quality.
REM    The recursion winner mC_cla1_ag4_r20 needs 70.9 MiB because it uses cla1
REM    AND recursion, and those are the two levers that both grow KV.
REM
REM    This arm puts recursion on the cla2 body instead. Derived: 10 owners x 2
REM    passes = 18 entries = 27.0 MiB, plus 16.8 weights = 43.8. Still over 36,
REM    but --repeat-kv-reuse would fold it to 10 entries = 31.8, which fits.
REM    P077 stage 0 measures what that reuse costs.
REM
REM  INDEPENDENT VARIABLE
REM    --train-repeat 2.0 on top of mC_cla2_ag4. One flag.
REM
REM  PREDICTIONS
REM    R1  weights identical to mC_cla2_ag4 to the decimal. Recursion stores
REM        nothing. This held exactly in result 047 s13 T1.
REM    R2  kv_entries = 18. If it is 20 the schedule is not what we think.
REM    R3  quality gain over mC_cla2_ag4 of -0.005 to -0.015. The R1-to-R2 step
REM        was -0.0202 on the 20-layer body and -0.0204 on the shallow one, so
REM        it is remarkably stable across bodies - but result 059 s13 says
REM        shallower bodies have more to gain.
REM    R4  wall clock about +85 percent over mC_cla2_ag4.
REM
REM  RULER
REM    Tied 2 sigma = 0.0010. The recursion family has no ruler yet - say
REM    "borrowed" when quoting.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 --note "=============================================================================" "P073 stage 5   recursion on the cheap-KV body" "cla1 and recursion both grow KV. This one keeps recursion and drops cla1." "=============================================================================="

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 --note "[1/3] train - mC_cla2_ag4 plus --train-repeat 2.0"
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --attn-group 4 --train-repeat 2.0 --init-from --tag mC_cla2_ag4_r20
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
set TL_WB_TAG=mC_cla2_ag4_r20
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 --note "[2/3] paired - match the trained schedule, trap 39"
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20 mC_cla2_ag4 mC_cla1_ag4_r20nc mC_initonly_nc --match-train-repeat
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 --note "[3/3] R1 and R2 - weights unchanged, entries 18, and what reuse would give"
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4_r20 mC_cla2_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 3a failed - continuing
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --repeat-kv-reuse
if errorlevel 1 echo [WARN] step 3b failed - continuing

echo.
python scripts\runlog.py --name P073_stage5_cla2_ag4_r20 --note "=============================================================================" "READ IN THIS ORDER" "1. R2 first - kv_entries must be 18. Anything else and the schedule is not" "   what the plan says, and the rest of the reading is void." "2. R1 - weights identical to mC_cla2_ag4. Recursion stores nothing." "3. R3 - the paired delta against mC_cla2_ag4, on the borrowed tied ruler." "4. step 3b - entries with reuse on. If that is 10, then weights 16.8 plus KV" "   15.0 equals 31.8 and this arm fits the four-thread budget with recursion" "   still on. That would be the first one that does." "5. quality against mC_cla1_ag4_r20nc, which is 3.6760 at 70.9 MiB." "=============================================================================="

if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
