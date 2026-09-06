@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage6_bench_winners.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     P062 Stage8 makes two models that are the first candidates to satisfy BOTH
REM     deployment targets at once - residency and speed. Nothing is known about
REM     their downstream behaviour. Full-val is not a proxy for that: result 067
REM     s12.5 has a model winning full-val by 20 rulers and losing hellaswag.
REM
REM   PREREQUISITE: P062 Stage8.
REM
REM   READ IN THIS ORDER
REM     1. gold CE ordering versus accuracy ordering. Three tasks so far have
REM        split them. If it splits again the dissociation is a property of our
REM        models, not of one benchmark.
REM     2. McNemar z, not the confidence intervals. Unpaired CIs overlap when the
REM        paired test separates, and the reverse also happens.
REM     3. the Korean held-out chance level is 25.0 and the negation shortcut
REM        scores 30.2. Beating 25 but not 30 means we measured the shortcut.
REM     4. these models are the same FAMILY as d12_cla2_r20 - dense body, cla2.
REM        Accuracy has only ever separated ACROSS families. Expect no separation
REM        and say so if that is what happens.
REM
REM   NO TRAINING. COST: about 1.2h.   PLAN: test_plan/P085 Stage6
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage6_bench_winners --note "[1/2] Korean held-out v2.7 on the speed-compliant candidates"
python scripts\runlog.py --name P085_stage6_bench_winners -- python scripts\eval_bench_suite.py --task stage1_heldout --n 400 --preset m100s12 --models d16_cla2_norecur d14_cla2_norecur d12_cla2_norecur d12_cla2_r20 --wandb
if errorlevel 1 echo [WARN] Korean held-out scoring failed - continuing

python scripts\runlog.py --name P085_stage6_bench_winners --note "[2/2] English suite - arc_easy, hellaswag, piqa"
python scripts\runlog.py --name P085_stage6_bench_winners -- python scripts\eval_bench_suite.py --task arc_easy --n 5000 --preset m100s12 --models d16_cla2_norecur d14_cla2_norecur d12_cla2_norecur d12_cla2_r20 --wandb
if errorlevel 1 echo [WARN] arc_easy failed - continuing
python scripts\runlog.py --name P085_stage6_bench_winners -- python scripts\eval_bench_suite.py --task hellaswag --n 5000 --preset m100s12 --models d16_cla2_norecur d14_cla2_norecur d12_cla2_norecur d12_cla2_r20 --wandb
if errorlevel 1 echo [WARN] hellaswag failed - continuing

python scripts\runlog.py --name P085_stage6_bench_winners --note "DONE. Read McNemar z, not the CIs. Same family means accuracy probably will not separate - record that, it is a measurement."

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
