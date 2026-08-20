@echo off
REM =============================================================================
REM  P066 stage 0  -  residency of the four candidates on the DEPLOYMENT path
REM                   (NO TRAINING, CPU, a few minutes)
REM
REM  THE GOAL, RESTATED
REM    packed is already inside the L2+L3 budget: 9.6 MB at best against 40 MB.
REM    RESIDENT is not: 379.7 MB at best, which is 9.5 times over. The user set
REM    the target explicitly - resident memory during inference, not file size.
REM    So every number this batch reads is runtime_mb and measured RSS. packed
REM    is printed for reference and is NOT the judgement.
REM
REM  WHY NOW, BEFORE REVIEW3
REM    mC_d36_ag4 became the best resident model on 2026-08-20 at 379.7 MB, and
REM    we have never measured it on the int8 or drop-latent paths. Trap 24 says
REM    lever rankings FLIP between fp32 and int8 - E=128 wins by 18.8 percent in
REM    int8 and only 3.6 percent in fp32. Starting REVIEW3 from the fp32 table
REM    alone would be starting from the wrong ranking.
REM
REM  THE FOUR MODELS AND WHY EACH ONE
REM    mC_wsd        the shared control every lever table compares against
REM    mC_initonly   the no-KD baseline REVIEW2 is about to adopt
REM    mC_d36_ag4    best RESIDENT, 379.7 MB
REM    mC_p1c1g16    best PACKED, 9.6 MB   - included to show these differ
REM
REM  THE FOUR PASSES
REM    a  fp32 baseline                       what deployment costs today
REM    b  --drop-latent                       cause 2, the duplicate fp32 copy
REM    c  --drop-latent --int8-store          cause 1, partially
REM    d  + --unpack-cache                    unpack once per unique module
REM
REM  PREDICTIONS, fixed in advance (plan P066 s2.2)
REM    P1  drop-latent lands at 0.50 to 0.55 of fp32
REM    P2  plus int8 lands at about 0.14 to 0.15 of fp32
REM    P3  mC_d36_ag4 STILL misses 40 MB, landing near 90 MB, because the
REM        embedding stays fp32 at 34.3 MB
REM    P4  the packed winner and the resident winner are DIFFERENT models
REM    P5  the unpack-cache logit gate reads exactly 0.000e+00
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Speed - only 32 tokens are generated, nowhere near steady state.
REM    Quality - the int8 path's loss cost needs a separate eval.
REM    Actual cache behaviour - RSS and tensor sums are byte accounting, not
REM    hit rates. That gap is plan P066 stage 4 and we have no tool for it.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

set TL_NOPAUSE=1
set TL_LOGNAME=P066_stage0_residency
set TL_MODELS=mC_wsd mC_initonly mC_d36_ag4 mC_p1c1g16
set TL_SKIP_CUDA=1

echo.
echo.
python scripts\runlog.py --name P066_stage0_residency --note "=============================================================================" "P066 stage 0   resident memory on the deployment path   NO TRAINING   CPU" "The target is RESIDENT, not packed. packed already fits; resident is 9.5x over." "=============================================================================="
echo.

python scripts\runlog.py --name P066_stage0_residency --note "[1/4] fp32 baseline - what deployment costs today"
set TL_EXTRA=
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] fp32 pass failed - continuing

echo.
python scripts\runlog.py --name P066_stage0_residency --note "[2/4] --drop-latent - cause 2, the duplicate fp32 copy. Logit gate must stay clean."
set TL_EXTRA=--drop-latent
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] drop-latent pass failed - continuing

echo.
python scripts\runlog.py --name P066_stage0_residency --note "[3/4] --drop-latent --int8-store - cause 1, partially. Ternary 4 bytes down to 1."
set TL_EXTRA=--drop-latent --int8-store
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] int8 pass failed - continuing

echo.
python scripts\runlog.py --name P066_stage0_residency --note "[4/4] plus --unpack-cache - unpack once per unique module. attn-group should raise the hit rate."
set TL_EXTRA=--drop-latent --int8-store --unpack-cache
call scripts\batch\tool_mem_profile.bat
if errorlevel 1 echo [WARN] unpack-cache pass failed - continuing

echo.
echo.
python scripts\runlog.py --name P066_stage0_residency --note "=============================================================================" "READ IN THIS ORDER" "1. pass 2 and 4 logit gates. A nonzero difference means a BUG, not a saving." "2. the fp32 column for all four models. That is today's deployment cost." "3. ratio of each pass to fp32, against P1 and P2." "4. does mC_d36_ag4 reach 40 MB in pass 4? P3 says no, and says why -" "   the embedding is 34.3 MB and none of these passes touch it." "5. compare the packed winner with the resident winner. If they differ," "   trap 1 is demonstrated on our own best models." "REMINDER  RSS overstates, tensor sums understate. Read both, never one." "REMINDER  packed is reference only. The judgement number is runtime_mb." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
