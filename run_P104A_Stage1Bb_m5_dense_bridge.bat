@echo off
setlocal enabledelayedexpansion
REM P104A Stage1Bb: Windows drive/UNC path fix for tiny dense M5 bridge.
REM About 0.1 h GPU on Windows. No model-quality or speed adoption.
REM The old Stage1B failure log is preserved. Output is write-once.
if not exist run100m.py goto BADROOT
set PYTHONIOENCODING=utf-8
python scripts/runlog.py --num 095 --name P104A_Stage1Bb_m5_dense_bridge --note "Windows drive/UNC path alias fixed by root-relative code keys. Verify pure path contract before the same tiny checkpoint and seed104 GPU gate."
python scripts/runlog.py --num 095 --name P104A_Stage1Bb_m5_dense_bridge -- python -B -X utf8 scripts/check_m5_dense_bridge.py --self-test
set TL_RC=!errorlevel!
if not "!TL_RC!"=="0" goto ERROR
python scripts/runlog.py --num 095 --name P104A_Stage1Bb_m5_dense_bridge -- python -B -X utf8 scripts/diag_m5_dense_bridge.py --platform windows --out runs/bench/p104a_m5_windows.json
set TL_RC=!errorlevel!
if not "!TL_RC!"=="0" goto ERROR
python scripts/runlog.py --num 095 --name P104A_Stage1Bb_m5_dense_bridge --note "Run WSL Stage1W only after this Windows JSON exists; compare checkpoint/code/input SHA and one-step CE. Full M5 quality NOT_RUN."
if not defined TL_NOPAUSE pause
exit /b 0
:BADROOT
echo [STOP] run from the TinyLM repository root
if not defined TL_NOPAUSE pause
exit /b 9
:ERROR
echo [FAIL] Windows bridge returned an error; inspect its runlog
if not defined TL_NOPAUSE pause
exit /b !TL_RC!
