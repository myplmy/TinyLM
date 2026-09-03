@echo off
REM P079 stage 6  -  a second seed for the two budget winners.  About 4.0 hours.
REM
REM   WHY THIS IS FIRST.  Result 067 s11.2 named two winners and BOTH are one
REM   seed.  d12_cla2_r20 3.6054 at 30.7 MiB beats the previous 32-budget best
REM   by -0.0835, and d16_cla2_r20 3.5642 at 38.5 MiB beats d16_dense on BOTH
REM   quality and memory.  Those are the headline claims of the session and
REM   nothing under them has been repeated.
REM
REM   WHAT WOULD OVERTURN THEM.  The dense ruler is 0.0021 and the recursion
REM   ruler is 0.0018 (result 039 s12, raised from 0.0006 by the third seeds).
REM   The 32-budget margin is -0.0835, about 46x the ruler - a seed will not
REM   move that.  The 40-budget margin over d16_dense is -0.0115, about 5.5x.
REM   That one CAN move, and it is the claim that says "smaller AND better".
REM
REM   INDEPENDENT VARIABLE: --seed 2024.  Everything else is byte-identical to
REM   stage 4.  Tags get _s2 so the stage 4 checkpoints are untouched.
REM
REM   VISITS AND --no-ckpt.  d12 at R=2 is 20 visits (M x visits = 163,840) and
REM   d16 at R=2 is 28 (229,376).  Both inside the 294,912 ceiling confirmed at
REM   M=8192.  lint_bat rule 23 agrees and dryrun_batch prints the arithmetic.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage6_winner_seeds --note "[1/5] d12_cla2_r20 seed 2024 - the 32 MiB winner"
python scripts\runlog.py --name P079_stage6_winner_seeds -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --tag d12_cla2_r20_s2
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d12_cla2_r20_s2
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage6_winner_seeds --note "[2/5] d16_cla2_r20 seed 2024 - the 40 MiB winner"
python scripts\runlog.py --name P079_stage6_winner_seeds -- python run100m.py train --preset m100s12 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --tag d16_cla2_r20_s2
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d16_cla2_r20_s2
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P079_stage6_winner_seeds --note "[3/5] crops - match the trained schedule, trap 39"
python scripts\runlog.py --name P079_stage6_winner_seeds -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20_s2 d12_cla2_r20 d12_cla2 d12_dense --match-train-repeat --dump-crops runs/logs/p079_s6_d12.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage6_winner_seeds -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 300M --models d16_cla2_r20_s2 d16_cla2_r20 d16_cla2 d16_dense --match-train-repeat --dump-crops runs/logs/p079_s6_d16.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage6_winner_seeds --note "[4/5] join - the two winners against the tied line on the same crops"
python scripts\runlog.py --name P079_stage6_winner_seeds -- python scripts\paired_join.py --crops runs/logs/p079_s6_d12.json runs/logs/p079_s6_d16.json runs/logs/p079_tied.json --pairs d12_cla2_r20_s2:d12_cla2_r20 d16_cla2_r20_s2:d16_cla2_r20 d12_cla2_r20:mC_cla2_ag4_r20 d16_cla2_r20:mC_cla1_ag4_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage6_winner_seeds --note "[5/5] budget - confirm the seed did not move the residency"
python scripts\runlog.py --name P079_stage6_winner_seeds -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s8 --models d12_cla2_r20_s2 d12_cla2_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage6_winner_seeds -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s12 --models d16_cla2_r20_s2 d16_cla2_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage6_winner_seeds --note "READ IN THIS ORDER" "1. the two seed pairs first. abs(delta) against the recursion ruler 0.0018." "   Over 0.0024 and the ruler itself is in question, not the model." "2. THEN d16_cla2_r20 against d16_dense 3.5757.  Stage 4 measured -0.0115." "   If the second seed lands on the other side of 3.5757, the pareto" "   dominance claim in 067 s11.2 becomes seed-dependent and must be" "   written as 'equal quality at 1.9 MiB less' instead." "3. d12_cla2_r20 against mC_cla2_ag4_r20 was -0.0835.  A seed cannot" "   move that.  If it does, suspect the instrument." "4. residency must be UNCHANGED by seed.  A different number there is an" "   accounting bug, not a result." "5. do not read val_loss from the training log.  paired_eval owns it."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
