@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  P065 stage 2b  -  re-probe after the CE chunking fix
REM                    4 short runs, 250 steps each, about 1 hour
REM
REM  WHAT STAGE 2 FOUND  (result 054)
REM    Both arms died at the SAME line, and it was not the model forward:
REM        ce = F.cross_entropy(logits.reshape(-1, vocab), y.reshape(-1))
REM        OutOfMemoryError: Tried to allocate 512.00 MiB ... 0 bytes is free
REM        d36: 14.73 GiB allocated   r20 recursion: 14.84 GiB allocated
REM    512 MiB is 8192 x 32768 x 2B. --kd-chunk splits the KD loss only; the
REM    plain CE had never been split. In a no-KD run the KD chunking does
REM    nothing, so no-KD plus --no-ckpt is exactly where this term surfaces.
REM
REM  WHAT CHANGED
REM    --ce-chunk N splits the mean CE by rows. It does NOT remove the tensors
REM    that backward needs - it removes the SIMULTANEOUS temporaries, which is
REM    what the 512 MiB was. Expected saving is a few hundred MiB, not GiB.
REM    PYTORCH_ALLOC_CONF=expandable_segments:True is set below because torch
REM    itself suggested it in the traceback. It is set HERE, temporarily, and
REM    cleared on exit - the user's environment is not modified.
REM
REM  THE LADDER, and why arms 2 and 4 are here
REM    1  d36 + --no-ckpt + --ce-chunk      the question
REM    2  d36 + grad ckpt  + --ce-chunk     known-good control
REM    3  r20 recursion + --no-ckpt + chunk the question
REM    4  r20 recursion + grad ckpt         known-good control (= mC_r20_nokd)
REM    !! If 1 fails and 2 passes, the cause is --no-ckpt and NOT a bug in the
REM       new code. That distinction is the whole point of running 2 and 4.
REM
REM  !! READ ONLY VRAM AND ms/step. DO NOT READ val.
REM    250 steps is a memory probe. Result 046 is the model for this usage.
REM
REM  GATE
REM    pass  reserved under 14.0 GiB AND skip 0 AND no CUBLAS_STATUS failure
REM    fail  above 14.0 - WDDM spills between 13 and 14 and a spill is silent
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM temporary, this process only. cleared on every exit path below.
set PYTORCH_ALLOC_CONF=expandable_segments:True

echo.
python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "=============================================================================" "P065 stage 2b   re-probe after the CE chunking fix" "Stage 2 died in F.cross_entropy, not in the model. --kd-chunk never covered" "the plain CE, and a no-KD run is exactly where that shows." "Arms 2 and 4 are known-good controls: if 1 fails and 2 passes, the cause is" "--no-ckpt and not the new code." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "[1/4] d36 + --no-ckpt + --ce-chunk 2048   THE QUESTION"
python scripts\runlog.py --name P065_stage2b_nockpt_vram -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --attn-group 4 --init-from --no-ckpt --ce-chunk 2048 --tag pb_d36_nock_cc
if errorlevel 1 echo [WARN] pb_d36_nock_cc failed - that IS an answer, continuing

echo.
python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "[wait] let WDDM release VRAM - result 037 s7.3"
timeout /t 15 /nobreak

python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "[2/4] d36 + grad ckpt + --ce-chunk 2048   CONTROL, expected to pass"
python scripts\runlog.py --name P065_stage2b_nockpt_vram -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --attn-group 4 --init-from --ce-chunk 2048 --tag pb_d36_ckpt_cc
if errorlevel 1 echo [WARN] pb_d36_ckpt_cc failed - THIS ONE FAILING WOULD MEAN A BUG, continuing

echo.
python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "[wait] let WDDM release VRAM"
timeout /t 15 /nobreak

python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "[3/4] r20 recursion + --no-ckpt + --ce-chunk 2048   THE QUESTION"
python scripts\runlog.py --name P065_stage2b_nockpt_vram -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --train-repeat 2.0 --init-from --no-ckpt --ce-chunk 2048 --tag pb_r20_nock_cc
if errorlevel 1 echo [WARN] pb_r20_nock_cc failed - that IS an answer, continuing

echo.
python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "[wait] let WDDM release VRAM"
timeout /t 15 /nobreak

python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "[4/4] r20 recursion + grad ckpt   CONTROL, this is how mC_r20_nokd ran"
python scripts\runlog.py --name P065_stage2b_nockpt_vram -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --train-repeat 2.0 --init-from --tag pb_r20_ckpt
if errorlevel 1 echo [WARN] pb_r20_ckpt failed - THIS ONE FAILING WOULD MEAN A BUG, continuing

echo.
python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "[wandb] push all four probes"
set TL_WB_TAG=pb_
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P065_stage2b_nockpt_vram --note "=============================================================================" "READ IN THIS ORDER" "1. WHICH arms died. The pattern is the answer:" "   1 and 3 die, 2 and 4 live  -^> --no-ckpt does not fit. Keep grad ckpt at" "                                 36 layers and under recursion. NOT a bug." "   2 or 4 dies                -^> a bug in the new code. Stop and fix." "   all four live              -^> --ce-chunk closed the gap. --no-ckpt opens" "                                 for both conditions and every later run" "                                 gets 20 percent." "2. vram_reserved_gb from the json, not the console. Gate is under 14.0." "3. ms_step_median between 1 and 2, and between 3 and 4. That is the price of" "   grad checkpointing in THIS condition - result 051 measured 20.6 percent" "   at 20 layers without recursion, and it is condition dependent." "!! DO NOT READ val. 250 steps cannot rank quality." "=============================================================================="
set PYTORCH_ALLOC_CONF=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
set PYTORCH_ALLOC_CONF=
if not defined TL_NOPAUSE pause
exit /b 1
