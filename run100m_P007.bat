@echo off
REM ===== P007 Token sweep (CLEAN pool) : 100/300/600M all sampled from the SAME 600M pool =====
REM WHY: Loader draws random offsets over the WHOLE cache, so "X tokens from a 300M cache" and
REM      "X tokens from a 600M cache" are DIFFERENT conditions (different pool = different data seen).
REM      To isolate the single variable (tokens TRAINED), every budget must sample the same pool.
REM      -> build the 600M cache once, then train all budgets with --pool-tokens 600M --exact-cache.
REM
REM SEED NOTE: same pool + same seed => the 100M run's crops are an exact prefix of the 300M run's,
REM            which are a prefix of the 600M run's. Cleanest possible tokens-trained scaling curve.
REM
REM NAMING: all runs are TAGGED (p6d/p6t/p6tk) so they NEVER overwrite canonical m100_ko-en_*_dense
REM         logs/checkpoints. tied variants init/distill from the tagged dense via --init-from-tag /
REM         --kd-teacher-tag p6d (NOT the canonical dense). Fixed tied config = g8 across all budgets.
REM
REM COST: ~9 full trainings (dense+tied+kd x 3 budgets). 100M~0.5h, 300M~2.5h, 600M~3h each => heavy.
REM       If you only want dense-vs-KD, comment out the p6t (plain tied) lines.

echo [0] Build the 600M pool once (exact, one-time re-tokenization)
python run100m.py prepare --data ko-en --tokens 600M --exact-cache
if errorlevel 1 goto ERROR

REM ---- helper pattern per budget: dense(p6d) -> tied plain(p6t) -> tied KD-init(p6tk) ----

echo === 100M trained (pool=600M) ===
python run100m.py train --arch dense --data ko-en --tokens 100M --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --tag p6d
if errorlevel 1 goto ERROR
python run100m.py train --arch tied  --data ko-en --tokens 100M --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 8 --tag p6t
if errorlevel 1 goto ERROR
python run100m.py train --arch tied  --data ko-en --tokens 100M --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 8 --init-from-tag p6d --kd --kd-teacher-tag p6d --ema 0.999 --tag p6tk
if errorlevel 1 goto ERROR

echo === 300M trained (pool=600M) ===
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --tag p6d
if errorlevel 1 goto ERROR
python run100m.py train --arch tied  --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 8 --tag p6t
if errorlevel 1 goto ERROR
python run100m.py train --arch tied  --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 8 --init-from-tag p6d --kd --kd-teacher-tag p6d --ema 0.999 --tag p6tk
if errorlevel 1 goto ERROR

echo === 600M trained (pool=600M, full epoch) ===
python run100m.py train --arch dense --data ko-en --tokens 600M --steps 4578 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --tag p6d
if errorlevel 1 goto ERROR
python run100m.py train --arch tied  --data ko-en --tokens 600M --steps 4578 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 8 --tag p6t
if errorlevel 1 goto ERROR
python run100m.py train --arch tied  --data ko-en --tokens 600M --steps 4578 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --pool-tokens 600M --exact-cache --mlp-group 8 --init-from-tag p6d --kd --kd-teacher-tag p6d --ema 0.999 --tag p6tk
if errorlevel 1 goto ERROR

echo === Compares per budget (dense p6d vs tied p6t, and vs KD-init p6tk) ===
python run100m.py compare --data ko-en --tokens 100M --tag p6d --vs p6t
python run100m.py compare --data ko-en --tokens 100M --tag p6d --vs p6tk
python run100m.py compare --data ko-en --tokens 300M --tag p6d --vs p6t
python run100m.py compare --data ko-en --tokens 300M --tag p6d --vs p6tk
python run100m.py compare --data ko-en --tokens 600M --tag p6d --vs p6t
python run100m.py compare --data ko-en --tokens 600M --tag p6d --vs p6tk

echo ================================================================
echo Record per budget: dense val, tied val, gap(=tied-dense), bpb, |g|max -> plot vs tokens.
echo All three budgets sampled the SAME 600M pool -> only "tokens trained" varies.
echo Check: (1) gap shrinks with more tokens? (2) val slope (diminishing returns) (3) KD closes gap?
echo ================================================================
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause
