@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P032_paired_eval.bat  --  P032 : deterministic full-val + paired compare
REM  Plan: test_plan\P032_...md    Roadmap: R6
REM =============================================================================
REM
REM THE PROBLEM
REM   Result 012 reported mA 3.7003 vs p6d 3.7045, a gap of 0.0042. Sigma is
REM   0.012 and the working resolution is 0.024. Confirming 0.0042 by comparing
REM   MEANS would take about 49 runs per arm - roughly 196 hours. The plan
REM   abandoned that route. This is the replacement, and it costs minutes.
REM
REM WHAT CHANGES
REM   1. Deterministic full-val. evaluate() samples 50 random crops out of the
REM      1.5M token val set, so the same checkpoint scores differently each call.
REM      Here val is walked end to end without overlap, so the eval sampling
REM      component of sigma becomes exactly ZERO.
REM   2. Paired per-crop differencing. Both models see the SAME crops, and we
REM      difference crop by crop. "Is this crop intrinsically hard" is common to
REM      both models and cancels.
REM
REM ***THE LIMIT THAT MUST GO IN THE RESULT DOCUMENT***
REM   Pairing removes EVAL noise only. TRAINING reproduction noise is untouched.
REM   So this can settle "these two CHECKPOINTS differ" and cannot settle
REM   "this ARCHITECTURE is better". The second claim still needs several seeds.
REM   Blurring the two would repeat result 015's error in a new costume.
REM
REM COST: minutes. No training. No GPU time to speak of.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P032] deterministic full-val + paired per-crop comparison
python scripts\runlog.py --name P032-paired --note "[P032] deterministic full-val + paired per-crop comparison"
echo =============================================================

echo.
echo [guard] scripts\paired_eval.py present
python scripts\runlog.py --name P032-paired --note "[guard] scripts\paired_eval.py present"
if not exist scripts\paired_eval.py goto NOSCRIPT

echo.
echo =============================================================
echo [1/3] GPU pass, bf16 autocast - fast, and the headline table
python scripts\runlog.py --name P032-paired --note "[1/3] GPU pass, bf16 autocast - fast, and the headline table"
echo =============================================================
python scripts\runlog.py --name P032-paired -- python scripts\paired_eval.py --models mA_g4s34_k4 mC_g8_k4 p6d --seq 1024 --micro-bs 8
if errorlevel 1 echo [WARN] cuda paired eval failed - continuing

echo.
echo =============================================================
echo [2/3] REPEAT the same command - determinism check
python scripts\runlog.py --name P032-paired --note "[2/3] REPEAT the same command - determinism check"
echo   If full-val is deterministic, both runs print IDENTICAL numbers. If they
echo   do not, the pairing rests on sand and nothing below it can be read.
echo =============================================================
python scripts\runlog.py --name P032-paired -- python scripts\paired_eval.py --models mA_g4s34_k4 mC_g8_k4 p6d --seq 1024 --micro-bs 8
if errorlevel 1 echo [WARN] repeat failed - continuing

echo.
echo =============================================================
echo [3/3] CPU pass, fp32 - removes bf16 ULP noise from the crop losses
python scripts\runlog.py --name P032-paired --note "[3/3] CPU pass, fp32 - removes bf16 ULP noise from the crop losses"
echo   Slower. Worth it because the difference we are chasing is 0.004.
echo =============================================================
python scripts\runlog.py --name P032-paired -- python scripts\paired_eval.py --models mA_g4s34_k4 p6d --seq 1024 --micro-bs 4 --device cpu
if errorlevel 1 echo [WARN] cpu paired eval failed - continuing

echo.
echo =================================================================
echo WHAT TO RECORD
echo   1. deterministic full-val per model (and that the repeat matched exactly)
echo   2. per pair: mean difference, SE, t, and the win rate over crops
echo   3. whether SE came out an order of magnitude below sigma = 0.012
echo   4. the cuda versus cpu numbers side by side
echo.
echo HOW TO ACT
echo   SE far below 0.012 and abs(t) over 2
echo       -^> these checkpoints are distinguishable. Record the SIGNED gap.
echo          Still not an architecture verdict - say so in the document.
echo   abs(t) under 2
echo       -^> not distinguishable even with eval noise removed. That is a strong
echo          statement: it means preserving BOTH candidates was correct.
echo   win rate near 50 percent with a nonzero mean
echo       -^> a few large crops carry the mean. Report that, not just the mean.
echo.
echo LIMITS: one seed per architecture / still this val set, so P037 data problems
echo   remain / crop boundaries cut context, equally for both models.
echo =================================================================
echo done.
pause
exit /b 0

:NOSCRIPT
echo.
echo =================================================================
echo [STOP] scripts\paired_eval.py is missing. Nothing was executed.
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
