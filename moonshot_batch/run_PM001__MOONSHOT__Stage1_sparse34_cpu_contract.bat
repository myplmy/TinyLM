@echo off
setlocal enabledelayedexpansion
REM PM001 Stage1 - build and validate the native 3:4 CPU LUT kernel. USER RUN ONLY.
REM Synthetic tensors only. The first call compiles a local PyTorch C++ extension.

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

set PYTHONIOENCODING=utf-8
set "TORCH_EXTENSIONS_DIR=!CD!\runs\cpp_extensions\pm001"
set "TINYLM_S34_BUILD_VERBOSE=1"

python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage1_sparse34_cpu_contract --note "Build time is recorded but excluded from latency. Native failures never fall back."
python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage1_sparse34_cpu_contract -- python scripts\diag_pm001_sparse34_cpu_lut.py --dim 256 --out 128 --batch 4 --group 128 --verbose-build
if errorlevel 1 goto CONTRACTFAIL

python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage1_sparse34_cpu_contract --note "STAGE1 PASS. Correctness and wiring only; speed remains unproven until Stage2."
goto DONE

:CONTRACTFAIL
python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage1_sparse34_cpu_contract --note "STAGE1 FAIL. Separate toolchain failure from numerical or wiring failure. Do not run Stage2."
set PYTHONIOENCODING=
set TORCH_EXTENSIONS_DIR=
set TINYLM_S34_BUILD_VERBOSE=
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
set TORCH_EXTENSIONS_DIR=
set TINYLM_S34_BUILD_VERBOSE=
echo.
echo VERDICT: PASS means build, numerical contract, and packed TLinear wiring only.
echo It does not prove speed. Run Stage2 next and compare every reported shape.
if not defined TL_NOPAUSE pause
exit /b 0
