@echo off
REM =============================================================================
REM  P072 stage 0  -  the layer interaction map
REM                   diagnostics only, no training, about 25 minutes
REM
REM  WHY THIS EXISTS  (user instruction, 2026-08-23)
REM    Four experiments asked the same question and none of them looked at the
REM    mechanism:
REM      P049 stage 3  attention reuse    rejected at +0.0281
REM      P057          attention tying    adopted at 36 layers
REM      P062          recursion R2       -0.0202
REM      P070          MLP shuffle        on hold
REM    All four are "what happens if we reuse a layer or change its order".
REM    All four have a result and no explanation. Draw the map first.
REM
REM  !! THE ONE THAT MATTERS  (U4)
REM    P049 measured cos 0.9882 between a layer's attention output and its
REM    duplicate visit, read that as "so we can skip it", and lost 0.0281.
REM    Similarity is not substitutability. U4 separates the two cases:
REM      same input, same work       means safe to tie
REM      same input, DIFFERENT work means do NOT tie
REM    If that pattern shows up, we get a test we can apply BEFORE running an
REM    experiment instead of after.
REM
REM  WHY DELTA AND NOT THE RESIDUAL ITSELF
REM    The residual stream barely changes across layers - that is what residual
REM    means. cos of x_i and x_j comes out 0.99 everywhere and carries no information.
REM    What a layer DID is the delta. Result 041's 0.9882 was a delta too.
REM
REM  GATES, fixed in advance
REM    M1  self similarity 1.0 within 1e-5      is the measurement sane
REM    M2  dense inter-layer cos under 0.3       is tying what made them similar
REM    M3  in-group cos minus cross-group over 0.1  does the boundary follow similarity
REM    M4  contribution max over min above 5x    are layers uneven enough to exploit
REM    M5  second pass over first pass 0.3-0.7  what does recursion add
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Causation. Similarity is correlation, and P049 is the cautionary tale.
REM    Also: one layer at a time. Removing two interacting layers is not the sum.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P072_stage0_layer_map --note "=============================================================================" "P072 stage 0   the layer interaction map   no training" "Four experiments reused or reordered layers and none looked at why." "U4 is the one that matters: same input with different work means do not tie." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P072_stage0_layer_map --note "[1/4] dense - the control. Tying is absent, so this is what similarity looks like without it."
python scripts\runlog.py --name P072_stage0_layer_map -- python scripts\diag_layer_map.py --preset m100 --data ko-en --tokens 300M --models dense
if errorlevel 1 echo [WARN] dense map failed - continuing

echo.
python scripts\runlog.py --name P072_stage0_layer_map --note "[2/4] mC_initonly - the standard control, mlp_group 8"
python scripts\runlog.py --name P072_stage0_layer_map -- python scripts\diag_layer_map.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly
if errorlevel 1 echo [WARN] mC_initonly map failed - continuing

echo.
python scripts\runlog.py --name P072_stage0_layer_map --note "[3/4] mC_d36_ag4_nokd - the standard model. What did attn_group 4 actually group."
python scripts\runlog.py --name P072_stage0_layer_map -- python scripts\diag_layer_map.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_nokd
if errorlevel 1 echo [WARN] d36 map failed - continuing

echo.
python scripts\runlog.py --name P072_stage0_layer_map --note "[4/4] mC_r20_nokd at R2 - U6, what the second pass contributes"
python scripts\runlog.py --name P072_stage0_layer_map -- python scripts\diag_layer_map.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20_nokd --infer-repeat 2.0
if errorlevel 1 echo [WARN] recursion map failed - continuing

echo.
python scripts\runlog.py --name P072_stage0_layer_map --note "=============================================================================" "READ IN THIS ORDER" "1. M1 on every model. If self similarity is not 1.0 the hooks are wrong and" "   nothing below means anything." "2. U4 on mC_r20_nokd. THIS is the P049 post mortem. If duplicate visits show" "   high input similarity and low delta similarity, that is why reuse failed" "   and we now have a test we can run before an experiment instead of after." "3. M3 on mC_initonly and the d36 model. If the tying boundary does not follow" "   similarity, the groups were drawn by j // g and nobody ever checked." "4. M2 on dense. High here means layers are naturally similar and tying did" "   not create that - which changes how we read every tying result." "5. U2 ranking. Layers we can compress harder are the ones at the bottom." "!! Similarity is correlation. P049 read it as causation and lost 0.0281." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
