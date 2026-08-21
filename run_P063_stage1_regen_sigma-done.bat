@echo off
REM =============================================================================
REM  P063 stage 1  +  P054 stage 1   -   ONE BATCH, TWO QUESTIONS
REM                   3 dense regenerations, identical command, seed 1337
REM                   about 5 hours of training, then a few minutes of eval
REM
REM  WHY THESE TWO EXPERIMENTS ARE THE SAME EXPERIMENT
REM    P063 asks: how big is the noise floor of a run?
REM    P054 asks: if I regenerate the dense parent, is it the same parent?
REM    Both are answered by ONE number - the spread of repeated runs under an
REM    IDENTICAL command. We have been paying for that number twice.
REM
REM  WHAT WE ALREADY KNOW, AND WHY IT IS NOT ENOUGH
REM    dense vs denseb   paired +0.0080   (result 040 s2)  same seed 1337
REM    p6d   vs p6d_s2   paired +0.0109   (result 049)     seed 1337 vs 2024
REM    Read together those two say something startling: changing the seed adds
REM    almost nothing on top of simply running the same command twice. But
REM    dense and denseb were trained WEEKS APART on different code, so code
REM    drift is confounded with nondeterminism. N=2 and confounded.
REM
REM  WHY THE SAME SEED STILL GIVES DIFFERENT ANSWERS
REM    trainer.py sets cudnn.benchmark = True and TF32 on. The autotuner picks
REM    kernels by wall clock, and reduction order is not fixed. Same seed does
REM    NOT mean same arithmetic. This batch measures how much that costs.
REM
REM  THE ARMS - all three commands are byte-identical except --tag
REM    dnc_r1 dnc_r2 dnc_r3    dense, seed 1337, cosine, anneal-end 0.60,
REM                            no --pool-tokens, no --exact-cache, --no-ckpt
REM    That is denseb's command exactly (runs/logs/..._denseb.json). Same code,
REM    same day, same machine - so the ONLY difference left is nondeterminism.
REM
REM  PREDICTIONS, fixed in advance
REM    P1  spread across the 3 lands between 0.005 and 0.012, i.e. most of the
REM        0.0109 that result 049 charged to the SEED is really the FLOOR
REM    P2  denseb sits inside that spread - if it does not, code drift is real
REM        and result 040 s2's +0.0080 was never a clean measurement
REM    P3  step0 CE of all three is 3.8080 within 0.01 - they are the same model
REM    P4  P054 verdict: the parent is replaceable if the spread is under 0.024
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Anything about the TIED condition. This measures the DENSE floor only.
REM    The tied + parent-init floor is 0.0017 (result 049) and nothing here
REM    changes that. Do not carry this number across conditions - that is
REM    exactly the mistake result 049 was written to stop.
REM    Also: 3 samples give 2 degrees of freedom. This is an order of magnitude,
REM    not a confidence interval.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P063_stage1_regen --note "=============================================================================" "P063 stage 1 + P054 stage 1   3 identical dense regenerations   about 5 hours" "Same command, same seed, three times. The number both plans need." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P063_stage1_regen --note "[1/4] regeneration 1 of 3 - denseb's exact command, tag dnc_r1"
python scripts\runlog.py --name P063_stage1_regen -- python run100m.py train --preset m100 --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched cosine --anneal-end 0.60 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --tag dnc_r1
if errorlevel 1 echo [WARN] dnc_r1 failed - continuing

echo.
python scripts\runlog.py --name P063_stage1_regen --note "[2/4] regeneration 2 of 3 - identical, tag dnc_r2"
python scripts\runlog.py --name P063_stage1_regen -- python run100m.py train --preset m100 --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched cosine --anneal-end 0.60 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --tag dnc_r2
if errorlevel 1 echo [WARN] dnc_r2 failed - continuing

echo.
python scripts\runlog.py --name P063_stage1_regen --note "[3/4] regeneration 3 of 3 - identical, tag dnc_r3"
python scripts\runlog.py --name P063_stage1_regen -- python run100m.py train --preset m100 --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched cosine --anneal-end 0.60 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --tag dnc_r3
if errorlevel 1 echo [WARN] dnc_r3 failed - continuing

echo.
python scripts\runlog.py --name P063_stage1_regen --note "[4/4] paired full-val over all five same-condition dense runs"
python scripts\runlog.py --name P063_stage1_regen -- python scripts\paired_eval.py --preset m100 --data ko-en --tokens 300M --models dnc_r1 dnc_r2 dnc_r3 denseb dense
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
echo.
python scripts\runlog.py --name P063_stage1_regen --note "=============================================================================" "READ IN THIS ORDER" "1. the three dnc_r pairwise deltas. THAT is the nondeterminism floor." "2. compare the floor with 0.0109 - the seed pair from result 049." "   If the floor is most of 0.0109, then SEED is not what moves the number." "3. where does denseb sit? Inside the spread means result 040 s2 was clean." "   Outside means code drift, and 040 s2 must be re-labelled." "4. dense sits on OLD code. It is the outlier by design - read it last." "REMINDER  3 runs = 2 degrees of freedom. Order of magnitude only." "REMINDER  this is the DENSE floor. The tied floor is 0.0017 (result 049)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
