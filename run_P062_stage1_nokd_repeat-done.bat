@echo off
REM =============================================================================
REM  P062 stage 1  -  recursion WITHOUT KD
REM                   1 training run, about 2.7 hours
REM
REM  WHY THIS IS NOW UNBLOCKED
REM    The prerequisite was "P055 stage 1 plus the REVIEW2 decision". P055
REM    stage 1 landed (result 042 s12, KD removed) and on 2026-08-21 the user
REM    set the interim standard to B2, which is no-KD. Both are satisfied.
REM
REM  THE OPPONENT CHANGED
REM    Result 047 s10 measured mC_r20 at R=2 two ways:
REM        versus mC_wsd     (KD baseline)     -0.0173   it WINS
REM        versus mC_initonly (no-KD baseline) +0.0035   it LOSES
REM    mC_r20 is a KD-trained run, so we cannot tell whether it loses because
REM    of recursion or because of KD. Result 047 predicted, additively, that
REM    no-KD plus recursion would land near 3.660, i.e. -0.018. Never measured.
REM
REM  WHY THIS ARM IS UNUSUAL AND WORTH THE TIME
REM    Recursion adds ZERO parameters - it runs the same middle block twice.
REM    So mC_r20_nokd and mC_initonly have identical ternary count, identical
REM    packed size and identical residency. This is a rare thing in this repo:
REM    a pure quality comparison at fixed memory. If S1 holds, it is free.
REM
REM  !! THE EVALUATION SCHEDULE IS NOT OPTIONAL - TRAP 39
REM    visit_schedule() honours train_repeat only when self.training is true,
REM    and every eval path calls model.eval(). Without --infer-repeat 2.0 the
REM    checkpoint is scored by a DIFFERENT FUNCTION than it was trained with.
REM    That is exactly what result 043 s14 retracted. paired_eval now prints a
REM    loud warning when the checkpoint has train_repeat != 1 and infer-repeat
REM    is 1.0 - if you do not see that warning on call 2, the tool is not
REM    engaged and the numbers are void.
REM
REM  PREDICTIONS, fixed in advance (plan P062 s1.4)
REM    S1  delta versus mC_initonly is -0.014 to -0.022 (additive guess -0.018)
REM    S2  ternary, packed and residency IDENTICAL to mC_initonly
REM    S3  reserved about 6.1 GiB (13.52 minus the 7.41 that KD cost)
REM    S4  wall clock about 2.7h
REM    S5  val minus train_ce under 0.05. The KD-trained mC_r20 showed +0.349,
REM        which is how trap 39 was found.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    The shape of the R curve - that is stage 0c.
REM    The optimal R - only R=2 is trained, and 1.5 and 2.5 both round to 2 in
REM    training (result 043 s5).
REM    Inference cost - recursion is free in memory and 2x in compute.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P062_stage1_nokd --note "=============================================================================" "P062 stage 1   recursion without KD   about 2.7 hours" "Zero extra parameters. A pure quality comparison at fixed memory." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P062_stage1_nokd --note "[1/2] mC_r20_nokd - train-repeat 2.0, uniform, parent-init, NO KD."
python scripts\runlog.py --name P062_stage1_nokd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --train-repeat 2.0 --repeat-mode uniform --tag mC_r20_nokd
if errorlevel 1 echo [WARN] mC_r20_nokd failed - continuing

echo.
python scripts\runlog.py --name P062_stage1_nokd --note "[2/2] paired full-val ON THE TRAINING SCHEDULE. Watch for the trap 39 warning."
python scripts\runlog.py --name P062_stage1_nokd -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20_nokd mC_initonly --infer-repeat 2.0 --repeat-where front
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
echo.
python scripts\runlog.py --name P062_stage1_nokd --note "=============================================================================" "READ IN THIS ORDER" "0. call 2 must print the P062 schedule line showing 36 layer visits. If it" "   prints 20, --infer-repeat did not land and everything below is void." "1. val minus train_ce in the training log. S5 says under 0.05. The KD run" "   showed +0.349 and that is how trap 39 was found. Check this FIRST." "2. json train_repeat 2.0, repeat_mode uniform, kd false (trap 37)." "3. paired delta versus mC_initonly against S1, ruler 2 sigma = 0.0034." "   Note mC_initonly is ALSO evaluated at R=2 in this call - it was trained" "   at R=1, so that arm is the P031 mismatch condition, not a baseline." "4. ternary, packed and runtime_mb must be IDENTICAL to mC_initonly (S2)." "5. reserved against S3." "REMINDER  if S1 comes out positive, the recursion gain depended on KD and" "          result 047 s10 additive assumption must be withdrawn." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
