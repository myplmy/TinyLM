@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage8_winner_1200M.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Our winner sits at 3.6 tokens per parameter. SmolLM2 is near 6,470. The
REM     single largest untouched lever is training tokens, and it costs ZERO
REM     deployment residency. This is the longest run we have ever queued.
REM
REM   THREE ARMS
REM     d14_cla2_norecur_t1200   1200M tokens, the 32 MiB shape
REM     d16_cla2_norecur_t1200   1200M tokens, the 40 MiB shape
REM     d16_cla2_norecur_p12     300M tokens on the 1200M pool - the pool control
REM
REM     The third arm exists so the first two are readable. Without it a change
REM     from the 300M runs mixes pool and tokens together.
REM
REM   HONEST LIMITATION, STATED UP FRONT
REM     arms 1 and 2 have pool equal to tokens, a ratio of 1.0. Our rule wants at
REM     least 2.0. Unique tokens fall to 1200 x (1 - 1/e) = 758M. We do not have a
REM     2.4B cache. The two-axis law already accounts for unique tokens, so the
REM     prediction stands, but this is OUTSIDE the standard condition and every
REM     quote of these numbers must say so.
REM
REM   PREREQUISITE: P062 Stage8 and Stage9. Do not start 13 hours before knowing
REM     the depth answer and the 600M answer.
REM
REM   READ IN THIS ORDER
REM     1. grad_max and n_skip. 9156 steps is four times anything we have run.
REM     2. arm 3 minus the 300M pool-600M run of the same shape isolates POOL.
REM     3. arm 2 minus arm 3 isolates TOKENS at fixed pool.
REM     4. the law predicts -0.1230 bpb, about -0.372 nats, from the 300M run.
REM        That is 5.8 times what depth 12 to 16 buys.
REM     5. common_bpb only across pools. Log val is not comparable.
REM
REM   COST: about 13.4h.   PLAN: test_plan/P088 Stage8
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P088_stage8_winner_1200M --note "[1/3] pool control - 300M tokens on the 1200M pool, 40 MiB shape"
timeout /t 15 /nobreak
python scripts\runlog.py --name P088_stage8_winner_1200M -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 1200M --exact-cache --tag d16_cla2_norecur_p12
if errorlevel 1 echo [WARN] pool control failed - continuing
set TL_WB_TAG=d16_cla2_norecur_p12
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P088_stage8_winner_1200M --note "[2/3] 32 MiB shape at 1200M tokens - ratio 1.0, outside the standard"
timeout /t 15 /nobreak
python scripts\runlog.py --name P088_stage8_winner_1200M -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 9156 --tokens 1200M --pool-tokens 1200M --exact-cache --tag d14_cla2_norecur_t1200
if errorlevel 1 echo [WARN] d14 t1200 failed - continuing
set TL_WB_TAG=d14_cla2_norecur_t1200
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P088_stage8_winner_1200M --note "[3/3] 40 MiB shape at 1200M tokens - the headline run"
timeout /t 15 /nobreak
python scripts\runlog.py --name P088_stage8_winner_1200M -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 9156 --tokens 1200M --pool-tokens 1200M --exact-cache --tag d16_cla2_norecur_t1200
if errorlevel 1 echo [WARN] d16 t1200 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_t1200
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P088_stage8_winner_1200M --note "DONE. Every quote of these two must carry: pool over tokens is 1.0, below the standard 2.0, unique tokens about 758M."

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
