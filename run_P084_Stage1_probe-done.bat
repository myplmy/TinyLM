@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P084_Stage1_probe.bat -- 250-step probe for --no-cla-edges
REM ==========================================================================
REM  
REM   WHAT
REM     P084 asks whether the CLA group should skip prelude and coda. Until
REM     2026-09-03 owner[i] = i - (i % cla_group) applied to EVERY layer, so the
REM     head and the tail shared K/V too - even though every other convention in
REM     this repo treats them as fully independent (no MLP tying, no recursion).
REM  
REM   WHY A PROBE FIRST
REM     Switching the flag changes the KV ENTRY COUNT. Arithmetic says 10 to 12
REM     entries, which is +1.5 MiB and puts d12 at about 32.2 MiB - just OVER the
REM     32 MiB budget. This 250-step run prints the real entry count and deploy_mb
REM     so we find out before spending 3.2 hours.
REM  
REM   READING THE OUTPUT
REM     1. the [P084] line: KV owner layers 10 to 12. If it does not print, the
REM        flag did not reach the model (trap 37).
REM     2. deploy_mb in runs/logs/*.json. Over 34 MiB means STOP - do not run Stage2.
REM     3. VRAM peak reserved, and ms/step spread.
REM     4. DO NOT read val. 250 steps says nothing about quality.
REM  
REM   COST: about 0.3h.   PLAN: test_plan/P084_*.md
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P084_stage1_probe --note "[1/1] d12 + no-cla-edges, 250-step probe"
python scripts\runlog.py --name P084_stage1_probe -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --no-cla-edges --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2e_r20_probe
if errorlevel 1 echo [WARN] arm failed - continuing


echo.
python scripts\runlog.py --name P084_stage1_probe --note "=================================================================" "READ IN THIS ORDER" "1. the [P084] line - owner layers must go 10 -> 12. No line = flag did not land." "2. deploy_mb in the json. Over 34 MiB -^> STOP, do not start Stage2." "3. VRAM peak and ms/step spread." "4. DO NOT read val. 250 steps carries no quality signal." "================================================================="

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
