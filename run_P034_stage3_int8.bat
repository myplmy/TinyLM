@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P034_stage3_int8.bat  --  P034 STAGE 3 : store the ternary copy as int8
REM  Plan: test_plan\P034_...md   Prior: result 016 section 9 (stage 2)
REM =============================================================================
REM
REM THE QUESTION THIS ANSWERS (asked directly by the user, 2026-08-02)
REM   "Ternary plus MLP tying should shrink the weights on disk AND in memory.
REM    Why has neither come close to the theoretical packed size?"
REM
REM   The tying part IS realised: unique ternary params fall from 123.86M (dense)
REM   to 54.85M (g8), and resident memory tracks that exactly. What is NOT realised
REM   is the BIT WIDTH. Each ternary value (minus a, 0, plus a) is held in a 32-bit
REM   float. Theory says 1.375 to 1.71 bits. That single fact is the whole 20x gap.
REM
REM   Stage 3 stores the code as int8 (1 byte) plus a per-group fp32 alpha, so the
REM   ternary term drops to about one quarter. Stage 4 (packing) would take it the
REM   rest of the way, but needs a kernel that reads packed weights WITHOUT
REM   expanding to fp32 - that is R8 and it is not written.
REM
REM PREDICTED NUMBERS (mA_g4s34_k4, from parameter counts - falsifiable)
REM   stage 1  latent + fp32 copy      523.5 MB
REM   stage 2  latent released         278.2 MB   (measured, result 016 section 9)
REM   stage 3  int8 code + alpha        96.2 MB   ^<-- THIS RUN
REM   stage 4  packed 1.375bpw          43.5 MB   (not implemented)
REM   stage 4 + packed embedding        12.4 MB   = the storage theory number
REM   So stage 3 alone lands at about 7.8x the theory, NOT at it. Claiming
REM   otherwise would repeat the "11.7MB" mistake in a new costume.
REM
REM ***EXPECT THIS TO BE SLOWER.***
REM   int8 has to be expanded back to fp32 every forward. Results 014 section 10
REM   and 016 section 9 both showed we are COMPUTE bound, not memory bound, so
REM   trading memory for compute should cost tokens per second. Writing the
REM   expectation down first is the point: if it slows down, that is the predicted
REM   trade, not a failure. If it does NOT slow down, that is the surprise worth
REM   chasing.
REM
REM COST: inference only, minutes. No GPU time required. Writes nothing to runs.
REM =============================================================================

if not exist run100m.py goto BADROOT
set TL_NOPAUSE=1

echo =============================================================
echo [P034-3] int8 storage : how much of the theory gap does it close
echo =============================================================
python scripts\runlog.py --name P034-stage3 --note "[P034-3] int8 storage : how much of the theory gap does it close"

echo.
echo =============================================================
echo [1/3] MEMORY : stage 2 alone (baseline for this run)
echo =============================================================
python scripts\runlog.py --name P034-stage3 --note "[1/3] MEMORY : stage 2 alone (baseline for this run)"
python scripts\runlog.py --name P034-stage3 -- python scripts\mem_runtime.py --device cpu --max-new 32 --drop-latent
if errorlevel 1 echo [WARN] stage 2 baseline failed - continuing

echo.
echo =============================================================
echo [2/3] MEMORY : stage 2 + stage 3 (int8 code plus group alpha)
echo   The logit gate runs per model. int8 reconstruction is EXACT for a ternary
echo   value, so it must still read 0.000e+00. Anything else means the code or
echo   the alpha is wrong, and then the memory numbers describe a different model.
echo =============================================================
python scripts\runlog.py --name P034-stage3 --note "[2/3] MEMORY : stage 2 + stage 3 (int8 code plus group alpha)"
python scripts\runlog.py --name P034-stage3 -- python scripts\mem_runtime.py --device cpu --max-new 32 --drop-latent --int8-store
if errorlevel 1 echo [WARN] stage 3 measurement failed - continuing

echo.
echo =============================================================
echo [3/3] SPEED : the cost side of the trade
echo =============================================================
python scripts\runlog.py --name P034-stage3 --note "[3/3] SPEED : the cost side of the trade"
python scripts\runlog.py --name P034-stage3 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent
if errorlevel 1 echo [WARN] stage 2 speed failed - continuing
python scripts\runlog.py --name P034-stage3 -- python scripts\bench_infer.py --device cpu --threads 1 --max-new 128 --reps 3 --drop-latent --int8-store
if errorlevel 1 echo [WARN] stage 3 speed failed - continuing

python scripts\runlog.py --name P034-stage3 --note "=================================================================" "WHAT TO RECORD  (label all of it 'P034 stage 3')" "  1. per model: resident MB at stage 2 versus stage 2+3, and the ratio" "  2. the logit gate value per model - it must be exactly 0.000e+00" "  3. tok/s at stage 2 versus stage 2+3, single thread, cache on" "  4. how far the result still is from the storage theory number" "" "HOW TO READ IT" "  ternary term near one quarter, gate 0" "      -^> stage 3 works. Resident is then about 7.8x the theory, and the rest" "         is fp32 embedding plus the missing packed format (stage 4 / R8)." "  slower by some percent" "      -^> the PREDICTED trade. Record it; that number prices stage 4, which" "         removes the expansion instead of paying for it every forward." "  NOT slower" "      -^> unexpected. Check the expansion is actually happening before" "         celebrating - a silent fallback to the fp32 path looks like this." "" "LIMITS: batch 1 / Windows CPU timing noisy (median of 3) / int8 is IRREVERSIBLE" "  in a process, training cannot resume after it / storage MB does not move here." "================================================================="
echo done.
pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
