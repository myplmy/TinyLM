@echo off
REM ===== P035 : anneal SHAPE - does the cooldown-QAT mechanism exist in our code at all =====
REM   Plan: test_plan\P035    Origin: test_result\015 section 2-(1)
REM
REM ***** WHAT THIS IS FOR *****
REM   P026 moved the anneal END POINT and found nothing: aligning it with the LR decay start
REM   was worth minus 0.0128, which is 1.1 sigma and therefore below the 0.024 resolution.
REM   The paper (arXiv 2509.22935) removes DUPLICATED updates between a full-precision phase
REM   and a separate QAT phase. Our anneal is a LINEAR RAMP - there is no such boundary, so
REM   there may have been no duplication to remove. Moving the end point cannot test that.
REM   This batch CREATES the duplication with a STEP anneal and asks whether alignment then
REM   starts to matter.
REM
REM   INDEPENDENT VARIABLE: anneal shape, linear to step. Transition point, schedule, steps,
REM   pool, seed and batch are all held at the result-015 values.
REM
REM ***** THE 2x2 - AND WHY ONLY TWO NEW RUNS *****
REM                     transition 0.60 (not aligned)   transition 0.80 (aligned)
REM     linear (have)   qb_wsd60   3.6275               qb_wsd80   3.6147
REM     step   (new)    qa_step60  ?                    qa_step80  ?
REM   The linear row already exists from result 015 and is reused as-is - same pool, same
REM   seed, same steps, same no-ckpt. So the whole 2x2 costs 2 runs, not 4.
REM
REM ***** HONEST PREDICTION (plan section 3) *****
REM   The step anneal is EXPECTED to be worse, which would show our ramp was already doing
REM   the right thing. But it may well land inside the 0.024 resolution, in which case the
REM   answer is "schedule shape does not matter at this scale" and the schedule line closes.
REM   Both outcomes are useful. Do not read a 1-sigma difference as a result.
REM
REM ***** PREREQUISITE *****
REM   --anneal-shape and --anneal-start. Implemented 2026-07-31, defaults unchanged
REM   (linear, start auto). The guard below confirms before burning 3.2 hours.
REM
REM COST: 2 runs x about 96 minutes = about 3.2h. VRAM 12.69GB reserved (measured, same config).
REM ERRORLEVEL POLICY: guard and prepare are hard stops. The runs and compares only warn.

echo ============================================================
echo [P035] anneal shape : linear ramp vs step transition
echo ============================================================

echo.
echo [guard] checking whether --anneal-shape is wired
python -c "import sys,pathlib; s=pathlib.Path('tinylm/cli.py').read_text(encoding='utf-8'); sys.exit(0 if '--anneal-shape' in s else 3)"
if errorlevel 3 goto NOTIMPL
if errorlevel 1 echo [WARN] guard check errored - continuing anyway

echo.
echo [prep] the 600M exact pool must be the same one result 015 used
python run100m.py prepare --data ko-en --tokens 600M --exact-cache
if errorlevel 1 goto ERROR

echo.
echo ============================================================
echo [1/2] qa_step60 : STEP anneal at 0.60, wsd decay starts 0.80  (NOT aligned)
echo   control for this run is qb_wsd60 (3.6275) - same transition point, linear ramp
echo ============================================================
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --pool-tokens 600M --exact-cache --sched wsd --decay-frac 0.2 --anneal-shape step --anneal-start 0.60 --tag qa_step60
if errorlevel 1 echo [WARN] qa_step60 failed - continuing to the second run

echo.
echo ============================================================
echo [2/2] qa_step80 : STEP anneal at 0.80, wsd decay starts 0.80  (ALIGNED)
echo   control for this run is qb_wsd80 (3.6147) - same transition point, linear ramp
echo ============================================================
python run100m.py train --arch dense --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --no-ckpt --pool-tokens 600M --exact-cache --sched wsd --decay-frac 0.2 --anneal-shape step --anneal-start 0.80 --tag qa_step80
if errorlevel 1 echo [WARN] qa_step80 failed - continuing

echo.
echo ============================================================
echo COMPARES
echo ============================================================
echo --- shape effect at 0.60 : linear vs step ---
python run100m.py compare --tag qb_wsd60 --vs qa_step60
if errorlevel 1 echo [WARN] compare failed - continuing
echo --- shape effect at 0.80 : linear vs step ---
python run100m.py compare --tag qb_wsd80 --vs qa_step80
if errorlevel 1 echo [WARN] compare failed - continuing
echo --- alignment effect INSIDE the step row (this is the paper mechanism) ---
python run100m.py compare --tag qa_step60 --vs qa_step80
if errorlevel 1 echo [WARN] compare failed - continuing

echo.
echo ================================================================
echo READ IN THIS ORDER - final val only, never best (result 015 section 2-(6))
echo.
echo   0. verify the [sched] line printed shape=step and the right transition step,
echo      and that run 2 says aligned while run 1 says not aligned
echo   1. SHAPE  qa_step60 vs qb_wsd60, and qa_step80 vs qb_wsd80
echo        step worse by over 0.024 -^> the linear ramp was buying something real.
echo                                    P026's null result is explained.
echo        both inside 0.024        -^> shape does not matter at this scale.
echo                                    CLOSE the schedule line, move budget to P023 / P033.
echo        step BETTER              -^> opposite of the prediction. Do not act on one run
echo                                    each - a repeat run comes first.
echo   2. ALIGNMENT INSIDE THE STEP ROW  qa_step60 vs qa_step80
echo        this is the actual paper mechanism. In the linear row it was minus 0.0128 (1.1
echo        sigma, not detectable). If the step row shows a much larger gap, the mechanism
echo        is REAL and our ramp had already absorbed it.
echo   3. grad_max from the json, not the printed bar. A step transition is where an
echo      instability would show up, and it may show in the eval curve even if the final
echo      val is unchanged. Record it either way.
echo.
echo REFERENCE (result 015, final val, same pool and seed)
echo   qb_cos 3.7030   qb_wsd60 3.6275   qb_wsd80 3.6147   qb_wsd80_s85 3.7080
echo   sigma is 0.012, resolution 0.024. Nothing closer than that gets ranked.
echo ================================================================
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: prepare failed, so the pool is not guaranteed to match the result 015
echo        runs. Comparing against them would be invalid, so nothing was trained.
pause
exit /b 1

:NOTIMPL
echo.
echo ================================================================
echo [STOP] --anneal-shape is not wired into tinylm\cli.py, so this batch cannot run.
echo.
echo   Needed: --anneal-shape linear,step and --anneal-start F on the train subcommand,
echo   passed through to trainer.train(). Defaults must reproduce the old behaviour
echo   exactly, or every existing log becomes incomparable.
echo.
echo   Suggested order:
echo     1. wire the flags
echo     2. run run_smoke.bat  (defaults must give the same val as before)
echo     3. re-run THIS batch
echo.
echo   Nothing was measured. No files were written.
echo ================================================================
pause
exit /b 3
