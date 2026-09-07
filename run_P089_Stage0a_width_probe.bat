@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P089_Stage0a_width_probe.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     We have never changed the width. Every preset except tiny is dim 768,
REM     and all 161 full-train runs used it. The whole width case rests on one
REM     unmeasured assumption: that decode time is bandwidth bound, so ms per
REM     visit falls linearly with dim. If that is wrong the axis loses half its
REM     value before we spend 8 hours on it.
REM
REM     mem_runtime and bench_infer both LOAD a checkpoint, so a zero-training
REM     probe is impossible. 250 steps is the cheapest way to get a file, and
REM     it also gives VRAM and ms/step for free.
REM
REM   READ IN THIS ORDER
REM     1. the report() memory block of each probe. Ternary per layer must be
REM        about 2.69M for dim 512 and 1.51M for dim 384. If it is not, the
REM        dim-squared scaling assumption is already wrong.
REM     2. LUT residency + other + KV against 9.0 + 0.788 x L for dim 512.
REM        Prediction 31.1 MiB at L 28. Tolerance 5 percent.
REM     3. single-thread tok/s. Prediction about 1.40 ms per visit at dim 512,
REM        so 28 visits gives about 46 ms = 21.7 tok/s. Tolerance 15 percent.
REM     4. DO NOT READ val. 250 steps says nothing about quality (repo rule).
REM
REM   NO PARENT INIT - no dim 512 parent exists yet. That is Stage1.
REM   COST: about 0.6h.   PLAN: test_plan/P089 Stage0a
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P089_stage0a_width_probe --note "[1/4] dim 512 depth 28 - 250 step probe, read report() and VRAM only"
python scripts\runlog.py --name P089_stage0a_width_probe -- python run100m.py train --preset m100w512s24 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --cla-group 2 --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag w512_d28_probe
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=w512_d28_probe
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

timeout /t 15 /nobreak
python scripts\runlog.py --name P089_stage0a_width_probe --note "[2/4] dim 384 depth 28 - the narrower point"
python scripts\runlog.py --name P089_stage0a_width_probe -- python run100m.py train --preset m100w384s24 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --cla-group 2 --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag w384_d28_probe
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=w384_d28_probe
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P089_stage0a_width_probe --note "[3/4] deployment residency of both narrow shapes - the canonical command"
python scripts\runlog.py --name P089_stage0a_width_probe -- python scripts\mem_runtime.py --preset m100w512s24 --data ko-en --tokens 300M --models w512_d28_probe --device cpu --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] arm 3a failed - continuing
python scripts\runlog.py --name P089_stage0a_width_probe -- python scripts\mem_runtime.py --preset m100w384s24 --data ko-en --tokens 300M --models w384_d28_probe --device cpu --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] arm 3b failed - continuing

python scripts\runlog.py --name P089_stage0a_width_probe --note "[4/4] single thread tok/s - is time linear in dim"
python scripts\runlog.py --name P089_stage0a_width_probe -- python scripts\bench_infer.py --models w512_d28_probe --preset m100w512s24 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] arm 4a failed - continuing
python scripts\runlog.py --name P089_stage0a_width_probe -- python scripts\bench_infer.py --models w384_d28_probe --preset m100w384s24 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache
if errorlevel 1 echo [WARN] arm 4b failed - continuing

python scripts\runlog.py --name P089_stage0a_width_probe --note "DONE. Three checks must all pass before Stage1. Do not read val from 250 steps."

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
