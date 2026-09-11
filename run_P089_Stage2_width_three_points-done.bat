@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P089_Stage2_width_three_points.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     The width axis has memory and speed numbers and ZERO quality runs.
REM     w512_d28 fits 31.1 MiB and reaches 15.55 tok/s - the same 32 MiB budget
REM     with twice the layers - and we have never measured what it costs.
REM     Stage1 built the narrow parent. This stage spends it.
REM
REM   THE POINT IS THE DECOMPOSITION, NOT THE WINNER
REM     Arm A is dim 512 at the SAME depth 14 as the baseline. It only uses
REM     19.9 MiB, and that is deliberate. A is not a candidate, it is the term
REM     that isolates the cost of narrowing.
REM       width cost    = val(A) - val(baseline d14_cla2_norecur_muon15)
REM       depth recovery= val(A) - val(B)
REM       net gain      = val(baseline) - val(B)
REM     Read all three. A single net number hides which half moved.
REM
REM   PRE-REGISTERED (plan section 5)
REM     P2 width cost   +0.05 to +0.12   under 0.02 means width is nearly free
REM     P3 recovery is larger than the cost, so net gain is negative
REM     P4 net gain     -0.05 to -0.13
REM     Adopt at net gain of -0.02 or better. Hold between -0.02 and 0.
REM     Reject above 0. The ruler is the no-recursion 0.0024.
REM
REM   ARM C (dim 384) IS NOT HERE - AND THAT IS NOT AN OVERSIGHT
REM     init_utils transplants weights of the SAME dim. The parent we have is
REM     dim 512, so a dim 384 child cannot inherit it, and running C from
REM     scratch would confound width with initialisation - exactly the trap
REM     section 3 of the plan warns about. C needs its own parent, about 2.0h.
REM     That is a separate decision, not something to smuggle into this batch.
REM
REM   WATCH grad_max AND n_skip. Thin layers are the risk (plan section 6.3).
REM     Read the json field, not the printed gradient sample (trap 4).
REM
REM   PREREQUISITE: w512_d20_parent, made by run_P089_Stage1_narrow_parent.
REM   COST: about 4.6h, two training runs.   PLAN: test_plan/P089 stage 2
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P089_stage2_width_three_points --note "[1/3] arm A - dim 512 at depth 14. The pure cost of narrowing. NOT a candidate."
timeout /t 15 /nobreak
python scripts\runlog.py --name P089_stage2_width_three_points -- python run100m.py train --preset m100w512s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from-tag w512_d20_parent --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag w512_d14_muon15
if errorlevel 1 echo [WARN] arm A failed - continuing
set TL_WB_TAG=w512_d14_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P089_stage2_width_three_points --note "[2/3] arm B - dim 512 at depth 28. Same 32 MiB budget as the baseline, twice the layers."
timeout /t 15 /nobreak
python scripts\runlog.py --name P089_stage2_width_three_points -- python run100m.py train --preset m100w512s24 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from-tag w512_d20_parent --depth-init role --cla-group 2 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag w512_d28_muon15
if errorlevel 1 echo [WARN] arm B failed - continuing
set TL_WB_TAG=w512_d28_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P089_stage2_width_three_points --note "[3/3] paired_eval - the verdict is paired, not the training log (rule R10)"
timeout /t 15 /nobreak
python scripts\runlog.py --name P089_stage2_width_three_points -- python scripts\paired_eval.py --preset m100w512s24 --data ko-en --tokens 600M --ckpt-tokens 300M --models w512_d14_muon15 w512_d28_muon15 d14_cla2_norecur_muon15
if errorlevel 1 echo [WARN] paired_eval failed - continuing

python scripts\runlog.py --name P089_stage2_width_three_points --note "DONE. Read three numbers: width cost, depth recovery, net gain. Ruler 0.0024."

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
