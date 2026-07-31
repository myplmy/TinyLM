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

REM ===== P028 stage 0 : token-cache health diagnosis (NO GPU, NO TRAINING) =====
REM
REM WHY: result 009 ended with ko-edu-en dense at train 3.03 / val 6.17 = a 3.14 nats gap.
REM   The same code on ko-en shows no such gap. At 300M tokens with 132M ternary parameters
REM   that is NOT ordinary overfitting. Two hypotheses, and this batch separates them
REM   WITHOUT spending any GPU time:
REM     H1  duplicate documents on the train side, so repeated exposure drops train loss only
REM     H2  val split distribution shift. prepare() takes the LAST 0.5 percent of the stream,
REM         and each source is consumed in shard order, so a sorted shard biases the tail
REM
REM   Until this is settled, ko-edu-en is on hold (see EXPERIMENT_BASELINES section 2.4) and
REM   running more data-comparison experiments on it would waste GPU hours.
REM
REM READ IT AS A COMPARISON: ko-en is the healthy control. An item that flags [!] on
REM   ko-edu-en but NOT on ko-en is the actual suspect. A flag on both is normal for this corpus.
REM
REM COST: minutes, CPU only, read-only on data_cache. Writes nothing, trains nothing.

echo ============================================================
echo [P028-0] cache diagnosis : ko-en (control) vs ko-edu-en (suspect)
python scripts\runlog.py --name P028-diag --note "[P028-0] cache diagnosis : ko-en (control) vs ko-edu-en (suspect)"
echo ============================================================
echo.
echo [0] caches present
python scripts\runlog.py --name P028-diag --note "[0] caches present"
python scripts\runlog.py --name P028-diag -- python scripts\diag_cache.py
if errorlevel 1 echo [WARN] listing failed - continuing

echo.
echo ============================================================
echo [1/2] CONTROL : ko-en 300M  (this one trained normally)
python scripts\runlog.py --name P028-diag --note "[1/2] CONTROL : ko-en 300M  (this one trained normally)"
echo ============================================================
python scripts\runlog.py --name P028-diag -- python scripts\diag_cache.py --data ko-en --tokens 300M
if errorlevel 1 echo [WARN] ko-en diag failed - continuing

echo.
echo ============================================================
echo [2/2] SUSPECT : ko-edu-en 300M  (3.14 nats train/val gap)
python scripts\runlog.py --name P028-diag --note "[2/2] SUSPECT : ko-edu-en 300M  (3.14 nats train/val gap)"
echo ============================================================
python scripts\runlog.py --name P028-diag -- python scripts\diag_cache.py --data ko-edu-en --tokens 300M
if errorlevel 1 echo [WARN] ko-edu-en diag failed - continuing

echo.
echo ============================================================
echo HOW TO DECIDE (compare the two reports above, item by item):
echo.
echo   [2] duplicate rate high on ko-edu-en only   -^> H1 confirmed. Rebuild the cache with
echo       document-hash dedup before using it for anything.
echo   [3] val-in-train leak                       -^> val is optimistic, rebuild.
echo   [4] val JS divergence far above every train chunk, ko-edu-en only
echo                                               -^> H2 confirmed. The real fix is to change
echo       prepare() so val is sampled at RANDOM over documents instead of taking the tail.
echo       That touches EVERY dataset, so propose it separately and get approval first.
echo   [5] val Hangul ratio outside the train range -^> source mixing is uneven across the stream.
echo.
echo   NOTHING flags on ko-edu-en  -^> the 3.14 nats gap is NOT explained by cache statistics.
echo       Look elsewhere: pool ratio (that run had no --pool-tokens, so pool = 1x trained),
echo       or the tokenizer trained on only 200k sampled docs.
echo.
echo LIMIT: these are statistics, not causes. A clean report does not prove the data is good,
echo   and a flagged report does not prove that flag caused the 3.14 nats. Only retraining does.
echo ============================================================
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
