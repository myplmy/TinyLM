@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_night_queue.bat -- overnight sequencer. Start it and go to sleep.
REM  v3, 2026-08-07. See "WHAT CHANGED" below.
REM =============================================================================
REM
REM WHAT THIS IS
REM   A thin sequencer. It does NOT contain experiment logic - each step is its
REM   own batch with its own plan, expectations and verdict text. This file only
REM   decides the ORDER and suppresses the pause prompts so nothing blocks.
REM
REM ***WHAT CHANGED IN v3***
REM   1. P046 (E=128) REMOVED from the queue. Its verdict was INVALID, not bad:
REM      grad_max 19.32 against a 0.847 baseline, and step-0 ce 10.4051 which is
REM      ln(32768) - the embedding started RANDOM. Fixed by an SVD-truncation
REM      transplant, but its priority is now LOW: result 032 showed E=128 is the
REM      most expensive lever per packed MB, and it only leads on the int8 path,
REM      which result 016 called "a last resort, not the default deployment path".
REM      Re-measure it after we commit to int8. No batch yet.
REM   2. P045 (g16) and P048 stage 1 DONE. Results 029 and 032.
REM   3. P047 STAYS AT THE FRONT - it produced 0 measurements last night because
REM      runlog.py silently dropped the command (--note and -- on one line, exit
REM      code 0, so the batch read it as success). THREE guards added: runlog
REM      refuses the combination, lint rule 9c catches it at authoring time, and
REM      rule 9d requires the plan number in --name. Batch fixed.
REM   4. P048 stage 2 ADDED - stacks g16 onto prelude/coda 1+1 to TEST A
REM      PREDICTION (+0.062) rather than to win. All three outcomes are useful.
REM   5. Log names now carry the plan number: P047_stage0, P048_mC_p1c1g16.
REM      Last night's logs came out as log_20260807_mC_g16.txt and had to be
REM      renamed by hand.
REM
REM ORDER AND WHY
REM   [1] P047 spam rate      20-60 min, ***GPU 0***
REM       Still the largest lever we have. Result 011 section 2 got -0.296 nats
REM       (24.7 sigma) from filtering ko-edu-en, and ko-en - the corpus EVERY
REM       baseline is trained on - has never been measured. Costs nothing.
REM       ***Must be known before REVIEW2*** - if positive, the task is not
REM       fixing the review, it is rebuilding the baselines.
REM   [2] P014C stage 1       1 min, GPU 0
REM       One-line check: does PyTorch expose a per-row fused int8 matmul.
REM       Result 028 opened this path (per-row costs only +0.005 to +0.006 bpb,
REM       under the 0.008 gate), and the answer decides whether we ever write a
REM       kernel. Cheapest decision-per-second in the queue.
REM   [3] P048 stage 2        about 3.0h
REM       g16 stacked on prelude/coda 1+1. Unique MLP 6 to 3, packed -26.3 pct.
REM       Predicted delta +0.062. Tests whether memory levers can be PRICED
REM       before spending GPU on them.
REM   [4] P040 tying speed    ***DO NOT PUT THIS IN THE QUEUE.*** It is a SPEED
REM       measurement and needs sole occupancy plus 5 minutes idle (result 016
REM       section 12.5). Run it alone, on a cold machine.
REM
REM   Total about 3.5 to 4.5 hours - shorter than v2 because two of the three
REM   training slots closed. If you want a fuller night, run P040 separately
REM   AFTER this queue finishes and the machine has been idle 5 minutes.
REM
REM SAFETY
REM   Each step warns and continues on failure, so one bad step does not waste
REM   the night. That rule already paid for itself: last night P047 died
REM   instantly and the remaining 10.5 hours ran anyway.
REM   ***You can Ctrl+C step [1] once its ratio has converged*** - it prints
REM   running totals every 200MB. That will not skip the rest of the queue.
REM
REM IN THE MORNING - read in this order, GATES BEFORE DELTAS
REM   1. P047: step 1 is the POSITIVE CONTROL (ko-edu-en). If it found no spam
REM      the tool is broken and step 2 means nothing. Then the ko-en spam CHAR
REM      percent, or the 95 percent upper bound if the count is 0.
REM      ***Also confirm the log is more than a few hundred bytes*** - that is
REM      what last night's failure looked like.
REM   2. P014C: just True or False, plus the signature if True.
REM   3. P048-2: the four [init] lines and report() ternary 38.0M FIRST, then
REM      ***grad_max from the json***, then the delta against the +0.062
REM      prediction.
REM =============================================================================

if not exist run100m.py goto BADROOT
set TL_NOPAUSE=1

echo =============================================================
echo [NIGHT QUEUE v3] 3 steps, about 3.5 to 4.5 hours
echo   [1] P047     corpus spam rate      20-60 min, GPU 0
echo   [2] P014C-1  fused int8 matmul     1 min,     GPU 0
echo   [3] P048-2   g16 + prelude/coda    about 3.0h
echo =============================================================
echo.

echo [1/3] P047 - corpus spam rate (no GPU, nothing written)
call run_P047_stage0_spam_rate.bat
if errorlevel 1 echo [WARN] P047 returned an error - continuing

echo.
echo [2/3] P014C stage 1 - does PyTorch have a per-row fused int8 matmul
python scripts\runlog.py --name P014C_stage1 --note "[P014C stage 1] per-row fused int8 matmul availability. Result 028 opened this path."
python scripts\runlog.py --name P014C_stage1 -- python scripts\check_fused_int8.py
if errorlevel 1 echo [WARN] P014C stage 1 returned an error - continuing

echo.
echo [3/3] P048 stage 2 - g16 stacked on prelude/coda 1+1
call run_P048_stage2_stack_g16.bat
if errorlevel 1 echo [WARN] P048 stage 2 returned an error - continuing

echo.
echo =============================================================
echo [NIGHT QUEUE v3] done. Logs in test_result\ (P047_stage0,
echo   P014C_stage1, P048_mC_p1c1g16). Read them in the order in
echo   this file's header - GATES come before DELTAS.
echo   Reminder: run_P040_tying_trainspeed.bat must be run ALONE
echo   on a cold machine, never inside this queue.
echo =============================================================
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
