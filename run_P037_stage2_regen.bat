@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P037_stage2_regen.bat  --  P037 STAGE 2 : regenerate ko-edu-en with a
REM                                 CONTENT filter, then re-diagnose
REM  Plan: test_plan\P037_...md    Prior: result 018 (stage 1)
REM =============================================================================
REM
REM WHAT STAGE 1 ACTUALLY FOUND (result 018) - and why it changed the fix
REM   The design assumed a LENGTH problem and planned a length cap. Stage 1 says
REM   otherwise:
REM     - boundaries are FINE. eos count 684 vs 685 documents, zero documents
REM       under 16 tokens, median length 1156. No over-splitting.
REM     - the 7 huge documents are SEO exam-dump spam: a certification sales
REM       pitch with unrelated novel text spliced in and the product keyword
REM       injected mid-sentence. Newlines 0.0 percent, line uniqueness 100
REM       percent - single-line mega documents.
REM   So a length cap alone would truncate spam rather than remove it. What is
REM   needed is a CONTENT filter; the length and share caps are secondary.
REM
REM   The ko-en control stayed healthy: excluding its top documents makes the
REM   loss slightly WORSE (+0.0013), meaning its heaviest documents are EASIER
REM   than average. Nothing pathological. Note that the tool nevertheless printed
REM   "random splitting is needed" for ko-en - that canned verdict fires on a
REM   near-zero delta and should not be taken as a recommendation. CLAUDE.md
REM   already holds that a full rewrite of the split lacks grounds.
REM
REM ***THIS BATCH IS GUARDED AND WILL STOP.***
REM   The content filter is not implemented in prepare(). The guard checks for
REM   the flag. Regenerating the cache without the filter would overwrite a cache
REM   we can still diagnose, and buy nothing.
REM
REM WHAT STAGE 2 MUST IMPLEMENT FIRST (scope: ko-edu-en ONLY, per result 011)
REM   1. --doc-filter in prepare(): drop documents whose line-uniqueness is ~100
REM      percent AND whose newline fraction is ~0 AND that exceed a size, i.e.
REM      the exact signature stage 1 measured. Log how many documents were cut.
REM   2. --doc-cap: per document share of val, as a second net.
REM   3. Write the new cache to a DIFFERENT directory. Do not overwrite - runs
REM      trained on the current cache must stay comparable to their own logs.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P037-2] ko-edu-en regeneration with a content filter - GUARDED
echo =============================================================

echo.
echo [guard] is --doc-filter implemented
python -c "import sys; sys.exit(0 if '--doc-filter' in open('tinylm/cli.py',encoding='utf-8').read() else 7)"
if errorlevel 1 goto NOTIMPL

echo.
echo =============================================================
echo [1/2] regenerate ko-edu-en with the filter, into a new cache
echo =============================================================
python scripts\runlog.py --name P037-stage2 -- python run100m.py prepare --data ko-edu-en --tokens 600M --exact-cache --doc-filter --doc-cap 0.01
if errorlevel 1 goto PREPBAD

echo.
echo =============================================================
echo [2/2] re-diagnose - the same measurement that found the problem
echo =============================================================
set TL_LOGNAME=P037-stage2
set TL_NOPAUSE=1
set TL_DATA1=ko-edu-en
set TL_DATA2=ko-en
set TL_INSPECT=7
call scripts\batch\tool_valdocs.bat
if errorlevel 1 echo [WARN] re-diagnosis failed - continuing

echo.
echo =================================================================
echo WHAT TO RECORD
echo   1. how many documents the filter removed, and the token count before
echo      and after - if it cut more than a few percent, inspect what went
echo   2. the new top-contribution table: no document should carry 5 percent
echo   3. the new total val loss, and that ko-en did not move
echo.
echo HOW TO READ IT
echo   spam gone, val loss drops a lot -^> the old ko-edu-en numbers were
echo       measuring the spam. Every cross-dataset claim built on them is void.
echo   spam gone, val loss barely moves -^> the difficulty was distributed, and
echo       the 7 documents were a symptom. Then P028 stage 1 is the next step.
echo   ko-en moved at all -^> the filter is not scoped correctly. Stop and fix.
echo =================================================================
echo done.
pause
exit /b 0

:NOTIMPL
echo.
echo =================================================================
echo [STOP] --doc-filter is not implemented. Nothing was executed.
echo   Regenerating without it would overwrite a cache we can still
echo   diagnose and gain nothing. See the header for the scope.
echo =================================================================
pause
exit /b 3

:PREPBAD
echo.
echo =================================================================
echo [STOP] preparation failed. The diagnosis step depends on it.
echo =================================================================
pause
exit /b 1

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
