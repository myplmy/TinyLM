@echo off
REM =============================================================================
REM  P057 stage 2  -  retrain the model candidate WITHOUT KD
REM                   1 training run, about 2.8 hours
REM
REM  WHY THIS IS NOW UNBLOCKED
REM    The prerequisite was "REVIEW2 decides the standard condition". On
REM    2026-08-21 the user set the interim standard to B2, which is no-KD.
REM    That is enough to run this - the arm does not depend on whether B2 is
REM    finally confirmed, only on KD being out, and result 042 s12 settled that
REM    with a monotone 5-point alpha sweep.
REM
REM  WHAT IS WRONG WITH THE CURRENT CANDIDATE
REM    mC_d36_ag4 is our best residency model - 379.7 MB, 15.9 percent under
REM    the baseline, at a quality cost of +0.0078. But it was trained WITH KD,
REM    and its delta was measured against mC_wsd which is also a KD run. So the
REM    headline number belongs to a condition we have discarded.
REM
REM  THE REFERENCE IS mC_initonly, NOT mC_wsd
REM    mC_initonly is no-KD, full-val 3.6776, and we know its 2 sigma: 0.0034
REM    (result 049). Using mC_wsd would mix the KD effect into the delta.
REM
REM  PREDICTIONS, fixed in advance (plan P057 s2.4)
REM    R1  delta versus mC_initonly lands at +0.006 to +0.010. The KD-condition
REM        delta was +0.0078 and lever-by-KD interaction is 0.0002 (029 s6).
REM    R2  ternary 45.43M, packed 11.220 MB, residency 379.7 MB - all unchanged
REM    R3  reserved drops from 12.44 to about 5.1 GiB (KD removal is -7.41)
REM    R4  wall clock about 2.8h, down 18 percent from the KD run
REM    R5  grad_max near 0.7
REM    Adoption line stays +0.041, re-derived from residency -15.9 percent.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    The final model. That belongs to REVIEW3, after REVIEW2 closes.
REM    Compute: FLOPs still do not drop - report() has no attn_group term
REM    (trap 25). This buys memory, not speed.
REM    L2+L3: 379.7 MB is still 9.5 times the 40 MB target (plan P066).
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P057_stage2_nokd --note "=============================================================================" "P057 stage 2   model candidate retrained without KD   about 2.8 hours" "The best residency model was trained in a condition we have discarded." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P057_stage2_nokd --note "[1/2] mC_d36_ag4_nokd - 36 layers, attn-group 4, parent-init, NO KD."
python scripts\runlog.py --name P057_stage2_nokd -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --depth-init gate_scale --attn-group 4 --tag mC_d36_ag4_nokd
if errorlevel 1 echo [WARN] mC_d36_ag4_nokd failed - continuing

echo.
python scripts\runlog.py --name P057_stage2_nokd --note "[2/2] paired full-val against the no-KD baseline and the KD-trained twin"
python scripts\runlog.py --name P057_stage2_nokd -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_d36_ag4_nokd mC_d36_ag4
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
echo.
python scripts\runlog.py --name P057_stage2_nokd --note "=============================================================================" "READ IN THIS ORDER" "1. the [init] lines. Eight shared attention modules should print teacher" "   layer averages like [2,2,3,3] up to [16,16,17,17]. If they do not, the" "   transplant did not happen and nothing below is readable." "2. json kd must be false and attn_group must be 4 (trap 37)." "3. paired delta versus mC_initonly against R1, ruler 2 sigma = 0.0034." "4. ternary, packed and runtime_mb against R2. They must be UNCHANGED - the" "   structure did not move, only the training condition." "5. reserved against R3. About 5.1 GiB means KD removal transferred cleanly." "6. the delta between mC_d36_ag4_nokd and mC_d36_ag4 is the KD effect ON THIS" "   ARCHITECTURE. We have never had that number." "REMINDER  adoption line +0.041. This buys memory, not speed." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
