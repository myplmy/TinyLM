@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P022B_stage0_fp8_probe.bat -- [P022B] stage 0. Can FP8 (E4M3) hold our
REM                                    ternary alpha, and what does the GPU support?
REM  Plan: test_plan\P022B / Report: docs\20260807_DeepSeekV3-FP8 ... analysis
REM =============================================================================
REM
REM ***MINUTES. NO TRAINING. NOTHING IS WRITTEN TO runs\.***
REM   Part A alone takes seconds and needs no checkpoint.
REM
REM WHY - DeepSeek-V3 section 3.3 does NOT train in FP8
REM   Only the three Linear GEMMs (Fprop, Dgrad, Wgrad) are FP8. Embedding,
REM   output head, gating, normalisation, attention, master weights, gradients
REM   and optimizer state all stay in BF16 or FP32. Accuracy is held by
REM   FINE-GRAINED SCALING: 1x128 tiles for activations, 128x128 blocks for
REM   weights, plus FP32 accumulation promotion every 128 elements.
REM
REM ***WHY WE MIGHT BE BETTER PLACED THAN THE PAPER***
REM   After annealing our weights are  wq = sign x alpha[o, g(i)]  with
REM   sign in {-1, 0, +1} and g = micro_group = 128. Divide by alpha and the
REM   values are EXACTLY -1, 0, +1. ***E4M3 represents those three exactly.***
REM   So our weight-side FP8 error is ZERO, provided the scale granularity
REM   matches our alpha granularity. The paper worked hard for a coarser
REM   version of what we already have.
REM
REM ***AND WHY THAT IS ALSO THE WALL***
REM   Technical report section 3.3.2, verbatim: per-group scaling factors along
REM   the inner dimension of GEMM 'is not directly supported in the standard
REM   FP8 GEMM'. DeepSeek wrote a CUTLASS kernel (DeepGEMM). Our alpha IS an
REM   inner-dimension group scale. ***This is the same wall as P014B U2***
REM   (bitnet.cpp keeps one scale per tensor). Two different axes, same wall.
REM
REM ***PREDICTIONS - WRITTEN BEFORE THE RUN (plan P022B section 3)***
REM   P1 [B] g128 row relative error is EXACTLY 0.00000. If not, the TOOL is
REM      wrong and no other row may be read. This is the self-check.
REM   P2 per-row plus E4M3 is WORSE than per-row alpha re-estimation alone
REM      (result 028 measured +0.0050 to +0.0063 bpb for that).
REM   P3 per-tensor is unusable. Result 028 already measured +0.0465 to +0.0862.
REM   P4 activations hurt more than weights at the same granularity.
REM   P5 blockwise _scaled_mm FAILS on sm_89. rowwise is the open question.
REM   P6 the overall verdict stays 'do not implement now'.
REM
REM HOW THIS DIFFERS FROM RESULT 028
REM   Result 028 re-estimated alpha at coarser granularity - a DIFFERENT error
REM   term. Here alpha is kept and the PRODUCT is rounded into E4M3.
REM   ***Do not subtract the two tables from each other.***
REM
REM ERRORLEVEL POLICY: part A is the prerequisite for reading parts B to D, but
REM   it is also useful alone, so a failure warns and continues.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist datasets\squad\train-v2.0.json goto NOSQUAD

echo =============================================================
echo [P022B-0] FP8 E4M3 numerical gate  (minutes, no training)
echo =============================================================
python scripts\runlog.py --name P022B_stage0 --note "[P022B stage 0] FP8 E4M3 numerical gate. No training. Nothing written to runs."

echo.
echo =============================================================
echo [1/2] part A only - what scale granularity does _scaled_mm accept here
echo =============================================================
python scripts\runlog.py --name P022B_stage0 --note "[1/2] part A : _scaled_mm capability probe (seconds, no checkpoint needed)"
python scripts\runlog.py --name P022B_stage0 -- python scripts\diag_fp8_precision.py --probe-only
if errorlevel 1 echo [WARN] capability probe failed - continuing, parts B to D do not need it

if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL

echo.
echo =============================================================
echo [2/2] parts B to D - E4M3 round trip on real checkpoints
echo =============================================================
python scripts\runlog.py --name P022B_stage0 --note "[2/2] parts B to D : weight / activation / combined E4M3 round trip, common-source bpb"
python scripts\runlog.py --name P022B_stage0 -- python scripts\diag_fp8_precision.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_g16 --max-docs 4000
if errorlevel 1 echo [WARN] round trip failed

python scripts\runlog.py --name P022B_stage0 --note "=================================================================" "WHAT TO RECORD" "  0. ***[B] g128 relative error. It must be 0.00000.*** If it is not, the" "     tool is wrong and NOTHING else in the log may be quoted." "  1. table [A] - which recipes said OK and which said FAIL, verbatim." "  2. table [B] - delta bpb per weight granularity." "  3. table [C] - delta bpb per activation granularity." "  4. table [D] - the combined table. ***The verdict comes from this one.***" "" "HOW TO READ IT (gate G0)" "  [D] best combination delta bpb under 0.008" "      -^> FP8 numerical gate PASSED. stage 1 becomes worth costing out." "  0.008 to 0.02" "      -^> post-hoc round trip is not enough; QAT retraining would be needed." "         Cost rises sharply. Record and stop." "  above 0.02" "      -^> ***close it here.*** It only works with a custom kernel, and that is" "         the same work P014B was dropped for." "" "  Read [A] together with [B]: if blockwise FAILED, the g128 row of [B] is an" "  UNREACHABLE best case and the reachable number is the per-row row." "" "LIMITS: no retraining, so QAT would do better. The real GEMM accumulation" "  error is invisible to this method, so reality could be worse." "  ***Uncertainty runs both ways - say so in the result document.***" "  bpb is English SQuAD text only. Korean behaviour is not measured." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:NOCTRL
echo.
echo [STOP] runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt is missing. Part A above still ran.
if not defined TL_NOPAUSE pause
exit /b 5

:NOSQUAD
echo.
echo [STOP] datasets\squad\train-v2.0.json is missing (common-source bpb needs it).
if not defined TL_NOPAUSE pause
exit /b 7

:BADROOT
echo.
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
