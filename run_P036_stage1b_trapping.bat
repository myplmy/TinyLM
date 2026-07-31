@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P036_stage1b_trapping.bat  --  P036 STAGE 1B : redo stage 1 properly
REM  Plan: test_plan\P036_...md    Roadmap: R4 (repeat)   Prior: result 019
REM =============================================================================
REM
REM WHY A REPEAT
REM   Stage 1 (result 019) did NOT produce the comparison it was designed to make:
REM     1. the dense control p6d CRASHED - torch.quantile refuses inputs above
REM        2^24 elements and dense accumulates about 30M samples. So the verdict
REM        rested on two TIED models only, which is exactly the confound the
REM        control existed to remove. Fixed in diag_trapping.py.
REM     2. the summary compared RAW mean ER across models, but the layer picker
REM        strides by TLinear count, so g4 and g8 sampled DIFFERENT layer shapes.
REM        Averaging a 2048-dim layer against a 768-dim one is not a comparison.
REM        Now reports ER over dimension plus a shape-matched table.
REM     3. the "zero occupancy" indicator read 25.00 percent for the 3:4 model.
REM        That is not a measurement - 3:4 FORCES exactly one zero in four. Using
REM        it as evidence is circular. It is now labelled as such.
REM
REM WHAT THIS DECIDES
REM   Whether weight trapping (arXiv:2601.07892) is observable at OUR scale.
REM   If yes, the 3:4 quality cost in result 008 is partly an implementation gap
REM   (we never built Arenas) and stage 2 is worth about 4.5 GPU hours.
REM   If no, that cost is the structural constraint itself and the question CLOSES.
REM
REM COST: seconds of GPU. No training.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P036-1B] weight trapping, with the dense control restored
echo =============================================================

echo.
echo [guard] scripts\diag_trapping.py present
if not exist scripts\diag_trapping.py goto NOSCRIPT

echo.
echo =============================================================
echo [1/2] all three models - the dense control is the point of this rerun
echo =============================================================
python scripts\runlog.py --name P036-stage1b -- python scripts\diag_trapping.py --models mA_g4s34_k4 mC_g8_k4 p6d --batches 4
if errorlevel 1 echo [WARN] run reported a problem - continuing

echo.
echo =============================================================
echo [2/2] more batches - is the ER estimate stable
echo   Stage 1 already showed 4 vs 12 agreeing to about 1 percent, so this is a
echo   confirmation, not a discovery. If it disagrees NOW, suspect the fix.
echo =============================================================
python scripts\runlog.py --name P036-stage1b -- python scripts\diag_trapping.py --models mA_g4s34_k4 mC_g8_k4 p6d --batches 12
if errorlevel 1 echo [WARN] run reported a problem - continuing

echo.
echo =================================================================
echo WHAT TO RECORD
echo   1. per model: valley fraction, mean ER over dimension, and the
echo      SHAPE-MATCHED table (that table is the only valid cross-model read)
echo   2. whether p6d completed this time
echo   3. 4-batch versus 12-batch agreement
echo.
echo VERDICT
echo   valley smaller AND ER/dim lower on mA only, with dense in between
echo       -^> trapping is real here. Run P036 stage 0 (implement Arenas), then
echo          stage 2 via run_P036_stage2_arenas.bat
echo   only one indicator points at mA
echo       -^> weak. Decide explicitly before spending 4.5 GPU hours.
echo   all three alike
echo       -^> not present at our scale. Do NOT run stage 2. Record that the 3:4
echo          quality cost is structural and CLOSE the question.
echo.
echo LIMITS: three checkpoints differing in more than 3:4 (g4 vs g8 as well), so
echo   attribution to 3:4 alone is still not clean - only stage 2 makes that
echo   comparison properly. ER is a finite gradient sample. The 0.5 alpha valley
echo   threshold is ours, not the paper's. Zero occupancy is NOT an indicator.
echo =================================================================
echo done.
pause
exit /b 0

:NOSCRIPT
echo.
echo =================================================================
echo [STOP] scripts\diag_trapping.py is missing. Nothing was executed.
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
