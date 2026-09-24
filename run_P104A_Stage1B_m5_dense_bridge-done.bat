@echo off
setlocal enabledelayedexpansion
REM P104A Stage1B: small dense bridge. About 0.1 h GPU on Windows.
REM Run before Stage1W WSL in the same repository and Python environment.
REM Same tiny checkpoint, source SHA and input are verified by the comparator.
REM No quality or platform speed adoption from this one-step synthetic control.
if not exist run100m.py goto BADROOT
set PYTHONIOENCODING=utf-8
python scripts/runlog.py --num 095 --name P104A_Stage1B_m5_dense_bridge --note "Use the same tiny dense checkpoint in WSL. This is a one-step functional bridge, not full M5 quality."
python scripts/runlog.py --num 095 --name P104A_Stage1B_m5_dense_bridge -- python -B -X utf8 scripts/diag_m5_dense_bridge.py
set TL_RC=!errorlevel!
if not "!TL_RC!"=="0" goto ERROR
python scripts/runlog.py --num 095 --name P104A_Stage1B_m5_dense_bridge --note "Now run the WSL Stage1W script in the same code tree, then compare both JSON files."
if not defined TL_NOPAUSE pause
exit /b 0
:BADROOT
echo [STOP] run from the TinyLM repository root
if not defined TL_NOPAUSE pause
exit /b 9
:ERROR
echo [FAIL] Windows bridge returned an error, inspect its runlog
if not defined TL_NOPAUSE pause
exit /b !TL_RC!
