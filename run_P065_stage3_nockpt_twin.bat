@echo off
REM =============================================================================
REM  P065 stage 3  -  the control twin that removes a drift term from every
REM                   future no-KD comparison.  1 run plus paired, about 1.9 h
REM
REM  WHY  (user, 2026-08-26; handoff 202609080600 section 1.5)
REM    The standard control mC_initonly trained with grad checkpointing ON.
REM    Since 2026-08-22 the standing instruction is that no-KD runs use
REM    --no-ckpt by default, so three recent experiments - P046 arm 1, P061 and
REM    P073 stage 0 - all compared a --no-ckpt arm against a ckpt-ON control.
REM    Result 015 measured that drift at minus 0.0016. That is 70 percent of
REM    P061's headline number.
REM
REM  !! IT DID NOT CHANGE ANY CONCLUSION - AND THAT IS WHY IT IS WORTH FIXING
REM    P046 (+0.0675) and P073 (minus 0.0268) are far past it, and in P061 the
REM    drift pushes toward the conclusion that was drawn. So nothing is wrong
REM    today. The point is that it will not stay that way: every future no-KD
REM    lever measured at 0.003 to 0.01 has this term inside it and we would
REM    have no way to separate it.
REM
REM  ONE FLAG DIFFERENT FROM mC_initonly
REM    --no-ckpt. Same preset, same seed, same everything else.
REM
REM  PREDICTIONS, fixed in advance
REM    T1  minus 0.0010 to minus 0.0025 versus mC_initonly. Result 015 measured
REM        minus 0.0016 on a dense pair; this is the tied pair.
REM    T2  identical deploy_mb and resident. Checkpointing is a training-time
REM        memory trade and stores nothing at deploy.
REM    T3  wall clock about 20 percent faster (result 051 measured minus 20.6).
REM        This is also the first clean same-batch --no-ckpt speed number we
REM        will own - EXPERIMENT_BASELINES 5.2 says we still do not have one.
REM    T4  reserved goes UP, roughly 5.07 to 10.3 GiB (result 051).
REM
REM  WHAT THIS CANNOT DECIDE
REM    Whether older comparisons should be redone. It gives the correction
REM    term; applying it is a reading rule, not a re-measurement.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P065_stage3_nockpt_twin --note "=============================================================================" "P065 stage 3   the --no-ckpt twin of the standard control" "Three recent experiments carry a minus 0.0016 drift because the control" "trained with checkpointing on. This removes it for good. About 1.9 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P065_stage3_nockpt_twin --note "[1/3] mC_initonly_nc - one flag different from the standard control"
python scripts\runlog.py --name P065_stage3_nockpt_twin -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --tag mC_initonly_nc
if errorlevel 1 echo [WARN] mC_initonly_nc failed - continuing

python scripts\runlog.py --name P065_stage3_nockpt_twin --note "[wandb] push this run"
set TL_WB_TAG=mC_initonly_nc
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P065_stage3_nockpt_twin --note "[2/3] paired - THIS DELTA IS THE CORRECTION TERM"
python scripts\runlog.py --name P065_stage3_nockpt_twin -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly_nc mC_initonly
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P065_stage3_nockpt_twin --note "[3/3] residency - T2 says these two are identical"
python scripts\runlog.py --name P065_stage3_nockpt_twin -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_initonly --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P065_stage3_nockpt_twin --note "=============================================================================" "READ IN THIS ORDER" "1. json grad_ckpt must read false. If it reads true this is a reseed of" "   mC_initonly and the delta is seed noise, not drift." "2. THE PAIRED DELTA IS THE PRODUCT. Write it into EXPERIMENT_BASELINES as" "   the tied-pair grad_ckpt drift, next to result 015's dense 0.0016." "3. deploy_mb and resident must match mC_initonly EXACTLY (T2). A difference" "   means checkpointing leaked into the saved model, which would be a bug." "4. ms_step_median. This is the first clean SAME-BATCH --no-ckpt speed number" "   in the repository - section 5.2 says the existing minus 6 to minus 20" "   range was never measured cleanly. Record it." "AFTER THIS  every no-KD comparison can subtract a measured term instead of" "  quoting a dense-pair number from result 015." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
