@echo off
REM P079 stage 5  -  second seeds for the two arms the conclusion rests on.
REM   About 2.8 hours.
REM
REM   WHY.  Result 067's headline is that d12_dense at 3.6130 beats every tied
REM   model we own by 0.063, and that d8_dense at 3.6776 ties our standard
REM   control while being smaller on every memory axis.
REM
REM     d8_dense  has THREE seeds - it is where the dense ruler 0.0021 comes from
REM     d12_dense has ONE
REM     d16_dense has ONE
REM     d20_dense has ONE
REM
REM   The depth curve's gaps are 16 to 31 times the ruler, so a second seed
REM   will not overturn the SHAPE.  What it protects is the specific number
REM   that stages 3 and 4 are being scored against, and the claim that d12 is
REM   the best model in the 32 MiB budget.  A 0.006 seed excursion would not
REM   change the curve but could change which arm wins a budget class.
REM
REM   INDEPENDENT VARIABLE: --seed 2024.  Everything else matches result 067
REM   exactly, including --no-ckpt and --ce-chunk 2048.
REM
REM   THIS IS ALSO A RULER CHECK.  The dense ruler was measured on d8, an
REM   8-layer body.  If the d12 and d16 seed gaps are much larger than 0.0021,
REM   the ruler is depth-dependent and every dense judgement needs re-reading.
REM   That would itself be worth the 2.8 hours.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage5_depth_seeds --note "[1/4] d12 dense, seed 2024"
python scripts\runlog.py --name P079_stage5_depth_seeds -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d12_dense_s2
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d12_dense_s2
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P079_stage5_depth_seeds --note "[2/4] d16 dense, seed 2024"
python scripts\runlog.py --name P079_stage5_depth_seeds -- python run100m.py train --preset m100s12 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d16_dense_s2
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=d16_dense_s2
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P079_stage5_depth_seeds --note "[3/4] paired - seed against seed, within preset"
python scripts\runlog.py --name P079_stage5_depth_seeds -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_dense_s2 d12_dense --dump-crops runs/logs/p079_s5_d12.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage5_depth_seeds -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 300M --models d16_dense_s2 d16_dense --dump-crops runs/logs/p079_s5_d16.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage5_depth_seeds --note "[4/4] join - is the ruler the same at every depth"
python scripts\runlog.py --name P079_stage5_depth_seeds -- python scripts\paired_join.py --crops runs/logs/p079_s5_d12.json runs/logs/p079_s5_d16.json runs/logs/p079_d08.json --pairs d12_dense_s2:d12_dense d16_dense_s2:d16_dense d8_dense:d8_dense_s2 d8_dense:d8_dense_s3
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage5_depth_seeds --note "READ IN THIS ORDER" "1. the seed gap at each depth. The dense ruler 0.0021 was measured on d8." "2. if d12 and d16 gaps are much larger, the ruler is depth-dependent and" "   the correct move is to WIDEN the ruler, not to explain the outlier." "3. seed-pair SE is about twice the architecture-pair SE (039 s9.4), so" "   read the ruler rather than the t statistic here." "4. this changes no conclusion about the SHAPE of the depth curve - those" "   gaps are 16 to 31 times the ruler either way." "5. it does decide how tightly stage 3 and stage 4 can be scored."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
