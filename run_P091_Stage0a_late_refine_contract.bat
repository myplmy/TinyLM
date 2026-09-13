@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P091 Stage0a - unique-candidate and foldable latent-expansion contract
REM  COST: under 0.1h. CPU diagnostic only. No training or checkpoints.
REM  Later controller and trainer wiring stay gated on this result.
REM ============================================================================

if not exist scripts\diag_late_refine_contract.py goto BADROOT
set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P091_stage0a_late_refine_contract --note "[1/1] default-off, unique-module, and exact fold contract"
python scripts\runlog.py --name P091_stage0a_late_refine_contract -- python scripts\diag_late_refine_contract.py --device cpu
if errorlevel 1 goto GATEFAIL
python scripts\runlog.py --name P091_stage0a_late_refine_contract --note "GATE PASS: design actual TLinear wiring next; Stage1 remains gated."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:GATEFAIL
echo [STOP] P091 Stage0a contract failed. Do not implement or run later stages.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
