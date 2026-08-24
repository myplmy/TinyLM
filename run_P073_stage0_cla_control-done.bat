@echo off
REM =============================================================================
REM  P073 stage 0  -  what does cla_group = 2 actually cost
REM                   1 training run plus paired eval and residency, about 1.8 hours
REM
REM  WHY THIS EXISTS  (audit, 2026-08-23)
REM    cla_group = 2 is ON BY DEFAULT in every preset and its quality cost has
REM    never been attributed. Result 033 measured VRAM (-35.3 percent) and KV
REM    cache (halved). Result 044 already wrote down that a cla_group = 1 control
REM    is needed to attribute the cost - and that control still does not exist.
REM
REM  !! THE REAL STAKE IS P057
REM    Every attn_group number we have was measured ON TOP OF cla_group = 2.
REM    If CLA is costing us quality, the attention-tying results are confounded
REM    and we should know that before spending more runs on that axis.
REM
REM  WHAT ONE FLAG CHANGES
REM    cla_group 1 gives every layer its own K/V. Parameters go up, VRAM goes up,
REM    KV cache doubles. So this is NOT "if it is better, adopt it" - it is
REM    "how much are we paying, and is the lever price competitive".
REM
REM  PREDICTIONS, fixed in advance
REM    Z1  cla1 is 0.005 to 0.020 BETTER. Zero would mean CLA is free.
REM    Z2  the lever price is WORSE than the existing line (0.0167 nats per MB).
REM        CLA is already adopted, so if it were a good deal we would know.
REM    Z3  ms/step nearly identical - report() FLOPs has no cla_group term
REM        (result 033). A difference here means the accounting is wrong.
REM    Z4  if Z1 lands away from zero, P057 results are confounded.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    The optimal cla_group. Only 1 versus 2. cla_group 4 stays on hold.
REM    clip_grad_norm - designed in P073 section 7 and deliberately NOT started.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P073_stage0_cla_control --note "=============================================================================" "P073 stage 0   what does cla_group = 2 cost" "It is on by default in every preset and has never been attributed." "Result 044 asked for this control and it still did not exist." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P073_stage0_cla_control --note "[1/3] mC_cla1 - one flag different from mC_initonly"
python scripts\runlog.py --name P073_stage0_cla_control -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --cla-group 1 --tag mC_cla1
if errorlevel 1 echo [WARN] mC_cla1 failed - continuing

echo.
python scripts\runlog.py --name P073_stage0_cla_control --note "[wandb] push this run"
set TL_WB_TAG=mC_cla1
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P073_stage0_cla_control --note "[2/3] paired full-val against the standard control"
python scripts\runlog.py --name P073_stage0_cla_control -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1 mC_initonly
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P073_stage0_cla_control --note "[3/3] residency - the denominator of the lever price"
python scripts\runlog.py --name P073_stage0_cla_control -- python scripts\mem_runtime.py --device cpu --max-new 32 --models mC_cla1 mC_initonly --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P073_stage0_cla_control --note "=============================================================================" "READ IN THIS ORDER" "1. json cla_group must read 1. If it reads 2 the flag did not land and this" "   run is a reseed of mC_initonly (trap 37)." "2. paired delta against Z1. Ruler is 2 sigma = 0.0034, NOT 0.024 - this is a" "   no-KD comparison and the tool prints the dense number." "3. step [3] residency. Lever price = delta quality divided by delta MB." "   Compare against the 0.0167 nats per MB line in EXPERIMENT_BASELINES 2.2c." "4. ms/step. Z3 says nearly identical because report() FLOPs has no cla_group" "   term. A real difference means the FLOP accounting is wrong, not the model." "!! If the delta is near zero, CLA is free and cla_group 4 becomes worth a look." "!! If the delta is large, every attn_group result is confounded (Z4)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
