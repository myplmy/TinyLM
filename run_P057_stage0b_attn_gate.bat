@echo off
REM =============================================================================
REM  P057 stage 0b  -  attention tying gate, RE-RUN after the import fix
REM                    (GPU light, about 1 minute, NO training)
REM
REM  WHY 0b AND NOT 0 AGAIN
REM    Stage 0 ran on 2026-08-14 and produced ZERO data. All three arms died in
REM    the first line of model construction with
REM        NameError: name 'build_attention' is not defined
REM    transformer.py called it without importing it, and only the attn_group
REM    branch calls it, so nothing else in the repo noticed. Log 044.
REM
REM    ***THE FILE NAME CARRIES THE ATTEMPT NUMBER ON PURPOSE.***
REM    Re-running an experiment under the SAME batch name destroys the record of
REM    what was already executed: the -done marker gets reverted, the runlog name
REM    collides with the old log, and the next session cannot tell a first run
REM    from a repeat. Convention: 0 -^> 0b -^> 0c. See ai_dev_tool/03 section 9.
REM
REM  WHAT CHANGED SINCE STAGE 0 (code, not this batch)
REM    1. transformer.py imports build_attention
REM    2. diag_depth_init.py G0-b is now axis-aware. It demands the P057 marker
REM       when --attn-group is on, and demands nothing when no axis is on.
REM       Stage 0's G0-b would have failed here for the wrong reason (result 045).
REM    3. tool_smoke.bat gained arms sm_ag and sm_split, which build a model on
REM       these axes. Run the smoke FIRST - it is what verifies fix 1.
REM
REM  THE AXIS
REM    Of the 54.85M ternary parameters, ATTENTION IS 26.54M = 48.4 percent, and
REM    it has never been tied. The MLP axis was closed at P045 (g16). This is the
REM    largest untouched memory lever we have.
REM
REM    !! AVERAGING IS NOT KNOWN TO WORK HERE.
REM    For MLPs it survived - result 030 s2 measured step0 ce 7.7742 against a
REM    random 10.4051. Attention patterns can be strongly position-specific per
REM    layer, in which case the average resembles no layer at all.
REM
REM  PASS BAND  (trap 34 - use a BAND, never a point)
REM    5.0 ^< step0 CE ^< 9.3972      anchor 7.7742 = tied + parent init (030 s2)
REM
REM  !! WHAT THIS GATE CAN AND CANNOT DECIDE  (decision trap D13, 2026-08-14)
REM    CAN : did the transplant work at all - a binary, versus the random control
REM    CANNOT : how big the quality cost will be after training, or the ranking
REM    Measured evidence: on the repeat axis the step0 cost was +0.1025 and the
REM    trained cost was +0.2275 (2.2x worse). On the depth axis the step0 lead
REM    was 0.5148 and the trained lead was 0.0250 (20.6x smaller). Direction held
REM    both times, magnitude did not. ***DO NOT CLOSE OR OPEN AN AXIS ON THIS.***
REM
REM  CONFOUND TO WRITE DOWN
REM    cla_group=2 already shares K/V across layer pairs, so a shared attention
REM    sits on both an owner and a re-user. Attributing the cost needs a
REM    cla_group=1 control. Stage 1 must not skip that.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P057_stage0b_attn --note "=============================================================================" "P057 stage 0b   attention tying gate RE-RUN   about 1 minute   NO training" "Stage 0 produced zero data - NameError on build_attention (log 044)." "Does the group-average attention transplant survive? Band 5.0 to 9.3972." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P057_stage0b_attn --note "[P057 stage 0b] attn_group 2 - 8 shared attentions over 16 middle layers."
python scripts\runlog.py --name P057_stage0b_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 2 --modes prop
if errorlevel 1 echo [WARN] attn-group 2 arm failed - continuing

echo.
python scripts\runlog.py --name P057_stage0b_attn --note "[P057 stage 0b] attn_group 4 - 4 shared attentions. Harder average, larger saving."
python scripts\runlog.py --name P057_stage0b_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 4 --modes prop
if errorlevel 1 echo [WARN] attn-group 4 arm failed - continuing

echo.
python scripts\runlog.py --name P057_stage0b_attn --note "[P057 stage 0b] attn_group 8 - 2 shared attentions. This is the aggressive end."
python scripts\runlog.py --name P057_stage0b_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 8 --modes prop
if errorlevel 1 echo [WARN] attn-group 8 arm failed - continuing

echo.
echo.
python scripts\runlog.py --name P057_stage0b_attn --note "=============================================================================" "WHAT TO READ" "1. The G0-b line - it should now name what it demands, and demand the P057 marker" "2. The random control - it should sit near ln V = 10.3972" "3. step0 CE per attn_group against the band 5.0 to 9.3972, anchor 7.7742" "4. The GAP between random and transplanted - that is what averaging bought" "5. Where the value collapses as g grows - that is the usable g" "REMINDER: single small crop, and step0 only. It decides GO or NO-GO for" "stage 1, and it decides NOTHING about the size of the trained cost (D13)." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
