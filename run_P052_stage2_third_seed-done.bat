@echo off
REM =============================================================================
REM  P052 stage 2  -  a third seed for each family.  about 3.6 hours.
REM
REM  WHY  (result 039 s8.5)
REM    Stage 1 measured one seed pair per family and got 2 sigma = 0.0010 (tied)
REM    and 0.0042 (dense). A pair gives a RANGE, not an estimate of sigma. Three
REM    judgements now hang on those two numbers:
REM      d8_dense vs mC_initonly_nc     +0.0014   equal, on the dense ruler
REM      mC_cla1_ag4 vs standard        +0.0033   significant, on the tied ruler
REM      cycle vs block at 2 unique     -0.0063   1.5x the crossing ruler
REM    The third of these is 1.5x the ruler. If the ruler is 40 percent wider than
REM    we think, that finding evaporates.
REM
REM  INDEPENDENT VARIABLE
REM    seed 1337 / 2024 / 777. Nothing else changes in either family.
REM
REM  PREDICTIONS
REM    S1  both families stay "indistinguishable" against their own two seeds.
REM    S2  the tied spread stays below the dense spread. The mechanism claim in
REM        result 039 s8.2 is that tying averages out per-layer luck.
REM    S3  the range of three tied runs is under 0.002 and of three dense runs
REM        under 0.006. Wider means our rulers are too narrow and every recent
REM        borderline judgement has to be reread.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P052_stage2_third_seed --note "=============================================================================" "P052 stage 2   the third seed" "One pair is a range. Three judgements currently rest on that range." "=============================================================================="

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P052_stage2_third_seed --note "[1/3] tied family - seed 777"
python scripts\runlog.py --name P052_stage2_third_seed -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 777 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --tag mC_initonly_s3
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
set TL_WB_TAG=mC_initonly_s3
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P052_stage2_third_seed --note "[2/3] dense family - seed 777"
python scripts\runlog.py --name P052_stage2_third_seed -- python run100m.py train --preset m100s4 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 777 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d8_dense_s3
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
set TL_WB_TAG=d8_dense_s3
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P052_stage2_third_seed --note "[3/3] three seeds per family, on one ruler each"
python scripts\runlog.py --name P052_stage2_third_seed -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly_s3 mC_initonly_s2 mC_initonly_nc
if errorlevel 1 echo [WARN] step 3a failed - continuing
python scripts\runlog.py --name P052_stage2_third_seed -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models d8_dense_s3 d8_dense_s2 d8_dense
if errorlevel 1 echo [WARN] step 3b failed - continuing

echo.
python scripts\runlog.py --name P052_stage2_third_seed --note "=============================================================================" "READ IN THIS ORDER" "1. the RANGE of three values per family, not the pairwise deltas. Range is what" "   we can defend from three samples." "2. S2 - tied spread below dense spread. Two independent observations of the" "   same direction is the minimum for writing it as a mechanism." "3. update EXPERIMENT_BASELINES B.9.1 with the new numbers and re-read every" "   judgement listed in the WHY block above." "4. three samples is still three. Write the number with that caveat attached." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
