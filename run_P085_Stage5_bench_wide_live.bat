@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage5_bench_wide_live.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     The wide-table implementation was approved and written today but has never
REM     run for real. Three things need a live run to be true rather than asserted:
REM       1. test_result/bench_results.tsv is created
REM       2. the bench/table_wide key carries a table
REM       3. INCREMENTAL - running one task again does not erase the other task
REM
REM     Point 3 is the risk the proposal itself flagged in section 11. The table is
REM     rebuilt in full from the canonical TSV every time, so a partial push must
REM     not lose rows. Arm 2 is the test: it scores a DIFFERENT task on the SAME
REM     models, and afterwards the stage1_heldout rows must still be there.
REM
REM   READ IN THIS ORDER
REM     1. after arm 1: the pushed line must say the table row count, 3 models.
REM     2. after arm 2: the row count must GROW, not reset.
REM     3. arm 3 prints the canonical TSV. Count the rows per model - it must be
REM        tasks times metrics, i.e. 2 tasks x 3 metrics = 6 rows per model.
REM     4. the W&B screen check is yours: does Chart fields show y_metric.
REM
REM   NO TRAINING. COST: about 0.8h.   PLAN: test_plan/P085 Stage5
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage5_bench_wide_live --note "[1/3] first task - this creates the canonical TSV"
python scripts\runlog.py --name P085_stage5_bench_wide_live -- python scripts\eval_bench_suite.py --task stage1_heldout --n 400 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] first bench push failed - continuing - continuing

python scripts\runlog.py --name P085_stage5_bench_wide_live --note "[2/3] second task on the same models - the incremental test"
python scripts\runlog.py --name P085_stage5_bench_wide_live -- python scripts\eval_bench_suite.py --task arc_easy --n 400 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] second bench push failed - continuing - continuing

python scripts\runlog.py --name P085_stage5_bench_wide_live --note "[3/3] print the canonical TSV in both shapes"
python scripts\runlog.py --name P085_stage5_bench_wide_live -- python scripts\bench_tsv.py --wide
if errorlevel 1 echo [WARN] bench_tsv read failed - continuing - continuing

python scripts\runlog.py --name P085_stage5_bench_wide_live --note "DONE. Rows must be 6 per model after arm 2. If stage1_heldout rows vanished, the upsert key is wrong and the wide table is not safe."

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
