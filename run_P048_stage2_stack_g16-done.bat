@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P048_stage2_stack_g16.bat -- [P048] stage 2. g16 STACKED on prelude/coda 1+1
REM  Plan: test_plan\P048 section 6 / Result 032 section 4
REM =============================================================================
REM
REM PRECONDITION: preset m100R1q (added 2026-08-07). Parent m100_ko-en_300M_dense.pt.
REM   n_middle=16 with g16 means mid_mlps[0..15] maps exactly, so the parent works.
REM
REM ***LONG UNATTENDED RUN.*** About 3.0 GPU hours (18 layers, slightly faster again).
REM
REM WHY - THIS RUN EXISTS TO TEST A PREDICTION, NOT TO WIN
REM   Result 032 section 4 found that g16 and prelude/coda 1+1 sit on the SAME
REM   efficiency line - 0.0167 vs 0.0199 nats per packed MB, and the ratio is
REM   1.19 to 1.20 on all three of packed, fp32 residency, and ternary params.
REM   That suggests a LOCAL law: about 0.0035 to 0.0041 nats per million unique
REM   ternary parameters, inside the KD plus parent-init pipeline.
REM
REM   Stacking both gives unique MLPs 6 -^> 3, ternary 54.85 -^> 38.04M:
REM     packed        13.050 -^> 9.61 MB  = -26.3 percent
REM     fp32 residency 451.5 -^> 323.2 MB = -28.4 percent
REM     int8 residency 86.94 -^> 70.38 MB = -19.0 percent
REM
REM ***THE PREDICTION - WRITTEN BEFORE THE RUN***
REM   16.81M unique ternary removed times 0.0037 = ***delta about +0.062***
REM   Additive  (+0.055 to +0.070) -^> the local linearisation holds. We can now
REM                                   PRICE memory levers before running them.
REM   Less      (under +0.055)     -^> the two levers OVERLAP - they take the same
REM                                   degree of freedom. Then stacking is a bargain.
REM   More      (over +0.070)      -^> they INTERACT. Then levers must be measured
REM                                   in combination, not priced separately.
REM   ***All three outcomes are informative. There is no failure mode here.***
REM   Simple sum of the measured parts is +0.0161 + 0.0493 = +0.0654, which is
REM   inside the additive band - so additive and simple-sum are not distinguishable
REM   by this run. Say so in the result rather than claiming precision.
REM
REM ***CONFOUND CARRIED OVER FROM STAGE 1: depth 20 to 18.*** Same as m100R1p.
REM   Do not attribute a bad delta to tying or to prelude/coda alone.
REM
REM ***G-init GATE - CHECK BEFORE READING THE DELTA***
REM   Expect the four '[init] ' structure-mismatch lines (student 18 layers,
REM   prelude 1, coda 1 vs teacher 20/2/2), the header 'layers=1+16+1  MLP g=16',
REM   'tied MLP one group ... 16 times', and report() ternary 38.0M.
REM   If report() still says 42.8M then g16 did not take; if 54.9M then neither did.
REM
REM CONTROL IS NOT RE-TRAINED: mC_wsd (result 024). Conditions must match:
REM   sched=wsd / anneal_end=0.80 / kd_every=4 / pool 600M exact / seed 1337.
REM   Initialisation is a PARTIAL transplant, same as stage 1.
REM
REM MEASUREMENT: quality only. Read 'final', never 'best'. grad_max from json -
REM   ***that is not optional***: result 030 had grad_max 19.32 while the printed
REM   ^|g^| was the lowest of the night, and it flipped a verdict.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

echo =============================================================
echo [P048-2] g16 stacked on prelude/coda 1+1 : unique MLP 6 to 3
echo   PREDICTION delta about +0.062 (local linear from result 032)
echo   packed -26.3 pct / fp32 residency -28.4 pct
echo =============================================================
python scripts\runlog.py --name P048_mC_p1c1g16 --note "[P048 stage 2] g16 stacked on prelude/coda 1+1 : unique MLP 6 to 3, PREDICTION +0.062"

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo =============================================================
echo [1/2] train  preset m100R1q (1 + 16 g16 + 1 = 18 layers, unique MLP 3)
echo =============================================================
python scripts\runlog.py --name P048_mC_p1c1g16 --note "[1/2] train preset m100R1q"
python scripts\runlog.py --name P048_mC_p1c1g16 -- python run100m.py train --preset m100R1q --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --tag mC_p1c1g16
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [2/2] paired comparison against mC_wsd and against mC_p1c1
echo =============================================================
python scripts\runlog.py --name P048_mC_p1c1g16 --note "[2/2] paired vs mC_wsd and vs mC_p1c1"
python scripts\runlog.py --name P048_mC_p1c1g16 -- python scripts\paired_eval.py --preset m100R1q --data ko-en --tokens 300M --models mC_wsd mC_p1c1 mC_p1c1g16
if errorlevel 1 echo [WARN] paired_eval failed - checkpoint is on disk, re-run this step alone

python scripts\runlog.py --name P048_mC_p1c1g16 --note "=================================================================" "WHAT TO RECORD" "  0. ***G-init FIRST.*** four [init] lines, header layers=1+16+1 MLP g=16," "     one group reused 16 times, and report() ternary 38.0M." "     42.8M means g16 did not take. 54.9M means nothing took." "  1. ***grad_max from the json, not the printed ^|g^|.***" "     Result 030 had printed ^|g^| 0.43 and grad_max 19.32. Not optional." "  2. paired delta vs mC_wsd (the prediction target) AND vs mC_p1c1" "     (the incremental cost of g16 on top of 1+1)." "  3. report() packed and residency against the computed 9.61 MB and 323.2 MB." "  4. ms/step and wall clock." "  5. header conditions vs mC_wsd. Any difference INVALIDATES the delta." "" "HOW TO READ IT - the prediction was +0.062" "  +0.055 to +0.070  -^> ***local linearisation holds.*** We can price memory" "                       levers before spending GPU on them. That is the win." "  under +0.055      -^> the levers OVERLAP. Stacking is cheaper than the sum," "                       so take both." "  over +0.070       -^> they INTERACT. Levers must be measured in combination;" "                       do not price them separately again." "  ***Note: simple sum of parts is +0.0654, inside the additive band.*** This" "  run cannot separate 'additive' from 'simple sum'. Do not claim it does." "" "  Separately: delta vs mC_p1c1 should be near +0.0161 (g16's cost measured on" "  a different base). If it is very different, the cost of g16 DEPENDS on the" "  base, which is itself the interaction signal." "" "LIMITS: depth 20 to 18 confounded (carried from stage 1). Partial parent" "  transplant. One seed. The memory figures are COMPUTED until report() confirms." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:BADKWARGS
echo.
echo [STOP] cli.py passes a keyword its target function does not accept.
if not defined TL_NOPAUSE pause
exit /b 6

:NOCTRL
echo.
echo [STOP] control runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt is missing.
if not defined TL_NOPAUSE pause
exit /b 5

:NOPARENT
echo.
echo [STOP] parent runs\ckpt\m100_ko-en_300M_dense.pt is missing (needed by --init-from).
if not defined TL_NOPAUSE pause
exit /b 7

:TRAINBAD
echo.
echo [STOP] training failed. Nothing to compare.
if not defined TL_NOPAUSE pause
exit /b 4

:BADROOT
echo.
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
