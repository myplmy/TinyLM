@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_night_queue_v4.bat -- SCHEDULER ONLY. It calls experiment batches.
REM  Rule: ai_dev_tool\03 section 6 -- one experiment, one batch. The queue only
REM        calls. Never put a training or diagnostic command in here.
REM =============================================================================
REM
REM ***ABOUT 18 GPU HOURS TOTAL.*** Built for a multi-day window with no AI help.
REM   Every step is independent. One failing does not stop the rest, and each
REM   one carries its own preconditions, predictions and reading guide in its
REM   own header - so a log alone is enough to write the result document later.
REM
REM ORDER AND WHY
REM   [0] smoke     - CODE CHANGED (--micro-group, diag_fp8_precision.py).
REM                   ***This one DOES stop the queue.*** 2026-07-31 left every
REM                   training run dead for hours because a report() regression
REM                   went unsmoked. Do not spend 18 hours on a broken tree.
REM   [1] P022B-0   - minutes, GPU diagnostic, no training. Cheap gates first
REM                   (ai_dev_tool\03 section 2.2).
REM   [2] P042-1    - 60 min. Speed and VRAM. Needs sole occupancy; sequential
REM                   execution provides it and the batch waits 300 s first.
REM   [3] P042-2    - 20 min. Does --no-ckpt open. An OOM is the answer.
REM   [4] P050      - 9.5 h. ***Highest value.*** It corrects how P046, P048 and
REM                   P049 deltas should be read, and decides whether the P049
REM                   prerequisite needs building at all.
REM   [5] P051      - 3.5 h. Closes the last unswept axis (alpha granularity).
REM   [6] P046      - 3.5 h. OPTIONAL, run last. Resolves a VERDICT IMPOSSIBLE.
REM
REM ***DELETE THIS FILE WHEN THE QUEUE IS DONE.*** It is a scheduler, not an
REM   experiment asset. Every command it needs lives in the called batches.
REM
REM TL_NOPAUSE suppresses the pause inside each child batch so the queue keeps
REM   moving. The queue itself pauses at the end.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
set TL_NOPAUSE=1

echo =============================================================
echo [queue v4] about 18 GPU hours, 7 steps, all independent
echo =============================================================

echo.
echo [0/6] smoke check - code changed, this is a hard gate
call run_smoke_check.bat
if errorlevel 1 goto SMOKEBAD

echo.
echo [1/6] P022B stage 0 - FP8 E4M3 numerical gate (minutes)
call run_P022B_stage0_fp8_probe.bat
if errorlevel 1 echo [WARN] P022B stage 0 failed - continuing

echo.
echo [2/6] P042 stage 1 - teacher inference mode speed and VRAM (about 60 min)
call run_P042_stage1_speed_vram.bat
if errorlevel 1 echo [WARN] P042 stage 1 failed - continuing

echo.
echo [3/6] P042 stage 2 - does --no-ckpt open (about 20 min)
call run_P042_stage2_nockpt.bat
if errorlevel 1 echo [WARN] P042 stage 2 did not finish - an OOM here is a RESULT, continuing

echo.
echo [4/6] P050 - parent dependency ablation (about 9.5 h)
call run_P050_parent_ablation.bat
if errorlevel 1 echo [WARN] P050 failed - continuing

echo.
echo [5/6] P051 - micro_group 128 to 256 (about 3.5 h)
call run_P051_micro_group256.bat
if errorlevel 1 echo [WARN] P051 failed - continuing

echo.
echo [6/6] P046 - embedding E=128 re-measured with SVD transplant (about 3.5 h, OPTIONAL)
call run_P046_emb_rank128.bat
if errorlevel 1 echo [WARN] P046 failed

echo.
echo =============================================================
echo [queue v4] finished. Collect the logs from test_result and smoketest_logs.
echo   Reading order: P022B-0 gate, then P042-1 drift check, then P042-2 OOM
echo   or not, then P050 decomposition, then P051 gate G-a, then P046 gate G-init.
echo =============================================================
set TL_NOPAUSE=
if not defined TL_NOPAUSE pause
exit /b 0

:SMOKEBAD
echo.
echo [STOP] smoke check failed. The tree is broken - do not burn 18 hours on it.
echo   Read the [VERIFY] lines in smoketest_logs and fix before re-queuing.
set TL_NOPAUSE=
if not defined TL_NOPAUSE pause
exit /b 3

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
