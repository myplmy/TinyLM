@echo off
REM ===== LOGGING (added 2026-07-31) =====
REM   Every python command below is run through scripts\runlog.py, which prints to the
REM   console in real time AND appends to test_result\log_YYYYMMDD_NAME.txt line by line,
REM   flushing and fsync-ing as it goes. If this batch dies halfway, or the machine loses
REM   power, everything up to the last couple of seconds is already on disk.
REM   Losing the log of a long run costs the whole run, so this is not optional.
REM   Exit codes pass through unchanged, so every `if errorlevel` below still works.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ===== P036 stage 1 : does WEIGHT TRAPPING exist at OUR scale =====
REM   Plan: test_plan\P036   Evidence: test_result\016 section 7.5 and 8.6
REM
REM ***** WHY THIS RUNS BEFORE ANY TRAINING *****
REM   The Sherry paper (arXiv 2601.07892 section 3.2) says applying 3:4 sparsity directly to
REM   ternary training triggers WEIGHT TRAPPING: the uniformly scattered zeros make the
REM   sparse matrix behave like a dense binary one, dL/dX becomes homogenised, gradient
REM   effective rank collapses (their Fig 4: ER under 750 with dimension 4096), and latent
REM   weights polarise into a binary-like state. Arenas is their fix, and WE DO NOT HAVE IT.
REM
REM   But the paper is 1B/3B parameters on 10B tokens. We are 132M on 300M tokens - 2.3
REM   tokens per parameter. IF THE MECHANISM IS NOT PRESENT AT OUR SCALE, THE FIX IS NOT
REM   NEEDED EITHER, and P036 stage 2 (about 4.5 hours of GPU) should not run.
REM   This batch answers that with existing checkpoints and almost no GPU.
REM
REM ***** WHAT IS MEASURED *****
REM   [1] latent weight polarisation - the "valley" fraction of abs(w) under 0.5 alpha.
REM       Polarisation empties the middle, so a SMALL number means polarised.
REM   [2] ternary occupancy of minus-alpha / zero / plus-alpha. Too few zeros means the
REM       model is not using the third state - that is the binary-like collapse.
REM   [3] gradient effective rank of dL/dX, the paper's central diagnostic.
REM       ER = exp(entropy of normalised singular values).
REM
REM   Read the MODEL-TO-MODEL comparison, not the absolute values. Our dimensions differ
REM   from the paper's, and ER is bounded by dimension.
REM
REM COST: 4 batches of 2x512 tokens forward+backward per model. Seconds of GPU.
REM ERRORLEVEL POLICY: nothing here is a hard stop.

echo ============================================================
echo [P036-1] weight trapping - does the mechanism exist at our scale
echo ============================================================

echo.
echo [guard] checking whether scripts\diag_trapping.py exists
if not exist scripts\diag_trapping.py goto NOTIMPL

echo.
echo ============================================================
echo [1/2] all three models - this is the comparison that decides
echo   mA_g4s34_k4 is the only 3:4 model. mC_g8_k4 is tied but NOT 3:4, so it separates
echo   "tying" from "3:4". p6d is the unquantised-structure control.
echo ============================================================
python scripts\runlog.py --name P036-stage1 -- python scripts\diag_trapping.py --models mA_g4s34_k4 mC_g8_k4 p6d --batches 4
if errorlevel 2 echo [WARN] some checkpoints missing - read which ones above
if errorlevel 1 echo [WARN] run reported a problem - continuing

echo.
echo ============================================================
echo [2/2] repeat with more batches - is the ER estimate stable
echo   ER comes from a finite gradient sample. If 4 and 12 batches disagree by a lot,
echo   the number is noise and must not be used for a decision.
echo ============================================================
python scripts\runlog.py --name P036-stage1 -- python scripts\diag_trapping.py --models mA_g4s34_k4 mC_g8_k4 --batches 12
if errorlevel 1 echo [WARN] stability pass failed - continuing

echo.
echo ================================================================
echo WHAT TO RECORD
echo   1. per model: valley fraction, zero occupancy, mean ER, ER over dimension
echo   2. the 3:4 versus non-3:4 comparison block at the end
echo   3. whether 4-batch and 12-batch ER agree (stability)
echo.
echo JUDGEMENT
echo   valley much smaller AND ER much lower on mA only
echo       TRAPPING IS REAL at our scale. Run P036 stage 2 (Arenas on/off, about 4.5h).
echo       The quality cost measured in result 008 was then partly an implementation gap.
echo   only one of the two indicators points at mA
echo       WEAK evidence. Ask before spending 4.5 hours.
echo   all three models look alike
echo       NOT PRESENT at our scale. Do not run stage 2. The 3:4 quality cost in result 008
echo       is the structural constraint itself, and that CLOSES the question.
echo   4-batch and 12-batch ER disagree badly
echo       the estimate is unusable. Raise --batches until it settles before judging.
echo.
echo LIMITS: three checkpoints that differ in MORE than 3:4 (g4 vs g8 too), so attribution
echo   to 3:4 alone is not clean here - stage 2 is what makes that comparison properly, by
echo   toggling only Arenas on identical conditions. ER is a finite sample. The 0.5 alpha
echo   valley threshold is ours, not the paper's.
echo ================================================================
echo done.
pause
exit /b 0

:NOTIMPL
echo.
echo ================================================================
echo [STOP] scripts\diag_trapping.py is missing.
echo   Nothing was measured. No files were written.
echo ================================================================
pause
exit /b 3

:BADROOT
echo.
echo [STOP] could not locate the repo root (run100m.py not found). Nothing was executed.
pause
exit /b 9
