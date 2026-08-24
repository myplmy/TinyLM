@echo off
REM =============================================================================
REM  P034 stage 5b  -  embedding quantisation, re-measured after two bug fixes
REM                    diagnostics plus paired eval, about 25 minutes. No training.
REM
REM  WHY A RERUN  (result 016 sections 15 to 19)
REM    Stage 5 produced two errors and one silently wrong table.
REM      E1 bf16 died: quantize_embedding changed emb.weight but not emb_up,
REM         which is fp32, so the matmul dtypes did not match. tiny has no
REM         emb_rank so the smoke could not see it - trap 37 again.
REM      int8, int4 and ternary all reported the SAME residency to four digits.
REM         That was not a result. tensor_mb counted model.parameters() only,
REM         and quantize_embedding stores the codes on python attributes after
REM         emptying emb.weight. Not one byte was counted. 38.4 MB was fiction.
REM      the quality arms measured the wrong thing: paired_eval applies
REM         --emb-quant to BOTH models, so the cost cancels. bf16 and int8
REM         returning exactly +0.0012 was the tell.
REM
REM  !! AND ONE FINDING THAT SURVIVES AND CHANGES THE PLAN
REM    int4 and ternary do not shrink storage at all. There is no int4 dtype in
REM    PyTorch, so the codes sit in a torch.int8 tensor either way. int4 is
REM    actually LARGER because it carries four times the scales. Shrinking below
REM    int8 needs packing, and packing already exists in model/lut.py.
REM
REM  WHAT CHANGED
REM    tensor_mb now counts _emb_code, _emb_scale, _lut_codes and _lut_alpha.
REM    quantize_embedding lowers emb_up together with emb for bf16 and fp16.
REM    paired_eval gained --emb-quant-per-tag so the same checkpoint can appear
REM    twice, quantised and not, which is what measures the actual cost.
REM
REM  GATES
REM    F1  the three int formats no longer report identical residency
REM    F2  bf16 completes at all
REM    F3  int4 residency is NOT below int8 - if it is, the accounting is still wrong
REM    F4  quality cost per format, same checkpoint quantised versus not
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P034_stage5b_emb_quant --note "=============================================================================" "P034 stage 5b   embedding quantisation, re-measured" "Stage 5 reported 38.4 MB and it was fiction - tensor_mb never counted the" "codes. And int4 does not shrink anything without packing." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P034_stage5b_emb_quant --note "[1/6] E0 fp32 reference - the number to beat"
python scripts\runlog.py --name P034_stage5b_emb_quant -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store
if errorlevel 1 echo [WARN] E0 failed - continuing

python scripts\runlog.py --name P034_stage5b_emb_quant --note "[2/6] E1 bf16 - this is the arm that died last time"
python scripts\runlog.py --name P034_stage5b_emb_quant -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store --emb-quant bf16
if errorlevel 1 echo [WARN] E1 failed AGAIN - the emb_up fix did not work, continuing

python scripts\runlog.py --name P034_stage5b_emb_quant --note "[3/6] E3 int8 per-row"
python scripts\runlog.py --name P034_stage5b_emb_quant -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store --emb-quant int8 --emb-chunk 4096
if errorlevel 1 echo [WARN] E3 failed - continuing

python scripts\runlog.py --name P034_stage5b_emb_quant --note "[4/6] E4 int4 group 64 - F3 says this must NOT come out below int8"
python scripts\runlog.py --name P034_stage5b_emb_quant -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store --emb-quant int4 --emb-chunk 4096
if errorlevel 1 echo [WARN] E4 failed - continuing

python scripts\runlog.py --name P034_stage5b_emb_quant --note "[5/6] E5 ternary per-row"
python scripts\runlog.py --name P034_stage5b_emb_quant -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_initonly mC_d36_ag4_nokd --drop-latent --int8-store --emb-quant ternary --emb-chunk 4096
if errorlevel 1 echo [WARN] E5 failed - continuing

echo.
python scripts\runlog.py --name P034_stage5b_emb_quant --note "[6/6] F4 quality - SAME checkpoint, quantised versus not. This is what stage 5 could not do."
python scripts\runlog.py --name P034_stage5b_emb_quant -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_initonly#2 --emb-quant-per-tag mC_initonly=none mC_initonly#2=bf16
if errorlevel 1 echo [WARN] F4 bf16 failed - continuing
python scripts\runlog.py --name P034_stage5b_emb_quant -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_initonly#2 --emb-quant-per-tag mC_initonly=none mC_initonly#2=int8 --emb-chunk 4096
if errorlevel 1 echo [WARN] F4 int8 failed - continuing
python scripts\runlog.py --name P034_stage5b_emb_quant -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_initonly#2 --emb-quant-per-tag mC_initonly=none mC_initonly#2=ternary --emb-chunk 4096
if errorlevel 1 echo [WARN] F4 ternary failed - continuing

echo.
python scripts\runlog.py --name P034_stage5b_emb_quant --note "=============================================================================" "READ IN THIS ORDER" "1. F1. If int8, int4 and ternary still report the same number, tensor_mb is" "   still not counting something and everything below is fiction again." "2. F3. int4 should come out SLIGHTLY LARGER than int8 - same int8 code tensor," "   four times the scales. If int4 looks smaller, the accounting is wrong." "3. F2. bf16 must complete. If it dies the same way, emb_up is not the only" "   fp32 module in that path." "4. F4. THIS is the quality cost, and stage 5 could not measure it. Same" "   checkpoint, quantised against not. Ruler is 2 sigma = 0.0034, not 0.024." "!! The headline for REVIEW3 is the embedding term. LUT already took ternary" "   from 44.7 to 8.88 MiB; the embedding is what is left." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
