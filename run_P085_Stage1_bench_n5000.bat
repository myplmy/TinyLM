@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_REVIEW4_expC_bench_n5000.bat -- REVIEW4 experiment C: raise n to 5,000
REM =============================================================================
REM
REM  WHY
REM    Result 067 sec 12.5 measured the detection boundary: a 0.08 nats gap shows
REM    up at n=400 and a 0.04 nats gap does NOT. Required N for the answer-CE is
REM    5,275 to 5,816 at SE 0.002, and the accuracy 95pc CI at n=400 is about
REM    +-5pp. So the current downstream table cannot rank our two budget winners.
REM    d16_cla2_r20 wins full-val by 0.0412 (20x the ruler) and LOSES hellaswag
REM    27.5 vs 29.8 - that contradiction may be nothing but sampling noise.
REM
REM  WHAT IT DOES
REM    Three usable tasks (hellaswag, piqa, arc_easy) at n=5000 on the three
REM    models that already have a n=400 row, so the two tables are comparable.
REM
REM  READING THE OUTPUT
REM    1. Does the n=5000 ranking match the n=400 ranking? If it flips, the
REM       n=400 table was noise and every downstream claim built on it is void.
REM    2. Read the answer-CE column, not accuracy. CE moved in the right
REM       direction at n=400 already; accuracy is what disagreed.
REM    3. Chance is 25.0 for hellaswag and arc_easy, 50.0 for piqa. boolq is
REM       NOT in this batch on purpose - its baseline is majority 62, not 50.
REM
REM  COST: no training. GPU inference only, about 40 minutes for 9 model-task
REM        pairs. Nothing is written to runs/ckpt.
REM
REM  PLAN: docs/review/202609031800_REVIEW4_draft (Korean filename) experiment C
REM =============================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P079_review4_expC --num 067 --note "[1/3] hellaswag n=5000"
python scripts\runlog.py --name P079_review4_expC --num 067 -- python scripts\eval_bench_suite.py --task hellaswag --n 5000 --preset m100R1c --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] hellaswag arm failed - continuing

python scripts\runlog.py --name P079_review4_expC --num 067 --note "[2/3] piqa n=5000"
python scripts\runlog.py --name P079_review4_expC --num 067 -- python scripts\eval_bench_suite.py --task piqa --n 5000 --preset m100R1c --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] piqa arm failed - continuing

python scripts\runlog.py --name P079_review4_expC --num 067 --note "[3/3] arc_easy n=5000"
python scripts\runlog.py --name P079_review4_expC --num 067 -- python scripts\eval_bench_suite.py --task arc_easy --n 5000 --preset m100R1c --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] arc_easy arm failed - continuing

echo.
python scripts\runlog.py --name P079_review4_expC --num 067 --note "=================================================================" "READ IN THIS ORDER" "1. compare the n=5000 ranking with the n=400 ranking in result 067 sec 12." "   If the order flips, the n=400 downstream table was sampling noise." "2. read the answer-CE column first. Accuracy is the column that" "   disagreed with full-val, CE was already consistent." "3. chance is 25.0 for hellaswag and arc_easy, 50.0 for piqa." "4. arc_easy at n=5000 may be capped by the dataset size - check the" "   printed item count, do not assume it reached 5000." "================================================================="

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
