@echo off
REM =============================================================================
REM  P067 stage 1b  -  Q256T, a teacher that is actually better than its student
REM                    1 training run plus common_bpb, about 6.0 hours
REM
REM  THE QUESTION THIS REPOSITORY HAS NOT ANSWERED
REM    Result 038 priced KD at minus 0.0032 - zero - and REVIEW2 removed it from
REM    the standard condition. But result 037 had already shown WHY: our teacher
REM    (dense, 3.8080) is WORSE than the student it teaches (3.6984). We removed
REM    KD on evidence gathered with a bad teacher. Q256T is the first run in this
REM    repository where the teacher is genuinely stronger than the student.
REM
REM  !! WHAT IS AT STAKE
REM    If Q256T beats QT0 by more than the resolution, REVIEW2's standard
REM    condition was decided under a confound and the KD axis reopens. That would
REM    change what "standard" means for every future run. If it does not, KD is
REM    dead for good and we stop revisiting it.
REM
REM  !! PREREQUISITE  run_P067_stage1a_qt0.bat MUST HAVE RUN
REM    Its [1] gate proves common_bpb can read these checkpoints, and QT0 is the
REM    control this run is measured against. Without QT0 the delta here mixes
REM    teacher and tokenizer and answers nothing (P067 s3).
REM
REM  ONE FLAG DIFFERENT FROM QT0
REM    --kd --kd-every 4 --kd-chunk 512 --kd-teacher-hf. Everything else, down to
REM    eval-every and the absence of --compile, is byte-identical to 1a.
REM
REM  PREDICTIONS, fixed in advance
REM    G1  Q256T beats QT0 on common_bpb by 0.01 to 0.05 bpb. A real teacher
REM        should do what a bad one could not.
REM    G2  it does NOT beat mC_initonly. The 151,936 vocab handicap (F1) is
REM        larger than any teacher can repay at 132M parameters.
REM    G3  reserved near 10.62 GiB - the probe measured exactly this.
REM    G4  ms/step near 9,114 - also the probe.
REM    G5  IF G1 FAILS, KD is dead regardless of teacher quality, and result 038
REM        stops being "measured with a bad teacher" and becomes conclusive.
REM
REM  WHAT THIS CANNOT DECIDE
REM    Whether KD should return to OUR standard condition. This runs at V=151,936
REM    with no parent initialisation, and result 038 says the parent is worth
REM    plus 0.1386 - 43 times KD. A Qwen teacher cannot be combined with our
REM    parent because the embedding shapes do not match.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P067_stage1b_q256t --note "=============================================================================" "P067 stage 1b   Q256T - the first teacher in this repo better than its student" "REVIEW2 removed KD on evidence from a teacher worse than the student." "PREREQUISITE  run_P067_stage1a_qt0.bat must have produced QT0. About 6 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P067_stage1b_q256t --note "[1/2] Q256T - one flag group different from QT0: the teacher"
python scripts\runlog.py --name P067_stage1b_q256t -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --kd --kd-every 4 --kd-chunk 512 --ce-chunk 1024 --tokenizer-hf HF\models--Qwen3-0.6B-Base --kd-teacher-hf HF\models--Qwen3-0.6B-Base --tag Q256T
if errorlevel 1 echo [WARN] Q256T failed - continuing

python scripts\runlog.py --name P067_stage1b_q256t --note "[wandb] push this run"
set TL_WB_TAG=Q256T
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P067_stage1b_q256t --note "[2/2] common_bpb - Q256T against its control QT0 and against our standard"
python scripts\runlog.py --name P067_stage1b_q256t -- python scripts\common_bpb.py --preset m100R1c --data ko-en --tokens 300M --models Q256T QT0 mC_initonly --tokenizer-hf Q256T=HF\models--Qwen3-0.6B-Base QT0=HF\models--Qwen3-0.6B-Base
if errorlevel 1 echo [WARN] common_bpb failed - continuing

echo.
python scripts\runlog.py --name P067_stage1b_q256t --note "=============================================================================" "READ IN THIS ORDER" "1. json kd must read true, kd_teacher_hf must be set, vocab_size 151936." "   If kd_teacher_hf is empty the run used OUR dense teacher and is void." "2. kd_fwd_steps should be about one quarter of steps (kd_every 4)." "3. grad_max under 10. mb2 is far off our tested shape." "4. Q256T MINUS QT0 on common_bpb is the ONLY number that answers the" "   question. Q256T minus mC_initonly answers a different question (vocab)." "5. resolution: this pair is not on our no-KD sigma. Treat differences under" "   0.01 bpb as unresolved and say so - we have no sigma for this condition." "IF Q256T BEATS QT0  REVIEW2's KD removal was decided under a confound and" "  the axis reopens as 'KD needs a good teacher', not 'KD is useless'." "IF IT DOES NOT  result 038 becomes conclusive and KD closes for good (G5)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
