@echo off
REM ===== LOGGING (added 2026-07-31) =====
REM   Every python command below is run through scripts\runlog.py, which prints to the
REM   console in real time AND appends to test_result\log_YYYYMMDD_NAME.txt line by line,
REM   flushing and fsync-ing as it goes. If this batch dies halfway, or the machine loses
REM   power, everything up to the last couple of seconds is already on disk.
REM   Losing the log of a long run costs the whole run, so this is not optional.
REM   Exit codes pass through unchanged, so every `if errorlevel` below still works.

REM ===== P031 : depth extrapolation - loop the middle block R times at INFERENCE =====
REM   Plan: test_plan\P031
REM
REM ***** PREREQUISITE NOT YET IMPLEMENTED *****
REM   This batch needs a --infer-repeat flag that does not exist yet. The guard below
REM   detects that and exits cleanly instead of producing garbage.
REM   Implementation needed (see the plan P031 implementation section):
REM     1. TMTConfig.infer_repeat (default 1.0)
REM     2. transformer.forward() loops the middle range R times
REM        - decide KV recompute vs reuse for CLA owners (default: recompute)
REM        - fractional R repeats a PREFIX of the middle block (front/back/even variants)
REM     3. --infer-repeat / --repeat-where flags on eval and generate
REM   R=1.0 MUST reproduce the existing numbers bit-for-bit. If it does not, the
REM   implementation is wrong and nothing below means anything.
REM
REM WHY BOTHER: cost is near zero (no training, eval only) and both outcomes are useful.
REM   degrades -^> confirms the tied layers learned POSITION-SPECIFIC functions, which gives
REM              result 006's "tying gap is a capacity ceiling" an actual mechanism
REM   improves -^> a quality lever that costs ZERO extra memory, which is exactly what
REM              CLAUDE.md line 1 asks for (optimise memory, spend compute freely)
REM
REM   HONEST PREDICTION: degradation is more likely. Every prior work where depth
REM   extrapolation worked TRAINED with a randomised loop count. We did not.
REM   And R BELOW 1 may well be the useful direction - same memory, half the latency.
REM
REM COST: eval only. 3 models x 6 R values x a few seconds each = tens of minutes.

echo ============================================================
echo [P031] depth extrapolation : middle block x R at inference
echo ============================================================

echo.
echo [guard] checking whether --infer-repeat exists
python -c "import sys; sys.path.insert(0,'.'); from tinylm.config import TMTConfig; sys.exit(0 if hasattr(TMTConfig(),'infer_repeat') else 3)"
if errorlevel 3 goto NOTIMPL
if errorlevel 1 echo [WARN] guard check errored - continuing anyway

echo.
echo [0] sanity: R=1.0 must reproduce the known value exactly
REM   mA_g4s34_k4 val must come out 3.7003. If it does not, STOP - the loop is wrong.
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mA_g4s34_k4 --infer-repeat 1.0
if errorlevel 1 echo [WARN] R=1.0 check failed - do NOT trust anything below

echo.
echo ============================================================
echo SHRINK direction (R below 1) - cheaper inference, same memory
echo   predicted to degrade GRACEFULLY. If so we get a quality/latency dial for edge.
echo ============================================================
REM Loops are unrolled on purpose: cmd for-loops need a percent sign, which this repo bans
REM in .bat files. Unrolled also lets you REM out individual runs, which is how these
REM batches actually get used.
echo --- R=0.5 ---
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mA_g4s34_k4 --infer-repeat 0.5
if errorlevel 1 echo [WARN] mA_g4s34_k4 R=0.5 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mC_g8_k4 --infer-repeat 0.5
if errorlevel 1 echo [WARN] mC_g8_k4 R=0.5 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch dense --data ko-en --tokens 300M --tag p6d --infer-repeat 0.5
if errorlevel 1 echo [WARN] p6d R=0.5 failed - continuing
echo --- R=0.75 ---
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mA_g4s34_k4 --infer-repeat 0.75
if errorlevel 1 echo [WARN] mA_g4s34_k4 R=0.75 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mC_g8_k4 --infer-repeat 0.75
if errorlevel 1 echo [WARN] mC_g8_k4 R=0.75 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch dense --data ko-en --tokens 300M --tag p6d --infer-repeat 0.75
if errorlevel 1 echo [WARN] p6d R=0.75 failed - continuing

echo.
echo ============================================================
echo EXTRAPOLATE direction (R above 1) - more compute, same memory
echo   predicted to degrade. g8 has stronger sharing than g4, so if sharing helps
echo   extrapolation, mC should tolerate it better than mA. p6d (no sharing) is the control.
echo ============================================================
echo --- R=1.25 ---
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mA_g4s34_k4 --infer-repeat 1.25
if errorlevel 1 echo [WARN] mA_g4s34_k4 R=1.25 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mC_g8_k4 --infer-repeat 1.25
if errorlevel 1 echo [WARN] mC_g8_k4 R=1.25 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch dense --data ko-en --tokens 300M --tag p6d --infer-repeat 1.25
if errorlevel 1 echo [WARN] p6d R=1.25 failed - continuing
echo --- R=1.5 ---
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mA_g4s34_k4 --infer-repeat 1.5
if errorlevel 1 echo [WARN] mA_g4s34_k4 R=1.5 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mC_g8_k4 --infer-repeat 1.5
if errorlevel 1 echo [WARN] mC_g8_k4 R=1.5 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch dense --data ko-en --tokens 300M --tag p6d --infer-repeat 1.5
if errorlevel 1 echo [WARN] p6d R=1.5 failed - continuing
echo --- R=2.0 ---
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mA_g4s34_k4 --infer-repeat 2.0
if errorlevel 1 echo [WARN] mA_g4s34_k4 R=2.0 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch tied --data ko-en --tokens 300M --tag mC_g8_k4 --infer-repeat 2.0
if errorlevel 1 echo [WARN] mC_g8_k4 R=2.0 failed - continuing
python scripts\runlog.py --name P031 -- python run100m.py eval --arch dense --data ko-en --tokens 300M --tag p6d --infer-repeat 2.0
if errorlevel 1 echo [WARN] p6d R=2.0 failed - continuing

echo.
echo ============================================================
echo REFERENCE (R=1.0, already measured - do not re-run, just compare against these)
echo   mA_g4s34_k4  3.7003     mC_g8_k4  3.6862     p6d  3.7045
echo.
echo JUDGEMENT - sigma is 0.012, so the resolution is 0.024
echo   R^>1 improves by more than 0.024  -^> NEW LEVER. Escalate to training with randomised R
echo   R^>1 degrades by less than 0.024  -^> extrapolation does not break. Randomised training
echo                                        might work. Conditional follow-up.
echo   R^>1 degrades a lot / diverges    -^> position-specific functions confirmed. This is the
echo                                        MECHANISM behind the tying gap. Record and close.
echo   R^<1 degrades gracefully          -^> quality/latency dial for edge. Connect to P030.
echo   mC tolerates better than mA      -^> sharing strength correlates with extrapolability.
echo                                        That sets the direction for randomised training.
echo.
echo ALSO: fractional R repeats only PART of the middle block, and WHICH part matters.
echo   Do not generalise from one placement - the plan asks for front/back/even variants.
echo ================================================================
echo done.
pause
exit /b 0

:NOTIMPL
echo.
echo ================================================================
echo [STOP] --infer-repeat is not implemented yet, so this batch cannot run.
echo.
echo   TMTConfig has no infer_repeat field. See the REM header at the top of this file
echo   and test_plan\P031 for exactly what to implement (3 small changes).
echo.
echo   Suggested order:
echo     1. implement TMTConfig.infer_repeat + the forward() loop + the CLI flags
echo     2. run run_smoke.bat  (R=1.0 must be bit-identical to before)
echo     3. re-run THIS batch
echo.
echo   Nothing was measured. No files were written.
echo ================================================================
pause
