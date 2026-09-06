@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  PM000 Stage2E - deterministic paired full-val for the complete R3 triad.
REM  USER RUN ONLY. Do not compare R2 fixed directly with R3 treatment for cause.
REM ============================================================================

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

if not exist runs\ckpt\m100s8_ko-en_600M_dense_pm000__s2__r30__gqafixed__gps0__t100__s1337.pt goto MISSING
if not exist runs\ckpt\m100s8_ko-en_600M_dense_pm000__s2__r30__gqalatin__gps0__t100__s1337.pt goto MISSING
if not exist runs\ckpt\m100s8_ko-en_600M_dense_pm000__s2__r30__gqarandom__gps17__t100__s1337.pt goto MISSING

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2E_r3_paired_eval --note "[Stage2E] deterministic 600M full-val, each checkpoint uses its trained R3 function"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2E_r3_paired_eval -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --models dense_pm000__s2__r30__gqafixed__gps0__t100__s1337 dense_pm000__s2__r30__gqalatin__gps0__t100__s1337 dense_pm000__s2__r30__gqarandom__gps17__t100__s1337 --match-train-repeat
if errorlevel 1 goto EVALFAIL

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2E_r3_paired_eval --note "READ: Latin-fixed and random-fixed only inside R3. One seed cannot establish an architecture winner."
goto DONE

:MISSING
echo.
echo [STOP] one or more Stage2 final checkpoints are missing. Do not score a partial triad.
if not defined TL_NOPAUSE pause
exit /b 7

:EVALFAIL
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage2E_r3_paired_eval --note "STAGE2E FAIL. Separate environment/evaluation failure from model quality."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 1

:PREFLIGHTFAIL
echo.
echo [STOP] moonshot branch or namespace preflight failed. No evaluation was started.
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
