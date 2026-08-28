@echo off
REM =============================================================================
REM  P075 stage 3  -  emb_rank 128 under the no-KD standard condition
REM                   1 training run plus paired eval and residency
REM                   about 1.8 hours
REM
REM  WHY THIS ONE FIRST
REM    P075 has four stages. Three of them need a prerequisite - stage 1 needs a
REM    verified common text (the ruler does not exist yet), stage 2 needs jamo
REM    normalisation implemented, stage 4 needs the gemma blockers rechecked.
REM    This one needs nothing: the vocabulary does not change, so paired_eval
REM    judges it directly and no common_bpb is involved.
REM
REM  THE QUESTION
REM    ALBERT (Lan 2020) Table 3 reports E=128 at 12M/79.6 against E=256 at
REM    16M/80.1 - 25 percent fewer parameters and half a point HIGHER. Our own
REM    measurement of E=128 (result 030) was taken under KD and came back with
REM    grad_max 19.32, which our own rule calls a training problem, so the
REM    verdict was "cannot judge" rather than a number.
REM    The standard condition has been no-KD since 2026-08-22. Nobody re-ran it.
REM
REM  PREDICTIONS, fixed in advance
REM    W1  int8 embedding term falls 9.1 -^> about 4.9 MiB. Check this first; if
REM        it does not move, the flag did not land (trap 37).
REM    W2  quality is WORSE by 0.01 to 0.03. The logit rank is halved and result
REM        030 saw +0.1768 under KD - most of that was the grad blow-up, but not
REM        all of it.
REM    W3  grad_max stays under 10. If it does not, this is the same failure as
REM        result 030 and the KD framing was never the cause.
REM    W4  ms/step nearly unchanged. The embedding is not the compute bottleneck.
REM
REM  WHAT THIS CANNOT DECIDE
REM    The vocabulary size. E is the factorisation rank, not the vocabulary -
REM    that is stage 1 and it needs the common text first.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P075_stage3_emb128_nokd --note "=============================================================================" "P075 stage 3   emb_rank 128 under the no-KD standard condition" "The only P075 stage with no prerequisite - the vocabulary does not change." "Result 030 measured this under KD with grad_max 19.32 = cannot judge." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P075_stage3_emb128_nokd --note "[1/3] mC_e128_nc - one flag different from mC_initonly_nc"
python scripts\runlog.py --name P075_stage3_emb128_nokd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --emb-rank 128 --init-from --tag mC_e128_nc
if errorlevel 1 echo [WARN] mC_e128_nc failed - continuing

echo.
python scripts\runlog.py --name P075_stage3_emb128_nokd --note "[wandb] push this run"
set TL_WB_TAG=mC_e128_nc
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P075_stage3_emb128_nokd --note "[2/3] paired full-val against the no-ckpt twin of the standard control"
python scripts\runlog.py --name P075_stage3_emb128_nokd -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_e128_nc mC_initonly_nc
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P075_stage3_emb128_nokd --note "[3/3] residency - W1 lives or dies here"
python scripts\runlog.py --name P075_stage3_emb128_nokd -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_e128_nc mC_initonly_nc --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P075_stage3_emb128_nokd --note "=============================================================================" "READ IN THIS ORDER" "1. W1 first. Step [3] other term should read about 4.9 against 9.1. If it" "   reads 9.1 the flag did not land and nothing else here means anything." "2. json grad_max against W3 (under 10). Result 030 read 19.32 under KD and" "   that is why its number was never usable." "3. paired delta against W2. Ruler is 2 sigma = 0.0034 - this is a no-KD" "   comparison against the no-ckpt twin, so conditions match exactly." "4. lever price = delta quality divided by delta resident MiB. Compare against" "   the g16 line 0.000447 nats per MiB in EXPERIMENT_BASELINES B.5." "IF W1 HOLDS AND THE DELTA IS UNDER 0.01  REVIEW3 option B drops by about" "  4 MiB and E=128 becomes the default." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
