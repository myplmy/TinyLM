@echo off
REM ===== LOGGING (added 2026-07-31) =====
REM   Every python command below is run through scripts\runlog.py, which prints to the
REM   console in real time AND appends to test_result\log_YYYYMMDD_NAME.txt line by line,
REM   flushing and fsync-ing as it goes. If this batch dies halfway, or the machine loses
REM   power, everything up to the last couple of seconds is already on disk.
REM   Losing the log of a long run costs the whole run, so this is not optional.
REM   Exit codes pass through unchanged, so every `if errorlevel` below still works.

REM ===== P001B : LR re-search at the CURRENT effective batch =====
REM   Plan: test_plan\P001 section P001B
REM
REM WHY RE-SEARCH: lr 1e-3 was fixed back in the v5 era, for two reasons that BOTH expired.
REM   (a) it was lowered to stop divergence. QK-norm and the NaN guard landed after that,
REM       and grad_max now sits near 1.0 on real runs. The ceiling that forced 1e-3 is gone.
REM   (b) P001's lrfind ran WITHOUT --accum, so it used the CLI default 8 = effective batch
REM       65K tokens. Our standard is --accum 16 = 131K. Optimal LR scales with batch size,
REM       so the number we are using was measured at HALF the batch we actually train at.
REM   Cost is under an hour. P033 (18-28h) would be spent at whatever LR we pick here.
REM
REM ***** READ BEFORE TRUSTING THE OUTPUT - THREE REAL LIMITS *****
REM   1. lr_finder._make() calls build_config(preset, arch, seq, ckpt) ONLY. It does NOT
REM      apply --mlp-group or --sparse34. So this measures plain dense / plain tied,
REM      NOT the mA (g4+s34) configuration. Treat the tied number as an upper reference.
REM   2. It runs at set_anneal(0.0) = full FP, no ternary. Deliberate (divergence happened
REM      pre-anneal historically) but it says NOTHING about stability inside the QAT phase.
REM   3. The range test uses safety=3.0, and it is NOT exposed as a flag. In P001 it
REM      suggested 5.6e-4 while the real runs happily took 1e-3 - so range is calibrated
REM      CONSERVATIVELY for this repo. TRUST THE GRID, use range only for the ceiling.
REM
REM ***** WHY THE COPY LINES EXIST *****
REM   lr_find() always writes runs\logs\lrfind.json - a FIXED name, no tag. Four
REM   invocations would leave only the last one. Each run below is copied to its own
REM   file immediately. Do not remove those copy lines.
REM
REM DATA: uses --tokens 300M so it reuses the existing canonical cache. No new prepare,
REM   no new download. Pool size is irrelevant here - we measure divergence, not quality.
REM
REM COST: about 18 min per invocation (range 150 steps + grid 5x60 steps at accum 16).
REM   Three invocations = roughly 1 hour. No checkpoints written, runs\ckpt untouched.
REM
REM ERRORLEVEL POLICY: independent measurements, failures only warn.

echo ============================================================
echo [P001B] LR re-search at accum 16 (effective batch 131K)
python scripts\runlog.py --name P001B --note "[P001B] LR re-search at accum 16 (effective batch 131K)"
echo ============================================================

echo.
echo [pre] static attribute check
python scripts\runlog.py --name P001B --note "[pre] static attribute check"
python scripts\runlog.py --name P001B -- python scripts\check_attrs.py
if errorlevel 1 echo [WARN] attribute check found problems - FIX THEM FIRST

echo.
echo ============================================================
echo [1/3] DENSE at accum 16   ***THE ONE THAT MATTERS MOST***
python scripts\runlog.py --name P001B --note "[1/3] DENSE at accum 16   ***THE ONE THAT MATTERS MOST***"
echo   dense is the teacher. Every KD run inherits its quality, so if any LR is wrong
echo   this is the expensive one. Also the P033 dense baseline runs 17 hours.
echo ============================================================
python scripts\runlog.py --name P001B -- python run100m.py lrfind --arch dense --preset m100 --data ko-en --tokens 300M --method both --micro-bs 8 --seq 1024 --accum 16 --lrs 6e-4,1e-3,2e-3,3e-3,4e-3 --lrfind-steps 150
if errorlevel 1 (echo [WARN] dense lrfind failed - continuing) else (copy /Y runs\logs\lrfind.json runs\logs\lrfind_P001B_dense_a16.json)

echo.
echo ============================================================
echo [2/3] TIED at accum 16
python scripts\runlog.py --name P001B --note "[2/3] TIED at accum 16"
echo   the student. Tied shares MLP weights, so per-weight gradient magnitude differs
echo   from dense and the optimum need not be the same number.
echo ============================================================
python scripts\runlog.py --name P001B -- python run100m.py lrfind --arch tied --preset m100 --data ko-en --tokens 300M --method both --micro-bs 8 --seq 1024 --accum 16 --lrs 6e-4,1e-3,2e-3,3e-3,4e-3 --lrfind-steps 150
if errorlevel 1 (echo [WARN] tied lrfind failed - continuing) else (copy /Y runs\logs\lrfind.json runs\logs\lrfind_P001B_tied_a16.json)

echo.
echo ============================================================
echo [3/3] CONTROL - dense at accum 8, reproducing P001's condition
python scripts\runlog.py --name P001B --note "[3/3] CONTROL - dense at accum 8, reproducing P001's condition"
echo   This is what validates the whole exercise. If accum 8 lands near P001's
echo   1.7e-3 divergence and accum 16 lands HIGHER, the batch-size dependence is
echo   demonstrated rather than assumed. If the two come out the SAME, then claim (b)
echo   above was wrong and only claim (a) justifies any change. Either way we learn.
echo ============================================================
python scripts\runlog.py --name P001B -- python run100m.py lrfind --arch dense --preset m100 --data ko-en --tokens 300M --method both --micro-bs 8 --seq 1024 --accum 8 --lrs 6e-4,1e-3,2e-3,3e-3,4e-3 --lrfind-steps 150
if errorlevel 1 (echo [WARN] control lrfind failed - continuing) else (copy /Y runs\logs\lrfind.json runs\logs\lrfind_P001B_dense_a8.json)

echo.
echo ============================================================
echo WHAT TO RECORD - send back all three files
echo   runs\logs\lrfind_P001B_dense_a16.json
echo   runs\logs\lrfind_P001B_tied_a16.json
echo   runs\logs\lrfind_P001B_dense_a8.json
echo   plus the console text (the per-step lines are not all in the json)
echo.
echo HOW TO READ IT
echo   grid  : the largest lr with grad_max under 10 AND loss decreasing. This is the
echo           number to act on. Compare its suggested_lr against 1e-3.
echo   range : diverge_lr is a useful CEILING. Ignore its suggested_lr - safety=3.0
echo           already proved too conservative once (P001: suggested 5.6e-4, reality 1e-3).
echo.
echo DECISION RULE
echo   grid picks 1e-3            -^> current LR confirmed. Close this out, P033 unblocked.
echo   grid picks ABOVE 1e-3      -^> headroom exists, but DO NOT adopt it from 60 steps.
echo                                 Short runs read speed only, never quality (CLAUDE.md).
echo                                 Adopt only after one full 300M run beats p6d 3.7045
echo                                 by more than 0.024. That run is the real evidence.
echo   grid picks BELOW 1e-3      -^> we have been training slightly too hot the whole time.
echo                                 Check grad_max in past json before believing it.
echo   accum 8 and 16 differ      -^> batch-dependence confirmed. Then P033's larger batch
echo                                 needs its OWN lrfind, not this number.
echo.
echo LIMITS: no mlp-group / no sparse34 (plain arch only) / full FP, no ternary anneal /
echo   safety=3.0 not adjustable from the CLI / this does not measure quality at all.
echo ================================================================
echo done.
pause
