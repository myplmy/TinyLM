@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P046_emb_rank128.bat -- [P046] embedding rank 256 -^> 128, RE-MEASURED
REM                              with the SVD truncation transplant.
REM  Plan: test_plan\P046 / First attempt: result 030 (VERDICT IMPOSSIBLE)
REM =============================================================================
REM
REM PRECONDITION: --emb-rank (2026-08-07) plus _svd_emb_init in init_utils.py.
REM
REM ***LONG UNATTENDED RUN.*** About 3.5 GPU hours for one run.
REM ***THIS IS A RE-MEASUREMENT.*** The first attempt is result 030 and it was
REM   VERDICT IMPOSSIBLE, not a rejection. Read that before reading this log.
REM
REM WHY THE FIRST ATTEMPT DID NOT COUNT
REM   --init-from could not copy the embedding because the shape differed, so
REM   the embedding started from RANDOM while attention and MLP were inherited.
REM   Three signs, all pointing the same way:
REM     step 0 ce 10.4051 = ln(32768) = uniform output (mC_g16 the same night: 7.7742)
REM     grad_max 19.32 against a 0.847 baseline - CLAUDE.md says over 10 is a
REM       TRAINING problem, not an architecture verdict
REM     three [init] warnings already said 'embedding starts from random'
REM   The delta +0.1768 measured 'the initialisation broke', not 'E=128 is bad'.
REM
REM WHAT CHANGED
REM   _svd_emb_init does an Eckart-Young optimal low-rank approximation of the
REM   EFFECTIVE embedding  W = emb (V x E) @ emb_up (E x dim):
REM     W ~ U_k S_k Vh_k  -^>  emb' = U_k sqrt(S_k),  emb_up' = sqrt(S_k) Vh_k
REM   The head is TIED to the embedding (result 025), so approximating W is the
REM   right object - truncating emb alone would break the output side.
REM   ***This does not make E=128 free.*** The logit rank is still capped at E.
REM   It removes the initialisation handicap and nothing else.
REM
REM ***GATE G-init - CHECK THESE THREE BEFORE READING ANY DELTA***
REM   1. the log contains  [init] embedding SVD truncation transplant - E 256 -^> 128
REM      ***If instead you see the 'starts from random' warning, STOP.*** The
REM      transplant did not fire and this is result 030 all over again.
REM   2. step 0 ce is BELOW 8.5. (result 030 had 10.4051; a healthy parent-init
REM      run the same night had 7.7742.)
REM   3. grad_max from the json is BELOW 3. Over 10 = VERDICT IMPOSSIBLE again.
REM   Also record the 'spectrum energy retained' percentage the transplant prints.
REM   ***That number is new information*** - it says how much of the effective
REM   embedding actually lives in the top 128 directions, and it predicts the
REM   floor of the quality cost independently of the run.
REM
REM ***EXPECTATION - WRITE IT DOWN FIRST***
REM   +0.02 to +0.08 worse, now that initialisation is fixed. Under +0.024 means
REM   int8 residency minus 18.8 percent is nearly free.
REM   ***Quote the deployment path.*** Result 032 section 4.3: E=128 is first on
REM   INT8 residency (-18.8 percent) but only -3.6 percent on fp32, and it is the
REM   WORST lever on packed. Trap 24 - the ranking flips with the path.
REM
REM ***NEW TAG mC_e128svd.*** The old mC_e128 checkpoint is kept so the two
REM   initialisations can be compared. Do not overwrite it.
REM
REM ***THE CONTROL IS NOT RE-RUN.*** mC_wsd from result 024 differs by exactly
REM   one flag. sched=wsd / anneal_end=0.80 / decay_frac=0.20 / kd_every=4 /
REM   pool 600M exact / seed 1337 - check them in the header first.
REM
REM PRIORITY NOTE: the handoff ranks this LAST of the queued runs. It resolves an
REM   open VERDICT IMPOSSIBLE, which is worth doing, but the lever itself only
REM   pays off if int8 becomes the deployment path. Run it when the queue drains.
REM
REM ERRORLEVEL POLICY: training is the prerequisite, so it stops the batch.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

echo.
python scripts\runlog.py --name P046_mC_e128svd --note "=============================================================" "[P046] embedding rank 256 to 128, re-measured with SVD transplant" "============================================================="
python scripts\runlog.py --name P046_mC_e128svd --note "[P046] embedding rank 256 to 128, RE-MEASURED. Result 030 was VERDICT IMPOSSIBLE because the embedding started from random. Gate G-init below."

echo.
echo.
python scripts\runlog.py --name P046_mC_e128svd --note "[guard] cli.py call-keyword sanity"
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo.
python scripts\runlog.py --name P046_mC_e128svd --note "=============================================================" "[1/2] train" "============================================================="
python scripts\runlog.py --name P046_mC_e128svd --note "[1/2] train : --emb-rank 128 with SVD truncation transplant"
python scripts\runlog.py --name P046_mC_e128svd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --emb-rank 128 --tag mC_e128svd
if errorlevel 1 goto TRAINBAD

echo.
echo.
python scripts\runlog.py --name P046_mC_e128svd --note "=============================================================" "[2/2] paired comparison against mC_wsd and against the broken first run" "============================================================="
python scripts\runlog.py --name P046_mC_e128svd --note "[2/2] paired comparison : mC_wsd is the control, mC_e128 is the random-init version"
python scripts\runlog.py --name P046_mC_e128svd -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_e128svd
if errorlevel 1 echo [WARN] paired_eval failed - checkpoint is on disk, re-run this step alone

python scripts\runlog.py --name P046_mC_e128svd --note "=================================================================" "WHAT TO RECORD" "  0. ***GATE G-init, all three.*** SVD transplant line present / step 0 ce" "     below 8.5 / grad_max below 3. Any one failing means VERDICT IMPOSSIBLE" "     again and the delta must NOT be quoted." "  1. the 'spectrum energy retained' percentage. New information." "  2. final val, NOT best." "  3. the paired_eval delta, SE and t against mC_wsd." "  4. the report() block - ternary and embedding parameter counts." "  5. the header conditions against mC_wsd." "" "HOW TO READ IT" "  delta under +0.024" "      -^> ACCEPT for review. int8 residency -18.8 percent for free." "         ***But say 'int8'.*** On fp32 it is only -3.6 percent and on packed" "         it is the worst lever we have (result 032 section 4.3, trap 24)." "  +0.024 to +0.08" "      -^> a real trade. Worth it only if the deployment target is memory" "         constrained AND int8 is the chosen path." "  above +0.08" "      -^> reject at E=128. Try E=192 (-9.4 percent) or close the axis." "" "  ***ALSO COMPARE against result 030.*** The gap between +0.1768 (random init)" "  and this delta is the SIZE OF THE INITIALISATION HANDICAP, and that number" "  matters far beyond P046 - P048 and P049 carry the same handicap wherever" "  --init-from cannot transplant cleanly. ***P050 measures the same thing from" "  the other side.*** Read the two together." "" "LIMITS: one seed / E=128 only / the -18.8 percent is COMPUTED, confirm with" "  mem_runtime.py separately / vocab stays at 32,768 (result 025 closed vocab" "  reduction)." "================================================================="
echo.
python scripts\runlog.py --name P046_mC_e128svd --note "done."
if not defined TL_NOPAUSE pause
exit /b 0

:BADKWARGS
echo.
echo [STOP] cli.py passes a keyword its target function does not accept.
if not defined TL_NOPAUSE pause
exit /b 6

:NOCTRL
echo.
echo [STOP] control runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt is missing.
if not defined TL_NOPAUSE pause
exit /b 5

:NOPARENT
echo.
echo [STOP] parent runs\ckpt\m100_ko-en_300M_dense.pt is missing (SVD transplant needs it).
if not defined TL_NOPAUSE pause
exit /b 5

:TRAINBAD
echo.
echo [STOP] training failed. Nothing to compare.
if not defined TL_NOPAUSE pause
exit /b 4

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
