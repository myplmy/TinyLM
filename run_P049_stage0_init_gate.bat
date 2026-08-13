@echo off
REM =============================================================================
REM  P049 stage 0  -  RE-RUN after the gate itself was found to be broken
REM
REM  ***THE PREVIOUS TWO RUNS MEASURED NOTHING.***  Result 041 s11:
REM    the gate fed the model RANDOM tokens as input AND RANDOM tokens as the
REM    target. Against random targets a well-initialised model scores WORSE than
REM    a random one, because it predicts confidently and the target is noise.
REM    So the metric ran backwards - the better the transplant, the worse it looked.
REM
REM    identity is mathematically IDENTICAL to the teacher (duplicated layers get
REM    gates=0, an exact identity), yet it scored 13.4887 while the teacher's
REM    deterministic full-val is 3.8080 (result 040 s2). A teacher cannot score
REM    3.5x its own value. That is what exposed the bug.
REM
REM  FIXED
REM    - real val data with next-token targets, loader seed 99 (the standard)
REM    - the gate now prints the teacher reference 3.8080 alongside ln(V)
REM
REM  So: random init should land near 10.40, a working transplant near 3.81.
REM  ***Nothing about the depth axis is known yet.*** The earlier conclusions
REM  ("the transplant is harmful", "logits explode", "gate_scale is worse so the
REM  magnitude hypothesis is dead") were all retracted.
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
