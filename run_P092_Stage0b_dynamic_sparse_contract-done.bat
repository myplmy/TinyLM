@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P092 Stage0b - masked forward/backward and topology accounting contract
REM  COST: under 0.1h. CUDA diagnostic only. No training or checkpoints.
REM  Dense tensor plus mask is not counted as sparse compute acceleration.
REM ============================================================================

if not exist scripts\diag_dynamic_sparse_contract.py goto BADROOT
set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P092_stage0b_dynamic_sparse_contract --note "[1/1] mask STE, inactive regrowth score, and birth-death conservation"
python scripts\runlog.py --name P092_stage0b_dynamic_sparse_contract -- python scripts\diag_dynamic_sparse_contract.py --device cuda
if errorlevel 1 goto GATEFAIL
python scripts\runlog.py --name P092_stage0b_dynamic_sparse_contract --note "GATE PASS: TLinear and trainer integration may be designed; Stage1 remains gated."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:GATEFAIL
echo [STOP] P092 Stage0b contract failed. Do not open Stage1.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
