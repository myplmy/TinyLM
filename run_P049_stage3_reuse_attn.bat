@echo off
REM =============================================================================
REM  P049 stage 3  -  reuse the attention output on a duplicated visit  (6.5-1)
REM                   1 training run plus paired eval, about 2.4 hours
REM
REM  WHY THIS IS THE MOST INTERESTING ARM WE HAVE
REM    Result 041 s17 measured cosine similarity 0.9882 between the attention
REM    output of a layer and the attention output of its duplicate visit.
REM    The second pass computes almost exactly the same thing. That is waste.
REM
REM    Every other lever in this repo trades quality for MEMORY. This one is the
REM    first that trades quality for COMPUTE - and compute is the thing recursion
REM    costs us (+69 percent wall clock for -0.0203).
REM
REM  WHAT --reuse-attn-on-dup DOES
REM    On the second and later visit to a layer, skip the attention sub-block
REM    entirely and reuse the first pass output. If that layer is also the sole
REM    consumer of its KV, skip computing KV too - otherwise the QKV projection
REM    stays and the saving is only half of what it looks like.
REM    Default off. With infer_repeat and train_repeat both 1.0 the whole block
REM    is dead code and the run is bit identical.
REM
REM  !! TRAINING AND INFERENCE MUST AGREE
REM    Trap 39. The eval below passes --reuse-attn-on-dup as well. If you run
REM    paired_eval without it you are evaluating a different function.
REM
REM  PREDICTIONS, fixed in advance
REM    V1  wall clock drops 10 to 20 percent versus mC_r20_nokd. Attention is
REM        48.4 percent of the ternary parameters but attention FLOPs at seq
REM        1024 are less than that share, so a full halving is not expected.
REM    V2  quality within 0.010 of mC_r20_nokd. cos 0.9882 is the argument.
REM    V3  memory identical - packed and resident both. Nothing is stored or
REM        dropped, only skipped.
REM    V4  reserved may drop a little - one fewer activation set per dup visit.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether the same trick works at R greater than 2, or at 36 layers. The
REM    duplicate-visit similarity was measured at one depth only.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P049_stage3_reuseattn --note "=============================================================================" "P049 stage 3   --reuse-attn-on-dup   6.5-1" "Result 041 s17: duplicate layer attention output cos 0.9882. The second" "pass recomputes almost the same thing. This is the first COMPUTE lever." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P049_stage3_reuseattn --note "[1/3] mC_r20ra_nokd - one flag different from mC_r20_nokd"
python scripts\runlog.py --name P049_stage3_reuseattn -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --train-repeat 2.0 --reuse-attn-on-dup --init-from --tag mC_r20ra_nokd
if errorlevel 1 echo [WARN] mC_r20ra_nokd failed - continuing

echo.
python scripts\runlog.py --name P049_stage3_reuseattn --note "[wandb] push this run"
set TL_WB_TAG=mC_r20ra_nokd
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P049_stage3_reuseattn --note "[2/3] paired full-val - --match-train-repeat gives EACH model its own trained function"
python scripts\runlog.py --name P049_stage3_reuseattn -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20ra_nokd mC_r20_nokd --match-train-repeat
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P049_stage3_reuseattn --note "[3/3] cross check - is reuse also free at INFERENCE on a model trained without it"
python scripts\runlog.py --name P049_stage3_reuseattn -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20_nokd --infer-repeat 2.0 --repeat-where front --reuse-attn-on-dup
if errorlevel 1 echo [WARN] cross check failed - continuing

echo.
python scripts\runlog.py --name P049_stage3_reuseattn --note "=============================================================================" "READ IN THIS ORDER" "1. json reuse_attn_on_dup must read true. If false the flag did not land." "2. wall clock against mC_r20_nokd. THIS is the headline (V1: -10 to -20 pct)." "3. paired delta against V2. Ruler is 2 sigma = 0.0034 (no-KD)." "4. deploy_mb and mem_parts_mb must be IDENTICAL (V3). If they moved, the" "   accounting is wrong - nothing was stored or dropped." "5. step [3/3] answers a different question: can an ALREADY TRAINED recursion" "   model get the speedup for free at inference. If yes that is a deployment" "   lever with zero retraining cost." "!! step [3/3] is a train/infer MISMATCH on purpose. Do not read it as quality." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
