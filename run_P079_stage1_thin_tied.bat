@echo off
REM P079 stage 1  -  put MLP tying on thin bodies. About 8.1 hours.
REM
REM   Tying has only ever been measured at 20 layers. The question is whether
REM   its benefit survives on a shallow body, where each layer carries more.
REM
REM   INDEPENDENT VARIABLE: mlp_group, at fixed depth.
REM
REM   PREDICTION E3: d12_g4 will be WORSE than mC_initonly_nc and also larger,
REM   because 12 layers at g4 leaves only 2 unique middle blocks and 059 s14
REM   measured that the recurrent advantage is 3.2x smaller at 2 unique blocks.
REM   If that prediction misses, the unique-block law does not generalise
REM   across depth and that is the finding.
REM
REM   RULER: tied 2 sigma = 0.0006 (039 s9). Cross-family uses 0.0021.

REM   DEPTH IS SET BY PRESET, NOT A FLAG.  m100s{n_middle} plus prelude 2 and
REM   coda 2.  8 layers = m100s4, 12 = m100s8, 16 = m100s12 (added 2026-08-31),
REM   20 = m100 with --arch dense.  There is no --n-layers option and the
REM   batch-flag gate caught the first draft of this file using one.
REM
REM   CROSS-PRESET COMPARISON.  Checkpoints live at
REM   runs/ckpt/{preset}_{data}_{tokens}_{tag}.pt, so paired_eval can only
REM   load models that share a preset.  Paired statistics are therefore
REM   WITHIN preset.  Across presets, compare the deterministic full-val
REM   numbers - those are comparable because the val set and tokenizer are
REM   identical, but they carry no paired SE.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage1_thin_tied --note "[d8 g2] tied, 8 layers, group 2"
python scripts\runlog.py --name P079_stage1_thin_tied -- python run100m.py train --preset m100s4 --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --mlp-group 2 --depth-init role --tag d8_g2
if errorlevel 1 echo [WARN] step failed - continuing
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage1_thin_tied --note "[d12 g4] tied, 12 layers, group 4"
python scripts\runlog.py --name P079_stage1_thin_tied -- python run100m.py train --preset m100s8 --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --mlp-group 4 --depth-init role --tag d12_g4
if errorlevel 1 echo [WARN] step failed - continuing
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage1_thin_tied --note "[d16 g4] tied, 16 layers, group 4"
python scripts\runlog.py --name P079_stage1_thin_tied -- python run100m.py train --preset m100s12 --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --mlp-group 4 --depth-init role --tag d16_g4
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage1_thin_tied --note "[4/4] paired - against the 20-layer tied baseline"
python scripts\runlog.py --name P079_stage1_thin_tied -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models d8_g2
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage1_thin_tied -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_g4
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage1_thin_tied -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 300M --models d16_g4
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage1_thin_tied -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly_nc
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage1_thin_tied --note "[5/5] weights plus KV - quality alone does not decide this"
python scripts\runlog.py --name P079_stage1_thin_tied -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s4 --models d8_g2 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage1_thin_tied -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s8 --models d12_g4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage1_thin_tied -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s12 --models d16_g4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage1_thin_tied -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage1_thin_tied --note "READ IN THIS ORDER" "1. step0 CE per arm. The tied plus parent-init anchor is 7.7742." "2. paired against mC_initonly_nc, cross-family ruler 0.0021." "3. THEN memory. An arm that wins on quality but costs more resident memory" "   has not won - that was the mC_cla1_ag4_r20 trap (best quality, 70.9 MiB," "   twice the budget)." "4. unique middle blocks per arm: d8 g2 gives 2, d12 g4 gives 2, d16 g4 gives 3." "   Read the results against 059 s14, which says fewer unique blocks means a" "   smaller recurrent advantage." "5. do not rank arms whose gap is under the ruler."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
