@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P030_Stage6_norecur_tokps.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage5 measured two points, 20 and 28 visits, and both models differ in
REM     BOTH depth and visits. Fitting a line to two confounded points gives an
REM     intercept of 2.40 ms, which would be 417 tok/s at zero visits - obviously
REM     wrong. So the boundary of 18 visits rests on ONE clean point plus a model.
REM     This stage measures 12, 14 and 16 visits directly at fixed architecture.
REM
REM   PREREQUISITE: P062 Stage8 must have produced d14 and d16 without recursion.
REM     If it did not, arms 2 and 3 will skip and arm 1 still gives a second point.
REM
REM   READ IN THIS ORDER
REM     1. the printed visit count per model. 12, 14, 16, and 20 for the control.
REM     2. one thread tok/s against 15. That is the whole question.
REM     3. plot the four against visits. If they are collinear the visit-count
REM        model holds inside a family and the boundary of 18 is real.
REM     4. if they are NOT collinear there is a separate depth term, which matters
REM        more than the boundary itself. Say so plainly.
REM     5. the residency column is NOT the deployment number - see 014 s15.3.
REM
REM   NO TRAINING. COST: about 0.5h.   PLAN: test_plan/P030 Stage6
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P030_stage6_norecur_tokps --note "[1/2] the three no-recursion depths, one and four threads"
python scripts\runlog.py --name P030_stage6_norecur_tokps -- python scripts\bench_infer.py --models d12_cla2_norecur --preset m100s8 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] d12 no-recursion bench failed - continuing
python scripts\runlog.py --name P030_stage6_norecur_tokps -- python scripts\bench_infer.py --models d14_cla2_norecur --preset m100s10 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] d14 no-recursion bench failed - continuing
python scripts\runlog.py --name P030_stage6_norecur_tokps -- python scripts\bench_infer.py --models d16_cla2_norecur --preset m100s12 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] d16 no-recursion bench failed - continuing

python scripts\runlog.py --name P030_stage6_norecur_tokps --note "[2/2] the recursive control at 20 visits - same day, same machine"
python scripts\runlog.py --name P030_stage6_norecur_tokps -- python scripts\bench_infer.py --models d12_cla2_r20 --preset m100s8 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache --infer-repeat 2.0
if errorlevel 1 echo [WARN] control bench failed - continuing

python scripts\runlog.py --name P030_stage6_norecur_tokps --note "DONE. Four points at 12, 14, 16, 20 visits measured the same day. Do not mix these with numbers from another session - 7.5 percent drift."

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
