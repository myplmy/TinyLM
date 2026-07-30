@echo off
REM ===== REVIEW1 : validate the 3 candidate models on the FAIR 600M pool =====
REM Source: the 1st review doc in docs\review\ dated 202607301200, section 6
REM
REM Reference dense = p6d (m100_ko-en_300M_p6d, val 3.7045) - ALREADY TRAINED, reused.
REM Parent-init AND KD teacher are both p6d, so pool / teacher / student all match.
REM
REM WHY the fair pool: result 006 showed the 300M-pool dense (3.8241) was handicapped by
REM   about 0.12 nats, so every gap in result 008 was measured against a weakened baseline.
REM   This batch re-measures all three candidates against a dense that is NOT handicapped.
REM
REM BONUS: run [3] is ALSO the confirmation run that result 006 section 2-(4) requires
REM        (p6tk re-done with static k4 instead of full KD).
REM
REM ***** NO --no-ckpt HERE - ON PURPOSE *****
REM   result 007: tied + KD + COMPRESSED teacher + no-ckpt already sat at 15.6-15.7GB.
REM   These runs use a DENSE teacher (132.5M) which needs MORE, and 16GB is the hard limit.
REM   Losing 6 hours to an OOM at hour 5 costs more than the 17 percent no-ckpt saves.
REM   Grad-checkpoint ON = the known-good config from result 008 (ran 166min clean).
REM
REM COST: 3 x about 141min = about 7.1 hours. A failed run does NOT abort the later ones.

echo === [0] make sure the 600M pool exists (no-op if already built) ===
python run100m.py prepare --data ko-en --tokens 600M --exact-cache
if errorlevel 1 goto ERROR

echo.
echo === [1/3] CANDIDATE A: g4 + sparse34 + KD k4   (11.7MB, 2.64x) ===
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 4 --sparse34 --init-from-tag p6d --kd --kd-teacher-tag p6d --kd-every 4 --tag mA_g4s34_k4
if errorlevel 1 echo [WARN] candidate A failed - continuing

echo.
echo === [2/3] CANDIDATE B: g8 + sparse34 + KD k4   (10.3MB, 3.00x) ===
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 8 --sparse34 --init-from-tag p6d --kd --kd-teacher-tag p6d --kd-every 4 --tag mB_g8s34_k4
if errorlevel 1 echo [WARN] candidate B failed - continuing

echo.
echo === [3/3] CANDIDATE C: g8 + KD k4, no sparsity (14.9MB, 2.07x) ===
REM this run doubles as the fair-pool k4 confirmation run for result 006 section 2-(4)
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 8 --init-from-tag p6d --kd --kd-teacher-tag p6d --kd-every 4 --tag mC_g8_k4
if errorlevel 1 echo [WARN] candidate C failed - continuing

echo.
echo === Compares against the fair-pool dense p6d (3.7045) ===
python run100m.py compare --data ko-en --tokens 300M --tag p6d --vs mA_g4s34_k4
python run100m.py compare --data ko-en --tokens 300M --tag p6d --vs mB_g8s34_k4
python run100m.py compare --data ko-en --tokens 300M --tag p6d --vs mC_g8_k4
echo === sparsity cost isolated, at equal g and equal pool ===
python run100m.py compare --data ko-en --tokens 300M --tag mC_g8_k4 --vs mB_g8s34_k4

echo.
echo ================================================================
echo REFERENCE: p6d val 3.7045  (600M pool, 300M trained, dense, NOT handicapped)
echo.
echo RECORD per candidate: val, best, bpb, minutes, ^|g^|max, and the gap vs 3.7045.
echo   gap ^<= +0.07     -^> candidate passes, promote to canonical candidate
echo   +0.07 to +0.15   -^> raise prelude/coda or lower g
echo   ^> +0.15          -^> check ^|g^|max FIRST (10+ means training problem, not capacity)
echo.
echo TIE-BREAK: if candidates land within 0.05 of each other, that is inside the unmeasured
echo   noise floor (review section 5-A) - pick the SMALLER memory one, memory is goal #1.
echo.
echo IGNORE the deploy-memory numbers compare prints for the sparse34 runs - they are wrong
echo   (review section 5-D). Use the report() block at the top of each training log instead.
echo.
echo LAST COMPARE isolates pure 3:4 sparsity cost on the fair pool. Result 008 measured
echo   +0.0555 for this on the handicapped pool - check whether it holds.
echo ================================================================
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: the 600M pool could not be prepared.
pause
