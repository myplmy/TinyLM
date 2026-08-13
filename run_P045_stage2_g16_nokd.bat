@echo off
REM =============================================================================
REM  P045 stage 2  -  lever x KD interaction (REVIEW2 condition 5)   (about 1.8 h)
REM
REM  THE QUESTION
REM    Every memory lever in this repo was measured against mC_wsd, which is a
REM    KD + parent-init run. REVIEW2 proposes dropping KD from the standard
REM    condition (result 038: reserved 12.47 -^> 5.07 GiB, quality -0.0208).
REM    If the control moves, do the lever deltas survive?
REM
REM    Section 2.3 of the review argues they do, on the grounds that parent-init
REM    and KD were nearly additive (interaction +0.0176). ***That is an estimate,
REM    not a measurement.*** This run measures it once, on the best understood
REM    axis, and that is the whole point of the run.
REM
REM  WHAT IS COMPARED
REM    KD condition     mC_g16      vs mC_wsd       = +0.0161   (result 029)
REM    no-KD condition  mC_g16_nokd vs mC_initonly  = this run
REM    Both control checkpoints ALREADY EXIST. No control retraining needed.
REM
REM  PREDICTION FIXED IN ADVANCE
REM    P1  the two deltas differ by less than 0.024  -^> the existing lever table
REM        carries over unchanged, and REVIEW2 condition 5 is satisfied
REM    P2  no-KD delta stays positive (g16 still costs something)
REM    P3  reserved lands near 5.0 GiB, not 12.5 - no KD teacher in memory
REM        (result 038 measured 5.07 for mC_initonly)
REM    If P1 misses, the lever table must be re-read as KD-conditional and the
REM    review has to say so explicitly. That is worth 1.8 hours to know.
REM
REM  !! THIS RUN HAS NO --kd. THAT IS THE EXPERIMENT, NOT AN OMISSION.
REM     Everything else is byte-identical to the mC_g16 command in result 029 s5.
REM
REM  !! WATCH
REM     step0 ce near 7.7742 (tied + parent init anchor, baselines s2.2)
REM     no [kd] line in the log
REM     grad_max, not the printed abs-g sample
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P045_g16_nokd --note "=============================================================================" "REVIEW2 condition 5   lever x KD interaction   about 1.8 hours   -   tag mC_g16_nokd" "KD condition delta was +0.0161 (mC_g16 vs mC_wsd, result 029)." "Carry-over threshold fixed in advance: the two deltas differ by less than 0.024." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P045_g16_nokd --note "[R2] g16 WITHOUT KD. Same command as result 029 s5 minus --kd --kd-every 4. Control mC_initonly already exists (result 038)."

python scripts\runlog.py --name P045_g16_nokd -- python run100m.py train --preset m100R1c --arch tied --mlp-group 16 --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --tag mC_g16_nokd
if errorlevel 1 goto TRAINBAD

echo.
echo.
python scripts\runlog.py --name P045_g16_nokd --note "[queue] settling 15 s before the evaluation process starts"
timeout /t 15 /nobreak

python scripts\runlog.py --name P045_g16_nokd -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_g16 mC_initonly mC_g16_nokd
if errorlevel 1 echo [WARN] paired_eval returned an error - the training run is still valid

echo.
echo.
python scripts\runlog.py --name P045_g16_nokd --note "=============================================================================" "Read in this order:" "1. no [kd] line in the training log - if there is one the experiment is void" "2. step0 ce near 7.7742, grad_max ^< 10" "3. paired delta mC_g16_nokd - mC_initonly" "4. compare it with +0.0161 (mC_g16 - mC_wsd). Difference under 0.024 means" "   the existing lever table carries over into the no-KD standard condition." "5. reserved GiB - expect near 5.0, not 12.5" "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:TRAINBAD
echo.
echo [STOP] training failed. Read the log before retrying.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
