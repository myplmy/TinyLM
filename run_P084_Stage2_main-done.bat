@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P084_Stage2_main.bat -- full run, prelude/coda keep their own K/V
REM ==========================================================================
REM  
REM   PRECONDITION
REM     Stage1 probe must have printed deploy_mb at or under 34 MiB. If it did not,
REM     this run is pointless - the model cannot ship.
REM  
REM   WHAT IT MEASURES
REM     cla_group=2 costs -0.0268 in quality (result 057). Nobody has ever asked
REM     how much of that cost comes from the head and the tail as opposed to the
REM     body. This arm frees only the edges.
REM  
REM   JUDGEMENT - fixed before the run
REM     ruler: recursion series 2 sigma = 0.0018. control d12_cla2_r20 = 3.6054.
REM     below the ruler        to close the axis
REM     above AND nats/MiB ^ to  0.00427 to adopt candidate
REM     above BUT nats/MiB lower      to record as bad exchange rate, not rejected
REM  
REM   COST: about 3.2h.   PLAN: test_plan/P084_*.md
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P084_stage2_main --note "[1/1] d12 + no-cla-edges, full 300M run"
python scripts\runlog.py --name P084_stage2_main -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --no-cla-edges --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2e_r20
if errorlevel 1 echo [WARN] arm failed - continuing


echo.
python scripts\runlog.py --name P084_stage2_main --note "=================================================================" "READ IN THIS ORDER" "1. paired_eval against d12_cla2_r20 (3.6054). Ruler is 0.0018." "2. divide the gain by the MiB it cost. Compare with 0.00427 nats/MiB," "   which is what a third recursion visit costs on this body." "3. a gain that loses on nats/MiB is a BAD EXCHANGE RATE, not a rejection." "================================================================="

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
