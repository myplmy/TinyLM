@echo off
REM =============================================================================
REM  P075 stage 0b  -  how many tokens is the stage1 dataset really.
REM  about 0.1 hours. NO TRAINING. NO GPU.
REM
REM  WHY  (docs/20260829 stage1 quality review s10)
REM    We reported 238,924 training tokens as bytes / 4.366. That coefficient
REM    came from a general corpus (result 053 s1.7.4). This data is short,
REM    highly templated definition sentences. The coefficient may not hold, and
REM    the whole "we are at 49 percent of target" claim rests on it.
REM
REM  INDEPENDENT VARIABLE
REM    none - this is a measurement, not a comparison.
REM
REM  PREDICTIONS
REM    T1  bytes_per_token lands between 3.0 and 6.0. Under 1.0 means the
REM        tokenizer did not match. Over 10 means the encoding broke.
REM    T2  the estimate is within 15 percent of the measurement. Templated text
REM        should tokenize slightly BETTER than general text - repeated phrases
REM        become single tokens - so the true count may be LOWER than the 4.366
REM        estimate, which would make the shortfall worse, not better.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P075_stage0b_dataset_tokens --note "=============================================================================" "P075 stage 0b   real token count for TinyDataset stage1" "The 49 percent figure rests on a coefficient borrowed from another corpus." "=============================================================================="

echo.
python scripts\runlog.py --name P075_stage0b_dataset_tokens --note "[1/2] text field only - this is the training decision as of 2026-08-30"
python scripts\runlog.py --name P075_stage0b_dataset_tokens -- python scripts\diag_dataset_tokens.py --train "datasets/TinyDataset/stage1_highdensity_dataset/train/stage1_(1)identity_high_density_train_v*.json" --val "datasets/TinyDataset/stage1_highdensity_dataset/val/stage1_(1)identity_high_density_val_v*.json" --fields text
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P075_stage0b_dataset_tokens --note "[2/2] all fields - the alternative we are NOT taking, for the record"
python scripts\runlog.py --name P075_stage0b_dataset_tokens -- python scripts\diag_dataset_tokens.py --train "datasets/TinyDataset/stage1_highdensity_dataset/train/stage1_(1)identity_high_density_train_v*.json" --val "datasets/TinyDataset/stage1_highdensity_dataset/val/stage1_(1)identity_high_density_val_v*.json" --fields all
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P075_stage0b_dataset_tokens --note "=============================================================================" "READ IN THIS ORDER" "1. bytes_per_token first. Outside 3.0 to 6.0 means the tool is wrong." "2. the estimate-vs-measured error line. Over 15 percent and every volume" "   number in the quality review needs rewriting." "3. the remaining-files line. That is what to ask the generator for next." "=============================================================================="

if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
