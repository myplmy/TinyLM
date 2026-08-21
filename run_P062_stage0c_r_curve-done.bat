@echo off
REM =============================================================================
REM  P062 stage 0c  -  the R curve. Why did arm3 equal arm1?
REM                    (NO TRAINING, GPU eval only, roughly 25 minutes)
REM
REM  WHY THIS BATCH EXISTS NOW AND NOT LAST SESSION
REM    The 202608270600 handoff listed this as recommended item 7 with the note
REM    "no batch - prerequisite". That note was correct for item 6 and WRONG for
REM    item 7. One sentence covered two rows and only one of them had a reason.
REM    There is no prerequisite here: paired_eval already carries --infer-repeat
REM    and --repeat-where, both landed in the same session. It runs today.
REM    Recorded as decision trap D15.
REM
REM  THE UNEXPLAINED THING (handoff s3.3, plan P062 s10.4)
REM    Result 043 s5 found arms at R = 1.5, 2.0 and 2.5 producing ONE run. The
REM    cause was found for training: _repeat_schedule uses int(round(R)), so
REM    1.5 and 2.0 and 2.5 all round to 2. But INFERENCE uses a different
REM    formula, int(round(n_middle * R)), which does NOT collapse:
REM        R 1.25 gives 20 middle passes     R 1.75 gives 28
REM        R 1.50 gives 24                   R 2.00 gives 32
REM    Four distinct schedules. So if the inference curve ALSO comes out flat,
REM    the rounding explanation is not the whole story and every fractional-R
REM    result in P031 has to be re-read.
REM
REM  THE TWO MODELS, AND WHY THE SECOND ONE IS NOT WASTE
REM    mC_r20        trained with --train-repeat 2.0
REM    mC_initonly   trained at R = 1, no KD
REM    --infer-repeat applies to BOTH arms of each call. That is deliberate:
REM    at each R the pair separates "recursion in TRAINING" from "recursion at
REM    INFERENCE only", which is exactly the P031 mismatch condition.
REM
REM  PREDICTIONS, fixed in advance
REM    P1  mC_r20 full-val VARIES across the four R values. Flat means the
REM        rounding story is incomplete and P031 needs re-reading.
REM    P2  mC_r20 is best at R = 2.0, the schedule it was trained on.
REM    P3  mC_initonly gets WORSE as R rises - it never saw those schedules.
REM    P4  the R = 1.0 call prints the trap 39 warning for mC_r20. It should.
REM        That is the tool working, not a failure.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether recursion is worth adopting. Result 047 s10 already showed
REM    mC_r20 loses to the no-KD baseline by +0.0035. This only explains the
REM    SHAPE of the R curve.
REM    And it is a checkpoint comparison, not an architecture comparison.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P062_stage0c_rcurve --note "=============================================================================" "P062 stage 0c   the R curve   NO TRAINING   about 25 minutes" "Inference rounding does not collapse the way training rounding did." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P062_stage0c_rcurve --note "[1/5] R = 1.00 - reference. Expect the trap 39 warning on mC_r20; that is correct behaviour."
python scripts\runlog.py --name P062_stage0c_rcurve -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20 mC_initonly
if errorlevel 1 echo [WARN] R 1.00 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0c_rcurve --note "[2/5] R = 1.25 - 20 middle passes"
python scripts\runlog.py --name P062_stage0c_rcurve -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20 mC_initonly --infer-repeat 1.25 --repeat-where front
if errorlevel 1 echo [WARN] R 1.25 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0c_rcurve --note "[3/5] R = 1.50 - 24 middle passes. THE ONE THAT COLLAPSED IN TRAINING."
python scripts\runlog.py --name P062_stage0c_rcurve -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20 mC_initonly --infer-repeat 1.5 --repeat-where front
if errorlevel 1 echo [WARN] R 1.50 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0c_rcurve --note "[4/5] R = 1.75 - 28 middle passes"
python scripts\runlog.py --name P062_stage0c_rcurve -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20 mC_initonly --infer-repeat 1.75 --repeat-where front
if errorlevel 1 echo [WARN] R 1.75 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0c_rcurve --note "[5/5] R = 2.00 - 32 middle passes. The schedule mC_r20 was trained on."
python scripts\runlog.py --name P062_stage0c_rcurve -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20 mC_initonly --infer-repeat 2.0 --repeat-where front
if errorlevel 1 echo [WARN] R 2.00 failed - continuing

echo.
echo.
python scripts\runlog.py --name P062_stage0c_rcurve --note "=============================================================================" "READ IN THIS ORDER" "1. the P062 line each call prints - layer visits must read 20, 24, 28, 32" "   plus prelude and coda. If two calls print the same count, the schedule" "   collapsed and the whole curve is one point (trap 37)." "2. mC_r20 full-val across the five R values. Flat means P1 failed and the" "   rounding explanation from result 043 does not cover inference." "3. is mC_r20 best at R = 2.0? That is P2 - train and infer schedules agree." "4. mC_initonly across R. Rising loss is P3, the P031 mismatch." "REMINDER  this explains the curve. It does not decide whether to adopt." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
