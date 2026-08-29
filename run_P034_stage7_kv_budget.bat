@echo off
REM =============================================================================
REM  P034 stage 7  -  measure the KV cache residency we just implemented
REM                   no training. about 10 minutes. GPU not required.
REM
REM  WHY  (handoff Q1, REVIEW3 unknown 8, user instruction 10)
REM    Until 2026-08-29 the residency formula had no KV term. REVIEW3 section 18
REM    DERIVED a table and that table says the KV cache is 15 to 54 MiB at seq
REM    1024 - as large as or larger than the whole plan-B weight residency
REM    (16.9 to 19.8 MiB). If the derivation is right, the weight-only Pareto in
REM    result 047 s13 and 059 s13 is not a deployment Pareto.
REM
REM  WHAT IS NEW
REM    Transformer.kv_report() replicates the forward cache key (owner, pass) and
REM    mem_runtime prints it. It reads train_repeat from the checkpoint so a
REM    recursively trained model is counted on the schedule it was trained with.
REM
REM  PREDICTIONS  (DERIVED, not measured - REVIEW3 section 18.2)
REM    E1  mC_initonly_nc    10 entries  15.0 MiB at seq 1024 fp32
REM    E2  mC_cla1_ag4       20 entries  30.0 MiB
REM    E3  mC_cla1_ag4_r20   36 entries  54.0 MiB   the direct one to check
REM    E4  mC_d36_ag4_nokd   18 entries  27.0 MiB
REM    E5  kv_mb is exactly proportional to seq. 512 must be half of 1024.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P034_stage7_kv_budget --note "=============================================================================" "P034 stage 7   KV cache residency - first measurement" "The formula had no KV term until today. REVIEW3 s18 derived the numbers." "This batch turns the derivation into a measurement. No training." "=============================================================================="

echo.
python scripts\runlog.py --name P034_stage7_kv_budget --note "[1/4] the three models that carry the current Pareto claims, seq 1024"
python scripts\runlog.py --name P034_stage7_kv_budget -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_cla1_ag4 mC_cla1_ag4_r20 --drop-latent --int8-store --kv-seq 1024
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P034_stage7_kv_budget --note "[2/4] the standard model - 36 layers, cla2"
python scripts\runlog.py --name P034_stage7_kv_budget -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1d --models mC_d36_ag4_nokd --drop-latent --int8-store --kv-seq 1024
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P034_stage7_kv_budget --note "[3/4] E5 linearity - the same models at seq 512. Every kv_mb must halve."
python scripts\runlog.py --name P034_stage7_kv_budget -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_cla1_ag4 mC_cla1_ag4_r20 --drop-latent --int8-store --kv-seq 512
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P034_stage7_kv_budget --note "[4/4] plan B assembled, with KV. This is the number REVIEW3 needs."
python scripts\runlog.py --name P034_stage7_kv_budget -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_cla1_ag4 mC_cla1_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 4 failed - continuing

echo.
python scripts\runlog.py --name P034_stage7_kv_budget --note "=============================================================================" "READ IN THIS ORDER" "1. kv_entries first. 10 / 20 / 36 / 18. If they differ from the prediction the" "   key replication is wrong and nothing below matters." "2. E5 - seq 512 must be exactly half of seq 1024." "3. step [4] runtime_mb plus kv_mb against the 36 MiB four-thread budget." "   Weight-only said 16.9 was the smallest. With KV it may not be." "4. if the ordering by weights plus KV differs from the ordering by weights," "   REVIEW3 section 15 must be rewritten and result 047 s13.3 relabelled." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
