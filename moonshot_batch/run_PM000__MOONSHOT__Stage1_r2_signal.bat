@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  PM000 Stage1 - R2 fixed vs Latin vs deterministic random, 100M tokens each.
REM  USER RUN ONLY. Run latest full smoke and Stage0B first; clear HOLD explicitly.
REM  All three arms are scratch and matched.
REM  The --tokens 600M value selects the exact clean cache/checkpoint namespace;
REM  763 steps x 8 x 16 x 1024 = 100007936 actual training tokens per arm.
REM ============================================================================

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1_r2_signal --note "[1/3] R2 fixed mapping - matched control"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1_r2_signal -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 600M --exact-cache --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --compile --ce-chunk 2048 --cla-group 2 --train-repeat 2.0 --gqa-pass-schedule fixed --gqa-pass-seed 0 --tag dense_pm000__s1__r20__gqafixed__gps0__t100__s1337
if errorlevel 1 echo [WARN] fixed arm failed - continue independent arms

timeout /t 15 /nobreak

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1_r2_signal --note "[2/3] R2 Latin mapping - ordered shifts 0 then 1"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1_r2_signal -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 600M --exact-cache --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --compile --ce-chunk 2048 --cla-group 2 --train-repeat 2.0 --gqa-pass-schedule latin --gqa-pass-seed 0 --tag dense_pm000__s1__r20__gqalatin__gps0__t100__s1337
if errorlevel 1 echo [WARN] Latin arm failed - continue independent arms

timeout /t 15 /nobreak

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1_r2_signal --note "[3/3] R2 random balanced mapping - schedule seed 17"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1_r2_signal -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 600M --exact-cache --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --compile --ce-chunk 2048 --cla-group 2 --train-repeat 2.0 --gqa-pass-schedule random --gqa-pass-seed 17 --tag dense_pm000__s1__r20__gqarandom__gps17__t100__s1337
if errorlevel 1 echo [WARN] random arm failed - triad verdict must remain pending

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1_r2_signal --note "END Stage1. Do not rank single best checkpoints. Run Stage1E only if all three final checkpoints exist."
goto DONE

:PREFLIGHTFAIL
echo.
echo [STOP] moonshot branch or namespace preflight failed. No training was started.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo.
echo [STOP] run this from the repo root or moonshot_batch folder.
if not defined TL_NOPAUSE pause
exit /b 9

:DONE
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0
