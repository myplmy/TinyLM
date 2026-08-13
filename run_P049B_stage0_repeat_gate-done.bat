@echo off
REM =============================================================================
REM  P049B stage 0  -  what does training-time recurrence cost at the start?
REM  GPU small, minutes. No training.
REM
REM  WHY THIS GATE IS CLEANER THAN P049 STAGE 0
REM    P049 grows the student to 36 PHYSICAL layers, so the transplant itself was
REM    a new technique - and result 041 shows that is where the instrumentation
REM    accident happened. P049B keeps 20 physical layers and changes only the
REM    forward SCHEDULE. The depth map is therefore the identity, so parent init
REM    is bit identical to every previous run.
REM
REM    ***That makes the measurement clean***: the student starts as a perfect
REM    copy of the teacher, and the rise in step0 CE IS the composition mismatch.
REM    That is the quantity result 041 tried to measure and could not.
REM
REM  GATES
REM    G0-a  does not raise (KV bank splits by (owner, pass))
REM    G0-b  ternary parameter count UNCHANGED across R - if it moves, the whole
REM          premise of this axis (same memory, more compute) is gone
REM    G0-c  ***R=1.0 must land near the teacher full-val 3.8080 (result 040 s2).***
REM          This is the health check. If it misses, do not read anything else -
REM          that is exactly how result 041 went wrong.
REM    G0-d  cost of repetition = CE(R=2) - CE(R=1)
REM    G0-e  schedule length is 36 at R=2
REM
REM  !! Uses REAL val data with next-token targets. Random tokens make the metric
REM     go the WRONG WAY - a well-initialised model scores worse against random
REM     targets than a random model does (result 041 s11, measurement trap 31).
REM
REM  Log goes to test_result. A gate is an experiment.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P049B_stage0_repeat --note "=============================================================================" "P049B stage 0   training-time recurrence gate   R = 1.0 / 1.5 / 2.0 / 2.5" "Reference: teacher dense deterministic full-val = 3.8080 (result 040 s2)" "R=1.0 must land near it, or the measurement is broken (result 041 s11)" "============================================================================="

python scripts\runlog.py --name P049B_stage0_repeat -- python scripts\diag_train_repeat.py --preset m100R1c --repeats 1.0 1.5 2.0 2.5 --mode uniform
if errorlevel 1 goto GATEBAD

echo.
python scripts\runlog.py --name P049B_stage0_repeat --note "=============================================================================" "Gate passed. Read, in this order:" "1. G0-c - is R=1.0 near 3.8080? if not, STOP, nothing else is readable" "2. G0-b - ternary parameter count identical across R" "3. G0-d - the start cost of each R. This is a step0 number, NOT a verdict." "   Training may recover it - that is the whole question of P049B." "4. peak alloc per R - activation memory grows with repetition even though" "   RESIDENT memory does not. That is the price of this axis." "!! uniform rounds R to an integer, so R=1.5 behaves as 2. Use progressive" "   for fractional depth. Write that in the result document." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:GATEBAD
echo.
echo [STOP] the recurrence gate failed. Read the per-R table.
echo        If G0-c failed, the measurement is broken, not the method -
echo        check the data loader before touching the model (trap 31).
echo        If G0-b failed, repetition changed the parameter count, which
echo        would mean the schedule is not what we think it is.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
