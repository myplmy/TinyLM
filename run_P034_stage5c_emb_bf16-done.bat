@echo off
REM =============================================================================
REM  P034 stage 5c  -  the bf16 embedding arm that died twice
REM                    diagnostics only, no training, about 12 minutes
REM
REM  WHAT HAPPENED  (result 016 section 20.4)
REM    E2 of stage 5b crashed:
REM        ternary.py:355  y = F.linear(x, wq)
REM        RuntimeError: expected m1 and m2 to have the same dtype,
REM                      but got: BFloat16 != float
REM    The 08-23 fix downcast emb_up alongside emb. That did not fix it - it
REM    pushed the failure one layer deeper, into the ternary blocks, whose
REM    dequantised weights are fp32.
REM
REM  THE 08-24 FIX
REM    A quantisation format is a STORAGE format, not a compute format. The
REM    weights stay bf16; forward() casts the embedding output back to fp32.
REM    int8 and ternary already did exactly this through _emb_rows(). bf16 was
REM    the only path that did not.
REM
REM  !! WHY THIS IS LOW PRIORITY NOW
REM    Stage 5b measured embedding int8 at plus 0.0001 - one thirty-fourth of the
REM    no-KD resolution - while taking the non-ternary resident term from 33.0 to
REM    9.1 MiB. bf16 can only reach 16.5. So bf16 has no path to adoption; this
REM    run exists to close the code defect, not to open an option.
REM
REM  PREDICTIONS, fixed in advance
REM    J1  it completes. If it dies again, fp32 modules remain in that path and
REM        the fix is still incomplete.
REM    J2  non-ternary resident term about 16.5 MiB - half of 33.0, no more.
REM        bf16 halves the table and nothing else.
REM    J3  quality cost is EXACTLY 0.0000 to four decimals on the paired test.
REM        bf16 has 8 exponent bits and fp32 has 8; only the mantissa is cut,
REM        and the paired test is deterministic. A non-zero number here means
REM        the cast is happening somewhere it should not.
REM    J4  int8 still beats it on both axes. If it does not, re-read stage 5b.
REM
REM  WHAT THIS CANNOT DECIDE
REM    Anything about adoption. This is a defect closure plus one data point.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P034_stage5c_emb_bf16 --note "=============================================================================" "P034 stage 5c   the bf16 embedding arm, after the 08-24 fix" "Storage format is not compute format. Weights stay bf16, forward casts back." "Defect closure. int8 already won on both axes. About 12 minutes." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P034_stage5c_emb_bf16 --note "[1/3] baseline - no embedding quantisation, for the resident reference"
python scripts\runlog.py --name P034_stage5c_emb_bf16 -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store
if errorlevel 1 echo [WARN] baseline failed - continuing

echo.
python scripts\runlog.py --name P034_stage5c_emb_bf16 --note "[2/3] E2 retry - bf16. THIS IS THE ARM THAT DIED TWICE"
python scripts\runlog.py --name P034_stage5c_emb_bf16 -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store --emb-quant bf16
if errorlevel 1 echo [WARN] bf16 STILL fails - read the traceback, the fix is incomplete

echo.
python scripts\runlog.py --name P034_stage5c_emb_bf16 --note "[3/3] quality cost - same checkpoint, quantised against not"
python scripts\runlog.py --name P034_stage5c_emb_bf16 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_initonly#2 --emb-quant-per-tag mC_initonly=none mC_initonly#2=bf16
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P034_stage5c_emb_bf16 --note "=============================================================================" "READ IN THIS ORDER" "1. did step [2] complete. That is J1 and it is the point of this batch." "   If it died at ternary.py again, storage-vs-compute is still leaking." "2. non-ternary resident term against J2 (about 16.5). Compare with the 9.1" "   that int8 gave in result 016 section 20." "3. paired delta against J3. Expect 0.0000. Anything else means a cast is" "   happening in the compute path, not just in storage." "4. J4 - int8 should still win on BOTH axes. It costs plus 0.0001 and reaches" "   9.1 MiB. bf16 costs 0 and reaches 16.5. Neither dominates on paper;" "   int8 wins because 9.1 is what fits in L3 and 16.5 is not." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
