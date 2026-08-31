@echo off
REM P079 stage 3  -  the cheapest lever on the thin dense bodies.  About 2.8 hours.
REM
REM   WHAT RESULT 067 CHANGED.  The depth curve put d12_dense at 3.6130, which
REM   is 0.063 better than every tied model we own, and d8_dense at 3.6776,
REM   which is inside the dense ruler of our standard control mC_initonly_nc
REM   (3.6762) while being smaller in parameters, packed storage AND KV.
REM
REM   Stage 1 and stage 2 vary mlp_group on these bodies - the lever that buys
REM   WEIGHTS.  Nobody has varied cla_group on them, and result 058 s13 showed
REM   cla_group is the only lever we have that aims at KV instead of weights:
REM   it halves KV entries exactly, for a measured quality cost of -0.0268 on
REM   the 20-layer tied body.
REM
REM   INDEPENDENT VARIABLE: --cla-group 2, at fixed depth, dense MLP.
REM   No tying, no recursion.  One flag against d12_dense and d16_dense.
REM
REM   ESTIMATED BUDGET (weights plus bf16 KV at 1024, LUT plus int8 embedding):
REM     d12_dense          23.3 + 9.0  = 32.3   quality 3.6130
REM     d12 cla2           23.3 + 4.5  = 27.8   quality unknown
REM     d16_dense          28.0 + 12.0 = 40.0   quality 3.5757
REM     d16 cla2           28.0 + 6.0  = 34.0   quality unknown
REM   Stage 0b measures the weight halves. These are estimates until it runs.
REM
REM   PREDICTION.  If the 20-layer cla2 cost of -0.0268 transfers, d12 cla2
REM   lands near 3.640 at 27.8 MiB and d16 cla2 near 3.603 at 34.0 MiB, which
REM   would make them the best models in the 32 and 40 MiB targets by a wide
REM   margin.  If the cost is much larger on a shallow body, that is the
REM   result - it would mean CLA needs depth to hide behind.
REM
REM   RULER: dense 2 sigma 0.0021.  Cross-family against tied uses 0.0021 too.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage3_thin_cla2 --note "[1/5] d12 dense with cla_group 2 - KV entries 12 to 6"
python scripts\runlog.py --name P079_stage3_thin_cla2 -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --tag d12_cla2
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d12_cla2
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage3_thin_cla2 --note "[2/5] d16 dense with cla_group 2 - KV entries 16 to 8"
python scripts\runlog.py --name P079_stage3_thin_cla2 -- python run100m.py train --preset m100s12 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --tag d16_cla2
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d16_cla2
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P079_stage3_thin_cla2 --note "[3/5] crops - each preset separately, joined afterwards"
python scripts\runlog.py --name P079_stage3_thin_cla2 -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2 d12_dense --dump-crops runs/logs/p079_s3_d12.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage3_thin_cla2 -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 300M --models d16_cla2 d16_dense --dump-crops runs/logs/p079_s3_d16.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage3_thin_cla2 --note "[4/5] join - the cla2 cost on each body, and against the tied line"
python scripts\runlog.py --name P079_stage3_thin_cla2 -- python scripts\paired_join.py --crops runs/logs/p079_s3_d12.json runs/logs/p079_s3_d16.json runs/logs/p079_tied.json --pairs d12_cla2:d12_dense d16_cla2:d16_dense d12_cla2:mC_initonly_nc d12_cla2:mC_cla2_ag4 d16_cla2:mC_cla2_ag4_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage3_thin_cla2 --note "[5/5] the memory half - without it a quality win is not a win"
python scripts\runlog.py --name P079_stage3_thin_cla2 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s8 --models d12_cla2 d12_dense --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage3_thin_cla2 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s12 --models d16_cla2 d16_dense --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage3_thin_cla2 --note "READ IN THIS ORDER" "1. kv_entries FIRST. d12 cla2 must read 6 and d16 cla2 must read 8." "   If they read 12 and 16 the flag never reached the model and every" "   number below is fiction (trap 37)." "2. weights must be UNCHANGED against the dense twin. CLA shares K and V" "   projections across pairs of layers, so a small drop is expected -" "   a large one means something else moved." "3. the cla2 cost per body, on the dense ruler 0.0021. Compare it with the" "   -0.0268 measured on the 20-layer tied body (058 s11)." "4. THEN the budget column. Quality alone is not a result here." "5. run 4 requires runs/logs/p079_tied.json from stage 0b. If stage 0b has" "   not run, that join step will skip the cross-family pairs and only the" "   within-preset ones are valid."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
