@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P022B_stage2_optstate.bat -- [P022B stage 2] AdamW optimizer STATE in
REM                                   BF16. DeepSeek-V3 section 3.3.3.
REM  Plan: test_plan\P022B section 4 stage 2  (read section 2.3 BEFORE running)
REM =============================================================================
REM
REM PRECONDITION: --opt-dtype and tinylm\train\adamw_bf16.py, both 2026-08-07.
REM   ***Code changed - run run_smoke_check.bat first.***
REM
REM ***ABOUT 4.2 GPU HOURS in three parts: minutes, 40 min, then 3.5 h.***
REM ***DO NOT WALK AWAY BEFORE PART [2/4] FINISHES.*** Parts 1 and 2 are the
REM   cheap gates that decide whether the 3.5 hour run is worth starting.
REM
REM WHY - this is the MEMORY half of the DeepSeek paper, and memory is our goal
REM   Technical report section 3.3.3, verbatim: BF16 for the first and second
REM   moments 'without incurring observable performance degradation', with
REM   master weights and gradients kept in FP32. Our trainable parameters are
REM   about 63.5M, so AdamW carries 2 x 4B x 63.5M = about 508 MB of state.
REM   In BF16 that is about 254 MB returned.
REM   ***Unlike FP8 GEMM, this serves the project's first-line goal.***
REM   CLAUDE.md line one: memory optimisation, not compute.
REM
REM ***WHAT CHANGES AND WHAT DOES NOT***
REM   changes:  exp_avg and exp_avg_sq storage dtype. That is all.
REM   unchanged: master weight p, gradient p.grad, and ***all arithmetic***.
REM   Every step lifts the state to fp32, updates, and lowers it only to store.
REM
REM ***THREE MODES, AND WHY THERE ARE THREE***
REM   fp32   torch.optim.AdamW(fused=True). The default. ***Bit identical.***
REM   fp32c  our AdamWLowPrec with fp32 state. ***THE SELF CHECK.***
REM   bf16   our AdamWLowPrec with bf16 state. The experiment.
REM   Without fp32c we could not tell an implementation bug from a dtype effect.
REM   The formula was verified against torch _single_tensor_adamw in numpy:
REM   max absolute difference 1.1e-16 over 2289 steps = machine epsilon.
REM
REM ***PREDICTIONS - WRITTEN BEFORE THE RUN (plan section 2.2)***
REM   S1 fp32c and fp32 printed losses agree to 4 decimals.
REM      ***Bit identity is NOT expected*** - one is a fused kernel.
REM   S2 bf16 VRAM reserved is about 0.25 GB lower. json opt_state_mb measures it.
REM   S3 quality delta inside the 0.024 resolution.
REM   S4 ms/step within about +0.5 percent. The optimizer is 0.13 percent of a
REM      step (result 033), so even a 5x slower one barely shows.
REM   S5 --no-ckpt STILL does not open. 254 MB is not enough - see the analysis
REM      report section 4.1. Do not expect this to rescue P042.
REM
REM ***THIS IS THE ONE EXPERIMENT THAT CAN FAIL QUIETLY.***
REM   Everything else either dies or prints an obviously wrong number. A
REM   low-precision optimizer can draw a plausible loss curve and still drift.
REM   ***Plan section 2.3 has the watch list. Read it before starting part 3.***
REM   Short version: the [opt] line must exist and say about 254 MB, step 0 ce
REM   must match the control, skip must stay 0, and val must not rise twice in
REM   a row.
REM
REM ERRORLEVEL POLICY: part 1 is a hard gate - a broken optimizer must not reach
REM   the 3.5 hour run. Parts 2 and 3 warn and continue.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

echo =============================================================
echo [P022B-2] AdamW optimizer state in BF16  (about 4.2 h, three parts)
echo =============================================================
python scripts\runlog.py --name P022B_stage2 --note "[P022B stage 2] AdamW optimizer state in BF16. DeepSeek-V3 section 3.3.3. Read plan section 2.3 for the watch list."

echo.
echo [guard] flags actually exist in the parser
python scripts\check_batch_flags.py
if errorlevel 1 goto BADFLAGS

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo =============================================================
echo [1/4] GATE S-a : tiny 30 steps x 3 modes. fp32 vs fp32c must agree.
echo =============================================================
python scripts\runlog.py --name P022B_stage2 --note "[1/4] GATE S-a : tiny, fp32 vs fp32c vs bf16. Compare printed losses."
set TL_OUTDIR=smoketest_logs

python scripts\runlog.py --name P022B_stage2 --note "[1a] tiny parent (needed by --init-from and --kd)"
python scripts\runlog.py --name P022B_stage2 -- python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15
if errorlevel 1 goto PARENTBAD

python scripts\runlog.py --name P022B_stage2 --note "[1b] REFERENCE : --opt-dtype fp32 (torch fused AdamW)"
python scripts\runlog.py --name P022B_stage2 -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --kd --init-from --mlp-group 4 --opt-dtype fp32 --tag p22b_fp32
if errorlevel 1 goto GATEBAD

python scripts\runlog.py --name P022B_stage2 --note "[1c] SELF CHECK : --opt-dtype fp32c (our loop, fp32 state)"
python scripts\runlog.py --name P022B_stage2 -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --kd --init-from --mlp-group 4 --opt-dtype fp32c --tag p22b_fp32c
if errorlevel 1 goto GATEBAD

python scripts\runlog.py --name P022B_stage2 --note "[1d] TREATMENT : --opt-dtype bf16"
python scripts\runlog.py --name P022B_stage2 -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --kd --init-from --mlp-group 4 --opt-dtype bf16 --tag p22b_bf16
if errorlevel 1 goto GATEBAD

python scripts\runlog.py --name P022B_stage2 --note "***STOP AND LOOK.*** Compare the step 0 / 10 / 20 / 29 lines of [1b] and [1c]. They must agree to 4 decimals. If they do not, the implementation is wrong and parts 2 and 3 are meaningless - kill the batch. [1d] is EXPECTED to differ slightly; that difference is the dtype and it is what we are measuring."

set TL_OUTDIR=

echo.
echo =============================================================
echo [2/4] GATE S-b : 250 steps x 2 modes. VRAM and speed only.
echo =============================================================
python scripts\runlog.py --name P022B_stage2 --note "[2/4] GATE S-b : 250 steps, fp32 vs bf16. ***Read VRAM and ms/step. DO NOT read val_loss.***"

python scripts\runlog.py --name P022B_stage2 --note "[2a] 250 steps, --opt-dtype fp32"
python scripts\runlog.py --name P022B_stage2 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --opt-dtype fp32 --tag mC_opt32_250
if errorlevel 1 echo [WARN] fp32 250-step run failed - continuing

python scripts\runlog.py --name P022B_stage2 --note "[2b] 250 steps, --opt-dtype bf16"
python scripts\runlog.py --name P022B_stage2 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --opt-dtype bf16 --tag mC_optbf16_250
if errorlevel 1 echo [WARN] bf16 250-step run failed - continuing

python scripts\runlog.py --name P022B_stage2 --note "***STOP AND LOOK AGAIN.*** [2b] must show the [opt] line with about 254 MB, skip 0, grad_max under 3, and peak reserved about 0.25 GB below [2a]. If skip is not 0 or grad_max is over 10, do not start part 3."

echo.
echo =============================================================
echo [3/4] full run, 2289 steps, --opt-dtype bf16  (about 3.5 h)
echo =============================================================
python scripts\runlog.py --name P022B_stage2 --note "[3/4] full run : 2289 steps with bf16 optimizer state. Control mC_wsd is NOT retrained."
python scripts\runlog.py --name P022B_stage2 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --opt-dtype bf16 --tag mC_optbf16
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [4/4] paired comparison against mC_wsd
echo =============================================================
python scripts\runlog.py --name P022B_stage2 --note "[4/4] paired comparison against mC_wsd"
python scripts\runlog.py --name P022B_stage2 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_optbf16
if errorlevel 1 echo [WARN] paired_eval failed - the checkpoint is on disk, re-run this step alone

python scripts\runlog.py --name P022B_stage2 --note "=================================================================" "WHAT TO RECORD" "  0. ***the [opt] line from every non-fp32 run.*** No line, no experiment." "  1. GATE S-a : do [1b] and [1c] agree to 4 decimals." "  2. json opt_state_mb for each mode. ***MEASURED, not computed*** - result" "     026 was burned by an accounting claim that the code did not honour." "  3. peak reserved VRAM, fp32 vs bf16, from the [vram] lines." "  4. steady state ms/step for both 250 step runs." "     (running_avg x N - step0) / (N - 1)   with N = 250" "  5. final val of the 2289 step run, NOT best, plus the paired delta and t." "  6. grad_max and skip count from the json for every run." "" "HOW TO READ IT" "  S-a fails      -^> ***implementation bug.*** Nothing else may be quoted." "  S-a passes, paired delta under 0.024" "                 -^> ***ADOPT.*** About 254 MB back for free, and it composes" "                    with every architecture lever because it touches none." "  delta 0.024 to 0.05" "                 -^> a real trade. Note that the paper's 'no degradation' was" "                    at 1T tokens with a DIFFERENT rounding budget; our 2289" "                    steps accumulate far less. A cost here would be a genuine" "                    disagreement with the paper and worth writing up." "  above 0.05 or skip ^> 0" "                 -^> reject. Suspect deterministic rounding bias in the EMA;" "                    stochastic rounding would be the next thing to try." "" "  ***CHECK S5 TOO.*** 254 MB does NOT open --no-ckpt (about 1.7 to 2.7 GB is" "  needed). If someone later claims it does, that is this batch's number." "" "LIMITS: one seed. 2289 steps only - ***do not extrapolate to longer budgets***," "  rounding bias accumulates and the paper ran 1T tokens. Deterministic" "  round-to-nearest, not stochastic. --resume is not recommended in this mode." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:GATEBAD
echo.
echo [STOP] a tiny gate run failed. Fix the optimizer before spending 3.5 hours.
set TL_OUTDIR=
if not defined TL_NOPAUSE pause
exit /b 3

:PARENTBAD
echo.
echo [STOP] tiny dense parent failed. Nothing to distil from.
set TL_OUTDIR=
if not defined TL_NOPAUSE pause
exit /b 4

:BADFLAGS
echo.
echo [STOP] a flag used by this batch is not in the CLI parser.
if not defined TL_NOPAUSE pause
exit /b 6

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
echo [STOP] parent runs\ckpt\m100_ko-en_300M_dense.pt is missing.
if not defined TL_NOPAUSE pause
exit /b 5

:TRAINBAD
echo.
echo [STOP] the full run failed. Nothing to compare.
if not defined TL_NOPAUSE pause
exit /b 4

:BADROOT
echo.
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
