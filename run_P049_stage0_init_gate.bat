@echo off
REM =============================================================================
REM  P049 stage 0  -  depth-expanding transplant gate   RE-RUN with identity mode
REM
REM  ***THE FIRST RUN FAILED AND THAT IS THE POINT.***  Result 041:
REM    random control  step0 CE 10.4082   ^|logit^|max  0.98
REM    prop            step0 CE 12.7224   ^|logit^|max 15.94
REM    gate_scale      step0 CE 13.4782   ^|logit^|max 18.75
REM
REM  The transplant was WORSE than random. Not "init did not happen" - "init hurts".
REM  And halving the gates (gate_scale) made it worse still, which rules out the
REM  residual-magnitude explanation: the problem is COMPOSITION. A layer trained
REM  to see depth-k activations is being fed its own output.
REM
REM  NEW MODE: identity. Duplicated layers get gates = 0, and since
REM  Layer.forward is x = x + gates * branch, gate 0 is an exact identity.
REM  So the 36-layer student starts as EXACTLY the 20-layer teacher.
REM  Expect step0 CE near the teacher's val, about 3.8, not 12.7.
REM
REM  Logs land in test_result, NOT smoketest_logs - a gate is an experiment.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P049_stage0_identity --note "=============================================================================" "P049 stage 0 RE-RUN - identity mode added after result 041" "prop 12.7224 / gate_scale 13.4782 / random 10.4082 -^> all failed G0-c" "identity should land near the teacher val (about 3.8)" "============================================================================="

python scripts\runlog.py --name P049_stage0_identity -- python scripts\diag_depth_init.py --preset m100R1d --teacher-preset m100
if errorlevel 1 goto GATEBAD

echo.
python scripts\runlog.py --name P049_stage0_identity --note "=============================================================================" "Gate passed. Before starting stage 1, set --depth-init to the recommended mode" "in run_P049_depth_g16x2.bat (it currently says identity)." "!! identity starts the duplicated layers as no-ops. The open question is" "   whether training WAKES THEM UP - stage 1 must record whether the" "   duplicated gates moved away from 0. If they did not, 36 layers are" "   effectively 20 and P049 cannot answer its own question." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:GATEBAD
echo.
echo [STOP] the transplant gate failed again.
echo        Read the per-mode step0 CE table. If identity is ALSO above the line,
echo        the problem is not the gates - suspect the layer map or the coda.
echo        Do NOT start the 5.8 hour run. Result 030 is what that costs.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
