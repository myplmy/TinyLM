@echo off
REM ===== P022 stage-0 GATE : FP8(E4M3) _scaled_mm vs bf16 F.linear, PURE GEMM microbench =====
REM
REM WHY THIS IS A GATE, NOT AN EXPERIMENT:
REM   FP8 is the only candidate that could give a REAL GPU training speedup on Ada (sm_89).
REM   But our GEMMs are small (d=768, ffn=2048, M=8192) and FP8 needs per-tensor cast+scale
REM   every step. So we measure the CEILING first (pure matmul, no cast overhead in the loop).
REM   If the ceiling is not over 1.2-1.3x, end-to-end training can only be worse: drop P022.
REM
REM COST: seconds. No training, no checkpoint, no VRAM pressure. Safe to run anytime.
REM
REM NOTE: no --compile anywhere (this is raw torch), and NOTHING is written to runs/.
REM       Paste the whole table back into test_result as the P022 stage-0 record.

echo ============================================================
echo [P022-0] FP8 vs bf16 pure-GEMM microbench
echo ============================================================
echo.
echo [env] reporting torch / GPU capability first
python -c "import torch;print('torch',torch.__version__,'cuda',torch.version.cuda);print('gpu',torch.cuda.get_device_name() if torch.cuda.is_available() else 'NO CUDA');print('cap',torch.cuda.get_device_capability() if torch.cuda.is_available() else '-');print('has float8_e4m3fn',hasattr(torch,'float8_e4m3fn'));print('has _scaled_mm',hasattr(torch,'_scaled_mm'))"
if errorlevel 1 echo [WARN] env probe failed - continuing anyway

echo.
echo [1/1] running scripts\bench_fp8_gemm.py
python scripts\bench_fp8_gemm.py
if errorlevel 1 goto SOFTFAIL

echo.
echo ============================================================
echo GATE DECISION RULE (read the speedup column above):
echo   - mostly ^>1.30x   : PROCEED to P022 stage-1 (torchao float8 linear on MLP only)
echo   - 1.15x ^~ 1.30x  : MARGINAL. cast/scale overhead will eat it. record and defer.
echo   - ^<1.15x          : DROP P022. record as a negative result and move on.
echo.
echo REMEMBER: the number above is an UPPER BOUND. Real training adds per-step
echo           activation cast + amax/scale elementwise work, so end-to-end is worse.
echo.
echo ALSO CHECK: sm_89 requires CUDA 12.x and a torch build with _scaled_mm.
echo             If _scaled_mm is missing or every row failed, that is an ENV result,
echo             not a hardware result - record it as such before dropping P022.
echo ============================================================
echo done.
pause
exit /b 0

:SOFTFAIL
echo.
echo [WARN] bench_fp8_gemm.py exited with an error.
echo        This is itself a valid stage-0 outcome (no FP8 support in this build).
echo        Copy the traceback above into test_result and record P022 as env-blocked.
pause
exit /b 0
