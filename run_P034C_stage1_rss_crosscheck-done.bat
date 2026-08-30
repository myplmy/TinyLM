@echo off
REM =============================================================================
REM  P034C stage 1  -  how far apart are the accounting and the allocator.
REM  about 0.2 hours. NO TRAINING. NO GPU.
REM
REM  WHY  (result 016 s24.7 wrote this down as a limit)
REM    Our runtime_mb is a tensor sum. Result 016 has printed the same caveat
REM    every time: RSS overstates because of the allocator, the tensor sum
REM    understates because it drops temporaries. Read both. We never once put
REM    the two in a table.
REM
REM    It matters now. The budget is 36 MiB and our best numbers are 31.8 to
REM    34.8. Headroom of 1.2 to 4.2 MiB, and we do not know the accounting
REM    error. If the allocator takes 3 MiB more then "it fits" is false.
REM
REM  INDEPENDENT VARIABLE
REM    --max-new 32 vs 512. Everything else is held.
REM
REM  PREDICTIONS
REM    M1  RSS delta is 1.2x to 2.0x the accounted value.
REM    M2  going 32 to 512 adds about 7.5 MiB of RSS  (kv_mb 15.0 x 480/1024).
REM    M3  if M2 does not hold, the KV is not actually being held - the generate
REM        path is not caching. That is a defect, not a result (trap 37).
REM
REM  DECISION
REM    ratio under 1.5   quote the accounting, apply a 1.5 safety factor.
REM    1.5 to 3.0        state the factor and redo every budget verdict.
REM    over 3.0          "31.8 MiB fits" is withdrawn until remeasured.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P034C_stage1_rss_crosscheck --note "=============================================================================" "P034C stage 1   accounting vs allocator" "The budget headroom is 1.2 to 4.2 MiB and we do not know the error bar." "=============================================================================="

echo.
python scripts\runlog.py --name P034C_stage1_rss_crosscheck --note "[1/3] short generation - KV barely filled. This is the baseline RSS."
python scripts\runlog.py --name P034C_stage1_rss_crosscheck -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4 mC_initonly_nc mC_cla1_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P034C_stage1_rss_crosscheck --note "[2/3] long generation - KV half filled. M2 lives or dies here."
python scripts\runlog.py --name P034C_stage1_rss_crosscheck -- python scripts\mem_runtime.py --device cpu --max-new 512 --preset m100R1c --models mC_cla2_ag4 mC_initonly_nc mC_cla1_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P034C_stage1_rss_crosscheck --note "[3/3] the 36 layer model too - 18 entries instead of 10"
python scripts\runlog.py --name P034C_stage1_rss_crosscheck -- python scripts\mem_runtime.py --device cpu --max-new 512 --preset m100R1d --models mC_d36_ag4_nokd --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P034C_stage1_rss_crosscheck --note "=============================================================================" "READ IN THIS ORDER" "1. M3 first. RSS at max-new 512 minus RSS at 32, per model. If that is near" "   zero the cache is not being held and steps 1 and 2 measured nothing." "2. M2 - is that difference near kv_mb x 480/1024." "3. M1 - RSS increase over load, divided by (runtime_mb + kv_mb)." "4. that ratio is the safety factor every budget statement now needs." "=============================================================================="

if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
