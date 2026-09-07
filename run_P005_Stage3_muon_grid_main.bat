@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P005_Stage3_muon_grid_main.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     x15 was chosen on a 763-step grid. At 2289 steps the effect grew 1.51 times
REM     (-0.02922 to -0.04406). When the effect moves the optimum can move with it.
REM     Arm 3 recovers the optimiser-by-tokens arm that died on 2026-09-07.
REM
REM   READ IN THIS ORDER
REM     1. Arms 1 and 2 against d12_cla2_r20_muon15 3.51375. Ruler is 0.0018.
REM     2. If either beats x15 by more than 0.0036 the baseline proposal takes that value.
REM     3. If all three sit inside the ruler the multiplier is flat - that is also information.
REM     4. Arm 3 minus d16_cla2_norecur_t600 answers whether Muon and tokens add or overlap.
REM     5. This stage answers up to 2289 steps only. 9156 is still unknown.
REM
REM   COST: about 6.1h.   PLAN: test_plan/P005 stage3
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005_stage3_muon_grid_main --note "[1/3] muon multiplier x10 at the main scale"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage3_muon_grid_main -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-lr-mult 10 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_muon10
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon10
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage3_muon_grid_main --note "[2/3] muon multiplier x20 at the main scale"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage3_muon_grid_main -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-lr-mult 20 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_muon20
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon20
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage3_muon_grid_main --note "[3/3] optimiser x tokens - the arm that died. --ckpt-tokens is the fix"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage3_muon_grid_main -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d16_cla2_norecur_muon15_t600
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_muon15_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage3_muon_grid_main --note "DONE. This stage answers up to 2289 steps only. 9156 is still unknown."

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
