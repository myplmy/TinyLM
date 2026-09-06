@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P005_Stage2_muon_main.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage1b closed the bracket: x15 is the best of 15, 30, 45 and the middle
REM     of 5, 15, 30. The multiplier is settled. What is NOT settled is whether
REM     the 763-step gain of -0.02922 survives to the 2289-step main run.
REM
REM   THREE ARMS
REM     1. Muon x15 at 2289 steps on d12_cla2_r20        the question
REM     2. AdamW control at 2289 steps, same tag scheme  the reference
REM     3. Muon x15 on the speed-compliant d16 no-recursion shape
REM
REM     Arm 2 exists even though d12_cla2_r20 is already an AdamW run at these
REM     settings, because that run did not pass --optimizer at all. Same default,
REM     but R08 says compare matched conditions, and one flag is cheap insurance.
REM
REM     Arm 3 asks whether the optimiser gain transfers across architecture. If
REM     Muon only helps the recursive shape it is not useful to us - the recursive
REM     shapes miss the speed floor.
REM
REM   PREREQUISITE for arm 3: P062 Stage8 must have run. If not it skips.
REM
REM   READ IN THIS ORDER
REM     1. grad_max. At x15 the 763-step value was 0.7721. Three times the steps
REM        is not three times the gradient, but watch for anything above 3.
REM     2. n_skip must be 0. Any skip and the loss number is not comparable.
REM     3. arm 1 minus arm 2. The 763-step gap was -0.02922. Same sign is the
REM        question; the same size is not expected.
REM     4. do NOT compare these with the 763-step arms. Warmup fraction differs.
REM
REM   COST: about 5.2h.   PLAN: test_plan/P005 Stage2
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005_stage2_muon_main --note "[1/3] Muon x15 main run - 2289 steps"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage2_muon_main -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --optimizer muon --muon-lr-mult 15 --tag d12_cla2_r20_muon15
if errorlevel 1 echo [WARN] Muon main run failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage2_muon_main --note "[2/3] AdamW control at the same 2289 steps with the flag made explicit"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage2_muon_main -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --optimizer adamw --tag d12_cla2_r20_adamw
if errorlevel 1 echo [WARN] AdamW control failed - continuing
set TL_WB_TAG=d12_cla2_r20_adamw
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage2_muon_main --note "[3/3] does the optimiser gain transfer to the speed-compliant shape"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage2_muon_main -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --optimizer muon --muon-lr-mult 15 --tag d16_cla2_norecur_muon15
if errorlevel 1 echo [WARN] Muon on the no-recursion shape failed - continuing
set TL_WB_TAG=d16_cla2_norecur_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage2_muon_main --note "[4/4] optimiser x tokens on the shipping shape - 600M tokens, pool 1200M"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage2_muon_main -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --seed 1337 --steps 4578 --tokens 600M --pool-tokens 1200M --exact-cache --optimizer muon --muon-lr-mult 15 --tag d16_cla2_norecur_muon15_t600
if errorlevel 1 echo [WARN] Muon at 600M tokens failed - continuing
set TL_WB_TAG=d16_cla2_norecur_muon15_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage2_muon_main --note "DONE. Arm 1 minus arm 2 is the headline. Arm 3 minus d16_cla2_norecur (P062 Stage8) answers transfer. Arm 4 minus d16_cla2_norecur_t600 (P062 Stage9) answers whether the optimiser gain and the token gain add up or overlap."

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
