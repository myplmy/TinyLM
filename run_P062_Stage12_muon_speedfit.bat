@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage12_muon_speedfit.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Muon x15 is worth -0.04406 on the recursive body and -0.03625 on d16 no-recursion
REM     (result 076 section 10). It has never been put on the 32 MiB shapes.
REM     If d14 plus muon lands near 3.537 it is the new best model that clears BOTH targets.
REM
REM   READ IN THIS ORDER
REM     1. Each arm against its AdamW twin: d12 3.59031 and d14 3.57313.
REM     2. grad_max is expected near 1.1 with n_skip 0. Skips mean the multiplier is too high.
REM     3. If d12 and d14 gains differ by more than 0.005 the gain is depth dependent - say so.
REM     4. Judgement needs paired_eval, not this log.
REM
REM   COST: about 2.6h.   PLAN: test_plan/P062 stage12
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage12_muon_speedfit --note "[1/2] depth 12 no recursion plus muon x15 - the 28.0 MiB point"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage12_muon_speedfit -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_norecur_muon15
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_norecur_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage12_muon_speedfit --note "[2/2] depth 14 no recursion plus muon x15 - the 32 MiB candidate"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage12_muon_speedfit -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d14_cla2_norecur_muon15
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d14_cla2_norecur_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage12_muon_speedfit --note "DONE. Judgement needs paired_eval, not this log."

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
