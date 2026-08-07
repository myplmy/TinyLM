@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P045_g16_ceiling.bat -- [P045] tying ceiling g16 : closes the tying axis
REM  Plan: test_plan\P045 (tying ceiling g16)
REM =============================================================================
REM
REM PRECONDITION: none. --mlp-group has existed since v6.
REM
REM ***LONG UNATTENDED RUN. START IT AND WALK AWAY.*** About 3.5 GPU hours for one run.
REM
REM WHY - AND WHY EXPECTATIONS ARE DELIBERATELY LOW
REM   n_middle is 16, so g16 is the STRUCTURAL CEILING (the assert requires
REM   n_middle divides evenly by mlp_group, giving g in 1,2,4,8,16). Measuring it CLOSES
REM   the tying sweep.
REM   But the gain is small: unique middle MLPs go 2 -^> 1 (prelude 2 and coda 2
REM   stay independent), so residency 87.1 -^> 82.4 MB = only -5.3 percent, and
REM   packed 13.12 -^> 12.16 MB (2.07x -^> 2.24x).
REM   P046 buys -18.8 percent for the same 3.5 hours. This run is about CLOSING
REM   AN AXIS, not about the size of the prize.
REM   Result 027 just closed per-layer conditioning (FiLM +0.0003), so tying
REM   strength is the remaining architecture knob.
REM
REM ***EXPECTATION.***
REM   +0.01 to +0.03, i.e. right on the resolution boundary. The old measurement
REM   was t_kd_g16 3.8420 vs t_kd_g8 3.8292 = +0.0128, but that was the 300M pool
REM   with full KD; k4 is slightly weaker than full KD.
REM   Because it sits on the boundary, paired_eval (SE 0.0004) is REQUIRED - the
REM   averaged val cannot decide this.
REM   Note also that --init-from averages mlp_group layers, so at g16 the parent
REM   init averages ALL 16 middle layers. That is mixed into the g effect.
REM
REM ***THE CONTROL IS NOT RE-RUN.*** mC_wsd from result 024 is the same configuration except --mlp-group.
REM   Condition matching is therefore critical: sched=wsd / anneal_end=0.80 /
REM   kd_every=4 / pool 600M exact / seed 1337.
REM   ***CHECK THOSE IN THE LOG HEADER BEFORE TRUSTING ANY DELTA.***
REM
REM MEASUREMENT: quality only. Wall clock is NOT comparable to the control
REM   (different session). Read 'final', never 'best' (result 015 flipped a sign).
REM   grad_max comes from the json, not the printed 10-step sample.
REM
REM ERRORLEVEL POLICY: training is the prerequisite, so it stops the batch.
REM =============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL

echo =============================================================
echo [P045] tying ceiling g16 : closes the tying axis
echo =============================================================
python scripts\runlog.py --name P045_mC_g16 --note "[P045] tying ceiling g16 : closes the tying axis"

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo =============================================================
echo [1/2] train
echo =============================================================
python scripts\runlog.py --name P045_mC_g16 --note "[1/2] train"
python scripts\runlog.py --name P045_mC_g16 -- python run100m.py train --preset m100R1c --arch tied --mlp-group 16 --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --tag mC_g16
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [2/2] paired comparison against mC_wsd
echo =============================================================
python scripts\runlog.py --name P045_mC_g16 --note "[2/2] paired comparison against mC_wsd"
python scripts\runlog.py --name P045_mC_g16 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_g16
if errorlevel 1 echo [WARN] paired_eval failed - checkpoint is on disk, re-run this step alone

python scripts\runlog.py --name P045_mC_g16 --note "=================================================================" "WHAT TO RECORD" "  1. final val, NOT best." "  2. the paired_eval delta and t value against mC_wsd." "  3. grad_max from the json." "  4. the report() block - the ternary/embedding parameter counts." "  5. the header conditions. If any differ from mC_wsd the delta is INVALID." "" "HOW TO READ IT" "  delta under +0.024" "      -^> ACCEPT for review. packed 2.07x -^> 2.24x, residency -5.3 percent." "  +0.024 to +0.05" "      -^> only for memory-constrained deployment targets." "  above +0.05" "      -^> g8 IS the ceiling. Close the tying axis - that is a real answer." "  ***ALSO CHECK*** the header says MLP g=16 and report() shows ternary 50.1M." "  If it still says g=8 the override did not take and the run is worthless." "" "LIMITS: one seed / g16 only (it is already the ceiling) / parent init averages" "  all 16 middle layers, which is mixed into the g effect / prelude and coda stay" "  independent and are NOT touched - result 002 called that the single largest" "  gain / the -5.3 percent is COMPUTED." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:BADKWARGS
echo.
echo [STOP] cli.py passes a keyword its target function does not accept.
exit /b 6

:NOCTRL
echo.
echo [STOP] control runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt is missing.
exit /b 5

:TRAINBAD
echo.
echo [STOP] training failed. Nothing to compare.
exit /b 4

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
exit /b 9
