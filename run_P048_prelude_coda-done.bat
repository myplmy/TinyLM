@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P048_prelude_coda.bat -- [P048] prelude/coda 2+2 to 1+1
REM  Plan: test_plan\P048 (prelude coda 1+1, largest remaining packed lever)
REM =============================================================================
REM
REM PRECONDITION: preset m100R1p exists (added 2026-08-07, config.py).
REM   Parent dense runs\ckpt\m100_ko-en_300M_dense.pt must exist (PRESET_PARENT).
REM
REM ***LONG UNATTENDED RUN. START IT AND WALK AWAY.*** About 3.2 GPU hours.
REM   Slightly faster than P045/P046 because the model is 18 layers, not 20.
REM
REM WHY THIS IS THE BIGGEST REMAINING PACKED LEVER
REM   prelude and coda MLPs are NOT tied - each of those layers owns a whole
REM   unique MLP, while 8 middle layers share one. So 20 percent of the layers
REM   (4 of 20) hold 67 percent of the unique MLPs (4 of 6).
REM   Going 1+1 takes unique MLPs 6 to 4:
REM     ternary   54.85M to 42.76M   = -22.0 percent
REM     packed    12.93  to 10.47 MB = -19.0 percent   ^<- largest lever we have
REM     int8 res  86.70  to 74.81 MB = -13.7 percent
REM   Computed with the same mem_breakdown formula that reproduces the MEASURED
REM   m100=64.29M, m100R1c=54.85M and 86.9MB. The formula was checked first.
REM
REM ***THE BIGGEST RISK - RESULT 002 POINTS THE OTHER WAY***
REM   Result 002 called prelude/coda the single largest gain. But that comparison
REM   was against 0+0 (everything tied), NOT against 1+1.
REM     0+0 ---------- 1+1 ---------- 2+2
REM     002 says bad   THIS RUN       002 says good
REM   1+1 is an unmeasured middle point. If the gain is linear, 1+1 is half as
REM   bad. If it saturates, 1+1 is nearly as good as 2+2. We do not know, and
REM   that is the whole point of the run.
REM
REM ***CONFOUND YOU MUST NOT FORGET: DEPTH DROPS 20 to 18.***
REM   n_prelude=1 and n_coda=1 with n_middle=16 gives 18 layers. Keeping 20 would
REM   need n_middle=18 with g9, and then init_from_dense indexes mid_mlps[17]
REM   while the m100 parent only has 16 - IndexError. Holding depth costs a new
REM   dense parent (+3.5h). We chose parent reuse.
REM   -^> If the delta is bad, the cause MAY BE DEPTH. Do not attribute it to
REM      prelude/coda alone. Plan section 7.
REM
REM ***EXPECTATION - WRITTEN BEFORE THE RUN SO IT CANNOT BE RATIONALISED***
REM   P1 paired delta +0.02 to +0.06 (worse).
REM      ACCEPT if under +0.02 - residency -13.7 percent easily wins there.
REM      CLOSE THE A-6 AXIS if above +0.10.
REM   P2 worse than P045 g16 (tying is an extension of a known trajectory;
REM      prelude/coda removes layers with a DIFFERENT ROLE).
REM   P3 training about 10 percent faster (18/20 layers).
REM   P4 grad_max roughly unchanged (this is not a conditioning device, unlike
REM      the FiLM of result 027 which doubled it).
REM   P5 ***the [init] warning lines MUST appear*** - see below.
REM
REM ***G-init GATE - CHECK THIS BEFORE READING ANY DELTA***
REM   Because student is 18 layers and the parent is 20, init_from_dense does a
REM   PARTIAL transplant: zip stops at 18, so the student's coda layer receives
REM   a MIDDLE layer's weights, and pre_mlps/coda_mlps take only the parent's
REM   first one. That is intended, but it must not be silent - a guard added
REM   2026-08-07 prints four '[init] ' warning lines.
REM   If those four lines are ABSENT, the preset did not take and the run is
REM   worthless. Also confirm report() shows ternary 42.76M, not 54.85M.
REM
REM ***THE CONTROL IS NOT RE-TRAINED.*** mC_wsd (result 024) is the same
REM   configuration except preset. Condition matching is therefore critical:
REM   sched=wsd / anneal_end=0.80 / kd_every=4 / pool 600M exact / seed 1337.
REM   Note the initialisation condition DIFFERS (partial transplant), so part of
REM   the delta may be init rather than architecture. This run cannot separate them.
REM
REM MEASUREMENT: quality only. Wall clock is NOT comparable across sessions.
REM   Read 'final', never 'best' (result 015 flipped a sign). grad_max from json.
REM
REM ERRORLEVEL POLICY: training is the prerequisite, so it stops the batch.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

echo =============================================================
echo [P048] prelude/coda 2+2 to 1+1 : largest remaining packed lever
echo   unique MLP 6 to 4 / ternary -22.0 pct / packed -19.0 pct
echo   WATCH FOR the four [init] warning lines - that is the G-init gate
echo =============================================================
python scripts\runlog.py --name P048_mC_p1c1 --note "[P048] prelude/coda 1+1 : unique MLP 6 to 4"

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo =============================================================
echo [1/2] train  preset m100R1p (1 + 16 g8 + 1 = 18 layers)
echo =============================================================
python scripts\runlog.py --name P048_mC_p1c1 --note "[1/2] train preset m100R1p 18 layers"
python scripts\runlog.py --name P048_mC_p1c1 -- python run100m.py train --preset m100R1p --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --tag mC_p1c1
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [2/2] paired comparison against mC_wsd
echo =============================================================
python scripts\runlog.py --name P048_mC_p1c1 --note "[2/2] paired comparison against mC_wsd"
python scripts\runlog.py --name P048_mC_p1c1 -- python scripts\paired_eval.py --preset m100R1p --data ko-en --tokens 300M --models mC_wsd mC_p1c1
if errorlevel 1 echo [WARN] paired_eval failed - checkpoint is on disk, re-run this step alone

python scripts\runlog.py --name P048_mC_p1c1 --note "=================================================================" "WHAT TO RECORD" "  0. ***G-init FIRST.*** Four '[init] ' warning lines about structure" "     mismatch, AND report() ternary 42.76M. If either is missing the preset" "     did not take - stop and report that instead of the delta." "  1. final val, NOT best." "  2. the paired_eval delta and t value against mC_wsd." "  3. grad_max from the json (P4 says roughly unchanged)." "  4. the report() block - packed MB and residency MB, against the computed" "     10.47 MB packed and 74.81 MB int8 residency." "  5. ms/step, for P3 (about 10 percent faster on 18 vs 20 layers)." "  6. the header conditions. If any differ from mC_wsd the delta is INVALID." "" "HOW TO READ IT" "  delta under +0.02" "      -^> ACCEPT. residency -13.7 pct and packed -19.0 pct for free." "         Next: stage 2, stack with --emb-rank 128 for -32.6 pct residency." "  +0.02 to +0.10" "      -^> hold. Other levers first. Revisit only if RAM-bound." "  above +0.10" "      -^> CLOSE THE A-6 AXIS. prelude/coda matter by EXISTENCE, not count." "         That is a real answer, not a failure." "" "LIMITS: ***depth 20 to 18 is confounded*** - a bad delta may be depth, not" "  prelude/coda. Separating it needs a new dense parent (+3.5h) and is only" "  worth paying if this gate fails. Parent init is a PARTIAL transplant so the" "  init condition differs from mC_wsd. One seed. Result 002's numbers were" "  measured WITHOUT KD and on a different pool, and result 027 showed KD" "  already occupies the per-layer conditioning role - so 002's magnitude does" "  not transfer. The memory figures are COMPUTED, not measured." "================================================================="
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
