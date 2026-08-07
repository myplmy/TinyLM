@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P042_stage1_speed_vram.bat -- [P042] stage 1. What does the teacher
REM                                    inference mode actually buy in speed and VRAM?
REM  Plan: test_plan\P042 / Gate result: test_result\034
REM =============================================================================
REM
REM PRECONDITION: stage 0 PASSED (result 034 - bit identity confirmed).
REM   Do not run this if the losses in stage 0 differed. That would be a bug,
REM   and measuring the speed of a bug is worse than not measuring.
REM
REM ***ABOUT 60 MINUTES. RUN IT ALONE.***
REM   Close other GPU work. Result 016 section 12.5 requires sole occupancy and
REM   about 5 minutes of idle before a speed measurement. The batch waits 300 s
REM   at the start and 120 s between runs, so you only need to leave it alone.
REM
REM WHY THREE RUNS AND NOT TWO
REM   Result 034 section 3.1 already showed the trap: in the tiny gate the OFF
REM   arm ran FIRST and looked 20 percent slower, and that number is worthless
REM   because ordering and thermals were confounded with the treatment.
REM   So here the order is  OFF -^> ON -^> OFF again.
REM   ***The two OFF runs bracket the ON run.*** If they differ from each other
REM   by more than the OFF-to-ON gap, the measurement is drift, not effect.
REM   Result 016 section 15 learned exactly this - a baseline inside the same
REM   log is what made the ratio survive a 12 to 17 percent baseline shift.
REM
REM ***PREDICTIONS - WRITTEN BEFORE THE RUN (plan P042 section 3)***
REM   P1 the teacher forward barely speeds up, minus 0 to 5 percent end to end.
REM      --kd-every 4 means the teacher runs on one step in four, so the ceiling
REM      is structurally low.
REM      ***BUT*** result 034 section 3.1 saw minus 20.6 percent on the tiny
REM      preset. That is NOT evidence - three confounds - but it does mean
REM      ***P1 may well be rejected here, and that is a real finding.***
REM   P2 VRAM drops by about 0.4 to 0.5 GB. Teacher latent is 123.86M x 4B
REM      = 472.5 MiB. In the tiny gate the drop was about 10 MB against a
REM      12.6 MiB latent - right order of magnitude.
REM
REM ***WHAT NOT TO READ***
REM   ***Do NOT read val_loss.*** 250 steps sits in the unstable band
REM   (CLAUDE.md: grad_max 10 to 35). Quality is stage 3 only.
REM   ms/step in the log is a RUNNING AVERAGE. Convert with
REM       (running_avg x N - step0) / (N - 1)
REM
REM ERRORLEVEL POLICY: the three runs are independent measurements. One failing
REM   still leaves the others readable, so WARN and continue.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

echo =============================================================
echo [P042-1] teacher inference mode : speed and VRAM (about 60 min, run alone)
echo =============================================================
python scripts\runlog.py --name P042_stage1 --note "[P042 stage 1] teacher inference mode : speed and VRAM. Order OFF - ON - OFF."

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo [idle] waiting 300 s so the GPU settles (result 016 section 12.5)
timeout /t 300 /nobreak

echo.
echo =============================================================
echo [1/3] CONTROL A - teacher inference mode OFF
echo =============================================================
python scripts\runlog.py --name P042_stage1 --note "[1/3] CONTROL A : --kd-teacher-infer OFF"
python scripts\runlog.py --name P042_stage1 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --tag mC_tinf_off
if errorlevel 1 echo [WARN] control A failed - continuing

echo.
echo [idle] waiting 120 s
timeout /t 120 /nobreak

echo.
echo =============================================================
echo [2/3] TREATMENT - teacher inference mode ON
echo =============================================================
python scripts\runlog.py --name P042_stage1 --note "[2/3] TREATMENT : --kd-teacher-infer ON"
python scripts\runlog.py --name P042_stage1 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --kd-teacher-infer --tag mC_tinf_on
if errorlevel 1 echo [WARN] treatment failed - continuing

echo.
echo [idle] waiting 120 s
timeout /t 120 /nobreak

echo.
echo =============================================================
echo [3/3] CONTROL B - OFF again, to measure drift
echo =============================================================
python scripts\runlog.py --name P042_stage1 --note "[3/3] CONTROL B : --kd-teacher-infer OFF again (drift check)"
python scripts\runlog.py --name P042_stage1 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --tag mC_tinf_off2
if errorlevel 1 echo [WARN] control B failed

python scripts\runlog.py --name P042_stage1 --note "=================================================================" "WHAT TO RECORD" "  1. steady state ms/step for all three runs." "     (running_avg x N - step0) / (N - 1)   with N = 250" "  2. peak reserved VRAM from the [vram] line of each run." "  3. the [kd] teacher inference mode lines in run [2/3] only." "  4. grad_max from runs\\logs\\*.json - NOT the printed bar g." "" "HOW TO READ IT" "  drift  = OFF_B - OFF_A. ***Compute this FIRST.***" "  effect = ON - mean(OFF_A, OFF_B)" "  If abs(drift) is comparable to abs(effect), the measurement is thermal" "  and the honest answer is 'below the noise of this rig', not a number." "" "  VRAM: expect about 0.4 to 0.5 GB less on ON. If it is much less than that," "  PyTorch was already sharing the storage somewhere." "" "***DO NOT READ val_loss.*** 250 steps is speed only (result 007)." "  Quality is stage 3, and only if stage 2 opens --no-ckpt." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:BADKWARGS
echo.
echo [STOP] cli.py passes a keyword its target function does not accept.
if not defined TL_NOPAUSE pause
exit /b 6

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
