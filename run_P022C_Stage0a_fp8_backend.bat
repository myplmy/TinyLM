@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P022C Stage0a - strict CUDA FP8 backend feasibility on TinyLM shapes
REM  COST: about 0.1h. GPU diagnostic only. No model or training checkpoint.
REM  A successful cast is insufficient; torch._scaled_mm must execute on CUDA.
REM ============================================================================

if not exist scripts\diag_fp8_backend_gate.py goto BADROOT
if not exist scripts\bench_fp8_gemm.py goto BADROOT
set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P022C_stage0a_fp8_backend --note "[1/2] strict CUDA scaled-mm feasibility"
python scripts\runlog.py --name P022C_stage0a_fp8_backend -- python scripts\diag_fp8_backend_gate.py
if errorlevel 1 goto GATEFAIL

python scripts\runlog.py --name P022C_stage0a_fp8_backend --note "[2/2] same-session pure GEMM upper bound"
python scripts\runlog.py --name P022C_stage0a_fp8_backend -- python scripts\bench_fp8_gemm.py
if errorlevel 1 goto GATEFAIL
python scripts\runlog.py --name P022C_stage0a_fp8_backend --note "GATE PASS means backend feasibility only. Scaling, backward, whole-step speed, and quality remain NOT_RUN."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:GATEFAIL
echo [STOP] P022C Stage0a backend gate failed. Do not open later compute stages.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
