@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P034_stage3c_unpackcache.bat -- P034 STAGE 3C : cache the int8 unpack
REM  Plan: test_plan\P034_...md
REM  Basis: docs\ 2026-08-06 tying analysis report, section 5
REM =============================================================================
REM
REM PRECONDITION: IMPLEMENTED 2026-08-06. Nothing is pending.
REM   TLinear._wq_from_i8 + set_unpack_gen  /  Transformer.enable_unpack_cache
REM   bench_infer.py --unpack-cache  /  mem_runtime.py --unpack-cache
REM   Default is OFF, so every existing path is bit identical.
REM
REM WHAT THIS TESTS
REM   Tied layers share ONE MLP object, but _wq_from_i8 runs per FORWARD CALL.
REM   At g8 the 16 middle layers unpack the same weights 16 times instead of 2.
REM   The layer schedule is mid_mlps[j // g], so the same MLP appears in g
REM   CONSECUTIVE layers - unpack once, reuse for g layers, then drop it.
REM   Only one fp32 buffer is ever alive, so the memory win is untouched.
REM
REM ***WRITE YOUR EXPECTATION DOWN BEFORE READING THE NUMBERS.***
REM   mC (g8)  14.23 -^> about 21.5 tok/s   (1.51x)
REM   mA (g4)  14.33 -^> about 20.2 tok/s   (1.41x)
REM   p6d (g1) 13.73 -^> 13.73 UNCHANGED    ^<-- THIS IS THE CONTROL
REM
REM   ***IF p6d MOVES, THE MEASUREMENT IS WRONG, NOT THE MODEL.***
REM   p6d has no sharing, so it has nothing to reuse. A speedup there means
REM   something else changed (thermal, load, a different code path).
REM
REM GATE - RUN [1/4] FIRST AND READ IT
REM   The cache returns THE TENSOR IT JUST COMPUTED, so logits must be bit
REM   identical: max^|dlogit^| = 0.000e+00. Anything else is a bug. If the gate
REM   fails, STOP - do not record the speed numbers.
REM
REM MEASUREMENT HYGIENE (result 016 section 12.5, revised)
REM   1. run this ALONE
REM   2. machine IDLE FOR 5 MINUTES first - especially no prepare/tokenising.
REM      Result 016 section 12 drifted 2 to 9 percent from a 12 minute
REM      tokenising job that had finished before the benchmark started.
REM   3. this batch measures the baseline and the new path IN THE SAME RUN,
REM      so read the RATIO, not the absolute tok/s.
REM
REM COST: a few minutes, GPU 0 (cuda pass is optional and short).
REM DEPENDS ON NOTHING. Touches no checkpoint, no cache, no other experiment.
REM ERRORLEVEL POLICY: the gate stops the batch. Benchmarks warn and continue.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P034-3C] does caching the int8 unpack turn tying into speed
echo =============================================================
python scripts\runlog.py --name P034-stage3c --note "[P034-3C] does caching the int8 unpack turn tying into speed"

echo.
echo [pre] machine load check - close everything else, then wait 5 minutes
echo       (result 016 section 12: a finished tokenising job still cost 2-9 percent)
python scripts\runlog.py --name P034-stage3c --note "[pre] solo run + 5 min idle required (result 016 section 12.5)"

echo.
echo =============================================================
echo [1/4] GATE - logit equality with the unpack cache ON
echo =============================================================
python scripts\runlog.py --name P034-stage3c --note "[1/4] GATE - logit equality with the unpack cache ON"
python scripts\runlog.py --name P034-stage3c -- python scripts\mem_runtime.py --device cpu --max-new 32 --drop-latent --int8-store --unpack-cache
if errorlevel 1 goto GATEBAD

echo.
echo =============================================================
echo [2/4] BASELINE - int8, no unpack cache (this is result 016 section 12)
echo =============================================================
python scripts\runlog.py --name P034-stage3c --note "[2/4] BASELINE - int8 without the unpack cache"
python scripts\runlog.py --name P034-stage3c -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] baseline bench failed - continuing

echo.
echo =============================================================
echo [3/4] TREATMENT - int8 WITH the unpack cache
echo =============================================================
python scripts\runlog.py --name P034-stage3c --note "[3/4] TREATMENT - int8 with the unpack cache"
python scripts\runlog.py --name P034-stage3c -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] treatment bench failed - continuing

echo.
echo =============================================================
echo [4/4] cuda, same pair - is the effect device dependent
echo =============================================================
python scripts\runlog.py --name P034-stage3c --note "[4/4] cuda, same pair"
python scripts\runlog.py --name P034-stage3c -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] cuda baseline failed - continuing
python scripts\runlog.py --name P034-stage3c -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] cuda treatment failed - continuing

python scripts\runlog.py --name P034-stage3c --note "=================================================================" "WHAT TO RECORD" "  1. the GATE line from [1/4]. It must read 0.000e+00 for all three models." "     If it does not, record THAT and discard the speed numbers." "  2. tok/s for [2/4] and [3/4], as a RATIO per model. Absolute values drift" "     with thermal state - the ratio does not." "  3. the p6d ratio SEPARATELY. It is the control and it should be 1.00." "" "HOW TO READ IT" "  mC and mA speed up, p6d does not" "      -^> confirmed. Tying now buys speed as well as memory, and the gain" "         scales with g. This also lowers the bar for R8 (stage 4), whose" "         unpack is MORE expensive than int8." "  everything speeds up including p6d" "      -^> NOT confirmed. Something environmental changed. Re-run after idle." "  nothing changes" "      -^> the unpack was not the cost. Then the layer cost is elsewhere and" "         result 014 section 11.4 needs a different decomposition." "" "LIMITS: batch 1 single stream decode / one measurement per condition / this" "  changes NOTHING about training and NOTHING about memory - the packed and" "  runtime MB columns must be identical between [2/4] and [3/4]." "================================================================="
echo done.
pause
exit /b 0

:GATEBAD
echo.
echo =================================================================
echo [STOP] the logit equality gate failed. The unpack cache is NOT
echo        bit identical, which means it is a bug and not a tradeoff.
echo        Do not record any speed number from this run.
echo =================================================================
pause
exit /b 4

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
