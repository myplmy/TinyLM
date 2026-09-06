@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  PM000 Stage0 - Latin GQA wiring contract. USER RUN ONLY.
REM  No training and no dataset preparation. This still imports torch and builds
REM  a small model, so the AI must never execute this batch or its diagnostic.
REM ============================================================================

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage0_contract --note "[Stage0] R1 identity, R3 live path, cache agreement, state keys, finite backward"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage0_contract -- python scripts\diag_pm000_latin_gqa.py --device cpu
if errorlevel 1 goto CONTRACTFAIL

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage0_contract --note "STAGE0 PASS. This proves wiring only, not quality. Stage1 may now be run by the user."
goto DONE

:CONTRACTFAIL
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage0_contract --note "STAGE0 FAIL. Do not run Stage1 or Stage2. Treat this as a code defect, not a model result."
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
if not defined TL_NOPAUSE pause
exit /b 0
