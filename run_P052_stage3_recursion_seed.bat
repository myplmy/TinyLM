@echo off
REM =============================================================================
REM  P052 stage 3  -  a ruler for the recursion family.  about 3.3 hours.
REM
REM  WHY  (result 039 s8.5, 047 s13.6, 059 s13.6)
REM    We have two measured rulers - tied 0.0010 and dense 0.0042 - and we have
REM    been BORROWING the dense one for every recursion arm because recursion runs
REM    on a dense-like body. That is an assumption, not a measurement, and three
REM    of the last five judgements used it:
REM      cycle vs block at 2 unique   -0.0063   1.5x the borrowed ruler
REM      16 to 20 visits              -0.0044   1.05x
REM      20 to 28 visits              -0.0036   0.86x, rejected on that basis
REM    The last one REJECTED R=6. If the recursion ruler is narrower than the
REM    dense one, that rejection is wrong.
REM
REM  INDEPENDENT VARIABLE
REM    seed 1337 to 2024 on mC_cla1_ag4_r20. Everything else identical, including
REM    grad checkpointing ON - the twin must match, confound and all.
REM
REM  PREDICTIONS
REM    T1  indistinguishable from mC_cla1_ag4_r20. Any seed pair should be.
REM    T2  the absolute delta lands between the tied 0.0005 and the dense 0.0021.
REM        Recursion re-uses weights like tying, so the averaging argument in
REM        result 039 s8.2 predicts the narrow end.
REM    T3  if the delta is above 0.0021 the borrowed ruler was too narrow and the
REM        R=6 rejection in result 059 s13.4 has to be reopened.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P052_stage3_recursion_seed --note "=============================================================================" "P052 stage 3   the recursion family ruler" "We have been borrowing the dense ruler for recursion arms. This measures it." "The twin keeps grad checkpointing ON so the pair matches." "=============================================================================="

echo.
python scripts\runlog.py --name P052_stage3_recursion_seed --note "[1/2] mC_cla1_ag4_r20 with seed 2024 - ckpt ON, matching the original"
python scripts\runlog.py --name P052_stage3_recursion_seed -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --ce-chunk 2048 --cla-group 1 --attn-group 4 --train-repeat 2.0 --init-from --tag mC_cla1_ag4_r20_s2
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
set TL_WB_TAG=mC_cla1_ag4_r20_s2
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P052_stage3_recursion_seed --note "[2/2] the seed pair on one ruler, matched schedules"
python scripts\runlog.py --name P052_stage3_recursion_seed -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20_s2 mC_cla1_ag4_r20 --match-train-repeat
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P052_stage3_recursion_seed --note "=============================================================================" "READ IN THIS ORDER" "1. the absolute delta. 2 sigma is twice it (result 049 convention)." "2. T2 - between 0.0005 and 0.0021 supports the averaging mechanism." "3. T3 - above 0.0021 reopens the R=6 rejection in result 059 s13.4 and the" "   cycle-beats-block margin at 2 unique blocks in 059 s14.2.1." "4. add the number to EXPERIMENT_BASELINES B.9.1 as a THIRD family ruler and" "   stop writing 'we borrow the dense ruler'." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
