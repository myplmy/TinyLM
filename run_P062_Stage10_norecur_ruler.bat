@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage10_norecur_ruler.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage8, Stage9 and P088 Stage8 all judge inside the dense+cla2
REM     NO-RECURSION family. That family has no ruler. We are borrowing the
REM     dense 0.0021, and borrowing a ruler is exactly how the recursion
REM     ruler ended up three times too small (result 039 s12: 0.0006 to
REM     0.0018). Two seed replicas fix that.
REM
REM     Stage8 already produces d16_cla2_norecur_s2. This batch fills 12
REM     and 14, so the family ruler exists at three depths.
REM
REM   SEED 2024, the same value every other replica in this repo uses.
REM
REM   READ IN THIS ORDER
REM     1. grad_max and n_skip for both.
REM     2. paired_eval each replica against its base, then take the LARGEST
REM        of the three absolute deltas as the family ruler.
REM     3. if it lands above 0.004, part of the depth difference in Stage8
REM        falls inside the ruler and those verdicts must be rewritten.
REM     4. two seeds means the ruler itself has about 52 percent relative
REM        sd. Say so whenever you quote it.
REM
REM   COST: about 2.6h.   PLAN: test_plan/P062 Stage10
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P062_stage10_norecur_ruler --note "[1/2] depth 12 seed replica"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage10_norecur_ruler -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --seed 2024 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_norecur_s2
if errorlevel 1 echo [WARN] d12 seed replica failed - continuing
set TL_WB_TAG=d12_cla2_norecur_s2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage10_norecur_ruler --note "[2/2] depth 14 seed replica - preset m100s10"
timeout /t 15 /nobreak
python scripts\runlog.py --name P062_stage10_norecur_ruler -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --seed 2024 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d14_cla2_norecur_s2
if errorlevel 1 echo [WARN] d14 seed replica failed - continuing
set TL_WB_TAG=d14_cla2_norecur_s2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P062_stage10_norecur_ruler --note "DONE. The family ruler is the LARGEST of the three absolute paired deltas, not the mean. Quote it with the n=2 caveat."

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
