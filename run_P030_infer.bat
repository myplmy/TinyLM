@echo off
REM ===== P030 : inference speed - CPU is the project target and we never measured it =====
REM   Plan: test_plan\P030
REM
REM WHY: everything measured so far is GPU TRAINING speed (results 007, P021B, 010).
REM   CLAUDE.md line 1 says the target is low-end CPU / edge. CPU inference: measured ZERO times.
REM   So we do not actually know what shrinking 30.9MB to 11.7MB buys us.
REM
REM ***** READ THIS BEFORE BELIEVING THE NUMBERS *****
REM   (a) sample() has NO KV CACHE - it recomputes the whole sequence every token.
REM       max_new=32 with a 10-token prompt is roughly 700 token-forwards instead of 32.
REM       Absolute tok/s here is PESSIMISTIC. Model-to-model comparison is still valid
REM       because all three models pay the same penalty.
REM   (b) ternary weights are DEQUANTISED to bf16/fp16 before the GEMM. So 11.7MB is the
REM       STORAGE size, not the working-set size. Expect the memory advantage to transfer
REM       only partially - possibly not at all. That negative result is the whole point:
REM       it is the evidence that a 5-bit packed CPU kernel (P030 stage 3) is needed.
REM
REM   THIS BATCH IS STAGE 2 OF P030. Stage 1 (implement the KV cache) is NOT done yet.
REM   Running stage 2 first is deliberate: it gives us the baseline numbers that stage 1
REM   and stage 3 have to beat, using only code that exists today.
REM
REM COST: CPU-heavy, a few minutes to tens of minutes depending on thread sweep.
REM   No training. Writes nothing to runs\.
REM
REM ERRORLEVEL POLICY: independent measurements, failures only warn.

echo ============================================================
echo [P030-2] inference speed : GPU vs CPU, three models
echo ============================================================

echo.
echo [env] CPU / cache info - record this, the L3 size decides whether 11.7MB resides
wmic cpu get Name,NumberOfCores,NumberOfLogicalProcessors,L2CacheSize,L3CacheSize /format:list
if errorlevel 1 echo [WARN] wmic failed - note your CPU model manually

echo.
echo === [1/3] GPU baseline (for the CPU/GPU ratio) ===
python scripts\bench_infer.py --device cuda --max-new 32 --reps 3
if errorlevel 1 echo [WARN] GPU bench failed - continuing

echo.
echo === [2/3] CPU, single thread - the most realistic edge number ===
python scripts\bench_infer.py --device cpu --threads 1 --max-new 32 --reps 3
if errorlevel 1 echo [WARN] CPU 1-thread bench failed - continuing

echo.
echo === [3/3] CPU thread sweep - how much does it scale? ===
python scripts\bench_infer.py --device cpu --threads 2 4 8 --max-new 32 --reps 3
if errorlevel 1 echo [WARN] CPU sweep failed - continuing

echo.
echo ================================================================
echo WHAT TO RECORD
echo   1. CPU model, core count, L3 size (from the wmic block above)
echo   2. tok/s and TTFT per (device, threads, model)
echo   3. the "speed ratio vs memory ratio" summary the script prints
echo.
echo HOW TO READ IT - the one question that matters
echo   speed ratio close to the memory ratio  -^> memory-to-speed transfer WORKS.
echo       The whole memory-optimisation thesis gets direct support.
echo   speed ratio close to 1.0               -^> NO transfer at this stage.
echo       Expected, because weights are dequantised before the GEMM. This is the
echo       evidence that a packed 5-bit CPU kernel is required to cash in the 1.25bpw.
echo       Record it as a NEGATIVE RESULT, not a failure.
echo.
echo   Also: if 1-thread CPU tok/s is under about 1, the model is not usable on edge as-is
echo   and the KV cache (stage 1) becomes the top priority, not an optimisation.
echo.
echo LIMITS: no KV cache yet (absolute values pessimistic, comparisons valid) /
echo   Windows CPU timing is noisy (median of 3, ignore 1-2 percent) /
echo   batch 1 single request only - server throughput is a different subject.
echo ================================================================
echo done.
pause
