@echo off
REM ===== P026 cooldown-QAT schedule alignment (m100 dense, ko-en 300M, accum16) =====
REM
REM HYPOTHESIS: ternary anneal finishes at 0.60 of training while WSD LR decay starts at 0.80,
REM   so the model spends 0.60~0.80 doing full-ternary updates at PEAK lr and then has to
REM   re-settle during cooldown. Papers (arXiv:2509.22935, arXiv:2605.25966) say QAT should
REM   OVERLAP the cooldown. If we align them, the same val should be reachable in FEWER steps.
REM
REM NEW FLAGS (default = old behaviour, so nothing else changes):
REM   --anneal-end F   full-ternary reached at progress F   (default 0.60)
REM   --decay-frac F   WSD final decay fraction            (default 0.20)
REM   aligned = --sched wsd --anneal-end 0.80 --decay-frac 0.2
REM   (the trainer prints [sched] ... aligned/not-aligned so you can verify from the log)
REM
REM ALL RUNS: dense, --no-ckpt (13.5GB, minus 17 percent step time per result 007), tagged qb_*
REM           so nothing canonical is overwritten. [1] is the IN-EXPERIMENT control: compare
REM           2,3,4 to IT, not to the canonical dense 3.8241 (different grad-ckpt path, see
REM           result 007 section 2-4).
REM
REM BONUS: [1] vs canonical dense (3.8241) is ALSO our first same-config noise datapoint at
REM        2289 steps. Write that delta down - result 007 showed 0.11 nats of drift at 250 steps
REM        and we still do not know the converged-run number that our +-0.07 rule depends on.
REM
REM COST: 3 x ~81min + 1 x ~69min = about 5.2 hours.
REM NOTE: errors do NOT abort the batch (result 007 lesson) - later runs still execute.

echo === [1/4] control: cosine, anneal 0.60 (current default schedule) ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --sched cosine --anneal-end 0.60 --tag qb_cos
if errorlevel 1 echo [WARN] [1/4] failed - continuing

echo === [2/4] wsd, anneal 0.60 (NOT aligned: ternary done 0.60, decay starts 0.80) ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --sched wsd --anneal-end 0.60 --decay-frac 0.2 --tag qb_wsd60
if errorlevel 1 echo [WARN] [2/4] failed - continuing

echo === [3/4] wsd, anneal 0.80 (ALIGNED: ternary completes as cooldown begins) ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --sched wsd --anneal-end 0.80 --decay-frac 0.2 --tag qb_wsd80
if errorlevel 1 echo [WARN] [3/4] failed - continuing

echo === [4/4] PAYOFF TEST: aligned + 15 percent fewer steps (1946) ===
REM 1946 steps x 131K = 255M tokens. If val matches [1] at 2289 steps, alignment bought us 15pct.
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 1946 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --sched wsd --anneal-end 0.80 --decay-frac 0.2 --tag qb_wsd80_s85
if errorlevel 1 echo [WARN] [4/4] failed - continuing

echo.
echo === Compares ===
python run100m.py compare --tag qb_cos --vs qb_wsd60
python run100m.py compare --tag qb_cos --vs qb_wsd80
python run100m.py compare --tag qb_cos --vs qb_wsd80_s85

echo.
echo ================================================================
echo READ IN THIS ORDER:
echo   1. verify the [sched] line in runs 2/3/4 says aligned where expected
echo   2. [3] vs [1] : does alignment help AT ALL at equal steps?
echo   3. [4] vs [1] : the real question - same val with 15pct fewer steps?
echo   4. [2] vs [1] : how much of any change is just wsd-vs-cosine, not alignment
echo   5. [1] vs canonical dense 3.8241 : same-config drift (noise floor evidence)
echo.
echo DECISION: adopt aligned schedule as project default only if [4] reaches [1]'s val
echo           by a margin larger than the drift you measured in step 5. Otherwise the
echo           result is inside the noise and we keep the current schedule.
echo ================================================================
echo done.
pause
