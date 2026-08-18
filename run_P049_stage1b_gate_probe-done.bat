@echo off
REM =============================================================================
REM  P049 stage 1b  -  did the duplicated layers wake up?
REM                    (NO TRAINING, NO GPU, a few seconds)
REM
REM  WHY 1b
REM    Result 041 s13.4 fixed this as "stage 1 MUST record" and stage 1 did not.
REM    The batch never printed a gate value, so it came out as unmeasured
REM    (result 041 s14.5). That is trap 13 - writing an action in a document is
REM    not the same as putting it in the batch.
REM    Stage 1 already ran, so this is a NEW stage name, not a re-run (D14).
REM
REM  WHAT IT ANSWERS
REM    --depth-init gate_scale halves the residual gate of every duplicated
REM    layer. mC_d36 has 32 middle layers mapped onto 16 teacher layers, so
REM    those start at half strength. Did training move them off that value?
REM    If not, 36 layers were effectively 20 and P049 never answered its own
REM    question. The answer decides between two very different conclusions:
REM      "the depth axis is dead"  vs  "our transplant could not use depth"
REM
REM  HOW IT DECIDES
REM    gate size alone is misleading - duplicated layers START at half, so they
REM    look small no matter what. The metric is RELATIVE MOVEMENT from the
REM    transplanted value, duplicated layers versus non-duplicated ones.
REM      ratio ^>= 0.5   awake
REM      0.2 to 0.5     partial
REM      ^< 0.2          not awake
REM
REM  COST: seconds. It only opens two state_dicts. No model is built.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P049_stage1b_gates --note "=============================================================================" "P049 stage 1b   did the duplicated layers wake up   seconds   NO TRAINING" "Metric is relative movement from the transplanted gate, dup vs non-dup." "awake ^>= 0.5   partial 0.2 to 0.5   not awake ^< 0.2" "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P049_stage1b_gates --note "[1/2] mC_d36 - the 36 layer run. 32 middle layers over 16 teacher layers, so lrep is 2."
python scripts\runlog.py --name P049_stage1b_gates -- python scripts\diag_layer_gates.py --tag mC_d36 --preset m100R1d --teacher-preset m100
if errorlevel 1 echo [WARN] mC_d36 probe failed - continuing

echo.
python scripts\runlog.py --name P049_stage1b_gates --note "[2/2] mC_wsd - CONTROL. Same depth as the teacher, so lrep is 1 everywhere. This shows what ordinary gate movement looks like."
python scripts\runlog.py --name P049_stage1b_gates -- python scripts\diag_layer_gates.py --tag mC_wsd --preset m100R1c --teacher-preset m100
if errorlevel 1 echo [WARN] mC_wsd control failed - continuing

echo.
echo.
python scripts\runlog.py --name P049_stage1b_gates --note "=============================================================================" "READ" "1. arm 2 first - the control tells you what normal movement is on this data." "2. arm 1 verdict line for attention and for MLP separately." "3. if NOT AWAKE: P049's -0.0250 was bought by 20 effective layers, and the" "   axis is not dead - our transplant is. That reopens the design question." "4. if AWAKE: the depth axis really did cost 35.9 percent residency for 0.0250" "   and the closure stands." "LIMIT: gate size is not usefulness. Only ablation proves that, and it is dearer." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
