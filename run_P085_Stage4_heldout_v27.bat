@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage4_heldout_v27.bat -- the Korean ruler we built ourselves
REM ==========================================================================
REM
REM   WHY THIS IS ONLY POSSIBLE NOW
REM     held-out has existed since v1 and we have never scored a model with
REM     it. Every version until v2.7 carried a defect that made scoring
REM     meaningless: v2.5 and earlier had an item with NO correct answer
REM     (E-272), and v2.3 through v2.6 had two items with TWO correct
REM     answers (E-157, E-205). v2.7 fixed the last two. D1 and D6 are now 0.
REM
REM   WHAT IT BUYS
REM     result 075 s11.5 named the confound we cannot currently separate: a
REM     bigger pool also means more English, and common_bpb is English only.
REM     A Korean ruler splits that. KoBEST gave us two tasks - COPA at
REM     chance, HellaSwag well above it - and this is the third, and the
REM     only one whose item design we control.
REM
REM   ARM 1 PRINTS WHICH VERSION IT USED AND REFUSES A BROKEN ONE
REM     fetch_bench_data now reads the newest held-out folder directly and
REM     raises if D1 or D6 is non-zero. Scores from a version with a
REM     two-answer item are not scores. Read the version line - it is not in
REM     the tag, so a later version silently changes the numbers.
REM
REM   ARM 2 IS THE OVERLAP CHECK AND ITS COVERAGE IS PARTIAL
REM     our prompts are short. With k=8 roughly 260 of 300 carry a window.
REM     Read the "checked" count, not just the rate. And note what this tool
REM     cannot see: held-out is generated from TinyDataset templates while we
REM     train on Korean Wikipedia plus fineweb-edu, so verbatim overlap is
REM     near zero by construction. The interesting leak would be CONCEPT
REM     overlap, and n-gram matching does not measure that.
REM
REM   CHANCE IS 25 PERCENT AND THE DESIGN DEFENDS IT
REM     four candidates, correct_index perfectly balanced at 75/75/75/75,
REM     candidate lengths matched since v2.3. Result 068 measured the
REM     trivial-strategy baselines: longest-choice 25.0 percent, and the
REM     negation shortcut sits at 30.2 percent (z +2.1) - so a model that
REM     only learned "pick the negated one" would score about 30.
REM
REM   NO TRAINING. Inference only. COST: about 0.3h.
REM   PLAN: test_plan/P085 (Korean filename) Stage4
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage4_heldout_v27 --note "[1/3] export the canonical held-out - prints the version and refuses D1 or D6 non-zero"
python scripts\runlog.py --name P085_stage4_heldout_v27 -- python scripts\fetch_bench_data.py --only stage1_heldout
if errorlevel 1 echo [WARN] export refused or failed - the scores below are void, read the reason

python scripts\runlog.py --name P085_stage4_heldout_v27 --note "[2/3] overlap against our training stream - partial coverage, read the checked count"
python scripts\runlog.py --name P085_stage4_heldout_v27 -- python scripts\diag_bench_overlap.py --task stage1_heldout --data ko-en --tokens 600M --sample 300 --k 8
if errorlevel 1 echo [WARN] overlap check flagged something - read it before the scores

python scripts\runlog.py --name P085_stage4_heldout_v27 --note "[3/3] score three models on 300 items, chance 25 percent"
python scripts\runlog.py --name P085_stage4_heldout_v27 -- python scripts\eval_bench_suite.py --task stage1_heldout --n 400 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] scoring failed - continuing

echo.
python scripts\runlog.py --name P085_stage4_heldout_v27 --note "=================================================================" "READ IN THIS ORDER" "1. the version line from arm 1. It must say held-out_v2.7 with" "   D1 0 and D6 0. Anything else and stop reading." "2. arm 2 checked count and rate. Under 1 percent is background." "   Over 10 percent voids the task. Partial coverage is expected." "3. accuracy against 25 percent chance, and against 30.2 - that is" "   what the negation shortcut alone would score (result 068)." "   Beating 25 but not 30 means we measured the shortcut, not skill." "4. gold CE ordering. On three tasks so far d16 wins gold CE and" "   ties on accuracy. If that repeats here it is 4 for 4 and the" "   dissociation is a property of our models, not of one benchmark." "5. this is a KOREAN ruler. Result 075 s11.5 wanted exactly this to" "   split more-unique-tokens from more-English. Compare the model" "   ordering here with the common_bpb ordering." "================================================================="

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
