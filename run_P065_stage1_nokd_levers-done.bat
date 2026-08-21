@echo off
REM =============================================================================
REM  P065 stage 1  -  every lever that was never measured WITHOUT KD
REM                   2 full runs plus a 250-step speed pair, about 4.4 hours
REM
REM  THE PROBLEM, IN ONE LINE FROM OUR OWN BASELINE TABLE
REM    EXPERIMENT_BASELINES s2.2c is headed:
REM        "memory lever family, ko-en, 600M pool, 300M training,
REM         ALL RUNS KD k4 + parent-init + wsd"
REM    The whole lever table is a KD table. Exactly one lever has ever been
REM    re-measured without KD: mlp-group 16 (result 029 s6, +0.0163 vs +0.0161).
REM    KD is now removed from the standard. Everything else in that table is
REM    an assumption.
REM
REM  WHAT B2 SPECIFICALLY MADE NECESSARY
REM    B2 deliberately leaves --micro-group OPEN as an experiment axis. An open
REM    axis with no no-KD measurement is not an axis, it is a hole. Arm A fills
REM    it. And removing KD returned 7.41 GiB of VRAM, which may finally open
REM    --no-ckpt - result 034 s10 blocked it at 0.62 GiB of headroom under KD.
REM
REM  THE ARMS - one flag each, against the existing mC_initonly at 3.6776
REM    A  mC_mg256_nokd   --micro-group 256    2289 steps   quality + packed
REM    B  mC_e192_nokd    --emb-rank 192       2289 steps   quality + packed
REM    C1 mC_ck250        (nothing)             250 steps   SPEED/VRAM ONLY
REM    C2 mC_nock250      --no-ckpt             250 steps   SPEED/VRAM ONLY
REM
REM  WHY C IS ONLY 250 STEPS
REM    Gradient checkpointing is mathematically an identity - it only changes
REM    recomputation. There is nothing to learn about quality. Repo rule:
REM    short runs are read for speed and VRAM, never for quality.
REM    C1 and C2 run back to back ON PURPOSE. Session drift is 7.5 percent on
REM    ms/step and 0.787 GiB on reserved (trap 41), so the only valid speed
REM    comparison is a pair inside one session. Do NOT compare either of them
REM    to mC_initonly - that run has no ms_step_median at all.
REM
REM  PREDICTIONS, fixed in advance (plan P065 s1.4)
REM    Q1  mC_mg256_nokd delta between -0.002 and +0.002 (KD gave -0.0007)
REM    Q2  its packed = 12.578 MB
REM    Q3  mC_e192_nokd delta between +0.010 and +0.020 (KD gave +0.0154)
REM    Q4  its packed = 12.613 MB, residency about 441 MB
REM    Q5  mC_nock250 reserved 7.5 to 8.5 GiB (5.07 plus the 2.90 ckpt cost)
REM    Q6  mC_nock250 is 10 to 25 percent faster than mC_ck250
REM    Q7  the two 250-step arms agree on final val within 0.01
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether B2 is confirmed - that is stage 0 (mC_std2b).
REM    The best micro_group - the grid has only two legal points, 128 and 256,
REM    because config.py line 110 needs g to divide both 768 and 2048.
REM    Anything about architecture - levers are standard-condition, not model.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P065_stage1_nokd --note "=============================================================================" "P065 stage 1   levers never measured without KD   about 4.4 hours" "The whole lever table is a KD table. KD is gone. Re-measure." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P065_stage1_nokd --note "[1/5] arm A - micro-group 256 without KD. B2 left this axis open, so it needs a no-KD point."
python scripts\runlog.py --name P065_stage1_nokd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --micro-group 256 --tag mC_mg256_nokd
if errorlevel 1 echo [WARN] mC_mg256_nokd failed - continuing

echo.
python scripts\runlog.py --name P065_stage1_nokd --note "[2/5] arm B - emb-rank 192 without KD. KD condition gave +0.0154."
python scripts\runlog.py --name P065_stage1_nokd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --emb-rank 192 --tag mC_e192_nokd
if errorlevel 1 echo [WARN] mC_e192_nokd failed - continuing

echo.
python scripts\runlog.py --name P065_stage1_nokd --note "[3/5] arm C1 - 250 steps, checkpointing ON. This is the SPEED reference for C2."
python scripts\runlog.py --name P065_stage1_nokd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --tag mC_ck250
if errorlevel 1 echo [WARN] mC_ck250 failed - continuing

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P065_stage1_nokd --note "[4/5] arm C2 - 250 steps, --no-ckpt. Removing KD returned 7.41 GiB; does it fit now?"
python scripts\runlog.py --name P065_stage1_nokd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --no-ckpt --tag mC_nock250
if errorlevel 1 echo [WARN] mC_nock250 failed - continuing

echo.
python scripts\runlog.py --name P065_stage1_nokd --note "[5/5] paired full-val for arms A and B against the no-KD baseline"
python scripts\runlog.py --name P065_stage1_nokd -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_mg256_nokd mC_e192_nokd
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
echo.
python scripts\runlog.py --name P065_stage1_nokd --note "=============================================================================" "READ IN THIS ORDER" "1. json micro_group and emb_rank on arms A and B. If a flag did not land," "   nothing below means anything (trap 37)." "2. paired deltas against 2 sigma = 0.0034, NOT 0.024. Q1 and Q3." "3. packed and runtime_mb against Q2 and Q4. Accounting check." "4. arm C: reserved on C2 against Q5. Over 12 GiB means the estimate is wrong." "5. arm C: ms_step_median C2 versus C1 - the ONLY valid speed pair here." "   Both ran in this session, back to back. Do not bring in other runs." "6. arm C: the two final val values should agree within 0.01 (Q7). They are" "   NOT a quality measurement - checkpointing is a mathematical identity." "REMINDER  if Q1 fails, the lever depends on KD and result 029 s6 needs a" "          condition column added to the whole lever table." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
