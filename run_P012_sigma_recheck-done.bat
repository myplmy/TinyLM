@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P012_sigma_recheck.bat -- was the sigma = 0.012 of result 012 actually
REM                                EVAL noise rather than TRAINING noise?
REM  Origin: result 039 section 3.1 / 6 (P052)
REM =============================================================================
REM
REM ***MINUTES. NO TRAINING. NOTHING IS WRITTEN TO runs\ckpt.***
REM   Both checkpoints already exist on disk. This only re-evaluates them.
REM
REM WHY THIS IS THE CHEAPEST HIGH-VALUE RUN ON THE BOARD
REM   The whole repo judges with 'resolution 0.024 = 2 sigma' and sigma = 0.012
REM   comes from result 012: p6d 3.704531 vs p6d_s2 3.692656, difference 0.011875.
REM   ***That was measured with `final val_loss`, an evaluate(...,100) ESTIMATOR,
REM   because paired_eval did not exist yet.***
REM
REM   Result 039 then measured the same kind of thing with paired_eval and got
REM       mC_wsd vs mC_wsd_s2   +0.0006  (t 0.53, indistinguishable)
REM       mC_g16 vs mC_g16_s2   +0.0006  (t 0.56, indistinguishable)
REM   ***Twenty times smaller.*** Two explanations, and this run separates them:
REM     (1) result 012's 0.0119 contained EVAL SAMPLING NOISE
REM     (2) KD plus parent-init suppresses training noise (mC has both, p6d has
REM         neither), so the two conditions genuinely differ
REM   paired_eval removes eval noise by construction. So:
REM     ***if p6d vs p6d_s2 comes out near 0.012, explanation (2) wins***
REM        =^> sigma really is condition dependent; keep two sigmas in the table
REM     ***if it comes out near 0.001, explanation (1) wins***
REM        =^> sigma = 0.012 was largely an artefact of the old estimator, and
REM           the repo's resolution of 0.024 was built on it
REM
REM ***PREDICTION - WRITTEN BEFORE THE RUN***
REM   P1 the paired delta lands between 0.002 and 0.010, i.e. BOTH effects are
REM      real and neither explanation is complete. Reason: result 015 already
REM      showed that periodic-eval quantities carry selection bias (best was
REM      biased low over 23 draws), so (1) must contribute something; and the
REM      grad_max split in result 038 (0.64-0.85 with parent-init vs 1.48-1.52
REM      without) says (2) must contribute something too.
REM   P2 whatever the number, ***it will not be exactly 0.0119*** - that value
REM      came from a different estimator and cannot be reproduced by this one.
REM
REM ***WHAT THIS DOES NOT DO.*** It does not re-derive the resolution 0.024.
REM   That is a DECISION RULE, not a statistical bound - see result 039
REM   section 3.2. This run only tells us where the number came from.
REM
REM ERRORLEVEL POLICY: single step, nothing depends on it.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100_ko-en_300M_p6d.pt goto NOP6D
if not exist runs\ckpt\m100_ko-en_300M_p6d_s2.pt goto NOP6DS2

echo =============================================================
echo [P012] was sigma = 0.012 eval noise or training noise  (minutes, no training)
echo =============================================================
python scripts\runlog.py --name P012_sigma_recheck --note "[P012] paired_eval on p6d vs p6d_s2. Result 012 measured 0.011875 with the OLD estimator; result 039 got +0.0006 on mC with paired_eval. This separates eval noise from training noise."

echo.
echo =============================================================
echo [1/2] p6d vs p6d_s2 - the same pair result 012 used, new instrument
echo =============================================================
python scripts\runlog.py --name P012_sigma_recheck --note "[1/2] paired(p6d, p6d_s2). Both are dense, cosine, 600M pool, no parent, no teacher."
python scripts\runlog.py --name P012_sigma_recheck -- python scripts\paired_eval.py --preset m100 --data ko-en --tokens 300M --models p6d p6d_s2
if errorlevel 1 echo [WARN] paired_eval failed - check that both checkpoints load

echo.
echo =============================================================
echo [2/2] context - the mC pair from result 039, same instrument, same run
echo =============================================================
python scripts\runlog.py --name P012_sigma_recheck --note "[2/2] paired(mC_wsd, mC_wsd_s2) again, so both numbers sit in ONE log and cannot be blamed on a session difference."
python scripts\runlog.py --name P012_sigma_recheck -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_wsd_s2
if errorlevel 1 echo [WARN] paired_eval failed

python scripts\runlog.py --name P012_sigma_recheck --note "=================================================================" "WHAT TO RECORD" "  1. paired delta, SE and t for p6d vs p6d_s2." "  2. the same for mC_wsd vs mC_wsd_s2 - ***in this same log***, so the" "     comparison cannot be blamed on a session difference." "  3. both full-val values, to compare against result 012's printed 3.704531" "     and 3.692656. ***They will NOT match*** - different estimator." "" "HOW TO READ IT" "  p6d delta near 0.012" "      -^> explanation (2). sigma is CONDITION DEPENDENT. Keep two rows in" "         EXPERIMENT_BASELINES: dense-no-parent-no-teacher vs mC-KD-parent-init." "         The resolution 0.024 stays justified for the dense condition." "  p6d delta near 0.001" "      -^> explanation (1). ***sigma = 0.012 was largely the old estimator.***" "         Then every 'below resolution, effectively equal' verdict in this repo" "         needs re-reading - result 039 section 3.2 already lists which ones." "  in between (the prediction)" "      -^> both effects are real. Report the split and stop; do not re-derive" "         the decision rule from one pair." "" "LIMITS: ONE pair per condition. This is not an estimate of sigma with useful" "  precision - it is a comparison of two instruments on the same pair." "  ***And the resolution 0.024 is a decision rule, not a statistical bound.***" "  Changing it is a REVIEW2 judgement, not this run's output." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:NOP6D
echo.
echo [STOP] runs\ckpt\m100_ko-en_300M_p6d.pt is missing.
if not defined TL_NOPAUSE pause
exit /b 5

:NOP6DS2
echo.
echo [STOP] runs\ckpt\m100_ko-en_300M_p6d_s2.pt is missing (the seed-2024 dense run).
if not defined TL_NOPAUSE pause
exit /b 5

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
