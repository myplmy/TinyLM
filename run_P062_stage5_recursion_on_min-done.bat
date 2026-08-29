@echo off
REM =============================================================================
REM  P062 stage 5  -  recursion on the SMALLEST resident body
REM                   1 training run plus paired eval and residency, about 2.0 hours
REM
REM  THE QUESTION
REM    mC_cla1_ag4 is the smallest resident learned artefact in the repository
REM    (339.0 MiB fp32, 72.4 int8, full-val 3.6867). Recursion is the only lever we
REM    have that buys quality at ZERO memory (result 047: -0.0202 at 20 layers,
REM    -0.0157 at 36 layers with identical deploy_mb).
REM    Nobody has put the two together. If recursion pays its usual amount here,
REM    the smallest body in the repository also becomes competitive on quality.
REM
REM  PREDICTIONS
REM    T1  resident IDENTICAL to mC_cla1_ag4 - 339.0 fp32, 72.4 int8. Check first.
REM    T2  quality gain between -0.010 and -0.020. Result 047 got -0.0202 at 20
REM        layers and -0.0157 at 36; this body has 20 layers but a tighter
REM        attention budget (4 unique attentions), so expect the lower half.
REM    T3  it lands better than mC_initonly_nc (3.6762) at 112.5 MiB less resident.
REM        That would make it the new Pareto point below 400 MiB.
REM    T4  decode cost doubles - 20 visits becomes 36 (2 + 16x2 + 2). Result 014
REM        section 12.2 says time is linear in visits, so about 11.4 -^> 6.9 tok/s.
REM        THIS IS THE COST. Report it beside the quality number, never alone.
REM
REM  !! EVALUATE WITH --match-train-repeat (trap 39).
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P062_stage5_recursion_on_min --note "=============================================================================" "P062 stage 5   recursion on the smallest resident body (mC_cla1_ag4)" "The only zero-memory quality lever, applied to the smallest artefact we have." "About 2.0 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P062_stage5_recursion_on_min --note "[1/3] mC_cla1_ag4_r20 - one flag different from mC_cla1_ag4"
python scripts\runlog.py --name P062_stage5_recursion_on_min -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --ce-chunk 2048 --cla-group 1 --attn-group 4 --train-repeat 2.0 --init-from --tag mC_cla1_ag4_r20
if errorlevel 1 echo [WARN] mC_cla1_ag4_r20 failed - continuing
set TL_WB_TAG=mC_cla1_ag4_r20
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P062_stage5_recursion_on_min --note "[2/3] paired - against its own no-recursion twin and the standard control"
python scripts\runlog.py --name P062_stage5_recursion_on_min -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20 mC_cla1_ag4 mC_initonly_nc --match-train-repeat
if errorlevel 1 echo [WARN] paired failed - continuing

echo.
python scripts\runlog.py --name P062_stage5_recursion_on_min --note "[3/3] residency - T1 says identical to mC_cla1_ag4"
python scripts\runlog.py --name P062_stage5_recursion_on_min -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla1_ag4_r20 mC_cla1_ag4 --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P062_stage5_recursion_on_min --note "=============================================================================" "READ IN THIS ORDER" "1. T1 - resident identical to mC_cla1_ag4 (339.0 / 72.4). Recursion stores" "   nothing; a difference here is an accounting bug." "2. json train_repeat must read 2.0 AND cla_group 1 AND attn_group 4. All three." "3. paired against T2 (-0.010 to -0.020) and T3 (beats mC_initonly_nc 3.6762)." "4. T4 - the cost is decode speed, 20 visits becomes 36. Report tok/s beside" "   the quality number. run_P030_stage2D measures the 20-visit baseline." "IF T3 HOLDS  the frontier below 400 MiB gets a new point and REVIEW3 option B" "  can be built on a 339 MiB body instead of a 379.7 one." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
