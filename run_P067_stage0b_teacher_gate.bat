@echo off
REM =============================================================================
REM  P067 stage 0b  -  does the external teacher path actually run
REM                    plus tokenise the corpus with the teacher tokenizer
REM                    plus a 250 step VRAM probe
REM                    about 1.2 hours, most of it tokenisation
REM
REM  WHAT P067 IS ACTUALLY ASKING  (user, 2026-08-22)
REM    1. can a better teacher raise training efficiency
REM    2. !! was KD useless because KD is useless, or because OUR DENSE WAS BAD
REM
REM    The second one is the real question. Result 038 measured parent-init worth
REM    +0.1386 and KD worth -0.0032, a factor of 43, and concluded KD does not
REM    pay. But our teacher was a dense model trained on OUR corpus at OUR size.
REM    "KD does not help" and "our teacher has nothing to teach" produce the same
REM    number. A frontier 0.6B teacher separates them.
REM
REM  WHY THE TOKENIZER MUST CHANGE
REM    Online KD compares teacher and student logits on the SAME vocabulary.
REM    Different vocabularies make the KL undefined. Vocabulary mapping loses
REM    information and is a large build, so per the user instruction we move the
REM    STUDENT onto the teacher tokenizer and accept the model growing.
REM
REM  !! WHAT THIS BATCH DOES NOT DO
REM    It does not adopt the teacher ARCHITECTURE. Result 053 found Gemma shares
REM    KV across 20 of 35 layers and Qwen3.5 replaces 18 of 24 attentions with
REM    linear attention. Interesting, and explicitly OUT OF SCOPE - adopting them
REM    would confound this experiment and force a new baseline.
REM
REM  TEACHER CHOICE, and why Qwen3-0.6B-Base first
REM    Qwen3-0.6B-Base   28L/1024, vocab 151936, pure text ForCausalLM, bf16
REM    gemma-3-270m      18L/640,  vocab 262144, pure text ForCausalLM, bf16
REM    Qwen3.5-0.8B and gemma-4-E2B are ForConditionalGeneration - multimodal.
REM    Qwen3 wins on vocabulary: 151936 versus 262144. Our embedding goes
REM    25.2M to 116.7M with Qwen3, or to 201.3M with Gemma3. Both hurt; Qwen3
REM    hurts 1.7x less.
REM
REM  !! THE VRAM RISK IS THE VOCABULARY, NOT THE TEACHER
REM    Result 038: the KD loss over the full vocabulary cost +5.48 GiB at vocab
REM    32768. At 151936 that term is 4.6x larger. The teacher weights are only
REM    1.2 GiB in bf16 - they are not the problem. That is why step [3] is a
REM    250 step probe with a REDUCED micro-bs and --kd-chunk on.
REM
REM  GATES
REM    T1-T6  diag_p067_teacher.py prints its own criteria first
REM    V      probe reserved under 14.0 GiB and skip 0
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P067_stage0b_teacher_gate --note "=============================================================================" "P067 stage 0b   external teacher gate + tokenisation + VRAM probe" "The real question: was KD useless, or was OUR DENSE TEACHER useless." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P067_stage0b_teacher_gate --note "[1/4] candidate survey - config.json only, no torch, no GPU"
python scripts\runlog.py --name P067_stage0b_teacher_gate -- python scripts\diag_p067_teacher.py --spec-only
if errorlevel 1 echo [WARN] spec survey failed - continuing

echo.
python scripts\runlog.py --name P067_stage0b_teacher_gate --note "[2/4] T1 to T6 on Qwen3-0.6B-Base - load, forward, logit dtype, tokenizer round trip"
python scripts\runlog.py --name P067_stage0b_teacher_gate -- python scripts\diag_p067_teacher.py --teacher HF\models--Qwen3-0.6B-Base
if errorlevel 1 goto ERROR

echo.
python scripts\runlog.py --name P067_stage0b_teacher_gate --note "[3/4] tokenise the corpus with the teacher tokenizer - SEPARATE cache directory"
python scripts\runlog.py --name P067_stage0b_teacher_gate -- python run100m.py prepare --data ko-en --tokens 600M --exact-cache --tokenizer-hf HF\models--Qwen3-0.6B-Base
if errorlevel 1 goto ERROR

echo.
python scripts\runlog.py --name P067_stage0b_teacher_gate --note "[4/4] 250 step VRAM probe - reduced micro-bs and kd-chunk because the vocab is 4.6x"
python scripts\runlog.py --name P067_stage0b_teacher_gate -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 4 --accum 32 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --kd --kd-every 4 --kd-chunk 1024 --tokenizer-hf HF\models--Qwen3-0.6B-Base --kd-teacher-hf HF\models--Qwen3-0.6B-Base --tag probe_q3teach
if errorlevel 1 echo [WARN] probe_q3teach failed - THAT IS THE ANSWER, read the error, continuing

echo.
python scripts\runlog.py --name P067_stage0b_teacher_gate --note "[wandb] push the probe"
set TL_WB_TAG=probe_q3teach
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P067_stage0b_teacher_gate --note "=============================================================================" "READ IN THIS ORDER" "1. T1 in step [2]. If the teacher will not load, nothing below matters." "2. T4. Logits MUST be fp32. bf16 log_softmax crushes the tail and the KL" "   would be measuring rounding, not the teacher." "3. step [3] must print token_dtype uint32. Qwen3 vocab is 151936 and uint16" "   holds 65536 - writing uint16 would WRAP IDS SILENTLY and the model would" "   learn garbage while the loss looked fine." "4. step [4] vram_reserved_gb. Gate is under 14.0. If it OOMs, halve micro-bs" "   and double accum - the effective batch must stay 131072 tokens." "5. json vocab_size must read 151936 and kd_teacher_hf must be set." "!! DO NOT COMPARE THIS RUN's val TO ANY EXISTING RUN. Different tokenizer" "   means different val token boundaries (trap 2). Cross comparison is only" "   valid through scripts\\common_bpb.py." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:ERROR
echo.
python scripts\runlog.py --name P067_stage0b_teacher_gate --note "[STOP] a prerequisite step failed. Later steps depend on it - stopping." "If step [2] failed the teacher path does not run: fix that first." "If step [3] failed there is no tokenised cache to train on."
if not defined TL_NOPAUSE pause
exit /b 2

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
