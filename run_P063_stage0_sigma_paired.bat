@echo off
REM =============================================================================
REM  P063 stage 0  -  is 0.024 the right resolution?
REM                   (NO TRAINING, a few minutes)
REM
REM  THE PROBLEM
REM    Our "same in practice" line is 0.024 = 2 sigma, and that sigma came from
REM    result 012: dense, no parent, no teacher, and measured with the TRAINING
REM    LOG's final val_loss - a random-crop estimator we no longer judge with.
REM    Every judgement today is tied + parent-init + paired_eval full-val.
REM
REM    And sigma is already known to be condition-dependent by 20x:
REM      dense, no teacher      0.0119   (result 012, final val_loss)
REM      parent-init only       0.0017   (result 038 s9, paired_eval)
REM      KD + parent-init       0.0006   (result 039, paired_eval)
REM
REM    So we keep calling things "the same" that are 23 to 35 times the seed
REM    noise of the condition they were measured in: g16 +0.0161, E192 +0.0154,
REM    d36_ag2 -0.0138, recursion -0.0173, KD removal -0.0208.
REM
REM  WHAT THIS DECIDES
REM    Result 039 s3.1 wrote down two hypotheses and never tested the first:
REM      (1) 0.012 is an ESTIMATOR artefact - final val_loss carries eval
REM          sampling noise, paired_eval carries none
REM      (2) it is a CONDITION effect - KD and parent-init converge trajectories
REM    Re-measuring the SAME two checkpoints with paired_eval separates them.
REM
REM  PREDICTIONS, fixed in advance (plan P063 s4)
REM    P1  p6d vs p6d_s2 comes out BELOW 0.0119
REM    P2  but still above the mC_wsd pair (0.0006)
REM    P3  the three conditions spread by at least 3x
REM    P4  the conclusion will be that 0.024 is too large
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether to KEEP 0.024 as a practical rule. Statistical significance and
REM    practical importance are different things (result 039). Stage 2 splits
REM    the two in the judgement rules; this stage only measures the statistics.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P063_stage0_sigma --note "=============================================================================" "P063 stage 0   is 0.024 the right resolution   a few minutes   NO TRAINING" "Three seed pairs, one estimator. Result 039 s3.1 left this untested." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P063_stage0_sigma --note "[1/3] dense, no teacher - THE PAIR THAT PRODUCED 0.024. Result 012 measured 0.0119 with final val_loss."
python scripts\runlog.py --name P063_stage0_sigma -- python scripts\paired_eval.py --preset m100 --data ko-en --tokens 300M --models p6d p6d_s2
if errorlevel 1 echo [WARN] dense pair failed - continuing

echo.
python scripts\runlog.py --name P063_stage0_sigma --note "[2/3] parent-init only, no KD - the candidate standard condition. Result 038 s9 measured +0.0017."
python scripts\runlog.py --name P063_stage0_sigma -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_initonly_s2
if errorlevel 1 echo [WARN] initonly pair failed - continuing

echo.
python scripts\runlog.py --name P063_stage0_sigma --note "[3/3] KD + parent-init - the current standard control. Result 039 measured +0.0006."
python scripts\runlog.py --name P063_stage0_sigma -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_wsd_s2
if errorlevel 1 echo [WARN] wsd pair failed - continuing

echo.
echo.
python scripts\runlog.py --name P063_stage0_sigma --note "=============================================================================" "READ IN THIS ORDER" "1. call 1's p6d full-val must be near 3.7045 (baselines s2.2). If it is not," "   the measurement is sick and nothing below can be read." "2. call 1's paired delta against 0.0119. That is hypothesis (1)." "3. the three paired deltas side by side. That is the sigma table we never had." "4. spread of at least 3x means a single resolution number cannot be right." "REMINDER: two-sample sigma is an order-of-magnitude estimate, not a test." "And 0.024 is also a PRACTICAL rule - do not delete it on statistics alone." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
