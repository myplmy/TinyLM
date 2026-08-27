@echo off
REM =============================================================================
REM  P034 stage 5d  -  the bf16 embedding arm, attempt FOUR
REM                    diagnostics only, no training, about 12 minutes
REM
REM  !! IT HAS FAILED THREE TIMES AT THREE DIFFERENT PLACES
REM    1  08-23  emb downcast only          then emb_up (fp32) mismatch
REM    2  08-23  emb_up downcast too        then ternary.py, the ATTENTION blocks
REM    3  08-24  forward casts x to fp32    then _head_logits, the OUTPUT head
REM    Each fix moved the failure one call frame deeper. Note also that 1 and 2
REM    reported BFloat16 != float and 3 reported float != BFloat16 - the
REM    direction reversed, which is what chasing symptoms looks like.
REM
REM  THE ACTUAL CAUSE  (found 2026-08-26)
REM    Weight tying puts emb.weight and emb_up.weight at BOTH ends of the model.
REM    They are consumed in FOUR places: input lookup, input up-projection, head
REM    up-projection, head logits. Fixing one site at a time cannot terminate.
REM
REM  THE FIX
REM    Two accessors, _emb_w() and _emb_up_w(), that always return the compute
REM    dtype, and all four sites go through them. A quantisation format is a
REM    STORAGE format - int8 and ternary already worked this way through
REM    _emb_rows(); bf16 was the only path leaking storage dtype into compute.
REM    Plus a self-test: quantize_embedding now runs a one-token forward
REM    immediately and raises a readable message if anything still leaks, so a
REM    fourth failure surfaces AT THE MUTATION instead of thirty frames away.
REM
REM  PREDICTIONS, fixed in advance
REM    J1  it completes. If not, the self-test fires first and names the site.
REM    J2  non-ternary resident term about 16.5 MiB - half of 33.0. bf16 halves
REM        the table and does nothing else.
REM    J3  quality cost near zero but NOT exactly zero. bf16 keeps all 8
REM        exponent bits and cuts the mantissa to 7, so the table is rounded.
REM        Expect the 1e-4 range, like int8's plus 0.0001.
REM    J4  int8 still wins - 9.1 MiB against 16.5, and 9.1 is what fits.
REM
REM  !! WHY THIS IS LOW PRIORITY
REM    Result 016 section 20 already measured embedding int8 at plus 0.0001
REM    while taking the non-ternary resident term from 33.0 to 9.1 MiB. bf16
REM    cannot reach 9.1. This closes a code defect and fills one table cell.
REM    IF IT DIES A FOURTH TIME, DO NOT PATCH IT AGAIN - delete the bf16 path.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P034_stage5d_emb_bf16 --note "=============================================================================" "P034 stage 5d   bf16 embedding, attempt four" "Three fixes moved the failure three times. The cause was four consumption" "sites for two tensors. Accessors plus a self-test. About 12 minutes." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P034_stage5d_emb_bf16 --note "[1/3] baseline - no embedding quantisation, for the resident reference"
python scripts\runlog.py --name P034_stage5d_emb_bf16 -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store
if errorlevel 1 echo [WARN] baseline failed - continuing

echo.
python scripts\runlog.py --name P034_stage5d_emb_bf16 --note "[2/3] E2 attempt four - bf16. IF THIS DIES, READ THE SELF-TEST MESSAGE FIRST"
python scripts\runlog.py --name P034_stage5d_emb_bf16 -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store --emb-quant bf16
if errorlevel 1 echo [WARN] bf16 failed a FOURTH time - the self-test message names the site

echo.
python scripts\runlog.py --name P034_stage5d_emb_bf16 --note "[3/3] quality cost - same checkpoint, quantised against not"
python scripts\runlog.py --name P034_stage5d_emb_bf16 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_initonly#2 --emb-quant-per-tag mC_initonly=none mC_initonly#2=bf16
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P034_stage5d_emb_bf16 --note "=============================================================================" "READ IN THIS ORDER" "1. did step [2] complete. That is J1 and the point of this batch." "2. if it did NOT, the traceback should now START with the self-test message" "   from quantize_embedding, naming the leak. If it does not - if it dies" "   deep in the model again - the accessor approach is also incomplete and" "   the right move is to stop patching and delete the bf16 path." "3. resident term against J2 (about 16.5). int8 gave 9.1 in result 016 s20." "4. paired delta against J3. Expect 1e-4, not 0. Exactly 0.0000 would mean" "   the cast is not happening and the storage is still fp32." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
