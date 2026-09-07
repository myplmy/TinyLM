@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage8_speed_depth.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     The speed floor of 15 tok/s means at most 18 visits (result 014 s15.2).
REM     Without recursion visits equal layers, so residency is 9.0 + 1.585 x L:
REM       32 MiB gives L at most 14.5      40 MiB gives L at most 19.6
REM     Our depth presets were 8, 12, 16, 20 - there was no 14. m100s10 is new
REM     today and is exactly that point.
REM
REM   THREE ARMS
REM     d14_cla2_norecur      m100s10   14 layers   30.2 MiB   about 18.1 tok/s
REM     d16_cla2_norecur      m100s12   16 layers   34.4 MiB   about 16.0 tok/s
REM     d16_cla2_norecur_s2   seed replica - the family ruler on this shape
REM
REM   THE QUESTION: does d16 without recursion beat d12_cla2_r20 with it? The
REM     recursive winner is 3.55719 on log val but runs 14.32 tok/s and misses.
REM
REM   m100s10 IS BEING USED FOR THE FIRST TIME. --depth-init role is mandatory:
REM     the parent dense is 20 layers and the student is 14, so the transplant
REM     goes by role bands, not by index zip.
REM
REM   READ IN THIS ORDER
REM     1. the printed layer line for d14: it must say layers=2+10+2.
REM     2. grad_max and n_skip from the json, before any loss number.
REM     3. val minus train_ce. Over 0.3 means the instrument, not the model.
REM     4. log val is NOT the verdict. Stage7b and paired_eval settle it.
REM
REM   COST: about 4.6h.   PLAN: test_plan/P062 Stage8
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage8_speed_depth --note "[1/3] d14_cla2_norecur - the 32 MiB speed-compliant point, preset m100s10"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage8_speed_depth -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d14_cla2_norecur
if errorlevel 1 echo [WARN] d14_cla2_norecur failed - continuing
set TL_WB_TAG=d14_cla2_norecur
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage8_speed_depth --note "[2/3] d16_cla2_norecur - the 40 MiB speed-compliant point"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage8_speed_depth -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_cla2_norecur
if errorlevel 1 echo [WARN] d16_cla2_norecur failed - continuing
set TL_WB_TAG=d16_cla2_norecur
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage8_speed_depth --note "[3/3] seed replica of the 40 MiB point - this is the family ruler"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage8_speed_depth -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --seed 2024 --tag d16_cla2_norecur_s2
if errorlevel 1 echo [WARN] seed replica failed - continuing
set TL_WB_TAG=d16_cla2_norecur_s2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage8_speed_depth --note "DONE. Read grad_max and n_skip first, then the layer counts, then val minus train_ce. The verdict needs paired_eval, not this log."

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
