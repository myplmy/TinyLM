@echo off
setlocal
REM PM001 Stage0 - strict Triton environment and implementation contract. USER RUN ONLY.
REM Synthetic tensors only. No training, checkpoint, or dataset access.

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage0_triton_fp32 --note "Strict backend: import, compile, launch, telemetry, values and gradients. No fallback allowed."
python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage0_triton_fp32 -- python scripts\diag_pm001_ternary_triton.py --device cuda --dtype fp32
if errorlevel 1 goto CONTRACTFAIL

python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage0_triton_bf16 --note "Training-like bf16 activation contract. No fallback allowed."
python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage0_triton_bf16 -- python scripts\diag_pm001_ternary_triton.py --device cuda --dtype bf16
if errorlevel 1 goto CONTRACTFAIL

python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage0_triton_contract --note "STAGE0 PASS. Triton ran in this interpreter. This does not prove speedup."
goto DONE

:CONTRACTFAIL
python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage0_triton_contract --note "STAGE0 FAIL. Read failure stage/category; do not classify a fallback as Triton success."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 1

:PREFLIGHTFAIL
echo.
echo [STOP] moonshot branch or namespace preflight failed. Nothing was run.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo.
echo [STOP] run this from the repo root or moonshot_batch folder.
if not defined TL_NOPAUSE pause
exit /b 9

:DONE
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0
