@echo off
setlocal
REM P104A Stage2B real M5 Windows side. Same pinned d14 dense checkpoint as WSL.
REM No retraining: fixed ko-en 600M validation and one in-memory SGD step.
REM Expected up to 1.0 h on a single GPU. Run from the TinyLM repository root.
REM This output is write-once. A dependent failure stops this batch.
if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist scripts\diag_m5_real_bridge.py goto BADROOT
set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P104A_Stage2B_m5_real_windows --note "P104A same real d14 checkpoint Windows capture; no training checkpoint write."
if errorlevel 1 goto ERROR
python scripts\runlog.py --name P104A_Stage2B_m5_real_windows -- python -B -X utf8 scripts\check_m5_real_bridge.py --self-test
if errorlevel 1 goto ERROR
python scripts\runlog.py --name P104A_Stage2B_m5_real_windows -- python -B -X utf8 scripts\diag_m5_real_bridge.py --platform windows --out runs/bench/p104a_m5_real_windows.json --check-only
if errorlevel 1 goto ERROR
python scripts\runlog.py --name P104A_Stage2B_m5_real_windows -- python -B -X utf8 scripts\diag_m5_real_bridge.py --platform windows --out runs/bench/p104a_m5_real_windows.json
if errorlevel 1 goto ERROR
python scripts\runlog.py --name P104A_Stage2B_m5_real_windows --note "Read the Windows JSON and run the WSL companion on the identical checkpoint before comparing CE and gradient; wall ratios are descriptive."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [FAIL] Start from the TinyLM repository folder. Nothing ran.
if not defined TL_NOPAUSE pause
exit /b 9

:ERROR
echo [FAIL] P104A real Windows collection stopped. Preserve the runlog and do not overwrite the JSON.
if not defined TL_NOPAUSE pause
exit /b 1
