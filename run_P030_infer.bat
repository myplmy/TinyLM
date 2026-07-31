@echo off
REM ===== P030 stage 2 RE-RUN : inference speed after the stage-1 fixes =====
REM   Plan: test_plan\P030   Previous (INVALID) result: test_result\014
REM
REM ***** WHY THIS IS A RE-RUN, NOT A NEW MEASUREMENT *****
REM   Result 014 measured something that was not inference. Two defects, both now fixed:
REM     (1) transformer.forward() called refresh_quant() on EVERY forward. Correct during
REM         training (latent weights change each step) but pure waste at inference.
REM         It was about 79 percent of CPU time, and the sparse34 path (argmin + scatter)
REM         was the most expensive - which is why the 11.7MB model looked SLOWER than dense.
REM         Fix: model.freeze_quant() in load_model, skipped in forward while frozen.
REM     (2) No KV cache - every token recomputed the whole sequence, O(T squared).
REM         Fix: past_kv through Attention, cache keyed by the CLA OWNER layer.
REM   Expect the model ranking to CHANGE. Do not compare these numbers to 014's table
REM   except to quantify how wrong 014 was.
REM
REM ***** STEP 0 IS NOT OPTIONAL *****
REM   A KV cache that is subtly wrong still produces fluent text and still looks fast.
REM   The two classic bugs are silent:
REM     - RoPE sliced as [:T] instead of [past_len : past_len+T]
REM     - SDPA is_causal=True when q_len is not kv_len (mask aligns TOP-LEFT, wrong rows)
REM   Greedy output with and without the cache must be IDENTICAL. If step 0 fails,
REM   everything below is meaningless - stop and fix the cache.
REM
REM COST: CPU-heavy, tens of minutes. No training. Writes nothing to runs\.
REM ERRORLEVEL POLICY: step 0 is a hard gate. The rest only warn.

echo ============================================================
echo [P030-2 RERUN] inference speed after stage-1 fixes
echo ============================================================

echo.
echo [env] CPU / cache info - the L3 size decides whether the weights reside
wmic cpu get Name,NumberOfCores,NumberOfLogicalProcessors,L2CacheSize,L3CacheSize /format:list
if errorlevel 1 echo [WARN] wmic failed - note your CPU model manually

echo.
echo ============================================================
echo [0/4] GATE : KV cache correctness (greedy, cache on vs off must match)
echo ============================================================
REM   Korean prompts cannot live in a .bat (ASCII rule), so the driver owns them.
python scripts\probe_prompts.py --check-cache
if errorlevel 1 goto CACHEBAD
echo   [OK] cache matches no-cache on every model and prompt.

echo.
echo ============================================================
echo [1/4] GPU baseline, cache on vs off  (the cache speedup multiple)
echo ============================================================
python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --both-cache
if errorlevel 1 echo [WARN] GPU bench failed - continuing

echo.
echo ============================================================
echo [2/4] CPU single thread - the most realistic edge number
echo   THIS IS THE HEADLINE NUMBER of the whole project. Record it carefully.
echo ============================================================
python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --both-cache
if errorlevel 1 echo [WARN] CPU 1-thread bench failed - continuing

echo.
echo ============================================================
echo [3/4] CPU thread sweep (cache on only - off is already characterised above)
echo ============================================================
python scripts\bench_infer.py --device cpu --threads 2 4 8 --max-new 128 --reps 3
if errorlevel 1 echo [WARN] CPU sweep failed - continuing

echo.
echo ============================================================
echo [4/4] eos stop, qualitative - does generation now END instead of running on?
echo   Result 013 saw an English document intrude into a Korean prompt. That was the
echo   missing eos check letting generation cross a document boundary.
echo ============================================================
python scripts\probe_prompts.py --models mA_g4s34_k4 --temps 0.7
if errorlevel 1 echo [WARN] eos demo failed - continuing

echo.
echo ================================================================
echo WHAT TO RECORD
echo   1. CPU model / cores / L3 (from the wmic block)
echo   2. the cache on-vs-off multiple, per device
echo   3. tok/s and TTFT per (device, threads, model), cache ON
echo   4. whether [4/4] outputs STOP at a document end (eos) or run to max_new
echo.
echo THE QUESTION THIS ANSWERS
echo   With the measurement artefact gone, does LESS MEMORY still mean FASTER CPU?
echo   speed ratio near the memory ratio -^> memory-to-speed transfer is real
echo   speed ratio near 1.0             -^> no transfer. Weights are dequantised to
echo       fp32 before the GEMM, so storage size is not working-set size. That is a
echo       NEGATIVE RESULT, not a failure - and it is exactly what P034 exists to measure.
echo.
echo   Watch specifically whether mA (sparse34) is still slower than dense. If it is,
echo   the cost is real and structural, not the mask-rebuild artefact from 014.
echo.
echo LIMITS: batch 1 single request / Windows CPU timing is noisy (median of 3) /
echo   storage MB is NOT resident MB - P034 stage 1 measures that separately.
echo ================================================================
echo done.
pause
exit /b 0

:CACHEBAD
echo.
echo ================================================================
echo [STOP] greedy output differs between the cache and no-cache paths.
echo.
echo   Nothing else ran. But DO NOT go straight to RoPE and the mask - that advice was
echo   in this file until 2026-07-31 and it was wrong. Here is what is already known
echo   (test_result\014 section 8):
echo.
echo     - RoPE slicing and the SDPA mask are SHARED by dense and tied. p6d passed 5 of 5,
echo       so neither can be the cause on its own.
echo     - This gate compares DECODED STRINGS, which is not the invariant P030 asked for.
echo       It runs bf16 on cuda and feeds 24 autoregressive steps, so ONE argmax flip at a
echo       near-tie rewrites the whole continuation. That is a plausible false alarm.
echo.
echo   Do this instead, in order:
echo     1. run_P030_cachecheck.bat   fp32 on cpu. Separates precision from a real bug.
echo     2. run_P030_cachegate.bat    teacher-forced logit equivalence. This is the proof.
echo     3. come back here only after 2 is green.
echo.
echo   Nothing was measured. No files were written.
echo ================================================================
pause
