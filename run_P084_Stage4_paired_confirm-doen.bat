@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P084_Stage4_paired_confirm.bat -- deterministic full-val confirmation
REM ==========================================================================
REM
REM   WHY THIS EXISTS
REM     Stage2 measured -0.0075 on the TRAINING LOG val, which is a random crop
REM     sample. The ruler (0.0018 recursion / 0.0021 dense) is defined on the
REM     deterministic full-val that paired_eval computes. The exchange rate came
REM     out 0.00465 nats per MiB against a pre-registered threshold of 0.00427.
REM     That is 1.09x. A ten percent move in delta flips the verdict, so the
REM     training-log number cannot decide this.
REM
REM   THREE PAIRS, ONE PRESET FAMILY
REM     all four checkpoints are m100s8, so one paired_eval call handles them.
REM       d12_cla2_r20        control, 3.6054 on full-val
REM       d12_cla2e_r20       P084 Stage2   -- no-cla-edges
REM       d12_cla2_r20_lrm    P086 Stage2   -- mlp-lrm
REM       d12_cla2_r20_s2     second seed of the control, gives the noise floor
REM
REM   MATCH THE TRAINING FUNCTION
REM     every checkpoint here was trained with --train-repeat 2.0. Evaluating
REM     without --match-train-repeat scores a function that was never trained
REM     (trap 39). The flag is on.
REM
REM   READING IT
REM     1. control vs cla2e. Divide by 1.61 MiB and compare with 0.00427.
REM     2. control vs lrm. The ruler is 0.0018. Log val said -0.0005.
REM     3. control vs s2 is the noise floor for this exact condition.
REM        If pair 2 is not clearly larger than pair 3, P086 stays closed.
REM
REM   COST: no training. GPU inference only, about 0.3h.
REM   PLAN: test_plan/P084_prelude-coda (Korean filename) Stage4
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P084_stage4_paired_confirm --note "[1/1] paired_eval - control vs cla2e vs lrm vs seed2"
python scripts\runlog.py --name P084_stage4_paired_confirm -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_cla2e_r20 d12_cla2_r20_lrm d12_cla2_r20_s2 --match-train-repeat
if errorlevel 1 echo [WARN] paired_eval failed - continuing

echo.
python scripts\runlog.py --name P084_stage4_paired_confirm --note "=================================================================" "READ IN THIS ORDER" "1. cla2e minus control, divided by 1.61 MiB, against 0.00427 nats/MiB." "   above it means adopt candidate, below it means bad exchange rate." "2. lrm minus control against the recursion ruler 0.0018." "3. s2 minus control is the noise floor. pair 2 must beat it to count." "4. the tool prints which ruler it used. do not apply one by hand." "================================================================="

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
