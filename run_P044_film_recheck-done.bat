@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P044_film_recheck.bat -- P044 : is FiLM worth 0.13 MB in the CURRENT
REM                               candidate configuration
REM  Plan: test_plan\P044_...md
REM =============================================================================
REM
REM PRECONDITION: none. --mlp-film has existed since v6. Nothing to implement.
REM
REM ***THIS IS A LONG UNATTENDED RUN. START IT AND WALK AWAY.*** About 3.5 hours.
REM   It needs no decisions and touches no other experiment's output.
REM
REM WHAT THIS TESTS
REM   FiLM modulates the shared MLP hidden state per layer: h*(1+gamma)+beta.
REM   It costs about 65K parameters = 0.13 MB, so the reduction ratio goes from
REM   2.07x to 2.06x. Essentially free.
REM   Layer.__init__ already wires it for tied layers, but the current
REM   candidates mA and mC both have it OFF. It has never been in the final
REM   combination.
REM
REM WHY NOW - THE TOOL CAUGHT UP
REM   Old measurements were both BELOW the 0.024 resolution:
REM     t_film  3.9420 vs t_base 3.9558  = -0.0138  (plain, no KD)
REM     t_all   3.8188 vs t_kdinit 3.8253 = -0.0065 (with KD, but LoRA+FiLM together)
REM   Averaged val could not decide. paired_eval.py now gives SE 0.0005, which
REM   is one twentieth of sigma (result 021), so a -0.005 signal is readable.
REM
REM ***EXPECTATION - AND WHY IT MATTERS THAT IT IS SMALL.***
REM   Expect -0.005 to -0.015. ***A small win IS the success case here.***
REM   This experiment asks "can 0.13 MB buy a little quality", not "is there a
REM   big win". If you read it expecting a big number you will call a success a
REM   failure. If it comes out beyond -0.024, be suspicious and check the
REM   conditions matched.
REM
REM ***THE CONTROL IS NOT RE-RUN.*** mC_wsd from result 024 (final 3.6442) is
REM   the same configuration. That makes condition matching critical:
REM   sched=wsd / anneal_end=0.80 / kd_every=4 / pool 600M / seed 1337.
REM   ***CHECK THOSE IN THE LOG HEADER BEFORE TRUSTING THE COMPARISON.***
REM
REM ALSO CHECK: the report() block. Result 026 found that annealed LoRA was
REM   still being charged in the memory accounting even at scale zero. Confirm
REM   FiLM shows up where you expect and costs what you expect.
REM
REM COST: about 3.5 GPU hours for one run, plus a few minutes for paired_eval.
REM ERRORLEVEL POLICY: training is the prerequisite, so it stops the batch.
REM =============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL

echo =============================================================
echo [P044] FiLM in the current candidate - is 0.13 MB worth it
echo =============================================================
python scripts\runlog.py --name P044-film --note "[P044] FiLM in the current candidate - is 0.13 MB worth it"

echo.
echo =============================================================
echo [1/2] mC_film - mC_wsd plus --mlp-film, nothing else changed
echo       CHECK THE HEADER: sched=wsd, anneal_end=0.80, kd_every=4
echo =============================================================
python scripts\runlog.py --name P044-film --note "[1/2] mC_film - mC_wsd plus --mlp-film"
python scripts\runlog.py --name P044-film -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --mlp-film --tag mC_film
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [2/2] paired comparison against mC_wsd
echo =============================================================
python scripts\runlog.py --name P044-film --note "[2/2] paired comparison against mC_wsd"
python scripts\runlog.py --name P044-film -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_film
if errorlevel 1 echo [WARN] paired_eval failed - the checkpoint is on disk, re-run this step alone

python scripts\runlog.py --name P044-film --note "=================================================================" "WHAT TO RECORD" "  1. final val for mC_film, NOT best. Result 015 flipped a sign that way." "  2. the paired_eval delta against mC_wsd (3.6442) and its t value." "  3. grad_max from the json, not the printed 10-step sample." "  4. the report() block - what FiLM costs and whether it is charged where" "     you expect. Result 026 found annealed LoRA being charged at scale zero." "  5. the header conditions. If sched or anneal_end or kd_every differ from" "     mC_wsd, the comparison is INVALID - say so instead of reporting a delta." "" "HOW TO READ IT" "  delta below -0.010 and t significant" "      -^> ACCEPT. 0.13 MB bought real quality. Consider promoting mlp_film" "         into the m100R1c preset." "  between -0.010 and 0" "      -^> record the observation, hold the decision. One seed means sigma" "         0.012 still applies even though paired removes eval noise." "  zero or worse" "      -^> KD already occupies that role. Close the line - that is an answer." "" "LIMITS: one seed / g8 only / the control was trained in a different session so" "  wall-clock is NOT comparable (quality is) / this says nothing about FiLM at" "  other tying strengths." "================================================================="
echo done.
pause
exit /b 0

:NOCTRL
echo.
echo =================================================================
echo [STOP] control checkpoint runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt
echo        is missing. Without it there is nothing to compare against.
echo =================================================================
pause
exit /b 5

:TRAINBAD
echo.
echo =================================================================
echo [STOP] training failed. Nothing to compare.
echo =================================================================
pause
exit /b 4

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
