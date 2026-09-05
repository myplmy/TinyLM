@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage4_d16_t300.bat -- close the 2x2 my own Stage3 left open
REM ==========================================================================
REM
REM   WHAT WENT WRONG IN STAGE3
REM     Stage3 asked "does the token axis pay more on the bigger body" and its
REM     header told the reader to compare against the Stage1 d12 delta. But
REM     the interaction term needs FOUR cells and only three were ever run:
REM       d12 t300 @1.2B pool   3.63171875   ran
REM       d12 t600 @1.2B pool   3.525        ran
REM       d16 t600 @1.2B pool   3.47921875   ran
REM       d16 t300 @1.2B pool   MISSING      NOTE: this batch
REM     Without it there is no d16 delta to compare, so the question Stage3
REM     was built to answer stayed unanswered. That is a design hole, mine.
REM
REM   WHAT IT DECIDES
REM     interaction = (d16_t600 - d16_t300) - (d12_t600 - d12_t300)
REM     negative and large  gives depth and tokens compound, spend the next hours
REM                            on the 40 MiB budget
REM     near zero           gives they are additive, buy tokens on the small body
REM     Ruler is the dense series, 0.0021.
REM
REM   SAME EVERYTHING ELSE
REM     same 1.2B pool, same val.bin, same seed, same schedule shape. Only the
REM     body differs from Stage1's control and only the step count differs
REM     from Stage3. That is the whole point.
REM
REM   VRAM: d16 at --no-ckpt measured 12.32 GB reserved in Stage3.
REM   COST: about 2.2h.   PLAN: test_plan/P088 (Korean filename) Stage4
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

timeout /t 15 /nobreak

python scripts\runlog.py --name P088_stage4_d16_t300 --note "[1/1] d16 with 300M tokens over the 1.2B pool - the missing cell"
python scripts\runlog.py --name P088_stage4_d16_t300 -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --steps 2289 --tokens 300M --pool-tokens 1200M --exact-cache --tag d16_cla2_r20_p12_t300
if errorlevel 1 echo [WARN] d16 t300 arm failed - continuing

set TL_WB_TAG=d16_cla2_r20_p12_t300
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

echo.
python scripts\runlog.py --name P088_stage4_d16_t300 --note "=================================================================" "READ IN THIS ORDER" "1. val minus train_ce tail average first. The other three arms sat" "   between 0.052 and 0.082." "2. the four cells are now complete. Compute the interaction:" "   (d16_t600 - d16_t300) - (d12_t600 - d12_t300)" "3. all four used the 1.2B pool and the same val.bin, so this is the" "   one comparison in P088 that needs no caveat." "4. residency does not move. d16 stays 38.5 MiB." "5. remember the 1.2B pool val has ZERO Korean - this says nothing" "   about Korean. KoBEST is the arm for that." "================================================================="

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
