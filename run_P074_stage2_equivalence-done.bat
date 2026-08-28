@echo off
REM =============================================================================
REM  P074 stage 2  -  the three-way equivalence, with memory held EXACTLY fixed
REM                   3 training runs plus paired eval and residency
REM                   about 4.8 hours
REM
REM  THE QUESTION  (user, 2026-08-27)
REM    "Is tying just layer reduction? Is 2+4+2 dense the same thing as
REM     2+16(attn_group 4 + mlp tying)+2, and the same thing again as
REM     dense 2+4 with 4x recursion +2?"
REM
REM  WHY THIS IS A CLEAN EXPERIMENT
REM    All three arms have the SAME UNIQUE PARAMETERS. Verified from config:
REM
REM      arm   preset    shape        unique mid MLP   unique attn   cla
REM      E1    m100s4    2+4+2   =  8      4                4         1
REM      E2    m100      2+16+2  = 20      4 (mlp g4)       4 (ag4)   1
REM      E3    m100s4    2+4+2   =  8      4                4         1
REM
REM    So resident memory and deploy_mb must be IDENTICAL across all three.
REM    What differs is only how many times those parameters are VISITED and
REM    IN WHAT ORDER:
REM
REM      E1   8 visits      each middle block once
REM      E2  20 visits      block-wise:  1 1 1 1 2 2 2 2 3 3 3 3 4 4 4 4
REM      E3  20 visits      cycle-wise:  1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4
REM
REM    E2 versus E3 is therefore a PURE TEST OF VISIT ORDER at fixed parameters
REM    and fixed visit count. Nobody has ever run that comparison here.
REM    E1 versus E2 is the pure test of visit COUNT at fixed parameters.
REM
REM  !! E3 MUST BE TRAINED WITH RECURSION ON
REM    --train-repeat 4.0 during training, and --match-train-repeat at eval.
REM    Evaluating an R=4 checkpoint at R=1 evaluates a function that was never
REM    trained (trap 39). The user asked for exactly this: the shallow dense
REM    recursive model has to be TRAINED with recursive inference in mind.
REM
REM  PREDICTIONS, fixed in advance
REM    X1  resident and deploy_mb IDENTICAL across E1, E2, E3 to 15 decimals.
REM        If they are not, the parameter accounting is wrong and nothing else
REM        in this batch means anything. CHECK THIS FIRST.
REM    X2  E1 is the worst. 8 visits cannot match 20.
REM    X3  E2 and E3 land within 2 sigma (0.0034) of each other. That is the
REM        "tying IS layer reduction" hypothesis stated as a number.
REM    X4  if E3 beats E2 by more than 2 sigma, cycle-wise beats block-wise and
REM        our immediate-sharing layout (mid_mlps[j // g]) is the wrong default.
REM    X5  E1 to E2 gap is larger than the E2 to E3 gap. Visit count matters
REM        more than visit order.
REM
REM  !! COMPARISON VALIDITY
REM    All three use cla_group 1 so the CLA confound is removed by construction
REM    (result 058 section 12 measured it at -0.0268 at 20 layers, -0.0136 at 36).
REM    E1 and E2 use --no-ckpt. E3 keeps grad checkpointing ON because dense
REM    times recursion has never had a VRAM measurement and 36 layer recursion
REM    is already known to OOM without it (result 051 stage 2b). Result 051
REM    stage 3 measured the ckpt drift at -0.0014, which is inside the 0.0034
REM    ruler - so this does not invalidate E2 versus E3, but SAY SO in the
REM    result document rather than letting the reader assume matched conditions.
REM    All three share seed, pool, steps and tokenizer.
REM    E1 and E3 are shallower than the m100 dense parent so they need
REM    --depth-init role; E2 is the same depth and uses the default.
REM
REM  PREREQUISITE
REM    run_P074_stage1_dense_depth_curve.bat should be re-run first. It is the
REM    cheap gate on the same transplant path and it died four times on
REM    2026-08-27 (result 059). If stage 1 dies again, do not start this.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "=============================================================================" "P074 stage 2   is tying just layer reduction" "Three arms with IDENTICAL unique parameters. Only visit count and visit" "order differ. E2 versus E3 is a pure test of visit ORDER. About 4.8 hours." "PREREQUISITE  run_P074_stage1_dense_depth_curve.bat must pass first." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[1/6] E1  shallow dense 2+4+2, 8 visits, no recursion"
python scripts\runlog.py --name P074_stage2_equivalence -- python run100m.py train --preset m100s4 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag eq_d8_dense
if errorlevel 1 echo [WARN] eq_d8_dense failed - continuing

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[wandb] push E1"
set TL_WB_TAG=eq_d8_dense
call scripts\batch\tool_wandb_push.bat

timeout /t 15 /nobreak

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[2/6] E2  tied 2+16+2 with mlp g4 and attn_group 4, 20 visits, block-wise order"
python scripts\runlog.py --name P074_stage2_equivalence -- python run100m.py train --preset m100 --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --attn-group 4 --cla-group 1 --init-from --tag eq_t20_ag4
if errorlevel 1 echo [WARN] eq_t20_ag4 failed - continuing

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[wandb] push E2"
set TL_WB_TAG=eq_t20_ag4
call scripts\batch\tool_wandb_push.bat

timeout /t 15 /nobreak

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[3/6] E3  shallow dense 2+4+2 TRAINED at 4x recursion, 20 visits, cycle-wise order"
python scripts\runlog.py --name P074_stage2_equivalence -- python run100m.py train --preset m100s4 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --ce-chunk 2048 --train-repeat 4.0 --init-from --depth-init role --tag eq_d8_r40
if errorlevel 1 echo [WARN] eq_d8_r40 failed - continuing

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[wandb] push E3"
set TL_WB_TAG=eq_d8_r40
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[4/6] paired  E1 versus E2, each at its own trained function"
python scripts\runlog.py --name P074_stage2_equivalence -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models eq_d8_dense eq_t20_ag4 --match-train-repeat
if errorlevel 1 echo [WARN] paired 1 failed - continuing

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[5/6] paired  E3 against both. --match-train-repeat is REQUIRED here (trap 39)"
python scripts\runlog.py --name P074_stage2_equivalence -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models eq_d8_r40 eq_t20_ag4 eq_d8_dense --match-train-repeat
if errorlevel 1 echo [WARN] paired 2 failed - continuing

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "[6/6] residency  X1 says these three must be IDENTICAL"
python scripts\runlog.py --name P074_stage2_equivalence -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s4 --models eq_d8_dense eq_t20_ag4 eq_d8_r40 --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P074_stage2_equivalence --note "=============================================================================" "READ IN THIS ORDER" "1. X1 FIRST. step [6] resident and deploy_mb must be identical for all three." "   If they differ the parameter accounting is wrong and the rest is void." "   Step [6] now exits 1 if it measured nothing (result 059 section 5)." "2. json for E3 must read train_repeat 4.0 and for E2 attn_group 4 plus" "   cla_group 1. A field that is absent means the flag did not land (trap 37)." "3. val minus train_ce for E3 will be LARGE - that is expected, evaluate() runs" "   at R=1 while training ran at R=4 (trap 39, result 047 section 11.4)." "   The judgement is the paired number, not the training log." "4. E2 versus E3 against X3 (within 0.0034) and X4 (E3 better by more)." "   THIS IS THE ANSWER TO THE WHOLE QUESTION." "5. E1 versus E2 against X2 and X5." "IF X3 HOLDS  tying at fixed parameters IS layer reduction, and REVIEW3 can" "  treat shallow dense plus recursion and deep tied as the same design point." "IF X4 HOLDS  cycle-wise beats block-wise and mid_mlps[j // g] is the wrong" "  default layout - that would be the largest architecture finding this month." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
