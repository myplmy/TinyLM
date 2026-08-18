@echo off
REM =============================================================================
REM  P060 stage A2  -  which SDPA backend is actually alive on this build?
REM                    (NO TRAINING, seconds)
REM
REM  WHY A2 EXISTS  (user question, 2026-08-14)
REM    Stage A probed the three backends with enable_gqa=True ONLY. It never
REM    probed enable_gqa=False, which is our ORDINARY TRAINING PATH. So the two
REM    log lines below could not be told apart:
REM
REM      "Torch was not compiled with flash attention"
REM          -^> the build has no FLASH at all, nothing to do with enable_gqa
REM      "both fused kernels require query, key and value to have the same
REM       num_heads"
REM          -^> rejected BECAUSE of enable_gqa
REM
REM    Without a baseline the rejection in result 046 cannot be attributed.
REM
REM  !! AND THERE IS A BIGGER QUESTION HIDING HERE
REM    What backend does our NORMAL training path use right now?
REM    If that is MATH too, then every run we have ever done has been on the
REM    unfused kernel, and that is a far larger problem than F-1. We have never
REM    checked. This batch checks, in seconds.
REM
REM  WHAT IT PRINTS
REM    a 2 x 4 matrix: enable_gqa off/on  x  FLASH / MEM_EFFICIENT / CUDNN / MATH
REM    plus the default-dispatch speed ratio, to compare against the 1.958x
REM    ms/step ratio measured in result 046.
REM
REM  PREDICTIONS, fixed in advance (plan P060 s4.1)
REM    A2-P1  off has MEM_EFFICIENT      - if not, our whole training is MATH
REM    A2-P2  off rejects FLASH          - the build says it is not compiled
REM    A2-P3  on has NO fused backend    - reproduces result 046
REM    A2-P4  speed ratio near 1.9x      - matches the training ms/step ratio
REM
REM  COST: seconds, one small tensor. Safe to run any time.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P060_stageA2_backends --note "=============================================================================" "P060 stage A2   SDPA backend availability matrix   seconds   NO TRAINING" "Stage A only probed enable_gqa=True, so the rejection could not be attributed." "The bigger question: is our ORDINARY training path also on MATH?" "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P060_stageA2_backends --note "[1/2] standard training shape - micro-bs 8, seq 1024, 12 q heads, 3 kv heads"
python scripts\runlog.py --name P060_stageA2_backends -- python scripts\diag_sdpa_backends.py --bs 8 --seq 1024 --q-heads 12 --kv-heads 3 --head-dim 64
if errorlevel 1 echo [WARN] standard shape probe failed - continuing

echo.
python scripts\runlog.py --name P060_stageA2_backends --note "[2/2] smaller shape - some kernels have size or alignment constraints, so a rejection at one shape is not a rejection at all shapes"
python scripts\runlog.py --name P060_stageA2_backends -- python scripts\diag_sdpa_backends.py --bs 1 --seq 128 --q-heads 12 --kv-heads 3 --head-dim 64
if errorlevel 1 echo [WARN] small shape probe failed - continuing

echo.
echo.
python scripts\runlog.py --name P060_stageA2_backends --note "=============================================================================" "READ IN THIS ORDER" "1. the off column FIRST. That is our training path, not the experiment." "   If only MATH is OK there, stop and read the verdict block - it is bigger" "   than F-1 and it needs its own plan (P060 stage C, torch build)." "2. the on column - reproduces result 046 and completes the attribution." "3. the speed ratio against 1.958x from the 250 step pair." "4. compare the two shapes. A kernel rejected at one shape may work at another." "LIMIT: this measures kernel availability and relative speed only." "Correctness is G-a in diag_gqa_equiv.py, already passed at 2.831e-06." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
