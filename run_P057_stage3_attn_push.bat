@echo off
REM =============================================================================
REM  P057 stage 3  -  how far does attention tying go on the 36 layer model
REM                   2 training runs plus paired eval and residency, about 6.3 h
REM
REM  WHY THIS EXISTS
REM    Attention tying is the CHEAPEST lever we have measured. EXPERIMENT_BASELINES
REM    B.5 puts it at 0.00083 nats per million unique ternary, which is 4.1 times
REM    cheaper than MLP tying (0.00342). We stopped at attn_group 4 and never
REM    asked where the price stops being cheap.
REM
REM  WHAT IS ALREADY KNOWN
REM    mC_d36_ag2   step0 anchor identical to no tying (result 044 s7)
REM    mC_d36_ag4   3.6848, resident 379.7 MiB, MINUS 15.9 percent vs baseline.
REM                 This is the standard model (EXPERIMENT_BASELINES B.6).
REM    ag8 and ag16 have never been run. m100R1d has 32 middle layers so both
REM    divide (trainer asserts n_middle modulo attn_group == 0).
REM
REM  WHY IT MATTERS NOW
REM    REVIEW3 needs residency below 40 MiB and the LUT already took the ternary
REM    term from 44.7 to 8.88. Attention is the term LUT does not shrink further,
REM    so cutting unique attention is the remaining structural lever on the
REM    deployment model itself rather than on the 20 layer baseline.
REM
REM  PREDICTIONS, fixed in advance
REM    A1  ag8 lands between plus 0.005 and plus 0.025 versus mC_d36_ag4 3.6848.
REM    A2  ag16 is WORSE than twice ag8. Lever price is convex (result 032 s8.3)
REM        so do NOT predict ag16 from the average of ag2 and ag4.
REM    A3  residency drops monotonically. If it does not, the accounting is wrong.
REM    A4  ms/step nearly flat. Tying does not reduce compute (result 033).
REM
REM  WHAT THIS CANNOT DECIDE
REM    The optimal attn_group. Two more points on a convex curve narrow it, they
REM    do not locate a minimum. And nothing here is valid for the 20 layer model.
REM
REM  !! NO --no-ckpt HERE ON PURPOSE
REM    Result 051 stage 2b proved 36 layers does not fit with --no-ckpt. lint_bat
REM    rule 21 will print an [i] for each run - that is expected, not a defect.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P057_stage3_attn_push --note "=============================================================================" "P057 stage 3   attention tying 8 and 16 on the 36 layer standard model" "Attention is the cheapest lever we have (0.00083 nats per million) and we" "stopped at 4 without asking where it stops being cheap. About 6.3 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P057_stage3_attn_push --note "[1/4] mC_d36_ag8_nokd - one flag different from the standard model"
python scripts\runlog.py --name P057_stage3_attn_push -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --attn-group 8 --ce-chunk 2048 --init-from --tag mC_d36_ag8_nokd
if errorlevel 1 echo [WARN] mC_d36_ag8_nokd failed - continuing

python scripts\runlog.py --name P057_stage3_attn_push --note "[wandb] push arm 1"
set TL_WB_TAG=mC_d36_ag8_nokd
call scripts\batch\tool_wandb_push.bat

echo.
timeout /t 15 /nobreak

python scripts\runlog.py --name P057_stage3_attn_push --note "[2/4] mC_d36_ag16_nokd - the aggressive end of the same axis"
python scripts\runlog.py --name P057_stage3_attn_push -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --attn-group 16 --ce-chunk 2048 --init-from --tag mC_d36_ag16_nokd
if errorlevel 1 echo [WARN] mC_d36_ag16_nokd failed - continuing

python scripts\runlog.py --name P057_stage3_attn_push --note "[wandb] push arm 2"
set TL_WB_TAG=mC_d36_ag16_nokd
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P057_stage3_attn_push --note "[3/4] paired full-val - three points on the attention tying curve"
python scripts\runlog.py --name P057_stage3_attn_push -- python scripts\paired_eval.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag8_nokd mC_d36_ag16_nokd mC_d36_ag4_nokd
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P057_stage3_attn_push --note "[4/4] residency - the denominator of the lever price"
python scripts\runlog.py --name P057_stage3_attn_push -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1d --models mC_d36_ag8_nokd mC_d36_ag16_nokd mC_d36_ag4_nokd --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P057_stage3_attn_push --note "=============================================================================" "READ IN THIS ORDER" "1. json attn_group must read 8 and 16. If either reads 4 the flag did not" "   land and that run is a reseed of the standard model (trap 37)." "2. val minus train_ce. Over 0.3 means measurement, not model (result 043 s14)." "3. paired delta against A1. Ruler is 2 sigma = 0.0034, NOT the 0.024 the tool" "   prints - that number is the dense estimator (open question Q6)." "4. lever price = delta quality divided by delta resident MiB. Compare against" "   0.00083 nats per million unique ternary in EXPERIMENT_BASELINES B.5." "5. ms/step. A4 says flat. A real change means the FLOP accounting is wrong." "IF ag8 STAYS CHEAP  the deployment model gets smaller for almost nothing." "IF ag8 IS ALREADY EXPENSIVE  the attention axis is closed at 4 and REVIEW3" "  should stop counting on it." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
