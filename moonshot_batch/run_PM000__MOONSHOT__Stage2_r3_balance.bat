@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  PM000 Stage2 - R3 full GQA balance cycle, 100M tokens per arm.
REM  USER RUN ONLY. R3 has more compute than R2; infer only inside this triad.
REM ============================================================================

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2_r3_balance --note "[1/3] R3 fixed mapping - matched control"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2_r3_balance -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 600M --exact-cache --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --compile --ce-chunk 2048 --cla-group 2 --train-repeat 3.0 --gqa-pass-schedule fixed --gqa-pass-seed 0 --tag dense_pm000__s2__r30__gqafixed__gps0__t100__s1337
if errorlevel 1 echo [WARN] fixed arm failed - continue independent arms

timeout /t 15 /nobreak

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2_r3_balance --note "[2/3] R3 Latin mapping - complete shifts 0, 1, 2"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2_r3_balance -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 600M --exact-cache --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --compile --ce-chunk 2048 --cla-group 2 --train-repeat 3.0 --gqa-pass-schedule latin --gqa-pass-seed 0 --tag dense_pm000__s2__r30__gqalatin__gps0__t100__s1337
if errorlevel 1 echo [WARN] Latin arm failed - continue independent arms

timeout /t 15 /nobreak

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2_r3_balance --note "[3/3] R3 random balanced mapping - schedule seed 17"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2_r3_balance -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 600M --exact-cache --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --compile --ce-chunk 2048 --cla-group 2 --train-repeat 3.0 --gqa-pass-schedule random --gqa-pass-seed 17 --tag dense_pm000__s2__r30__gqarandom__gps17__t100__s1337
if errorlevel 1 echo [WARN] random arm failed - triad verdict must remain pending

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2_r3_balance --note "END Stage2. Compare only within R3. Run Stage2E only if all three final checkpoints exist."
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
