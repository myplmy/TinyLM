@echo off
REM =============================================================================
REM  P073 stage 2  -  finish un-confounding the attention axis
REM                   2 training runs plus paired eval, about 3.6 hours
REM
REM  WHERE WE ARE  (results 058 stage 0 and stage 1)
REM    cla_group 1 versus 2, measured twice:
REM        20 layers, attn_group 1      minus 0.0268   past 0.024 resolution
REM        36 layers, attn_group 4      minus 0.0136   half of that
REM    So the two mechanisms DO overlap - the more attention is already tied,
REM    the less CLA costs. But it is not zero, and the axis is only two points.
REM
REM  WHAT IS STILL CONFOUNDED
REM    EXPERIMENT_BASELINES B.5 prices attention tying at 0.00083 nats per
REM    million unique ternary. That line came from ag1 versus ag4 measured on
REM    cla2. Result 044 stage 3 then priced ag4 to ag8 at 0.00381 on cla2 too.
REM    Neither has a cla1 twin, so the ATTENTION axis has never been priced on
REM    a clean K/V baseline.
REM
REM  THE TWO ARMS
REM    mC_cla1_ag4   20 layers, attn_group 4, cla_group 1
REM           with mC_cla1 (ag1/cla1) already on disk this gives the ag1-to-ag4
REM           price ON cla1. Compare against the same step measured on cla2.
REM    mC_d36_ag8_cla1  36 layers, attn_group 8, cla_group 1
REM           tests whether the ag4-to-ag8 cliff (result 044: 4.6x the B.5 line)
REM           is real or an artifact of doing it on top of shared K/V.
REM
REM  PREDICTIONS, fixed in advance
REM    P1  on cla1 the ag1-to-ag4 price is HIGHER than 0.00083. CLA was doing
REM        part of the sharing for free; take it away and attention tying has
REM        to do more work.
REM    P2  the ag4-to-ag8 cliff SURVIVES. If it vanishes, result 044's axis
REM        closure was an artifact and ag8 reopens.
REM    P3  resident goes up on both arms - cla1 gives every layer its own K/V.
REM    P4  if P1 and P2 both hold, B.5 needs a footnote, not a rewrite.
REM
REM  !! arm 1 uses --no-ckpt (20 layers, no KD - result 051). arm 2 does not
REM     (36 layers does not fit). That is deliberate: each arm matches the
REM     grad_ckpt of the control it is compared against.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P073_stage2_cla1_matrix --note "=============================================================================" "P073 stage 2   price the attention axis on a clean K/V baseline" "B.5's 0.00083 and result 044's 0.00381 were both measured on cla2." "Neither has a cla1 twin. About 3.6 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P073_stage2_cla1_matrix --note "[1/4] mC_cla1_ag4 - one flag different from mC_cla1"
python scripts\runlog.py --name P073_stage2_cla1_matrix -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --cla-group 1 --attn-group 4 --init-from --tag mC_cla1_ag4
if errorlevel 1 echo [WARN] mC_cla1_ag4 failed - continuing
python scripts\runlog.py --name P073_stage2_cla1_matrix --note "[wandb] push arm 1"
set TL_WB_TAG=mC_cla1_ag4
call scripts\batch\tool_wandb_push.bat

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P073_stage2_cla1_matrix --note "[2/4] mC_d36_ag8_cla1 - does the ag8 cliff survive a clean K/V baseline"
python scripts\runlog.py --name P073_stage2_cla1_matrix -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --ce-chunk 2048 --cla-group 1 --attn-group 8 --init-from --tag mC_d36_ag8_cla1
if errorlevel 1 echo [WARN] mC_d36_ag8_cla1 failed - continuing
python scripts\runlog.py --name P073_stage2_cla1_matrix --note "[wandb] push arm 2"
set TL_WB_TAG=mC_d36_ag8_cla1
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P073_stage2_cla1_matrix --note "[3/4] paired - the attention axis on cla1, both depths"
python scripts\runlog.py --name P073_stage2_cla1_matrix -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4 mC_cla1 mC_initonly
if errorlevel 1 echo [WARN] paired eval 20 layer failed - continuing
python scripts\runlog.py --name P073_stage2_cla1_matrix -- python scripts\paired_eval.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag8_cla1 mC_d36_ag4_cla1 mC_d36_ag8_nokd
if errorlevel 1 echo [WARN] paired eval 36 layer failed - continuing

echo.
python scripts\runlog.py --name P073_stage2_cla1_matrix --note "[4/4] residency"
python scripts\runlog.py --name P073_stage2_cla1_matrix -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla1_ag4 mC_cla1 --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P073_stage2_cla1_matrix --note "=============================================================================" "READ IN THIS ORDER" "1. json cla_group must read 1 and attn_group 4 / 8 on the two arms." "2. ag1-to-ag4 price ON cla1 = (mC_cla1_ag4 minus mC_cla1) divided by the" "   unique-ternary delta. Compare against B.5's 0.00083, which was cla2." "3. ag4-to-ag8 ON cla1 = (mC_d36_ag8_cla1 minus mC_d36_ag4_cla1). Compare" "   against 0.00381 from result 044, which was cla2. P2 says it survives." "4. the ruler is now chosen automatically by condition (2026-08-26). Read" "   which band the tool printed - do not assume 0.024." "IF THE CLIFF VANISHES  ag8 reopens and result 044's closure was an artifact." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
