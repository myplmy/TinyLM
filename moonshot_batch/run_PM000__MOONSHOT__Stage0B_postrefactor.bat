@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  PM000 Stage0B - post-refactor Latin GQA wiring contract. USER RUN ONLY.
REM  This is a new stage name so the original Stage0 evidence is never mixed.
REM  No training/data prep, but it imports torch and builds a small model.
REM  The AI must never execute this batch or its diagnostic.
REM ============================================================================

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage0B_postrefactor --note "[Stage0B] Revalidate PM000 after algorithm isolation: R1, R3, cache, state, backward"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage0B_postrefactor -- python scripts\diag_pm000_latin_gqa.py --device cpu
if errorlevel 1 goto CONTRACTFAIL

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage0B_postrefactor --note "STAGE0B PASS. Wiring only. Do not run Stage1 until the latest full-smoke disposition is recorded."
goto DONE

:CONTRACTFAIL
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage0B_postrefactor --note "STAGE0B FAIL. Do not run Stage1 or Stage2. Treat this as a code defect, not a model result."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 1

:PREFLIGHTFAIL
echo.
echo [STOP] moonshot branch or namespace preflight failed. Nothing was run.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo.
echo [STOP] run this from the repo root or moonshot_batch folder.
if not defined TL_NOPAUSE pause
exit /b 9

:DONE
set PYTHONIOENCODING=
echo [READ] Stage0B is wiring-only. Review the latest full smoke before Stage1.
if not defined TL_NOPAUSE pause
exit /b 0
