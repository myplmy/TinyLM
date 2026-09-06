@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P005_Stage1b_muon_lr_bracket.bat -- close the bracket before Stage2
REM ==========================================================================
REM
REM   WHAT STAGE1 FOUND (result 076)
REM     763 steps, 100M tokens, same day / cache / seed / val crop:
REM       AdamW     3.78547
REM       Muon x1   3.91984   +0.13437   64.0x the dense ruler - LOSES badly
REM       Muon x5   3.78453   -0.00094    0.4x - dead even
REM       Muon x15  3.75625   -0.02922   13.9x - WINS
REM     The axis is open. But the three points are MONOTONE, so the optimum
REM     is at or beyond x15 and we do not know where.
REM
REM   WHY THIS COMES BEFORE STAGE2
REM     Stage2 is a 3.7h full-length run at ONE multiplier. Spending it at
REM     x15 when the optimum is x30 leaves us with "at x15 it did this",
REM     which is the same shape of mistake x1 would have been. 1.3h here
REM     protects 3.7h there.
REM
REM   TWO POINTS, GEOMETRIC
REM     x30 and x45. If x30 beats x15 and x45 is worse than x30, the bracket
REM     is closed and Stage2 runs at x30. If x45 still wins, the band is
REM     wider than expected and we say so rather than adding a third arm
REM     here - at that point the honest move is to ask why.
REM
REM   WATCH grad_max
REM     x15 already carried the highest grad_max of the four (0.7721 versus
REM     0.4526 at x5). Raising lr further is the direction where divergence
REM     lives. n_skip above 0 or grad_max above about 5 means the arm is not
REM     a quality measurement, it is a stability measurement.
REM
REM   COST: about 1.3h.   PLAN: test_plan/P005 (Korean filename) Stage1b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

timeout /t 15 /nobreak

python scripts\runlog.py --name P005_stage1b_muon_lr_bracket --note "[1/2] Muon lr x30"
python scripts\runlog.py --name P005_stage1b_muon_lr_bracket -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 763 --tokens 300M --pool-tokens 600M --exact-cache --optimizer muon --muon-lr-mult 30 --tag d12_cla2_r20_s763_muon30
if errorlevel 1 echo [WARN] x30 arm failed - continuing

python scripts\runlog.py --name P005_stage1b_muon_lr_bracket --note "[2/2] Muon lr x45"
python scripts\runlog.py --name P005_stage1b_muon_lr_bracket -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 763 --tokens 300M --pool-tokens 600M --exact-cache --optimizer muon --muon-lr-mult 45 --tag d12_cla2_r20_s763_muon45
if errorlevel 1 echo [WARN] x45 arm failed - continuing

set TL_WB_TAG=d12_cla2_r20_s763_muon30
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=d12_cla2_r20_s763_muon45
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

echo.
python scripts\runlog.py --name P005_stage1b_muon_lr_bracket --note "=================================================================" "READ IN THIS ORDER" "1. grad_max and n_skip FIRST. These are the two highest learning" "   rates we have ever run. If either arm diverged its val is not a" "   quality number and the bracket question is unanswered." "2. json optimizer must say muon and muon_lr_mult must say 30 / 45." "   If muon_lr_mult is null the flag did not reach the optimiser." "3. put the five multipliers in order: 1 5 15 30 45 against" "   +0.13437 / -0.00094 / -0.02922 / ? / ?. The bracket is closed" "   when the middle of the last three is the best of the three." "4. compare ONLY with the four 763-step arms from Stage1. Never with" "   a 2289-step run - warmup fraction and anneal schedule differ." "5. Stage2 uses whichever multiplier wins here, not x15 by default." "================================================================="

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
