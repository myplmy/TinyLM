@echo off
REM =============================================================================
REM  P030 stage 2E  -  the 36 MiB body on CPU, with a measured background load.
REM  about 0.4 hours. NO TRAINING.
REM
REM  WHY  two reasons
REM    1. result 058 s13 produced mC_cla2_ag4, the first model besides the
REM       control that fits 36 MiB once KV is counted (16.8 + 15.0 = 31.8).
REM       We have no CPU speed for it. Both 058 s13.8 and 014 s13.8 asked.
REM    2. bench_infer now measures the background CPU load for 10 seconds BEFORE
REM       any inference and prints it as a reference value. Until now ext was a
REM       number with nothing to compare it to - you could not tell background
REM       from mis-attribution. This is the first run with the baseline.
REM
REM  INDEPENDENT VARIABLE
REM    model, at fixed thread count. The dbase column is instrumentation.
REM
REM  PREDICTIONS
REM    E1  mC_cla2_ag4 lands within 5 percent of mC_initonly at 1 thread. Both
REM        are 20 visits and the visit-count law held with no exception in
REM        result 014 s13.1.
REM    E2  dbase stays near zero on every row. If it is large and positive our
REM        run is provoking system work that is not charged to our process.
REM    E3  the baseline is 6 to 12 percent on the user machine - that is what
REM        task manager showed. In the AI environment it measured 7.9.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P030_stage2E_cpu_baseline --note "=============================================================================" "P030 stage 2E   the 36 MiB body on CPU" "First run with a measured background baseline. ext now has something to be" "compared against." "=============================================================================="

echo.
python scripts\runlog.py --name P030_stage2E_cpu_baseline --note "[1/2] mC_cla2_ag4 against its two neighbours"
python scripts\runlog.py --name P030_stage2E_cpu_baseline -- python scripts\bench_infer.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 mC_initonly mC_cla1_ag4 --device cpu --threads 1 4 --max-new 128 --reps 5 --drop-latent --int8-store --cpu-watch --cpu-ext-limit 15 --cpu-baseline 10
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2E_cpu_baseline --note "[2/2] the recursion winner at its trained schedule, for the frontier table"
python scripts\runlog.py --name P030_stage2E_cpu_baseline -- python scripts\bench_infer.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20nc mC_cla2_ag4_r20 --device cpu --threads 1 4 --max-new 128 --reps 5 --drop-latent --int8-store --infer-repeat 2.0 --cpu-watch --cpu-ext-limit 15 --cpu-baseline 10
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P030_stage2E_cpu_baseline --note "=============================================================================" "READ IN THIS ORDER" "1. the baseline line at the top, before any table. That is the reference." "2. dbase per row. Near zero means the ext on that row is background." "3. E1 - mC_cla2_ag4 against mC_initonly at 1 thread, both 20 visits." "4. add the rows to the deployment frontier table in result 014 s13.4." "5. the limit does not block anything now. Over-limit rows are still valid" "   measurements as long as the rows agree with each other." "=============================================================================="

if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
