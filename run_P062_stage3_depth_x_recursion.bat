@echo off
REM =============================================================================
REM  P062 stage 3  -  depth AND recursion together   (REVIEW2 s7, permitted
REM                   2026-08-22)
REM                   1 training run plus paired eval, about 5 hours
REM
REM  THE QUESTION
REM    We have two levers that both buy quality without buying memory:
REM        36 layers with attn_group 4   3.6848   resident 379.7 MiB
REM        recursion R=2 on 20 layers    3.6573   resident 451.5 MiB, memory
REM                                               IDENTICAL to its baseline
REM    Nobody has run them together. If the gains add, the standard model gets
REM    better at no memory cost. If they do not add, that tells us both levers
REM    are buying the same thing - effective depth - and we stop stacking them.
REM
REM  !!! 2026-08-22 UPDATE - THE PREREQUISITE PROBE ALREADY FAILED
REM    run_P065_stage2 died on BOTH arms (result 054):
REM      d36 alone with --no-ckpt        14.73 GiB allocated, needed 512 MiB more
REM      r20 recursion with --no-ckpt    14.84 GiB allocated, needed 512 MiB more
REM    This batch is 36 layers AND recursion at once, which is strictly larger
REM    than either. It keeps grad checkpointing ON, which is the only reason it
REM    is not already known to fail - but 36 layers times recursion doubles the
REM    number of checkpoint segments and that has never been measured.
REM    -^> RUN run_P065_stage2b_nockpt_vram.bat FIRST. Its arm 2 (d36 + ckpt)
REM       and arm 4 (r20 recursion + ckpt) bracket this configuration.
REM       If either control dies, do not start this five hour run.
REM
REM  !! PREREQUISITE  run_P065_stage2b_nockpt_vram.bat MUST PASS FIRST
REM    36 layers times recursion is the largest activation footprint we have
REM    ever built. Neither term has a --no-ckpt measurement. This batch keeps
REM    grad checkpointing ON for that reason. If the probe shows headroom, add
REM    --no-ckpt and this run drops from 5 hours to about 4.
REM
REM  PREDICTIONS, fixed in advance
REM    W1  versus mC_d36_ag4_nokd 3.6848, this lands between 3.660 and 3.675.
REM        That is "recursion still pays about half of its 0.0203 at 36 layers".
REM    W2  it does NOT reach the sum. Result 041 s17 says the duplicate visit is
REM        already nearly redundant at 20 layers; at 36 it should be more so.
REM    W3  resident memory IDENTICAL to mC_d36_ag4_nokd, 379.7 MiB. Recursion
REM        stores nothing. If this moves, the accounting is wrong.
REM    W4  wall clock about 1.7x mC_d36_ag4_nokd.
REM
REM  !! HOW TO EVALUATE IT
REM    --match-train-repeat. This checkpoint trained at R=2; evaluating it at
REM    R=1 evaluates a function that was never trained (trap 39).
REM
REM  WHAT THIS CANNOT DECIDE
REM    Whether a THIRD lever stacks on top. Two points do not make a curve, and
REM    result 032 s8.3 already showed lever price is convex - do not predict the
REM    third from the average of the first two.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P062_stage3_depth_x_recursion --note "=============================================================================" "P062 stage 3   36 layers AND recursion R2   REVIEW2 s7" "Two memory free quality levers, never combined. About 5 hours." "PREREQUISITE  run_P065_stage2_nockpt_vram.bat must have passed." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P062_stage3_depth_x_recursion --note "[1/2] mC_d36_ag4_r20_nokd - two flags different from mC_d36_ag4_nokd"
python scripts\runlog.py --name P062_stage3_depth_x_recursion -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --attn-group 4 --train-repeat 2.0 --ce-chunk 2048 --init-from --tag mC_d36_ag4_r20_nokd
if errorlevel 1 echo [WARN] mC_d36_ag4_r20_nokd failed - continuing

echo.
python scripts\runlog.py --name P062_stage3_depth_x_recursion --note "[wandb] push this run"
set TL_WB_TAG=mC_d36_ag4_r20_nokd
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P062_stage3_depth_x_recursion --note "[2/2] paired full-val against the standard model, each at its own trained function"
python scripts\runlog.py --name P062_stage3_depth_x_recursion -- python scripts\paired_eval.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_r20_nokd mC_d36_ag4_nokd --match-train-repeat
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P062_stage3_depth_x_recursion --note "=============================================================================" "READ IN THIS ORDER" "1. did it OOM. A CUBLAS_STATUS_EXECUTION_FAILED is an OOM under a different" "   name (trap 29). If so, this configuration does not fit and that IS the" "   answer - write it down, do not retry blind." "2. json train_repeat must read 2.0 and attn_group must read 4. Both." "3. val minus train_ce. Over 0.3 means training and eval ran different" "   schedules - stop and read result 043 s14 before believing any number." "4. paired delta against W1 (3.660 to 3.675). Ruler is 2 sigma = 0.0034." "5. deploy_mb must equal mC_d36_ag4_nokd exactly (W3). Recursion stores" "   nothing. A difference here is an accounting bug, not a finding." "IF W1 HOLDS  the standard model gains 0.010 to 0.025 at zero memory cost." "IF THE GAIN VANISHES  both levers buy the same thing and we stop stacking." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
