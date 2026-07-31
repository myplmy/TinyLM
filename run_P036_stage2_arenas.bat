@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P036_stage2_arenas.bat  --  P036 STAGE 2 : Arenas on/off, same conditions
REM  Plan: test_plan\P036_...md    Roadmap: R5 (conditional on R4/stage 1B)
REM =============================================================================
REM
REM STAGE 0 IS DONE (2026-07-31). --arenas is implemented.
REM   Y = X*Ta + lambda_t*X*W                  (paper eq 7)
REM   dL/dX = (dL/dY)(Ta + lambda_t*W)^^T        (paper eq 8)
REM   The formula came from the paper BODY, recorded in result 016 section 8.6 -
REM   not from the abstract. That distinction matters here: result 016 section 7.5
REM   records how reading this same paper at abstract level produced three
REM   misreadings, one of which made us run 3:4 WITHOUT a required part of the method.
REM
REM   Our quantisation anneal is NOT this. refresh_quant computes
REM   wq + (1-a)*(w - wq).detach(), and the detach means latent W never enters the
REM   input-gradient path. Arenas exists precisely for that path, so it is a
REM   separate term, added undetached, with its own schedule (lambda_t -^> 0).
REM   lambda_t reaches 0 before training ends, so INFERENCE OVERHEAD IS ZERO.
REM
REM ***STILL GATED - ON EVIDENCE, NOT ON CODE.***
REM   Do not spend 4.5 GPU hours until run_P036_stage1b_trapping.bat says trapping
REM   is observable at our scale. As of result 019 the evidence is WEAK and the
REM   dense control had crashed, so stage 1B is the real decision point.
REM   The guard below now checks the FLAG only; the evidence check is on you.
REM
REM DESIGN, once unblocked - the comparison this makes
REM   Identical conditions, Arenas the ONLY difference, on the 3:4 preset:
REM     m100R1a + --arenas   vs   m100R1a
REM   That isolates Arenas from g and from 3:4, which the stage 1 checkpoints
REM   could not do (they differ in g as well).
REM COST: about 4.5 GPU hours for the pair.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P036-2] Arenas on/off - run stage 1B FIRST
python scripts\runlog.py --name P036-stage2 --note "[P036-2] Arenas on/off - GUARDED"
echo =============================================================

echo.
echo [guard] is --arenas implemented in the CLI
python scripts\runlog.py --name P036-stage2 --note "[guard] is --arenas implemented in the CLI"
python -c "import sys; sys.exit(0 if '--arenas' in open('tinylm/cli.py',encoding='utf-8').read() else 7)"
if errorlevel 1 goto NOTIMPL

echo.
echo =============================================================
echo [1/2] baseline : m100R1a, Arenas OFF
python scripts\runlog.py --name P036-stage2 --note "[1/2] baseline : m100R1a, Arenas OFF"
echo =============================================================
python scripts\runlog.py --name P036-stage2 -- python run100m.py train --preset m100R1a --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --kd --kd-every 4 --init-from --tag ar_off
if errorlevel 1 echo [WARN] ar_off failed - continuing

echo.
echo =============================================================
echo [2/2] treatment : same command plus --arenas
python scripts\runlog.py --name P036-stage2 --note "[2/2] treatment : same command plus --arenas"
echo =============================================================
python scripts\runlog.py --name P036-stage2 -- python run100m.py train --preset m100R1a --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --kd --kd-every 4 --init-from --arenas --tag ar_on
if errorlevel 1 echo [WARN] ar_on failed - read the traceback above

echo.
echo =============================================================
echo [post] trapping indicators on the two NEW checkpoints
python scripts\runlog.py --name P036-stage2 --note "[post] trapping indicators on the two NEW checkpoints"
echo =============================================================
python scripts\runlog.py --name P036-stage2 -- python scripts\diag_trapping.py --models ar_on ar_off --batches 12
if errorlevel 1 echo [WARN] trapping diagnosis failed - the training logs still stand

echo.
echo =================================================================
echo WHAT TO RECORD
echo   1. final val loss for both - 'final', never 'best'
echo   2. the valley fraction and ER/dim shift between ar_on and ar_off
echo   3. whether a quality recovery, if any, exceeds the 0.024 resolution
echo.
echo VERDICT
echo   ar_on better by more than 0.024, and the trapping indicators move
echo       -^> the 3:4 quality cost was partly OUR missing implementation.
echo          Candidate A must be re-evaluated - REVIEW1 inputs change.
echo   no difference beyond resolution
echo       -^> Arenas does not help at our scale. Record it and CLOSE R5. The
echo          3:4 cost is then structural, and A rests entirely on R8.
echo =================================================================
echo done.
pause
exit /b 0

:NOTIMPL
echo.
echo =================================================================
echo [STOP] --arenas was not found in the CLI. It WAS implemented on
echo   2026-07-31, so this means the working tree is older than that, or
echo   the change was reverted. Nothing was executed.
echo   Running 4.5 hours without the feature would produce a tidy log of
echo   the wrong experiment and we would conclude Arenas does nothing.
echo =================================================================
pause
exit /b 3

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
