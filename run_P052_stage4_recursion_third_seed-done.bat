@echo off
REM P052 stage 4  -  a third seed for the recursion ruler.
REM
REM   The tied and dense rulers rest on THREE seeds each (result 039 s9).
REM   The recursion ruler rests on TWO (039 s10). That asymmetry matters
REM   because 039 s9 is exactly the result that showed a two-point range is a
REM   systematic OVER-estimate - the gap between two points is closer to the
REM   expectation of sigma root two than to sigma.
REM
REM   So the recursion 2 sigma of 0.0006 may itself be biased, and it is the
REM   ruler that overturned the R=6 rejection. It should stand on three points.
REM
REM   INDEPENDENT VARIABLE: --seed 777. Everything else matches mC_cla1_ag4_r20.
REM   The confound must match too - that arm ran with grad checkpointing ON,
REM   so this one does as well. Do NOT add --no-ckpt here.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P052_stage4_recursion_third_seed --note "[1/2] train - seed 777 on the recursion arm"
python scripts\runlog.py --name P052_stage4_recursion_third_seed -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 777 --eval-every 100 --compile --attn-group 4 --train-repeat 2.0 --init-from --tag mC_cla1_ag4_r20_s3
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=mC_cla1_ag4_r20_s3
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
echo.
python scripts\runlog.py --name P052_stage4_recursion_third_seed --note "[2/2] paired against the other two seeds"
python scripts\runlog.py --name P052_stage4_recursion_third_seed -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20_s3 mC_cla1_ag4_r20 mC_cla1_ag4_r20_s2 --match-train-repeat
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P052_stage4_recursion_third_seed --note "READ IN THIS ORDER" "1. the three full-val values. Sample sigma over three points, then 2 sigma." "2. compare that to the current 0.0006, which came from a pair." "3. if the new ruler is LARGER, re-check the R=6 retraction in 039 s10." "   20 to 28 visits was -0.0036 = 6.0x the pair-based ruler. It stays" "   significant unless 2 sigma exceeds 0.0018." "4. seed-pair SE is about 0.0013, twice the architecture-pair SE. Read the" "   ruler, not the t statistic (039 s9.4)."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
