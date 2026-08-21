@echo off
REM =============================================================================
REM  tool_wandb_push.bat  --  push finished training logs to wandb
REM
REM  WHY THIS IS A SEPARATE STEP AND NOT A HOOK IN trainer.py
REM    Two reasons, both about not breaking training:
REM      1. a hook could change numerics or at least perturb timing, and we
REM         judge on differences of 0.003
REM      2. a network failure inside the training loop would kill a run that
REM         has already spent hours
REM    So the batch calls this AFTER the training command returns. If it fails,
REM    nothing is lost - the json on disk is still the source of truth.
REM
REM  ARGUMENTS (environment variables)
REM    TL_WB_TAG      substring filter on the log name. Push only matching runs.
REM                   Leave unset to push everything eligible.
REM    TL_WB_PROJECT  wandb project. default: tinylm
REM    TL_NOPAUSE     set to skip the pause
REM
REM  USAGE inside an experiment batch
REM    set TL_WB_TAG=mC_wqbf16
REM    call scripts\batch\tool_wandb_push.bat
REM
REM  NOTE  the API key is read from a path only - never printed, never logged.
REM        Default Z:\TinyLM_private\weave_apikey_only.txt, override with
REM        TL_WANDB_KEY_FILE.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

setlocal enabledelayedexpansion
if not defined TL_WB_PROJECT set TL_WB_PROJECT=tinylm
set TL_WB_ARG=
if defined TL_WB_TAG set TL_WB_ARG=--tag !TL_WB_TAG!

echo.
echo   [wandb] project=!TL_WB_PROJECT!  filter=!TL_WB_ARG!
python scripts\wandb_sync.py --push --project !TL_WB_PROJECT! !TL_WB_ARG!
if errorlevel 1 echo [WARN] wandb push failed - the json on disk is unaffected, continuing
endlocal

exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
