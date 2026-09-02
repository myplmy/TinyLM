@echo off
REM P079 stage 0b  -  the two holes stage 0 left.  About 0.5 hours, no training.
REM
REM   Stage 0 drew the depth curve and then could not do two things:
REM
REM     1. It never measured DEPLOYMENT resident memory for the dense arms.
REM        The 978.0 MB printed in the log is report()'s fp32 current
REM        implementation, not the LUT plus int8-embedding plus latent-release
REM        path we actually deploy.  The batch tail claimed "resident memory
REM        scales with depth here" while nothing on that path was measured.
REM
REM     2. paired_eval exited 2 four times.  One model is not a pair, and
REM        checkpoints live under {preset}_..., so cross-preset arms can only
REM        be loaded one at a time.  The depth curve therefore had no paired SE.
REM
REM   BOTH ARE FIXED WITHOUT NEW TRAINING.
REM     - paired_eval now writes --dump-crops BEFORE the "fewer than 2" exit,
REM       so a single-model call still produces its crop file.
REM     - scripts/paired_join.py joins those files across presets.  It was
REM       verified by reproducing paired_eval's own numbers exactly
REM       (+0.0117 / SE 0.0005 / t 21.82 / 27.7 percent).
REM
REM   WHAT THIS DECIDES.  d12_dense scores 3.6130, which is 0.0646 better than
REM   d8_dense and 0.063 better than every tied model we own.  Its estimated
REM   budget is 23.3 MiB of weights plus 9.0 MiB of bf16 KV at 1024 context =
REM   about 32.3 MiB.  If that estimate holds, d12_dense is the best model in
REM   the repository at the 32 MiB target and it already exists.
REM   This batch turns that estimate into a measurement.
REM
REM   RESIDENCY IS QUOTED AS (model, KV dtype, context).  Every mem_runtime
REM   call below fixes KV dtype bf16 and context 1024.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P079_stage0b_depth_memory --note "[1/6] crops - the dense depth curve, one call per preset"
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_eval.py --preset m100s2 --data ko-en --tokens 300M --models d6_dense --dump-crops runs/logs/p079_d06.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models d8_dense d8_dense_s2 d8_dense_s3 --dump-crops runs/logs/p079_d08.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_eval.py --preset m100s6 --data ko-en --tokens 300M --models d10_dense --dump-crops runs/logs/p079_d10.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_dense --dump-crops runs/logs/p079_d12.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 300M --models d16_dense --dump-crops runs/logs/p079_d16.json
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_eval.py --preset m100 --data ko-en --tokens 300M --models d20_dense --dump-crops runs/logs/p079_d20.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage0b_depth_memory --note "[2/6] crops - the tied references we are racing against"
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly_nc mC_cla2_ag4 mC_cla2_ag4_r20 mC_cla1_ag4_r20 --match-train-repeat --dump-crops runs/logs/p079_tied.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage0b_depth_memory --note "[3/6] join - the paired SE the depth curve never had"
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_join.py --crops runs/logs/p079_d06.json runs/logs/p079_d08.json runs/logs/p079_d10.json runs/logs/p079_d12.json runs/logs/p079_d16.json runs/logs/p079_d20.json --pairs d6_dense:d8_dense d8_dense:d10_dense d10_dense:d12_dense d12_dense:d16_dense d16_dense:d20_dense
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage0b_depth_memory --note "[4/6] join - dense against tied at the same budget"
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\paired_join.py --crops runs/logs/p079_d08.json runs/logs/p079_d12.json runs/logs/p079_tied.json --pairs d8_dense:mC_initonly_nc d8_dense:mC_cla2_ag4 d12_dense:mC_initonly_nc d12_dense:mC_cla2_ag4_r20 d8_dense:d8_dense_s2 d8_dense:d8_dense_s3
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage0b_depth_memory --note "[5/6] DEPLOYMENT residency - LUT plus int8 embedding plus latent release, KV bf16 at 1024"
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s4 --models d8_dense --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s8 --models d12_dense --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s12 --models d16_dense --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100 --models d20_dense --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage0b_depth_memory --note "[6/6] the tied side of the same table, same three-tuple"
python scripts\runlog.py --name P079_stage0b_depth_memory -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc mC_cla2_ag4 mC_cla2_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P079_stage0b_depth_memory --note "READ IN THIS ORDER" "1. step 5 first, the row for d12_dense. Tensor-sum resident plus kv_mb is" "   the whole question. The estimate to beat or break is 23.3 plus 9.0." "2. then the same for d8 and d16. d8 is estimated 18.5 plus 6.0 = 24.5 and" "   d16 is estimated 28.0 plus 12.0 = 40.0, exactly at the maximum target." "3. only then step 4. Quality without the memory column is not a result -" "   that was the mC_cla1_ag4_r20 trap." "4. step 3 gives the depth curve a paired SE for the first time. Read the" "   dense ruler 0.0021 next to it." "5. d8_dense against its own two extra seeds is a ruler check. If those" "   three do not sit inside 0.0021 of each other, the dense ruler is wrong" "   and everything above needs re-reading." "6. nothing here changes a preset or picks a deployment model. That is a" "   REVIEW call."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
