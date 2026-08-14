@echo off
REM =============================================================================
REM  P049B stage 1  -  training-time recurrence, R = 2.0   (about 7 GPU hours)
REM
REM  THE QUESTION
REM    Stage 0 (result 043) measured the STARTING cost of passing the middle
REM    block twice: +0.1025 nats at step 0, with ternary parameters UNCHANGED
REM    at 54.85M. The plan's own ceiling was 0.3, so the axis stayed open.
REM    Stage 1 asks whether TRAINING RECOVERS that cost.
REM
REM  WHY ONE RUN AND NOT THREE
REM    The plan originally swept R = 1.5 / 2.0 / 2.5 for about 12 hours.
REM    Stage 0 proved uniform mode ROUNDS TO AN INTEGER - 1.5, 2.0 and 2.5 all
REM    produced 36 visits and CE 7.3824, the identical model. Running the old
REM    grid would spend 12 hours measuring the same point three times.
REM    The R=1.0 baseline is mC_wsd, which already exists (3.6984).
REM    So: one run, about 7 hours.
REM
REM  SUCCESS CRITERION - FIXED BEFORE THE RESULT (plan s12.6)
REM    Better than mC_wsd by 0.024 or more   ==  the axis is alive
REM    Within plus or minus 0.024            ==  NOT "a tie". It means the
REM                                             starting cost of 0.1025 WAS
REM                                             recovered, and that is itself
REM                                             information.
REM    Worse by 0.024 or more                ==  recurrence is not recovered by
REM                                             training. Do NOT run stage 2.
REM    Judged with paired_eval, never with the training log val (trap 33).
REM
REM  WHAT THIS RUN MUST RECORD  (result 043 s6)
REM    VRAM. Stage 0 measured 1.47 GiB peak alloc and it did NOT move with R,
REM    but that was FORWARD ONLY under no_grad. Backward has to keep activations
REM    for all 36 visits. The honest expectation is that training VRAM DOES
REM    rise. Grad checkpointing stays ON, which is what should absorb it.
REM    Also record ms/step steady state and grad_max.
REM
REM  STANDARD CONDITIONS - identical to mC_wsd so the pair is valid
REM    ko-en, 600M pool exact, 2289 steps, mb8 x accum16 x seq1024, lr 1e-3,
REM    wsd 0.80/0.2, seed 1337, KD k4 + parent init.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ---- refuse to run without the stage 0 gate --------------------------------
python -c "import glob,sys; sys.exit(0 if glob.glob('test_result/*P049B_stage0_repeat*.txt') else 1)"
if errorlevel 1 goto NOGATE

echo.
echo.
python scripts\runlog.py --name P049B_stage1_repeat --note "=============================================================================" "P049B stage 1   train_repeat 2.0   tag mC_r20   about 7 hours" "Starting cost measured at stage 0 was +0.1025 nats. Does training recover it?" "Threshold fixed in advance: -0.024 vs mC_wsd means the axis is alive." "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P049B_stage1_repeat --note "[P049B stage 1] m100R1c with --train-repeat 2.0 uniform. 20 physical layers, 36 visits, ternary unchanged at 54.85M. RECORD VRAM - stage 0's 1.47 GiB was forward only."

python scripts\runlog.py --name P049B_stage1_repeat -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --kd --kd-every 4 --train-repeat 2.0 --repeat-mode uniform --tag mC_r20
if errorlevel 1 goto TRAINBAD

echo.
echo.
python scripts\runlog.py --name P049B_stage1_repeat --note "[queue] settling 15 s before the evaluation process starts"
timeout /t 15 /nobreak

python scripts\runlog.py --name P049B_stage1_repeat -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_r20
if errorlevel 1 echo [WARN] paired_eval returned an error - the training run is still valid

echo.
echo.
python scripts\runlog.py --name P049B_stage1_repeat --note "=============================================================================" "WHAT TO RECORD" "1. paired_eval delta vs mC_wsd - threshold was fixed at -0.024" "2. VRAM alloc and reserved - stage 0 could not see backward activations" "3. ms/step steady state, and remember sessions drift 7.5 percent" "4. grad_max from runs/logs json, NOT the printed abs-g sample" "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:NOGATE
echo.
echo [STOP] stage 0 gate log not found in test_result.
echo        Run run_P049B_stage0_repeat_gate.bat first - it takes 12 seconds.
echo        (If it was already run and the log deleted, result 043 has the numbers.)
if not defined TL_NOPAUSE pause
exit /b 1

:TRAINBAD
echo.
echo [STOP] training failed. Check for CUBLAS_STATUS_EXECUTION_FAILED - that is
echo        how an out-of-memory arrives here (trap 29), not as OutOfMemoryError.
echo        36 visits with grad checkpointing ON should fit, but if it does not,
echo        that IS the result - record it.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
