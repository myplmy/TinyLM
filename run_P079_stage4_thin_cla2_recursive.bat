@echo off
REM P079 stage 4  -  thin dense, cheap KV, and recursion on top.  About 4.7 hours.
REM
REM   THE STACK.  Stage 3 buys KV with cla_group.  Recursion then buys quality
REM   with visits - and on a cla2 body it buys MORE: result 058 s14 measured
REM   -0.0172 on cla2 against -0.0107 on cla1, a factor of 1.61.
REM
REM   Recursion also spends KV, because entries scale with visits.  On a cla2
REM   body that spend is halved, which is exactly why the pairing is worth a
REM   run.  For d12 at R=2: 24 visits, 12 entries, bf16 KV 9.0 MiB - the SAME
REM   KV as plain d12_dense, with the quality of a deeper model.
REM
REM   ESTIMATED BUDGET (weights plus bf16 KV at 1024):
REM     d12 cla2 r20   23.3 + 9.0  = 32.3   at the optimum target
REM     d16 cla2 r20   28.0 + 12.0 = 40.0   at the maximum target
REM
REM   INDEPENDENT VARIABLE: --train-repeat 2.0 on top of stage 3's arms.
REM
REM   VISIT COUNT AND --no-ckpt.  d12 at R=2 is 2 + 8x2 + 2 = 20 visits and
REM   d16 at R=2 is 2 + 12x2 + 2 = 28 visits.  Both are inside the measured
REM   36-visit ceiling, so --no-ckpt is allowed here and lint_bat rule 23
REM   agrees.  It also has to be on, because the stage 3 arms it is compared
REM   against ran with it.
REM
REM   PREREQUISITE.  Stage 3 must have produced d12_cla2 and d16_cla2 for the
REM   comparison to mean anything.  The training here does not depend on them
REM   (both initialise from the same dense parent), so this batch still runs
REM   standalone - the paired steps will simply skip the missing tags.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive --note "[1/5] d12 cla2 with R=2.0 - 20 visits, 12 KV entries"
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --tag d12_cla2_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d12_cla2_r20
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive --note "[2/5] d16 cla2 with R=2.0 - 28 visits, 16 KV entries"
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive -- python run100m.py train --preset m100s12 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --tag d16_cla2_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d16_cla2_r20
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive --note "[3/5] crops - trap 39, the trained schedule must be matched"
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_cla2 d12_dense --match-train-repeat --dump-crops runs/logs/p079_s4_d12.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 300M --models d16_cla2_r20 d16_cla2 d16_dense --match-train-repeat --dump-crops runs/logs/p079_s4_d16.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive --note "[4/5] join - against the whole tied line at once"
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive -- python scripts\paired_join.py --crops runs/logs/p079_s4_d12.json runs/logs/p079_s4_d16.json runs/logs/p079_tied.json --pairs d12_cla2_r20:d12_cla2 d16_cla2_r20:d16_cla2 d12_cla2_r20:mC_initonly_nc d12_cla2_r20:mC_cla2_ag4_r20 d16_cla2_r20:mC_cla1_ag4_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive --note "[5/5] the budget - weights plus bf16 KV at 1024"
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s8 --models d12_cla2_r20 d12_cla2 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s12 --models d16_cla2_r20 d16_cla2 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage4_thin_cla2_recursive --note "READ IN THIS ORDER" "1. kv_entries. d12 cla2 r20 must read 12 and d16 cla2 r20 must read 16." "   Those are 2x the stage 3 numbers because visits doubled - that IS the" "   recursion gate (trap 37)." "2. VRAM reserved. 20 and 28 visits are inside the measured 36 ceiling," "   so --no-ckpt should hold. If either OOMs, the linear fit in" "   058 s15.2 does not transfer to dense bodies and that is worth writing." "3. the recursion gain per body, on the recursion ruler. Use the LARGER" "   estimate 0.0016, not 0.0006." "4. THEN the total budget. d12 cla2 r20 is estimated at 32.3 MiB and the" "   optimum target is 32. A tenth of a MiB decides whether it counts." "5. cross-family pairs use ruler 0.0021, not 0.0006. paired_join picks" "   that automatically and prints which one it used." "6. this does not pick a deployment model. That is a REVIEW call."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
