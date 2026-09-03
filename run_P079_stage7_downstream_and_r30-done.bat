@echo off
REM P079 stage 7  -  does the budget winner win on tasks too, and does a third
REM visit still pay in a thin body.  About 3.1 hours.
REM
REM   THE GAP.  Result 067 s11 picked two winners on full-val, which is
REM   compression.  Nobody has asked whether the ordering survives on tasks.
REM   Result 056 already showed the two can disagree: recursion won HellaSwag
REM   by 3.7 points while LOSING answer CE 3.6240 to 3.9226 - ranking got
REM   better and calibration got worse.  So this is not a formality.
REM
REM   ONLY THREE BENCHMARKS ARE ALIVE (result 056): hellaswag, piqa, arc_easy.
REM   MMLU is at chance, BoolQ is below the majority class, MuSR exceeds seq.
REM   We run the three and read them as three, not as a mean.
REM
REM   THE SECOND QUESTION.  R=3 on the 20-layer cla2 body bought -0.0059 for
REM   6.0 MiB of KV - 2.9x the price of the 20 to 36 visit step (058 s16).
REM   Recursion is stronger in thin bodies (-0.0309 at d12 against -0.0172 at
REM   d20), so the third visit may be worth more there.  d12_cla2_r30 lands
REM   at an estimated 23.2 + 10.5 = 33.7 MiB, between the two winners.
REM
REM   VISITS AND --no-ckpt.  d12 at R=3 is 2 + 8x3 + 2 = 28 visits,
REM   M x visits = 229,376, inside the 294,912 ceiling.
REM
REM   INDEPENDENT VARIABLE: --train-repeat 3.0 against stage 4's 2.0.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage7_downstream_and_r30 --note "[1/5] d12 cla2 with R=3.0 - 28 visits, 14 KV entries"
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 3.0 --tag d12_cla2_r30
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d12_cla2_r30
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P079_stage7_downstream_and_r30 --note "[2/5] crops and budget for the new arm"
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r30 d12_cla2_r20 d12_cla2 d12_dense --match-train-repeat --dump-crops runs/logs/p079_s7_d12.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s8 --models d12_cla2_r30 d12_cla2_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage7_downstream_and_r30 --note "[3/5] hellaswag - the 32 MiB winner against the tied line it replaces"
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task hellaswag --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_cla2 d12_dense --n 400
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task hellaswag --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20 mC_initonly_nc --n 400
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage7_downstream_and_r30 --note "[4/5] piqa and arc_easy - same two groups"
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task piqa --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_cla2 d12_dense --n 400
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task piqa --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20 mC_initonly_nc --n 400
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task arc_easy --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_cla2 d12_dense --n 400
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task arc_easy --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20 mC_initonly_nc --n 400
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage7_downstream_and_r30 --note "[5/5] the deeper winner on the same three tasks"
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task hellaswag --preset m100s12 --data ko-en --tokens 300M --models d16_cla2_r20 d16_dense --n 400
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task piqa --preset m100s12 --data ko-en --tokens 300M --models d16_cla2_r20 d16_dense --n 400
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage7_downstream_and_r30 -- python scripts\eval_bench_suite.py --task arc_easy --preset m100s12 --data ko-en --tokens 300M --models d16_cla2_r20 d16_dense --n 400
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage7_downstream_and_r30 --note "READ IN THIS ORDER" "1. the three task accuracies as THREE numbers.  Chance is 25 for" "   hellaswag and arc_easy and 50 for piqa.  Result 056 measured 30.0" "   to 33.7 on hellaswag and 51.7 to 56.7 on piqa - the whole live range" "   is a few points wide, so n=400 gives about 2.3 points of standard" "   error.  A 2-point difference is noise." "2. does the full-val ordering survive.  d12_cla2_r20 beats" "   mC_cla2_ag4_r20 by -0.0835 on full-val.  If tasks disagree, say so" "   plainly - result 056 already saw ranking and calibration move in" "   opposite directions." "3. THEN d12_cla2_r30 against d12_cla2_r20 on the recursion ruler 0.0018." "   The 20-layer body paid 0.00098 nats per MiB for the third visit." "   Cheaper here means recursion scales with thinness; the same or worse" "   means the 32 winner is already at its best visit count." "4. kv_entries for d12_cla2_r30 must read 14.  That is the trap-37 gate." "5. do not average the three tasks into one score."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
