@echo off
REM =============================================================================
REM  P049 stage 1  -  does tying buy depth?   m100R1d = 36 layers, g16, 2 groups
REM
REM  ***PREREQUISITE: run_P049_stage0b_init_gate.bat must have passed.***
REM  Without it the transplant is unverified and 5.8 hours are at risk.
REM  This batch checks for the gate log and refuses to start if it is absent.
REM
REM  THE QUESTION
REM    Unique MLP count is unchanged (6). MLP ternary is IDENTICAL (28.31M).
REM    Attention is not tied, so 20 -^> 36 layers costs +80 percent attention
REM    ternary, +38.7 percent total, +35.9 percent fp32 resident.
REM    So: buy depth with attention memory - is the quality worth it?
REM
REM  ADOPTION THRESHOLD, FIXED BEFORE THE RESULT (plan P049 s3)
REM    paired delta must be better than -0.075 versus mC_wsd.
REM    That is the price result 032 s8 measured for REMOVING 16.81M. If adding
REM    21.2M does not buy it back, depth is the worst way to spend memory.
REM    -0.075 to 0  =^> improves but does not pay for itself, axis closed.
REM    ^> 0          =^> depth is saturated at this scale.
REM
REM  VRAM WARNING
REM    36 layers plus a 20 layer KD teacher. Result 033 measured g8 alone at
REM    5.06 GiB; 1.8x is about 9.1 GiB before the teacher. This is close to the
REM    spill wall. Grad checkpointing stays ON. If it OOMs, the message may
REM    arrive as CUBLAS_STATUS_EXECUTION_FAILED (trap 29), not as OOM.
REM
REM  STANDARD CONDITIONS - identical to mC_wsd so the pair is valid:
REM    ko-en, 600M pool exact, 2289 steps, mb8 x accum16 x seq1024, lr 1e-3,
REM    wsd 0.80/0.2, seed 1337, KD k4 + parent init.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ---- refuse to run without the stage 0 gate --------------------------------
REM   The gate log name is {YYYYMMDDHHMM}_{name}_{sha7}.txt, so the timestamp is
REM   unknown here. Ask python for the answer - a wildcard test in cmd would
REM   need a redirect, and unescaped redirects are a lint error in this repo.
python -c "import glob,sys; sys.exit(0 if glob.glob('test_result/*P049_stage0b_identity*.txt') else 1)"
if errorlevel 1 goto NOGATE

echo.
echo.
python scripts\runlog.py --name P049_depth_g16x2 --note "=============================================================================" "P049 stage 1   about 5.8 hours   -   tag mC_d36" "36 layers vs 20. Adoption threshold was fixed in advance: better than -0.075" "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P049_depth_g16x2 --note "[P049 stage 1] m100R1d 2+32+2 g16, KD k4 + parent init, wsd. Threshold fixed in advance at -0.075 vs mC_wsd."

python scripts\runlog.py --name P049_depth_g16x2 -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --kd --kd-every 4 --depth-init identity --tag mC_d36
if errorlevel 1 goto TRAINBAD

echo.
echo.
python scripts\runlog.py --name P049_depth_g16x2 --note "[queue] settling 15 s before the evaluation process starts"
timeout /t 15 /nobreak

python scripts\runlog.py --name P049_depth_g16x2 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_g16 mC_d36
if errorlevel 1 echo [WARN] paired_eval returned an error - the training run is still valid

echo.
echo.
python scripts\runlog.py --name P049_depth_g16x2 --note "=============================================================================" "Read, in this order:" "1. the [init] lines at the top - how many layers were duplicated" "2. json n_layers = 36 and depth_init, or the preset did not apply" "3. json grad_max ^< 10, else judgement is not possible (result 030)" "4. paired delta vs mC_wsd against the -0.075 threshold" "5. peak_reserved_gib and ms_step_spread (spill band 0.065 to 0.154)" "!! mC_d36 is NOT comparable to a 20-layer run on speed - different depth." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:NOGATE
echo.
echo [STOP] stage 0 gate log not found in test_result.
echo        Run run_P049_stage0b_init_gate.bat first. It takes minutes and it is
echo        the only thing standing between you and 5.8 hours through a broken
echo        transplant (result 030).
if not defined TL_NOPAUSE pause
exit /b 1

:TRAINBAD
echo.
echo [STOP] training failed. If the message mentions CUBLAS_STATUS_EXECUTION_FAILED
echo        it is an out-of-memory under a different name (trap 29). 36 layers plus
echo        the KD teacher is close to the wall - try dropping the teacher first
echo        (result 038: removing KD costs nothing in quality and frees 7.41 GiB).
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
