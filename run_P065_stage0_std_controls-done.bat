@echo off
REM =============================================================================
REM  P065 stage 0  -  train the REVIEW2 option B2 control NOW
REM                   1 training run (about 1.8h) plus a zero-training screen
REM
REM  WHAT THE USER DECIDED (2026-08-21)
REM    Interim standard = option B2. KD is removed - that part is settled by
REM    result 042 s12. But only ONE flag gets frozen into the standard:
REM        --opt-dtype bf16
REM    --micro-group stays OPEN because the user wants to explore it further,
REM    and --mlp-group stays OPEN because tying, depth and recursion all use
REM    it right now. Freezing either would turn every experiment on those axes
REM    into an off-standard condition.
REM    The standard is NOT final. It is confirmed only after the controls are
REM    measured - which is what this batch produces.
REM
REM  THE MICRO-GROUP CEILING (code audit, 2026-08-21)
REM    config.py line 110 asserts dim % g == 0 and ffn_dim % g == 0.
REM    TLinear in_features are only 768 and 2048, and gcd(768, 2048) = 256.
REM    So --micro-group 512 dies on the assert. Training-side exploration of
REM    that axis ends at 256, and 256 was already measured at -0.0007
REM    (result 036). Anything wider has to be screened without training -
REM    that is what call 3 does.
REM
REM  WHAT WAS SETTLED FIRST (both landed 2026-08-20)
REM    result 042 s12  KD removal CONFIRMED - alpha 0 to 0.7 is monotone and
REM                    alpha 0.1 is indistinguishable from no KD at all.
REM                    So the shared base of all three options is now measured.
REM    result 049      resolution is condition-dependent by 18x. For THIS
REM                    condition (tied, parent-init, no KD) 2 sigma is 0.0034.
REM                    That is the ruler these two runs get judged with.
REM
REM  THE ARM - exactly one flag differs from the reference
REM    mC_std2b  = mC_initonly + --opt-dtype bf16
REM    Reference mC_initonly already exists at full-val 3.6776 - not retrained.
REM    micro_group stays at the preset 128. mlp_group stays at 8.
REM
REM  WHAT bf16 ACTUALLY BUYS
REM    Nothing in packed size and nothing in residency - the optimiser state
REM    is not part of either. It buys about 1.02 GiB of TRAINING VRAM
REM    (result 035 s12). If P4 below fails, there is no reason to adopt B2.
REM
REM  PREDICTIONS, fixed in advance (plan P065 s4)
REM    P1  mC_std2b lands within 0.001 of mC_initonly. bf16 alone measured
REM        -0.0002 (result 035 s12). Outside 0.0034 - the no-KD 2 sigma from
REM        result 049 - means the cost is condition-dependent.
REM    P2  packed stays 13.050 MB. opt_dtype does not touch storage.
REM    P3  residency stays 451.5 MB. Same reason.
REM    P4  reserved lands at 4.0 to 4.6 GiB. THIS IS THE ONLY GAIN.
REM    P5  grad_max near 0.64. We never measured bf16 stability without KD.
REM
REM  !! DO NOT RESUME THIS BATCH
REM    --opt-dtype bf16 is not compatible with --resume (result 035 s12).
REM    If a run dies, start that arm over from the beginning.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether B2 is final. The user set it as INTERIM and will confirm only
REM    after all the controls are measured. This batch builds one of them.
REM    Also: call 3 regroups alpha on an ALREADY TRAINED model. That is a
REM    screen, not a verdict - training with a given micro_group and
REM    regrouping after training are different things (result 036 measured
REM    256 by training and got -0.0007).
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P065_stage0_controls --note "=============================================================================" "P065 stage 0   REVIEW2 option B and C controls   about 3.6 hours" "Pre-emptive. Neither run depends on the decision they unblock." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P065_stage0_controls --note "[1/3] option B2 control - mC_std2b - opt-dtype bf16 only. DO NOT RESUME."
python scripts\runlog.py --name P065_stage0_controls -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --opt-dtype bf16 --tag mC_std2b
if errorlevel 1 echo [WARN] mC_std2b failed - continuing

echo.
python scripts\runlog.py --name P065_stage0_controls --note "[2/3] paired full-val against the existing no-KD reference"
python scripts\runlog.py --name P065_stage0_controls -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_std2b
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P065_stage0_controls --note "[3/3] micro-group screen WITHOUT training - regroup alpha and measure common-text bpb"
python scripts\runlog.py --name P065_stage0_controls -- python scripts\diag_alpha_group.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_d36_ag4
if errorlevel 1 echo [WARN] alpha-group screen failed - continuing

echo.
echo.
python scripts\runlog.py --name P065_stage0_controls --note "=============================================================================" "READ IN THIS ORDER" "1. json opt_dtype must be bf16 AND micro_group must still be 128." "   If micro_group moved, the arm is not B2 (trap 37)." "2. mC_std2b vs mC_initonly. The ruler is 2 sigma = 0.0034, not 0.024." "3. reserved GB. That is the only thing bf16 buys - if it did not drop by" "   about 1 GiB there is no reason to adopt B2 at all." "4. packed and runtime_mb must be UNCHANGED from mC_initonly." "5. call 3: how far can alpha be coarsened before bpb moves? Note how many" "   tensors fell back to per-row - g512 cannot divide 768." "REMINDER  B2 is INTERIM. This batch does not confirm it." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
