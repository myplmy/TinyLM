@echo off
REM P077 stage 1b  -  fp16 KV, and the fixed gate re-run.  About 0.2 hours.
REM
REM   WHY fp16 IS WORTH A LOOK.  bf16 and fp16 are BOTH two bytes, so they cost
REM   the same KV.  They differ in where those bytes go:
REM
REM     bf16 : 8 exponent bits,  8 mantissa bits  gives relative error 2^-8
REM     fp16 : 5 exponent bits, 11 mantissa bits  gives relative error 2^-11
REM
REM   fp16 is 8 times more precise at the same size.  Its cost is dynamic
REM   range, and our K and V go through RMSNorm before the cache, so the range
REM   argument is weak here.  If fp16 passes, it is a free precision upgrade
REM   at identical memory - and nobody has tried it.
REM
REM   ALSO RE-RUNS THE bf16 GATE.  Stage 1's bf16 arm exited 1 and printed
REM   "exceeding tolerance in fp32 means a REAL BUG", which is fp32 text on a
REM   bf16 run.  diag_kvcache now picks tolerance from the KV dtype (1e-3 /
REM   5e-2 / 5e-3, derived from mantissa bits) and judges on three conditions:
REM   deviation above zero (the flag reached the cache, trap 37), deviation
REM   below tolerance, and ZERO argmax changes.  This re-run is what puts a
REM   clean pass in the log.
REM
REM   THIS IS NOT A QUALITY MEASUREMENT.  Teacher-forced evaluation has no
REM   autoregressive feedback, so a wrong token never poisons what follows.
REM   The real cost needs generation-based evaluation and that is stage 2.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P077_stage1b_kv_fp16 --note "[1/5] fp32 baseline - the number the other two are read against"
python scripts\runlog.py --name P077_stage1b_kv_fp16 -- python scripts\diag_kvcache.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 mC_cla2_ag4_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1b_kv_fp16 --note "[2/5] bf16 through the FIXED gate - a clean pass this time"
python scripts\runlog.py --name P077_stage1b_kv_fp16 -- python scripts\diag_kvcache.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 mC_cla2_ag4_r20 --kv-dtype bf16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1b_kv_fp16 --note "[3/5] fp16 - same two bytes, three more mantissa bits"
python scripts\runlog.py --name P077_stage1b_kv_fp16 -- python scripts\diag_kvcache.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 mC_cla2_ag4_r20 --kv-dtype fp16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1b_kv_fp16 --note "[4/5] the recursive arm too - it has the most KV to lose"
python scripts\runlog.py --name P077_stage1b_kv_fp16 -- python scripts\diag_kvcache.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20 --kv-dtype fp16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1b_kv_fp16 --note "[5/5] accounting - fp16 must give exactly the same MiB as bf16"
python scripts\runlog.py --name P077_stage1b_kv_fp16 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4 mC_cla2_ag4_r20 --drop-latent --lut --emb-quant int8 --kv-seq 1024 --kv-dtype fp16
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1b_kv_fp16 --note "READ IN THIS ORDER" "1. the verdict column, not the exit code. Four states now: pass, exceed," "   decision-change, and no-response. No-response means the flag never" "   reached the cache and everything downstream is fiction (trap 37)." "2. argmax mismatch must be 0. That is the contract a KV cache owes -" "   the magnitude is context, the decisions are the gate." "3. fp16 deviation against bf16 deviation. Expect roughly 8 times smaller." "   If it is not, the cast is not where we think it is." "4. step 5 kv_mb must equal the bf16 numbers EXACTLY. Both are two bytes." "   A difference there is an accounting bug, not a precision result." "5. none of this is the quality cost. Teacher-forced evaluation does not" "   use the cache the way generation does."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
