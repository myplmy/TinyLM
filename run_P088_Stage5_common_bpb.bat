@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage5_common_bpb.bat -- the one ruler that crosses pools
REM ==========================================================================
REM
REM   THE PROBLEM THIS SOLVES
REM     P087 and P088 measured the same thing - double the steps - and got
REM     -0.11547 and -0.10672. Reading those side by side is what produced
REM     the headline "repetition is nearly free". But they were measured on
REM     DIFFERENT test sets:
REM       300M pool  val is 13.5 percent Korean
REM       600M pool  val is  5.5 percent
REM       1200M pool val is  0.0 percent   NOTE: not one Korean character
REM     (diag_val_lang, recorded 2026-08-06). Korean wikipedia runs out at
REM     300.19M tokens and prepare() takes val from the tail of the stream.
REM
REM     Worse, result 075 section 6 found that a small cache's val.bin is
REM     byte-identical to a slice of a bigger cache's train.bin, so
REM     paired_eval cannot be pointed at a common cache either.
REM
REM   WHY common_bpb IS THE ANSWER
REM     it scores external text that is in NO pool, tokenised per model. All
REM     eight models here share our BPE, so the comparison is clean.
REM
REM   ONE CALL, NOT EIGHT
REM     common_bpb only builds a comparison table when a single invocation
REM     has two or more models. Splitting it exits 0 and produces nothing.
REM     That mistake has been made twice. All eight go in one call.
REM
REM   PRESET
REM     one --preset is passed for all eight and it is WRONG for the two d16
REM     models on purpose. resolve_ckpt falls back to a global search when
REM     exactly one candidate matches the tag, and every tag here is unique.
REM     If a model is skipped, read the printed name - do not assume.
REM
REM   NO TRAINING. Inference only. COST: about 0.6h.
REM   PLAN: test_plan/P088 (Korean filename) Stage5
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P088_stage5_common_bpb --note "[1/1] eight models, three pools, one external text"
python scripts\runlog.py --name P088_stage5_common_bpb -- python scripts\common_bpb.py --preset m100s8 --data-default ko-en --tokens 300M --micro-bs 2 --ce-chunk 4096 --models d12_cla2_r20_p300_e1 d12_cla2_r20_p300_e2 d12_cla2_r20_p300_e4 d12_cla2_r20 d16_cla2_r20 d12_cla2_r20_p12_t300 d12_cla2_r20_p12_t600 d16_cla2_r20_p12_t600
if errorlevel 1 echo [WARN] common_bpb failed - continuing

echo.
python scripts\runlog.py --name P088_stage5_common_bpb --note "=================================================================" "READ IN THIS ORDER" "1. the skipped list. Eight models must be scored. If any is missing" "   the global checkpoint search did not resolve it." "2. bpb ordering across ALL eight. This is the first table in the" "   repo that puts three different pools on one ruler." "3. the two step-doubling deltas: e1 to e2 on the 300M pool, and" "   t300 to t600 on the 1.2B pool. If they stay within 0.01 of each" "   other, repetition really is nearly free at our scale." "4. e4 versus t600. Same 600M... no: e4 is 1200M tokens. Read the" "   token counts from the registry, not from the tag." "5. absolute bpb here is NOT comparable to external models - the" "   common text is 8.7 percent contaminated (result 053). Between" "   OUR models it is a shared constant and therefore valid." "================================================================="

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
