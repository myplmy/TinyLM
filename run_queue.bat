@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_queue.bat -- INTERACTIVE SCHEDULER, driven by experiments.tsv
REM  Rule: ai_dev_tool\03 section 6 -- one experiment, one batch. This file only
REM        CALLS them, and it does not know their names.
REM =============================================================================
REM
REM ***NOTHING IS HARDCODED HERE.*** The list of experiments, their priority,
REM   GPU usage, estimated hours and one-line purpose all live in
REM       experiments.tsv
REM   Claude writes a new experiment batch and adds ONE LINE to that file.
REM   This batch is never edited again.
REM
REM HOW TO USE
REM   Double-click it, or run it from the TinyLM folder.
REM     1. it prints the menu (only batches that exist and are not -done)
REM     2. type the ids you want, in the order you want, on ONE line:  0 1 3
REM     3. it echoes the plan back with warnings, asks y or n
REM     4. from then on it is unattended
REM   Just press ENTER to cancel.
REM
REM   Put  0  first whenever the code changed. ***The smoke check is the only
REM   step that aborts the whole queue*** - 2026-07-31 left every training run
REM   dead for hours because a report regression went unsmoked.
REM
REM WHY A PYTHON HELPER
REM   ***THE PERCENT SIGN IS BANNED IN THIS REPO'S BATCH FILES*** (lint rule 3),
REM   so `for /f` cannot be used and a file cannot be read here. scripts\
REM   queue_menu.py reads the table, validates the picks, and GENERATES
REM   runs\_queue_plan.bat containing only `call` lines plus the errorlevel
REM   policy. ***A machine now enforces ai_dev_tool\03 section 6 rule 2.***
REM
REM   The generated file lives in runs\ (gitignored) so lint_bat.py and the
REM   -done bookkeeping never see it.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist experiments.tsv goto NOTSV

python scripts\queue_menu.py --list
if errorlevel 1 goto MENUBAD

set TL_PICK=
set /p TL_PICK=ids to run, in order, space separated:
if not defined TL_PICK goto NOTHING

python scripts\queue_menu.py --build "!TL_PICK!"
if errorlevel 1 goto BUILDBAD

set TL_GO=
set /p TL_GO=start now, y or n:
if /i not "!TL_GO!"=="y" goto ABORT

REM child batches must not pause, or the queue stalls overnight
set TL_NOPAUSE=1

echo.
echo [queue] started
date /t
time /t

call runs\_queue_plan.bat
set TL_RC=!errorlevel!

echo.
echo =================================================================
echo [queue] finished
date /t
time /t
echo.
echo   Logs: test_result for experiment runs, smoketest_logs for gates.
echo   ***Read each batch's own WHAT TO RECORD block before reading any
echo   number out of the run*** - several of them tell you which numbers are
echo   NOT to be trusted.
echo   Before quoting any ms/step:  python scripts\check_spill.py ^<log^>
echo =================================================================
set TL_NOPAUSE=
if not "!TL_RC!"=="0" echo [queue] the plan returned !TL_RC! - see above
if not defined TL_NOPAUSE pause
exit /b 0

:MENUBAD
echo.
echo [STOP] could not read experiments.tsv (see the message above).
if not defined TL_NOPAUSE pause
exit /b 8

:BUILDBAD
echo.
echo [queue] nothing valid was selected. Cancelled.
if not defined TL_NOPAUSE pause
exit /b 0

:NOTSV
echo.
echo [STOP] experiments.tsv is missing. It is the only source of truth for the menu.
if not defined TL_NOPAUSE pause
exit /b 8

:NOTHING
echo.
echo [queue] no ids entered. Nothing to do.
if not defined TL_NOPAUSE pause
exit /b 0

:ABORT
echo.
echo [queue] cancelled. Nothing was run.
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
