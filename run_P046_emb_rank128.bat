@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P046_emb_rank128.bat -- [P046] embedding rank 256 -^> 128 : the largest remaining residency item
REM  Plan: test_plan\P046 (embedding rank reduction)
REM =============================================================================
REM
REM PRECONDITION: --emb-rank IMPLEMENTED 2026-08-07, plus a shape guard in init_from_dense.
REM
REM ***LONG UNATTENDED RUN. START IT AND WALK AWAY.*** About 3.5 GPU hours for one run.
REM
REM WHY THIS IS THE BIGGEST REMAINING MEMORY LEVER
REM   After int8 (P034 stage 3) mC residency is 87.1 MB and 32.0 MB of that is
REM   emb.weight in fp32 - the ternary part already shrank, the embedding did not.
REM   emb = V*E + E*dim, so E is LINEAR in the embedding size:
REM     E=256 -^> 8,585,216 params (32.8 MiB fp32)
REM     E=128 -^> 4,292,608 params (16.4 MiB fp32)   exactly half
REM   Computed effect: residency 87.1 -^> 70.7 MB = ***-18.8 percent***,
REM   packed 13.12 -^> 12.25 MB (reduction 2.07x -^> 2.22x).
REM   For comparison, g16 (P045) buys only -5.3 percent for the same 3.5 hours.
REM
REM ***EXPECTATION - WRITE IT DOWN FIRST.***
REM   +0.02 to +0.08 worse. The output head is tied to the embedding, so logits
REM   pass through a rank-E matrix - at E=128 a 32,768-way softmax is squeezed
REM   through rank 128. Under +0.024 means residency -18.8 percent is nearly free.
REM
REM ***THE BIG CONFOUND - READ THIS.***
REM   --init-from cannot copy the embedding because the shape differs. The code
REM   now SKIPS it and prints a loud [init] warning instead of crashing. So the
REM   embedding starts from random while attention and MLP are inherited.
REM   ***That means this is NOT a strict single-variable experiment.*** The delta
REM   mixes 'E halved' with 'embedding not parent-initialised'. If the result is
REM   ambiguous, an --init-from-free control is needed (two more runs).
REM
REM ***THE CONTROL IS NOT RE-RUN.*** mC_wsd from result 024 is the same configuration except --emb-rank.
REM   Condition matching is therefore critical: sched=wsd / anneal_end=0.80 /
REM   kd_every=4 / pool 600M exact / seed 1337.
REM   ***CHECK THOSE IN THE LOG HEADER BEFORE TRUSTING ANY DELTA.***
REM
REM MEASUREMENT: quality only. Wall clock is NOT comparable to the control
REM   (different session). Read 'final', never 'best' (result 015 flipped a sign).
REM   grad_max comes from the json, not the printed 10-step sample.
REM
REM ERRORLEVEL POLICY: training is the prerequisite, so it stops the batch.
REM =============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL

echo =============================================================
echo [P046] embedding rank 256 -^> 128 : the largest remaining residency item
echo =============================================================
python scripts\runlog.py --name P046_mC_e128 --note "[P046] embedding rank 256 -^> 128 : the largest remaining residency item"

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo =============================================================
echo [1/2] train
echo =============================================================
python scripts\runlog.py --name P046_mC_e128 --note "[1/2] train"
python scripts\runlog.py --name P046_mC_e128 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --emb-rank 128 --tag mC_e128
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [2/2] paired comparison against mC_wsd
echo =============================================================
python scripts\runlog.py --name P046_mC_e128 --note "[2/2] paired comparison against mC_wsd"
python scripts\runlog.py --name P046_mC_e128 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_e128
if errorlevel 1 echo [WARN] paired_eval failed - checkpoint is on disk, re-run this step alone

python scripts\runlog.py --name P046_mC_e128 --note "=================================================================" "WHAT TO RECORD" "  1. final val, NOT best." "  2. the paired_eval delta and t value against mC_wsd." "  3. grad_max from the json." "  4. the report() block - the ternary/embedding parameter counts." "  5. the header conditions. If any differ from mC_wsd the delta is INVALID." "" "HOW TO READ IT" "  delta under +0.024" "      -^> ACCEPT for review. residency -18.8 percent for free." "  +0.024 to +0.08" "      -^> a real tradeoff. Worth it only if the deployment target is memory" "         constrained (see 08_paper_review section 3, the ESP32 table)." "  above +0.08" "      -^> reject at E=128. Try E=192 (-9.4 percent residency) or close the axis." "  ***ALSO CHECK*** the [emb] and [init] warning lines. If the [init] warning is" "  absent, the shape guard did not fire and something is wrong." "" "LIMITS: one seed / E=128 only / ***the parent-init confound above*** / the" "  -18.8 percent is COMPUTED, confirm with mem_runtime.py separately / the" "  logit-rank penalty depends on vocab size, and result 025 closed vocab" "  reduction so vocab stays at 32,768." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:BADKWARGS
echo.
echo [STOP] cli.py passes a keyword its target function does not accept.
exit /b 6

:NOCTRL
echo.
echo [STOP] control runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt is missing.
exit /b 5

:TRAINBAD
echo.
echo [STOP] training failed. Nothing to compare.
exit /b 4

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
exit /b 9
