@echo off
REM ===== LOGGING (added 2026-07-31) =====
REM   Every python command below is run through scripts\runlog.py, which prints to the
REM   console in real time AND appends to test_result\log_YYYYMMDD_NAME.txt line by line,
REM   flushing and fsync-ing as it goes. If this batch dies halfway, or the machine loses
REM   power, everything up to the last couple of seconds is already on disk.
REM   Losing the log of a long run costs the whole run, so this is not optional.
REM   Exit codes pass through unchanged, so every `if errorlevel` below still works.

REM ===== relocated-style header: this batch runs from either location =====
if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ===== P037 stage 1 : is the DOCUMENT BOUNDARY judgement itself trustworthy =====
REM   Plan: test_plan\P037 (was P028 stage 0.7)   Evidence: test_result\011 section 0.6
REM
REM ***** WHY THIS EXISTS *****
REM   P028 stage 0.5 reported "one document is 23.5 percent of val (352,399 tokens)".
REM   That was WRONG. The tool guessed the eos id by frequency - from the FIRST 5M TRAIN
REM   tokens - and applied it to val. Since stage 0 had just established that train-head and
REM   val have different distributions, the tool was broken BY THE VERY EFFECT IT FOUND.
REM   The real maximum document is 88,350 tokens (5.9 percent).
REM
REM   Stage 0.6 used tok.token_to_id of the eos string instead, which is authoritative. But
REM   TWO unverified assumptions into its own limits section. Fixing prepare() before closing
REM   those means regenerating data to match a diagnosis we have not checked.
REM   This batch checks them.
REM
REM ***** WHAT IS CHECKED *****
REM   [A] can a literal eos-looking string in the source text be confused with the boundary
REM   [B] boundary-count sanity: eos occurrences vs document count vs length distribution,
REM       and how many absurdly short documents exist (over-splitting signal)
REM   [C] decode the top contributing documents and READ them - does a new document heading
REM       appear in the MIDDLE (that would mean a MISSING boundary, not a long document)
REM   [D] character statistics - tables, lists, code, non-Korean. If the big documents are
REM       weird in CONTENT, a length cap is the wrong fix
REM
REM COST: CPU, minutes. No training. Writes nothing to runs.
REM ERRORLEVEL POLICY: nothing here is a hard stop.

echo ============================================================
echo [P037-1] document boundary trustworthiness
echo ============================================================

echo.
echo [guard] checking whether diag_val_docs.py accepts --inspect
python -c "import sys,pathlib; s=pathlib.Path('scripts/diag_val_docs.py').read_text(encoding='utf-8'); sys.exit(0 if '--inspect' in s else 3)"
if errorlevel 3 goto NOTIMPL

echo.
echo ============================================================
echo [1/2] SUSPECT : ko-edu-en - the 7 huge documents
echo   Stage 0.6 found 7 documents of 72k-88k tokens carrying 37 pct of tokens and
echo   53 pct of the loss. Are they really ONE document each
echo ============================================================
python scripts\runlog.py --name P037-stage1 -- python scripts\diag_val_docs.py --data ko-edu-en --tokens 300M --arch dense --tag dense --inspect 7
if errorlevel 1 echo [WARN] ko-edu-en inspect failed - continuing

echo.
echo ============================================================
echo [2/2] CONTROL : ko-en - known healthy, so it calibrates the checks
echo   If ko-en shows the same over-splitting signals, the signal is about the TOOL,
echo   not about ko-edu-en.
echo ============================================================
python scripts\runlog.py --name P037-stage1 -- python scripts\diag_val_docs.py --data ko-en --tokens 300M --arch dense --tag dense --inspect 3
if errorlevel 1 echo [WARN] ko-en inspect failed - continuing

echo.
echo ================================================================
echo WHAT TO RECORD
echo   1. [A] does tok.encode("^<eos^>") return the boundary id
echo   2. [B] eos count, document count, median/max length, pct of documents under 16 tokens
echo   3. [C] for each big document: does a heading reappear mid-document
echo   4. [D] Korean pct, ASCII pct, digit pct, newline pct, line uniqueness
echo   5. the same four for the ko-en control
echo.
echo HOW TO ACT
echo   all clean
echo       stage 0.6 is CONFIRMED. Proceed to P037 stage 2 (regenerate ko-edu-en) with a
echo       length cap plus a per-document share cap.
echo   [A] warns AND [B] shows many tiny documents
echo       OVER-SPLITTING. Escape special-token strings in prepare(), then re-run 0.6.
echo       Do NOT regenerate on the current numbers.
echo   [C] shows a heading mid-document
echo       MISSING boundary. The cause is not length at all - the fix is completely
echo       different and stage 2 as designed would be wrong.
echo   [D] points at tables / lists / code / non-Korean
echo       a length cap alone is insufficient. Design a CONTENT filter with it.
echo.
echo LIMITS: this reads the TOKENISED cache, not the raw dataset. It can tell you the
echo   boundaries look wrong, but confirming WHY may need the source documents.
echo ================================================================
echo done.
pause
exit /b 0

:NOTIMPL
echo.
echo ================================================================
echo [STOP] scripts\diag_val_docs.py has no --inspect flag.
echo   Nothing was measured. No files were written.
echo ================================================================
pause
exit /b 3

:BADROOT
echo.
echo [STOP] could not locate the repo root (run100m.py not found). Nothing was executed.
pause
exit /b 9
