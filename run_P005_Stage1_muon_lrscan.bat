@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P005_Stage1_muon_lrscan.bat -- Muon, finally run at all
REM ==========================================================================
REM
REM   WHY THIS BATCH DID NOT EXIST BEFORE
REM     --optimizer muon went into the parser on 2026-09-03 and had run zero
REM     times. Auditing it on 2026-09-05 found three defects that would have
REM     made any comparison invalid, all now fixed:
REM       1 the LR schedule never reached the Muon optimiser. base_lrs was
REM         read off opt.param_groups only, so opt_muon kept a constant lr
REM         with no warmup and no wsd decay. The AdamW arm and the Muon arm
REM         would have been running different schedules.
REM       2 the AdamW side lost its weight-decay convention. Passing one
REM         params list drops the dense 0.1 / norm 0 / lrm 0.01 split.
REM       3 the json did not record optimizer at all, so afterwards you could
REM         not tell a Muon run from an AdamW one.
REM     A smoke arm [19b] sm_muon was added at the same time - trap 37.
REM
REM   THE NEW FLAG
REM     --muon-lr-mult, default 1.0 which is the old behaviour. Muon's usual
REM     lr is an order of magnitude above AdamW's (reference impl 2e-2 versus
REM     our 1e-3) and the old code simply handed it the AdamW lr. Running
REM     once at that value and declaring Muon a loser would be measuring the
REM     wrong thing.
REM
REM   DESIGN - 763 steps, four arms, one control inside the batch
REM     763 x 131,072 = 100.0M tokens. That is a third of the standard run
REM     and it is deliberately ABOVE the 500-step full-train threshold,
REM     because this arm has to be read for quality, not just speed.
REM     Compare only within this batch. Never against a 2289-step run.
REM
REM   BODY: the 32 MiB winner d12_cla2_r20 - dense, cla_group 2, recursion R2.
REM
REM   VRAM: same shape as P088 Stage1, measured 9.72 GB reserved. Muon adds
REM   one momentum buffer per matrix, which is smaller than AdamW's two
REM   moments, so the Muon arms should sit at or below the control.
REM
REM   COST: about 2.6h.   PLAN: test_plan/P005 (Korean filename) Stage1
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

timeout /t 15 /nobreak

python scripts\runlog.py --name P005_stage1_muon_lrscan --note "[1/4] control - AdamW, 763 steps"
python scripts\runlog.py --name P005_stage1_muon_lrscan -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 763 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_s763_adamw
if errorlevel 1 echo [WARN] adamw control failed - continuing

python scripts\runlog.py --name P005_stage1_muon_lrscan --note "[2/4] Muon, lr multiplier 1 - the old default"
python scripts\runlog.py --name P005_stage1_muon_lrscan -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 763 --tokens 300M --pool-tokens 600M --exact-cache --optimizer muon --muon-lr-mult 1 --tag d12_cla2_r20_s763_muon1
if errorlevel 1 echo [WARN] muon1 failed - continuing

python scripts\runlog.py --name P005_stage1_muon_lrscan --note "[3/4] Muon, lr multiplier 5"
python scripts\runlog.py --name P005_stage1_muon_lrscan -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 763 --tokens 300M --pool-tokens 600M --exact-cache --optimizer muon --muon-lr-mult 5 --tag d12_cla2_r20_s763_muon5
if errorlevel 1 echo [WARN] muon5 failed - continuing

python scripts\runlog.py --name P005_stage1_muon_lrscan --note "[4/4] Muon, lr multiplier 15 - close to the reference 2e-2"
python scripts\runlog.py --name P005_stage1_muon_lrscan -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 763 --tokens 300M --pool-tokens 600M --exact-cache --optimizer muon --muon-lr-mult 15 --tag d12_cla2_r20_s763_muon15
if errorlevel 1 echo [WARN] muon15 failed - continuing

set TL_WB_TAG=d12_cla2_r20_s763_adamw
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=d12_cla2_r20_s763_muon1
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=d12_cla2_r20_s763_muon5
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=d12_cla2_r20_s763_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

echo.
python scripts\runlog.py --name P005_stage1_muon_lrscan --note "=================================================================" "READ IN THIS ORDER" "1. grad_max and n_skip FIRST on every Muon arm. If a run diverged the" "   lr multiplier was too big and its loss says nothing about Muon." "2. json optimizer, muon_lr_mult, muon_matrices must be present. If any" "   is missing the fix did not take and the arm is unattributable." "3. best Muon arm minus the AdamW control. Ruler is dense 0.0021." "4. compare only inside this batch. 763 steps is not 2289 steps." "5. if all three Muon arms lose, that is NOT a rejection of Muon - it" "   may be that the lr band is outside 1x to 15x. Say so." "6. ms/step. Newton-Schulz 5 costs compute the control does not pay." "================================================================="

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
