@echo off
REM =============================================================================
REM  P070 stage 0  -  train the REVIEW2 option B and option C controls NOW
REM                   2 runs, about 3.6 hours total
REM
REM  WHY BEFORE THE DECISION IS MADE
REM    REVIEW2 cannot be closed until the user picks one of three standard
REM    conditions. Options B and C each need one control run first. That
REM    retraining does NOT depend on which option is picked - both commands
REM    run today, and at least one of them will be used no matter what.
REM    Decision trap D1: if you say "later", write the number. The number is
REM    3.6 hours, and there is no prerequisite.
REM
REM  WHAT WAS SETTLED FIRST (both landed 2026-08-20)
REM    result 042 s12  KD removal CONFIRMED - alpha 0 to 0.7 is monotone and
REM                    alpha 0.1 is indistinguishable from no KD at all.
REM                    So the shared base of all three options is now measured.
REM    result 049      resolution is condition-dependent by 18x. For THIS
REM                    condition (tied, parent-init, no KD) 2 sigma is 0.0034.
REM                    That is the ruler these two runs get judged with.
REM
REM  THE ARMS
REM    mC_std2   option B   = mC_initonly + --micro-group 256 --opt-dtype bf16
REM    mC_std3   option C   = mC_std2     + --mlp-group 16
REM    Reference mC_initonly already exists at full-val 3.6776 - not retrained.
REM
REM  SECOND PAYOFF
REM    mC_std3 minus mC_std2 measures g16 ON THE NEW STANDARD. Result 029 s6
REM    measured g16 at micro_group 128 and opt fp32. We have never had the
REM    number on the condition we are about to adopt.
REM
REM  PREDICTIONS, fixed in advance (plan P070 s4)
REM    P1  mC_std2 lands within 0.001 of mC_initonly (the two levers sum to
REM        -0.0009). Outside 0.0034 means the levers interact.
REM    P2  mC_std3 minus mC_std2 is about +0.0163, matching result 029 s6.
REM    P3  mC_std2 packed 12.578 MB
REM    P4  mC_std2 reserved 4.0 to 4.6 GiB
REM    P5  mC_std3 residency 415.5 MB, minus 8.0 percent
REM
REM  !! DO NOT RESUME THIS BATCH
REM    --opt-dtype bf16 is not compatible with --resume (result 035 s12).
REM    If a run dies, start that arm over from the beginning.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Which option is right. That is the user's decision - this only builds
REM    the material. And it says nothing about model architecture: mC_d36_ag4
REM    is a MODEL candidate, not a standard-condition candidate.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P070_stage0_controls --note "=============================================================================" "P070 stage 0   REVIEW2 option B and C controls   about 3.6 hours" "Pre-emptive. Neither run depends on the decision they unblock." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P070_stage0_controls --note "[1/3] option B control - mC_std2 - micro-group 256 plus opt-dtype bf16. DO NOT RESUME."
python scripts\runlog.py --name P070_stage0_controls -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --micro-group 256 --opt-dtype bf16 --tag mC_std2
if errorlevel 1 echo [WARN] mC_std2 failed - continuing

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P070_stage0_controls --note "[2/3] option C control - mC_std3 - same plus mlp-group 16. Also measures g16 on the new standard."
python scripts\runlog.py --name P070_stage0_controls -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --micro-group 256 --opt-dtype bf16 --mlp-group 16 --tag mC_std3
if errorlevel 1 echo [WARN] mC_std3 failed - continuing

echo.
python scripts\runlog.py --name P070_stage0_controls --note "[3/3] paired full-val against the existing no-KD reference"
python scripts\runlog.py --name P070_stage0_controls -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_std2 mC_std3
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
echo.
python scripts\runlog.py --name P070_stage0_controls --note "=============================================================================" "READ IN THIS ORDER" "1. json micro_group must be 256 and opt_dtype must be bf16 on both arms." "   If a flag did not land, nothing below means anything (trap 37)." "2. mC_std2 vs mC_initonly. The ruler is 2 sigma = 0.0034, not 0.024." "3. mC_std3 minus mC_std2. That is g16 on the NEW standard - compare with" "   the +0.0163 that result 029 s6 measured on the OLD one." "4. packed and runtime_mb against P3 and P5. Accounting check." "REMINDER  this builds material for the decision. It does not make it." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
