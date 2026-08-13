@echo off
REM =============================================================================
REM  P055 stage 0c  -  KD implementation audit, THIRD run   (GPU light, ~2 min)
REM
REM  WHY A THIRD RUN
REM    stage 0  (result 042 s0-s9) : synthetic logits were DEGENERATE - teacher
REM        and student shared the same base, so KL was about 0 and A2/A4 were
REM        measuring nothing. Fixed: independent draws + TVD guard.
REM    stage 0b (result 042 s10)   : data was healthy (TVD 0.5206) but A4 was
REM        STILL VACUOUS. Cause found: torch autocast keeps log_softmax,
REM        softmax and kl_div in its fp32 list, so the autocast arm can never
REM        differ from the fp32 arm. The test could not fail.
REM    stage 0c (this)             : A4 now prints the actual dtype AND adds a
REM        FORCED bf16 arm, so the check can fail. A5 and --real are new.
REM
REM  WHAT IS NEW SINCE 0b
REM    A4  : dtype proof + forced-bf16 control arm
REM    A5  : teacher vs student quantisation contract (vocab_size, quant_anneal,
REM          micro_group, twn_thr_ratio, ste_clip, quantize_embedding,
REM          sparse34, emb_rank). vocab mismatch invalidates the KL outright.
REM    --real : real checkpoint logits, so A2's MAGNITUDE becomes usable.
REM             Until now only its DIRECTION was valid - a diffuse distribution
REM             makes the L2 norm of (p_s - p_t) structurally small regardless of KD.
REM
REM  WHY THIS RUNS BEFORE P055 STAGE 1
REM    Stage 1 is an alpha sweep costing about 12 GPU hours. If nominal alpha
REM    0.5/0.3/0.1/0 all land in the same effective band, those 12 hours measure
REM    the same point four times. --real costs 2 minutes and tells us the grid.
REM
REM  WHAT TO READ
REM    1. TVD line first. Below 0.05 means the data is degenerate again - stop.
REM    2. A5 - if vocab_size differs, do not read A2/A4 at all.
REM    3. A4 - "autocast dtype = torch.float32" is the PROOF we were missing.
REM    4. A2 under --real - THIS is the number stage 1's grid depends on.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P055_stage0c_audit --note "=============================================================================" "P055 stage 0c   KD audit, third run   about 2 minutes" "New since 0b: A4 dtype proof + forced bf16 arm, A5 contract, --real logits" "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P055_stage0c_audit --note "[P055 stage 0c] synthetic arm first - A1/A2/A4 with independent draws and the fixed A4."
python scripts\runlog.py --name P055_stage0c_audit -- python scripts\diag_kd_loss.py
if errorlevel 1 echo [WARN] synthetic arm reported problems - continuing to the real arm

echo.
python scripts\runlog.py --name P055_stage0c_audit --note "[P055 stage 0c] real arm - dense teacher vs mC_wsd student. A5 runs here. GPU forward only, no training."
python scripts\runlog.py --name P055_stage0c_audit -- python scripts\diag_kd_loss.py --real
if errorlevel 1 echo [WARN] real arm reported problems - the log still has the numbers

echo.
echo.
python scripts\runlog.py --name P055_stage0c_audit --note "=============================================================================" "READ IN THIS ORDER" "1. TVD - below 0.05 means degenerate data again, stop reading" "2. A5 - a vocab_size mismatch invalidates A2/A4 completely" "3. A4 - autocast dtype float32 is the proof stage 0b was missing" "4. A2 under --real - stage 1's alpha grid depends on this number" "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
