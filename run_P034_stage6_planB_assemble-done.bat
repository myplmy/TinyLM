@echo off
REM =============================================================================
REM  P034 stage 6  -  ASSEMBLE REVIEW3 option B and measure it
REM                   no training. about 0.3 hours. GPU not required.
REM
REM  WHY
REM    REVIEW3 option B has been the leading candidate for weeks and its total has
REM    NEVER BEEN MEASURED - it is the sum of three separately measured terms:
REM        LUT ternary        8.88 MiB   (result 016, measured alone)
REM      + embedding int8     9.1        (result 016 section 20, measured alone)
REM      + other fp32         0.4
REM      = 18.4 MiB           this total is an ADDITION, not a measurement
REM    Adding measurements is how accounting errors hide. Result 016 section 16
REM    already caught one: int4, int8 and ternary all printed the same number
REM    because tensor_mb() was not counting the code table.
REM
REM  AND THE TARGET IS NOW FIXED
REM    User confirmed 2026-08-29: L2 + L3 = 8 MB + 32 MB = 40 MB.
REM    L2 is per-core private on this CPU, so the usable budget is
REM        1 thread  ~33 MiB      4 threads ~36 MiB      8 threads ~40 MiB
REM    Result 014 section 12.3 measured 4 threads at +69 percent tok/s over 1,
REM    so 36 MiB is the practical line.
REM
REM  PREDICTIONS
REM    B1  the assembled total is within 0.5 MiB of 18.4. A larger gap means a
REM        term is double counted or a table is uncounted.
REM    B2  it passes 36 MiB with room to spare - about 17.6 MiB of headroom.
REM    B3  the same assembly on mC_cla1_ag4 (smaller ternary term) lands near
REM        17.7 MiB. That body is the smaller one and should stay smaller.
REM    B4  the logit equivalence gate is NOT zero for the LUT path - per-row alpha
REM        is re-estimated. That is expected (CLAUDE.md) and is not a failure.
REM
REM  WHAT THIS CANNOT DECIDE
REM    Quality. This measures memory only. The LUT quality cost in bpb is still
REM    unmeasured (REVIEW3 section 13 unknown 3) and the embedding int8 cost was
REM    measured under cuda autocast, not the CPU fp32 deployment path (016 s22.4).
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P034_stage6_planB_assemble --note "=============================================================================" "P034 stage 6   assemble REVIEW3 option B and measure the total" "18.4 MiB has always been an addition of three separately measured terms." "Target confirmed 2026-08-29: L2+L3 = 40 MB, practical line 36 MiB at 4 threads." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P034_stage6_planB_assemble --note "[1/4] baseline - drop latent + int8 only. The number we already know."
python scripts\runlog.py --name P034_stage6_planB_assemble -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_cla1_ag4 --drop-latent --int8-store
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P034_stage6_planB_assemble --note "[2/4] add the embedding int8 term"
python scripts\runlog.py --name P034_stage6_planB_assemble -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_cla1_ag4 --drop-latent --int8-store --emb-quant int8
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P034_stage6_planB_assemble --note "[3/4] option B assembled - LUT ternary plus embedding int8. B1 and B2."
python scripts\runlog.py --name P034_stage6_planB_assemble -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_cla1_ag4 --drop-latent --lut --emb-quant int8
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P034_stage6_planB_assemble --note "[4/4] the 36-layer standard model on the same assembly, for the record"
python scripts\runlog.py --name P034_stage6_planB_assemble -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1d --models mC_d36_ag4_nokd --drop-latent --lut --emb-quant int8
if errorlevel 1 echo [WARN] step 4 failed - continuing

echo.
python scripts\runlog.py --name P034_stage6_planB_assemble --note "=============================================================================" "READ IN THIS ORDER" "1. B1 - step [3] total against the arithmetic 18.4. Within 0.5 MiB means the" "   three terms really do add. Outside it means one of them was wrong alone." "2. B2 - against 36 MiB (4 threads) and 40 MiB (8 threads). Write BOTH." "3. B3 - mC_cla1_ag4 should be the smaller of the two in every column." "4. B4 - the LUT logit gate is not zero. Read result 028 before calling it a" "   failure; per-row alpha is re-estimated by construction." "5. subtract step [2] from step [3] to see what LUT alone bought on top of int8." "   That difference is the honest value of the LUT path." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
