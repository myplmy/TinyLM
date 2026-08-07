@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P051_micro_group256.bat -- [P051] ternary alpha group 128 -^> 256.
REM                                 The one axis that has never been swept.
REM  Plan: test_plan\P051
REM =============================================================================
REM
REM PRECONDITION: --micro-group IMPLEMENTED 2026-08-07. Unset = preset value =
REM   bit identical. ***Code changed, so run run_smoke_check.bat first.***
REM
REM ***LONG UNATTENDED RUN. START IT AND WALK AWAY.*** About 3.5 GPU hours.
REM
REM WHY - our storage bpw has two terms and we only ever touched one
REM   report() prints:  B: code(log2 3 / 1.25) + group scale(16 / micro_group)
REM     code        1.5850 bpw   touched by P016, P034, P014
REM     group scale 0.1250 bpw   ***never touched***
REM   micro_group 128 -^> 256 halves the scale term: 1.7100 -^> 1.6475 bpw.
REM   No architecture change at all. Layers, depth, tying, embedding: identical.
REM
REM ***THIS LEVER IS ORTHOGONAL.*** g16 (P045), prelude/coda (P048) and E
REM   reduction (P046) all cut the NUMBER of unique ternary parameters.
REM   micro_group cuts BITS PER PARAMETER and leaves the count alone. So it sits
REM   OUTSIDE the convexity found in result 032 section 8.3 - that convexity is
REM   about removing capacity, and this removes none.
REM
REM ***BUT IT IS A PACKED-ONLY LEVER.*** Residency is
REM   unique_ternary x 4B x 2 copies + rest, and ***bpw is not in that formula***
REM   (trap 1). Expect fp32 residency to be UNCHANGED at 451.5 MB.
REM   ***Say 'packed' whenever quoting this result.***
REM
REM ***EXPECTATION - WRITE IT DOWN FIRST (plan P051 section 3)***
REM   P1 paired delta +0.000 to +0.008, well inside the 0.024 resolution.
REM      Result 028 re-estimated alpha at g256 POST HOC and got delta bpb
REM      +0.0010 to +0.0015 = about 0.003 to 0.005 nats. Retraining should be
REM      no worse than a post-hoc squeeze, so that number is an upper bound.
REM   P2 packed 13.050 -^> 12.573 MB, ratio 2.07x -^> 2.15x.
REM   P3 fp32 residency UNCHANGED (451.5 MB).
REM   P4 grad_max stays near baseline 0.847, in 0.5 to 1.5.
REM   P5 wall clock within 2 percent. Only reshape sizes change.
REM
REM ***THE AXIS CLOSES HERE.*** dim is 768 and 768 mod 512 is not 0, so g512 is
REM   structurally impossible. g256 is the ceiling, exactly as n_middle=16 made
REM   g16 the ceiling for tying in P045. One run closes the axis either way.
REM
REM ***GATE G-a - CHECK THIS BEFORE TRUSTING ANYTHING***
REM   The log must contain the line  [micro_group] alpha group 128 -^> 256
REM   and report() must show packed in the 12.5 MB range. If it still says
REM   13.05 MB the override did not take and ***this run is worthless.***
REM
REM ***THE CONTROL IS NOT RE-RUN.*** mC_wsd from result 024 differs by exactly
REM   one flag. Check sched=wsd / anneal_end=0.80 / decay_frac=0.20 /
REM   kd_every=4 / pool 600M exact / seed 1337 in the header before any delta.
REM
REM   The KD teacher stays at g128 - load_dense restores it from its own cfg.
REM   That is deliberate. Changing the teacher too would make two variables.
REM
REM ERRORLEVEL POLICY: training is the prerequisite, so it stops the batch.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

echo =============================================================
echo [P051] ternary alpha group 128 to 256 : the last unswept axis
echo =============================================================
python scripts\runlog.py --name P051_mC_g256a --note "[P051] micro_group 128 to 256. Packed-only lever, orthogonal to every capacity lever."

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
echo [1/2] train
echo =============================================================
python scripts\runlog.py --name P051_mC_g256a --note "[1/2] train : --micro-group 256"
python scripts\runlog.py --name P051_mC_g256a -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --init-from --micro-group 256 --tag mC_g256a
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [2/2] paired comparison against mC_wsd
echo =============================================================
python scripts\runlog.py --name P051_mC_g256a --note "[2/2] paired comparison against mC_wsd"
python scripts\runlog.py --name P051_mC_g256a -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_g256a
if errorlevel 1 echo [WARN] paired_eval failed - the checkpoint is on disk, re-run this step alone

python scripts\runlog.py --name P051_mC_g256a --note "=================================================================" "WHAT TO RECORD" "  0. ***the [micro_group] line.*** No line, no experiment." "  1. the report() block - packed MB and the reduction ratio." "  2. final val, NOT best." "  3. the paired_eval delta, SE and t against mC_wsd." "  4. grad_max from the json, and micro_group from the json too." "  5. the header conditions. Any mismatch with mC_wsd invalidates the delta." "" "HOW TO READ IT" "  delta under 0.024 and packed about -3.6 percent" "      -^> ***ACCEPT and close the axis.*** Composes with g16 and p1c1 because" "         it removes no capacity. Quote it as PACKED only." "  0.024 to 0.05" "      -^> a real trade. Small gain, so probably not worth it - but record the" "         number, it is the price of alpha granularity and nobody has one." "  above 0.05" "      -^> reject. And that is interesting in itself: it would mean result 028" "         post-hoc re-estimation UNDERSTATES the cost of coarse alpha, which" "         also weakens the per-row path in P014C." "" "  ***Check P3 too.*** If fp32 residency moved, the accounting double counts" "  somewhere - bpw is not supposed to appear in the residency formula." "" "LIMITS: one seed. Packed only, no residency gain. g512 is impossible" "  (768 mod 512), so this single run closes the axis." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

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
echo [STOP] parent runs\ckpt\m100_ko-en_300M_dense.pt is missing (KD and --init-from need it).
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
