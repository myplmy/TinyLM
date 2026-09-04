@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P086_Stage6_lrm_values.bat -- did the multipliers actually move?
REM ==========================================================================
REM
REM   WHY THIS EXISTS
REM     Stage2 concluded that per-layer scalars buy nothing on a dense body
REM     (delta -0.0005, well inside the ruler). That conclusion has one hole.
REM     params went up by exactly 24, which proves the parameters were BUILT.
REM     It does not prove they were TRAINED. The multipliers carry weight decay
REM     0.01 which pulls them back toward 1.0, so "no effect" and "never turned
REM     on" produce the same number.
REM
REM     Trap 37 has three known faces already. This is the fourth:
REM       1 a field is recorded          is not   that path runs
REM       2 a file exists                is not   that file is imported
REM       3 a flag is in the parser      is not   that flag does anything
REM       4 a parameter was created      is not   that parameter moved
REM
REM   THE GATE
REM     max abs(s - 1) at least 0.01  pass. result 072 stands.
REM     1e-4 to 0.01             weak. look at whether WD 0.01 was too strong.
REM     below 1e-4               FAIL, exit 1. result 072 section 1 is withdrawn
REM                              and the finding becomes "LRM never turned on".
REM
REM   COST: no training, no GPU work beyond loading one checkpoint. about 0.1h.
REM   PLAN: test_plan/P086_tying-scale (Korean filename) Stage6
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P086_stage6_lrm_values --note "[1/2] main run - d12_cla2_r20_lrm"
python scripts\runlog.py --name P086_stage6_lrm_values -- python scripts\diag_lrm_values.py --tag d12_cla2_r20_lrm
if errorlevel 1 echo [WARN] main arm reported FAIL - that is the finding, continuing

python scripts\runlog.py --name P086_stage6_lrm_values --note "[2/2] probe - 250 steps. expected to move less."
python scripts\runlog.py --name P086_stage6_lrm_values -- python scripts\diag_lrm_values.py --tag d12_cla2_r20_lrm_probe
if errorlevel 1 echo [WARN] probe arm reported FAIL - continuing

echo.
python scripts\runlog.py --name P086_stage6_lrm_values --note "=================================================================" "READ IN THIS ORDER" "1. max abs(s-1) on the MAIN run. Under 1e-4 withdraws result 072." "2. compare main against probe. The probe ran 250 steps, the main 2289." "   If the main moved no more than the probe, the gradient is not arriving." "3. gate/up/down separately. silu is nonlinear so they need not agree." "4. this arm reads a checkpoint. It never writes one." "================================================================="

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
