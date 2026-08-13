@echo off
REM =============================================================================
REM  P061 stage 0  -  uneven tying: are early and late layers different?
REM                   (GPU light, about 1 minute, NO training)
REM
REM  THE IDEA
REM    mC_wsd ties 16 middle layers as 8+8, two unique MLPs. Keep the COUNT and
REM    change only the LAYOUT:
REM        A (front-heavy)  12+4    [0..11] [12..15]
REM        B (back-heavy)    4+12   [0..3]  [4..15]
REM    Both still have two unique MLPs, so MEMORY IS IDENTICAL. The only thing
REM    that moves is where the sharing pressure sits.
REM
REM  WHY B EXISTS
REM    B is the control. Literature says early layers are more redundant, so A
REM    should win. Measuring A alone cannot separate "layer position matters"
REM    from "12+4 happens to beat 8+8". B is what makes the claim falsifiable.
REM
REM  WHAT STAGE 0 CHECKS  (shape only, no training)
REM    G0-a  unique mid MLP count is 2 for both A and B
REM    G0-b  ternary parameter count is UNCHANGED at 54.85M
REM    G0-c  step0 CE inside the band 5.0 to 9.3972
REM
REM  PASS BAND  (trap 34)
REM    anchor 7.7742 = tied + parent init (result 030 s2).
REM    !! EXPECT MORE SPREAD THAN USUAL. Averaging 12 teacher MLPs into one
REM    loses more than averaging 8, so A and B need not land together. That is
REM    WHY the gate is a band and not a point - a point check would false-alarm.
REM
REM  ALREADY VERIFIED WITHOUT GPU
REM    16-layer enumeration confirmed that an empty split reproduces j // g
REM    exactly, so mlp_split unset is bit identical. This batch checks the part
REM    that arithmetic cannot: whether the transplant still lands.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P061_stage0_split --note "=============================================================================" "P061 stage 0   uneven tying shape gate   about 1 minute   NO training" "A = 12+4 front-heavy, B = 4+12 back-heavy. Same memory, different layout." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P061_stage0_split --note "[P061 stage 0] baseline 8+8 - this must reproduce the ordinary g8 numbers."
python scripts\runlog.py --name P061_stage0_split -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --modes prop
if errorlevel 1 echo [WARN] baseline arm failed - continuing

echo.
python scripts\runlog.py --name P061_stage0_split --note "[P061 stage 0] A front-heavy 12+4 - early layers share harder."
python scripts\runlog.py --name P061_stage0_split -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --mlp-split 12 --modes prop
if errorlevel 1 echo [WARN] arm A failed - continuing

echo.
python scripts\runlog.py --name P061_stage0_split --note "[P061 stage 0] B back-heavy 4+12 - the control. Without it the claim is not falsifiable."
python scripts\runlog.py --name P061_stage0_split -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --mlp-split 4 --modes prop
if errorlevel 1 echo [WARN] arm B failed - continuing

echo.
echo.
python scripts\runlog.py --name P061_stage0_split --note "=============================================================================" "WHAT TO READ" "1. group sizes printed by the axis line - must be 8,8 then 12,4 then 4,12" "2. unique mid MLP count - must be 2 in all three" "3. step0 CE against the band 5.0 to 9.3972, anchor 7.7742" "4. A vs B at step 0 is SUGGESTIVE ONLY. Training decides, stage 1 does that." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
