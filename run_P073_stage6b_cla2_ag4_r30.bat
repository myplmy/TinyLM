@echo off
REM P073 stage 6b  -  R=3 on the cheap-KV body.  RETRY.  About 3.9 hours.
REM
REM   WHY 6b.  Stage 6 died at 1.4 minutes with CUDA out of memory - 14.67 GiB
REM   allocated, 256 MiB more refused.  --no-ckpt with --train-repeat 3.0 is
REM   52 layer visits on the m100 body, and the registry already had the line
REM   that predicts it:
REM
REM     mC_cla2_ag4      20 visits  --no-ckpt   8.89 GB reserved
REM     mC_cla2_ag4_r20  36 visits  --no-ckpt  12.59 GB reserved
REM     gives reserved = 4.27 + 0.231 x visits gives 52 visits = 16.29 GB
REM
REM   It was computable before the run.  CLAUDE.md said "--no-ckpt opens at 20
REM   layers by 36 visits (13.73 GiB)" and that permission got carried to 52
REM   visits.  lint_bat rule 23 now computes visits from the preset and errors.
REM
REM   WHY --no-ckpt STAYS.  The arm this is compared against,
REM   mC_cla2_ag4_r20, has grad_ckpt False.  Dropping --no-ckpt here would add
REM   the grad-checkpoint drift of about 0.0014, which is HALF the expected
REM   signal (20 to 28 visits was -0.0036, so 36 to 52 should be a few
REM   thousandths).  Confounding the measurement with something that large is
REM   worse than paying for the memory another way.
REM
REM   SO M SHRINKS INSTEAD.  --micro-bs 4 --accum 32 keeps the effective batch
REM   at 131,072 tokens, identical to every other run in this line, and halves
REM   activation memory.  Predicted reserved: about 10.3 GB.
REM   The cost is speed: M = 4096 was measured at -8.7 percent (result 007),
REM   so 3.6 hours becomes about 3.9.
REM   DO NOT compare ms/step from this run against the other arms - M differs.
REM
REM   WHAT IT BUYS.  KV entries 26, so 39.0 KB/token, so bf16 19.5 MiB plus
REM   16.8 MiB of weights = 36.3 MiB at 1024 context.  Outside the 32 MiB
REM   optimum, inside the 40 MiB maximum.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P073_stage6b_cla2_ag4_r30 --note "[1/3] train - cla2 body, R=3.0, M halved to fit --no-ckpt"
python scripts\runlog.py --name P073_stage6b_cla2_ag4_r30 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 4 --accum 32 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --attn-group 4 --train-repeat 3.0 --init-from --tag mC_cla2_ag4_r30
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=mC_cla2_ag4_r30
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P073_stage6b_cla2_ag4_r30 --note "[2/3] paired - match the trained schedule, trap 39"
python scripts\runlog.py --name P073_stage6b_cla2_ag4_r30 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r30 mC_cla2_ag4_r20 mC_cla2_ag4 mC_initonly_nc --match-train-repeat --dump-crops runs/logs/p073_cla2_visits.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P073_stage6b_cla2_ag4_r30 --note "[3/3] weights unchanged, entries 26, and what bf16 does to that"
python scripts\runlog.py --name P073_stage6b_cla2_ag4_r30 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4_r30 mC_cla2_ag4_r20 mC_cla2_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P073_stage6b_cla2_ag4_r30 --note "READ IN THIS ORDER" "1. VRAM reserved first. The prediction is about 10.3 GB from the linear" "   fit 4.27 plus 0.231 times visits. If it lands far off, that fit is" "   wrong and rule 23 needs re-deriving." "2. weights must be IDENTICAL to mC_cla2_ag4 - recursion adds visits, not" "   parameters. If the weight column moves, something else changed." "3. kv_entries must be 26. That is the gate that the recursion actually" "   ran at R=3 (trap 37)." "4. only then the quality delta, on the recursion ruler. Use the LARGER" "   estimate 0.0016 (the cla2 seed pair), not 0.0006." "5. the expected gain from 36 to 52 visits is a few thousandths. That is" "   1 to 3 times the ruler - a marginal call by design, so read t as well." "6. do NOT compare ms/step with the other arms. M is 4096 here, 8192 there."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
