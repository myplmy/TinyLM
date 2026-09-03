@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage1_tokens600m.bat -- unique-token axis, pool 1.2B
REM ==========================================================================
REM  
REM   WHAT
REM     our winner sees about 3.7 tokens per parameter. External models in the same
REM     memory class see 8,026 to 121,739. Nobody has ever measured what happens
REM     when we simply feed more unique text. Deployment residency does not move.
REM  
REM   WHY BOTH ARMS ARE NEW RUNS
REM     the control has to come from the SAME pool, and no existing run used the
REM     1.2B pool. Comparing against a 600M-pool run would be invalid (trap 2).
REM  
REM   WHAT THIS CANNOT ANSWER
REM     Korean. The validation split of this pool is 0.0 percent Korean. P087 is
REM     the experiment that covers that side.
REM  
REM   COST: about 5.1h.   PLAN: test_plan/P088_*.md
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P088_stage1_tokens600m --note "[1/2] control - 300M tokens over the 1.2B pool"
python scripts\runlog.py --name P088_stage1_tokens600m -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 2289 --tokens 300M --pool-tokens 1200M --exact-cache --tag d12_cla2_r20_p12_t300
if errorlevel 1 echo [WARN] arm failed - continuing

python scripts\runlog.py --name P088_stage1_tokens600m --note "[2/2] treatment - 600M tokens over the same pool"
python scripts\runlog.py --name P088_stage1_tokens600m -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 4578 --tokens 300M --pool-tokens 1200M --exact-cache --tag d12_cla2_r20_p12_t600
if errorlevel 1 echo [WARN] arm failed - continuing


echo.
python scripts\runlog.py --name P088_stage1_tokens600m --note "=================================================================" "READ IN THIS ORDER" "1. t600 minus t300 with paired_eval. Ruler is the dense series, 0.0021." "2. neither arm is comparable to anything outside this batch. Same pool only." "3. residency does not change. Any gain here is free at deploy time." "4. this says nothing about Korean - see P087." "================================================================="

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
