@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_smoke_check.bat  --  RUN THIS AFTER ANY CODE CHANGE, BEFORE ANY LONG RUN
REM =============================================================================
REM
REM  WHAT IT IS
REM    A few minutes of tiny-preset training on synthetic data, followed by a check
REM    that every instrumentation field a result document depends on was actually
REM    written to the json. It is the cheapest net this repo has.
REM
REM  WHY IT EXISTS AS A ROOT BATCH
REM    The smoke logic lives in scripts\batch\tool_smoke.bat, which is a MODULE.
REM    Modules are not for direct invocation - an experiment or a maintenance entry
REM    point calls them. This file is that entry point.
REM
REM  WHY YOU SHOULD ACTUALLY RUN IT (2026-07-31, paid for in real time)
REM    The bpw accounting commit changed report(self, bpw=1.95) to bpw=None but left
REM    one line still using the raw argument. Every single training run then died with
REM        TypeError: unsupported operand type(s) for *: 'int' and 'NoneType'
REM    It surfaced only when P035 was launched, hours later. tool_smoke.bat runs
REM    `train --tiny`, which calls report() - so this batch would have caught it in
REM    minutes. Skipping the smoke was the entire cost of that incident.
REM
REM  READING THE OUTPUT
REM    The answer is the contract check that runs LAST: one block per training run,
REM    then a final total-error-count line. Zero means every instrumentation field a
REM    result document depends on was actually written to the json.
REM    The [VERIFY] banner is only a SECTION TITLE, not the answer - that wording
REM    confused things once already.
REM    Everything else is noise. Losses from 30 steps on synthetic data mean NOTHING:
REM    do not read them, compare them, or record them anywhere.
REM    Logs land in smoketest_logs (via TL_OUTDIR below), NOT in test_result.
REM    Filename carries the minute and the commit sha7.
REM
REM  COST: a few minutes, GPU barely used. Writes sm_* tags into runs\ (throwaway).
REM =============================================================================

if not exist run100m.py goto BADROOT

REM ***2026-08-07: TL_OUTDIR is the fix for logs landing in test_result.***
REM   This header used to CLAIM logs land in smoketest_logs while tool_smoke.bat
REM   never passed --outdir, so all 13 runlog calls wrote to test_result.
REM   Documented but not implemented (trap 13). runlog.py now reads TL_OUTDIR, so
REM   setting it HERE covers every call below it - one place, not thirteen.
REM   Filenames become {YYYYMMDDHHMM}_{name}_{sha7}.txt and every log opens with a
REM   [commit] banner, so you can tell WHICH COMMIT a smoke ran against.
set TL_OUTDIR=smoketest_logs
set TL_LOGNAME=smoke
set TL_NOPAUSE=1
call scripts\batch\tool_smoke.bat
if errorlevel 1 echo [WARN] smoke reported a problem - read which field is missing

REM ***2026-09-03: exit-code summary. The contract check counts INSTRUMENTATION
REM   fields only - it never looks at any arm's exit code. On 2026-09-03 one arm
REM   exited 1 and the last line still said 'Long runs are safe to start'.
REM   summarize_smoke.py reads this log back and joins BOTH verdicts into one.
REM   PYTHONIOENCODING is set because the summary prints non-ASCII marks and the
REM   default cp949 console kills python on them.
REM ***2026-09-06: the `--` was MISSING on the line below and runlog.py therefore
REM   refused the whole invocation with `unrecognized arguments`. summarize_smoke.py
REM   was added on 2026-09-03 to close trap 38 and it HAD NEVER RUN ONCE - two smoke
REM   sessions passed with it dead. On 2026-09-05 diag_sparse34_pack.py exited 1 and
REM   the last line still said 'Long runs are safe to start', which is the exact
REM   failure summarize_smoke exists to prevent.
REM   argparse writes its error to stderr and dies BEFORE opening the log file, so
REM   the failure was visible on the console and absent from the log - that is the
REM   'console differs from log' the user reported. lint_bat rule 25 now catches a
REM   runlog invocation that carries a command without the `--` separator.
set PYTHONIOENCODING=utf-8
echo.
python scripts\runlog.py --name smoke -- python scripts\summarize_smoke.py
if errorlevel 1 echo [WARN] summarize_smoke reported a failing arm - read section A above

REM ***2026-09-06: the old trailing block restated 'Long runs are safe to start'
REM   UNCONDITIONALLY, so it contradicted summarize_smoke on every bad run. The
REM   summary already joins both verdicts (exit codes AND the field contract) into
REM   one line, so restating it here can only ever disagree with it. Point at it
REM   instead of repeating it - one concept, one definition (R14).
echo.
python scripts\runlog.py --name smoke --note "=================================================================" "VERDICT: the single answer is the last line of the SUMMARY above," "  which joins BOTH checks - every arm's exit code AND the field" "  contract. Neither one alone is the verdict." "  Section A lists arms that exited non-zero. Section B lists arms" "  that exited 0 with an error mark in their output - read those by" "  hand, exit codes cannot see them." "  The [VERIFY] banner further up is a section title, not the answer." "=================================================================" "done."
REM 2026-08-13 - clear TL_OUTDIR before returning. setlocal SHOULD scope it, but a
REM   queue run leaked it to three later batches and their experiment logs went to
REM   smoketest_logs. The exact leak path was never pinned down, so clear it on
REM   every exit path. runlog.py also decides by name now (3 nets).
set TL_OUTDIR=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
set TL_OUTDIR=
if not defined TL_NOPAUSE pause
exit /b 9
