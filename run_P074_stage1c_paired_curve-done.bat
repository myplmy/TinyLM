@echo off
REM =============================================================================
REM  P074 stage 1c  -  put a ruler on the depth curve. NO TRAINING. about 3 min.
REM
REM  WHY THIS EXISTS
REM    Stage 1b trained four shallow dense models and printed only the training
REM    log val, which our own rule (R10) says is a random-crop sample and not a
REM    judgement. I built a batch to draw a curve and forgot to put a ruler in
REM    it. The four checkpoints already exist, so this costs three minutes.
REM
REM    Result 059 section 10.2 currently carries three estimated numbers marked
REM    with the calculated-value symbol, derived from a SINGLE anchor. This
REM    batch replaces all three with measurements.
REM
REM  WHAT IT ANSWERS
REM    Z1  the deterministic full-val of d6, d8, d10, d12 on the same crops.
REM    Z2  where the shallow dense curve crosses the tied models. Result 059
REM        section 10.3 shows d8_dense ties mC_initonly_nc at 9 percent less
REM        resident memory; the estimate says d6 loses to mC_cla1_ag4. The
REM        crossing point is the whole question and it is currently a guess.
REM    Z3  whether the constant offset assumption in 059 section 10.2.1 holds.
REM        If d8 comes back at 3.6767 the anchor is confirmed.
REM
REM  PREDICTIONS
REM    Y1  d8_dense lands at 3.6767 plus or minus 0.002 - it is the same
REM        configuration as eq_d8_dense from stage 2, so this is a reproduction
REM        check as well as a measurement.
REM    Y2  the curve is monotone in depth. If it is not, something is wrong with
REM        one of the four runs and the whole curve is suspect.
REM    Y3  d10_dense beats mC_initonly_nc (3.6762) but at 505.4 against 451.5
REM        resident - better and bigger, so not a free win.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P074_stage1c_paired_curve --note "=============================================================================" "P074 stage 1c   a ruler for the depth curve. No training." "Stage 1b printed training-log val, which is not a judgement (rule R10)." "Result 059 section 10.2 has three estimated numbers this batch replaces." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P074_stage1c_paired_curve --note "[1/2] paired full-val - four depths on the same crops, plus both controls"
python scripts\runlog.py --name P074_stage1c_paired_curve -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models d6_dense d8_dense d10_dense d12_dense
if errorlevel 1 echo [WARN] paired curve failed - continuing

echo.
python scripts\runlog.py --name P074_stage1c_paired_curve --note "[2/2] the tied controls on the same ruler"
python scripts\runlog.py --name P074_stage1c_paired_curve -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly_nc mC_cla1_ag4 mC_initonly
if errorlevel 1 echo [WARN] control pass failed - continuing

echo.
python scripts\runlog.py --name P074_stage1c_paired_curve --note "=============================================================================" "READ IN THIS ORDER" "1. Y1 - d8_dense against 3.6767. This is a reproduction check: the same" "   configuration was trained twice (d8_dense and eq_d8_dense). If the two" "   differ by more than 0.002 the seed control is not doing its job." "2. Y2 - is the curve monotone in depth. If not, suspect one run." "3. plot the four against resident MiB (316.3 / 410.8 / 505.4 / 599.9) with" "   the tied models on the same axes (mC_cla1_ag4 339.0, mC_initonly 451.5," "   mC_d36_ag4_nokd 379.7). THE CROSSING POINT IS THE ANSWER." "4. replace the three estimated numbers in result 059 section 10.2.1 and" "   delete the offset assumption - it is no longer needed." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
