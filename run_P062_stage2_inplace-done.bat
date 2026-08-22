@echo off
REM =============================================================================
REM  P062 stage 2  -  the training pair of inference --repeat-where even
REM                   1 training run plus paired eval, about 2.8 hours
REM
REM  WHY THIS EXISTS  (2026-08-22, the user was right)
REM    The user asked whether P062 trained front / back / even SEPARATELY, or
REM    only trained R=2 and varied where at inference. The second one.
REM    Reading the code:
REM        _repeat_schedule (TRAINING) reads only repeat_mode
REM        repeat_where appears ONLY in the inference branch of visit_schedule
REM    So with m=16 and R=2:
REM        training  uniform  gives  mid + mid
REM        inference front    gives  mid + mid          identical, extra == m
REM        inference back     gives  mid + mid          identical
REM        inference even     gives  each layer twice in place   NEVER TRAINED
REM
REM    !! That means result 047 stage 0 "even +0.0992" does not say even is bad.
REM       It says we evaluated a function nobody trained. Trap 39, again.
REM
REM  WHAT --repeat-mode inplace DOES
REM    It is the training counterpart of inference where=even. Same visit list.
REM    Default is uniform, so every existing run is untouched and bit identical.
REM
REM  PREDICTIONS, fixed in advance
REM    T1  mC_r20in_nokd evaluated at even lands within 0.010 of mC_r20_nokd
REM        evaluated at front. If so, the order axis is closed and P070 does not
REM        start.
REM    T2  the +0.0992 gap collapses to under 0.010 once training matches
REM    T3  memory identical - only the schedule changed
REM    T4  wall clock identical - same number of layer visits
REM
REM  !! PREREQUISITE  run_P065_stage2_nockpt_vram.bat FIRST
REM    This run does NOT use --no-ckpt even though the 2026-08-22 rule says
REM    no-KD should default to it. Reason: recursion VRAM with --no-ckpt has
REM    never been measured, the estimate is 12.6 to 14 GiB and the spill wall is
REM    13 to 14. P065 stage 2 measures it in 15 minutes. If that probe passes,
REM    add --no-ckpt here and take the 20 percent.
REM
REM  !! EVALUATION MUST USE --match-train-repeat
REM    Without it paired_eval evaluates this checkpoint at R=1 and the number is
REM    meaningless. The flag reads train_repeat and repeat_mode off each
REM    checkpoint and maps inplace to even, uniform to front.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P062_stage2_inplace --note "=============================================================================" "P062 stage 2   --repeat-mode inplace   the training pair of where=even" "repeat_where never entered the training path. even was never trained." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P062_stage2_inplace --note "[1/3] mC_r20in_nokd - one flag different from mC_r20_nokd (uniform to inplace)"
python scripts\runlog.py --name P062_stage2_inplace -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --train-repeat 2.0 --repeat-mode inplace --init-from --tag mC_r20in_nokd
if errorlevel 1 echo [WARN] mC_r20in_nokd failed - continuing

echo.
python scripts\runlog.py --name P062_stage2_inplace --note "[wandb] push this run"
set TL_WB_TAG=mC_r20in_nokd
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P062_stage2_inplace --note "[2/3] paired full-val - EACH model at its own trained function (--match-train-repeat)"
python scripts\runlog.py --name P062_stage2_inplace -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20_nokd mC_r20in_nokd mC_initonly --match-train-repeat
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P062_stage2_inplace --note "[3/3] control - the SAME checkpoints forced onto the wrong schedule, to size trap 39"
python scripts\runlog.py --name P062_stage2_inplace -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20_nokd mC_r20in_nokd --infer-repeat 2.0 --repeat-where even
if errorlevel 1 echo [WARN] control eval failed - continuing

echo.
python scripts\runlog.py --name P062_stage2_inplace --note "=============================================================================" "READ IN THIS ORDER" "1. json repeat_mode must read inplace. If it reads uniform the flag did not" "   land and this run is a reseed of mC_r20_nokd (trap 37)." "2. val minus train_ce. Baselines run about -0.004. Over 0.3 means training" "   and evaluation ran different schedules (result 043 s14)." "3. step [2/3] is the real answer. Ruler is 2 sigma = 0.0034 (no-KD)." "4. step [3/3] sizes how much of the old +0.0992 was pure schedule mismatch." "IF T1 HOLDS (within 0.010)  the order axis is closed and P070 does not start." "IF IT DOES NOT  order is a real axis and P070 becomes worth its 50 lines." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
