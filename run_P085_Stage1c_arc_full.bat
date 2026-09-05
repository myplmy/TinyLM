@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage1c_arc_full.bat -- three percent short of a verdict
REM ==========================================================================
REM
REM   WHERE THIS CAME FROM
REM     result 074 section 4 said the accuracy axis was closed: unpaired
REM     estimates put the needed item count at 45,000 to 254,000. Stage1b
REM     added McNemar and the paired test cut that by up to 18.4x:
REM       arc_easy  d16 minus mC   z +1.97   needed 2,451   have 2,376
REM     Three point two percent short. Every other pair is still far away.
REM
REM   THE ITEMS EXIST
REM     we score only the test split. The local dataset card says
REM       train 2,251 + test 2,376 + validation 570 = 5,197
REM     which is 2.1x the needed count. Expected z scales with sqrt(n):
REM       d16 minus mC   +1.97 gives about +2.9
REM       d12 minus mC   +1.56 gives about +2.3
REM     If that holds it is the first time accuracy separates two of our
REM     models at all.
REM
REM   ARM 1 IS THE CONTAMINATION CHECK AND IT COMES FIRST
REM     ARC questions are science exam items and fineweb-edu scrapes the
REM     open web. Overlap is not zero a priori. KorQuAD turned out to be
REM     94.8 percent of our stream (result 060) and we found that AFTER
REM     using it. So: measure the overlap, then score. If the overlap is
REM     large the whole task is void, not just the extra splits.
REM
REM   arc_easy_full IS A SEPARATE TASK NAME ON PURPOSE
REM     the existing arc_easy (test only) keeps its numbers. Overwriting it
REM     would silently break every past comparison.
REM
REM   NO TRAINING. Inference only. COST: about 0.6h.
REM   PLAN: test_plan/P085 (Korean filename) section 3.0c, Stage1c
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage1c_arc_full --note "[1/3] fetch all three ARC-Easy splits - must print 5197"
python scripts\runlog.py --name P085_stage1c_arc_full -- python scripts\fetch_bench_data.py --only arc_easy_full
if errorlevel 1 echo [WARN] fetch failed - the arms below will say so

python scripts\runlog.py --name P085_stage1c_arc_full --note "[2/3] overlap against our training stream - READ THIS BEFORE THE SCORES"
python scripts\runlog.py --name P085_stage1c_arc_full -- python scripts\diag_bench_overlap.py --task arc_easy_full --data ko-en --tokens 600M --sample 400 --k 12
if errorlevel 1 echo [WARN] overlap check reported contamination - read the rate first

python scripts\runlog.py --name P085_stage1c_arc_full --note "[3/3] arc_easy_full - 5197 items, chance 25 percent"
python scripts\runlog.py --name P085_stage1c_arc_full -- python scripts\eval_bench_suite.py --task arc_easy_full --n 6000 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] arc_easy_full failed - continuing

echo.
python scripts\runlog.py --name P085_stage1c_arc_full --note "=================================================================" "READ IN THIS ORDER" "1. the fetch arm must print 5197. Anything else means the split" "   string was wrong and the scores below are void." "2. arm 2 is the real overlap measurement. Scale: KorQuAD was 94.8" "   percent of our stream, SQuAD train 8.7. Over 10 percent means" "   the task is void, not just imprecise. Read it BEFORE the scores." "3. McNemar z for d16 minus mC. Above 2 means accuracy separated two" "   of our models for the first time. Below means the axis stays" "   closed and gold CE remains the only downstream ruler." "4. gold CE on 5197 items should track the 2376-item value closely." "   If it moves a lot, the extra splits are a different distribution." "5. do NOT overwrite arc_easy numbers with these. Different task." "================================================================="

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
