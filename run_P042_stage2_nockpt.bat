@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P042_stage2_nockpt.bat -- [P042] stage 2. Does freeing the teacher
REM                                latent open --no-ckpt for tied + KD?
REM  Plan: test_plan\P042 section 5 / Gate result: test_result\034
REM =============================================================================
REM
REM PRECONDITION: stage 0 PASSED (result 034) and stage 1 has been RUN.
REM   Stage 1 gives the VRAM number this stage is trying to spend. If you run
REM   this first you will not know whether an OOM means 'not enough' or
REM   'the flag did nothing'.
REM
REM ***ABOUT 20 MINUTES. 250 STEPS. ONE RUN.***
REM
REM WHAT IS AT STAKE
REM   --no-ckpt (gradient checkpointing off) is minus 17.3 percent, the single
REM   largest engineering lever in this repo. It is BANNED on tied + KD with a
REM   dense teacher because result 007 recorded 15.7 GB and the spill wall is
REM   13 to 14 GB. Freeing the teacher latent returns 472.5 MiB.
REM
REM ***THE ARITHMETIC, WRITTEN DOWN BEFORE THE RUN***
REM   15.7 GB - 0.47 GB = 15.2 GB.  ***THAT IS STILL ABOVE THE WALL.***
REM   So the honest prediction is that this OOMs. Plan P042 section 3 calls P3
REM   'the largest uncertainty' for exactly this reason.
REM
REM   ***AN OOM HERE IS THE ANSWER, NOT A FAILURE.*** It costs 20 minutes to
REM   learn it instead of five hours into a real run. If it OOMs, the plan goes
REM   to P042 section 7 (teacher int8: another ~350 MB, and CUDA int8 unpack is
REM   only minus 12 to 15 percent per result 016 section 12.3, paid on one step
REM   in four).
REM
REM   ***ONE REASON IT MIGHT SURVIVE***: result 033 measured tied VRAM at
REM   5.06 GB reserved, minus 35.3 percent against dense. The 15.7 GB figure in
REM   EXPERIMENT_BASELINES section 5 is OLD and came from a different config.
REM   ***It may simply be stale.*** That is the second thing this run tests.
REM
REM NOTE: lint_bat will warn about --no-ckpt plus KD with a dense teacher.
REM   That warning is CORRECT and it is the point of this experiment. 250 steps
REM   is the cheapest possible way to find out.
REM
REM ***DO NOT READ val_loss.*** 250 steps. This run answers one yes-or-no
REM   question: does it complete without OOM.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

echo =============================================================
echo [P042-2] does --no-ckpt open for tied + KD  (about 20 min)
echo =============================================================
python scripts\runlog.py --name P042_stage2 --note "[P042 stage 2] --no-ckpt on tied + KD + dense teacher, with teacher latent freed. An OOM is the answer, not a failure."

echo.
echo [idle] waiting 120 s so the GPU settles
timeout /t 120 /nobreak

echo.
echo =============================================================
echo [1/1] teacher inference mode ON  plus  --no-ckpt
echo =============================================================
python scripts\runlog.py --name P042_stage2 --note "[1/1] --kd-teacher-infer ON plus --no-ckpt"
python scripts\runlog.py --name P042_stage2 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --kd-teacher-infer --no-ckpt --tag mC_tinf_nockpt
if errorlevel 1 echo [WARN] the run did not finish - read the tail of the log, an OOM here is a RESULT

python scripts\runlog.py --name P042_stage2 --note "=================================================================" "WHAT TO RECORD" "  1. did it finish 250 steps, yes or no." "  2. peak reserved VRAM from the [vram] line - ***record it either way***," "     including the allocation size in the OOM message if it died." "  3. steady state ms/step, to compare against stage 1 run [2/3]." "  4. grad_max from the json." "" "HOW TO READ IT" "  finished  -^> ***--no-ckpt IS OPEN for tied + KD.*** That is minus 17.3" "               percent on every KD run from now on, and it means the" "               15.7 GB figure in EXPERIMENT_BASELINES section 5 was stale." "               Revise section 5 - but ONLY after this run, per P042 preflight." "  OOM       -^> the expected outcome. Record the peak and the allocation size," "               then go to P042 section 7 (teacher int8). ***This is a cheap" "               negative, not a failed experiment.***" "" "LIMITS: 250 steps. A 2289 step run allocates the same peak per step, so" "  surviving 250 steps is strong evidence but not proof - fragmentation" "  accumulates. If it passes, the first long run still needs watching." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:NOPARENT
echo.
echo [STOP] parent runs\ckpt\m100_ko-en_300M_dense.pt is missing. KD needs it.
if not defined TL_NOPAUSE pause
exit /b 5

:BADROOT
echo.
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
