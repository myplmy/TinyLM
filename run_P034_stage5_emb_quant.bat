@echo off
REM =============================================================================
REM  P034 stage 5  -  embedding quantisation, five formats
REM                   (NO TRAINING, deployment conversion, CPU, minutes)
REM
REM  WHY THIS IS NOW THE TOP ITEM
REM    Result 052 measured the int8 path: 70.4 MiB at best, and 33.0 MiB of that
REM    is the embedding. As ternary shrinks, the embedding share grows:
REM        fp32 7.3 percent, drop-latent 13.6, int8 38.0, best model 46.9
REM    The embedding is now the single largest term on the residency axis.
REM
REM  THE STRUCTURAL PROBLEM (plan P034 s11.2)
REM    Input lookup touches a few ROWS. The output head puts the whole (V, E)
REM    matrix through a GEMM every step. So naive int8 INCREASES residency:
REM    store 8.32 plus a 32.75 fp32 restore is 40.94, worse than 32.75.
REM    The fix is chunked restore - the same trick P053 used on the KD loss to
REM    free 3.06 GiB. Chunk 4096 caps the live buffer at 4 MiB.
REM
REM  BF16 IS SPECIAL - THERE IS NO RESTORE AT ALL
REM    forward already runs inside autocast(bf16), so F.linear casts emb to
REM    bf16 anyway. Storing it as bf16 makes that cast disappear. Residency
REM    32.75 to 16.38 MiB and the arithmetic gets SHORTER, not longer.
REM
REM  THE ARMS - all converted from the SAME checkpoint, so seed and training
REM  condition are perfectly matched. Quality differences are pure quantisation.
REM    E0 fp32 (reference)   E1 bf16   E2 fp16   E3 int8   E4 int4   E5 ternary
REM
REM  PREDICTIONS, fixed in advance (plan P034 s11.6)
REM    F1  E1 delta under 0.002 - only the bf16 round trip remains
REM    F2  E1 tok/s at least as fast as E0 - a cast disappears
REM    F3  E2 delta no worse than E1 - three more mantissa bits
REM    F4  E3 delta 0.005 to 0.020 - below the E=128 rank cut (+0.0645)
REM    F5  E4 delta 0.03 to 0.10
REM    F6  E5 delta over 0.15 - that is the "training problem" band, and
REM        finding where it breaks tells us how far int4 can be pushed
REM    F7  E3 to E5 lose 3 to 10 percent tok/s from the chunked restore
REM    Adoption: E1 is adopted outright if delta is under 0.0034 (no-KD 2 sigma).
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether we reach 40 MiB. Result 052 s3.1 showed int8 ternary weights
REM    plus a ternary embedding still lands at 39.5, i.e. only just inside.
REM    The LUT kernel is still required. This measures one of the two terms.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P034_stage5_embq --note "=============================================================================" "P034 stage 5   embedding quantisation, five formats   NO TRAINING" "Result 052: the embedding is now 47 percent of the int8 residency." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

set TL_NOPAUSE=1
set TL_LOGNAME=P034_stage5_embq
set TL_MODELS=mC_initonly mC_d36_ag4_nokd mC_p1c1g16
set TL_SKIP_CUDA=1

python scripts\runlog.py --name P034_stage5_embq --note "[1/6] E0 fp32 reference - deployment cost today"
set TL_EXTRA=--drop-latent --int8-store
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] E0 failed - continuing

echo.
python scripts\runlog.py --name P034_stage5_embq --note "[2/6] E1 bf16 - THE ONE. No restore, and the cast disappears."
set TL_EXTRA=--drop-latent --int8-store --emb-quant bf16
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] E1 failed - continuing

echo.
python scripts\runlog.py --name P034_stage5_embq --note "[3/6] E3 int8 with chunked restore, chunk 4096"
set TL_EXTRA=--drop-latent --int8-store --emb-quant int8 --emb-chunk 4096
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] E3 failed - continuing

echo.
python scripts\runlog.py --name P034_stage5_embq --note "[4/6] E4 int4 group 64, chunked"
set TL_EXTRA=--drop-latent --int8-store --emb-quant int4 --emb-chunk 4096
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] E4 failed - continuing

echo.
python scripts\runlog.py --name P034_stage5_embq --note "[5/6] E5 ternary - expected to break. That is the point."
set TL_EXTRA=--drop-latent --int8-store --emb-quant ternary --emb-chunk 4096
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] E5 failed - continuing

echo.
python scripts\runlog.py --name P034_stage5_embq --note "[6/6] quality - paired full-val for each format against fp32"
python scripts\runlog.py --name P034_stage5_embq -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly
if errorlevel 1 echo [WARN] reference eval failed - continuing
python scripts\runlog.py --name P034_stage5_embq -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_std2b --emb-quant bf16
if errorlevel 1 echo [WARN] bf16 quality failed - continuing
python scripts\runlog.py --name P034_stage5_embq -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_std2b --emb-quant int8 --emb-chunk 4096
if errorlevel 1 echo [WARN] int8 quality failed - continuing
python scripts\runlog.py --name P034_stage5_embq -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_std2b --emb-quant ternary --emb-chunk 4096
if errorlevel 1 echo [WARN] ternary quality failed - continuing

echo.
echo.
python scripts\runlog.py --name P034_stage5_embq --note "=============================================================================" "READ IN THIS ORDER" "1. E0 tensor-sum residency. It must match result 052: 86.9 for mC_initonly." "   If it does not, something else changed and nothing below is comparable." "2. E1 residency. Expect about 70.5 - that is 86.9 minus 16.4." "3. E3 residency. Expect about 62.2. E4 about 58.2. E5 about 55.7." "4. tok/s across the arms. E1 must NOT be slower (F2). If it is, the cast" "   was not actually removed and the implementation is wrong." "5. the paired full-val calls. Each prints one number per model - compare the" "   quantised run against the 3.6776 reference. That is the quality cost." "6. E5 ternary is EXPECTED to break. Note WHERE it breaks, not that it did." "REMINDER  this is one of two terms. The LUT kernel is the other, and result" "          052 s3.1 says both are needed to reach 40 MiB." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
