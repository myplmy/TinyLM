@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P025B Stage0a - native 2:4 backend and same-session MLP speed gate
REM  COST: about 0.1h. GPU diagnostic only. No model or training checkpoint.
REM  Failure is a valid negative result; later acceleration stages stay closed.
REM ============================================================================

if not exist scripts\diag_sparse24_backend.py goto BADROOT
set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P025B_stage0a_sparse24_backend --note "[1/1] exact 2:4, sparse forward/input-grad, and speed gate"
python scripts\runlog.py --name P025B_stage0a_sparse24_backend -- python scripts\diag_sparse24_backend.py
if errorlevel 1 goto GATEFAIL
python scripts\runlog.py --name P025B_stage0a_sparse24_backend --note "GATE PASS: whole-step, weight-gradient, TLinear, quality, and VRAM remain NOT_RUN."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:GATEFAIL
echo [STOP] P025B Stage0a was negative or unsupported. Do not open acceleration stages.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
