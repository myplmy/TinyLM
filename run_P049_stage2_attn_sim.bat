@echo off
REM =============================================================================
REM  P049 stage 2  -  do duplicated layers compute the SAME attention?
REM                   (NO TRAINING, GPU eval only, a few minutes)
REM
REM  THE QUESTION THAT HAS BEEN OPEN SINCE 2026-08-20
REM    The user asked: if the second pass through a duplicated layer recomputes
REM    the same positional pattern, can the two be batched?
REM    We answered in docs/20260806 s7.1 that the sentence points at TWO claims:
REM        (1) the OUTPUT is the same   then skip the second pass entirely
REM        (2) the CONTRIBUTION is small then the gate closed, output may differ
REM    Result 041 s15 measured (2): duplicated layers end at 0.279x the gate of
REM    non-duplicated ones. Nobody has ever measured (1). This does.
REM
REM  WHY A CONTROL IS MANDATORY
REM    Attention outputs are similar to each other by nature - they live in a
REM    narrow cone. So the tool measures THREE groups:
REM        (a) duplicated pair      same teacher layer, same attention module
REM        (b) same module, not dup grouped by attn-group but different source
REM        (c) different module     unrelated pair = the floor
REM    Group (a) must beat (c) by a clear margin. Reading (a) alone is the
REM    mistake this repo keeps making (trap 34).
REM
REM  GATES, fixed in advance
REM    (a) mean cos at least 0.95 AND (a) minus (c) at least 0.20  reuse possible
REM    (a) minus (c) under 0.05                                    claim 1 REJECTED
REM    duplicated contribution under 0.25x                         skip candidate
REM
REM  TWO MODELS AND WHY
REM    mC_d36_ag4  36 layers, attn-group 4 - our best residency model
REM    mC_d36      36 layers, no attention tying - separates "sharing the
REM                module" from "being a duplicate of the same teacher layer"
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether skipping is free. The quality cost only comes from actually
REM    removing the attention and running full-val - that is a separate arm.
REM    Measured under bf16 autocast: read cosine to 2 decimals, not 4.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P049_stage2_attnsim --note "=============================================================================" "P049 stage 2   do duplicated layers compute the same attention   NO TRAINING" "Result 041 measured the gate. This measures the output." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P049_stage2_attnsim --note "[1/2] mC_d36_ag4 - 36 layers with attn-group 4. Best residency model."
python scripts\runlog.py --name P049_stage2_attnsim -- python scripts\diag_repeat_attn_sim.py --tag mC_d36_ag4 --preset m100R1c --data ko-en --tokens 300M --crops 8
if errorlevel 1 echo [WARN] d36_ag4 pass failed - continuing

echo.
python scripts\runlog.py --name P049_stage2_attnsim --note "[2/2] mC_d36 - 36 layers, NO attention tying. Separates sharing from duplication."
python scripts\runlog.py --name P049_stage2_attnsim -- python scripts\diag_repeat_attn_sim.py --tag mC_d36 --preset m100R1c --data ko-en --tokens 300M --crops 8
if errorlevel 1 echo [WARN] d36 pass failed - continuing

echo.
echo.
python scripts\runlog.py --name P049_stage2_attnsim --note "=============================================================================" "READ IN THIS ORDER" "1. the unique attention module count. ag4 should show 36 layers over about" "   10 modules; d36 should show one module per layer." "2. group (c) mean. THAT is the floor. Everything else is read against it." "3. group (a) minus group (c). Under 0.05 rejects claim (1) outright." "4. section B contribution ratio. Below 0.25 means skipping is cheap even if" "   the outputs differ - that is claim (2) made quantitative." "5. compare the two models. If (a) is high only in ag4, the similarity comes" "   from SHARING the module, not from being a duplicate - a different story." "REMINDER  bf16 autocast. Cosine to 2 decimals." "REMINDER  this does not say skipping is free. Only a full-val with the" "          attention removed says that." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
