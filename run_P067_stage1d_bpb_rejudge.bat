@echo off
REM =============================================================================
REM  P067 stage 1d  -  re-run the judgement that OOMed, no training
REM                    diagnostics only, about 15 minutes
REM
REM  WHAT HAPPENED  (results 053, stages 1a, 1b and 1c)
REM    All three training runs finished - 21.5 hours of GPU. All three judgement
REM    steps died:
REM        common_bpb.py line 154
REM        torch.OutOfMemoryError: Tried to allocate 4.64 GiB
REM    That number is exactly micro_bs 8 times seq 1024 times 151936 times 4B.
REM    The cross-entropy logits tensor, materialised in one piece.
REM
REM  !! THIS IS A LESSON WE WROTE DOWN AND THEN IGNORED
REM    Result 053 stage 0-c says: the M = 8192 knee is a vocab-32,768 number,
REM    not a constant; at 4.6x the vocabulary the micro batch has to come down.
REM    The TRAINING batches respected that and used micro-bs 2. The JUDGEMENT
REM    tool kept its default of 8 and nobody checked. Trap 37 in a new costume:
REM    the axis was turned on in one path and left off in another.
REM
REM  THE FIX  (2026-08-26)
REM    common_bpb.py gained --ce-chunk, the same shape P071 verified for the
REM    training loss - chunk the rows instead of materialising the whole
REM    vocabulary at once. Default 0 keeps the old path bit-identical. This
REM    batch also passes --micro-bs 2, belt and braces.
REM
REM  WHAT SURVIVED THE CRASH
REM    Enough to read the answer, as it happens. Each call printed its FIRST
REM    model before dying on the second:
REM        mC_initonly  1.3075   (stage 1a step 3, which completed)
REM        QT0          1.3440   (stage 1a step 3)
REM        Q256T        1.3362   (stage 1b, printed before the crash)
REM        Q64T         1.3999   (stage 1c, printed before the crash)
REM    All four on the same 641,795 token stream, so the matrix is readable.
REM    This batch re-runs it IN ONE CALL so the numbers are provably comparable
REM    instead of assembled by hand from three logs.
REM
REM  PREDICTIONS, fixed in advance
REM    R1  the four values reproduce to four decimals. This is deterministic.
REM        If they do not, assembling them by hand was wrong and result 053
REM        stage 1 needs correcting before anything is built on it.
REM    R2  Q256T minus QT0 stays near minus 0.008 bpb - right at the practical
REM        resolution, not past it.
REM    R3  it does not OOM. If it does, --ce-chunk is not the whole story and
REM        the model itself is too big to hold two at once at this vocabulary.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P067_stage1d_bpb_rejudge --note "=============================================================================" "P067 stage 1d   re-run the judgement that OOMed" "Three training runs finished; all three judgement steps died on a 4.64 GiB" "single allocation. --ce-chunk fixes it. No training. About 15 minutes." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P067_stage1d_bpb_rejudge --note "[1/1] the whole stage 1 matrix in ONE call, chunked CE, micro-bs 2"
python scripts\runlog.py --name P067_stage1d_bpb_rejudge -- python scripts\common_bpb.py --preset m100R1c --data ko-en --tokens 300M --micro-bs 2 --ce-chunk 4096 --models Q64T Q256T QT0 mC_initonly --tokenizer-hf Q64T=HF\models--Qwen3-0.6B-Base Q256T=HF\models--Qwen3-0.6B-Base QT0=HF\models--Qwen3-0.6B-Base
if errorlevel 1 echo [WARN] common_bpb STILL failed - read the traceback

echo.
python scripts\runlog.py --name P067_stage1d_bpb_rejudge --note "=============================================================================" "READ IN THIS ORDER" "1. R1 - do the four bpb values match what the three crashed logs printed" "   (1.3999 / 1.3362 / 1.3440 / 1.3075). They should, to four decimals." "2. Q256T MINUS QT0 is the answer to the whole P067 question. That is the" "   teacher's contribution with a teacher genuinely better than its student." "   Everything else in the table answers a different question." "3. the tool prints 0.008 bpb as the practical resolution. If the delta is" "   under it, write UNRESOLVED - do not rank." "4. Q64T minus Q256T is the rank price WITH a good teacher." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
