@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  P067 stage 0c  -  re-probe after the teacher-logit dtype fix
REM                    3 short runs, about 25 minutes. Tokenisation already done.
REM
REM  WHAT STAGE 0b FOUND  (result 054)
REM    T1 to T6 ALL PASSED. The external teacher path works:
REM      teacher loads, logits (2,64,151936), tokenizer round trip clean,
REM      cache written as uint32, vocab switched 32768 to 151936, 12.3 min
REM      to tokenise 600M tokens.
REM    Then the 250 step probe died:
REM      _kd_kl -^> F.kl_div: Tried to allocate 594.00 MiB, 14.96 GiB allocated
REM
REM  !! THE CAUSE WAS MY CODE, NOT THE MODEL SIZE
REM    HFTeacher.forward ended with lg.float(). That turns a
REM    (4, 1024, 151936) bf16 tensor into fp32 - a 2.32 GiB SINGLE allocation -
REM    before _kd_kl ever gets to chunk anything. The chunking was working; it
REM    was just chunking a tensor that had already been materialised whole.
REM    Fix: the teacher returns its native dtype, and _kd_kl promotes to fp32
REM    INSIDE each chunk. The fp32-KL rule is unchanged; only WHEN moved.
REM    Expected saving: about 1.16 GiB. We needed 594 MiB.
REM
REM  ALSO ON
REM    --ce-chunk 2048          the plain CE was never chunked (result 054)
REM    PYTORCH_ALLOC_CONF       torch suggested it in the traceback. Set here,
REM                             temporarily, cleared on exit.
REM
REM  THE LADDER
REM    1  micro-bs 4, kd-chunk 1024   the same shape that died. Did the fix work
REM    2  micro-bs 2, kd-chunk 512    fallback if 1 still dies
REM    3  gemma-3-270m teacher        different failure mode: teacher half the
REM                                   size but vocab 262144 instead of 151936.
REM                                   !! This measures WHICH term dominates -
REM                                   teacher weights or vocabulary width.
REM
REM  !! WHATEVER HAPPENS, DO NOT COMPARE val TO ANY EXISTING RUN
REM    Different tokenizer means different val token boundaries (trap 2).
REM    Cross comparison is only valid through scripts\common_bpb.py.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

set PYTORCH_ALLOC_CONF=expandable_segments:True

echo.
python scripts\runlog.py --name P067_stage0c_teacher_gate --note "=============================================================================" "P067 stage 0c   re-probe after the teacher-logit dtype fix" "Stage 0b passed every gate and then OOMed because HFTeacher.forward called" "lg.float() on a (4,1024,151936) tensor - a 2.32 GiB single allocation." "That was my code, not the model size." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P067_stage0c_teacher_gate --note "[1/3] the same shape that died in stage 0b - micro-bs 4, kd-chunk 1024"
python scripts\runlog.py --name P067_stage0c_teacher_gate -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 4 --accum 32 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --kd --kd-every 4 --kd-chunk 1024 --ce-chunk 2048 --tokenizer-hf HF\models--Qwen3-0.6B-Base --kd-teacher-hf HF\models--Qwen3-0.6B-Base --tag pq_q3_mb4
if errorlevel 1 echo [WARN] pq_q3_mb4 failed - the fallback below is why arm 2 exists, continuing

echo.
python scripts\runlog.py --name P067_stage0c_teacher_gate --note "[wait] let WDDM release VRAM - result 037 s7.3"
timeout /t 15 /nobreak

python scripts\runlog.py --name P067_stage0c_teacher_gate --note "[2/3] fallback - micro-bs 2, kd-chunk 512. Effective batch stays 131072 tokens."
python scripts\runlog.py --name P067_stage0c_teacher_gate -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --kd --kd-every 4 --kd-chunk 512 --ce-chunk 1024 --tokenizer-hf HF\models--Qwen3-0.6B-Base --kd-teacher-hf HF\models--Qwen3-0.6B-Base --tag pq_q3_mb2
if errorlevel 1 echo [WARN] pq_q3_mb2 failed - continuing

echo.
python scripts\runlog.py --name P067_stage0c_teacher_gate --note "[wait] let WDDM release VRAM"
timeout /t 15 /nobreak

python scripts\runlog.py --name P067_stage0c_teacher_gate --note "[3/3] gemma-3-270m gate only - teacher is half the size but vocab is 262144"
python scripts\runlog.py --name P067_stage0c_teacher_gate -- python scripts\diag_p067_teacher.py --teacher HF\models--google--gemma-3-270m
if errorlevel 1 echo [WARN] gemma gate failed - continuing

echo.
python scripts\runlog.py --name P067_stage0c_teacher_gate --note "[wandb] push the probes"
set TL_WB_TAG=pq_
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P067_stage0c_teacher_gate --note "=============================================================================" "READ IN THIS ORDER" "1. did arm 1 survive. If yes the dtype fix closed a 1.16 GiB hole and the" "   original micro-bs 4 shape is usable." "2. if arm 1 died and arm 2 lived, the vocabulary is simply too wide for" "   M=4096 and we run P067 at M=2048. That costs wall clock, not validity -" "   effective batch is 131072 tokens in both." "3. json must show vocab_size 151936, kd_teacher_hf set, token_dtype uint32." "   If vocab_size reads 32768 the flag did not land and the run is a plain" "   no-KD reseed (trap 37)." "4. arm 3 tells us which term dominates. gemma-3-270m has HALF the teacher" "   weights but a WIDER vocabulary (262144 vs 151936). If its reported VRAM" "   is higher, the vocabulary dominates and a smaller teacher does not help." "!! val from this run is NOT comparable to anything (trap 2). common_bpb only." "=============================================================================="
set PYTORCH_ALLOC_CONF=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
set PYTORCH_ALLOC_CONF=
if not defined TL_NOPAUSE pause
exit /b 1
