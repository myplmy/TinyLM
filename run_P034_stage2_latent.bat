@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P034_stage2_latent.bat  --  P034 STAGE 2 : drop the fp32 latent weight
REM  Plan: test_plan\P034_...md   Roadmap: REVIEW1 R2
REM =============================================================================
REM
REM THE CLAIM BEING TESTED
REM   Result 016 measured resident memory as
REM       unique ternary params x 4 bytes x TWO copies (latent + dequant) + 33 MB
REM   Inference has no backward pass, so the latent copy is dead weight. Removing
REM   it should roughly HALVE resident memory. No custom kernel, no retraining.
REM   This is the largest single memory lever available today.
REM
REM WHAT WOULD FALSIFY IT
REM   1. resident drops by much less than 2x  -^> something else holds a reference
REM      (an autograd graph on the frozen tensor is the usual suspect)
REM   2. the logit gate is nonzero            -^> we changed the model, not the
REM      memory. In that case DISCARD the memory numbers - they describe a
REM      different model than the one we measured before.
REM   3. the resident ORDER changes (mC ^< mA ^< p6d today) -^> the prediction that
REM      residency tracks unique parameter count was incomplete.
REM
REM WHY MEASURE SPEED TOO
REM   Result 016 predicted speed should track RESIDENT memory, not stored MB.
REM   Stage 2 halves resident while leaving stored MB untouched, so it is the
REM   cleanest test of that prediction we will ever get: one axis moves alone.
REM   If tok/s does not move, memory-to-speed transfer is dead and P034 stage 4
REM   (5-bit packing) is the only remaining route - that is R8 in the roadmap.
REM
REM COST: inference only, a few minutes, no GPU time required. Writes nothing
REM   to runs\. Nothing here is destructive.
REM ERRORLEVEL POLICY: independent measurements, failures only warn.
REM =============================================================================

if not exist run100m.py goto BADROOT
set TL_NOPAUSE=1

echo =============================================================
echo [P034-2] latent release : resident memory and whether speed follows
echo =============================================================

echo.
echo =============================================================
echo [0/3] GATE : the cache path must still be correct
echo   Cheap, and it means a surprise later cannot be blamed on the cache.
echo =============================================================
set TL_LOGNAME=P034-stage2
set TL_MODELS=mA_g4s34_k4 mC_g8_k4 p6d
call scripts\batch\tool_kvcache_gate.bat
if errorlevel 1 goto GATEBAD

echo.
echo =============================================================
echo [1/3] BASELINE : resident memory WITHOUT the latent release
echo   Same numbers as result 016. Re-measured here so the before and after
echo   sit in ONE log - comparing across logs is how conventions drift.
echo =============================================================
set TL_LOGNAME=P034-stage2
set TL_MODELS=mA_g4s34_k4 mC_g8_k4 p6d
set TL_EXTRA=
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] baseline memory profile failed - continuing

echo.
echo =============================================================
echo [2/3] STAGE 2 : same measurement WITH --drop-latent
echo   The script runs a logit equivalence gate per model before and after the
echo   release. It must read 0.000e+00. Releasing a tensor we no longer read
echo   cannot change arithmetic - anything else means we released too much.
echo =============================================================
set TL_LOGNAME=P034-stage2
set TL_MODELS=mA_g4s34_k4 mC_g8_k4 p6d
set TL_EXTRA=--drop-latent
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] drop-latent memory profile failed - continuing

echo.
echo =============================================================
echo [3/3] SPEED : does halved resident memory buy CPU tokens per second
echo   Single thread is the honest edge number. Cache on.
echo =============================================================
python scripts\runlog.py --name P034-stage2 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3
if errorlevel 1 echo [WARN] baseline speed bench failed - continuing
python scripts\runlog.py --name P034-stage2 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent
if errorlevel 1 echo [WARN] drop-latent speed bench failed - continuing

echo.
echo =================================================================
echo WHAT TO RECORD  (label all of it "P034 stage 2")
echo   1. per model: resident MB before and after, and the ratio
echo   2. the logit gate value per model - it must be exactly 0.000e+00
echo   3. whether the resident ORDER changed
echo   4. tok/s before and after, single thread, cache on
echo.
echo HOW TO READ IT
echo   ratio near 2.0x, gate 0, order unchanged
echo       -^> stage 2 works. Report runtime_mb everywhere from now on, and
echo          update the residency claims in result 016 and METHODS.
echo   ratio well under 2.0x
echo       -^> a reference survives. Look for an autograd graph on the frozen
echo          tensor before writing any conclusion.
echo   speed unchanged despite half the resident memory
echo       -^> memory-to-speed transfer is NOT happening at this size. That is a
echo          NEGATIVE RESULT and it is the argument for R8 (5-bit packing).
echo          It is not a failure of stage 2 - the memory win is real either way.
echo.
echo LIMITS: batch 1 single request / Windows CPU timing is noisy (median of 3) /
echo   drop_latent is IRREVERSIBLE in a process - training cannot resume after it /
echo   stored MB does NOT move here, and it is not supposed to.
echo =================================================================
echo done.
pause
exit /b 0

:GATEBAD
echo.
echo =================================================================
echo [STOP] the KV cache gate failed. Memory and speed numbers taken after
echo   a broken cache describe nothing. Fix the cache first.
echo =================================================================
pause
exit /b 1

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
