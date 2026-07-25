@echo off
REM ===== P007 Token sweep (100/300/600M): dense-vs-tied gap & quality curve =====
REM steps = tokens / 131072  (100M->763, 300M->2289, 600M->4578). eff-batch mbs8*accum16*seq1024=131K.
REM 300M reuses existing dense; 100M/600M are new. Tied variant = default g4 (t_base via 'all', t_kdinit=+KD-init+EMA).
REM NOTE: 600M triggers a one-time re-tokenization of the ko-en cache (~3h/model). Ensure disk space.

echo === 100M ===
echo [100M a] dense + tied(t_base) via all
python run100m.py all --data ko-en --tokens 100M --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile
if errorlevel 1 goto ERROR
echo [100M b] tied + KD-init + EMA (t_kdinit)
python run100m.py train --arch tied --data ko-en --tokens 100M --steps 763 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --ema 0.999 --init-from --kd --tag t_kdinit
if errorlevel 1 goto ERROR

echo === 600M (one-time re-tokenization) ===
echo [600M a] dense + tied(t_base) via all
python run100m.py all --data ko-en --tokens 600M --steps 4578 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile
if errorlevel 1 goto ERROR
echo [600M b] tied + KD-init + EMA (t_kdinit)
python run100m.py train --arch tied --data ko-en --tokens 600M --steps 4578 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --ema 0.999 --init-from --kd --tag t_kdinit
if errorlevel 1 goto ERROR

echo === 300M optional t_kdinit(g4) for a consistent curve (skip if reusing existing g8 line) ===
REM python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --ema 0.999 --init-from --kd --tag t_kdinit

echo === Compares (dense vs tied, dense vs KD-tied) per budget ===
python run100m.py compare --data ko-en --tokens 100M
python run100m.py compare --data ko-en --tokens 100M --tag t_kdinit
python run100m.py compare --data ko-en --tokens 300M
REM python run100m.py compare --data ko-en --tokens 300M --tag t_kdinit
python run100m.py compare --data ko-en --tokens 600M
python run100m.py compare --data ko-en --tokens 600M --tag t_kdinit

echo ================================================================
echo Record per budget: dense val, tied val, gap, bpb, |g|max -> plot vs tokens.
echo Check: (1) gap shrinks with more tokens? (2) val slope (diminishing returns) (3) KD closes gap?
echo ================================================================
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause
