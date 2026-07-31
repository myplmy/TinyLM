@echo off
REM ===== LOGGING (added 2026-07-31) =====
REM   Every python command below is run through scripts\runlog.py, which prints to the
REM   console in real time AND appends to test_result\log_YYYYMMDD_NAME.txt line by line,
REM   flushing and fsync-ing as it goes. If this batch dies halfway, or the machine loses
REM   power, everything up to the last couple of seconds is already on disk.
REM   Losing the log of a long run costs the whole run, so this is not optional.
REM   Exit codes pass through unchanged, so every `if errorlevel` below still works.

REM ===== relocated to scripts\batch on 2026-07-31 =====
REM   Root now holds only batches for experiments that have NOT run yet. This one is a
REM   REUSABLE tool or a completed run kept for re-verification, so it lives here.
REM   It works from EITHER location: launched from the repo root, or double-clicked here.
REM   No percent-expansion is used (this repo bans the percent sign in .bat files), so the
REM   working directory is fixed by looking for a marker file instead.
if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ===== P028 stage 0.5 : CAUSAL check - is the tail region intrinsically harder? =====
REM   Plan: test_plan\P028 section "stage 0.5"
REM
REM WHY THIS EXISTS
REM   Stage 0 (run_P028_diag.bat) gave STATISTICS, not causes. And the magnitudes do not add up:
REM   the observed gap is 3.14 nats (perplexity 23x), but unigram JS 0.057 + Hangul ratio +6.3pp
REM   + duplicate rate 5.69 percent do not naturally produce that. Something may be unaccounted for.
REM
REM THE IDEA
REM   Compare the FRONT and the BACK of train.bin. Both were trained on, so "never seen before"
REM   is held constant and only "is this region intrinsically harder" remains.
REM
REM     front ~= back, val much worse : pure never-seen effect, so H1 (duplication)
REM     front much better than back, back ~= val : the tail IS harder, so H2 CONFIRMED
REM     all three similar : not explained by the cache, look at setup / tokenizer
REM
REM   ko-en is run the same way as the healthy control (its val - train gap was about 0).
REM
REM COST: inference only, no training. A few minutes. Writes nothing to runs\.
REM   Uses the EXISTING checkpoints, so nothing has to be retrained to get this answer.
REM
REM ERRORLEVEL POLICY: independent runs, failures only warn.

echo ============================================================
echo [P028-0.5] causal check : front vs back of train, vs val
python scripts\runlog.py --name P028-stage05 --note "[P028-0.5] causal check : front vs back of train, vs val"
echo ============================================================

echo.
echo ============================================================
echo [1/2] CONTROL : ko-en (healthy - val minus train was about 0)
python scripts\runlog.py --name P028-stage05 --note "[1/2] CONTROL : ko-en (healthy - val minus train was about 0)"
echo ============================================================
python scripts\runlog.py --name P028-stage05 -- python scripts\eval_slices.py --data ko-en --tokens 300M --tag dense --arch dense --docstats
if errorlevel 1 echo [WARN] ko-en slice eval failed - continuing

echo.
echo ============================================================
echo [2/2] SUSPECT : ko-edu-en (the 3.14 nats gap)
python scripts\runlog.py --name P028-stage05 --note "[2/2] SUSPECT : ko-edu-en (the 3.14 nats gap)"
echo ============================================================
python scripts\runlog.py --name P028-stage05 -- python scripts\eval_slices.py --data ko-edu-en --tokens 300M --tag dense --arch dense --docstats
if errorlevel 1 echo [WARN] ko-edu-en slice eval failed - continuing

echo.
echo ================================================================
echo HOW TO DECIDE - compare the two reports, especially "back minus front"
echo.
echo   ko-en back-minus-front should be SMALL. If ko-edu-en back-minus-front is LARGE,
echo   the tail of that corpus really is different, and the tail-val split is the direct cause.
echo.
echo   Also read the val document stats. If ONE document is more than 20 percent of val,
echo   that single document could be driving the whole val loss - which would make this a
echo   FILTERING problem, not a corpus-quality problem. Very different fix.
echo.
echo NEXT STEP DEPENDS ON THE ANSWER
echo   H2 confirmed  -^> the prepare() val split must change (random over documents).
echo                    That touches EVERY dataset - see P028 appendix A for the C to D plan.
echo   H1 confirmed  -^> dedup on rebuild is the fix, the val split is secondary.
echo   neither       -^> stop blaming the cache and look at tokenizer / pool ratio.
echo.
echo LIMIT: front and back were BOTH trained on, so this separates "region difficulty",
echo   not "how much was memorised". Final causal proof needs a rebuild plus a retrain.
echo ================================================================
echo done.
pause

:BADROOT
echo.
echo ================================================================
echo [STOP] could not locate the repo root (run100m.py not found).
echo   Run this batch from the TinyLM working folder, or double-click it where it lives
echo   (scripts\batch). Nothing was executed.
echo ================================================================
pause
exit /b 9
