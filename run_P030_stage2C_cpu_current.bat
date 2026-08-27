@echo off
REM =============================================================================
REM  P030 stage 2C  -  CPU deployment speed of the CURRENT model set
REM                    no training. about 25 minutes. GPU not required.
REM
REM  WHY THIS EXISTS  (2026-08-27)
REM    REVIEW3 section 5-5 has been waiting five sessions for "does the +69
REM    percent wall clock of recursion hurt at deployment". The handoff kept
REM    listing "P030 stage 2B" as the missing measurement.
REM    ^-^> That was wrong. Stage 2B RAN on 2026-07-31 (result 014 section 10,
REM        31 to 35 tok/s at one CPU thread). The plan document still carried a
REM        pause marker on that section, and I read the marker instead of the
REM        banner three lines above it. The stale marker is fixed.
REM
REM    What is actually missing is a CPU measurement of the models we have NOW.
REM    Stage 2B measured p6d, mA_g4s34_k4 and mC_g8_k4 - a month old, and
REM    recursion did not exist yet. Recursion is the whole question.
REM
REM  WHAT THIS ANSWERS
REM    Y1  tok/s of the standard model at one CPU thread, deployment path
REM        (latent dropped, int8 stored).
REM    Y2  what recursion R=2 and R=3 cost at INFERENCE. Training wall clock was
REM        +69 percent at R=2. Inference should be worse - training amortises
REM        over a batch and decode does not.
REM    Y3  whether 20 layers plus cla1 plus ag4 (mC_cla1_ag4, resident 339.0)
REM        beats the 36 layer standard model (379.7) on CPU as well as on memory.
REM        Result 058 section 12.5 says it is the smaller model of the two.
REM    Y4  thread scaling. Result 014 found tok/s flat from 1 to 8 threads while
REM        TTFT fell 42 percent. Confirm that still holds.
REM
REM  PREDICTIONS, fixed in advance
REM    V1  standard model 20 to 30 tok/s at one thread. Lower than 014 because
REM        36 layers, higher per layer because ag4 shares attention.
REM    V2  R=2 costs MORE than +69 percent at decode. If it is under +69, the
REM        training number was dominated by something other than layer visits.
REM    V3  mC_cla1_ag4 is FASTER than mC_d36_ag4_nokd. 16 fewer layers.
REM    V4  tok/s flat across threads, TTFT falls. Same shape as 014.
REM
REM  WHAT THIS CANNOT DECIDE
REM    LUT kernel speed. mem_runtime --lut is a PyTorch reference and slow by
REM    construction - that is P014B U1 and needs a C/AVX2 kernel first.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P030_stage2C_cpu_current --note "=============================================================================" "P030 stage 2C   CPU deployment speed of the models we have NOW" "Stage 2B ran on 2026-07-31. This is the CURRENT set plus recursion." "REVIEW3 section 5-5 is the caller. No training. About 25 minutes." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P030_stage2C_cpu_current --note "[1/4] m100R1c family - baseline, cla1+ag4 candidate, recursion R1 checkpoint"
python scripts\runlog.py --name P030_stage2C_cpu_current -- python scripts\bench_infer.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_cla1_ag4 --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2C_cpu_current --note "[2/4] the standard model - 36 layers, attn_group 4"
python scripts\runlog.py --name P030_stage2C_cpu_current -- python scripts\bench_infer.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_nokd --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2C_cpu_current --note "[3/4] recursion at R=2 - evaluate the function that was trained (trap 39)"
python scripts\runlog.py --name P030_stage2C_cpu_current -- python scripts\bench_infer.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20_nokd --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store --infer-repeat 2.0
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2C_cpu_current --note "[4/4] recursion at R=3"
python scripts\runlog.py --name P030_stage2C_cpu_current -- python scripts\bench_infer.py --preset m100R1c --data ko-en --tokens 300M --models mC_r30_nokd --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store --infer-repeat 3.0
if errorlevel 1 echo [WARN] step 4 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2C_cpu_current --note "=============================================================================" "READ IN THIS ORDER" "1. tok/s at one thread for mC_d36_ag4_nokd against V1 (20 to 30)." "2. mC_r20_nokd tok/s divided by mC_initonly tok/s. V2 says the decode" "   penalty is WORSE than the +69 percent seen in training." "3. mC_cla1_ag4 against mC_d36_ag4_nokd (V3). If the 20 layer model is both" "   smaller (339.0 vs 379.7 resident) and faster, REVIEW3 has a new body." "4. tok/s across threads 1 and 4 (V4). Result 014 says flat, TTFT falls." "5. TTFT is the number a user feels first. Report it beside tok/s, never alone." "IF RECURSION COSTS MORE THAN 2x AT DECODE  REVIEW3 option B loses its" "  recovery lever and the LUT quality cost has to be paid some other way." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
