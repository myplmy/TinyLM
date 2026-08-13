@echo off
REM =============================================================================
REM  P055 stage 0b  -  RE-RUN after the audit tool was fixed (2026-08-13)
REM
REM  ***WHY THIS RUNS AGAIN.***  Result 042: only A1 was valid.
REM    A1 batchmean denominator   diff 0.00e+00        PASSED, and it is an
REM                                                    identity so it holds for
REM                                                    any distribution
REM    A2 T^2 x alpha ratio       0.000                ***INVALID***
REM    A4 bf16 log_softmax        0.000e+00            ***INVALID***
REM
REM  The synthetic logits were degenerate: teacher and student shared the same
REM  `base` tensor and differed only in the target logit, so the two
REM  distributions were nearly identical, KL was about 5e-5, and its gradient
REM  was ~0. That is a property of MY test data, not of the KD implementation.
REM
REM  FIXED
REM    - teacher and student logits are now INDEPENDENT random draws
REM    - the script prints the total-variation distance FIRST and refuses to let
REM      you read A2/A4 if it is below 0.05 (degenerate-data guard)
REM
REM  NAMING: this is stage "0b", not stage 0 again. A re-run under a changed
REM  tool is a DIFFERENT measurement and must be distinguishable in the log
REM  filename, the registry and the result document. See ai_dev_tool/03 s7.
REM
REM  !! H2 (implementation bug) is NOT yet ruled out. Only the denominator was
REM     confirmed. REVIEW2 must not decide about KD until this passes properly.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P055_stage0b_audit --note "=============================================================================" "P055 stage 0b  KD implementation audit (RE-RUN)   GPU 0" "A1 batchmean denominator / A2 T^2 x alpha effective weight" "A3 KD vs non-KD step scale / A4 bf16 log_softmax tail" "============================================================================="

python scripts\runlog.py --name P055_stage0b_audit -- python scripts\diag_kd_loss.py
if errorlevel 1 goto AUDITBAD

echo.
python scripts\runlog.py --name P055_stage0b_audit --note "=============================================================================" "Audit passed - H2 is ruled out. What remains is H1 and H3, and the" "kd_alpha sweep (stage 1) separates them." "!! If A2 printed a WARNING, that is the finding: the nominal alpha and the" "   effective gradient ratio disagree, which means alpha was never actually" "   explored. Stage 1 measures 0.5 / 0.3 / 0.1 / 0 directly." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:AUDITBAD
echo.
echo [STOP] the KD audit FAILED. That is the answer - H2 is confirmed.
echo        Do not let REVIEW2 judge KD until this is fixed, and re-read every
echo        past KD result afterwards. Result 038 would need re-measuring.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
