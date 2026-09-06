@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage0b_wandb_wide.bat -- the metric selector that did not work
REM ==========================================================================
REM
REM   WHAT STAGE0 SETTLED AND WHAT IT DID NOT
REM     the user confirmed on screen that a Custom Chart reads bench/table
REM     from three runs at once and draws three tasks x three models. That
REM     was the question Stage0 asked, and the answer is yes.
REM
REM     It left one thing broken: the Vega params selector (metric_choice)
REM     does not work in the W&B panel. Changing which metric is plotted
REM     means hand-editing a filter string inside the Vega spec. That is not
REM     "one chart definition serving three metrics" (review request s10).
REM
REM   WHAT THE W&B WORKSPACE AI SUGGESTED
REM     put the metrics in COLUMNS instead of rows. Then the official
REM     column-picker syntax works:
REM       "y": {"field": "${field:y_metric}", "type": "quantitative"}
REM     and a y_metric dropdown appears in Chart fields.
REM
REM       long   model task metric   value        9 rows per run
REM       wide   model task acc acc_norm gold_ce  3 rows per run
REM
REM   THIS BATCH UPLOADS BOTH, SIDE BY SIDE
REM     six dummy runs. long keeps its old names and key so the chart the
REM     user already built keeps working. wide gets probe_wide_* and a
REM     DIFFERENT key, bench/table_wide - two schemas under one key would
REM     hand Vega rows with missing columns.
REM
REM   THE TRADE IS NOT ONE-SIDED
REM     wide wins the selector and stops acc (0 to 1) sharing an axis with
REM     gold_ce (3.5 to 6.8). wide loses schema stability: a new metric adds
REM     a COLUMN, and two metrics can no longer be overlaid in one chart.
REM     The canonical store is the TSV either way, so switching later costs
REM     about 0.3h. Pick on the screen, not in the abstract.
REM
REM   NO TRAINING. NO GPU. COST: about 0.1h plus about 0.2h of screen work.
REM   PLAN: test_plan/P085 (Korean filename) Stage0b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage0b_wandb_wide --note "[1/2] dry run - prints both schemas and the click-by-click guide, uploads nothing"
python scripts\runlog.py --name P085_stage0b_wandb_wide -- python scripts\wandb_table_probe.py --project tinylm-probe --format both --dry-run
if errorlevel 1 echo [WARN] dry run failed - the upload below will probably fail too

python scripts\runlog.py --name P085_stage0b_wandb_wide --note "[2/2] upload six dummy runs to tinylm-probe - three long, three wide"
python scripts\runlog.py --name P085_stage0b_wandb_wide -- python scripts\wandb_table_probe.py --project tinylm-probe --format both
if errorlevel 1 echo [WARN] upload failed - continuing

echo.
python scripts\runlog.py --name P085_stage0b_wandb_wide --note "=================================================================" "READ IN THIS ORDER" "1. six lines saying uploaded. Three probe_model* and three" "   probe_wide_model*. Fewer than six means a wandb.init failed." "2. then the screen work is yours - about 0.2h. The log prints the" "   Vega spec to paste and the exact fields to set." "3. THE ONE QUESTION: does a y_metric dropdown appear in Chart" "   fields with acc / acc_norm / gold_ce in it?" "     yes gives wide is adopted, one chart serves three metrics" "     no  gives long stays, and we build three separate charts" "4. also check that switching y_metric to gold_ce moves the y axis" "   into the 9 to 10 band. That is the second thing wide buys." "5. the dummy runs are yours to delete in the W&B UI. Our no-delete" "   rule (R01) is about files on disk, not your W&B account." "================================================================="

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
