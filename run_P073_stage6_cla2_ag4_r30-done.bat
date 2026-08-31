@echo off
REM =============================================================================
REM  P073 stage 6  -  R=3 on the cheap-KV body.  about 3.6 hours.
REM
REM  WHY  (result 058 s14.2, result 059 s13, result 039 s10)
REM    Stage 4 found that the recursion gain depends on the body. On the cla1
REM    body R1 to R2 bought -0.0107. On the cla2 body it bought -0.0172, which
REM    is 1.61x more. That breaks the reading in result 059 s13 that the first
REM    recursion step is worth about -0.020 regardless of body.
REM
REM    Separately, result 039 s10 measured the recursion ruler for the first
REM    time - 2 sigma = 0.0006, seven times tighter than the dense ruler we had
REM    been borrowing. That overturned the "R=6 rejected" verdict in 059 s13:
REM    every interval out to 28 visits is significant.
REM
REM    Put together: recursion has more room on this body than we thought, and
REM    the ruler is sharp enough to see it. R=3 is the next point.
REM
REM  INDEPENDENT VARIABLE
REM    --train-repeat 3.0 instead of 2.0. One number.
REM
REM  PREDICTIONS
REM    T1  weights identical to mC_cla2_ag4 again. Recursion stores nothing.
REM    T2  kv_entries = 26.  10 owners, prelude and coda visited once, middle
REM        visited three times.  If it is not 26 the schedule is not what the
REM        plan says and the rest of the reading is void.
REM    T3  gain over mC_cla2_ag4_r20 of -0.004 to -0.010. The R2-to-R3 step was
REM        -0.0106 on the eq_d8 body (059 s13, 12 to 16 visits) and the steps
REM        halve, so a smaller number than the -0.0172 of R1 to R2.
REM    T4  wall clock about +40 percent over stage 4. Stage 4 was +44.6 percent
REM        over R1 for one extra pass; this adds one more.
REM
REM  RULER
REM    Recursion 2 sigma = 0.0006, MEASURED (result 039 s10). No longer borrowed.
REM
REM  DECISION
REM    gain over -0.0006 and the KV goes 18 to 26 entries, so 27.0 to 39.0 MiB.
REM    Weights 16.8 puts the total at 55.8, well over budget. This arm is only
REM    deployable if --repeat-kv-reuse folds it back to 10 entries. P077 stage 0
REM    measures that cost. Read the two together.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 --note "=============================================================================" "P073 stage 6   R=3 on the cheap-KV body" "Stage 4 showed recursion pays 1.61x more on this body than on cla1." "The recursion ruler is now measured, not borrowed." "=============================================================================="

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 --note "[1/3] train - mC_cla2_ag4 plus --train-repeat 3.0"
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --attn-group 4 --train-repeat 3.0 --init-from --tag mC_cla2_ag4_r30
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
set TL_WB_TAG=mC_cla2_ag4_r30
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 --note "[2/3] paired - match the trained schedule, trap 39"
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r30 mC_cla2_ag4_r20 mC_cla2_ag4 mC_initonly_nc --match-train-repeat
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 --note "[3/3] T1 and T2 - weights unchanged, entries 26, and what reuse would give"
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4_r30 mC_cla2_ag4_r20 mC_cla2_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 3a failed - continuing
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4_r30 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --repeat-kv-reuse
if errorlevel 1 echo [WARN] step 3b failed - continuing

echo.
python scripts\runlog.py --name P073_stage6_cla2_ag4_r30 --note "=============================================================================" "READ IN THIS ORDER" "1. T2 first - kv_entries must be 26. Anything else and the schedule is wrong." "2. T1 - weights identical to mC_cla2_ag4. Recursion stores nothing." "3. T3 - the paired delta against mC_cla2_ag4_r20, on the MEASURED recursion" "   ruler 0.0006. Not the borrowed dense ruler." "4. plot the three points 20, 36, 52 visits against quality. That is the visit" "   curve for this body, and 059 s13 has the same curve for eq_d8." "5. step 3b - entries with reuse. If reuse is cheap this arm is deployable;" "   if not, it is a quality result only." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
