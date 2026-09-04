@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P087_Stage1_epoch12.bat -- repeat exposure, pool fixed at 300M
REM ==========================================================================
REM  
REM   WHAT IS DIFFERENT FROM P088
REM     P088 adds UNIQUE tokens (pool 1.2B). This adds REPEAT exposure: the pool is
REM     pinned at 300M and only the training length moves, so arm 1 is 1.0 epoch and
REM     arm 2 is 2.0 epochs over the same text.
REM  
REM   WHY IT MATTERS THAT THE POOL IS SMALL
REM     the 1.2B pool has a validation split that is 0.0 percent Korean (measured).
REM     The 300M pool does not. This is the ONLY token-axis experiment that can say
REM     anything about Korean.
REM  
REM   EXPECTED - written before the run
REM     arm e1 will look WORSE than any existing 300M run. That is expected: those
REM     runs drew from a 600M pool. Read inside this series only, never across.
REM  
REM   COST: about 5.1h.   PLAN: test_plan/P087_*.md
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P087_stage1_epoch12 --note "[1/2] e1 - 300M tokens over a 300M pool = 1.0 epoch"
python scripts\runlog.py --name P087_stage1_epoch12 -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 2289 --tokens 300M --pool-tokens 300M --exact-cache --tag d12_cla2_r20_p300_e1
if errorlevel 1 echo [WARN] arm failed - continuing

python scripts\runlog.py --name P087_stage1_epoch12 --note "[2/2] e2 - 600M tokens over the same pool = 2.0 epochs"
python scripts\runlog.py --name P087_stage1_epoch12 -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 4578 --tokens 300M --pool-tokens 300M --exact-cache --tag d12_cla2_r20_p300_e2
if errorlevel 1 echo [WARN] arm failed - continuing


echo.
python scripts\runlog.py --name P087_stage1_epoch12 --note "=================================================================" "READ IN THIS ORDER" "1. e2 minus e1 with paired_eval. Ruler is the dense series, 0.0021." "2. check val minus train_ce on BOTH arms before judging. Baseline series" "   sits near zero. Above 0.3 means suspect the measurement first." "3. do NOT compare either arm with the existing 300M runs - different pool." "4. wsd anneal is a fraction of steps, so e2 anneals later in wall time." "   That is intended. Write it as tokens AND a proportional schedule." "================================================================="

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
