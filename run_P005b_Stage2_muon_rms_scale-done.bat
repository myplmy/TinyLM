@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P005b_Stage2_muon_rms_scale.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Newton-Schulz erases the size of the update, so it has to be put back.
REM     Two reference implementations put back DIFFERENT amounts:
REM       jordan  max(1, out/in) ** 0.5           = what we have always used
REM       rms     0.2 * sqrt(max(out, in))        = Essential AI 2505.02222
REM                                                  footnote 2, Kimi K2 Alg 1
REM     Measured on our five actual shapes, rms is 3.20 to 9.05 times jordan,
REM     and the SPREAD across shapes is 2.83x. A uniform --muon-lr-mult cannot
REM     express that, which is the whole reason --muon-scale exists.
REM
REM   TWO MULTIPLIERS THAT BRACKET THE JORDAN OPTIMUM - THIS IS THE POINT
REM     Revised 2026-09-10 (session 2) BEFORE any run. Two facts moved:
REM       a. P005 stage 3 found jordan x20 beats x15 by 0.00656 at 2289 steps.
REM       b. Weighted by parameter count the rms/jordan ratio is about 6.4
REM          (60 of 73 matrices sit at 5.54, twelve at 9.05, one at 3.20).
REM     So rms x1 is about jordan x6 and rms x2 about jordan x13 - both BELOW
REM     the jordan optimum. The first design (x1 and x2) would most likely have
REM     lost for a multiplier reason and been misread as a convention verdict.
REM     rms x2 (about jordan x13) and rms x4 (about jordan x26) bracket the
REM     jordan x15 to x20 region instead.
REM
REM   READ IN THIS ORDER
REM     1. The jordan pair is two existing runs, neither is retrained:
REM          d12_cla2_r20_muon15   log val 3.51375
REM          d12_cla2_r20_muon20   log val 3.50719   (the better jordan point)
REM        Ruler 0.0018 (recursion family).
REM     2. Compare the better rms arm with jordan x20 first.
REM     3. Every run prints the shape table before step 0. Read the spread
REM        line: if it is far from 1.00 the two conventions are not a multiple
REM        of each other, and that is the claim this batch rests on.
REM     4. grad_max is expected to move with the effective step size. n_skip
REM        is the stability signal, and it has been 0 at every multiplier so
REM        far - the ceiling has been quality, not divergence (076 section 9.2).
REM
REM   PRE-REGISTERED (plan P005b stage 2)
REM     Better rms arm beats jordan x20 by 0.0036 or more: the convention
REM     becomes the default and --muon-lr-mult stops carrying it by hand.
REM     Better rms arm within the ruler: the conventions differ by a multiple.
REM     Both rms arms lose to jordan x20 beyond the ruler: close the axis.
REM     rms x2 beats rms x4: the rms optimum is below x2 - redo the grid.
REM
REM   COST: about 3.4h, two training runs.   PLAN: test_plan/P005b stage 2
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005b_stage2_muon_rms_scale --note "[1/3] rms scale at multiplier 2 - about jordan x13, below the jordan optimum"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage2_muon_rms_scale -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale rms --muon-lr-mult 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_rms2
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_r20_rms2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage2_muon_rms_scale --note "[2/3] rms scale at multiplier 4 - about jordan x26, above the jordan optimum"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage2_muon_rms_scale -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_rms4
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_rms4
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage2_muon_rms_scale --note "[3/3] paired_eval against jordan x20 and x15 - the verdict is paired (R10)"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage2_muon_rms_scale -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_r20_muon20 d12_cla2_r20_muon15 d12_cla2_r20_rms2 d12_cla2_r20_rms4
if errorlevel 1 echo [WARN] paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage2_muon_rms_scale --note "DONE. Compare the better rms arm to jordan x20 first. Ruler 0.0018. rms x2 vs x4 tells the side."

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
