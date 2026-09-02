@echo off
REM P067 stage 3  -  the Gemma no-KD control that stage 2 does not have.
REM About 6.3 hours.
REM
REM   WHY THIS EXISTS.  run_P067_stage2_gemma270m_full.bat trains ONE arm,
REM   G270Tfull, and compares its common-text bpb against mC_initonly_nc.
REM   Those two differ in FOUR ways at once: tokenizer, vocabulary size and
REM   therefore parameter count, KD on or off, and the micro-bs/accum shape.
REM   The difference cannot isolate the teacher.  The batch footer claims it
REM   answers "does a real external teacher beat our no-KD baseline" - that
REM   claim is broader than the design supports.
REM
REM   This was found by the external review in
REM   docs/20260901_model-quality-survey (the Korean-named report) section 2.4.
REM
REM   WHAT THIS ARM IS.  Byte-identical to stage 2 except that --kd,
REM   --kd-every, --kd-chunk, --teacher-dtype and --kd-teacher-hf are gone.
REM   Same tokenizer, same vocabulary, same shape, same seed, same steps.
REM   G270Tfull minus GT0full IS the teacher effect and nothing else.
REM
REM   COST NOTE.  The Qwen pair measured 470.3 min with KD and 336.8 without,
REM   a factor of 1.40.  Gemma KD is about 8.8 h, so this is estimated at
REM   about 6.3 h.  That is an EXTRAPOLATION across a different vocabulary,
REM   not a measurement.
REM
REM   VRAM.  The KD probe reserved 14.77 GiB with 0.23 headroom.  Removing KD
REM   removes the largest single term - the KL over the full vocabulary - so
REM   this should sit far below that.  The shape is NOT changed to exploit
REM   the freed memory: a different micro-bs would break the comparison.
REM
REM   INDEPENDENT VARIABLE: --kd and its four companions, removed.
REM
REM   WHY NO --no-ckpt.  The linter will note that a no-KD run normally gets
REM   it (result 051: -20.6 percent wall clock).  Not here.  G270Tfull runs
REM   WITH gradient checkpointing and the drift between the two settings is
REM   -0.0014, which is the same order as the effect we are trying to see.
REM   Matching the control to the arm beats saving an hour.
REM
REM   CROSS-COMPARISON.  Different tokenizer means different val token
REM   boundaries.  CE is NOT comparable to any native run (trap 2).
REM   Only scripts/common_bpb.py is valid.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P067_stage3_gemma_nokd_control --note "[1/3] train - the matched no-KD control, gemma tokenizer"
python scripts\runlog.py --name P067_stage3_gemma_nokd_control -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --ce-chunk 1024 --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 --tag GT0full
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=GT0full
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P067_stage3_gemma_nokd_control --note "[2/3] common-text bpb - the control and the KD arm together"
python scripts\runlog.py --name P067_stage3_gemma_nokd_control -- python scripts\common_bpb.py --preset m100R1c --models GT0full G270Tfull --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P067_stage3_gemma_nokd_control --note "[3/3] and the native baseline for the deployment view only"
python scripts\runlog.py --name P067_stage3_gemma_nokd_control -- python scripts\common_bpb.py --preset m100R1c --models mC_initonly_nc
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P067_stage3_gemma_nokd_control --note "READ IN THIS ORDER" "1. grad_max from the json, not the printed g.  The 250-step probes read" "   36.9 with no KD and 118.8 and 488.8 with it - all three fail the" "   repository gate of 10.  If the full no-KD run also exceeds 10, the" "   instability belongs to the gemma-vocab student, not to KD, and that" "   is the single most useful thing this run can tell us." "2. G270Tfull minus GT0full.  THAT is the teacher effect.  Everything" "   else in step 2 and 3 is context." "3. the bpb ruler is 0.008 and it was fixed under NATIVE conditions." "   It is not the standard deviation of this condition.  A result inside" "   0.008 is undetermined, not negative." "4. do NOT compare val_loss or CE to any native run.  Different" "   tokenizer, different token boundaries." "5. one seed.  Whatever the sign, it is one seed." "6. mC_initonly_nc has a different vocabulary and parameter count.  Its" "   bpb is a deployment comparison, not a KD comparison."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
