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

REM ===== P028 stage 0.6 : is ONE document driving the whole val loss? =====
REM   Plan: test_plan\P028   Previous: result 011 (stage 0 and stage 0.5)
REM
REM WHY THIS AND NOT A prepare() REWRITE
REM   Stage 0.5 measured, for ko-edu-en:
REM       back minus front  = +1.040   (distribution shift, real)
REM       val minus back    = +2.198   (cost of "never seen")
REM   The control ko-en scored +0.153 for that same "never seen" term. Fourteen times
REM   smaller. Unseen text from the SAME corpus has no business costing +2.198.
REM   And stage 0.5 also found that ONE document is 23.5 percent of that val set.
REM   So "never seen" and "that one document is weird" are still tangled together.
REM
REM   The fix depends on which it is, and the two fixes are very different in size:
REM       one document dominates  -^> FILTERING problem. Length cap plus a per-document
REM                                  share cap. Narrow change, ko-edu-en only.
REM       all documents are bad   -^> SPLIT problem. Random split over documents.
REM                                  Touches EVERY dataset and invalidates every val
REM                                  number we have. Large change, needs a version split.
REM   Rewriting prepare() before knowing which one would be guessing. This costs minutes.
REM
REM COST: inference only, minutes. No training. Writes nothing to runs\.
REM ERRORLEVEL POLICY: independent measurements, failures only warn.

echo ============================================================
echo [P028-0.6] per-document val loss decomposition
python scripts\runlog.py --name P028-stage06 --note "[P028-0.6] per-document val loss decomposition"
echo ============================================================

echo.
echo ============================================================
echo [1/2] SUSPECT : ko-edu-en  (val minus back was +2.198)
python scripts\runlog.py --name P028-stage06 --note "[1/2] SUSPECT : ko-edu-en  (val minus back was +2.198)"
echo ============================================================
python scripts\runlog.py --name P028-stage06 -- python scripts\diag_val_docs.py --data ko-edu-en --tokens 300M --arch dense
if errorlevel 1 echo [WARN] ko-edu-en decomposition failed - continuing

echo.
echo ============================================================
echo [2/2] CONTROL : ko-en  (val minus back was +0.153 - the healthy number)
python scripts\runlog.py --name P028-stage06 --note "[2/2] CONTROL : ko-en  (val minus back was +0.153 - the healthy number)"
echo   Needed to calibrate. If ko-en ALSO has a dominant document, then a skewed
echo   document-size distribution is normal for our pipeline and the ko-edu-en
echo   number means something else.
echo ============================================================
python scripts\runlog.py --name P028-stage06 -- python scripts\diag_val_docs.py --data ko-en --tokens 300M --arch dense
if errorlevel 1 echo [WARN] ko-en decomposition failed - continuing

echo.
echo ================================================================
echo WHAT TO RECORD
echo   1. overall val loss and the loss with the top 1 / 2 / 5 / 10 documents removed
echo   2. the token share and loss share of the single biggest contributor
echo   3. the per-document loss distribution (median vs 95th percentile vs max)
echo   4. the same four things for the ko-en control
echo.
echo HOW TO ACT ON IT
echo   removing the top document drops val a LOT (over 0.5 nats)
echo       -^> filtering problem. Add a document length cap and a per-document share
echo          cap to prepare(). ko-edu-en only. Do NOT randomise the split yet -
echo          that touches every dataset for no reason.
echo   removing it changes little (under 0.15)
echo       -^> the whole val distribution is different. Then the random split IS
echo          needed, which means a C to D version transition (P028 appendix A):
echo          new cache directory, registry split, and NO comparing old val numbers
echo          to new ones. Budget for re-running the baselines.
echo   in between
echo       -^> both. Fix filtering first because it is cheap, then re-measure before
echo          committing to the split rewrite.
echo.
echo   IMPORTANT: whichever way this goes, ko-en run-to-run comparisons stay valid.
echo   Its defects are a COMMON OFFSET across all runs. Only absolute values are
echo   optimistic. Do not invalidate REVIEW1 over this.
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
