@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P047_stage0_spam_rate.bat -- P047 stage 0. Spam rate of the STANDARD corpus.
REM  Plan: test_plan/P047 (ko-en spam rate)
REM =============================================================================
REM
REM WHY THIS ONE FIRST
REM   Result 011 section 2 is the LARGEST single quality gain in this repo:
REM   -0.296 nats (24.7 sigma), and it came from DATA, not architecture. 63 percent
REM   of the ko-edu-en gap was spam.
REM   But every baseline we own is trained on ko-en, and ko-en's spam rate has
REM   NEVER been measured. Result 018 called ko-en a "healthy control" from a
REM   handful of samples - that is "not seen in a sample", not "absent".
REM
REM   NO GPU. NO TRAINING. NOTHING IS WRITTEN. Cost is essentially zero and the
REM   potential is a -0.3 nats class gain, so this runs before REVIEW2.
REM
REM WHAT IT DOES
REM   Calls prepare.spam_signature() - the SAME function --doc-filter uses, so
REM   what we count is exactly what the filter would drop. Does not tokenize
REM   (the signature only looks at chars, newlines, line-uniqueness), so it runs
REM   at streaming speed instead of paying the 12 minute tokenizer pass.
REM
REM ***STEP 1 IS THE POSITIVE CONTROL - READ IT FIRST***
REM   ko-edu-en is KNOWN to contain spam (results 018 and 023 section 8). If step 1
REM   finds none, the TOOL is broken and step 2's numbers mean nothing.
REM   Trap 17: never run an optimisation without a condition where nothing
REM   should change.
REM
REM PREDICTIONS (plan section 3) - written here so the result cannot be smoothed over
REM   P1 ko-en rate much lower than ko-edu-en
REM   P2 but NOT zero (fineweb-edu is a web crawl; its filter scores content
REM      quality, not spam structure)
REM   P3 char share under 0.1 percent
REM   P5 most large docs pass the newline test but FAIL the uniqueness test
REM      (wiki large docs are lists and tables, so lines repeat)
REM   P2 and P3 point opposite ways on purpose. One of them will be wrong.
REM
REM HOW TO READ THE RESULT
REM   spam 0 AND large docs exist AND control fired = ko-en is clean. P047 closes.
REM                                    That is the FIRST confirmation our baselines
REM                                    sit on safe data.
REM   spam chars ^>= 0.01 percent      = stage 1. And that means rebuilding baselines.
REM   spam 0 AND large docs 0         = VERDICT IMPOSSIBLE. Rerun with
REM                                    --min-chars 10000.
REM   ***A small share is NOT a small problem*** - result 023 section 8 found spam
REM   was a minority of tokens but 53 percent of the val loss. The gate is
REM   EXISTENCE, not share.
REM
REM   You can Ctrl+C once the ratio has converged. Partial totals are printed.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo =============================================================
echo [P047-0] corpus spam rate. NO GPU, NO TRAINING, NOTHING WRITTEN
echo   [1/2] ko-edu-en  400MB   POSITIVE CONTROL - must find spam
echo   [2/2] ko-en      1.5GB   the real question
echo =============================================================
echo.

echo [1/2] POSITIVE CONTROL - ko-edu-en (must detect spam or the tool is broken)
python scripts\runlog.py --name P047_stage0 --note "[1/2] POSITIVE CONTROL ko-edu-en - must find spam"
python scripts\runlog.py --name P047_stage0 -- python scripts\diag_spam_rate.py --data ko-edu-en --max-bytes 400M --report-every 100M
if errorlevel 1 echo [WARN] control step returned an error - continuing

echo.
echo [2/2] ko-en - the standard corpus every baseline is trained on
python scripts\runlog.py --name P047_stage0 --note "[2/2] ko-en the standard corpus"
python scripts\runlog.py --name P047_stage0 -- python scripts\diag_spam_rate.py --data ko-en --max-bytes 1.5G --report-every 200M
if errorlevel 1 echo [WARN] ko-en step returned an error - continuing

echo.
echo =================================================================
echo WHAT TO RECORD
echo   1. ***step 1 must show spam ^> 0.*** If it does not, stop and report that
echo      the tool is broken. Do not read step 2.
echo   2. step 2 spam doc count and spam CHAR percent.
echo   3. if 0 docs: the 95 percent upper bound line. That converts "found none"
echo      into "the rate is at most this much".
echo   4. the large-document profile: how many large docs pass ONLY the newline
echo      test, how many pass ONLY uniqueness. If one condition never fires in
echo      ko-en, the signature does not describe this corpus and a 0 means
echo      "cannot see", not "clean".
echo   5. per-source attribution - wikipedia.ko or fineweb-edu.
echo.
echo HOW TO READ IT
echo   clean   -^> P047 closes. First confirmation the baselines are safe.
echo   dirty   -^> stage 1 (loss attribution, GPU 0) BEFORE any retraining.
echo   no large docs -^> verdict impossible, rerun with --min-chars 10000.
echo.
echo LIMITS: the signature was derived from ko-edu-en spam (result 018). Other
echo   contamination shapes are invisible to it. Chars are not tokens.
echo   Past the Korean exhaustion point (~280.6M tokens) the mix changes (L4).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
