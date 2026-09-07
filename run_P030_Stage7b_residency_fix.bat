@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P030_Stage7b_residency_fix.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage7 tried to measure deployment residency and did not. The batch
REM     omitted --drop-latent, and the LUT switch lives inside that block, so
REM     --lut never ran. Exit code 0, three tables, two verdict sections, and
REM     the one number we asked for was missing. See result 014 s17.
REM
REM     Every 32 and 40 MiB budget decision we have rests on the formula
REM     9.0 + 1.585 x L. It has never been checked against the canonical tool.
REM
REM   READ IN THIS ORDER
REM     1. the line "LUT residency (codes + alpha)". If it is absent the LUT
REM        path did NOT run again and everything below it is the wrong number.
REM     2. max abs dlogit must be non-zero. LUT re-estimates per-row alpha, so
REM        zero means the switch did not happen. Do not read it as quality.
REM     3. add LUT residency + other + KV and compare with 9.0 + 1.585 x L.
REM        Prediction: within 5 percent. Hand estimate 27.8 / 30.9 / 34.1 MiB.
REM     4. KV entries must be visits / cla_group: 6 / 7 / 8 for the three
REM        no-recursion shapes and 10 for d12_cla2_r20.
REM
REM   NO TRAINING. NO GPU. COST: about 0.3h.   PLAN: test_plan/P030 Stage7b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P030_stage7b_residency_fix --note "[1/4] depth 12 no recursion - canonical deployment residency with drop-latent"
python scripts\runlog.py --name P030_stage7b_residency_fix -- python scripts\mem_runtime.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_norecur --device cpu --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] arm 1 failed - continuing

python scripts\runlog.py --name P030_stage7b_residency_fix --note "[2/4] depth 14 - preset m100s10"
python scripts\runlog.py --name P030_stage7b_residency_fix -- python scripts\mem_runtime.py --preset m100s10 --data ko-en --tokens 300M --models d14_cla2_norecur --device cpu --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] arm 2 failed - continuing

python scripts\runlog.py --name P030_stage7b_residency_fix --note "[3/4] depth 16 plus the muon shape - optimizer must not change the number"
python scripts\runlog.py --name P030_stage7b_residency_fix -- python scripts\mem_runtime.py --preset m100s12 --data ko-en --tokens 300M --models d16_cla2_norecur d16_cla2_norecur_muon15 --device cpu --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] arm 3 failed - continuing

python scripts\runlog.py --name P030_stage7b_residency_fix --note "[4/4] the recursive control - KV entries should be 10, not 6"
python scripts\runlog.py --name P030_stage7b_residency_fix -- python scripts\mem_runtime.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_cla2_r20_muon15 --device cpu --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] arm 4 failed - continuing

python scripts\runlog.py --name P030_stage7b_residency_fix --note "DONE. If the LUT residency line is missing the run failed even at exit 0."

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
