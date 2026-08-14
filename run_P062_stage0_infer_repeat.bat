@echo off
REM =============================================================================
REM  P062 stage 0  -  recursion: train schedule vs inference schedule
REM                   (GPU light, about 15 minutes, NO TRAINING, NO CODE CHANGE)
REM
REM  WHY THIS EXISTS
REM    visit_schedule() only honours train_repeat when self.training is True:
REM
REM        if self.training and TR != 1.0:  return self._repeat_schedule(TR)
REM        if R == 1.0:                     return list(range(n))
REM
REM    Every evaluation path calls model.eval() - evaluate.py L17, paired_eval L71.
REM    So mC_r20 was TRAINED with 36 passes and EVALUATED with 20 passes.
REM    Every val number we reported for it, including the +0.2275 that closed the
REM    axis, was measured on a different function than the one we trained.
REM
REM    The log said so 22 times. val minus train_ce:
REM        baseline family   -0.004
REM        mC_d36 (36 real layers)  +0.099
REM        mC_r20 (repeat R=2)      +0.349   ^<- and train_ce matched mC_d36
REM
REM  WHAT THIS BATCH DOES
REM    Re-evaluates the EXISTING checkpoints under different inference schedules.
REM    No training. No code change. cli.py already overrides inference-only config
REM    on top of a loaded checkpoint (L308 to L316), and
REM        --infer-repeat 2.0 --repeat-where front
REM    reproduces the training schedule exactly:
REM        train  : prelude + mid*2 + coda        = 2 + 32 + 2 = 36
REM        infer  : total=32, extra=16=m, front   = 2 + 32 + 2 = 36
REM    repeat_kv_reuse defaults to False on both sides, so those match too.
REM
REM  !! HOW TO READ  (this is not paired_eval)
REM    run100m.py eval uses evaluate() with 100 iterations of a seed-99 loader.
REM    It is DETERMINISTIC, so all arms below see the SAME crops and arm-to-arm
REM    comparison is valid. It is NOT the same estimator as paired_eval full-val,
REM    so DO NOT put these numbers next to +0.2275 directly. Use arm 1 as the
REM    local baseline and read differences from it.
REM
REM    DECISION LINE, fixed in advance:
REM      arm2 - arm1 better than -0.15   -^> most of +0.2275 was instrumentation
REM                                         -^> design stage 1, implement
REM                                            paired_eval --infer-repeat (12 lines)
REM      arm2 - arm1 near 0              -^> the repeat cost is real after all
REM      arm7 better than arm2           -^> the train/infer matching hypothesis is wrong
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether recursion beats the baseline. R=2 costs about 2x wall clock, and
REM    mC_r20 was trained with lr 1e-3 which was tuned for R=1. Stage 1 does that.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "=============================================================================" "P062 stage 0   recursion schedule matching   about 15 minutes   NO TRAINING" "mC_r20 was trained with 36 passes and evaluated with 20. This re-evaluates it." "Decision line fixed in advance: arm2 minus arm1 better than -0.15." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P062_stage0_inferrep --note "[1/8] mC_r20 at infer-repeat 1.0 - reproduces the number we reported. LOCAL BASELINE."
python scripts\runlog.py --name P062_stage0_inferrep -- python run100m.py eval --preset m100R1c --arch tied --data ko-en --tokens 300M --tag mC_r20
if errorlevel 1 echo [WARN] arm 1 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "[2/8] mC_r20 at infer-repeat 2.0 front - MATCHES THE TRAINING SCHEDULE. This is the experiment."
python scripts\runlog.py --name P062_stage0_inferrep -- python run100m.py eval --preset m100R1c --arch tied --data ko-en --tokens 300M --tag mC_r20 --infer-repeat 2.0 --repeat-where front
if errorlevel 1 echo [WARN] arm 2 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "[3/8] mC_r20 at infer-repeat 1.5 front - is the optimum at the trained R, or below it?"
python scripts\runlog.py --name P062_stage0_inferrep -- python run100m.py eval --preset m100R1c --arch tied --data ko-en --tokens 300M --tag mC_r20 --infer-repeat 1.5 --repeat-where front
if errorlevel 1 echo [WARN] arm 3 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "[4/8] mC_r20 at infer-repeat 2.0 back - does the shape of the schedule matter?"
python scripts\runlog.py --name P062_stage0_inferrep -- python run100m.py eval --preset m100R1c --arch tied --data ko-en --tokens 300M --tag mC_r20 --infer-repeat 2.0 --repeat-where back
if errorlevel 1 echo [WARN] arm 4 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "[5/8] mC_r20 at infer-repeat 2.0 even - third shape."
python scripts\runlog.py --name P062_stage0_inferrep -- python run100m.py eval --preset m100R1c --arch tied --data ko-en --tokens 300M --tag mC_r20 --infer-repeat 2.0 --repeat-where even
if errorlevel 1 echo [WARN] arm 5 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "[6/8] mC_r20 at infer-repeat 2.0 front with kv-reuse - training recomputed KV, so this should be WORSE. It is a control."
python scripts\runlog.py --name P062_stage0_inferrep -- python run100m.py eval --preset m100R1c --arch tied --data ko-en --tokens 300M --tag mC_r20 --infer-repeat 2.0 --repeat-where front --repeat-kv-reuse
if errorlevel 1 echo [WARN] arm 6 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "[7/8] mC_wsd at infer-repeat 2.0 front - CONTROL. R=1 trained, R=2 inferred. This is what P031 measured. It should be bad."
python scripts\runlog.py --name P062_stage0_inferrep -- python run100m.py eval --preset m100R1c --arch tied --data ko-en --tokens 300M --tag mC_wsd --infer-repeat 2.0 --repeat-where front
if errorlevel 1 echo [WARN] arm 7 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "[8/8] mC_wsd at infer-repeat 1.0 - the ordinary baseline anchor."
python scripts\runlog.py --name P062_stage0_inferrep -- python run100m.py eval --preset m100R1c --arch tied --data ko-en --tokens 300M --tag mC_wsd
if errorlevel 1 echo [WARN] arm 8 failed - continuing

echo.
echo.
python scripts\runlog.py --name P062_stage0_inferrep --note "=============================================================================" "READ IN THIS ORDER" "1. the [P031] line in each arm - it prints how many layer passes were made." "   Arm 2 must say 36. If it says 20 the flag did nothing and the arm is void." "2. arm 1 val_loss - this is the LOCAL BASELINE, not the paired_eval number." "3. arm 2 minus arm 1 against the fixed line of -0.15." "4. arms 3/4/5 - does R or the shape matter more?" "5. arm 6 - kv reuse should be worse. If it is better, the training path is odd." "6. arm 7 vs arm 8 - P031 reproduction on an R=1 trained model." "REMINDER: evaluate() is 100 deterministic crops. Arm to arm is valid." "DO NOT put these next to paired_eval full-val numbers (trap 4, trap 33)." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
