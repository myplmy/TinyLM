@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P087_Stage2_epoch4.bat -- four epochs over the same 300M pool
REM ==========================================================================
REM
REM   WHY THIS OPENED
REM     Stage1 measured e1 3.6432813 and e2 3.5278125. That is -0.1155, which is
REM     55 times the dense ruler. The pre-registered rule said "greater than
REM     0.0021 opens Stage2", so Stage2 is open.
REM
REM     The prediction that missed is the one that matters here. We expected
REM     val minus train_ce to widen at two epochs. It did not: +0.108 then
REM     +0.109. No overfitting signal at all, which is the evidence that four
REM     epochs is worth 6.8 hours.
REM
REM   WHAT CHANGES AND WHAT DOES NOT
REM     pool stays 300M. steps go 4578 to 9156, so training tokens go 600M to
REM     1200M. Everything else is byte-identical to the e1 and e2 arms.
REM     Deployment residency does not move by one byte.
REM
REM   THERE IS NO EPOCH IN THE LOADER
REM     loader.py draws uniform random crop offsets with replacement. "4 epochs"
REM     is the NAME of tokens divided by pool, not a data structure. Unique
REM     coverage is 1 - exp(-T/P): e1 63.2 percent, e2 86.5 percent, and this
REM     arm 98.2 percent. So this run also answers a second question - what
REM     happens when the pool is nearly exhausted.
REM
REM   WSD ANNEALS ON A FRACTION OF STEPS
REM     doubling steps doubles the wall time before the decay starts. That is
REM     intended, but write it as "tokens and a schedule proportional to them",
REM     not as "tokens only".
REM
REM   COST: about 6.8h.   PLAN: test_plan/P087 (Korean filename) Stage2
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

timeout /t 15 /nobreak

python scripts\runlog.py --name P087_stage2_epoch4 --note "[1/1] e4 - 1200M tokens over the 300M pool = 4.0 epochs"
python scripts\runlog.py --name P087_stage2_epoch4 -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 9156 --tokens 300M --pool-tokens 300M --exact-cache --tag d12_cla2_r20_p300_e4
if errorlevel 1 echo [WARN] e4 arm failed - continuing

set TL_WB_TAG=d12_cla2_r20_p300_e4
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

echo.
python scripts\runlog.py --name P087_stage2_epoch4 --note "=================================================================" "READ IN THIS ORDER" "1. val minus train_ce FIRST, before any quality reading. e1 and e2 both" "   sat at +0.108. If this arm is much wider, that is overfitting and the" "   axis closes here regardless of the loss number." "2. e4 minus e2 with paired_eval. Ruler is the dense series 0.0021." "   e1 to e2 gave -0.1155. Diminishing returns are expected, closure is not." "3. compare the per-token price: e1 to e2 cost 300M tokens for -0.1155." "   Divide this arm the same way before calling it a win." "4. do NOT compare with any 600M-pool run. Different pool, trap 2." "================================================================="

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
