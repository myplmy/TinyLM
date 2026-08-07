@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P042_stage0_gate.bat -- [P042] stage 0. Is the teacher inference mode
REM                              BIT IDENTICAL? Cheap gate before any long run.
REM  Plan: test_plan\P042
REM =============================================================================
REM
REM ***A FEW MINUTES. TINY PRESET. RUN THIS BEFORE STAGE 1.***
REM
REM WHY - the teacher does not learn, but it runs as if it did
REM   forward() calls refresh_quant() every step because the STUDENT's latent
REM   weights change every step. The TEACHER's do not. So the teacher pays for
REM   a recomputation it never needs, and keeps an fp32 latent copy - about
REM   472.5 MB for a dense teacher.
REM   --kd-teacher-infer (new, default OFF) attaches freeze_quant() and
REM   drop_latent(), both already implemented and already gated for inference.
REM
REM ***WHAT THIS STAGE CHECKS - AND ONLY THIS***
REM   The teacher's logits must be ***BIT IDENTICAL*** with the flag on and off.
REM   freeze_quant reuses the same values; drop_latent was verified at logit
REM   equality 0.000e+00 in result 016 section 9. If the losses differ AT ALL,
REM   it is an implementation bug, not a tradeoff - stop and report.
REM
REM   Compare the step 0 and step 15 loss lines between the two runs below.
REM   Same seed, same data, same everything except the one flag.
REM
REM ***DO NOT read speed from this.*** Tiny preset, 30 steps, synthetic data.
REM   Speed is stage 1 and it needs sole occupancy plus 5 minutes idle.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
set TL_OUTDIR=smoketest_logs

echo =============================================================
echo [P042-0] teacher inference mode : BIT IDENTITY gate (tiny, minutes)
echo =============================================================
python scripts\runlog.py --name P042_stage0 --note "[P042 stage 0] teacher inference mode : bit identity gate"

echo.
echo [0/3] tiny dense parent (needed by --init-from and --kd)
python scripts\runlog.py --name P042_stage0 --note "[0/3] tiny dense parent"
python scripts\runlog.py --name P042_stage0 -- python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15
if errorlevel 1 goto PARENTBAD

echo.
echo [1/3] control - teacher inference mode OFF (previous behaviour)
python scripts\runlog.py --name P042_stage0 --note "[1/3] CONTROL : --kd-teacher-infer OFF"
python scripts\runlog.py --name P042_stage0 -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --kd --init-from --mlp-group 4 --tag p42_off
if errorlevel 1 echo [WARN] control failed - continuing

echo.
echo [2/3] treatment - teacher inference mode ON
python scripts\runlog.py --name P042_stage0 --note "[2/3] TREATMENT : --kd-teacher-infer ON"
python scripts\runlog.py --name P042_stage0 -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --kd --init-from --mlp-group 4 --kd-teacher-infer --tag p42_on
if errorlevel 1 echo [WARN] treatment failed

python scripts\runlog.py --name P042_stage0 --note "=================================================================" "WHAT TO RECORD" "  1. ***the step 0 and step 15 loss lines from BOTH runs.***" "     They must match to every printed digit. Same seed, same data," "     one flag apart." "  2. the two [kd] lines in run [2/3] confirming freeze_quant + drop_latent" "     actually fired. If they are absent the flag did not take." "" "HOW TO READ IT" "  identical  -^> gate G0 PASSED. Stage 1 (speed and VRAM, about 40 min," "                sole occupancy) is safe to run." "  different  -^> ***IMPLEMENTATION BUG, not a tradeoff.*** freeze_quant is" "                supposed to reuse the same values. Report the first step" "                where they diverge and stop." "" "LIMITS: tiny preset on synthetic data. ***The losses themselves mean" "  nothing*** - only their EQUALITY does. Speed and VRAM are stage 1." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:PARENTBAD
echo.
echo [STOP] tiny dense parent failed. Nothing to distil from.
if not defined TL_NOPAUSE pause
exit /b 4

:BADROOT
echo.
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
