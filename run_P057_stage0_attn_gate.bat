@echo off
REM =============================================================================
REM  P057 stage 0  -  attention tying: does the group-average transplant live?
REM                   (GPU light, about 1 minute, NO training)
REM
REM  THE AXIS
REM    Of the 54.85M ternary parameters, ATTENTION IS 26.54M = 48.4 percent, and
REM    it has never been tied. The MLP axis was closed at P045 (g16). This is the
REM    largest untouched memory lever we have.
REM
REM  WHAT STAGE 0 DECIDES
REM    attn_group g means g middle layers SHARE one attention module. Parent
REM    initialisation then has to map g teacher attentions onto one student
REM    attention. We implemented GROUP AVERAGING, the same rule mid_mlps uses.
REM
REM    !! AVERAGING IS NOT KNOWN TO WORK HERE.
REM    For MLPs it survived - result 030 s2 measured step0 ce 7.7742 against a
REM    random 10.4051, so the parent-init gain was still there after averaging.
REM    ATTENTION MAY NOT BEHAVE THE SAME. Attention patterns can be strongly
REM    position-specific per layer, in which case the average is a smear that
REM    resembles no layer. That is exactly what this gate measures.
REM
REM  PASS BAND  (trap 34 - use a BAND, never a point)
REM    5.0 ^< step0 CE ^< 9.3972      anchor 7.7742 = tied + parent init (030 s2)
REM    Above the ceiling (ln V - 1) the transplant bought nothing.
REM    Below the floor it is TOO GOOD - suspect that tying did not apply.
REM    The teacher's own 3.8080 is UNREACHABLE for a tied student. Do not use it.
REM
REM  WHAT THE RANDOM CONTROL IS FOR
REM    The script measures an uninitialised model first. The gap between that
REM    and the transplanted model IS the value of the transplant. Result 041 s13
REM    got -4.7831 nats on the depth axis; anything of that order here means
REM    attention averaging survives.
REM
REM  CONFOUND TO WRITE DOWN
REM    cla_group=2 already shares K/V across layer pairs, so a shared attention
REM    sits on both an owner and a re-user. It works, but attributing the cost
REM    needs a cla_group=1 control. Stage 1 must not skip that.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P057_stage0_attn --note "=============================================================================" "P057 stage 0   attention tying gate   about 1 minute   NO training" "Does the group-average attention transplant survive? Band 5.0 to 9.3972." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P057_stage0_attn --note "[P057 stage 0] attn_group 2 - 8 shared attentions over 16 middle layers."
python scripts\runlog.py --name P057_stage0_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 2 --modes prop
if errorlevel 1 echo [WARN] attn-group 2 arm failed - continuing

echo.
python scripts\runlog.py --name P057_stage0_attn --note "[P057 stage 0] attn_group 4 - 4 shared attentions. Harder average, larger saving."
python scripts\runlog.py --name P057_stage0_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 4 --modes prop
if errorlevel 1 echo [WARN] attn-group 4 arm failed - continuing

echo.
python scripts\runlog.py --name P057_stage0_attn --note "[P057 stage 0] attn_group 8 - 2 shared attentions. This is the aggressive end."
python scripts\runlog.py --name P057_stage0_attn -- python scripts\diag_depth_init.py --preset m100R1c --teacher-preset m100 --attn-group 8 --modes prop
if errorlevel 1 echo [WARN] attn-group 8 arm failed - continuing

echo.
echo.
python scripts\runlog.py --name P057_stage0_attn --note "=============================================================================" "WHAT TO READ" "1. The random control first - it should sit near ln V = 10.3972" "2. step0 CE per attn_group against the band 5.0 to 9.3972, anchor 7.7742" "3. The GAP between random and transplanted - that is what averaging bought" "4. Where the value collapses as g grows - that is the usable g" "REMINDER: this is a single small crop. Do not compare across scripts." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
