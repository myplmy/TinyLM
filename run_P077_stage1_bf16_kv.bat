@echo off
REM P077 stage 1  -  what does bf16 KV cost.
REM
REM   WHY NOW.  Result 062 rejected --repeat-kv-reuse (cost 5.4x the recursion
REM   gain), which closed the ENTRY axis. KV = entries x tokens x bytes, so the
REM   remaining levers are bytes (this) and tokens (P081 StreamingLLM).
REM
REM   Implemented 2026-08-30: cfg.kv_dtype, cast on store only, computation is
REM   raised back to fp32. Default fp32 skips the cast = bit identical.
REM
REM   K1 GATE FIRST.  diag_kvcache compares cached vs teacher-forced logits.
REM   With fp32 that deviation is the existing baseline. With bf16 it must be
REM   small but NONZERO - exactly zero would mean the flag did nothing.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P077_stage1_bf16_kv --note "[1/4] K1 gate - baseline cache equivalence at fp32"
python scripts\runlog.py --name P077_stage1_bf16_kv -- python scripts\diag_kvcache.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1_bf16_kv --note "[2/4] K1 gate - the same thing with bf16 KV. Nonzero and small is the pass"
python scripts\runlog.py --name P077_stage1_bf16_kv -- python scripts\diag_kvcache.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1_bf16_kv --note "[3/4] accounting - KV should be exactly half"
python scripts\runlog.py --name P077_stage1_bf16_kv -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4 mC_initonly_nc --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1_bf16_kv --note "[4/4] and the recursive arm, where KV is the binding constraint"
python scripts\runlog.py --name P077_stage1_bf16_kv -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla1_ag4_r20 mC_cla2_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1_bf16_kv --note "READ IN THIS ORDER" "1. step 2 first. If the deviation is EXACTLY the same as step 1, the flag did" "   nothing and steps 3 and 4 are accounting fiction (trap 37)." "2. the size of that deviation. Compare it to the LUT per-row deviation, which" "   result 028 priced at +0.0038 to +0.0068 bpb." "3. step 3 - kv_mb must be exactly half of the fp32 number." "4. step 4 - mC_cla1_ag4_r20 goes 54.0 to 27.0, total 70.9 to 43.9. Still over" "   budget. mC_cla2_ag4 goes 15.0 to 7.5, total 31.8 to 24.3." "5. quality cost is NOT measured here. Teacher-forced eval does not use the" "   cache. That needs a generation-based eval and it is stage 2."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
