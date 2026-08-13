@echo off
REM =============================================================================
REM  P054 stage 2  -  is the 0.017 gap noise, or a reproducibility problem?
REM  GPU 0, minutes. No training.
REM
REM  WHAT HAPPENED
REM    dense_best.pt was deleted by accident, so the parent was regenerated with
REM    --tag denseb under the ORIGINAL conditions (300M pool, cosine, seed 1337).
REM    Result 040: denseb final 3.8070 / best 3.7659
REM                dense  final 3.8241 / best 3.7797
REM    Same seed, same command string, 0.017 apart.
REM
REM  WHY THIS MATTERS MORE THAN THE CHECKPOINT
REM    dense-with-no-teacher sigma is 0.0109 (result 009 section P012B), so 0.017
REM    is the same order of magnitude and nondeterminism explains it. But
REM    "can be explained" is not "was explained". If the cause is the driver, the
REM    torch version, or the data cache, then the same command makes a different
REM    model - and every past judgement in this repo rests on that not being true.
REM
REM  paired_eval removes eval sampling noise by scoring both checkpoints on the
REM  SAME crops, so what is left is real training difference.
REM
REM  VERDICT
REM    delta ^<  0.011  nondeterminism. normal. nothing to do.
REM    0.011 to 0.024  borderline. check the cache and the version banner.
REM    delta ^>  0.024  ***escalate to a reproducibility investigation.***
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P054_stage2 --note "=============================================================================" "P054 stage 2   reproducibility check   GPU 0" "dense vs denseb - same seed, same command, 0.017 apart" "============================================================================="

python scripts\runlog.py --name P054_stage2 --note "[1/2] paired_eval - deterministic full-val on identical crops"
python scripts\runlog.py --name P054_stage2 -- python scripts\paired_eval.py --preset m100 --data ko-en --tokens 300M --models dense denseb
if errorlevel 1 echo [WARN] paired_eval returned an error - continuing to the cache diagnosis

python scripts\runlog.py --name P054_stage2 --note "[2/2] data cache diagnosis - did the pool change since 2026-07-23?"
python scripts\runlog.py --name P054_stage2 -- python scripts\diag_cache.py --data ko-en --tokens 300M
if errorlevel 1 echo [WARN] diag_cache returned an error - continuing

echo.
python scripts\runlog.py --name P054_stage2 --note "=============================================================================" "Read, in this order:" "1. paired mean delta, SE and t between dense and denseb" "2. compare it against 0.011 (dense sigma) and 0.024 (resolution)" "3. the cache document counts and language mix - same as the registry?" "VERDICT" "  under 0.011   nondeterminism, normal. denseb_best may stand in for" "                dense_best, but record in the registry that it came from" "                a different run." "  over 0.024    ***do not install denseb anywhere.*** Open a reproducibility" "                investigation first - this would mean the same command" "                produces a different model, and that undermines every" "                past comparison in this repo." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
