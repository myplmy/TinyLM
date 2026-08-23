@echo off
REM =============================================================================
REM  P067 stage 1c  -  Q64T, can a strong teacher pay for a crushed embedding
REM                    1 training run plus common_bpb, about 5.9 hours
REM
REM  THE QUESTION
REM    A 151,936 vocab is unaffordable for us at E=256 - the embedding term alone
REM    dominates residency, which is the whole subject of REVIEW3. E=64 is the
REM    aggressive setting that would make a big vocab affordable. Result 030 s9
REM    measured the initialisation handicap of a crushed embedding (plus 0.1123
REM    random, plus 0.0645 with SVD transplant) but never with a strong teacher.
REM
REM  WHY IT BELONGS IN THIS MATRIX
REM    P067 s3 defines it as "Q256T plus one flag: rank". Distillation is the one
REM    mechanism that could repay a rank handicap, because the teacher supplies a
REM    full-rank target distribution the student would otherwise have to infer.
REM    If a strong teacher cannot repay E=64, nothing can and the rank axis has a
REM    floor well above 64.
REM
REM  !! PREREQUISITE  run_P067_stage1b_q256t.bat MUST HAVE RUN
REM    Q256T is the control. Against QT0 this run mixes teacher and rank.
REM
REM  !! THERE IS NO SVD TRANSPLANT HERE
REM    _svd_emb_init needs a parent, and no parent exists at V=151,936. So E=64
REM    starts random. Result 030 says that costs about plus 0.1123 on its own -
REM    EXPECT A LARGE NUMBER and do not read it as the price of rank.
REM
REM  PREDICTIONS, fixed in advance
REM    H1  Q64T is WORSE than Q256T by 0.05 to 0.15 bpb. Random initialisation
REM        plus rank loss, only partly repaid by the teacher.
REM    H2  grad_max is the thing to watch, not the loss. Result 030 saw 19.32
REM        when the embedding started random. If it is over 10 here, the delta
REM        is not a rank measurement and must not enter the lever table.
REM    H3  step0 ce near ln(151936) = 11.93 confirms the random start. That is
REM        EXPECTED here, unlike everywhere else in this repo.
REM    H4  resident drops sharply - the embedding is the dominant term at this
REM        vocab. Report fp32 and int8 separately (trap 24).
REM
REM  WHAT THIS CANNOT DECIDE
REM    The rank floor for OUR vocab. 32,768 and 151,936 are different problems
REM    and result 032 s8.3 says lever price does not extrapolate.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P067_stage1c_q64t --note "=============================================================================" "P067 stage 1c   Q64T - can a strong teacher pay for a crushed embedding" "One flag different from Q256T: --emb-rank 64. No SVD transplant is possible" "at this vocab, so expect a large number. PREREQUISITE  stage 1b. About 5.9 h." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P067_stage1c_q64t --note "[1/3] Q64T - one flag different from Q256T"
python scripts\runlog.py --name P067_stage1c_q64t -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --kd --kd-every 4 --kd-chunk 512 --ce-chunk 1024 --emb-rank 64 --tokenizer-hf HF\models--Qwen3-0.6B-Base --kd-teacher-hf HF\models--Qwen3-0.6B-Base --tag Q64T
if errorlevel 1 echo [WARN] Q64T failed - continuing

python scripts\runlog.py --name P067_stage1c_q64t --note "[wandb] push this run"
set TL_WB_TAG=Q64T
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P067_stage1c_q64t --note "[2/3] common_bpb - the full stage 1 matrix in one table"
python scripts\runlog.py --name P067_stage1c_q64t -- python scripts\common_bpb.py --preset m100R1c --data ko-en --tokens 300M --models Q64T Q256T QT0 mC_initonly --tokenizer-hf Q64T=HF\models--Qwen3-0.6B-Base Q256T=HF\models--Qwen3-0.6B-Base QT0=HF\models--Qwen3-0.6B-Base
if errorlevel 1 echo [WARN] common_bpb failed - continuing

echo.
python scripts\runlog.py --name P067_stage1c_q64t --note "[3/3] residency - the reason E=64 was worth asking about"
python scripts\runlog.py --name P067_stage1c_q64t -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models Q64T Q256T --drop-latent
if errorlevel 1 echo [WARN] mem_runtime fp32 failed - continuing
python scripts\runlog.py --name P067_stage1c_q64t -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models Q64T Q256T --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime int8 failed - continuing

echo.
python scripts\runlog.py --name P067_stage1c_q64t --note "=============================================================================" "READ IN THIS ORDER" "1. json emb_rank must read 64 and kd_teacher_hf must be set." "2. grad_max BEFORE the loss (H2). Over 10 and this is not a rank number." "3. step0 ce near 11.93 = ln(151936) is EXPECTED here (H3). Elsewhere in this" "   repo that value means initialisation failure - not here, there is no" "   parent to transplant from." "4. Q64T minus Q256T is the rank price WITH a teacher. Q64T minus QT0 is not" "   a clean number - it mixes teacher and rank." "5. step [3] prints fp32 and int8 residency. Quote both or neither (trap 24)." "IF THE TEACHER REPAYS MOST OF THE RANK LOSS  distillation becomes a" "  compression tool and not just a quality tool - that is a new axis." "IF IT DOES NOT  E=64 has no path at any vocab and the rank floor is higher." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
