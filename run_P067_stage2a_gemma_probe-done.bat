@echo off
REM =============================================================================
REM  P067 stage 2a  -  gemma tokenizer cache and a VRAM probe.  about 0.8 hours.
REM
REM  WHY  (plan P067 section 2C, user instruction 11)
REM    Stage 2 wants three gemma arms: no teacher, gemma-3-1b-pt teacher, and
REM    gemma-3-270m teacher. The two gemma models share one tokenizer - the
REM    tokenizer.json files are byte identical (md5 379e7490d90f) - so the
REM    tokenizer arm runs once, not twice.
REM
REM    Two things must be true before any of that is worth 18 hours.
REM      P1  a gemma token cache exists. Vocabulary 262,144 needs uint32.
REM      P2  it fits in 16 GB. Result 053 stage 0c needed micro-bs 2, accum 64,
REM          kd-chunk 512 and ce-chunk 1024 to fit vocabulary 151,936 at reserved
REM          10.62 GiB. gemma is 1.73 times wider than that.
REM
REM  PREDICTIONS
REM    Q1  the cache builds and meta.json records token_dtype uint32.
REM    Q2  the no-teacher probe fits under 15.0 GiB reserved.
REM    Q3  the 1b teacher probe fits. If it does not, drop to micro-bs 1 accum 128
REM        and say so in the result document - the shape is then not comparable
REM        with the Qwen arms on ms/step.
REM    Q4  step0 ce is near ln(262144) = 12.48. There is no parent at this
REM        vocabulary so a random start is correct, not a failure.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P067_stage2a_gemma_probe --note "=============================================================================" "P067 stage 2a   gemma cache and VRAM probe" "gemma-3-1b-pt and gemma-3-270m share one tokenizer - verified byte identical." "Nothing else in stage 2 is worth starting until this fits." "=============================================================================="

echo.
python scripts\runlog.py --name P067_stage2a_gemma_probe --note "[1/3] build the gemma token cache. Q1."
python scripts\runlog.py --name P067_stage2a_gemma_probe -- python run100m.py prepare --data ko-en --tokens 600M --pool-tokens 600M --exact-cache --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29
if errorlevel 1 goto ERROR

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P067_stage2a_gemma_probe --note "[2/3] 250-step probe, no teacher. Q2 and Q4."
python scripts\runlog.py --name P067_stage2a_gemma_probe -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --ce-chunk 1024 --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 --tag GT0probe
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P067_stage2a_gemma_probe --note "[3/3] 250-step probe with the 1b teacher. Q3 - the hard one."
python scripts\runlog.py --name P067_stage2a_gemma_probe -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --ce-chunk 1024 --kd --kd-every 4 --kd-chunk 512 --teacher-dtype bf16 --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 --kd-teacher-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 --tag G1BTprobe
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
REM  250-step probes are below wandb_sync MIN_TOKENS so this reports a skip.
REM  The call is here so the batch obeys the 2026-08-22 rule, not to upload.
set TL_WB_TAG=GT0probe
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P067_stage2a_gemma_probe --note "=============================================================================" "READ IN THIS ORDER" "1. Q1 - the cache directory name and meta.json token dtype." "2. Q2 and Q3 - reserved GiB. Under 15.0 means stage 2 can run at this shape." "3. Q4 - step0 ce near 12.48. Trap 34 - suspect the reference value before the" "   model. There is no parent at vocabulary 262,144." "4. do NOT read val from a 250-step run. Speed and VRAM only." "5. if step 3 OOMs, the fix is micro-bs 1 accum 128, and the Qwen arms are then" "   not comparable on ms per step." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:ERROR
echo [STOP] the gemma cache did not build - nothing downstream can run
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
