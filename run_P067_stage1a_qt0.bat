@echo off
REM =============================================================================
REM  P067 stage 1a  -  QT0, the confound control nobody has run
REM                    1 gate plus 1 training run, about 4.9 hours
REM
REM  WHAT THIS ANSWERS
REM    P067 asks whether KD was useless because KD is useless, or because OUR
REM    teacher is bad. Result 037 measured that our KD teacher (dense, 3.8080) is
REM    WORSE than the student it teaches (mC_wsd, 3.6984). Result 038 then priced
REM    KD at minus 0.0032 - indistinguishable from zero - and REVIEW2 removed it
REM    from the standard condition ON THAT EVIDENCE.
REM
REM  WHY QT0 COMES FIRST
REM    Swapping to a Qwen3-0.6B teacher changes TWO things at once: the teacher
REM    AND the tokenizer (vocab 32,768 to 151,936). Without a Qwen-tokenizer,
REM    NO-teacher control, the two can never be separated. QT0 is that control.
REM    P067 s3 calls it "the condition the original plan was missing".
REM
REM  !! JUDGEMENT IS common_bpb ONLY
REM    val_loss across tokenizers is meaningless (trap 2, result 011). Even bpb
REM    on our own cache is not comparable. scripts\common_bpb.py scores the SAME
REM    raw text through each model's own tokenizer and is the only valid path.
REM    Step [1] proves that path works BEFORE spending five hours.
REM
REM  !! CONFIGURATION IS FROZEN TO THE ONLY MEASURED ONE
REM    micro-bs 2, accum 64, no --compile, eval-every 250. That is exactly
REM    result 053 stage 0-c, which completed 250 steps at reserved 10.62 GiB.
REM    M = 2048 is far below the knee of 8192, but the knee is a vocab-32,768
REM    number - at 151,936 the CE tensor is 4.6x larger and mb8 does not fit.
REM    All three P067 stage 1 batches share these numbers so that the only
REM    difference between them is the one being measured.
REM
REM  PREDICTIONS, fixed in advance
REM    F1  QT0 common_bpb is WORSE than mC_initonly. A 151,936 vocab on a 132M
REM        model spends parameters on embeddings we cannot afford.
REM    F2  ms/step near 7,000 to 8,000 - the 9,114 of the probe minus the teacher
REM        forward on one step in four.
REM    F3  reserved well under 10.62 GiB. No teacher, no teacher logits.
REM    F4  grad_max under 10. If not, mb2 is destabilising and the whole P067
REM        stage 1 matrix is unreadable - stop before running 1b and 1c.
REM
REM  WHAT THIS CANNOT DECIDE
REM    Anything about KD. That is 1b minus 1a. This run only establishes the
REM    Qwen-tokenizer baseline that 1b and 1c are measured against.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P067_stage1a_qt0 --note "=============================================================================" "P067 stage 1a   QT0 - Qwen tokenizer, NO teacher" "The control that separates 'teacher' from 'tokenizer'. Without it the" "stage 1 matrix cannot attribute anything. About 4.9 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P067_stage1a_qt0 --note "[1/3] PREREQUISITE GATE - can common_bpb read an external-tokenizer checkpoint"
python scripts\runlog.py --name P067_stage1a_qt0 -- python scripts\common_bpb.py --preset m100R1c --data ko-en --tokens 300M --models pq_q3_mb2 mC_initonly --tokenizer-hf pq_q3_mb2=HF\models--Qwen3-0.6B-Base --max-docs 400
if errorlevel 1 goto ERROR

echo.
python scripts\runlog.py --name P067_stage1a_qt0 --note "[2/3] QT0 - Qwen tokenizer, no teacher, no parent (shapes do not match at V=151936)"
python scripts\runlog.py --name P067_stage1a_qt0 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --ce-chunk 1024 --tokenizer-hf HF\models--Qwen3-0.6B-Base --tag QT0
if errorlevel 1 echo [WARN] QT0 failed - continuing

python scripts\runlog.py --name P067_stage1a_qt0 --note "[wandb] push this run"
set TL_WB_TAG=QT0
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P067_stage1a_qt0 --note "[3/3] common_bpb - the ONLY valid cross-tokenizer judgement"
python scripts\runlog.py --name P067_stage1a_qt0 -- python scripts\common_bpb.py --preset m100R1c --data ko-en --tokens 300M --models QT0 mC_initonly --tokenizer-hf QT0=HF\models--Qwen3-0.6B-Base
if errorlevel 1 echo [WARN] common_bpb failed - continuing

echo.
python scripts\runlog.py --name P067_stage1a_qt0 --note "=============================================================================" "READ IN THIS ORDER" "1. step [1] must have passed. It is a goto ERROR gate on purpose - if the" "   tool cannot score an external-tokenizer checkpoint, nothing downstream" "   can be compared and the five hours are wasted." "2. json vocab_size must read 151936 and tokenizer_hf must be set. If vocab" "   reads 32768 the tokenizer flag did not land and this is a reseed." "3. grad_max against F4. Over 10 means STOP - do not start 1b or 1c." "4. reserved against F3, ms/step against F2." "5. common_bpb ONLY for quality. Do NOT compare val_loss to any run on our" "   own tokenizer (trap 2). Within the Qwen family (QT0, Q256T, Q64T) the" "   val sets ARE the same, so their val_loss IS mutually comparable - but" "   paired_eval cannot reach that cache, so treat it as a coarse read." "IF F1 HOLDS  a big vocab costs us, which is expected and is not the point." "THE POINT IS THE BASELINE  1b minus this = the teacher's contribution." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:ERROR
echo.
python scripts\runlog.py --name P067_stage1a_qt0 --note "[STOP] common_bpb cannot read the external-tokenizer checkpoint." "P067 s7 flagged this as unverified. Fix the tool before running any of the" "stage 1 arms - without it there is no valid way to judge them."
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
