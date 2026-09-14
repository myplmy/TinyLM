@echo off
setlocal
REM P085 Stage10c: same-panel held-out version control, training 0.
REM Independent variable: v2.9 versus v3.0 on the same six seed2 checkpoints.
REM Cost: about 0.9 GPU-hour. Run alone. Watch the first model load.
REM Sequential dependencies stop the batch on failure.

python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control --note "PURPOSE: measure v2.9 on the exact seed2 panel already used for v3.0."
python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control --note "LIMIT: the existing v3.0 JSON lacks the new full condition signature, so comparison is core-only with an explicit metadata gap."

if not exist "runs\census\stage1_heldout.v3.0_independent_s2_census.json" goto MISSINGV3
if exist "runs\census\P085_stage10c_v29_fetch.log" goto EXISTS
if exist "runs\census\stage1_heldout.v2.9_independent_s2_stage10c_census.json" goto EXISTS
if exist "runs\census\stage1_heldout.v2.9_vs_v3.0_independent_s2_stage10c_compare.json" goto EXISTS

python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control --note "[1/3] activate held-out v2.9 in the benchmark cache"
python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control -- python scripts\fetch_bench_data.py --only stage1_heldout --heldout-version 2.9 --force --log runs\census\P085_stage10c_v29_fetch.log
if errorlevel 1 goto ERROR

python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control --note "[2/3] census v2.9 with the independent seed2 six-model panel"
python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control -- python scripts\census_heldout_discrimination.py --heldout-version 2.9 --models d12_cla2_norecur_s2=m100s8 d12_cla2_r20_s2=m100s8 d14_cla2_norecur_s2=m100s10 d16_cla2_norecur_s2=m100s12 d16_cla2_r20_s2=m100s12 d18_cla2_norecur_s2=m100s14 --n 4500 --out runs\census\stage1_heldout.v2.9_independent_s2_stage10c_census.json
if errorlevel 1 goto ERROR

python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control --note "[3/3] paired version comparison; legacy v3.0 metadata gap is explicit"
python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control -- python scripts\compare_heldout_census.py --baseline runs\census\stage1_heldout.v2.9_independent_s2_stage10c_census.json --candidate runs\census\stage1_heldout.v3.0_independent_s2_census.json --out runs\census\stage1_heldout.v2.9_vs_v3.0_independent_s2_stage10c_compare.json --allow-legacy-metadata-gap
if errorlevel 1 goto ERROR

python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control --note "VERDICT: CORE_REGRESSION only if v3.0 has lower D9, higher zero-info, and lower total bits on this same panel. Mixed directions are inconclusive."
python scripts\runlog.py --name P085_stage10c_heldout_v29_seed2_control --note "DONE. This is G0 diagnosis, not held-out promotion and not a sealed-final pass."
if not defined TL_NOPAUSE pause
exit /b 0

:MISSINGV3
echo [ERROR] Missing existing v3.0 seed2 census JSON.
if not defined TL_NOPAUSE pause
exit /b 2

:EXISTS
echo [ERROR] Stage10c evidence path already exists. Preserve it and use a new stage suffix.
if not defined TL_NOPAUSE pause
exit /b 2

:ERROR
echo [ERROR] P085 Stage10c stopped because a required step failed.
if not defined TL_NOPAUSE pause
exit /b 1
