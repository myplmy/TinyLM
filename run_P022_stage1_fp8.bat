@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P022_stage1_fp8.bat  --  P022 STAGE 1 : FP8 end-to-end training
REM  Plan: test_plan\P022_...md   Gate: result 010 (stage 0, PASSED)
REM =============================================================================
REM
REM UNBLOCKED 2026-08-06. Stage 1 was held for two preconditions and both are met:
REM   sigma measured  -^> result 012, sigma = 0.012, resolution 0.024
REM   REVIEW1 settled -^> result 024 recommends m100R1c as the default
REM
REM ***SET YOUR EXPECTATION BEFORE READING THE NUMBER.***
REM   Result 010 measured pure GEMM at 1.63 to 2.08x. It ALSO measured that GEMM
REM   is only about 50 percent of a step. So end-to-end should be around -15
REM   percent, with -23 percent as the ceiling. Quoting "2x" here would be the
REM   same class of error as the "2.64x reduction" that result 016 had to retract.
REM
REM   A -15 percent wall clock gain on a 4 hour run is 36 minutes. That is real,
REM   but it is not an architecture result and it must not cost quality.
REM
REM WHAT DECIDES IT
REM   quality: final val must stay within the resolution (0.024) of the control.
REM            Read 'final', never 'best' (result 015 flipped a sign that way).
REM   speed:   steady-state ms/step, NOT the printed running average. The log
REM            prints a cumulative mean that includes the compile step.
REM            Convert with (mean x N - step0) / (N - 1).
REM   safety:  grad_max from the json, not the printed 10-step sample.
REM            FP8 has a much narrower dynamic range - if it diverges, it shows here.
REM
REM CONDITIONS - identical to the control except the precision flag
REM   preset m100R1c / 300M tokens / pool 600M exact / 2289 steps / mb8 accum16
REM   seq 1024 / lr 1e-3 / sched wsd / anneal-end 0.80 / seed 1337 / KD k4 + init-from
REM   The control is mC_wsd from result 024 (final 3.6442). Same everything.
REM
REM COST: about 3.5 to 4 GPU hours for the one new run. The control already exists.
REM ERRORLEVEL POLICY: single run, so a failure stops the batch.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P022-1] FP8 end-to-end : does the GEMM gain survive the full step
echo =============================================================
python scripts\runlog.py --name P022-stage1 --note "[P022-1] FP8 end-to-end : does the GEMM gain survive the full step"

echo.
echo [guard] is an fp8 training flag wired into the CLI
python scripts\runlog.py --name P022-stage1 --note "[guard] is an fp8 training flag wired into the CLI"
python -c "import sys; sys.exit(0 if '--fp8' in open('tinylm/cli.py',encoding='utf-8').read() else 7)"
if errorlevel 1 goto NOTIMPL

echo.
echo =============================================================
echo [1/2] FP8 run
echo =============================================================
python scripts\runlog.py --name P022-stage1 --note "[1/2] FP8 run"
python scripts\runlog.py --name P022-stage1 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --kd --kd-every 4 --init-from --fp8 --tag mC_fp8
if errorlevel 1 goto RUNBAD

echo.
echo =============================================================
echo [2/2] paired comparison against the existing control mC_wsd
echo =============================================================
python scripts\runlog.py --name P022-stage1 --note "[2/2] paired comparison against the existing control mC_wsd"
python scripts\runlog.py --name P022-stage1 -- python scripts\paired_eval.py --models mC_fp8 mC_wsd --preset m100R1c --seq 1024 --micro-bs 8
if errorlevel 1 echo [WARN] paired eval failed - the training log still stands

python scripts\runlog.py --name P022-stage1 --note "=================================================================" "WHAT TO RECORD  (label it 'P022 stage 1')" "  1. final val for mC_fp8 versus mC_wsd 3.6442 - use 'final', never 'best'" "  2. steady-state ms/step for both, converted off the cumulative mean" "  3. grad_max from the json for both" "  4. the paired mean difference and SE" "" "HOW TO READ IT" "  quality within 0.024 and speed near -15 percent" "      -^> ADOPT. Update the standard conditions and docs\methods\05." "  quality within 0.024 but speed gain much smaller than -15 percent" "      -^> the GEMM share assumption was wrong. Record the real share; do not" "         adopt for a few percent." "  quality outside 0.024, or grad_max much higher than the control" "      -^> FP8 dynamic range is biting. REJECT for training; the CPU deployment" "         path is unaffected either way." "" "LIMITS: one seed / sigma 0.012, resolution 0.024 / speed comparisons are only" "  valid on an otherwise idle GPU (result 015 saw +14 percent from co-running)." "=================================================================" 
echo done.
pause
exit /b 0

:NOTIMPL
echo.
echo =================================================================
echo [STOP] no --fp8 flag in the CLI. P022 stage 1 needs the training path
echo   implemented first (torch fp8 autocast or transformer-engine).
echo   Stage 0 (result 010) only measured a standalone GEMM microbenchmark.
echo   Nothing was executed.
echo =================================================================
pause
exit /b 3

:RUNBAD
echo.
echo =================================================================
echo [STOP] the FP8 run failed. Read the traceback above. If it is a range
echo   or overflow error that is a RESULT, not just a bug - record it.
echo =================================================================
pause
exit /b 1

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
