@echo off
REM =============================================================================
REM  P068 stage 1a  -  store _wq in bf16
REM                    1 training run, about 1.5 hours
REM
REM  WHY THIS ARM AND NOT THE OTHERS
REM    Result 035 s13 measured the dtype map and both gates passed:
REM        cast bytes per step   15.46 GB (mC_initonly) / 26.99 GB (d36_ag4)
REM        refresh_quant share   11.2 percent / 8.2 percent
REM    And the decisive line: the weights entering F.linear are 100 percent
REM    fp32 - bf16 bytes through were 0.0 MB. autocast casts on EVERY call.
REM    Storing _wq in bf16 removes that cast entirely.
REM
REM    Plan P068 predicts A1 is the only arm that passes, because _wq is not an
REM    accumulator - it is rebuilt from the fp32 latent every step, so rounding
REM    error does not compound. master weight and gradient do accumulate, which
REM    is why DeepSeek-V3 s3.3.3 keeps them fp32 and we are not touching them.
REM
REM  !! NOT BIT IDENTICAL
REM    --wq-dtype bf16 changes the numbers. Default is fp32. The smoke arm
REM    sm_wqbf16 checks that the flag actually reaches the code (trap 37).
REM
REM  PREDICTIONS, fixed in advance (plan P068 s6)
REM    G3  delta versus mC_initonly under 0.005, ideally under 0.0034 (2 sigma)
REM    G6  reserved drops 0.2 to 0.3 GiB
REM    G7  THIS is the arm where a speed gain should appear - the others only
REM        change storage dtype and never touch a GEMM
REM    New: wall clock should drop. Result 035 s13 says the cast is 15.46 GB per
REM    step; if removing it does not move ms/step, the cast was not the cost.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether master or gradient can go bf16 - those are arms A3 and A2 and
REM    they are predicted to fail. Do not read this result as licence for them.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P068_stage1a_wqbf16 --note "=============================================================================" "P068 stage 1a   _wq stored in bf16   about 1.5 hours" "Result 035 s13: weights entering F.linear are 100 percent fp32." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P068_stage1a_wqbf16 --note "[1/2] mC_wqbf16 - one flag different from mC_initonly. NOT bit identical."
python scripts\runlog.py --name P068_stage1a_wqbf16 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --wq-dtype bf16 --tag mC_wqbf16
if errorlevel 1 echo [WARN] mC_wqbf16 failed - continuing

echo.
python scripts\runlog.py --name P068_stage1a_wqbf16 --note "[wandb] push this run. Never inside the training loop - see tool_wandb_push header."
set TL_WB_TAG=mC_wqbf16
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P068_stage1a_wqbf16 --note "[2/2] paired full-val against the no-KD baseline"
python scripts\runlog.py --name P068_stage1a_wqbf16 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_wqbf16
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
echo.
python scripts\runlog.py --name P068_stage1a_wqbf16 --note "=============================================================================" "READ IN THIS ORDER" "1. json wq_dtype must read bf16. If it reads fp32 the flag did not land and" "   the run is just a reseed of mC_initonly (trap 37)." "2. the [P068] print line at startup. No line, no experiment." "3. wall clock against mC_initonly 108.2 minutes. THIS is the headline - the" "   cast was 15.46 GB per step, so it should show." "4. paired delta against G3. The ruler is 2 sigma = 0.0034." "5. reserved against G6 (0.2 to 0.3 GiB lower)." "REMINDER  a pass here says nothing about master or gradient bf16." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
