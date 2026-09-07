@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage8_bench_final.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     After this queue there are six deployment candidates. Score them on the SAME day
REM     with the SAME items, and measure tok/s on the same day too.
REM     Session drift on ms/step is 7.5 percent (baseline rule 19) - never mix days.
REM
REM   READ IN THIS ORDER
REM     1. gold CE is expected to separate and accuracy is expected not to, within a family.
REM     2. That has been 5 out of 5. A counterexample would be the headline.
REM     3. The predicted 15.6 tok/s for depth 18 is a MODEL - this batch measures it.
REM     4. If depth 18 comes in under 15 tok/s it is not a deployment candidate.
REM     5. Deployment residency comes from mem_runtime --lut only, not bench_infer's column.
REM
REM   PREREQUISITE
REM     P062 Stage12 and Stage14 make the tags this batch scores.
REM
REM   COST: about 1.5h, no training.   PLAN: test_plan/P085 Stage8
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage8_bench_final --note "[1/5] korean held-out on the new no-recursion candidates"
timeout /t 15 /nobreak
python scripts\runlog.py --name P085_stage8_bench_final -- python scripts\eval_bench_suite.py --task stage1_heldout --n 400 --preset m100s12 --models d16_cla2_norecur d16_cla2_norecur_muon15 d18_cla2_norecur_muon15 --wandb
if errorlevel 1 echo [WARN] arm 1 failed - continuing

python scripts\runlog.py --name P085_stage8_bench_final --note "[2/5] arc easy on the same three"
timeout /t 15 /nobreak
python scripts\runlog.py --name P085_stage8_bench_final -- python scripts\eval_bench_suite.py --task arc_easy --n 400 --preset m100s12 --models d16_cla2_norecur d16_cla2_norecur_muon15 d18_cla2_norecur_muon15 --wandb
if errorlevel 1 echo [WARN] arm 2 failed - continuing

python scripts\runlog.py --name P085_stage8_bench_final --note "[3/5] kobest hellaswag on the same three"
timeout /t 15 /nobreak
python scripts\runlog.py --name P085_stage8_bench_final -- python scripts\eval_bench_suite.py --task kobest_hellaswag --n 400 --preset m100s12 --models d16_cla2_norecur d16_cla2_norecur_muon15 d18_cla2_norecur_muon15 --wandb
if errorlevel 1 echo [WARN] arm 3 failed - continuing

python scripts\runlog.py --name P085_stage8_bench_final --note "[4/5] single thread tok/s for depth 18 - does the 15.6 prediction hold"
timeout /t 15 /nobreak
python scripts\runlog.py --name P085_stage8_bench_final -- python scripts\bench_infer.py --models d18_cla2_norecur --preset m100s14 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] arm 4 failed - continuing

python scripts\runlog.py --name P085_stage8_bench_final --note "[5/5] deployment residency for depth 18 - the canonical tool"
timeout /t 15 /nobreak
python scripts\runlog.py --name P085_stage8_bench_final -- python scripts\mem_runtime.py --preset m100s14 --data ko-en --tokens 300M --models d18_cla2_norecur --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] arm 5 failed - continuing

python scripts\runlog.py --name P085_stage8_bench_final --note "DONE. Deployment residency comes from mem_runtime --lut only, not bench_infer's column."

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
