@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P052_seed_replicate.bat -- [P052] repeat the g16 comparison on a second
REM                                 seed, so REVIEW2 can talk about ARCHITECTURE.
REM  Plan: test_plan\P052
REM =============================================================================
REM
REM PRECONDITION: --seed exists (default 1337, val crop is pinned at 99).
REM   Controls mC_wsd and mC_g16 are NOT retrained - they are the seed 1337 arms.
REM
REM ***LONG UNATTENDED RUN. ABOUT 7 GPU HOURS for two runs.***
REM   The two training runs are INDEPENDENT - one failing leaves the other usable.
REM
REM WHY - the thing we are about to adopt rests on ONE seed
REM   REVIEW2 is about to promote mC_g16. The evidence is result 029:
REM   paired delta +0.0161, SE 0.0005, inside the 0.024 resolution.
REM   ***But that SE is the wrong uncertainty for the claim.***
REM     eval sampling noise   SE 0.0005   removed by paired_eval
REM     training seed noise   sigma 0.012 ***NOT removed***
REM   Two training runs carry seed noise twice, so the scale is
REM   sigma x sqrt(2) = about 0.017 - ***the same size as the +0.0161 we are
REM   about to build a decision on.***
REM
REM   What we actually know today:
REM     'these two checkpoints differ by 0.0161'          TRUE
REM     'the g16 architecture costs 0.0161'               NOT ESTABLISHED
REM   ***Result 029 section 3 already wrote that down*** and then nobody ran the
REM   second seed. If REVIEW2 ships first, the review inherits the limitation.
REM
REM ***WHY TWO RUNS AND NOT ONE***
REM   Running only mC_g16_s2 against mC_wsd (seed 1337) confounds architecture
REM   with seed. Both arms must move to the new seed.
REM     delta1 = paired(mC_wsd   , mC_g16   )  = +0.0161   result 029, seed 1337
REM     delta2 = paired(mC_wsd_s2, mC_g16_s2) = ?          seed 2024
REM   ***How well delta2 reproduces delta1 is the whole experiment.***
REM
REM ***PREDICTIONS - WRITTEN BEFORE THE RUN (plan section 3)***
REM   P1 delta2 is positive, +0.005 to +0.030. An independent old measurement
REM      (t_kd_g16 - t_kd_g8 = +0.0128, different pool and schedule) already
REM      pointed the same way.
REM   P2 abs(delta2 - delta1) under 0.017. If it is larger, sigma is bigger than
REM      0.012 IN THIS CONDITION and ***the repo's whole 0.024 resolution needs
REM      re-deriving*** - result 012 measured sigma on p6d, dense, cosine.
REM   P3 mean(delta1, delta2) under 0.024, so the adoption survives.
REM   P4 mC_wsd_s2 lands within 0.024 of mC_wsd in absolute loss.
REM
REM ***THE SUCCESS CASE IS BORING ON PURPOSE.*** Nothing changes if it works.
REM   Seven hours is cheaper than REVIEW2 confirming something irreproducible.
REM
REM ***STEP [4/4] IS THE CONTROL*** (ai_dev_tool\03 section 4.1): mC_wsd against
REM   mC_wsd_s2 is the SAME architecture with only the seed moved, so that
REM   number IS sigma x sqrt(2) measured in the mC / wsd / KD condition. It
REM   re-checks result 012, which was measured somewhere else.
REM
REM ***GATE G-a*** - the log header must say  seed=2024. Without it the two runs
REM   just retrained the same thing and seven hours are gone.
REM
REM ERRORLEVEL POLICY: the two training runs are independent - WARN and continue.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_g16.pt goto NOG16
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

echo =============================================================
echo [P052] second seed for the g16 comparison  (about 7 h, two runs)
echo =============================================================
python scripts\runlog.py --name P052_seed_replicate --note "[P052] seed 2024 replication of the mC_wsd vs mC_g16 comparison. Turns a two-checkpoint claim into an architecture claim, before REVIEW2 relies on it."

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo =============================================================
echo [1/4] arm A - g8 baseline, seed 2024
echo =============================================================
python scripts\runlog.py --name P052_seed_replicate --note "[1/4] arm A : mC_wsd_s2 (g8 preset default), --seed 2024"
python scripts\runlog.py --name P052_seed_replicate -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --kd --kd-every 4 --init-from --tag mC_wsd_s2
if errorlevel 1 echo [WARN] arm A failed - continuing, arm B is independent

echo.
echo =============================================================
echo [2/4] arm B - g16, seed 2024
echo =============================================================
python scripts\runlog.py --name P052_seed_replicate --note "[2/4] arm B : mC_g16_s2 (--mlp-group 16), --seed 2024"
python scripts\runlog.py --name P052_seed_replicate -- python run100m.py train --preset m100R1c --arch tied --mlp-group 16 --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --kd --kd-every 4 --init-from --tag mC_g16_s2
if errorlevel 1 echo [WARN] arm B failed - continuing

echo.
echo =============================================================
echo [3/4] delta2 - the seed 2024 architecture comparison
echo =============================================================
python scripts\runlog.py --name P052_seed_replicate --note "[3/4] delta2 = paired(mC_wsd_s2, mC_g16_s2)"
python scripts\runlog.py --name P052_seed_replicate -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd_s2 mC_g16_s2
if errorlevel 1 echo [WARN] paired_eval failed - checkpoints are on disk, re-run this step alone

echo.
echo =============================================================
echo [4/4] CONTROL - same architecture, seed only. This IS sigma x sqrt(2).
echo =============================================================
python scripts\runlog.py --name P052_seed_replicate --note "[4/4] CONTROL : paired(mC_wsd, mC_wsd_s2) - same architecture, seed only"
python scripts\runlog.py --name P052_seed_replicate -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_wsd_s2 mC_g16 mC_g16_s2
if errorlevel 1 echo [WARN] paired_eval failed - re-run this step alone

python scripts\runlog.py --name P052_seed_replicate --note "=================================================================" "WHAT TO RECORD" "  0. ***seed=2024 in BOTH run headers.*** Without it there is no experiment." "  1. delta2 from step [3], with SE and t." "  2. the four-way table from step [4]. In particular:" "       mC_wsd    vs mC_wsd_s2   = seed noise, g8 arm" "       mC_g16    vs mC_g16_s2   = seed noise, g16 arm" "     ***Those two ARE sigma x sqrt(2) in this condition.***" "  3. final val for both new runs, NOT best." "  4. grad_max from the json for both. Over 10 makes that arm unusable." "  5. wall clock, for the record." "" "HOW TO READ IT" "  delta2 positive and abs(delta2 - 0.0161) under 0.017" "      -^> ***the g16 verdict survives a second seed.*** REVIEW2 may now say" "         'architecture', not 'these two checkpoints'. Quote BOTH deltas." "  delta2 changes sign" "      -^> ***the g16 cost is not measurable at this budget.*** REVIEW2 must" "         say 'indistinguishable', which is still an adoption argument -" "         g16 buys packed -7.4 percent for no measurable loss." "  abs(delta2 - delta1) over 0.017" "      -^> sigma is LARGER than 0.012 here. ***That is a repo-wide finding***" "         - the 0.024 resolution came from result 012 on p6d/dense/cosine, and" "         every borderline verdict since would need re-reading. Report it as" "         the headline, not as a footnote." "  mean of the two deltas over 0.024" "      -^> withdraw the g16 adoption recommendation." "" "LIMITS: two seeds. abs(delta2 - delta1) is ONE SAMPLE of the seed spread, not" "  an estimate of sigma with useful precision. The parent and the KD teacher are" "  identical across all arms, so this measures the STUDENT's training noise," "  not the pipeline's. val crop seed stays pinned at 99 by design." "================================================================="
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
echo [STOP] runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt is missing (seed 1337 control).
if not defined TL_NOPAUSE pause
exit /b 5

:NOG16
echo.
echo [STOP] runs\ckpt\m100R1c_ko-en_300M_mC_g16.pt is missing (seed 1337 g16 arm).
if not defined TL_NOPAUSE pause
exit /b 5

:NOPARENT
echo.
echo [STOP] parent runs\ckpt\m100_ko-en_300M_dense.pt is missing.
if not defined TL_NOPAUSE pause
exit /b 5

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
