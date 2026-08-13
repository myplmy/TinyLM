@echo off
REM =============================================================================
REM  P055 stage 0  -  audit the KD implementation.   GPU 0, minutes.
REM
REM  ***RUN THIS BEFORE REVIEW2 DECIDES ANYTHING ABOUT KD.***
REM
REM  We know KD is harmful at 300M (result 038: +0.0208 and +0.0219 across two
REM  seeds, 12 to 13 times the noise of that condition). We do NOT know why, and
REM  the three hypotheses have opposite prescriptions:
REM
REM    H1  the teacher is worse than the student   -^>  get a better teacher
REM    H2  the implementation is wrong             -^>  ***fix it and KD revives***
REM    H3  the method does not fit this budget     -^>  drop KD
REM
REM  If REVIEW2 drops KD while H2 is true, we threw away a method because of a
REM  bug. This script costs zero GPU and rules H2 in or out.
REM
REM  Prior: H2 is unlikely - result 006 measured -0.110 (a real gain) at 100M
REM  with the same code. We audit anyway because it is nearly free and the
REM  downside is large. The likely finding is not a bug but an UNEXPLORED
REM  hyperparameter: T squared times alpha may not give the alpha we think.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P055_stage0_audit --note "=============================================================================" "P055 stage 0   KD implementation audit   GPU 0" "A1 batchmean denominator / A2 T^2 x alpha effective weight" "A3 KD vs non-KD step scale / A4 bf16 log_softmax tail" "============================================================================="

python scripts\runlog.py --name P055_stage0_audit -- python scripts\diag_kd_loss.py
if errorlevel 1 goto AUDITBAD

echo.
python scripts\runlog.py --name P055_stage0_audit --note "=============================================================================" "Audit passed - H2 is ruled out. What remains is H1 and H3, and the" "kd_alpha sweep (stage 1) separates them." "!! If A2 printed a WARNING, that is the finding: the nominal alpha and the" "   effective gradient ratio disagree, which means alpha was never actually" "   explored. Stage 1 measures 0.5 / 0.3 / 0.1 / 0 directly." "============================================================================="
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
