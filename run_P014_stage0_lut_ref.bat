@echo off
REM =============================================================================
REM  P014 stage 0  -  LUT reference implementation gate. No training, no GPU.
REM                   plus stage 1 residency on the real model. about 20 minutes
REM
REM  WHY NOW  (2026-08-22 user instruction: start the LUT kernel)
REM    Result 052 s3.1 settled it: int8 ternary cannot reach 40 MiB resident.
REM    int8 spends 8 bits per weight where the information content is log2(3) =
REM    1.585 bits. That is 5.05x thrown away, and no amount of embedding
REM    quantisation buys it back.
REM
REM  WHAT THIS GATE DOES AND DOES NOT DO
REM    does      packing format round trip, LUT matmul correctness, group scale
REM              acceptance, measured bpw, residency arithmetic
REM    does NOT   speed. The reference is written in PyTorch and it is SLOW.
REM              Measuring it would produce the false headline "LUT is slow".
REM              The speed gate belongs to P014B. check_fused_int8.py refuses to
REM              measure speed for the same reason.
REM
REM  WHY CORRECTNESS FIRST
REM    P014B s1.1 lists three unknowns. U2 (does the kernel accept our g128 group
REM    scale) and the memory number can both be answered with a slow reference.
REM    If either is negative a fast kernel would not help. Close the cheap ones.
REM
REM  GATES, fixed in advance
REM    L1  packing round trip mismatches        0
REM    L2  LUT versus dense relative error      under 1e-5
REM    L3  group scale accepted                 yes
REM    L4  measured bpw                         1.600
REM    L5  residency arithmetic                 reproduces result 052 within 1 MiB
REM
REM  !! L5 CARRIES A CORRECTION
REM    Result 052 s3.1 reports LUT plus emb int8 = 18.3 MiB. That row is for
REM    m100R1q, whose embedding is FACTORISED. The standard model confirmed on
REM    2026-08-22, mC_d36_ag4_nokd, has a full 32768x768 embedding. Copying that
REM    18.3 onto the standard model would be wrong. The tool prints both.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P014_stage0_lut_ref --note "=============================================================================" "P014 stage 0   LUT reference implementation gate   no training, no GPU" "Result 052: int8 cannot reach 40 MiB. 8 bits per weight for log2(3) = 1.585." "Speed is deliberately NOT measured here - that is P014B." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P014_stage0_lut_ref --note "[1/2] synthetic gates L1 to L4 plus residency arithmetic"
python scripts\runlog.py --name P014_stage0_lut_ref -- python scripts\diag_lut_kernel.py --dim 768 --out 2048 --micro-group 128
if errorlevel 1 echo [WARN] lut gate reported a failure - read WHICH gate, continuing

echo.
python scripts\runlog.py --name P014_stage0_lut_ref --note "[2/2] same gates against the standard model checkpoint - real weight count"
python scripts\runlog.py --name P014_stage0_lut_ref -- python scripts\diag_lut_kernel.py --dim 768 --out 2048 --micro-group 128 --ckpt runs\ckpt\m100R1d_ko-en_300M_mC_d36_ag4_nokd.pt
if errorlevel 1 echo [WARN] checkpoint pass failed - continuing

echo.
python scripts\runlog.py --name P014_stage0_lut_ref --note "[3/4] STAGE 1 - the LUT deployment path on the real model, resident memory"
python scripts\runlog.py --name P014_stage0_lut_ref -- python scripts\mem_runtime.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_nokd --device cpu --drop-latent --lut --lut-out-chunk 512
if errorlevel 1 echo [WARN] lut residency failed - continuing

echo.
python scripts\runlog.py --name P014_stage0_lut_ref --note "[4/4] the int8 path on the SAME model, so the two numbers are comparable"
python scripts\runlog.py --name P014_stage0_lut_ref -- python scripts\mem_runtime.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_nokd --device cpu --drop-latent --int8-store
if errorlevel 1 echo [WARN] int8 residency failed - continuing

echo.
python scripts\runlog.py --name P014_stage0_lut_ref --note "=============================================================================" "READ IN THIS ORDER" "1. L1. A single mismatch means the packing format is broken and nothing" "   below it means anything." "2. L2 and L3. These are exact arithmetic - anything above 1e-6 is a bug," "   not a rounding effect." "3. L4. Expect 1.600. Result 052 assumed 1.71 - if they disagree, 052 was an" "   assumption and this is a measurement." "4. L5 part (A) must land within 1 MiB of 18.3. If it does not, say so - do" "   not quietly adopt the new number (trap 34: suspect the reference value)." "5. L5 part (B) is NEW. The standard model has a full embedding, so its LUT" "   number is larger than 18.3. That is the number that matters now." "6. step [3] versus step [4] is THE number - LUT resident against int8 resident" "   on the SAME checkpoint. Expect about 5x on the ternary term: int8 spends 8" "   bits where the information content is 1.585." "7. step [3] logit difference is NOT zero and that is CORRECT. LUT re-estimates" "   alpha per row, because 768 has no divisor that is a multiple of 5. The cost" "   was measured in result 028: +0.0038 to 0.0068 bpb, under the 0.008 ruler." "   If it is far larger than that, the alpha re-estimation is wrong." "NEXT  P014B owns the speed question (U1: is LUT a win at dim 768)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
