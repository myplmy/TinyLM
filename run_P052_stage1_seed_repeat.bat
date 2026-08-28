@echo off
REM =============================================================================
REM  P052 stage 1  -  seed repetition. What is sigma in the CURRENT condition.
REM                   2 training runs plus paired eval, about 3.4 hours
REM
REM  WHY THIS MATTERS MORE THAN IT LOOKS
REM    Every judgement in this repository uses a resolution of 2 sigma = 0.0034,
REM    and that number comes from result 049 which measured ONE pair of seeds under
REM    the no-KD parent-init condition. Since then the standard condition changed:
REM    --no-ckpt became the default and the shallow dense family appeared.
REM    We have been applying a ruler measured elsewhere.
REM
REM    Recent findings that live or die on this number:
REM      d8_dense vs mC_initonly_nc  +0.0014   called "indistinguishable"
REM      mC_cla1_ag4 vs standard     +0.0033   called "just under 2 sigma"
REM      cycle vs block              -0.0157   called "4.6 sigma"
REM    If sigma is actually larger, the first two conclusions change.
REM
REM  ARMS - seed 2024, everything else identical to the existing runs
REM    mC_initonly_s2   the tied 20-layer control
REM    d8_dense_s2      the shallow dense point that the frontier claim rests on
REM
REM  PREDICTIONS
REM    R1  seed spread is 0.002 to 0.005 in both families. Result 049 measured
REM        0.0017 for one pair, and 2 sigma = 0.0034 came from doubling it.
REM    R2  the two families have DIFFERENT spreads. Nobody has checked this and
REM        we have been using one ruler for both.
REM    R3  resident identical within each family - seed does not change shape.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P052_stage1_seed_repeat --note "=============================================================================" "P052 stage 1   what is sigma in the CURRENT condition" "The 0.0034 ruler came from one seed pair measured before --no-ckpt became" "the default and before the shallow dense family existed. About 3.4 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P052_stage1_seed_repeat --note "[1/3] mC_initonly_s2 - seed 2024, otherwise identical to mC_initonly_nc"
python scripts\runlog.py --name P052_stage1_seed_repeat -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --tag mC_initonly_s2
if errorlevel 1 echo [WARN] mC_initonly_s2 failed - continuing
set TL_WB_TAG=mC_initonly_s2
call scripts\batch\tool_wandb_push.bat

timeout /t 15 /nobreak

echo.
python scripts\runlog.py --name P052_stage1_seed_repeat --note "[2/3] d8_dense_s2 - seed 2024, otherwise identical to d8_dense"
python scripts\runlog.py --name P052_stage1_seed_repeat -- python run100m.py train --preset m100s4 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d8_dense_s2
if errorlevel 1 echo [WARN] d8_dense_s2 failed - continuing
set TL_WB_TAG=d8_dense_s2
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P052_stage1_seed_repeat --note "[3/3] paired - seed spread within each family, on one ruler"
python scripts\runlog.py --name P052_stage1_seed_repeat -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly_s2 mC_initonly_nc
if errorlevel 1 echo [WARN] paired 1 failed - continuing
python scripts\runlog.py --name P052_stage1_seed_repeat -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models d8_dense_s2 d8_dense
if errorlevel 1 echo [WARN] paired 2 failed - continuing

echo.
python scripts\runlog.py --name P052_stage1_seed_repeat --note "=============================================================================" "READ IN THIS ORDER" "1. the two seed spreads. 2 sigma for each family = 2 x the absolute delta." "2. R2 - are the two families different. If they are, we need TWO rulers and" "   EXPERIMENT_BASELINES must say which one applies where." "3. re-judge these three claims with the new ruler:" "     d8_dense vs mC_initonly_nc  +0.0014" "     mC_cla1_ag4 vs standard     +0.0033" "     cycle vs block              -0.0157" "   The third survives almost any plausible sigma. The first two may not." "4. one seed pair gives a RANGE not a sigma. Two pairs is still not many." "   Write the number with that caveat attached, every time." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
