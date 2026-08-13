@echo off
REM =============================================================================
REM  P046 stage 3  -  embedding bottleneck E = 192   (about 3.5 h)
REM
REM  WHY 192 AND NOT 128 AGAIN
REM    Stage 2 re-measured E=128 with SVD truncation instead of random init and
REM    got +0.1123 versus mC_wsd (result 030 s9). That is 4.7x the resolution -
REM    a real and large cost. The SVD log also printed the spectrum: E=128 keeps
REM    about 82 percent of the energy, E=192 keeps 88.76 percent.
REM    So the prediction is written down BEFORE the run:
REM
REM      P1  E=192 costs clearly less than E=128, roughly +0.04 to +0.08
REM      P2  it is still above the 0.024 resolution, i.e. not free
REM      P3  the cost per kept-energy point is roughly linear in this range
REM
REM    If P1 misses high, the embedding axis is steeper than the spectrum says
REM    and the whole "spectrum energy predicts cost" idea is wrong - that is
REM    worth knowing on its own.
REM
REM  !! WHERE THIS PAYS
REM    Result 032 s4.3: E=128 is -18.8 percent on the int8 path but only -3.6
REM    percent on fp32. This lever ranks completely differently depending on the
REM    deployment path (trap 24). ***Always name the path when quoting it.***
REM
REM  !! INIT CONDITION
REM    Changing --emb-rank makes the embedding shape differ from the parent, so
REM    _svd_emb_init runs instead of a plain copy. Watch for the
REM    [init] embedding SVD line and the preserved-energy percentage.
REM    G-init: that line present, step0 ce ^< 8.5, grad_max ^< 3.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P046_emb_rank192 --note "=============================================================================" "P046 stage 3   E = 192   about 3.5 hours   -   tag mC_e192svd" "Reference: mC_wsd 3.6984 / mC_e128svd +0.1123" "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P046_emb_rank192 --note "[P046 stage 3] emb_rank 192 with SVD transplant. Prediction fixed in advance: +0.04 to +0.08 vs mC_wsd, spectrum energy 88.76 percent."

python scripts\runlog.py --name P046_emb_rank192 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --kd --kd-every 4 --emb-rank 192 --tag mC_e192svd
if errorlevel 1 goto TRAINBAD

echo.
echo.
python scripts\runlog.py --name P046_emb_rank192 --note "[queue] settling 15 s before the evaluation process starts"
timeout /t 15 /nobreak

python scripts\runlog.py --name P046_emb_rank192 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_e128svd mC_e192svd
if errorlevel 1 echo [WARN] paired_eval returned an error - the training run is still valid

echo.
echo.
python scripts\runlog.py --name P046_emb_rank192 --note "=============================================================================" "Read:" "1. the [init] SVD line - preserved spectrum energy percent" "2. json emb_rank = 192, else the flag did nothing" "3. grad_max ^< 3 (G-init), grad_max ^< 10 (judgeable at all)" "4. paired delta vs mC_wsd, and vs mC_e128svd (+0.1123)" "5. mem_breakdown - and say WHICH path (fp32 or int8) when you quote it" "============================================================================="
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
