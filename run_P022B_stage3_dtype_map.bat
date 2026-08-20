@echo off
REM =============================================================================
REM  P022B stage 3  -  measure the training dtype map
REM                    (NO TRAINING, GPU diagnostic, a few minutes)
REM
REM  WHAT THE DOC CONCLUDED, AND WHAT IT COULD NOT
REM    docs/20260821_hakseup-dtype-jido (the dtype map doc) read the code and:
REM        GEMM and activations are already bf16. master, gradient and the Adam
REM        arithmetic must stay fp32. The only candidate left is _wq.
REM    But it could not say whether _wq is WORTH changing, because the traffic
REM    estimate (2-3 GB per step) and the cast count (up to 16x per tensor
REM    because of tying) were both arithmetic, not measurement.
REM
REM  THE FOUR ARMS
REM    M1  dtype and byte inventory        promotes the doc table from reading
REM                                        code to measuring tensors
REM    M2  F.linear call and cast count    THE one that answers "how many times"
REM    M3  refresh_quant alone, timed      upper bound on what D1 can buy
REM    M4  share of a full step            "so what percent is it"
REM
REM  GATES, fixed in advance
REM    M2 cast bytes per step under 1 GB      close the D1 axis
REM    M3 refresh_quant under 5 percent       close the D1 axis
REM    M3 at or above 20 percent              promote D3 (recompute interval)
REM    The tool prints these BEFORE the numbers. Do not move a gate afterwards.
REM
REM  TWO MODELS AND WHY
REM    mC_initonly   the no-KD baseline, g8, 20 layers - the standard case
REM    mC_d36_ag4    36 layers, attn-group 4 - MAXIMUM tying, so if the cast
REM                  count scales with reuse this is where it shows
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether to implement D1. It measures size, not worth - and the quality
REM    cost of a bf16 _wq is a separate training experiment.
REM    This runs WITHOUT torch.compile. Real training compiles, and compile may
REM    fuse the elementwise chain - so M3 is an UPPER bound. It only errs in
REM    that direction, which is the safe direction for closing an axis.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P022B_stage3_dtypemap --note "=============================================================================" "P022B stage 3   training dtype map   NO TRAINING   a few minutes" "The doc read the code. This measures it." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P022B_stage3_dtypemap --note "[1/2] mC_initonly - the no-KD baseline. g8, 20 layers."
python scripts\runlog.py --name P022B_stage3_dtypemap -- python scripts\diag_dtype_map.py --tag mC_initonly --preset m100R1c --data ko-en --tokens 300M --iters 5
if errorlevel 1 echo [WARN] initonly pass failed - continuing

echo.
python scripts\runlog.py --name P022B_stage3_dtypemap --note "[2/2] mC_d36_ag4 - maximum tying. If cast count scales with reuse it shows here."
python scripts\runlog.py --name P022B_stage3_dtypemap -- python scripts\diag_dtype_map.py --tag mC_d36_ag4 --preset m100R1c --data ko-en --tokens 300M --iters 5
if errorlevel 1 echo [WARN] d36_ag4 pass failed - continuing

echo.
echo.
python scripts\runlog.py --name P022B_stage3_dtypemap --note "=============================================================================" "READ IN THIS ORDER" "1. M1 _wq line. If it says (none) the model was frozen and M2/M3 are void." "2. M2 average reuse. For g8 with 16 middle layers expect about 8 for the" "   shared MLP tensors. A reuse of 1 means autocast IS caching and the doc" "   estimate was wrong in our favour." "3. M2 converted cast bytes per step against the 1 GB gate." "4. M3 percent against the 5 and 20 percent gates." "5. compare the two models. If mC_d36_ag4 is much worse, tying is paying a" "   hidden cast cost we have never counted." "REMINDER  no compile here. M3 is an UPPER bound." "REMINDER  M2 measures BANDWIDTH, M3 measures TIME. If only one gate fails," "          do not close the axis - they are different quantities." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
