@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P037_stage2c_verify.bat  --  P037 STAGE 2C : verify the filtered cache,
REM                                   third attempt
REM  Plan: test_plan\P037_...md   Prior: results 023 sections 2 and 7
REM =============================================================================
REM
REM TWO FAILED ATTEMPTS, TWO DIFFERENT REASONS. Both are fixed now.
REM   stage 2  - the diagnostic had no way to point at the filtered cache, so it
REM              read the OLD one. Output matched result 018 to the decimal.
REM              Fixed by --doc-filter on diag_val_docs / eval_slices / diag_cache.
REM   stage 2B - the filtered cache opened correctly, then the run died on
REM              "checkpoint not found: m100_ko-edu-en_600M_dense.pt". One flag
REM              (--tokens) meant BOTH the pool size and the training budget.
REM              The pool is 600M; the ko-edu-en model was trained on 300M.
REM              Fixed by --ckpt-tokens, which separates the two.
REM
REM   Also: 'set TL_DATA2=' does not blank a variable in cmd, it UNDEFINES it, so
REM   the tool's default came back and an unintended ko-en run appeared. The
REM   sentinel is now TL_DATA2=none.
REM
REM WHAT THE CONDITIONS MUST BE (check these against the log before reading numbers)
REM   pool             600M filtered   -^> [data] ... ko-edu-en_600000000_filtered
REM   training budget  300M            -^> [ckpt] ... m100_ko-edu-en_300M_dense.pt
REM   If either line says something else, STOP. That is how the last two failed.
REM
REM WHAT TO EXPECT IF THE FILTER WORKED
REM   total val loss well below 6.0879 / no single document near 5 percent of val /
REM   max document length far below 88,351 tokens / ko-en COMPLETELY unchanged.
REM   If ko-en moves at all the scoping is wrong and stage 2 must be redone.
REM
REM COST: minutes, no GPU.
REM =============================================================================

if not exist run100m.py goto BADROOT
set TL_NOPAUSE=1

echo =============================================================
echo [P037-2C] verify the filtered cache - third attempt
echo =============================================================
python scripts\runlog.py --name P037-stage2c --note "[P037-2C] verify the filtered cache - third attempt"

echo.
echo =============================================================
echo [1/3] FILTERED ko-edu-en : pool 600M filtered, checkpoint budget 300M
echo =============================================================
python scripts\runlog.py --name P037-stage2c --note "[1/3] FILTERED ko-edu-en : pool 600M filtered, checkpoint budget 300M"
set TL_LOGNAME=P037-stage2c
set TL_DOCFILTER=1
set TL_CKPTTOKENS=300M
set TL_DATA1=ko-edu-en
set TL_DATA2=none
set TL_TOKENS=600M
set TL_INSPECT=7
call scripts\batch\tool_valdocs.bat
if errorlevel 1 echo [WARN] filtered diagnosis failed - continuing

echo.
echo =============================================================
echo [2/3] UNFILTERED ko-edu-en : the before picture, same log
echo =============================================================
python scripts\runlog.py --name P037-stage2c --note "[2/3] UNFILTERED ko-edu-en : the before picture, same log"
set TL_LOGNAME=P037-stage2c
set TL_DOCFILTER=
set TL_CKPTTOKENS=
set TL_DATA1=ko-edu-en
set TL_DATA2=none
set TL_TOKENS=300M
set TL_INSPECT=7
call scripts\batch\tool_valdocs.bat
if errorlevel 1 echo [WARN] unfiltered diagnosis failed - continuing

echo.
echo =============================================================
echo [3/3] CONTROL ko-en : must be untouched
echo =============================================================
python scripts\runlog.py --name P037-stage2c --note "[3/3] CONTROL ko-en : must be untouched"
set TL_LOGNAME=P037-stage2c
set TL_DOCFILTER=
set TL_CKPTTOKENS=
set TL_DATA1=ko-en
set TL_DATA2=none
set TL_TOKENS=300M
set TL_INSPECT=3
call scripts\batch\tool_valdocs.bat
if errorlevel 1 echo [WARN] control diagnosis failed - continuing

python scripts\runlog.py --name P037-stage2c --note "=================================================================" "WHAT TO RECORD" "  0. FIRST: copy the '[data] ... -^> path' and '[ckpt] ...' lines for EVERY run." "     Two attempts already failed on exactly these two lines." "  1. filtered vs unfiltered: total val loss and the top-contribution table" "  2. max document length in the filtered cache" "  3. that ko-en did not move at all" "" "HOW TO READ IT" "  loss drops a lot   -^> the old ko-edu-en numbers were measuring spam. Every" "      cross-dataset claim built on them is void, and P028 stage 1 can proceed." "  loss barely moves  -^> difficulty was distributed; the 7 documents were a" "      symptom. Then the dataset choice itself is the question" "      (docs\methods\07_corpus_selection.md)." "  ko-en moved        -^> scoping bug. Stop and fix before anything else." "=================================================================" 
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
