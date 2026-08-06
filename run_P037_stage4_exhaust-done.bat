@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P037_stage4_exhaust.bat -- P037 STAGE 4 : does the L4 exhaustion
REM                                 warning actually fire
REM  Plan: test_plan\P037_...md   Basis: result 023 section 9.3 / result 006 section 5
REM =============================================================================
REM
REM PRECONDITION: IMPLEMENTED 2026-08-06.
REM   _stream(exhausted_cb) counts per-source StopIteration and calls back once
REM   per source. prepare() prints the warning and records meta["mix_exhausted"].
REM   It also warns when the finished cache is SMALLER than requested, which is
REM   what happens when every source runs dry.
REM   ***The detection is written but has never fired in a real run.***
REM   Untested error paths are not error paths.
REM
REM WHY THIS MATTERS
REM   L4 is the defect that made P007B uninterpretable. Korean Wikipedia runs
REM   out at about 300M tokens and the old _stream() just did `continue`, so the
REM   1200M pool quietly became 25 percent Korean instead of 50, and because val
REM   is the last 0.5 percent of the stream the val set became 0.0 percent
REM   Korean. Nobody knew until the [mix] instrumentation went in.
REM   A warning nobody has seen fire is not protection.
REM
REM HOW IT IS FORCED
REM   --data ko is wikipedia 20231101.ko ALONE, ratio 1.0. Asking for 400M from
REM   a source that holds about 300M guarantees exhaustion, and it is the
REM   cheapest way to reach that state.
REM
REM ***EXPECTATION.***
REM   [mix] a warning naming wikimedia/wikipedia and the token count where it
REM         ran dry (expect roughly 300M)
REM   [data] a second warning that the cache is smaller than the directory name
REM   meta.json with a non-empty mix_exhausted
REM   If NONE of those appear, the callback is not wired and the fix is fake.
REM
REM ***FIRST ATTEMPT FAILED FOR AN UNRELATED REASON (2026-08-06).***
REM   TypeError: prepare() got an unexpected keyword argument 'lora_decay'
REM   A --lora-decay edit to cli.py landed on the prepare() call instead of the
REM   train() call, because the string used to locate it was not unique. This
REM   batch was simply the first thing to run afterwards. Fixed, and
REM   scripts/check_call_kwargs.py now catches that class of edit statically.
REM   Nothing about THIS experiment was wrong.
REM
REM COST: about 20 to 30 minutes of tokenising. GPU 0.
REM   Writes data_cache\ko_400000000 - a NEW directory. Touches nothing existing.
REM ERRORLEVEL POLICY: single step, failure stops.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P037-4] force source exhaustion - does the L4 warning fire
echo =============================================================
python scripts\runlog.py --name P037-stage4 --note "[P037-4] force source exhaustion - does the L4 warning fire"

echo.
echo.
echo [guard] cli.py call-keyword sanity (this is what broke the first attempt)
python scripts\runlog.py --name P037-stage4 --note "[guard] cli.py call-keyword sanity"
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo =============================================================
echo [1/2] ko alone, 400M requested from a roughly 300M source
echo       WATCH FOR THE [mix] WARNING - that is the whole experiment
echo =============================================================
python scripts\runlog.py --name P037-stage4 --note "[1/2] ko alone, 400M requested from a roughly 300M source"
python scripts\runlog.py --name P037-stage4 -- python run100m.py prepare --data ko --tokens 400M --exact-cache
if errorlevel 1 goto PREPBAD

echo.
echo =============================================================
echo [2/2] read back what was actually written
echo =============================================================
python scripts\runlog.py --name P037-stage4 --note "[2/2] read back what was actually written"
python scripts\runlog.py --name P037-stage4 -- python scripts\diag_val_lang.py --data ko --pools 400M
if errorlevel 1 echo [WARN] readback failed - the meta.json is still on disk

python scripts\runlog.py --name P037-stage4 --note "=================================================================" "WHAT TO RECORD" "  1. the [mix] exhaustion warning text and the token count it names." "     That number is the ACTUAL size of our Korean corpus - it is the single" "     most important figure for P041 and it has never been measured directly." "  2. the [data] size warning: requested 400M, actually written how much." "  3. mix_exhausted from the readback." "" "HOW TO READ IT" "  warnings fire and the count is around 300M" "      -^> L4 detection works AND we now know the Korean corpus size. Feed it" "         into P041 section 5 stage 0 as the baseline to beat." "  warnings do not fire" "      -^> the callback is not wired. The fix is cosmetic. Fix it before" "         trusting any future [mix] block." "  the count is much larger than 300M" "      -^> then ko-en's 300.2M ceiling came from the MIXER, not the source," "         and P041's premise needs rechecking. That would be good news." "" "LIMITS: ko is wikipedia only - ko-edu-en uses a different Korean source whose" "  size is still unmeasured / this builds a cache we do not train on, so it is" "  pure diagnostic cost / streaming order is fixed, so the count is repeatable." "================================================================="
echo done.
pause
exit /b 0

:BADKWARGS
echo.
echo =================================================================
echo [STOP] cli.py passes a keyword its target function does not accept.
echo        Fix that first - it will break unrelated commands.
echo =================================================================
pause
exit /b 6

:PREPBAD
echo.
echo =================================================================
echo [STOP] prepare failed. Check whether the ko dataset config is
echo        reachable (wikimedia/wikipedia 20231101.ko).
echo =================================================================
pause
exit /b 3

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
