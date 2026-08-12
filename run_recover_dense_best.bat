@echo off
REM =============================================================================
REM  RECOVER  m100_ko-en_300M_dense_best.pt   (deleted by accident 2026-08-14)
REM
REM  WHAT IS MISSING
REM    runs\ckpt\m100_ko-en_300M_dense_best.pt
REM  WHAT IS STILL THERE
REM    runs\ckpt\m100_ko-en_300M_dense.pt      = the CANONICAL parent / KD teacher
REM
REM  ***READ THIS BEFORE RUNNING.***
REM
REM  1) NOTHING IS BROKEN RIGHT NOW.
REM     Only `--kd-best` reads the _best file, and no current batch uses it.
REM     Every standard run uses the FINAL checkpoint, which still exists.
REM     So this recovery is OPTIONAL. Cost is about 100 minutes of GPU.
REM
REM  2) THE OBVIOUS FIX IS THE DANGEROUS ONE.
REM     Retraining without --tag writes m100_ko-en_300M_dense.pt, i.e. it
REM     OVERWRITES THE CANONICAL PARENT that every single tied run in this
REM     repo was initialised from and distilled against. CLAUDE.md: the
REM     untagged `dense` name is "never overwrite". So this batch uses
REM     --tag denseb and NEVER touches the canonical file.
REM
REM  3) THE RECOVERED FILE IS NOT THE ORIGINAL.
REM     The original was trained 2026-07-23 with a 300M pool (the 600M-pool
REM     standard came later, result 006). Training is also not bit-reproducible
REM     across driver/torch versions. So what you get is A dense best, not THE
REM     dense best. Registry value to compare against: val 3.8241 / best 3.7797
REM     (EXPERIMENT_BASELINES section 2.1).
REM     ***If the new best is far from 3.7797, do not silently treat it as the
REM        old teacher - record it as a new run.***
REM
REM  4) CONDITIONS BELOW REPLICATE THE ORIGINAL RUN, NOT TODAY'S STANDARD.
REM     pool = 300M (not 600M), sched = cosine (not wsd). That is deliberate:
REM     the point is to recreate the artefact, not to make a better one.
REM
REM  AFTER THE RUN
REM    The batch prints the copy command. ***You run it, not the AI.***
REM    (CLAUDE.md: file deletion and git are done by the user.)
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo =============================================================================
echo  RECOVER dense_best  -  about 100 minutes
echo =============================================================================
echo  This does NOT overwrite runs\ckpt\m100_ko-en_300M_dense.pt
echo  It writes            runs\ckpt\m100_ko-en_300M_denseb.pt
echo  and                  runs\ckpt\m100_ko-en_300M_denseb_best.pt
echo.
echo  Reference from the registry:  val 3.8241  /  best 3.7797
echo =============================================================================
echo.
if not defined TL_NOPAUSE pause

REM ---- safety: refuse to run if the canonical parent is missing --------------
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

python scripts\runlog.py --name P000_recover_dense_best --note "[recover] regenerate m100_ko-en_300M_dense_best.pt as tag denseb - original conditions: 300M pool, cosine, seed 1337"

python scripts\runlog.py --name P000_recover_dense_best -- python run100m.py train --preset m100 --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched cosine --seed 1337 --eval-every 100 --compile --no-ckpt --tag denseb
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================================
echo  DONE. Now decide, do not automate this part.
echo =============================================================================
echo.
echo  Compare the printed best value with 3.7797.
echo.
echo   - close  (within about 0.02)  the artefact is a fair stand-in. To install:
echo.
echo       copy runs\ckpt\m100_ko-en_300M_denseb_best.pt runs\ckpt\m100_ko-en_300M_dense_best.pt
echo.
echo   - far off                      DO NOT install it under the old name.
echo                                  Keep it as `denseb` and add a registry row.
echo.
echo  Either way runs\ckpt\m100_ko-en_300M_dense.pt is untouched, so nothing
echo  that already works can break.
echo =============================================================================
if not defined TL_NOPAUSE pause
exit /b 0

:NOPARENT
echo.
echo [STOP] runs\ckpt\m100_ko-en_300M_dense.pt is missing too.
echo        That is a much bigger problem than the _best file - every tied run
echo        in this repo initialises from it. Stop and check the checkpoint
echo        directory before running anything else.
if not defined TL_NOPAUSE pause
exit /b 1

:TRAINBAD
echo.
echo [STOP] training failed. Read the log under test_result\ before retrying.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
