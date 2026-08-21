@echo off
REM =============================================================================
REM  P049 stage 2b  -  rerun with the classifier fixed
REM                    (NO TRAINING, GPU eval, minutes)
REM
REM  WHY A RERUN (result 041 s17.5)
REM    Stage 2 defined "duplicated pair" as same_mod AND same_src. But the
REM    definition of duplicated is same_src alone - sharing the module is a
REM    different axis. With attn_group 1 the AND is never true, so group (a)
REM    came back EMPTY for mC_d36 and the comparison the batch was built for
REM    never ran. Trap 18: one name, two conditions.
REM    Fixed to (a) same_src, (b) same_mod and not same_src, (c) neither.
REM
REM  WHAT STAGE 2 ALREADY SHOWED, AND WHAT IS STILL INFERRED
REM    mC_d36_ag4: (a) 0.9882, (b) 0.8716, (c) 0.0586. Claim (1) HOLDS - the
REM    duplicated layers compute essentially the same attention output.
REM    mC_d36: (a) was empty. The only evidence was that max over ALL pairs
REM    was 0.7657, which implies the duplicate pairs cannot exceed 0.77. That
REM    is an inference. This run measures it.
REM
REM  THE THIRD MODEL IS NEW
REM    mC_d36_ag4_nokd (result 044 s10) is the model candidate we actually
REM    intend to ship. Stage 2 measured the KD-trained twin. If the similarity
REM    is a KD artefact it will show up here.
REM
REM  PREDICTIONS, fixed in advance
REM    Q1  mC_d36 group (a) is now non-empty with 16 pairs
REM    Q2  its mean lands near 0.7 and clearly under mC_d36_ag4's 0.9882 -
REM        confirming the similarity comes from SHARING, not duplication
REM    Q3  mC_d36_ag4_nokd reproduces about 0.98 - not a KD artefact
REM    Q4  the (c) floor stays near 0.05 in all three
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether skipping or reusing is free. cos 0.9882 is not 1, and 0.0118 of
REM    difference can compound over 36 layers. Only a full-val with the second
REM    attention actually removed answers that.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P049_stage2b_attnsim --note "=============================================================================" "P049 stage 2b   classifier fixed   NO TRAINING" "Stage 2 defined duplicated with two conditions. It is one." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P049_stage2b_attnsim --note "[1/3] mC_d36 - attn_group 1. Group (a) was EMPTY in stage 2. This is the fix."
python scripts\runlog.py --name P049_stage2b_attnsim -- python scripts\diag_repeat_attn_sim.py --tag mC_d36 --preset m100R1c --data ko-en --tokens 300M --crops 8
if errorlevel 1 echo [WARN] d36 failed - continuing

echo.
python scripts\runlog.py --name P049_stage2b_attnsim --note "[2/3] mC_d36_ag4 - regression check. Should reproduce 0.9882."
python scripts\runlog.py --name P049_stage2b_attnsim -- python scripts\diag_repeat_attn_sim.py --tag mC_d36_ag4 --preset m100R1c --data ko-en --tokens 300M --crops 8
if errorlevel 1 echo [WARN] d36_ag4 failed - continuing

echo.
python scripts\runlog.py --name P049_stage2b_attnsim --note "[3/3] mC_d36_ag4_nokd - the model we intend to ship. Is the similarity a KD artefact?"
python scripts\runlog.py --name P049_stage2b_attnsim -- python scripts\diag_repeat_attn_sim.py --tag mC_d36_ag4_nokd --preset m100R1c --data ko-en --tokens 300M --crops 8
if errorlevel 1 echo [WARN] d36_ag4_nokd failed - continuing

echo.
echo.
python scripts\runlog.py --name P049_stage2b_attnsim --note "=============================================================================" "READ IN THIS ORDER" "1. call 1 group (a) pair count. It must be 16, not 0. If it is still 0 the" "   fix did not land and nothing below is new." "2. call 1 (a) mean against call 2 (a) mean. That gap IS the answer to" "   duplication versus module sharing." "3. call 3 against call 2. A big drop means the 0.9882 needed KD." "4. the (c) floor in all three. If it moved, the data or model changed." "REMINDER  this does not say skipping is free. Only a full-val with the" "          attention removed says that." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
