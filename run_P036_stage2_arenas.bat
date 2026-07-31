@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P036_stage2_arenas.bat  --  P036 STAGE 2 : Arenas on/off, same conditions
REM  Plan: test_plan\P036_...md    Roadmap: R5 (conditional on R4/stage 1B)
REM =============================================================================
REM
REM ***THIS BATCH IS GUARDED AND WILL STOP.***
REM   P036 stage 0 - implementing Arenas - has not been done. The guard below
REM   checks for the flag and halts if it is absent. That is deliberate: a batch
REM   that silently trains without the feature it is named after would produce a
REM   clean-looking log of the WRONG experiment, and we would compare it to the
REM   baseline and conclude Arenas does nothing.
REM
REM   That is not hypothetical. Result 016 section 7.5 records exactly this class
REM   of mistake: the paper (Sherry, 3:4) was read at abstract level, "Arenas =
REM   our anneal" was assumed, and an experiment was run WITHOUT a required part
REM   of the method. Three misreadings came from that one shortcut.
REM
REM WHAT STAGE 0 MUST DELIVER BEFORE THIS RUNS
REM   1. Read the paper BODY, not the abstract - arXiv:2601.07892. web_fetch can
REM      retrieve the HTML. Write down, in the plan: what an Arena is, when it is
REM      applied, and the exact baseline the paper's numbers are measured against.
REM   2. Implement it in tinylm\ behind --arenas, with the parameter defaults in
REM      config.py and nowhere else.
REM   3. Run tool_smoke.bat. A new training flag that is not in the smoke
REM      contract is a flag that can be silently ignored for 4.5 hours.
REM   4. Only then delete the guard below.
REM
REM PRECONDITION ON EVIDENCE
REM   Stage 1B must first show trapping at our scale. As of result 019 the
REM   evidence is WEAK and the dense control had crashed, so stage 1B is the
REM   real gate on whether these 4.5 GPU hours are worth spending at all.
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
echo [P036-2] Arenas on/off - GUARDED
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
echo [STOP] --arenas is not implemented (P036 stage 0 is not done).
echo   Nothing was executed, on purpose. Running these 4.5 hours without
echo   the feature would produce a tidy log of the wrong experiment, and
echo   we would then conclude that Arenas does nothing.
echo   See the header for what stage 0 has to deliver first.
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
