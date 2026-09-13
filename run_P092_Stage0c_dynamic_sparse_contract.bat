@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P092 Stage0c - rerun topology contract after repository import-path fix
REM  COST: under 0.1h. CUDA diagnostic only. No training or checkpoints.
REM  Stage0b ended before the scientific gate; this is the first valid attempt.
REM ============================================================================

if not exist scripts\diag_dynamic_sparse_contract.py goto BADROOT
set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P092_stage0c_dynamic_sparse_contract --note "[1/1] import-fixed mask STE, inactive regrowth score, and birth-death conservation"
python scripts\runlog.py --name P092_stage0c_dynamic_sparse_contract -- python scripts\diag_dynamic_sparse_contract.py --device cuda
if errorlevel 1 goto GATEFAIL
python scripts\runlog.py --name P092_stage0c_dynamic_sparse_contract --note "GATE PASS: TLinear and trainer integration may be designed; Stage1 remains gated."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:GATEFAIL
echo [STOP] P092 Stage0c contract failed. Do not open Stage1.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
