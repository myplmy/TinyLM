@echo off
REM ===== LOGGING (added 2026-07-31) =====
REM   Every python command below is run through scripts\runlog.py, which prints to the
REM   console in real time AND appends to test_result\log_YYYYMMDD_NAME.txt line by line,
REM   flushing and fsync-ing as it goes. If this batch dies halfway, or the machine loses
REM   power, everything up to the last couple of seconds is already on disk.
REM   Losing the log of a long run costs the whole run, so this is not optional.
REM   Exit codes pass through unchanged, so every `if errorlevel` below still works.

REM ===== relocated to scripts\batch on 2026-07-31 =====
REM   Root now holds only batches for experiments that have NOT run yet. This one is a
REM   REUSABLE tool or a completed run kept for re-verification, so it lives here.
REM   It works from EITHER location: launched from the repo root, or double-clicked here.
REM   No percent-expansion is used (this repo bans the percent sign in .bat files), so the
REM   working directory is fixed by looking for a marker file instead.
if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ===== P034 stage 1 : RESIDENT memory, measured - because we never have =====
REM   Plan: test_plan\P034
REM
REM THE PROBLEM IN ONE SENTENCE
REM   Every "11.7MB / 2.64x" number in this repo is what mem_breakdown() computes for a
REM   PACKED format that does not exist yet. What actually sits in memory at inference is
REM   an fp32 latent weight PLUS an fp32 dequantised copy. Storage size is not working set.
REM
REM THE PREDICTION THIS TESTS (falsifiable, and we WANT to be wrong)
REM   Resident memory tracks UNIQUE PARAMETER COUNT, not bits-per-weight. If so:
REM     - tying (g up)          shrinks unique params -^> shrinks storage AND resident
REM     - ternary/sparse (bpw down) shrinks storage ONLY -^> resident unchanged
REM   Therefore mA (11.7MB stored, g4, 64.3M ternary params) should be RESIDENT-LARGER
REM   than mC (14.9MB stored, g8, 54.9M). Storage order and resident order INVERT.
REM   If the script reports that inversion, the prediction held and the headline
REM   "2.64x reduction" is a STORAGE claim only. If it does not invert, better news -
REM   write down why, because it would mean something else dominates.
REM
REM WHY TWO MEASUREMENT METHODS
REM   RSS      - what the OS sees. PyTorch does not return freed memory to the OS
REM              promptly, so RSS can OVERSTATE.
REM   tensor sum - bytes of tensors we deliberately hold. Ignores the allocator, but also
REM              ignores activations and temporaries, so it can UNDERSTATE.
REM   The truth is between them. Never quote just one.
REM
REM PREREQUISITE: psutil. If missing: pip install psutil
REM   (a /proc fallback exists but does not work on Windows)
REM
REM COST: inference only, a few minutes. No training. Writes nothing to runs\.
REM ERRORLEVEL POLICY: independent measurements, failures only warn.

echo ============================================================
echo [P034-1] resident memory : storage MB is not working-set MB
python scripts\runlog.py --name P034-memory --note "[P034-1] resident memory : storage MB is not working-set MB"
echo ============================================================

echo.
echo [pre] psutil availability
python scripts\runlog.py --name P034-memory --note "[pre] psutil availability"
python -c "import psutil; print('  psutil OK', psutil.__version__)"
if errorlevel 1 echo [WARN] psutil missing - RSS will be nan. Run: pip install psutil

echo.
echo ============================================================
echo [1/2] CPU - this is the deployment target, so this is the number that counts
python scripts\runlog.py --name P034-memory --note "[1/2] CPU - this is the deployment target, so this is the number that counts"
echo ============================================================
python scripts\runlog.py --name P034-memory -- python scripts\mem_runtime.py --device cpu --max-new 32
if errorlevel 1 echo [WARN] CPU memory measurement failed - continuing

echo.
echo ============================================================
echo [2/2] GPU - cross-check. CUDA reports an exact allocator peak, so it validates
python scripts\runlog.py --name P034-memory --note "[2/2] GPU - cross-check. CUDA reports an exact allocator peak, so it validates"
echo   the tensor-sum method against a number we can trust.
echo ============================================================
python scripts\runlog.py --name P034-memory -- python scripts\mem_runtime.py --device cuda --max-new 32
if errorlevel 1 echo [WARN] GPU memory measurement failed - continuing

echo.
echo ================================================================
echo WHAT TO RECORD
echo   1. per model: storage MB, tensor-sum resident MB, RSS delta, latent vs dequant split
echo   2. the TRANSFER RATE line (how much of the storage reduction became resident)
echo   3. whether the storage order and the resident order INVERTED
echo.
echo HOW TO ACT ON IT
echo   transfer near 100 percent -^> our reporting was right. Close P034 early.
echo   transfer near 0, tying-only gain (expected) -^> the ternary/sparse gain is
echo       THEORETICAL so far. Then:
echo         a. report packed_mb AND runtime_mb everywhere, never one alone
echo         b. P034 stage 2 (drop the latent weight after freeze) is the cheapest
echo            real win - inference needs no backward pass, so latent is dead weight
echo         c. stage 3 (int8 storage) and stage 4 (5-bit packing) follow
echo   resident WORSE than storage predicts -^> an unexpected copy exists. Find it first.
echo.
echo   Note stage 2 alone should roughly HALVE resident memory. That is the largest
echo   single lever available today and it needs no custom kernel.
echo.
echo LIMITS: RSS includes the python/torch runtime (read the DELTA only) / tensor sum
echo   excludes activations and KV cache / this measures TODAY's implementation, which
echo   is exactly the baseline stages 2-4 have to beat.
echo ================================================================
echo done.
pause

:BADROOT
echo.
echo ================================================================
echo [STOP] could not locate the repo root (run100m.py not found).
echo   Run this batch from the TinyLM working folder, or double-click it where it lives
echo   (scripts\batch). Nothing was executed.
echo ================================================================
pause
exit /b 9
