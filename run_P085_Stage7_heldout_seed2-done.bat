@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage7_heldout_seed2.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage6 found that Korean held-out accuracy gets WORSE with depth:
REM     d16 27.0 percent (chance), d14 34.3, d12 37.7, McNemar z -3.53 for
REM     d16 minus d12, which survives Bonferroni over six comparisons.
REM     Four other instruments - log val, common bpb, hellaswag, arc_easy -
REM     all say the opposite.
REM
REM     Every one of those four models is a single seed. The reversal could be
REM     a seed effect and nobody has checked. The seed-2 checkpoints already
REM     exist, so the check costs no training at all.
REM
REM     Until this runs we cannot make depth a first-class axis in the fifth
REM     review. It is the cheapest experiment in the queue and it gates one of
REM     the biggest decisions.
REM
REM   READ IN THIS ORDER
REM     1. does the SIGN reproduce - is d16 seed2 still below d12 seed2.
REM     2. is d16 seed2 still indistinguishable from chance (25 percent).
REM     3. compare the seed-to-seed spread with the depth spread of 10.67pp.
REM        If seeds move more than depth does, held-out 300 cannot measure
REM        depth at all and we must recompute the required item count.
REM
REM   NO TRAINING. COST: about 0.3h.   PLAN: test_plan/P085 Stage7
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage7_heldout_seed2 --note "[1/2] Korean held-out v2.7 on the seed-2 checkpoints of the same three depths"
python scripts\runlog.py --name P085_stage7_heldout_seed2 -- python scripts\eval_bench_suite.py --task stage1_heldout --n 400 --preset m100s12 --models d12_cla2_norecur_s2 d14_cla2_norecur_s2 d16_cla2_norecur_s2 --wandb
if errorlevel 1 echo [WARN] seed2 held-out scoring failed - continuing

python scripts\runlog.py --name P085_stage7_heldout_seed2 --note "[2/2] all six together - seed and depth in one McNemar table"
python scripts\runlog.py --name P085_stage7_heldout_seed2 -- python scripts\eval_bench_suite.py --task stage1_heldout --n 400 --preset m100s12 --models d12_cla2_norecur d12_cla2_norecur_s2 d14_cla2_norecur d14_cla2_norecur_s2 d16_cla2_norecur d16_cla2_norecur_s2 --wandb
if errorlevel 1 echo [WARN] combined table failed - continuing

python scripts\runlog.py --name P085_stage7_heldout_seed2 --note "DONE. If the sign does not reproduce the depth reversal was a seed effect and Stage6 s wording is retracted."

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
