@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P030_Stage5_winner_tokps.bat -- do our winners clear the new floor?
REM ==========================================================================
REM
REM   THE TARGET IS NEW (2026-09-06, user decision, baselines B.19.3)
REM     at least 15 tok/s on a single CPU on a single core. From 80 tok/s
REM     upward, trade speed for quality. Multi-core scaling is a separate
REM     experiment.
REM
REM   WE HAVE NEVER MEASURED OUR OWN WINNERS
REM     result 014 has a real table, but of OTHER models. The 12.5 to 13.2
REM     figure we keep quoting comes from mC_initonly, eq_d8_r40 and
REM     mC_cla1_ag4 - all at 20 visits, all borrowed. d12_cla2_r20 also sits
REM     at 20 visits so the anchor is plausible, and plausible is not
REM     measured. d16_cla2_r20 at 28 visits has no anchor at all.
REM
REM   PRE-REGISTERED VERDICT for d12_cla2_r20 on one thread
REM     15 or above   clears the floor, keep the 32 MiB plan as it stands
REM     12.5 to 15    misses, as the anchors predict. Next step is to price
REM                   a lower-visit shape (d12 without recursion, 12 visits)
REM     below 12.5    worse than the anchors. Look at the cla_group 2 second
REM                   order term (6 to 10 percent, result 014 s14) first
REM
REM   THE DEPLOYMENT PATH IS THREE FLAGS
REM     --drop-latent --int8-store --unpack-cache. Without them the numbers
REM     are not comparable with the result 014 table at all: the same model
REM     reads 34.67 versus 12.50 tok/s depending on path (014 s12.4).
REM
REM   --infer-repeat MUST MATCH TRAINING
REM     both checkpoints were trained with --train-repeat 2.0. Evaluating at
REM     1.0 measures a function that was never trained AND halves the visit
REM     count, which is exactly the quantity we are trying to price.
REM
REM   NO TRAINING. CPU inference. COST: about 0.4h.
REM   PLAN: test_plan/P030 (Korean filename) Stage5
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P030_stage5_winner_tokps --note "[1/2] d12_cla2_r20 - 32 MiB winner, 20 visits, threads 1 and 4"
python scripts\runlog.py --name P030_stage5_winner_tokps -- python scripts\bench_infer.py --models d12_cla2_r20 --preset m100s8 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache --infer-repeat 2.0
if errorlevel 1 echo [WARN] d12 arm failed - continuing

python scripts\runlog.py --name P030_stage5_winner_tokps --note "[2/2] d16_cla2_r20 - 40 MiB winner, 28 visits, no anchor exists for this one"
python scripts\runlog.py --name P030_stage5_winner_tokps -- python scripts\bench_infer.py --models d16_cla2_r20 --preset m100s12 --data ko-en --tokens 300M --device cpu --threads 1 4 --max-new 128 --reps 3 --drop-latent --int8-store --unpack-cache --infer-repeat 2.0
if errorlevel 1 echo [WARN] d16 arm failed - continuing

echo.
python scripts\runlog.py --name P030_stage5_winner_tokps --note "=================================================================" "READ IN THIS ORDER" "1. the printed visit count. d12 must say 20 and d16 must say 28." "   If either says 12 or 16 then --infer-repeat did not take and the" "   run measured a different function (trap 39)." "2. the runtime MB the script computes. It should land near 30.7 and" "   38.5. If it does not, the deployment flags did not all apply." "3. thread 1 tok/s against 15. That is the whole question. The" "   verdict rows are in the header - do not invent a new threshold." "4. thread 4 tok/s is a bonus reading, not the target. The user" "   asked for single core. Record it, do not judge on it." "5. Windows timing is noisy. Read the median of 3 and do NOT compare" "   with numbers measured on another day (7.5 percent session drift)." "6. this is NOT the LUT path. Unpacking is 41 to 56 percent of the" "   time, so a working LUT kernel would be 1.7 to 2.0x on top." "================================================================="

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
