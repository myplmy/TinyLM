@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P086_Stage2_main.bat -- full run with per-layer scalar multipliers
REM ==========================================================================
REM  
REM   HYPOTHESIS
REM     part of the MLP tying penalty (+0.0637 at d8, +0.1049 at d16 - it GROWS
REM     with depth) is not caused by sharing the weights but by sharing the scale.
REM     This run gives each tied middle layer its own gate/up/down scalar while
REM     the weights stay shared.
REM  
REM   WHY IT COSTS NO MEMORY
REM     at inference the multiplier folds into the per-row alpha we already store.
REM     Residency increase is zero. That is rare for a quality lever.
REM  
REM   JUDGEMENT - fixed before the run
REM     ruler 0.0018, control d12_cla2_r20 = 3.6054.
REM     Also confirm deploy_mb did NOT move. If it moved, the folding claim is wrong.
REM  
REM   COST: about 3.2h.   PLAN: test_plan/P086_*.md
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P086_stage2_main --note "[1/1] d12 + mlp-lrm, full 300M run"
python scripts\runlog.py --name P086_stage2_main -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --mlp-lrm --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_lrm
if errorlevel 1 echo [WARN] arm failed - continuing


echo.
python scripts\runlog.py --name P086_stage2_main --note "=================================================================" "READ IN THIS ORDER" "1. paired_eval against d12_cla2_r20 (3.6054). Ruler is 0.0018." "2. deploy_mb must be UNCHANGED. If it grew, the zero-residency claim fails." "3. the multipliers carry weight decay 0.01 on purpose - without it the" "   scale symmetry drifts and the norm grows without bound (paper fig 4)." "================================================================="

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
