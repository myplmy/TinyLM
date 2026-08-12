@echo off
REM =============================================================================
REM  CLEANUP  runs\ckpt   -   GPU 0, seconds
REM
REM  Source of truth = docs\20260813_checkpoint list (Korean filename).
REM  ***The file names are NOT written in this batch on purpose.***
REM  Trap 18 in ai_dev_tool/01: "the target set defined in two places" caused the
REM  same bug twice in result 016. One place decides, and it is the document.
REM  scripts\cleanup_ckpt.py reads that table.
REM
REM  Safety
REM    - dry run first, always. Nothing is deleted until you answer YES.
REM    - only rows judged "deletable" are candidates. keep / hold / unlisted
REM      files cannot be touched at all.
REM    - the canonical parent and the --kd-best target are hard-blocked in the
REM      script even if the table says otherwise. That line exists because
REM      m100_ko-en_300M_dense_best.pt was deleted by accident on 2026-08-14.
REM
REM  Make sure no training run is in progress before you answer YES.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo ============================== DRY RUN =====================================
python scripts\cleanup_ckpt.py
if errorlevel 1 goto PLANBAD

echo.
echo =============================================================================
echo  The list above is what WOULD be deleted. Nothing has been removed yet.
echo  Type  YES  in capitals to delete, anything else to cancel.
echo =============================================================================
set TL_OK=
set /p TL_OK=delete these files?
if not "!TL_OK!"=="YES" goto CANCEL

echo.
echo ============================== DELETING ====================================
python scripts\cleanup_ckpt.py --yes
if errorlevel 1 goto DELPART

echo.
echo [done] cleanup finished.
if not defined TL_NOPAUSE pause
exit /b 0

:CANCEL
echo.
echo [cancel] nothing was deleted.
if not defined TL_NOPAUSE pause
exit /b 0

:DELPART
echo.
echo [WARN] some files could not be deleted - see the list above.
echo        Most likely a training run still has them open.
if not defined TL_NOPAUSE pause
exit /b 1

:PLANBAD
echo.
echo [STOP] could not build the deletion plan. Is the judgement document there?
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
