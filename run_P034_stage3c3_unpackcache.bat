@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P034_stage3c3_unpackcache.bat -- P034 STAGE 3C, THIRD ATTEMPT
REM  Plan: test_plan\P034_...md   Prior attempt: result 016 section 13 (FAILED)
REM =============================================================================
REM
REM PRECONDITION: fixes IMPLEMENTED 2026-08-06. Nothing is pending.
REM
REM WHY THERE IS A THIRD ATTEMPT
REM   Attempt 2 (result 016 section 14) got mC +17.1 percent and mA +11.3 percent -
REM   the first time tying bought speed. But the CONTROL moved again: p6d went
REM   15.24 -^> 11.76 tok/s, 0.77x. And this time the MEMORY GATE said why:
REM   residency with the cache on was 267.3 / 188.2 / 197.5 MB against
REM   154.8 / 86.9 / 96.2 MB with it off.
REM
REM   The excess matches the ATTENTION TLinear caches to the byte:
REM     p6d  29.49M params -^> 112.5 MiB   log excess 112.5
REM     mC   26.54M params -^> 101.2 MiB   log excess 101.3
REM     mA   26.54M params -^> 101.2 MiB   log excess 101.3
REM
REM   Cause: enable_unpack_cache armed only the shared MLPs, but forward() then
REM   looped over ALL TLinears to stamp the generation counter, reviving the
REM   attention modules it had just disarmed. Attention is called once per layer,
REM   so it has zero cache hits and pays pure cost.
REM
REM ***THIS IS THE SAME CLASS OF MISTAKE TWICE.*** Attempt 1 got the arming
REM   scope wrong, attempt 2 got the stamping scope wrong. The set of modules a
REM   feature applies to is now defined in ONE place: _armed_tlinears.
REM
REM ***THE CONTROL IS STILL THE POINT.***
REM   p6d now has ZERO armed modules, so the loop body never executes for it.
REM   It must come out identical to its own baseline, not merely close.
REM   If p6d moves more than about 3 percent, STOP and report that.
REM
REM ***EXPECTATION, DERIVED FROM ATTEMPT 2 (result 016 section 14.5).***
REM   p6d paid 19.42 ms/tok for 112.5 MiB = 0.1726 ms/tok per MiB.
REM   mC paid 101.2 MiB of that = about 17.47 ms/tok, and still came out
REM   8.97 ms/tok ahead, so the unpack saving underneath is about 26.44 ms/tok.
REM     mC (g8)  16.06 -^> about 27.9 tok/s  (1.74x)
REM     mA (g4)  15.45 -^> about 24.6 tok/s  (1.59x)
REM     p6d      UNCHANGED
REM   Cross-check: mC saves 14 middle-layer unpacks, mA saves 12. Per unpack that
REM   is 1.89 ms and 2.00 ms - within 6 percent, and the same order as the 1.7 ms
REM   implied by result 014 section 11.4. Three independent routes agree, which is
REM   why this estimate is worth writing down before reading the number.
REM
REM MEASUREMENT HYGIENE (result 016 section 12.5)
REM   run ALONE / idle 5 minutes first, no prepare or tokenising beforehand /
REM   baseline and treatment are in the SAME run so read the RATIO.
REM
REM COST: a few minutes, GPU 0. Depends on nothing, writes nothing.
REM ERRORLEVEL POLICY: the gate stops the batch. Benchmarks warn and continue.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P034-3C3] unpack cache, second attempt - the control decides
echo =============================================================
python scripts\runlog.py --name P034-stage3c3 --note "[P034-3C3] unpack cache, second attempt - the control decides"

echo.
echo [pre] run alone, 5 minutes idle. No prepare/tokenising beforehand.
python scripts\runlog.py --name P034-stage3c3 --note "[pre] solo + 5 min idle (result 016 section 12.5)"

echo.
echo =============================================================
echo [1/5] GATE A - logit equality AND memory accounting
echo       the runtime MB column must NOT grow versus [2/5]
echo =============================================================
python scripts\runlog.py --name P034-stage3c3 --note "[1/5] GATE A - logit equality AND memory accounting"
python scripts\runlog.py --name P034-stage3c3 -- python scripts\mem_runtime.py --device cpu --max-new 32 --drop-latent --int8-store --unpack-cache
if errorlevel 1 goto GATEBAD

echo.
echo =============================================================
echo [2/5] GATE B - the SAME measurement without the cache
echo       compare the runtime MB columns of [1/5] and [2/5]
echo =============================================================
python scripts\runlog.py --name P034-stage3c3 --note "[2/5] GATE B - same measurement without the cache, for the MB comparison"
python scripts\runlog.py --name P034-stage3c3 -- python scripts\mem_runtime.py --device cpu --max-new 32 --drop-latent --int8-store
if errorlevel 1 echo [WARN] gate B failed - continuing but the MB comparison is lost

echo.
echo =============================================================
echo [3/5] BASELINE - int8, cache OFF
echo =============================================================
python scripts\runlog.py --name P034-stage3c3 --note "[3/5] BASELINE - int8, cache OFF"
python scripts\runlog.py --name P034-stage3c3 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] baseline bench failed - continuing

echo.
echo =============================================================
echo [4/5] TREATMENT - int8, cache ON
echo =============================================================
python scripts\runlog.py --name P034-stage3c3 --note "[4/5] TREATMENT - int8, cache ON"
python scripts\runlog.py --name P034-stage3c3 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] treatment bench failed - continuing

echo.
echo =============================================================
echo [5/5] cuda, same pair
echo =============================================================
python scripts\runlog.py --name P034-stage3c3 --note "[5/5] cuda, same pair"
python scripts\runlog.py --name P034-stage3c3 -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] cuda baseline failed - continuing
python scripts\runlog.py --name P034-stage3c3 -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] cuda treatment failed - continuing

python scripts\runlog.py --name P034-stage3c3 --note "=================================================================" "WHAT TO RECORD - IN THIS ORDER" "  1. ***THE p6d RATIO between [3/5] and [4/5].*** It must be within about" "     3 percent of 1.00. Report this FIRST, before any tied number." "  2. the runtime MB columns of [1/5] versus [2/5]. They must match. If the" "     cache-ON figure is larger, the buffers are not being freed and the" "     tied speedups are borrowed from memory - which is the whole point of" "     P034, so that would be a failure even if it looks fast." "  3. the logit gate: 0.000e+00 for all three models." "  4. only then, the mC and mA ratios." "" "HOW TO READ IT" "  p6d 1.00, mC and mA up, MB unchanged" "      -^> CONFIRMED. Tying buys speed as well as memory and the gain scales" "         with g. This also lowers the bar for R8, whose unpack is more" "         expensive than int8 - do stage 4 design next." "  p6d moved" "      -^> the fix did not work. Report the number and stop. Do not average" "         with result 016 section 13." "  MB grew with the cache on" "      -^> the free path is not firing. The speed number is not real." "  everything within noise" "      -^> the unpack was never the dominant cost. Then result 014 section" "         11.4's +2.1 ms/layer needs a different decomposition, and R8's" "         case rests on memory alone." "" "LIMITS: batch 1 single stream decode / one measurement per condition /" "  changes NOTHING about training / the 1.56x estimate rests on one" "  assumption and one data point (result 016 section 13.5)." "================================================================="
echo done.
pause
exit /b 0

:GATEBAD
echo.
echo =================================================================
echo [STOP] the logit equality gate failed. The unpack cache is NOT
echo        bit identical - that is a bug, not a tradeoff.
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
