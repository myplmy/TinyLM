@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P034_stage3c2_unpackcache.bat -- P034 STAGE 3C, SECOND ATTEMPT
REM  Plan: test_plan\P034_...md   Prior attempt: result 016 section 13 (FAILED)
REM =============================================================================
REM
REM PRECONDITION: fixes IMPLEMENTED 2026-08-06. Nothing is pending.
REM
REM WHY THERE IS A SECOND ATTEMPT
REM   The first run failed and the CONTROL is what caught it. p6d should have
REM   been unchanged and instead dropped 13.85 -^> 8.26 tok/s, a 40 percent
REM   REGRESSION. Cause, confirmed by reading the code:
REM     1. the cache was enabled on EVERY TLinear, including modules no layer
REM        shares. dense has zero hits and still paid, holding 472.5 MB of fp32
REM        buffers - exactly the copies that P034 stages 2 and 3 removed.
REM     2. nothing ever freed the buffers, so they lived until the next forward.
REM   And the memory accounting did not see any of it: tensor_mb() only counted
REM   parameters plus _wq/_i8, so it reported the same 154.8 / 86.9 / 96.2 MB.
REM
REM WHAT CHANGED
REM   enable_unpack_cache now counts how many layers reference each MLP and only
REM   arms the shared ones. ***dense has ZERO shared MLPs, so nothing is armed
REM   and the code path is identical to the cache being off.***
REM   forward() frees a group's buffers the moment the schedule leaves that
REM   group, so at most ONE MLP worth (about 18.9 MB) is alive.
REM   tensor_mb() now counts _i8_cache.
REM
REM ***THE CONTROL IS THE POINT OF THIS RUN.***
REM   p6d MUST come out within measurement noise of its own baseline. Not
REM   "roughly similar" - the code should not even execute for it.
REM   If p6d moves by more than about 3 percent in EITHER direction, stop and
REM   report that. Do not read the tied numbers.
REM
REM ***EXPECTATION, REVISED AND DERIVED FROM THE FAILED RUN.***
REM   Result 016 section 13.5 back-solves the first run: the penalty measured on
REM   p6d was 0.1035 ms/tok per MB of buffer, so mC's 209.2 MB cost it about
REM   21.6 ms/tok, which means the unpack saving was already about 24.8 ms/tok
REM   underneath. Removing the penalty should surface it:
REM     mC (g8)  14.48 -^> about 22.6 tok/s  (1.56x)
REM     mA (g4)  lower than mC, 12 layers saved against 14 - estimate unreliable
REM     p6d      UNCHANGED
REM   That derivation rests on ONE assumption (cost is linear in buffer MB) and
REM   ONE data point. Treat 1.56x as an order of magnitude, not a target.
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
echo [P034-3C2] unpack cache, second attempt - the control decides
echo =============================================================
python scripts\runlog.py --name P034-stage3c2 --note "[P034-3C2] unpack cache, second attempt - the control decides"

echo.
echo [pre] run alone, 5 minutes idle. No prepare/tokenising beforehand.
python scripts\runlog.py --name P034-stage3c2 --note "[pre] solo + 5 min idle (result 016 section 12.5)"

echo.
echo =============================================================
echo [1/5] GATE A - logit equality AND memory accounting
echo       the runtime MB column must NOT grow versus [2/5]
echo =============================================================
python scripts\runlog.py --name P034-stage3c2 --note "[1/5] GATE A - logit equality AND memory accounting"
python scripts\runlog.py --name P034-stage3c2 -- python scripts\mem_runtime.py --device cpu --max-new 32 --drop-latent --int8-store --unpack-cache
if errorlevel 1 goto GATEBAD

echo.
echo =============================================================
echo [2/5] GATE B - the SAME measurement without the cache
echo       compare the runtime MB columns of [1/5] and [2/5]
echo =============================================================
python scripts\runlog.py --name P034-stage3c2 --note "[2/5] GATE B - same measurement without the cache, for the MB comparison"
python scripts\runlog.py --name P034-stage3c2 -- python scripts\mem_runtime.py --device cpu --max-new 32 --drop-latent --int8-store
if errorlevel 1 echo [WARN] gate B failed - continuing but the MB comparison is lost

echo.
echo =============================================================
echo [3/5] BASELINE - int8, cache OFF
echo =============================================================
python scripts\runlog.py --name P034-stage3c2 --note "[3/5] BASELINE - int8, cache OFF"
python scripts\runlog.py --name P034-stage3c2 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] baseline bench failed - continuing

echo.
echo =============================================================
echo [4/5] TREATMENT - int8, cache ON
echo =============================================================
python scripts\runlog.py --name P034-stage3c2 --note "[4/5] TREATMENT - int8, cache ON"
python scripts\runlog.py --name P034-stage3c2 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] treatment bench failed - continuing

echo.
echo =============================================================
echo [5/5] cuda, same pair
echo =============================================================
python scripts\runlog.py --name P034-stage3c2 --note "[5/5] cuda, same pair"
python scripts\runlog.py --name P034-stage3c2 -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] cuda baseline failed - continuing
python scripts\runlog.py --name P034-stage3c2 -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] cuda treatment failed - continuing

python scripts\runlog.py --name P034-stage3c2 --note "=================================================================" "WHAT TO RECORD - IN THIS ORDER" "  1. ***THE p6d RATIO between [3/5] and [4/5].*** It must be within about" "     3 percent of 1.00. Report this FIRST, before any tied number." "  2. the runtime MB columns of [1/5] versus [2/5]. They must match. If the" "     cache-ON figure is larger, the buffers are not being freed and the" "     tied speedups are borrowed from memory - which is the whole point of" "     P034, so that would be a failure even if it looks fast." "  3. the logit gate: 0.000e+00 for all three models." "  4. only then, the mC and mA ratios." "" "HOW TO READ IT" "  p6d 1.00, mC and mA up, MB unchanged" "      -^> CONFIRMED. Tying buys speed as well as memory and the gain scales" "         with g. This also lowers the bar for R8, whose unpack is more" "         expensive than int8 - do stage 4 design next." "  p6d moved" "      -^> the fix did not work. Report the number and stop. Do not average" "         with result 016 section 13." "  MB grew with the cache on" "      -^> the free path is not firing. The speed number is not real." "  everything within noise" "      -^> the unpack was never the dominant cost. Then result 014 section" "         11.4's +2.1 ms/layer needs a different decomposition, and R8's" "         case rests on memory alone." "" "LIMITS: batch 1 single stream decode / one measurement per condition /" "  changes NOTHING about training / the 1.56x estimate rests on one" "  assumption and one data point (result 016 section 13.5)." "================================================================="
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
