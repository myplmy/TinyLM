@echo off
REM =============================================================================
REM  P062 stage 0b  -  make the headline canonical with paired_eval
REM                    (NO TRAINING, about 10 minutes)
REM
REM  WHY 0b
REM    Stage 0 used run100m.py eval, which is evaluate() over 100 deterministic
REM    crops. Arm-to-arm comparison is valid there, but it is NOT the estimator
REM    the repo judges with. mC_wsd reads 3.66609 under that tool and 3.6984
REM    under paired_eval - different quantities (traps 4 and 33).
REM    The stage 0 headline "recursion beat the baseline by 0.0166" therefore
REM    cannot be written into a baseline table yet. This fixes that.
REM
REM  WHAT CHANGED IN THE TOOL
REM    paired_eval.py gained --infer-repeat / --repeat-where / --repeat-kv-reuse
REM    (about 12 lines, 2026-08-15). Default 1.0 is bit-identical to before.
REM    It also now SHOUTS if a checkpoint has train_repeat but infer-repeat is 1,
REM    which is exactly the defect trap 39 recorded.
REM
REM  !! WHY TWO CALLS
REM    --infer-repeat applies to EVERY tag in one call, by design: mixing
REM    schedules inside a paired comparison would break the paired premise.
REM    So we make two calls and read ABSOLUTE full-val numbers across them.
REM    That is legitimate because full-val is DETERMINISTIC on a fixed val set -
REM    mC_wsd reads exactly 3.6984 in any call that uses R=1.
REM
REM  READ
REM    call 1 gives   mC_wsd@R1   mC_r20@R1   (R1 is the WRONG schedule for r20)
REM    call 2 gives   mC_wsd@R2   mC_r20@R2   (R2 is the RIGHT one for r20)
REM    the number that matters is   mC_r20@R2  minus  mC_wsd@R1
REM    stage 0 estimated -0.0166 with the other tool. Under 0.024 is "same in
REM    practice"; the sign and the fact that memory is IDENTICAL is the point.
REM    call 2's mC_wsd@R2 is the (train 1, infer 2) control - it should be bad,
REM    reproducing result 020 on the deterministic estimator.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P062_stage0b_paired --note "=============================================================================" "P062 stage 0b   paired_eval with matched inference schedule   about 10 min" "Stage 0 said -0.2427 and beat the baseline. This makes it canonical." "Two calls: R=1 then R=2. Read ABSOLUTE full-val across them - it is deterministic." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P062_stage0b_paired --note "[1/2] R=1 - the ordinary schedule. mC_r20 is MISMATCHED here on purpose; this reproduces the +0.2275 we reported."
python scripts\runlog.py --name P062_stage0b_paired -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_initonly mC_r20
if errorlevel 1 echo [WARN] call 1 failed - continuing

echo.
python scripts\runlog.py --name P062_stage0b_paired --note "[2/2] R=2 front - matches how mC_r20 was TRAINED. mC_wsd here is the (train 1, infer 2) control."
python scripts\runlog.py --name P062_stage0b_paired -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_r20 --infer-repeat 2.0 --repeat-where front
if errorlevel 1 echo [WARN] call 2 failed - continuing

echo.
echo.
python scripts\runlog.py --name P062_stage0b_paired --note "=============================================================================" "READ IN THIS ORDER" "1. call 1 must print the trap-39 warning for mC_r20. If it does not, the" "   tool patch did not take and the whole run is void." "2. call 2's [P062] line must say 36 passes for BOTH tags." "3. mC_r20@R2 (call 2) minus mC_wsd@R1 (call 1) - this is the headline." "4. mC_wsd@R2 minus mC_wsd@R1 - the (1,2) control. Should be clearly worse." "5. mC_wsd@R1 must read 3.6984 in call 1. If it does not, something moved and" "   nothing else in this log can be trusted." "REMINDER: mC_r20 has IDENTICAL unique-ternary, packed and residency to mC_wsd." "The cost is compute and latency, about 1.8x. Not memory." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
