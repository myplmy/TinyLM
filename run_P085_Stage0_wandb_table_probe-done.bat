@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage0_wandb_table_probe.bat -- can one Custom Chart merge runs?
REM ==========================================================================
REM
REM   WHY THIS EXISTS
REM     the W&B visualisation proposal put a Stage0 in front of everything:
REM     "log a 3-row bench/table by hand on any two runs and see whether one
REM     Custom Chart can read them together". It never said HOW to log it.
REM     The user asked for the missing tool. This is it.
REM
REM   WHAT IT DOES
REM     uploads three DUMMY runs (probe_modelA/B/C) to project tinylm-probe,
REM     each carrying the same long-format table under key bench/table:
REM       model / task / metric / value / n / n_asked / skipped / seed / pmi
REM     9 rows each (3 tasks x 3 metrics). Values are obvious dummies -
REM     acc 0.11..0.43 and gold_ce 9.1..10.3, well outside our real range.
REM
REM   WHY NOT PROJECT tinylm
REM     what we are testing is a property of W&B, not of our project, and
REM     three dummy runs in the real workspace would stay there. Pass
REM     TL_WB_PROJECT=tinylm if you want them next to the real runs.
REM
REM   AFTER IT RUNS
REM     the script prints the exact clicks. Read that block - the judgement
REM     is a human one and it takes about 0.2h.
REM
REM   NO TRAINING. NO GPU. Uploads only.
REM   PLAN: test_plan/P085 (Korean filename) section 3.0d
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8
if not defined TL_WB_PROJECT set TL_WB_PROJECT=tinylm-probe

python scripts\runlog.py --name P085_stage0_wandb_table_probe --note "[1/2] dry run - show the tables without uploading"
python scripts\runlog.py --name P085_stage0_wandb_table_probe -- python scripts\wandb_table_probe.py --project !TL_WB_PROJECT! --dry-run
if errorlevel 1 echo [WARN] dry run failed - continuing

python scripts\runlog.py --name P085_stage0_wandb_table_probe --note "[2/2] upload three dummy runs"
python scripts\runlog.py --name P085_stage0_wandb_table_probe -- python scripts\wandb_table_probe.py --project !TL_WB_PROJECT!
if errorlevel 1 echo [WARN] upload failed - continuing

echo.
python scripts\runlog.py --name P085_stage0_wandb_table_probe --note "=================================================================" "READ IN THIS ORDER" "1. the printed click-by-click block. The judgement is visual." "2. x axis must show three task buckets, each with three model bars." "3. then change the vega filter from acc to acc_norm to gold_ce." "   One chart definition has to serve all three metrics." "4. if it works the proposal takes plan A. If not, plan B." "5. the dummy runs are yours to delete in the W&B UI." "================================================================="

set TL_WB_PROJECT=
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
