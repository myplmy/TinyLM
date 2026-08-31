@echo off
REM P075 stage 0b RERUN - the first attempt died in 0.0 minutes.
REM   diag_dataset_tokens.py defined ROOT but never did sys.path.insert, so
REM   `import tinylm` raised ModuleNotFoundError. Fixed 2026-08-30, plus a new
REM   check in check_hf_redirect.py that catches the same class.
REM   Read: bytes_per_token first (3.0 to 6.0 or the tool is wrong).

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P075_stage0b_tokens_v2 --note "[1/2] text field only - the training decision as of 2026-08-31"
python scripts\runlog.py --name P075_stage0b_tokens_v2 -- python scripts\diag_dataset_tokens.py --train "datasets/TinyDataset/stage1_highdensity_dataset/train/stage1_(1)identity_high_density_train_v*.json" --val "datasets/TinyDataset/stage1_highdensity_dataset/val/stage1_(1)identity_high_density_val_v*.json" --fields text
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P075_stage0b_tokens_v2 --note "[2/2] all fields - the alternative we are NOT taking, for the record"
python scripts\runlog.py --name P075_stage0b_tokens_v2 -- python scripts\diag_dataset_tokens.py --train "datasets/TinyDataset/stage1_highdensity_dataset/train/stage1_(1)identity_high_density_train_v*.json" --val "datasets/TinyDataset/stage1_highdensity_dataset/val/stage1_(1)identity_high_density_val_v*.json" --fields all
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P075_stage0b_tokens_v2 --note "READ IN THIS ORDER" "1. bytes_per_token. Outside 3.0 to 6.0 means the tool is wrong." "2. the measured token count against the estimate of about 249,000." "3. quality review section 15.1 says 51 percent of target. That number is" "   an ESTIMATE until this run. Do not quote it as measured before this."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
