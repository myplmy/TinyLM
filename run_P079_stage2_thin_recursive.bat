@echo off
REM P079 stage 2  -  the actual question. About 10.8 hours.
REM
REM   Does a thin dense body, tied and then run recursively, beat our 20-layer
REM   tied model on BOTH quality and resident memory.
REM
REM   These arms train from the dense parent directly, so they do NOT depend on
REM   stage 1 finishing. Run stage 1 first anyway if you can - it tells you
REM   which of these is worth reading closely.
REM
REM   WIN CONDITION (set in advance, P079 s5)
REM     full-val at least 0.0021 below mC_initonly_nc (3.6762)
REM     AND weights plus KV no larger.
REM   Quality alone is not a win.
REM
REM   RULER: recursion 2 sigma = 0.0006, measured (039 s10).

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
python scripts\runlog.py --name P079_stage2_thin_recursive --note "[d12_g4_r20] 12 layers g4 R=2.0 - about 20 visits"
python scripts\runlog.py --name P079_stage2_thin_recursive -- python run100m.py train --preset m100s8 --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --mlp-group 4 --depth-init role --train-repeat 2.0 --tag d12_g4_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage2_thin_recursive --note "[d12_g4_r30] 12 layers g4 R=3.0 - about 28 visits"
python scripts\runlog.py --name P079_stage2_thin_recursive -- python run100m.py train --preset m100s8 --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --mlp-group 4 --depth-init role --train-repeat 3.0 --tag d12_g4_r30
if errorlevel 1 echo [WARN] step failed - continuing
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage2_thin_recursive --note "[d16_g4_r20] 16 layers g4 R=2.0 - about 28 visits"
python scripts\runlog.py --name P079_stage2_thin_recursive -- python run100m.py train --preset m100s12 --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --mlp-group 4 --depth-init role --train-repeat 2.0 --tag d16_g4_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage2_thin_recursive --note "[4/5] paired - each checkpoint on its own trained schedule"
python scripts\runlog.py --name P079_stage2_thin_recursive -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_g4_r20 d12_g4_r30 --match-train-repeat
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage2_thin_recursive -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 300M --models d16_g4_r20 --match-train-repeat
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage2_thin_recursive -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly_nc mC_cla1_ag4_r20 --match-train-repeat
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage2_thin_recursive --note "[5/5] weights plus KV, and the visit count that sets decode speed"
python scripts\runlog.py --name P079_stage2_thin_recursive -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s8 --models d12_g4_r20 d12_g4_r30 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage2_thin_recursive -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s12 --models d16_g4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage2_thin_recursive -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_cla1_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage2_thin_recursive --note "READ IN THIS ORDER" "1. --match-train-repeat is on, so each checkpoint runs the function it was" "   trained with. Check the printed visit counts against 20 / 28 / 28." "   If they differ, trap 39 is back and the numbers are void." "2. quality against mC_initonly_nc on the cross-family ruler 0.0021." "3. kv_entries. Recursion multiplies entries, and result 062 closed the only" "   way of folding them back. Whatever KV these arms carry, they carry." "4. the win condition needs BOTH columns. Report the loss of either plainly." "5. decode speed follows visits, not layers (014 s13.1). A 28-visit arm is" "   about 40 percent slower than a 20-visit one whatever its depth."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
