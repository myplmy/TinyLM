@echo off
REM ===== LOGGING (added 2026-07-31) =====
REM   Every python command below is run through scripts\runlog.py, which prints to the
REM   console in real time AND appends to test_result\log_YYYYMMDD_NAME.txt line by line,
REM   flushing and fsync-ing as it goes. If this batch dies halfway, or the machine loses
REM   power, everything up to the last couple of seconds is already on disk.
REM   Losing the log of a long run costs the whole run, so this is not optional.
REM   Exit codes pass through unchanged, so every `if errorlevel` below still works.

REM ===== P030 stage 2B : CPU inference measurement - the FIRST valid one =====
REM   Plan: test_plan\P030 (stage 2B)   History: test_result\014
REM
REM ***** WHY "2B" AND NOT "2 RERUN" *****
REM   Three attempts share the name "stage 2" and that has caused real confusion.
REM   From now on they are named separately:
REM     stage 2   (2026-07-31 early)  INVALID - measured per-forward requantisation,
REM                                   not inference. See result 014 section 1-2.
REM     stage 2 retry (same day)      ABORTED - the [0/4] gate stopped it, 0 measurements.
REM                                   That gate turned out to be a FALSE ALARM (section 8-9).
REM     stage 2B  (this file)         The first attempt with (a) a correct KV cache PROVEN
REM                                   by logit equivalence, (b) freeze_quant so the timer
REM                                   measures GEMM and not quantisation.
REM   Tag every number you record from this run as 2B. Do not merge it with the old tables.
REM
REM ***** WHAT CHANGED IN THE GATE (this was the actual bug in the old batch) *****
REM   The old [0/4] called probe_prompts.py --check-cache with NO --device, so it ran bf16
REM   on cuda and compared DECODED STRINGS. That is not the invariant P030 asked for, and it
REM   failed on near-tie-prone models while dense passed - a false alarm (result 014 s9).
REM   The gate now calls diag_kvcache.py in fp32 on cpu and compares LOGITS position by
REM   position with teacher forcing. Measured headroom: 1.1e-05 against a 1e-3 tolerance.
REM
REM ***** THE QUESTION THIS ANSWERS (unchanged from the plan) *****
REM   Q2 how many tokens per second on CPU - the project target, still never measured
REM   Q3 does 30.9MB to 14.7MB storage buy CPU speed
REM   Read Q3 together with result 016: storage is NOT working-set size. Resident memory is
REM   978 / 451.5 / 523.5 MB, so the L3-residency story does not hold today. Expect the
REM   speed ratio to track RESIDENT size (and unique parameter count), not storage MB.
REM
REM COST: CPU-heavy, tens of minutes. No training. Writes nothing to runs.
REM ERRORLEVEL POLICY: the gate is a hard stop. Everything after it only warns.

echo ============================================================
echo [P030-2B] CPU inference - first valid measurement
echo ============================================================

echo.
echo [env] CPU / cache info - L3 size is what the residency claim depends on
wmic cpu get Name,NumberOfCores,NumberOfLogicalProcessors,L2CacheSize,L3CacheSize /format:list
if errorlevel 1 echo [WARN] wmic failed - note your CPU model manually

echo.
echo ============================================================
echo [0/4] GATE : teacher-forced logit equivalence, fp32 on cpu
echo   This replaces the old greedy-string gate. Deterministic, no autoregressive
echo   amplification, and the error pattern localises a real bug if one appears.
echo ============================================================
python scripts\runlog.py --name P030-stage2B -- python scripts\diag_kvcache.py --models mA_g4s34_k4 mC_g8_k4 p6d --device cpu --tol 1e-3 --max-new 24
if errorlevel 1 goto CACHEBAD
echo   [OK] logit equivalence within 1e-3. Cache is correct. Speed numbers are meaningful.

echo.
echo ============================================================
echo [1/4] GPU baseline, cache on vs off  (the cache speedup multiple)
echo ============================================================
python scripts\runlog.py --name P030-stage2B -- python scripts\bench_infer.py --device cuda --max-new 128 --reps 3 --both-cache
if errorlevel 1 echo [WARN] GPU bench failed - continuing

echo.
echo ============================================================
echo [2/4] CPU single thread - the most realistic edge number
echo   THIS IS THE HEADLINE NUMBER of the whole project. Record it carefully.
echo ============================================================
python scripts\runlog.py --name P030-stage2B -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --both-cache
if errorlevel 1 echo [WARN] CPU 1-thread bench failed - continuing

echo.
echo ============================================================
echo [3/4] CPU thread sweep (cache on only - off is characterised above)
echo ============================================================
python scripts\runlog.py --name P030-stage2B -- python scripts\bench_infer.py --device cpu --threads 2 4 8 --max-new 128 --reps 3
if errorlevel 1 echo [WARN] CPU sweep failed - continuing

echo.
echo ============================================================
echo [4/4] eos stop, qualitative - does generation END instead of running on
echo ============================================================
python scripts\runlog.py --name P030-stage2B -- python scripts\probe_prompts.py --models mA_g4s34_k4 --temps 0.7
if errorlevel 1 echo [WARN] eos demo failed - continuing

echo.
echo ================================================================
echo WHAT TO RECORD  (label all of it "stage 2B")
echo   1. CPU model / cores / L3 from the wmic block
echo   2. the cache on-vs-off multiple, per device
echo   3. tok/s and TTFT per (device, threads, model), cache ON
echo   4. whether [4/4] output STOPS at a document end
echo.
echo HOW TO READ IT - and what result 016 already tells us to expect
echo   Storage MB is NOT the working set. Measured resident memory is
echo     p6d 978.0   mC_g8_k4 451.5   mA_g4s34_k4 523.5   MB
echo   so if speed tracks memory at all, it should track THAT order, which puts mC
echo   ahead of mA. If instead speed tracks storage MB (mA fastest), something other
echo   than memory is driving it and we have another measurement to distrust.
echo.
echo   speed ratio near the RESIDENT ratio -^> memory-to-speed transfer is real
echo   speed ratio near 1.0                -^> no transfer. Weights are dequantised to
echo       fp32 before the GEMM. That is a NEGATIVE RESULT, not a failure, and it is
echo       exactly what P034 stages 2-4 exist to fix.
echo.
echo   mA slower than mC is EXPECTED now: mA has 17 percent more unique ternary
echo   parameters (64.29M vs 54.85M). The old 26 percent deficit versus dense was the
echo   mask-rebuild artefact from result 014 and should be GONE after freeze_quant.
echo   If it is still there, the artefact was not the whole story - say so.
echo.
echo LIMITS: batch 1 single request / Windows CPU timing is noisy (median of 3) /
echo   storage MB is not resident MB (result 016) / do NOT compare these numbers to the
echo   invalid stage-2 table in result 014 section 1 except to quantify how wrong it was.
echo ================================================================
echo done.
pause
exit /b 0

:CACHEBAD
echo.
echo ================================================================
echo [STOP] fp32 logit equivalence FAILED. This one IS a real bug.
echo.
echo   Unlike the old greedy gate, this is deterministic - bf16 precision cannot explain
echo   it. Read the per-position deltas printed above:
echo     delta grows with position          RoPE absolute offset (transformer.forward)
echo     delta large only past the prefill  SDPA mask alignment (modules.Attention)
echo     delta only on tied models          CLA owner-keyed cache (kv_bank keys)
echo.
echo   Reference: this gate measured 1.1e-05 on 2026-07-31 (result 014 section 9). A
echo   failure means something regressed since then.
echo.
echo   Nothing was measured. No files were written.
echo ================================================================
pause
exit /b 1
