@echo off
REM =============================================================================
REM  P062 stage 4  -  is recursion R=3 still free
REM                   1 training run plus paired eval, about 4.3 hours
REM
REM  THE QUESTION
REM    R=2 gave minus 0.0202 at ZERO memory cost (result 047). That is the best
REM    price-per-MiB in the repository because the denominator is zero. Nobody
REM    has asked whether R=3 gives more, the same, or less. Two points make a
REM    line; we have one point and an origin.
REM
REM  WHY IT IS NOT OBVIOUS
REM    Result 041 s17 measured cos 0.9882 between the first and the duplicate
REM    attention pass and I MISREAD that as "replaceable" - it cost plus 0.0281.
REM    The correct reading is that the duplicate pass is already nearly redundant,
REM    which predicts R=3 adds little. But result 047 also showed the recursion
REM    gain is real, so "nearly redundant" is not "worthless". This measures it.
REM
REM  !! --repeat-mode uniform ROUNDS TO INTEGERS (result 043 s5)
REM    R=1.5, 2.0 and 2.5 all produced 36 visits and identical CE. So the axis is
REM    1, 2, 3 - there are no fractional points to sweep. R=3 is 60 visits on the
REM    20 layer model.
REM
REM  PREDICTIONS, fixed in advance
REM    E1  between 3.650 and 3.665. That is "R=3 keeps most of R=2's gain and
REM        adds at most half of it again" versus mC_r20_nokd 3.6573.
REM    E2  it does NOT reach 3.637 (linear extrapolation of R=2). Redundancy.
REM    E3  deploy_mb IDENTICAL to mC_initonly and mC_r20_nokd. Recursion stores
REM        nothing. A difference is an accounting bug.
REM    E4  wall clock about 2.4x the non-recursive baseline. R=2 was 1.68x.
REM    E5  IF E1 fails LOW (better than 3.650) the depth-by-reuse axis is not
REM        saturating and REVIEW3 s4 gains a much bigger lever than it thinks.
REM
REM  !! HOW TO EVALUATE IT
REM    --match-train-repeat. This checkpoint trains at R=3; evaluating it at R=1
REM    evaluates a function that was never trained (trap 39, result 043 s14).
REM
REM  !! NO --no-ckpt. Result 051 stage 2b: recursion does not fit without it.
REM     The [i] from lint_bat rule 21 is expected here.
REM
REM  WHAT THIS CANNOT DECIDE
REM    Whether R=3 is deployable. Wall clock is the blocker, not memory - we are
REM    at 36 tok/s single-thread CPU and R=3 would be about 15 (REVIEW3 s5).
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P062_stage4_r3_curve --note "=============================================================================" "P062 stage 4   recursion R=3 - the second point on a zero-memory lever" "R=2 bought minus 0.0202 for nothing. Nobody asked what R=3 buys." "About 4.3 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P062_stage4_r3_curve --note "[1/3] mC_r30_nokd - one flag different from mC_r20_nokd"
python scripts\runlog.py --name P062_stage4_r3_curve -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --train-repeat 3.0 --ce-chunk 2048 --init-from --tag mC_r30_nokd
if errorlevel 1 echo [WARN] mC_r30_nokd failed - continuing

python scripts\runlog.py --name P062_stage4_r3_curve --note "[wandb] push this run"
set TL_WB_TAG=mC_r30_nokd
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P062_stage4_r3_curve --note "[2/3] paired full-val - three points on the recursion curve, each at its own trained function"
python scripts\runlog.py --name P062_stage4_r3_curve -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r30_nokd mC_r20_nokd mC_initonly --match-train-repeat
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P062_stage4_r3_curve --note "[3/3] residency - E3 says all three are the same number"
python scripts\runlog.py --name P062_stage4_r3_curve -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_r30_nokd mC_initonly --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P062_stage4_r3_curve --note "=============================================================================" "READ IN THIS ORDER" "1. did it OOM. CUBLAS_STATUS_EXECUTION_FAILED is an OOM under another name" "   (trap 29). If so, R=3 does not fit at 20 layers and that IS the answer." "2. json train_repeat must read 3.0. Not 2.0, not 1.0." "3. val minus train_ce. Over 0.3 means the training and eval schedules differ" "   (trap 39). Check --match-train-repeat actually engaged before reading any" "   quality number." "4. paired delta against E1 (3.650 to 3.665). Ruler 2 sigma = 0.0034." "5. deploy_mb versus E3. Recursion stores nothing." "IF R=3 ADDS LESS THAN HALF OF R=2  the axis saturates and R=2 is the setting." "IF IT ADDS MORE  reopen the depth-by-reuse axis - that is a bigger result than" "  this batch was designed to find (E5)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
