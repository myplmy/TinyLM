@echo off
REM =============================================================================
REM  P067 stage 2b  -  the smaller gemma teacher.  about 0.8 hours.
REM
REM  WHY  (result 053 s8)
REM    Stage 2a got the cache built and trained without a teacher at 8.27 GiB.
REM    Then gemma-3-1b-pt as a KD teacher went out of memory in backward. The
REM    cause is known - the largest training VRAM term is the KD loss over the
REM    full vocabulary, and this vocabulary is 262,144 instead of 32,768, which
REM    is 8 times. --kd-chunk splits the KD term but not the backward graph.
REM
REM    gemma-3-270m shares a byte-identical tokenizer with gemma-3-1b-pt (md5
REM    379e7490d90f, checked in the chat template review). So the cache and the
REM    student stay fixed and only the teacher size changes. That is the arm
REM    Qwen cannot give us.
REM
REM  INDEPENDENT VARIABLE
REM    teacher = gemma-3-270m instead of gemma-3-1b-pt. Same shape as 2a.
REM
REM  PREDICTIONS
REM    G1  reserved under 15.0 GiB. The 1b teacher is 999.9M parameters and the
REM        270m is about 3.7x smaller, but the teacher weights were only a small
REM        part of the problem - the logits over 262,144 are the big term and
REM        they do NOT shrink with the teacher. CONFIDENCE IS LOW.
REM    G2  if G1 fails, micro-bs 1 accum 128 is the fallback, and ms/step then
REM        cannot be compared with 2a.
REM    G3  step0 CE near 12.4766 = ln(262144), same as 2a. There is no parent
REM        at this vocabulary.
REM
REM  DO NOT READ VAL. 250 steps measures speed and VRAM only (R13).
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P067_stage2b_gemma270m_teacher --note "=============================================================================" "P067 stage 2b   the smaller gemma teacher" "2a died in backward with the 1B teacher. Same tokenizer, smaller teacher." "Speed and VRAM only - do not read val from 250 steps." "=============================================================================="

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P067_stage2b_gemma270m_teacher --note "[1/2] 270m teacher at the 2a shape - the direct retry"
python scripts\runlog.py --name P067_stage2b_gemma270m_teacher -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --ce-chunk 1024 --kd --kd-every 4 --kd-chunk 512 --teacher-dtype bf16 --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 --kd-teacher-hf HF\models--google--gemma-3-270m --tag G270Tprobe
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P067_stage2b_gemma270m_teacher --note "[2/2] if step 1 died, the narrower shape. ms/step is NOT comparable to 2a."
python scripts\runlog.py --name P067_stage2b_gemma270m_teacher -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 1 --accum 128 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --ce-chunk 512 --kd --kd-every 4 --kd-chunk 256 --teacher-dtype bf16 --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 --kd-teacher-hf HF\models--google--gemma-3-270m --tag G270Tnarrow
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P067_stage2b_gemma270m_teacher --note "=============================================================================" "READ IN THIS ORDER" "1. did step 1 survive backward. That is the whole question." "2. reserved GiB against 15.0. Under it means stage 2 can run at this shape." "3. step0 CE near 12.4766. Trap 34 - suspect the reference before the model." "4. ms/step per token, against 0.0898 from 2a. If step 1 died and step 2 ran," "   that number is NOT comparable - the shape changed." "5. do not read val. 250 steps." "6. if BOTH steps die, the teacher axis is closed at this vocabulary and the" "   remaining option is top-k truncation of the KD loss, a new axis." "=============================================================================="

if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
