@echo off
REM =============================================================================
REM  P055 stage 1  -  the KD alpha sweep    (about 5.4 hours, 3 runs)
REM
REM  WHY THIS IS NOW THE TOP PRIORITY  (user instruction, 2026-08-19)
REM    REVIEW2 decision 1 is "do we keep KD in the standard condition". Every
REM    other confirmation condition is finished. This is the last unknown.
REM    What we already know:
REM      result 038   KD's own share is -0.0032, removing it gives -0.0208 and
REM                   reserved 12.47 -^> 5.07 GiB (-59 percent)
REM      result 042   H2 (implementation defect) is ruled out. A1, A4, A5 pass
REM      result 042   EFFECTIVE alpha is 0.288, not the nominal 0.5
REM    So the only way KD survives is if it was simply MIS-TUNED. That is what
REM    an alpha sweep answers, and it has never been run.
REM
REM  !! WHY THREE RUNS AND NOT FOUR
REM    The grid was 0.5 / 0.3 / 0.1 / 0. But alpha=0 IS mC_initonly, which is
REM    already trained (result 038) and sits at full-val 3.6776. Re-running it
REM    would cost 1.8 hours to reproduce a number we have. So three runs.
REM    Effective alphas, from result 042 s11.5.1 with r = 0.404:
REM      nominal 0.5 -^> 0.288   (this is mC_wsd, ALSO already trained, 3.6984)
REM      nominal 0.3 -^> 0.148
REM      nominal 0.1 -^> 0.043
REM    So strictly only 0.3 and 0.1 are new. The third arm below is 0.7, which
REM    extends the grid UPWARD - because if KD is mis-tuned, the fix might be
REM    MORE of it, and nobody has looked in that direction.
REM
REM  !! BASELINE AND WHY  (plan convention, P062 s11)
REM    mC_wsd      3.6984   nominal 0.5, effective 0.288   = current standard
REM    mC_initonly 3.6776   alpha 0                        = the no-KD candidate
REM    Both already exist. This batch adds points BETWEEN and ABOVE them.
REM
REM  ADOPTION LINE, FIXED IN ADVANCE
REM    KD survives only if some alpha beats mC_initonly (3.6776) by more than
REM    0.024. Anything less and we are paying 7.41 GiB of VRAM for noise.
REM    If the best alpha is 0, that is a clean answer too.
REM
REM  !! WATCH
REM    json kd_alpha must be 0.3 / 0.1 / 0.7. If it reads 0.5 the flag did nothing.
REM    grad_max from json, not the printed abs-g.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P055_stage1_alpha --note "=============================================================================" "P055 stage 1   KD alpha sweep   about 5.4 hours   -   REVIEW2 decision 1" "Adoption line fixed in advance: some alpha must beat mC_initonly 3.6776 by 0.024." "Existing points: alpha 0.5 = mC_wsd 3.6984 / alpha 0 = mC_initonly 3.6776" "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P055_stage1_alpha --note "[1/3] nominal alpha 0.3, effective about 0.148"
python scripts\runlog.py --name P055_stage1_alpha -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --kd --kd-every 4 --kd-alpha 0.3 --tag mC_a03
if errorlevel 1 echo [WARN] alpha 0.3 arm failed - continuing

echo.
python scripts\runlog.py --name P055_stage1_alpha --note "[queue] settling 15 s"
timeout /t 15 /nobreak
python scripts\runlog.py --name P055_stage1_alpha --note "[2/3] nominal alpha 0.1, effective about 0.043"
python scripts\runlog.py --name P055_stage1_alpha -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --kd --kd-every 4 --kd-alpha 0.1 --tag mC_a01
if errorlevel 1 echo [WARN] alpha 0.1 arm failed - continuing

echo.
python scripts\runlog.py --name P055_stage1_alpha --note "[queue] settling 15 s"
timeout /t 15 /nobreak
python scripts\runlog.py --name P055_stage1_alpha --note "[3/3] nominal alpha 0.7 - UPWARD. If KD is mis-tuned the fix might be more of it, and nobody looked there."
python scripts\runlog.py --name P055_stage1_alpha -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --kd --kd-every 4 --kd-alpha 0.7 --tag mC_a07
if errorlevel 1 echo [WARN] alpha 0.7 arm failed - continuing

echo.
echo.
python scripts\runlog.py --name P055_stage1_alpha --note "[queue] settling 15 s before the evaluation process starts"
timeout /t 15 /nobreak
python scripts\runlog.py --name P055_stage1_alpha -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_wsd mC_a01 mC_a03 mC_a07
if errorlevel 1 echo [WARN] paired_eval returned an error - the training runs are still valid

echo.
echo.
python scripts\runlog.py --name P055_stage1_alpha --note "=============================================================================" "READ IN THIS ORDER" "1. json kd_alpha for each arm. 0.3 / 0.1 / 0.7. If any reads 0.5 that arm is void." "2. the full-val column, all five, sorted. Where is the minimum?" "3. minimum versus mC_initonly 3.6776 against the fixed line of 0.024." "4. if the minimum IS mC_initonly, REVIEW2 decision 1 is settled: drop KD." "5. if some alpha wins, note reserved GiB too - KD costs 7.41 GiB and that has" "   to be paid out of the quality win, not ignored." "REMINDER: effective alpha is about 0.404 times nominal at start of training" "(result 042 s11.5). Quote both numbers when writing this up." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
