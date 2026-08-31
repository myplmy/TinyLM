@echo off
REM P079 stage 0  -  fill in the depth axis. About 8.1 hours.
REM
REM   We have never asked whether 20 layers is the right depth. The m100 preset
REM   was born at 20 and every experiment since has run on top of it. There is
REM   a d8_dense in the repo and nothing between 8 and 20 - and no d20_dense at
REM   all, because our 20-layer models are all tied.
REM
REM   INDEPENDENT VARIABLE: n_layers. dense, no tying, no recursion.
REM
REM   PREDICTIONS
REM     E1  d12 beats d8 by -0.01 to -0.03.
REM     E2  d20 is within the dense ruler (0.0021) of d16. If so, 16 is the knee.
REM     E3  step0 CE lands in 5.0 to 9.4 for all three - that is the transplant
REM         gate, and 20 to 12 shrinking transplant has never been done before.
REM
REM   RULER: dense 2 sigma = 0.0021, measured on three seeds (039 s9).

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
python scripts\runlog.py --name P079_stage0_depth_axis --note "[12] dense 12 layers"
python scripts\runlog.py --name P079_stage0_depth_axis -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d12_dense
if errorlevel 1 echo [WARN] step failed - continuing
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage0_depth_axis --note "[16] dense 16 layers"
python scripts\runlog.py --name P079_stage0_depth_axis -- python run100m.py train --preset m100s12 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d16_dense
if errorlevel 1 echo [WARN] step failed - continuing
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage0_depth_axis --note "[20] dense 20 layers"
python scripts\runlog.py --name P079_stage0_depth_axis -- python run100m.py train --preset m100 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d20_dense
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage0_depth_axis --note "[4/4] paired - the depth curve"
python scripts\runlog.py --name P079_stage0_depth_axis -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_dense
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0_depth_axis -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 300M --models d16_dense
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0_depth_axis -- python scripts\paired_eval.py --preset m100 --data ko-en --tokens 300M --models d20_dense
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0_depth_axis -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models d8_dense
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage0_depth_axis --note "READ IN THIS ORDER" "1. step0 CE on each arm FIRST. 5.0 to 9.4 means the transplant worked." "   Anything near 10.4 means that arm started from noise - a build failure," "   not a depth result (trap 34: suspect the reference before the model)." "2. the four full-val values as a curve. Read on the DENSE ruler 0.0021." "3. d20_dense against mC_initonly_nc. That is dense-versus-tied at equal depth" "   and we have never had it. Cross-family, so use the larger ruler 0.0021." "4. resident memory scales with depth here. This stage draws a curve, it does" "   not pick a winner - d20_dense is a reference point, not a deployment" "   candidate." "5. do NOT change the preset on the strength of this. That is a REVIEW call."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
