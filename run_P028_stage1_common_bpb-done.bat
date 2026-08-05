@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P028_stage1_common_bpb.bat  --  P028 STAGE 1 : cross-dataset comparison,
REM         made valid for the first time
REM  Plan: test_plan\P028_...md   Unblocked by: result 023 section 8
REM =============================================================================
REM
REM THE PROBLEM THIS CLOSES
REM   Result 009 measured ko-edu-en against ko-en and had to write "observation is
REM   worse but the verdict is impossible" - different tokenizers, different val
REM   sets. Every data experiment has been stuck behind that ever since.
REM
REM   bpb = loss / ln2 / bytes_per_token. Give two models the SAME source text with
REM   the SAME byte count and the denominator matches, so bpb becomes tokenizer
REM   independent. The text has to be something NEITHER model trained on.
REM
REM   SQuAD v2 contexts: 19,029 unique paragraphs, 14.0 MB, English Wikipedia prose,
REM   already in datasets\squad\, in none of our training corpora. Rationale and
REM   the alternatives considered are in docs\methods\07_corpus_selection.md.
REM
REM WHY IT IS UNBLOCKED NOW
REM   Result 023 section 8: the ko-edu-en spam filter is verified. Measuring against
REM   a corpus whose val loss was 26 percent spam would have produced a number that
REM   describes the spam, not the data.
REM
REM ***READ bpb, NOT loss.***
REM   The tool prints both on purpose. Token counts differ between tokenizers, so
REM   the loss column is NOT comparable across rows. If a summary ever quotes the
REM   loss column across datasets, that is result 009's mistake happening again.
REM
REM !! ENGLISH ONLY. SQuAD is English. This measures compression of English prose.
REM   Korean ability is not in this number at all. There is no Korean common text
REM   yet - that gap is recorded in 07_corpus_selection.md section 3.
REM
REM COST: inference only, minutes. No GPU time required.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P028-1] common source text bpb - the cross-dataset comparison
echo =============================================================
python scripts\runlog.py --name P028-stage1 --note "[P028-1] common source text bpb - the cross-dataset comparison"

echo.
echo [guard] SQuAD source present
python scripts\runlog.py --name P028-stage1 --note "[guard] SQuAD source present"
if not exist datasets\squad\train-v2.0.json goto NOSQUAD

echo.
echo =============================================================
echo [1/2] ko-en dense versus ko-edu-en dense - the question from result 009
echo =============================================================
python scripts\runlog.py --name P028-stage1 --note "[1/2] ko-en dense versus ko-edu-en dense - the question from result 009"
python scripts\runlog.py --name P028-stage1 -- python scripts\common_bpb.py --models dense dense --data ko-en ko-edu-en --tokens 300M --max-docs 4000
if errorlevel 1 echo [WARN] dense comparison failed - continuing

echo.
echo =============================================================
echo [2/2] the tied candidates on the same text
echo =============================================================
python scripts\runlog.py --name P028-stage1 --note "[2/2] tied candidates on the same text"
python scripts\runlog.py --name P028-stage1 -- python scripts\common_bpb.py --models p6d mC_g8_k4 mA_g4s34_k4 --data ko-en ko-en ko-en --tokens 300M --max-docs 4000
if errorlevel 1 echo [WARN] tied comparison failed - continuing

python scripts\runlog.py --name P028-stage1 --note "=================================================================" "WHAT TO RECORD" "  1. the bpb column ONLY. Copy the whole table, but the verdict is bpb." "  2. bytes/token per tokenizer - a finding about the TOKENIZER, not the model." "  3. token counts. A large difference means one tokenizer compresses this" "     text much better, which is itself worth knowing." "" "HOW TO READ IT" "  bpb gap larger than about 0.008 (= the 0.024 nats resolution in bpb terms)" "      -^> the first VALID cross-dataset statement this project has. Record which" "         corpus wins and update docs\methods\07_corpus_selection.md." "  bpb gap smaller than that" "      -^> the corpora are equivalent on English prose. That is also an answer," "         and it means the ko-edu-en curation bought nothing measurable here." "" "LIMITS: ENGLISH ONLY - Korean ability is not measured / SQuAD is Wikipedia" "  prose and both models saw English web text, so the domain is not alien to" "  either (fair, but not a hard generalisation test) / one seed per model." "=================================================================" 
echo done.
pause
exit /b 0

:NOSQUAD
echo.
echo =================================================================
echo [STOP] datasets\squad\train-v2.0.json not found. Nothing was executed.
echo =================================================================
pause
exit /b 3

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
