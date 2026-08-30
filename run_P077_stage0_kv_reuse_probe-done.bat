@echo off
REM =============================================================================
REM  P077 stage 0  -  what does --repeat-kv-reuse cost.  about 0.2 hours. NO TRAINING.
REM
REM  WHY  (result 016 s24, result 047 s14.4, docs/20260830 recursion-KV report)
REM    KV accounting landed and it killed the recursion line. mC_cla1_ag4_r20nc
REM    has the smallest weights we have ever built, 16.9 MiB, and it is
REM    indistinguishable from the standard control on quality. But its KV cache
REM    is 36 entries and 54.0 MiB at seq 1024, so the deployment total is 70.9
REM    against a 36 MiB budget. Twice over.
REM
REM    The fix already exists in the code. --repeat-kv-reuse folds the key from
REM    (owner, pass) down to (owner, 0), which takes 36 entries to 20. It is an
REM    INFERENCE ONLY flag, so no retraining. paired_eval already accepts it.
REM    We have never once measured what it costs.
REM
REM  INDEPENDENT VARIABLE
REM    --repeat-kv-reuse on the same checkpoint. Nothing else moves.
REM
REM  PREDICTIONS
REM    K1  entries 36 -^> 20, kv_mb 54.0 -^> 30.0. If they do NOT move, that is a
REM        defect and not a result - the flag is recorded but the path is dead
REM        (trap 37). Look at the code before writing anything down.
REM    K2  quality cost between +0.005 and +0.02. Confidence is LOW. The only
REM        related number is --reuse-attn-on-dup, which lost the whole recursion
REM        gain, but that one reused the attention OUTPUT so Q was stale too.
REM        Here Q is recomputed. Do not carry 041 over to this.
REM    K3  slightly faster - half the K/V projections disappear.
REM
REM  RULER
REM    Recursion 2 sigma = 0.0006, MEASURED (result 039 s10). The line that
REM    used to stand here said there was no recursion ruler and to write
REM    "borrowed" - that is now false. run_P052_stage3_recursion_seed ran.
REM    Tied is also 0.0006 on three seeds (039 s9), not the old 0.0010.
REM
REM  DECISION
REM    cost ^< 0.0006            adopt. The recursion line gets -24.0 MiB free.
REM    0.0006 to 0.0107         partial - still a net gain against the -0.0107
REM                             recursion benefit. Note 058 s14 measured -0.0172
REM                             on the cla2 body, so the margin is body-dependent.
REM    ^> 0.0107                reject. Same fate as --reuse-attn-on-dup.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P077_stage0_kv_reuse_probe --note "=============================================================================" "P077 stage 0   what does --repeat-kv-reuse cost" "The flag has existed for weeks. It has never been measured." "No training. Inference path only." "=============================================================================="

echo.
python scripts\runlog.py --name P077_stage0_kv_reuse_probe --note "[1/4] baseline - the trained schedule, 36 entries"
python scripts\runlog.py --name P077_stage0_kv_reuse_probe -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20nc mC_cla1_ag4_r20 mC_cla2_ag4_r20 mC_initonly_nc --match-train-repeat
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P077_stage0_kv_reuse_probe --note "[2/4] the same checkpoints with KV reuse on. This is the whole experiment."
python scripts\runlog.py --name P077_stage0_kv_reuse_probe -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20nc mC_cla1_ag4_r20 mC_cla2_ag4_r20 mC_initonly_nc --match-train-repeat --repeat-kv-reuse
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P077_stage0_kv_reuse_probe --note "[3/4] K1 - do the entries actually drop. Trap 37 gate."
python scripts\runlog.py --name P077_stage0_kv_reuse_probe -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla1_ag4_r20nc mC_cla2_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 3a failed - continuing
python scripts\runlog.py --name P077_stage0_kv_reuse_probe -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla1_ag4_r20nc mC_cla2_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --repeat-kv-reuse
if errorlevel 1 echo [WARN] step 3b failed - continuing

echo.
python scripts\runlog.py --name P077_stage0_kv_reuse_probe --note "[4/4] the KV cache correctness gate. Reuse changes the function - see what it does here."
python scripts\runlog.py --name P077_stage0_kv_reuse_probe -- python scripts\diag_kvcache.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20nc
if errorlevel 1 echo [WARN] step 4 failed - continuing

echo.
python scripts\runlog.py --name P077_stage0_kv_reuse_probe --note "=============================================================================" "READ IN THIS ORDER" "1. step 3 FIRST. If kv_entries does not go 36 to 20, stop. The flag is" "   recorded but the code path is dead, and step 2 measured nothing." "2. step 2 against step 1, same model, same crops. That delta is the cost." "3. compare it to the recursion benefit of -0.0107. Smaller means net gain." "4. the recursion ruler is 0.0006 and it is MEASURED (039 s10). Do not" "   write BORROWED - that instruction was withdrawn on 2026-08-30." "5. if the cost is under the ruler, mC_cla1_ag4_r20 drops from 70.9 to 46.9" "   MiB, and cla2 plus reuse would be 31.8 which fits the four-thread budget." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
