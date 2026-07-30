@echo off
REM ===== P007B : pool-saturation point + fair-pool k4 at the 600M budget =====
REM   Follow-up to result 006. Template reused from run100m_P007.bat, but a DIFFERENT experiment
REM   and a different file, so the original P007 record stays untouched.
REM
REM TWO OPEN QUESTIONS FROM RESULT 006
REM
REM Q1 (cheap) WHERE DOES THE POOL BENEFIT SATURATE?
REM   Result 006 found that keeping the trained tokens at 300M and only growing the sample pool
REM   from 300M to 600M improved dense by 0.12 nats. We do not know if that keeps going.
REM   We already have both existing points, so only ONE new run is needed:
REM       pool  300M -^> dense val 3.8241   (canonical tag "dense")
REM       pool  600M -^> dense val 3.7045   (tag p6d)
REM       pool 1200M -^> ?                  (tag p12d, THIS BATCH)
REM   If 1200M gives another 0.1, data pool is a cheaper lever than any architecture change and
REM   every baseline should be rebuilt on a bigger pool. If it gives ~0.02, 600M is enough and
REM   we stop thinking about it.
REM
REM Q2 (expensive) IS THE "KD GAIN SHRINKS WITH BUDGET" CONCLUSION CLEAN?
REM   Result 006 reported the KD gap growing: -0.110 (100M) / +0.062 (300M) / +0.098 (600M).
REM   BUT the pool was 600M for all three, so the pool-to-trained RATIO was 6x / 2x / 1x.
REM   The 600M-budget row therefore VIOLATES our own "pool must be at least 2x trained" rule -
REM   it is exactly the 1-epoch starvation condition that result 006 itself identified.
REM   Direction of the confound: starvation hurts dense, which would make the KD gap look
REM   SMALLER, yet we measured it LARGER. So the conclusion is conservative, not wrong.
REM   Still, to state it cleanly we need the 600M budget on a 1200M pool.
REM
REM ORDER: Q1 first. It is one run and it decides whether Q2 is even worth 9 hours.
REM
REM COST: [0] about 30min tokenization (one-time, 2.4GB on disk)
REM       PART 1 (Q1): 1 run, about 117min
REM       PART 2 (Q2): 2 runs, about 250min + 290min = about 9h  (COMMENTED OUT BY DEFAULT)
REM
REM ERRORLEVEL POLICY: the 1200M prepare is a hard prerequisite (goto ERROR). Training runs
REM   only warn, except p12d which PART 2 initialises and distills from.

echo === [0] build the 1200M pool (one-time, about 30min, 2.4GB) ===
python run100m.py prepare --data ko-en --tokens 1200M --exact-cache
if errorlevel 1 goto ERROR

echo.
echo ============================================================
echo PART 1 (Q1) : pool saturation - dense at 300M trained, pool 1200M
echo ============================================================
REM Same trained tokens as the two points we already have. ONLY the pool differs.
REM grad-ckpt left ON to match how p6d and the canonical dense were run (comparability first).
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --pool-tokens 1200M --exact-cache --tag p12d
if errorlevel 1 echo [WARN] p12d failed - PART 2 cannot run without it

echo.
echo --- Q1 readout ---
echo   pool  300M : 3.8241   (canonical dense)
echo   pool  600M : 3.7045   (p6d, minus 0.1196)
echo   pool 1200M : see the p12d line above
python run100m.py compare --data ko-en --tokens 300M --tag p6d --vs p12d
echo   INTERPRET: gain from 600M to 1200M vs the 0.1196 gain from 300M to 600M.
echo     still large   -^> pool is the cheapest quality lever, rebuild baselines bigger
echo     much smaller  -^> 600M pool is the standard, stop growing it
echo   CAVEAT: the canonical dense used --eval-every 250 and no --pool-tokens flag. It should be
echo     equivalent, but if the 300M point looks odd, trust p6d-vs-p12d and not the 3-point curve.

echo.
echo ============================================================
echo PART 2 (Q2) : 600M budget on a FAIR 1200M pool - about 9 hours
echo ============================================================
echo PART 2 is commented out on purpose. Read the Q1 result first, then remove the REM
echo prefixes from the two python lines below if you want to spend the 9 hours.
echo.
REM --- fair-pool dense at the 600M budget (reference for the KD gap) ---
REM python run100m.py train --arch dense --data ko-en --tokens 600M --steps 4578 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --pool-tokens 1200M --exact-cache --tag p12d600
REM if errorlevel 1 echo [WARN] p12d600 failed - continuing
REM
REM --- tied g8 + parent-init + STATIC k4 at the 600M budget (the confirmation run) ---
REM   uses k4, not full KD: result 005 showed static k4 beats full KD by 0.042 and is 15pct faster,
REM   and result 006 used full KD, which is exactly the gap this run closes.
REM python run100m.py train --arch tied --data ko-en --tokens 600M --steps 4578 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --pool-tokens 1200M --exact-cache --mlp-group 8 --init-from-tag p12d600 --kd --kd-teacher-tag p12d600 --kd-every 4 --tag p12tk600_k4
REM if errorlevel 1 echo [WARN] p12tk600_k4 failed - continuing
REM
REM python run100m.py compare --data ko-en --tokens 600M --tag p12d600 --vs p12tk600_k4

echo.
echo ================================================================
echo RECORD (both parts): val, best, bpb, minutes, grad_max from runs\logs\*.json.
echo   Note the pool-to-trained ratio for every row. Rows with ratio under 2x are starved and
echo   must be labelled as such - that is the mistake result 006 caught.
echo.
echo Q2 DECISION: if the fair-pool 600M gap is still clearly positive, "KD gain shrinks as the
echo   budget grows" is confirmed and tied+KD should be treated as a LOW-BUDGET technique.
echo   If it collapses toward zero, the 600M row in result 006 was a starvation artifact and
echo   result 006 section 2-(3) needs revising.
echo.
echo Compare any gap against sigma_hat from run100m_REVIEW1.bat before calling it real.
echo ================================================================
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: the 1200M pool could not be prepared (disk space? network?).
echo        Nothing else in this batch can run without it.
pause
