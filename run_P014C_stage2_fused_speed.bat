@echo off
REM =============================================================================
REM  P014C stage 2  -  does fused per-row int8 beat the unpack cache?
REM  CPU decode, no training, minutes.
REM
REM  THE BOTTLENECK
REM    int8 storage halves resident memory but forward has to rebuild fp32 every
REM    time. Result 014 s11.4: about 2.1 to 2.2 ms per layer, 20 layers, roughly
REM    43 ms per token. That is why int8 is -62 to -67 percent on CPU.
REM
REM  TWO ANSWERS
REM    unpack cache  (P034 stage 3C, done)   19.07 tok/s
REM    fused mpGEMM  (this stage)            torch._weight_int8pack_mm, no rebuild
REM
REM  ***GATE G2 = must beat 19.07 tok/s.***
REM  If it does not, this path is closed and the unpack cache is the answer.
REM  Something worse than what already exists is not worth carrying.
REM
REM  !! WHAT THIS DOES NOT MEASURE
REM    Quality. The script re-quantises a g128 checkpoint to per-row, so its
REM    outputs differ from the trained model. Speed only. The quality price of
REM    per-row was already measured: +0.0050 to +0.0063 bpb, below the 0.008
REM    resolution (result 028). Retraining at per-row is stage 3, not this.
REM
REM  !! RUN ALONE. Result 016 s12.5. All three conditions are timed inside one
REM    process on purpose - cross-session drift is 7.5 percent (result 037).
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

set TL_OUTDIR=smoketest_logs

echo.
echo.
python scripts\runlog.py --name P014C_stage2_fused --note "=============================================================================" "P014C stage 2   CPU decode speed gate   G2 = 19.07 tok/s" "Close other CPU-heavy programs before continuing." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P014C_stage2_fused --note "[P014C stage 2] fused per-row int8 vs unpack cache, CPU batch-1 decode. Gate G2 = 19.07 tok/s (result 016 s15)."
python scripts\runlog.py --name P014C_stage2_fused -- python scripts\bench_fused_int8.py --models mC_wsd --device cpu
if errorlevel 1 goto GATEMISS

echo.
echo.
python scripts\runlog.py --name P014C_stage2_fused --note "=============================================================================" "G2 passed. The fused path removes the fp32 rebuild AND is faster than the" "unpack cache. Next: stage 3 measures what per-row costs when TRAINED that" "way (--micro-group 0), which is the only honest quality number." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:GATEMISS
echo.
echo =============================================================================
echo  G2 not passed (or the run failed). Read the table above.
echo  If the fused path is simply slower, that is a RESULT, not a failure:
echo  record it, close the path, and keep the unpack cache. Do not retune it -
echo  result 016 s10 already says int8 is a last resort, not the default path.
echo =============================================================================
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
