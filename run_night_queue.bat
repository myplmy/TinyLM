@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_night_queue.bat -- overnight sequencer. Start it and go to sleep.
REM =============================================================================
REM
REM WHAT THIS IS
REM   A thin sequencer. It does NOT contain experiment logic - each step is its
REM   own batch with its own plan, expectations and verdict text. This file only
REM   decides the ORDER and suppresses the pause prompts so nothing blocks.
REM
REM ORDER AND WHY
REM   [1] P014C stage 0   minutes, GPU ~0   cheapest, highest information.
REM                       Decides whether we need a custom ternary kernel at all.
REM                       Run first so its answer is waiting in the morning.
REM   [2] P046 E=128      about 3.5h        LARGEST remaining memory lever,
REM                       residency -18.8 percent (computed).
REM   [3] P045 g16        about 3.5h        closes the tying axis, -5.3 percent.
REM
REM   Total about 7 to 7.5 hours. [2] before [3] because [2] buys 3.5x more.
REM
REM SAFETY
REM   Each step warns and continues on failure, so one bad step does not waste
REM   the whole night. Every step writes to test_result/ via runlog.py with fsync,
REM   so partial logs survive even if the machine is interrupted.
REM
REM ***WHAT NOT TO DO WHILE THIS RUNS***
REM   Do not start run_P040_tying_trainspeed.bat or any run_P034_* batch. Those
REM   are SPEED measurements and require sole occupancy plus 5 minutes idle
REM   (result 016 section 12.5). This queue is training, so it is fine with
REM   itself, but it would poison a speed benchmark.
REM
REM IN THE MORNING - read in this order
REM   1. P014C: the g128 row must show relative error 0.000000 (tool correctness),
REM      then the per-row Delta-bpb - that is the kernel fork.
REM   2. P046: paired delta vs mC_wsd, and the [init] warning lines.
REM   3. P045: paired delta, and that the header really says MLP g=16.
REM =============================================================================

if not exist run100m.py goto BADROOT
set TL_NOPAUSE=1

echo =============================================================
echo [NIGHT QUEUE] 3 steps, about 7 to 7.5 hours
echo   [1] P014C stage 0  alpha granularity      minutes
echo   [2] P046           embedding rank 128     about 3.5h
echo   [3] P045           tying ceiling g16      about 3.5h
echo =============================================================
echo.

echo [1/3] P014C stage 0 - alpha granularity
call run_P014C_stage0_alpha_group.bat
if errorlevel 1 echo [WARN] P014C stage 0 returned an error - continuing

echo.
echo [2/3] P046 - embedding rank 128
call run_P046_emb_rank128.bat
if errorlevel 1 echo [WARN] P046 returned an error - continuing

echo.
echo [3/3] P045 - tying ceiling g16
call run_P045_g16_ceiling.bat
if errorlevel 1 echo [WARN] P045 returned an error - continuing

echo.
echo =============================================================
echo [NIGHT QUEUE] done. Logs are in test_result\ (P014C-stage0,
echo   mC_e128, mC_g16). Read them in the order in this file's header.
echo =============================================================
pause
exit /b 0

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
pause
exit /b 9
