@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage1b_bench_wandb.bat -- re-run with the two tool fixes
REM ==========================================================================
REM
REM   WHY A RE-RUN
REM     Stage1 measured everything correctly but lost two things.
REM
REM     1 W&B got one model out of three. _run_name built the run id from the
REM       CLI --preset, and the batch handed the same preset to three models
REM       whose real presets are m100s8, m100s12 and m100R1c. Checkpoint loading
REM       recovered itself by global search, so the NUMBERS were always right.
REM       The run name did not recover, so _bench_eligible skipped two models.
REM       _run_name now reads the preset off the resolved checkpoint filename.
REM
REM     2 accuracy was compared unpaired. run_mc already returns per-item
REM       correctness and the code threw it away after the Wilson interval.
REM       Three models answer the SAME items, so McNemar applies and it is
REM       strictly more powerful. The needed-n figures in result 074 section 4
REM       (45,000 to 254,000) are unpaired upper bounds. This run replaces them
REM       with the real number.
REM
REM     Also fixed: the needed-N warning used to print "do not rank on this
REM     delta" even at t = +44.23, because needed-N is a precision target and
REM     not a significance test. It now branches on abs(t).
REM
REM   NOT A DUPLICATE
REM     same three models and same three tasks, but the previous run produced
REM     no McNemar rows and no W&B rows for two of three models. Those are the
REM     two outputs this run exists for.
REM
REM   COST: no training. GPU inference only, about 1.4h for 9 model-task pairs.
REM   PLAN: test_plan/P085 (Korean filename) Stage1b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage1b_bench_wandb --note "[1/3] hellaswag n=5000"
python scripts\runlog.py --name P085_stage1b_bench_wandb -- python scripts\eval_bench_suite.py --task hellaswag --n 5000 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] hellaswag arm failed - continuing

python scripts\runlog.py --name P085_stage1b_bench_wandb --note "[2/3] piqa - the dataset only has 1838 items"
python scripts\runlog.py --name P085_stage1b_bench_wandb -- python scripts\eval_bench_suite.py --task piqa --n 5000 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] piqa arm failed - continuing

python scripts\runlog.py --name P085_stage1b_bench_wandb --note "[3/3] arc_easy - the dataset only has 2376 items"
python scripts\runlog.py --name P085_stage1b_bench_wandb -- python scripts\eval_bench_suite.py --task arc_easy --n 5000 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] arc_easy arm failed - continuing

echo.
python scripts\runlog.py --name P085_stage1b_bench_wandb --note "=================================================================" "READ IN THIS ORDER" "1. the upload block must say pushed 3 and skipped 0. If a model is still" "   skipped, print the run name it looked for - the fix did not take." "2. the new McNemar block. needed-n there replaces the unpaired estimate" "   in result 074 section 4. If it is still above the item count, the" "   accuracy axis is closed for good on these three tasks." "3. gold CE numbers must reproduce result 074 to four decimals. They are" "   deterministic. If they moved, something else changed." "4. --preset m100s8 is deliberately WRONG for two of the three models." "   That is the regression test: the tool must correct itself." "================================================================="

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
