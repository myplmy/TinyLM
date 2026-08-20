@echo off
REM =============================================================================
REM  P014C stage 2b  -  WHY is the fused int8 path 6.5x slower?
REM                     (NO TRAINING, NO MODEL, seconds, CPU)
REM
REM  WHY 2b
REM    Stage 2 measured 2.91 tok/s against a gate of 19.07 and a same-run unpack
REM    cache of 24.42. Result 028 s13 showed by arithmetic that the effective
REM    rate is about 0.72 GFLOP/s, which is single-thread scalar territory on an
REM    8-thread CPU, and that it is NOT bandwidth bound (160 MB/s would be absurd).
REM    But WHICH condition sends it down that path was left as four hypotheses:
REM      dtype (fp32 vs bf16) / M=1 decode / thread count / non-contiguous B
REM    All four are measurable on the OPERATOR ALONE in seconds. No model, no
REM    checkpoint, no training. That is what this does.
REM
REM  !! WHAT IT CANNOT DECIDE
REM    Whether to adopt --fused-int8. Stage 2 already answered that: no.
REM    This fills in WHY, and if the cause is something we control (dtype,
REM    contiguity) then a one-line fix plus a re-measure is far cheaper than the
REM    3.5 hour retrain that stage 3 would have needed.
REM
REM  !! AND ONE THING IT CANNOT FIX EITHER WAY
REM    _weight_int8pack_mm is an INT8 operator, not a ternary one. It does an
REM    8-bit multiply and ignores the fact that our values are only -1, 0, +1.
REM    The real win is LUT mpGEMM (T-MAC, bitnet.cpp I2_S), which is P014 plan
REM    A/B and has never been started. See docs/methods/02_memory.md s M.3.3.
REM
REM  COST: seconds. CPU only. Safe to run any time.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P014C_stage2b_paths --note "=============================================================================" "P014C stage 2b   why is fused int8 slow   seconds   NO TRAINING NO MODEL" "Four hypotheses: dtype, M=1, threads, contiguity. All measurable on the op." "Reference: stage 2 measured fused 2.91 vs unpack cache 24.42 tok/s (8.4x)." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P014C_stage2b_paths --note "[1/1] operator matrix - our three layer shapes x M in 1,8,64 x fp32,bf16 x full,1 thread"
python scripts\runlog.py --name P014C_stage2b_paths -- python scripts\diag_int8mm_paths.py --iters 30
if errorlevel 1 echo [WARN] probe failed - continuing

echo.
echo.
python scripts\runlog.py --name P014C_stage2b_paths --note "=============================================================================" "READ" "1. the verdict block first - does ANY combination beat the dequant matmul?" "2. if yes, note which dtype / M / thread count, and compare it to what" "   _fused_int8_linear actually passes today (fp32 activations, M=1, w8 not" "   made contiguous). That gap is the fix." "3. if no, P014C plan C stays closed and the axis moves to LUT kernels." "4. the ratio here should be the same order as the 8.4x measured end to end." "   If it is not, the model-level slowdown has another source too." "REMINDER: this operator is int8, not ternary. Even a win here is not the win." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
