@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P037_stage2b_verify.bat  --  P037 STAGE 2B : verify the FILTERED cache
REM  Plan: test_plan\P037_...md   Prior: result 023
REM =============================================================================
REM
REM WHY THIS EXISTS
REM   Stage 2 regenerated ko-edu-en with the spam filter and wrote it to
REM   data_cache\ko-edu-en_600000000_filtered - a DIFFERENT directory, on purpose,
REM   so runs trained on the old cache stay comparable to their own logs.
REM   Then the verification step read the OLD cache anyway, because the diagnostic
REM   had no way to point at the new one. Its output matched result 018 to the
REM   decimal, which is the only reason anyone noticed (result 023).
REM
REM   Separating the output safely and being able to READ the separated output are
REM   two different jobs. Stage 2 did the first only. --doc-filter is the second.
REM
REM WHAT TO EXPECT IF THE FILTER WORKED
REM   total val loss well below 6.0879, no single document near 5 percent of val,
REM   max document length far below 88,351 tokens, and ko-en COMPLETELY unchanged
REM   (the filter is scoped to ko-edu-en per result 011 section 0.6).
REM   If ko-en moves at all, the scoping is wrong and stage 2 has to be redone.
REM
REM COST: minutes, no GPU.
REM =============================================================================

if not exist run100m.py goto BADROOT
set TL_NOPAUSE=1

echo =============================================================
echo [P037-2B] verify the filtered cache (the step 2 could not do)
echo =============================================================
python scripts\runlog.py --name P037-stage2b --note "[P037-2B] verify the filtered cache (the step stage 2 could not do)"

echo.
echo =============================================================
echo [1/3] FILTERED ko-edu-en - the measurement stage 2 was supposed to make
echo =============================================================
set TL_LOGNAME=P037-stage2b
set TL_DOCFILTER=1
set TL_DATA1=ko-edu-en
set TL_DATA2=
set TL_TOKENS=600M
set TL_INSPECT=7
call scripts\batch\tool_valdocs.bat
if errorlevel 1 echo [WARN] filtered diagnosis failed - continuing

echo.
echo =============================================================
echo [2/3] UNFILTERED ko-edu-en - the before picture, same command shape
echo   Reading both in ONE log is the point. Result 023 happened because the
echo   before and after numbers lived in different files.
echo =============================================================
set TL_LOGNAME=P037-stage2b
set TL_DOCFILTER=
set TL_DATA1=ko-edu-en
set TL_DATA2=
set TL_TOKENS=300M
set TL_INSPECT=7
call scripts\batch\tool_valdocs.bat
if errorlevel 1 echo [WARN] unfiltered diagnosis failed - continuing

echo.
echo =============================================================
echo [3/3] CONTROL ko-en - must be untouched
echo =============================================================
set TL_LOGNAME=P037-stage2b
set TL_DOCFILTER=
set TL_DATA1=ko-en
set TL_DATA2=
set TL_TOKENS=300M
set TL_INSPECT=3
call scripts\batch\tool_valdocs.bat
if errorlevel 1 echo [WARN] control diagnosis failed - continuing

python scripts\runlog.py --name P037-stage2b --note "=================================================================" "WHAT TO RECORD" "  1. filtered vs unfiltered: total val loss, and the top-contribution table" "  2. max document length in the filtered cache" "  3. that ko-en did not move at all" "  4. ALWAYS copy the '[data] ... -^> path' line next to each number. Result 023" "     happened because nobody checked which cache produced the figures." "" "HOW TO READ IT" "  loss drops a lot     -^> the old ko-edu-en numbers were measuring spam. Every" "      cross-dataset claim built on them is void, and P028 stage 1 can proceed." "  loss barely moves    -^> the difficulty was distributed and the 7 documents" "      were a symptom, not the cause. Then the dataset choice itself is the" "      question - see docs/methods/ on corpus selection." "  ko-en moved         -^> scoping bug. Stop and fix before anything else." "=================================================================" 
echo done.
pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
