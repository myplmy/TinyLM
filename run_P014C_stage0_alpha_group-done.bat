@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P014C_stage0_alpha_group.bat -- P014C STAGE 0 : how much quality do we
REM        lose if alpha gets coarser
REM  Plan: test_plan\P014C_...md
REM =============================================================================
REM
REM PRECONDITION: scripts\diag_alpha_group.py IMPLEMENTED 2026-08-07. No training.
REM
REM WHY THIS DECIDES THE WHOLE KERNEL QUESTION
REM   Our CPU bottleneck is dequantisation: _wq_from_i8 materialises fp32 every
REM   forward, and result 014 section 11.4 measured that at 1.54 to 1.60 ms per
REM   unpack. The only way to remove it is a FUSED mixed-precision GEMM.
REM   But every fused op uses a COARSER scale convention than ours:
REM     g128 (ours)   about 428,000 alphas for mC
REM     per-row       O alphas, 768 to 2048 per layer  ^<- PyTorch has candidates
REM     per-tensor    ONE                              ^<- bitnet.cpp I2_S and TL
REM   So the question is not "is the kernel fast" but "can we live with coarse
REM   alpha". That is measurable WITHOUT TRAINING, in minutes.
REM
REM HOW IT WORKS - no retraining, no checkpoint writes
REM   Takes the deployed _wq (= sign x alpha_g), KEEPS THE SIGNS, and re-derives
REM   alpha at each granularity. Since sign*A - sign*alpha_g = sign(A - alpha_g),
REM   the L2-optimal estimate is A = mean(^|w^|) over nonzero positions. That is
REM   exactly what a converter would do.
REM   Then it measures real SQuAD common-text bpb with the changed weights.
REM
REM ***EXPECTATIONS - WRITE THEM DOWN FIRST.***
REM   g128 must show relative error EXACTLY 0.000000. That is the correctness
REM        check - it recovers the original alpha. If it does not, the tool is
REM        wrong and every other row is meaningless.
REM   g256      expected within 0.008 bpb of g128
REM   per-row   expected 0.008 to 0.05  ^<- ***THIS IS THE FORK***
REM   per-tensor expected above 0.05    ^<- this is the bitnet.cpp convention
REM
REM HOW TO ACT ON IT
REM   per-row under 0.008  -^> NO KERNEL NEEDED. Go to stage 1, check whether
REM                           PyTorch has a per-row fused int8 matmul. Cheapest
REM                           possible ending.
REM   per-row 0.008 to 0.05 -^> retraining might absorb it (stage 3). This table
REM                           is a PESSIMISTIC BOUND because we did not retrain.
REM   per-row above 0.05   -^> we build a g128 kernel (P014 option C), and this
REM                           table is the quantitative reason why.
REM
REM COST: a few minutes. Reads checkpoints only, writes nothing but the log.
REM DEPENDS ON NOTHING.
REM ERRORLEVEL POLICY: independent scans, failures warn and continue.
REM =============================================================================

if not exist run100m.py goto BADROOT
if not exist datasets\squad\train-v2.0.json goto NOSQUAD

echo =============================================================
echo [P014C-0] alpha granularity vs quality - decides the kernel question
echo =============================================================
python scripts\runlog.py --name P014C-stage0 --note "[P014C-0] alpha granularity vs quality - decides the kernel question"

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo =============================================================
echo [1/2] the three REVIEW1 candidates at 300M
echo =============================================================
python scripts\runlog.py --name P014C-stage0 --note "[1/2] the three REVIEW1 candidates at 300M"
python scripts\runlog.py --name P014C-stage0 -- python scripts\diag_alpha_group.py --models p6d mC_g8_k4 mA_g4s34_k4 --preset m100 --data ko-en --tokens 300M --max-docs 4000
if errorlevel 1 echo [WARN] m100 scan failed - continuing

echo.
echo =============================================================
echo [2/2] the current default mC_wsd (m100R1c)
echo =============================================================
python scripts\runlog.py --name P014C-stage0 --note "[2/2] the current default mC_wsd (m100R1c)"
python scripts\runlog.py --name P014C-stage0 -- python scripts\diag_alpha_group.py --models mC_wsd --preset m100R1c --data ko-en --tokens 300M --max-docs 4000
if errorlevel 1 echo [WARN] m100R1c scan failed - continuing

python scripts\runlog.py --name P014C-stage0 --note "=================================================================" "WHAT TO RECORD" "  1. ***the g128 row's relative error.*** It must be 0.000000. This is the" "     tool's own correctness check - it should recover the original alpha." "     If it is not zero, stop and report that instead of the other rows." "  2. the per-row Delta-bpb. That is the fork." "  3. the per-tensor Delta-bpb. That number IS 'how much worse we get if we" "     put this model into bitnet.cpp today'." "  4. whether the three models agree. mA has sparse34 so its alpha structure" "     differs - if it behaves very differently, say so." "" "HOW TO READ IT" "  per-row under 0.008 bpb" "      -^> no custom kernel needed. Stage 1 next: does PyTorch have a per-row" "         fused int8 matmul. One command, one minute." "  per-row 0.008 to 0.05" "      -^> borderline. Retraining may absorb it - this table is a PESSIMISTIC" "         bound since we did not retrain. Stage 3 decides." "  per-row above 0.05" "      -^> build our own g128 kernel. This table becomes the quantitative" "         justification for not reusing external implementations." "" "LIMITS: ENGLISH ONLY (SQuAD) / no retraining, so pessimistic / weight relative" "  error is a reference column, NOT monotone with quality / one seed per model." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:BADKWARGS
echo.
echo =================================================================
echo [STOP] cli.py passes a keyword its target function does not accept.
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 6

:NOSQUAD
echo.
echo =================================================================
echo [STOP] datasets\squad\train-v2.0.json not found.
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 3

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
