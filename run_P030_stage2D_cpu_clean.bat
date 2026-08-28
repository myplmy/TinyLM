@echo off
REM =============================================================================
REM  P030 stage 2D  -  re-measure CPU speed WITH contamination monitoring
REM                    no training. about 0.6 hours. GPU not required.
REM
REM  WHY  (user, 2026-08-29)
REM    The int8 deployment-path numbers may have been contaminated by other CPU
REM    programs running at the same time.
REM    Correct concern. Stage 2C measured on a Windows desktop and recorded NOTHING
REM    about what else was running. A number nobody can reproduce is not a number.
REM
REM  WHAT IS NEW
REM    bench_infer.py now has --cpu-watch and --cpu-ext-limit. It samples system and
REM    own-process CPU across each measurement window, prints external load as a
REM    percentage of one core, RE-MEASURES a repetition that exceeded the limit, and
REM    marks the row if the retry also exceeded it. Requires psutil.
REM
REM  ALSO NEW HERE
REM    The four shallow dense models and the recursion winner have never had their
REM    CPU speed measured at all - result 059 section 12.5 predicts them from the
REM    linear model (b = 3.081 ms per visit) and that prediction is load-bearing for
REM    the claim that d8_dense is 1.86x faster than mC_initonly_nc.
REM
REM  PREDICTIONS
REM    D1  mC_initonly reproduces 12.50 tok/s within 5 percent. If it does not, the
REM        stage 2C table is contaminated and result 014 section 12 must be redone.
REM    D2  external load stays under 25 percent of one core on an idle desktop.
REM    D3  d8_dense lands near 23 tok/s (8 visits) - result 059 section 12.5.
REM    D4  eq_d8_r40 lands near mC_initonly (both 20 visits) - the visit-count law
REM        from result 014 section 12.2 predicts they are the same speed.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P030_stage2D_cpu_clean --note "=============================================================================" "P030 stage 2D   CPU speed re-measured with contamination monitoring" "Stage 2C recorded nothing about other processes. This one does." "Also the first CPU measurement of the shallow dense family. No training." "=============================================================================="
echo.
python scripts\runlog.py --name P030_stage2D_cpu_clean --note "CLOSE OTHER PROGRAMS BEFORE CONTINUING. The point of this run is a clean CPU." "The ext column shows external load; a contaminated row is not a measurement."
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P030_stage2D_cpu_clean --note "[1/4] reproduce the stage 2C row - D1 lives or dies here"
python scripts\runlog.py --name P030_stage2D_cpu_clean -- python scripts\bench_infer.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_cla1_ag4 --device cpu --threads 1 4 --max-new 128 --reps 5 --drop-latent --int8-store --cpu-watch --cpu-ext-limit 25
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2D_cpu_clean --note "[2/4] the standard model"
python scripts\runlog.py --name P030_stage2D_cpu_clean -- python scripts\bench_infer.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_nokd --device cpu --threads 1 4 --max-new 128 --reps 5 --drop-latent --int8-store --cpu-watch --cpu-ext-limit 25
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2D_cpu_clean --note "[3/4] the shallow dense family - never measured on CPU. D3."
python scripts\runlog.py --name P030_stage2D_cpu_clean -- python scripts\bench_infer.py --preset m100s4 --data ko-en --tokens 300M --models d6_dense d8_dense d10_dense d12_dense eq_d8_dense --device cpu --threads 1 4 --max-new 128 --reps 5 --drop-latent --int8-store --cpu-watch --cpu-ext-limit 25
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2D_cpu_clean --note "[4/4] the recursion winner at its trained schedule. D4."
python scripts\runlog.py --name P030_stage2D_cpu_clean -- python scripts\bench_infer.py --preset m100s4 --data ko-en --tokens 300M --models eq_d8_r40 --device cpu --threads 1 4 --max-new 128 --reps 5 --drop-latent --int8-store --infer-repeat 4.0 --cpu-watch --cpu-ext-limit 25
if errorlevel 1 echo [WARN] step 4 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2D_cpu_clean --note "=============================================================================" "READ IN THIS ORDER" "1. the ext column FIRST. If any row is marked contaminated, that row is not a" "   measurement. Re-run when the machine is idle." "2. D1 - mC_initonly against 12.50 from stage 2C. Within 5 percent means the" "   stage 2C table stands. Outside it means result 014 section 12 needs redoing." "3. D3 - d8_dense against the predicted 23.2 tok/s. Result 059 section 12.5" "   claims d8_dense is 1.86x faster than mC_initonly_nc at equal quality and" "   that claim currently rests on a model, not a measurement." "4. D4 - eq_d8_r40 against mC_initonly. Both are 20 visits. If they differ by" "   more than 10 percent the visit-count law (014 section 12.2) has an exception" "   and recursion is NOT free at decode the way depth is." "5. tabulate tok/s against resident MiB for all of them. That table is the" "   deployment frontier and REVIEW3 needs it." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
