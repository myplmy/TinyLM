@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P016_Stage3_sparse34_dense.bat -- what does 3:4 cost on OUR winner?
REM ==========================================================================
REM
REM   WHY P016 IS OPEN AGAIN
REM     it was marked done in August. Result 008 measured the quality cost
REM     (g4_s34 +0.0364, g8_s34 +0.0606) and the 1.25 bpw storage number.
REM     Nobody ever asked what it buys in RESIDENCY, because the residency
REM     formula has no bpw term in it (trap 1). So "1.25 bpw" sat for three
REM     weeks without anyone knowing whether it meant storage or runtime.
REM
REM   2026-09-05 the packing went in
REM     lut.py now carries a real 3:4 format at 5 bits per 4 weights, exactly
REM     the entropy bound. Residency arithmetic on our two winners:
REM       d12_cla2_r20  ternary term 14.52 gives 11.34 MiB, saves 3.18, new 27.5
REM       d16_cla2_r20  ternary term 19.36 gives 15.12 MiB, saves 4.23, new 34.3
REM     At the result-008 cost of +0.0364 that is 0.01146 and 0.00860 nats per
REM     MiB, against our lever line of 0.00531. Dominated by 2.16x and 1.62x.
REM
REM   BUT THE COST NUMBER IS FROM A DIFFERENT WORLD
REM     result 008 measured a 20-layer TIED body with KD and mlp_group 4.
REM     Our winner is a 12-layer DENSE body with no KD. Not one condition is
REM     shared. On d16 the ratio is already down to 1.62x, so a cost of
REM     0.0225 or less puts 3:4 back inside the line. This arm measures it.
REM
REM   ONE ARM, BECAUSE THE CONTROL ALREADY EXISTS
REM     d12_cla2_r20 is the standard 600M-pool run. This arm changes exactly
REM     one flag, --sparse34, and keeps everything else byte-identical.
REM     Judge with paired_eval against d12_cla2_r20. Ruler: dense 0.0021.
REM
REM   PRE-REGISTERED VERDICT
REM     delta (lt)= +0.0225        inside the line, promote to REVIEW3 v2 plan A
REM     +0.0225 to +0.0364  grey, 40 MiB budget only
REM     (gt) +0.0364        more expensive on dense, close the axis for good
REM
REM   COST: about 1.8h.   PLAN: test_plan/P016 (Korean filename) Stage3
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

timeout /t 15 /nobreak

python scripts\runlog.py --name P016_stage3_sparse34_dense --note "[1/1] d12_cla2_r20 plus --sparse34, everything else identical"
python scripts\runlog.py --name P016_stage3_sparse34_dense -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --sparse34 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_s34
if errorlevel 1 echo [WARN] sparse34 arm failed - continuing

set TL_WB_TAG=d12_cla2_r20_s34
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

echo.
python scripts\runlog.py --name P016_stage3_sparse34_dense --note "=================================================================" "READ IN THIS ORDER" "1. json sparse34 must be true and bpw must be 1.25. If either is" "   missing the flag did not reach the quantiser and the run is void." "2. paired_eval against d12_cla2_r20. BOTH used the 600M pool, so" "   --tokens 600M is the correct eval cache, not the 300M default." "   The 300M val is inside the 600M train (result 075 section 6)." "3. compare the delta with 0.0225 and 0.0364. The verdict is already" "   written in the header - do not invent a new threshold now." "4. grad_max. Forcing 25 percent of weights to zero can destabilise." "5. this measures the COST. The saving (3.18 MiB) is arithmetic and" "   mem_runtime confirms it in Stage4, only if this arm passes." "================================================================="

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
