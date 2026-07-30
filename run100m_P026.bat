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
REM           so nothing canonical is overwritten. [1] qb_cos is the IN-EXPERIMENT control:
REM           always compare 2,3,4 to IT.
REM
REM ***** POOL: 600M, NOT the default *****
REM   Added 2026-07-30. The first version of this batch omitted --pool-tokens, so it would have
REM   used the 300M cache = pool/trained ratio 1x = the starvation condition result 006 warned
REM   about, violating our own "pool at least 2x trained" standard. All four runs now sample the
REM   600M pool, which also makes [1] qb_cos directly comparable to the existing p6d (3.7045):
REM   qb_cos differs from p6d ONLY by --no-ckpt, so that delta is a clean grad-checkpoint
REM   drift measurement for free.
REM
REM COST: 3 x ~81min + 1 x ~69min = about 5.2 hours (+ nothing, the 600M cache already exists).
REM NOTE: errors do NOT abort the batch (result 007 lesson) - later runs still execute.

echo === [1/4] control: cosine, anneal 0.60 (current default schedule) ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --pool-tokens 600M --exact-cache --sched cosine --anneal-end 0.60 --tag qb_cos
if errorlevel 1 echo [WARN] [1/4] failed - continuing

echo === [2/4] wsd, anneal 0.60 (NOT aligned: ternary done 0.60, decay starts 0.80) ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --pool-tokens 600M --exact-cache --sched wsd --anneal-end 0.60 --decay-frac 0.2 --tag qb_wsd60
if errorlevel 1 echo [WARN] [2/4] failed - continuing

echo === [3/4] wsd, anneal 0.80 (ALIGNED: ternary completes as cooldown begins) ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --pool-tokens 600M --exact-cache --sched wsd --anneal-end 0.80 --decay-frac 0.2 --tag qb_wsd80
if errorlevel 1 echo [WARN] [3/4] failed - continuing

echo === [4/4] PAYOFF TEST: aligned + 15 percent fewer steps (1946) ===
REM 1946 steps x 131K = 255M tokens. If val matches [1] at 2289 steps, alignment bought us 15pct.
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 1946 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --pool-tokens 600M --exact-cache --sched wsd --anneal-end 0.80 --decay-frac 0.2 --tag qb_wsd80_s85
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
echo   5. [1] qb_cos vs p6d (3.7045) : differs ONLY by --no-ckpt on the same 600M pool,
echo      so that delta is the grad-checkpoint numeric drift. Do NOT compare to 3.8241, which
echo      is a 300M-pool run (different data seen entirely).
echo.
echo DECISION: adopt the aligned schedule as project default only if [4] reaches [1]'s val
echo           within sigma_hat (measured by run100m_REVIEW1.bat run [1], p6d_s2).
echo           RUN REVIEW1 FIRST - without sigma_hat this batch cannot be judged, because the
echo           effect we are looking for (a 15pct step cut costing ~0.03) is the same size as
echo           the noise we have not measured.
echo ================================================================
echo done.
pause
