@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage10_muon_1200M.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage8 measures 1200M tokens with AdamW. There is no arm that answers whether
REM     Muon (-0.036) and tokens (-0.107) ADD or OVERLAP - that arm died on 2026-09-07.
REM     Additive would be about 3.407. Overlapping would be near 3.44.
REM     Either answer is useful: if they overlap, the optimiser is cheaper than more tokens.
REM
REM   READ IN THIS ORDER
REM     1. grad_max and n_skip first. 9156 steps is four times anything we have run with Muon.
REM     2. Against d16_cla2_norecur_t1200 from Stage8 - same tokens, same pool, AdamW.
REM     3. Pool over tokens is 1.0, BELOW the standard 2.0. Unique tokens about 758M.
REM     4. Every quote of this number must carry that caveat.
REM
REM   PREREQUISITE
REM     P088 Stage8 gives the AdamW twin. Without it this arm has nothing to subtract.
REM
REM   COST: about 5.9h.   PLAN: test_plan/P088 Stage10
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P088_stage10_muon_1200M --note "[1/1] 40 MiB shape, 1200M tokens, muon x15 - the two biggest settled levers multiplied"
timeout /t 15 /nobreak
python scripts\runlog.py --name P088_stage10_muon_1200M -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 9156 --tokens 1200M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d16_cla2_norecur_muon15_t1200
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_muon15_t1200
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P088_stage10_muon_1200M --note "DONE. Every quote of this number must carry that caveat."

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
