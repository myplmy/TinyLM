@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P030_Stage7_norecur_residency.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     The residency column in result 014 section 16.4 is a FORMULA, not a measurement.
REM     Baseline rule 21 says deployment residency is quoted from mem_runtime --lut only.
REM     We wrote the rule and then did not follow it. This costs 0.2h and no training.
REM
REM   READ IN THIS ORDER
REM     1. mem_runtime numbers vs the formula 9.0 + 1.585 x L. Over 5 percent means the
REM     2. formula is wrong and the 32/40 depth caps 14.5 and 19.6 all move.
REM     3. bench_infer confirms the optimiser does not change speed at fixed shape.
REM     4. Read the LUT column, not bench_infer's own residency column.
REM
REM   COST: about 0.2h, no training.   PLAN: test_plan/P030 stage7
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P030_stage7_norecur_residency --note "[1/3] d12 d14 d16 no-recursion deployment residency - the canonical tool"
timeout /t 15 /nobreak
python scripts\runlog.py --name P030_stage7_norecur_residency -- python scripts\mem_runtime.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_norecur --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] arm 1 failed - continuing

python scripts\runlog.py --name P030_stage7_norecur_residency --note "[2/3] depth 14 - preset m100s10"
timeout /t 15 /nobreak
python scripts\runlog.py --name P030_stage7_norecur_residency -- python scripts\mem_runtime.py --preset m100s10 --data ko-en --tokens 300M --models d14_cla2_norecur --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] arm 2 failed - continuing

python scripts\runlog.py --name P030_stage7_norecur_residency --note "[3/3] depth 16 plus the muon shape - same architecture, so same number expected"
timeout /t 15 /nobreak
python scripts\runlog.py --name P030_stage7_norecur_residency -- python scripts\mem_runtime.py --preset m100s12 --data ko-en --tokens 300M --models d16_cla2_norecur d16_cla2_norecur_muon15 --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] arm 3 failed - continuing

python scripts\runlog.py --name P030_stage7_norecur_residency --note "DONE. Read the LUT column, not bench_infer's own residency column."

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
