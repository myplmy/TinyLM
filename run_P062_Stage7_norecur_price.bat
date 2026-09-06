@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P062_Stage7_norecur_price.bat -- what does recursion cost in TIME?
REM ==========================================================================
REM
REM   THE TARGET CHANGED ON 2026-09-06
REM     the user fixed a speed floor: at least 15 tok/s on one CPU core
REM     (baselines B.19.3). Our 32 MiB winner d12_cla2_r20 runs 20 visits and
REM     the measured anchors at 20 visits are 12.5 to 13.2 tok/s. It misses.
REM
REM     Visits decide decode time. Recursion R2 doubles the visits. So
REM     recursion is free in memory and costs exactly 2x in time - and until
REM     this week nothing in the repo priced that second half.
REM
REM   WHAT WE DO NOT KNOW
REM     the recursion GAIN on this body. The numbers we quote (-0.0107 and
REM     -0.0172, result 058 s14) come from a 20-layer TIED body. The winner
REM     is 12-layer DENSE. Not one condition is shared. That is exactly the
REM     mistake 3:4 sparse made: a cost measured on one body, quoted for
REM     another, and wrong by 15 percent when finally measured.
REM
REM   ONE ARM. THE CONTROL ALREADY EXISTS.
REM     d12_cla2_r20 is the standard run. This arm drops --train-repeat and
REM     changes nothing else. 12 visits instead of 20.
REM
REM   WHAT IT BUYS IF THE COST IS SMALL
REM     residency 30.7 gives about 28.0 MiB (KV entries 10 gives 6)
REM     speed     12.5 to 13.2 gives about 21.8 tok/s, which clears the floor
REM
REM   PRE-REGISTERED VERDICT   delta = norecur minus recur, positive means
REM   recursion was worth something. Ruler: recursion 0.0018.
REM     at or below +0.0100   drop recursion. Buy +66 percent speed with it
REM     +0.0100 to +0.0250    grey. This becomes a user decision
REM     above +0.0250         recursion earns its keep. Find speed elsewhere
REM
REM   Threshold reasoning: depth 12 to 16 costs 7.8 MiB for -0.0389, i.e.
REM   0.00499 nats per MiB. Dropping recursion saves 2.7 MiB, so +0.0135
REM   would be break-even on memory alone. Speed rides on top, so the
REM   threshold is set conservatively at 0.0100.
REM
REM   NO --infer-repeat ANYWHERE. This arm was not trained with recursion,
REM   so matching it would evaluate a function it never learned (trap 39,
REM   pointing the other way).
REM
REM   COST: about 1.2h.   PLAN: test_plan/P062 (Korean filename) Stage7
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

timeout /t 15 /nobreak

python scripts\runlog.py --name P062_stage7_norecur_price --note "[1/2] d12_cla2 with no recursion - 12 visits instead of 20"
python scripts\runlog.py --name P062_stage7_norecur_price -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_norecur
if errorlevel 1 echo [WARN] training arm failed - continuing

python scripts\runlog.py --name P062_stage7_norecur_price --note "[2/2] paired_eval against the recursive winner - 600M cache, both pooled 600M"
python scripts\runlog.py --name P062_stage7_norecur_price -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --models d12_cla2_r20 d12_cla2_norecur
if errorlevel 1 echo [WARN] paired_eval failed - continuing

set TL_WB_TAG=d12_cla2_norecur
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

echo.
python scripts\runlog.py --name P062_stage7_norecur_price --note "=================================================================" "READ IN THIS ORDER" "1. json kv_visits must be 12 and kv_entries 6. If it says 20 and" "   10 the flag did not come off and this arm is a duplicate run." "2. runtime_plus_kv_mb. Expect near 28.0 against the winner's 30.7." "3. paired_eval delta. Compare with the three PRE-REGISTERED rows in" "   the header. Do not invent a threshold after seeing the number." "   Note the tool picks its own ruler - this pair is dense without" "   recursion versus dense with it, so read which ruler it printed." "4. NOTE the asymmetry: paired_eval evaluates both at their trained" "   setting here because neither flag is passed and only ONE of them" "   was trained with recursion. If the printed visit counts differ" "   between the two models that is CORRECT for this comparison." "5. if the cost clears the floor, P030 Stage5 should re-measure this" "   shape too - 21.8 tok/s is a model estimate, not a measurement." "================================================================="

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
