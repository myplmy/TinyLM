@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P030_stage4_layerscaling.bat  --  P030 STAGE 4 : is decode speed set by
REM         PARAMETER COUNT or by LAYER COUNT (kernel launches)?
REM  Plan: test_plan\P030_...md   Prior: result 016 section 10.4
REM =============================================================================
REM
REM WHERE THIS QUESTION CAME FROM
REM   Result 016 section 10.4 noticed something that does not fit. With int8
REM   storage the three models run at 11.26 / 11.72 / 11.81 tok/s - within 5
REM   percent of each other - even though p6d has 2.26x the parameters of mC.
REM   At stage 2 the spread was already only 1.19x for a 2.26x parameter gap.
REM
REM   Hypothesis: at batch 1 the per-token GEMM is so small that PYTHON AND
REM   KERNEL LAUNCH overhead dominates, and that scales with the number of LAYERS
REM   (all three models have 20), not with parameters.
REM
REM WHY IT MATTERS MORE THAN IT SOUNDS
REM   If true, P034 stage 4 (the 5-bit packing kernel, roadmap R8) buys MEMORY but
REM   NOT SPEED - reading packed weights does not reduce the launch count. R8 is
REM   the largest remaining piece of work and the only surviving argument for
REM   candidate mA. Pricing it correctly before starting is worth a few minutes.
REM
REM THE DESIGN - one axis moves, and it is the one we never moved before
REM   --infer-repeat changes how many times the middle block is traversed. Layer
REM   passes go 12 / 16 / 20 / 24 / 28 / 36 while PARAMETERS, MEMORY and the
REM   weights themselves stay EXACTLY the same. P031 already used this flag but
REM   only recorded val_loss; it never timed anything. The code is already there.
REM
REM PREDICTIONS (falsifiable, written before the run)
REM   launch-bound  -^> tok/s is roughly proportional to 1 / layer_passes, i.e.
REM       R=0.5 about 1.7x faster than R=1.0, R=2.0 about 1.8x slower.
REM   compute-bound -^> same shape, so this alone does NOT separate them. What
REM       separates them is the ACROSS-MODEL spread at fixed R: if p6d stays
REM       within a few percent of mC at every R despite 2.26x the parameters,
REM       the launch/overhead explanation is the only one left standing.
REM   neither       -^> tok/s flat in R would mean something else entirely
REM       dominates (tokenizer, sampling, python loop). Also worth knowing.
REM
REM COST: inference only, minutes. No GPU time required.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P030-4] does decode speed follow parameters or layer count
echo =============================================================
python scripts\runlog.py --name P030-stage4 --note "[P030-4] does decode speed follow parameters or layer count"

echo.
echo =============================================================
echo [1/5] R=0.5  (12 layer passes)
echo =============================================================
python scripts\runlog.py --name P030-stage4 --note "[1/5] R=0.5  (12 layer passes)"
python scripts\runlog.py --name P030-stage4 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --infer-repeat 0.5
if errorlevel 1 echo [WARN] R=0.5 failed - continuing

echo.
echo =============================================================
echo [2/5] R=1.0  (20 passes, the trained depth = baseline)
echo =============================================================
python scripts\runlog.py --name P030-stage4 --note "[2/5] R=1.0  (20 passes, the trained depth = baseline)"
python scripts\runlog.py --name P030-stage4 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent
if errorlevel 1 echo [WARN] R=1.0 failed - continuing

echo.
echo =============================================================
echo [3/5] R=1.5  (28 passes)
echo =============================================================
python scripts\runlog.py --name P030-stage4 --note "[3/5] R=1.5  (28 passes)"
python scripts\runlog.py --name P030-stage4 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --infer-repeat 1.5
if errorlevel 1 echo [WARN] R=1.5 failed - continuing

echo.
echo =============================================================
echo [4/5] R=2.0  (36 passes)
echo =============================================================
python scripts\runlog.py --name P030-stage4 --note "[4/5] R=2.0  (36 passes)"
python scripts\runlog.py --name P030-stage4 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --infer-repeat 2.0
if errorlevel 1 echo [WARN] R=2.0 failed - continuing

echo.
echo =============================================================
echo [5/5] R=1.0 with int8 - does the extra dequant kernel scale the same way
echo =============================================================
python scripts\runlog.py --name P030-stage4 --note "[5/5] R=1.0 with int8 - does the extra dequant kernel scale the same way"
python scripts\runlog.py --name P030-stage4 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] int8 pass failed - continuing

python scripts\runlog.py --name P030-stage4 --note "=================================================================" "WHAT TO RECORD  (label all of it 'P030 stage 4')" "  1. a table of tok/s by (model, R). Five R values, three models." "  2. for each model: tok/s times layer_passes. If that product is roughly" "     CONSTANT, time per layer pass is fixed and the model is launch bound." "  3. the ACROSS-MODEL spread at each fixed R. That is the decisive column." "" "HOW TO ACT ON IT" "  spread stays within a few percent at every R" "      -^> launch bound confirmed. P034 stage 4 / R8 buys MEMORY ONLY. Re-price" "         R8 before starting it, and say so in the REVIEW1 roadmap." "  spread grows with parameters at larger R" "      -^> compute matters after all. R8 keeps its speed argument." "  tok/s flat in R" "      -^> neither hypothesis. Something outside the model dominates - profile" "         the sampling loop before drawing any architecture conclusion." "" "LIMITS: batch 1 only - a server batch would move the balance toward compute /" "  Windows CPU timing noisy (median of 3) / R other than 1.0 changes MODEL" "  QUALITY (result 020) but that is irrelevant here, we are timing only." "=================================================================" 
echo done.
pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
