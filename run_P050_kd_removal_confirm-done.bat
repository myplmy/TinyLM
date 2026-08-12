@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P050_kd_removal_confirm.bat -- [P050 stage 2] is dropping KD really a
REM                                     gain? Second seed, and the no-KD sigma.
REM  Plan: test_plan\P050 / Result: 038 section 3, 039 section 3.1
REM =============================================================================
REM
REM ***ABOUT 3.6 GPU HOURS. ONE RUN. UNATTENDED.***
REM
REM WHY THIS IS NOW THE MOST IMPORTANT RUN ON THE BOARD
REM   Result 038 measured the four arms and found:
REM     parent-init alone   -0.1386
REM     KD alone            -0.0032     ***effectively zero, wrong sign***
REM     mC_initonly (no KD) full-val 3.6776  vs  mC_wsd (with KD) 3.6984
REM   So dropping KD gave, on one seed:
REM     quality   -0.0208 (BETTER)
REM     reserved  12.47 to 5.07 GiB   ***-7.41 GiB, -59 percent***
REM     wall      132.7 to 108.2 min  (-18.5 percent on the student run)
REM   ***That single change is 1.9x larger than every teacher-memory lever this
REM   repo has found put together*** (compressed teacher -1.88, teacher infer
REM   mode -1.03, bf16 optimizer state -1.02).
REM
REM ***AND IT IS NOT A SURPRISE.*** EXPERIMENT_BASELINES section 7 already says
REM   'KD gain shrinks as budget grows: -0.110 to +0.062 to +0.098 at
REM   100/300/600M', and a positive sign there means KD HURTS. At 300M it was
REM   already +0.062. ***We knew, and ran almost every experiment with KD anyway.***
REM
REM WHY A SECOND SEED AND NOT A NEW ABLATION
REM   -0.0208 sits below the 0.024 decision resolution. Result 039 measured the
REM   seed noise of this condition at +0.0006, which would make -0.0208 real -
REM   ***but that +0.0006 was measured WITH KD and parent-init.*** Result 039
REM   section 3.1 hypothesis (2) says sharing a teacher and a parent is exactly
REM   what suppresses seed noise. mC_initonly has no teacher.
REM   ***So the no-KD condition may be noisier, and we must measure it, not
REM   assume it.*** One run answers both questions:
REM     Q1 does the KD-removal delta reproduce on seed 2024
REM     Q2 what is the seed noise WITHOUT a teacher
REM
REM ***PREDICTIONS - WRITTEN BEFORE THE RUN***
REM   P1 mC_initonly_s2 lands within 0.010 of mC_initonly (3.6776).
REM      If it lands further, the no-KD condition is noisier and -0.0208 is
REM      NOT established - that would be the important outcome.
REM   P2 paired(mC_wsd_s2, mC_initonly_s2) reproduces the sign of -0.0208.
REM   P3 reserved about 5.07 GiB, grad_max about 0.64, wall about 108 min.
REM      ***These three are near-deterministic*** - if any is off, the condition
REM      is not what we think it is.
REM   P4 ***the pipeline framing still matters.*** --init-from is not free: the
REM      dense parent costs 97.5 min first. Total no-KD pipeline 205.7 min vs
REM      230.2 min with KD = -10.6 percent, not -18.5. Do not quote -18.5 alone.
REM
REM ***WHAT THIS RUN CANNOT SETTLE.*** Whether KD should be dropped from the
REM   STANDARD CONDITION. Every memory-lever comparison in this repo (g16, p1c1,
REM   g256a, e128svd, ct, optbf16) was run WITH KD. Changing the standard
REM   invalidates the shared control mC_wsd. ***That is a REVIEW2 decision.***
REM   This run only establishes whether the effect is real.
REM
REM ERRORLEVEL POLICY: training is the prerequisite for the comparison.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_initonly.pt goto NOSEED1
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd_s2.pt goto NOWSDS2

echo =============================================================
echo [P050-2] KD removal, second seed  (about 3.6 h, unattended)
echo =============================================================
python scripts\runlog.py --name P050_kd_removal --note "[P050 stage 2] mC_initonly on seed 2024. Q1 does the KD-removal delta reproduce. Q2 what is the seed noise WITHOUT a teacher."

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo =============================================================
echo [1/2] train - parent init, NO KD, seed 2024
echo =============================================================
python scripts\runlog.py --name P050_kd_removal --note "[1/2] --init-from, NO --kd, --seed 2024. Expect reserved about 5.07 GiB and no [kd] line at all."
python scripts\runlog.py --name P050_kd_removal -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --init-from --tag mC_initonly_s2
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [2/2] paired - four checkpoints, two seeds, KD on and off
echo =============================================================
python scripts\runlog.py --name P050_kd_removal --note "[2/2] paired over mC_wsd, mC_wsd_s2, mC_initonly, mC_initonly_s2. Read the KD deltas AND the seed deltas from one table."
python scripts\runlog.py --name P050_kd_removal -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_wsd_s2 mC_initonly mC_initonly_s2
if errorlevel 1 echo [WARN] paired_eval failed - the checkpoint is on disk, re-run this step alone

echo.
echo =============================================================
echo [check] spill verdict - read this before quoting any ms/step
echo =============================================================
python scripts\check_spill.py test_result\*P050_kd_removal*.txt

python scripts\runlog.py --name P050_kd_removal --note "=================================================================" "WHAT TO RECORD" "  0. ***there must be NO [kd] line*** in run [1/2]. If there is one, --kd" "     leaked in and the run is worthless." "  1. peak reserved. Expect about 5.07 GiB. ***This is the headline number.***" "  2. from the [2/2] table, FOUR deltas:" "       mC_initonly    vs mC_initonly_s2   = seed noise WITHOUT a teacher  (Q2)" "       mC_wsd         vs mC_wsd_s2        = seed noise WITH a teacher (+0.0006)" "       mC_wsd         vs mC_initonly      = KD effect, seed 1337 (-0.0208)" "       mC_wsd_s2      vs mC_initonly_s2   = KD effect, seed 2024      (Q1)" "  3. grad_max and skip from the json. Expect about 0.64 and 0." "  4. wall clock. Expect about 108 min. ***Quote the PIPELINE number too***" "     (plus 97.5 min for the parent) - see prediction P4." "" "HOW TO READ IT" "  Q2 near +0.0006, and Q1 reproduces -0.0208" "      -^> ***KD is a net loss at 300M and the -7.41 GiB is free.*** Take it to" "         REVIEW2 as a standard-condition change. Note that every existing" "         lever comparison used KD, so the shared control would have to move." "  Q2 much larger than +0.0006 (say above 0.010)" "      -^> ***the no-KD condition is noisier and -0.0208 is NOT established.***" "         That is the more interesting outcome: it means result 039's" "         hypothesis (2) is right - sharing a teacher suppresses seed noise -" "         and the repo needs a sigma PER CONDITION, not one number." "  Q1 flips sign" "      -^> KD's effect is below this rig's noise. Then the honest claim is" "         'KD buys nothing at 300M', which still justifies dropping it for" "         the -7.41 GiB - but say 'buys nothing', not 'hurts'." "" "LIMITS: two seeds. 300M budget only - result 006 says KD WINS at 100M" "  (-0.110), so this conclusion is budget-conditional and must be quoted with" "  the budget attached. --init-from still costs a 97.5 min parent run." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:BADKWARGS
echo.
echo [STOP] cli.py passes a keyword its target function does not accept.
if not defined TL_NOPAUSE pause
exit /b 6

:NOPARENT
echo.
echo [STOP] parent runs\ckpt\m100_ko-en_300M_dense.pt is missing (--init-from needs it).
if not defined TL_NOPAUSE pause
exit /b 5

:NOSEED1
echo.
echo [STOP] runs\ckpt\m100R1c_ko-en_300M_mC_initonly.pt is missing (the seed-1337 arm).
if not defined TL_NOPAUSE pause
exit /b 5

:NOWSDS2
echo.
echo [STOP] runs\ckpt\m100R1c_ko-en_300M_mC_wsd_s2.pt is missing (needed for the seed-2024 pair).
if not defined TL_NOPAUSE pause
exit /b 5

:TRAINBAD
echo.
echo [STOP] training failed. Nothing to compare.
if not defined TL_NOPAUSE pause
exit /b 4

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
