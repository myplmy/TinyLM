@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  PM000 Stage1E - deterministic paired full-val for the complete R2 triad.
REM  USER RUN ONLY. This evaluates models on the exact 600M validation cache.
REM ============================================================================

if not exist run100m.py cd ..
if not exist run100m.py goto BADROOT

python scripts\check_moonshot_namespace.py
if errorlevel 1 goto PREFLIGHTFAIL

if not exist runs\ckpt\m100s8_ko-en_600M_dense_pm000__s1__r20__gqafixed__gps0__t100__s1337.pt goto MISSING
if not exist runs\ckpt\m100s8_ko-en_600M_dense_pm000__s1__r20__gqalatin__gps0__t100__s1337.pt goto MISSING
if not exist runs\ckpt\m100s8_ko-en_600M_dense_pm000__s1__r20__gqarandom__gps17__t100__s1337.pt goto MISSING

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1E_r2_paired_eval --note "[Stage1E] deterministic 600M full-val, each checkpoint uses its trained R2 function"
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1E_r2_paired_eval -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --models dense_pm000__s1__r20__gqafixed__gps0__t100__s1337 dense_pm000__s1__r20__gqalatin__gps0__t100__s1337 dense_pm000__s1__r20__gqarandom__gps17__t100__s1337 --match-train-repeat
if errorlevel 1 goto EVALFAIL

python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1E_r2_paired_eval --note "READ: Latin-fixed and random-fixed paired deltas, SE, VRAM, and wall time. One seed is checkpoint evidence, not architecture proof."
goto DONE

:MISSING
echo.
echo [STOP] one or more Stage1 final checkpoints are missing. Do not score a partial triad.
if not defined TL_NOPAUSE pause
exit /b 7

:EVALFAIL
python scripts\runlog.py --outdir moonshot_result --name PM000__MOONSHOT__Stage1E_r2_paired_eval --note "STAGE1E FAIL. Separate environment/evaluation failure from model quality."
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
