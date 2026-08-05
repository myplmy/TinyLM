@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P037_stage3_mixratio.bat  --  P037 STAGE 3 (L1) : what IS the actual
REM         Korean/English token ratio?
REM  Plan: test_plan\P037_...md   Basis: docs\methods\07_corpus_selection.md 4.3
REM =============================================================================
REM
REM THE DEFECT (L1)
REM   _stream() picks a SOURCE with rng.choice and then takes ONE DOCUMENT from it.
REM   The ratio in DATASETS is therefore a DOCUMENT ratio, not a token ratio. If
REM   Korean Wikipedia articles and fineweb-edu documents have different average
REM   lengths - and they do - the actual token split is not 0.5/0.5.
REM
REM   Every document in this repo that says "Korean 50 percent" is unverified.
REM   That includes results 006, 009, 011, 012, 018 and 023.
REM
REM   Run-to-run comparisons stay VALID (every run used the same loader). What is
REM   invalid is the absolute claim about composition, and val representativeness.
REM
REM WHAT THIS BATCH DOES
REM   prepare() now counts tokens and documents per source, prints both, and stores
REM   them in meta.json (mix_tokens / mix_docs / mix_token_frac). The instrumentation
REM   is non-destructive - it does not change what goes into the cache.
REM
REM   100M is used because the RATIO does not depend on pool size, and a 100M cache
REM   builds in minutes instead of an hour. If a 100M cache already exists it is
REM   reused and no [mix] block appears - in that case use a size you have not
REM   built yet, or delete the directory first.
REM
REM WHAT L2 IS AND WHY IT IS NOT HERE
REM   L2 = streaming yields in file order, no shuffle. A "600M pool" is literally
REM   the FIRST 600M tokens and val is the last 0.5 percent of that. Fixing it
REM   CHANGES CACHE CONTENT, which breaks comparability with every existing run.
REM   That needs its own cache namespace and its own decision. Measuring L1 first
REM   tells us whether L2 is even worth the disruption.
REM
REM COST: cache build time, no GPU.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P037-3] L1 : the real per-source token ratio
echo =============================================================
python scripts\runlog.py --name P037-stage3 --note "[P037-3] L1 : the real per-source token ratio"

echo.
echo =============================================================
echo [1/2] ko-en at 100M
echo =============================================================
python scripts\runlog.py --name P037-stage3 --note "[1/2] ko-en at 100M"
python scripts\runlog.py --name P037-stage3 -- python run100m.py prepare --data ko-en --tokens 100M --exact-cache
if errorlevel 1 echo [WARN] ko-en 100M prepare failed - continuing

echo.
echo =============================================================
echo [2/2] ko-edu-en at 100M - the curated mix, same question
echo =============================================================
python scripts\runlog.py --name P037-stage3 --note "[2/2] ko-edu-en at 100M - the curated mix"
python scripts\runlog.py --name P037-stage3 -- python run100m.py prepare --data ko-edu-en --tokens 100M --exact-cache
if errorlevel 1 echo [WARN] ko-edu-en 100M prepare failed - continuing

python scripts\runlog.py --name P037-stage3 --note "=================================================================" "WHAT TO RECORD" "  1. the [mix] block: per source, configured ratio / document share / TOKEN share" "  2. whether any source is flagged as differing from config by over 5 points" "  3. the same for both datasets" "  If no [mix] block appears, the cache already existed and was reused - the" "  count only happens on a fresh build." "" "HOW TO ACT ON IT" "  token share within a few points of the configured ratio" "      -^> L1 is cosmetic. Correct the wording in past documents and move on." "  token share far from the configured ratio" "      -^> every 'Korean 50 percent' statement is wrong and must be corrected." "         Then decide whether to switch the mixer to TOKEN units, which would" "         change cache content and therefore needs its own namespace." "" "LIMITS: measures the mix as built, at 100M. Does not touch L2 (no shuffle) or" "  L3 (single text field). L2 in particular changes cache content." "=================================================================" 
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
