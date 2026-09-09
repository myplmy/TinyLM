@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage19_budget32_final.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     The two 32 MiB families were measured under different conditions. Put them on the
REM     same 600M tokens with the same optimiser so the comparison is one variable.
REM     Arm 3 carries the 40 MiB shape along for reference at the same token count.
REM
REM   READ IN THIS ORDER
REM     1. Quality alone should favour recursion by about -0.016.
REM     2. The speed floor is a HARD constraint, so the deployment candidate is no-recursion.
REM     3. Do not put the two families in one ranking table - split the columns.
REM     4. Pool is 1200M so log val does not compare to the 300M runs. Use common_bpb.
REM
REM   PREREQUISITE
REM     P062 Stage12 and Stage14 make the 300M twins. Not strictly required to run,
REM     but the comparison is thin without them.
REM
REM   COST: about 9.2h.   PLAN: test_plan/P062 stage19
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage19_budget32_final --note "[1/3] 32 MiB no-recursion plus muon at 600M tokens"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage19_budget32_final -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d14_cla2_norecur_muon15_t600
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d14_cla2_norecur_muon15_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage19_budget32_final --note "[2/3] 32 MiB recursion plus muon at 600M tokens - fails speed, quality reference"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage19_budget32_final -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-lr-mult 15 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d12_cla2_r20_muon15_t600
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon15_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage19_budget32_final --note "[3/3] 40 MiB depth 18 plus muon at 600M tokens"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage19_budget32_final -- python run100m.py train --preset m100s14 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d18_cla2_norecur_muon15_t600
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d18_cla2_norecur_muon15_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage19_budget32_final --note "DONE. Pool is 1200M so log val does not compare to the 300M runs. Use common_bpb."

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
