@echo off
REM =============================================================================
REM  P049 stage 0  -  depth-expanding transplant gate   (no training, minutes)
REM
REM  WHY THIS RUNS BEFORE THE 5.8 HOUR RUN
REM    m100R1d is 36 layers, the dense parent is 20. The old init_from_dense
REM    would have died with IndexError in mid_mlps, and before that it would
REM    have left the student's last 16 layers random.
REM    Result 038 s9 measured that parent init is worth +0.1386 AND cuts seed
REM    noise 6.4x, so a broken transplant makes us underrate the architecture
REM    twice. Result 030 already paid that bill once.
REM
REM  GATES
REM    G0-a  does not raise
REM    G0-b  prints the structural mismatch warning
REM    G0-c  step0 CE ^< ln(vocab) - 1.0     i.e. the transplant actually helped
REM
REM  It also measures depth_init=prop vs gate_scale and recommends one.
REM  Duplicating a layer duplicates its residual contribution - whether that
REM  needs the gate divided is not guessed here, it is measured.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

set TL_OUTDIR=smoketest_logs

echo.
echo ================= P049 stage 0  init gate ==================================
python scripts\runlog.py --name P049_stage0_init --note "[P049 stage 0] depth-expanding transplant gate - 20 layer parent into 36 layer student, prop vs gate_scale"
python scripts\runlog.py --name P049_stage0_init -- python scripts\diag_depth_init.py --preset m100R1d --teacher-preset m100
if errorlevel 1 goto GATEBAD

echo.
echo =============================================================================
echo  Gate passed. run_P049_depth_g16x2.bat can now run (about 5.8 h).
echo  Put the recommended depth_init into that batch first if it is not `prop`.
echo =============================================================================
if not defined TL_NOPAUSE pause
exit /b 0

:GATEBAD
echo.
echo [STOP] the transplant gate failed. Do NOT start the 5.8 hour run.
echo        Fix the transplant, or record that the depth axis is closed.
echo        Result 030 is what happens when you measure through a broken init.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
