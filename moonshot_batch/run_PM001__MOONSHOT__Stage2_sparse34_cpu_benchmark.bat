@echo off
setlocal enabledelayedexpansion
REM PM001 Stage2 - representative CPU microbenchmark. USER RUN ONLY.
REM Run only after Stage1 PASS. Build/load time is excluded from measured calls.

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

set PYTHONIOENCODING=utf-8
set "TORCH_EXTENSIONS_DIR=!CD!\runs\cpp_extensions\pm001"

python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage2_sparse34_cpu_benchmark --note "Median CPU microbench: dense, generic g5 LUT, native 1.25bpw s34. Not end-to-end model proof."
python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage2_sparse34_cpu_benchmark -- python scripts\diag_pm001_sparse34_cpu_lut.py --benchmark --dim 256 --out 128 --batch 4 --group 128 --out-chunk 256 --iters 20
if errorlevel 1 goto BENCHFAIL

python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage2_sparse34_cpu_benchmark --note "STAGE2 COMPLETE. Interpret every shape; exit zero alone is not a speed verdict."
goto DONE

:BENCHFAIL
python scripts\runlog.py --outdir moonshot_result --name PM001__MOONSHOT__Stage2_sparse34_cpu_benchmark --note "STAGE2 FAILED its correctness/build precondition. Do not interpret partial timings."
set PYTHONIOENCODING=
set TORCH_EXTENSIONS_DIR=
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
echo.
echo VERDICT: exit zero means the measurements completed, not that native won.
echo Read native/dense and native/g5 for M=1 across all three shapes.
if not defined TL_NOPAUSE pause
exit /b 0
