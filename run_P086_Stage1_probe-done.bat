@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P086_Stage1_probe.bat -- 250-step probe for --mlp-lrm
REM ==========================================================================
REM  
REM   WHAT
REM     Tied layers share one W, so they also share its SCALE. The paper this
REM     comes from (arXiv:2601.04890, Falcon team) shows the norm of a weight-
REM     decayed matrix layer is set by sqrt(eta/lambda) - by the optimizer, not by
REM     the data - and that adding a scalar multiplier lets block output norms grow
REM     with depth. A tied stack cannot express that at all.
REM  
REM   WHAT THIS PROBE ANSWERS
REM     only throughput and stability. The paper says at most a couple of percent
REM     slower. Our session-to-session ms/step drift is 7.5 percent, so this must
REM     be compared against a same-day baseline or not at all.
REM  
REM   READING THE OUTPUT
REM     1. the [P086] line: 8 tied middle layers, 24 scalars.
REM     2. ms/step and VRAM. A drop worse than 5 percent changes the exchange rate.
REM     3. grad_max in the json, not the printed the printed grad bar.
REM     4. DO NOT read val.
REM  
REM   COST: about 0.3h.   PLAN: test_plan/P086_*.md
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P086_stage1_probe --note "[1/1] d12 + mlp-lrm, 250-step probe"
python scripts\runlog.py --name P086_stage1_probe -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --mlp-lrm --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_lrm_probe
if errorlevel 1 echo [WARN] arm failed - continuing


echo.
python scripts\runlog.py --name P086_stage1_probe --note "=================================================================" "READ IN THIS ORDER" "1. the [P086] line must appear. No line = the flag did not land (trap 37)." "2. ms/step versus a same-day baseline only. Drift across days is 7.5 pct." "3. grad_max from the json. The printed bar is a 10-step sample." "4. DO NOT read val. 250 steps carries no quality signal." "================================================================="

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
