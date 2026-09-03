@echo off
REM P067 stage 3b  -  measure the number that has now failed three times.
REM About 2 minutes.  No training.
REM
REM   WHY THIS EXISTS.  Two full runs are on disk, 15.9 hours between them,
REM   and the cross-tokenizer comparison they were built for has never been
REM   produced.  Three attempts, three different failures:
REM
REM     stage 2, 2026-09-02   AssertionError.  --tokenizer-hf was given the
REM                           bare-folder form that run100m.py train takes.
REM                           common_bpb takes TAG=folder.  (E14)
REM     stage 2, same log     the call was split across [2] and [3], so even
REM                           with the format fixed each half would have
REM                           printed "fewer than 2 models" and exited 0. (E15)
REM     stage 3, 2026-09-03   CUDA OOM.  Vocabulary 262,144 times 8x1024 rows
REM                           times 4 bytes is exactly 8.00 GiB, allocated in
REM                           one piece by F.cross_entropy(l2.float(), y1).
REM                           --ce-chunk was not passed.  (E22)
REM
REM   E22 IS A REGRESSION, NOT A NEW DEFECT.  Stage 1d already crossed this
REM   trap on 2026-08-27 with --micro-bs 2 --ce-chunk 4096 and produced the
REM   canonical 1.3363.  Those two flags did not travel to the new batch.
REM
REM   WHY --micro-bs 2 AND --ce-chunk BOTH.  --ce-chunk splits only the fp32
REM   copy.  The bf16 logits tensor is micro_bs x seq x vocab x 2B and is
REM   built before any chunking - 4.29 GB at micro-bs 8.  Only --micro-bs
REM   shrinks that.  At mb2 + chunk 1024 the pair costs about 2.1 GB.
REM
REM   THE KD QUESTION IS ALREADY ANSWERED - THIS IS NOT IT.  G270Tfull and
REM   GT0full share tokenizer, cache and seed, so their training-log val is
REM   directly comparable: 3.70938 with KD against 3.70172 without, so no-KD
REM   wins by 0.00766.  See result 053 section 11.2.  What is still missing
REM   is the comparison ACROSS tokenizers, against mC_initonly_nc, and that
REM   is what common_bpb exists for.
REM
REM   CONTAMINATION.  8.7 percent of the SQuAD train documents this scores
REM   overlap our training stream (result 068 section 11.3).  All three
REM   models saw the same stream, so comparing them to each other is valid.
REM   Do NOT put these absolute bpb values beside a published model.
REM   The second call repeats the measurement with those documents dropped,
REM   which is the first time that flag has ever run.
REM
REM   INDEPENDENT VARIABLE: none.  This is a measurement, not an experiment.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P067_stage3b_bpb_remeasure --note "[1/2] common-text bpb - ONE call, THREE models, mb2 + ce-chunk 1024"
python scripts\runlog.py --name P067_stage3b_bpb_remeasure -- python scripts\common_bpb.py --preset m100R1c --models GT0full G270Tfull mC_initonly_nc --micro-bs 2 --ce-chunk 1024 --tokenizer-hf GT0full=HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 G270Tfull=HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29
if errorlevel 1 echo [WARN] step failed - continuing
echo.
REM  --drop-contaminated has never been executed.  It defaults to off and is
REM  bit-identical when off, so this second call is the smoke arm for it
REM  (trap 37: a recorded flag is not a running code path).
python scripts\runlog.py --name P067_stage3b_bpb_remeasure --note "[2/2] same three models with the 348 contaminated documents dropped"
python scripts\runlog.py --name P067_stage3b_bpb_remeasure -- python scripts\common_bpb.py --preset m100R1c --models GT0full G270Tfull mC_initonly_nc --micro-bs 2 --ce-chunk 1024 --drop-contaminated --tokenizer-hf GT0full=HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 G270Tfull=HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P067_stage3b_bpb_remeasure --note "READ IN THIS ORDER" "1. did the [E22] line print a number under 6 GB.  If the tool refused" "   instead, read the command line it printed and use that - the guard" "   is new today and this is its first real run." "2. GT0full minus G270Tfull on common-text bpb.  The training-log val" "   already says no-KD wins by 0.00766.  If bpb disagrees in SIGN, the" "   two measurements are on different text and the val one is closer to" "   what we trained on - say so, do not average them." "3. the bpb ruler is 0.008 and it was fixed under NATIVE conditions." "   A gap inside 0.008 is undetermined, not negative." "4. mC_initonly_nc against either gemma arm answers a DIFFERENT" "   question - vocabulary and parameter count moved too.  It is a" "   deployment comparison, not a KD comparison." "5. compare call [1] against call [2].  If dropping 8.7 percent of the" "   documents moves the RANKING, the contamination is not a common" "   constant and every earlier common_bpb number needs re-reading." "6. one seed."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
