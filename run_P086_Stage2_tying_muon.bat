@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P086_Stage2_tying_muon.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Every tying measurement we own was made with AdamW. There are 98
REM     full-train runs with mlp_group above 1 and not one of them used Muon.
REM
REM     The mechanism is concrete. A tied matrix receives the SUM of the
REM     gradients of the g layers that share it. Muon orthogonalises that sum.
REM     Orthogonalising a sum of g gradients is not the same operation as
REM     orthogonalising one layer's gradient, and nothing tells us in advance
REM     which way it goes.
REM
REM     This gates the fifth review. If Muon becomes the default optimizer,
REM     every tying verdict gets re-graded on top of it, so we measure one
REM     point BEFORE promoting rather than after.
REM
REM   READ IN THIS ORDER
REM     1. the Muon gain on the tied body. Dense bodies gave -0.036 to -0.044
REM        in four out of four. Same band means the price table stands.
REM     2. then the gap d16_g4_muon15 minus d16_cla2_norecur_muon15, against
REM        the AdamW gap of +0.07954. Cross-family ruler is 0.0025.
REM     3. grad_max and n_skip. A tied matrix with a summed gradient is the
REM        most likely place for Muon to become unstable. n_skip must be 0.
REM
REM   PREREQUISITE: none - d16_g4 and d16_cla2_norecur_muon15 both exist.
REM   COST: about 1.4h, one training run.   PLAN: test_plan/P086 Stage2
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P086_stage2_tying_muon --note "[1/2] tied body d16 g4 with Muon x15 - the axis has never met this optimizer"
python scripts\runlog.py --name P086_stage2_tying_muon -- python run100m.py train --preset m100s12 --arch tied --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --mlp-group 4 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_g4_muon15
if errorlevel 1 echo [WARN] tied muon arm failed - continuing
set TL_WB_TAG=d16_g4_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P086_stage2_tying_muon --note "[2/2] paired judgement against the AdamW tied twin and the dense Muon twin"
python scripts\runlog.py --name P086_stage2_tying_muon -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 600M --ckpt-tokens 300M --models d16_g4 d16_g4_muon15 d16_cla2_norecur d16_cla2_norecur_muon15
if errorlevel 1 echo [WARN] paired judgement failed - continuing

python scripts\runlog.py --name P086_stage2_tying_muon --note "DONE. Read the Muon gain first, the family gap second. This does not adopt mlp_group."

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
