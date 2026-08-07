@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P050_parent_ablation.bat -- [P050] how much does the parent actually buy
REM  Plan: test_plan\P050 / Report: docs\20260807_parent-dependency analysis
REM =============================================================================
REM
REM PRECONDITION: parent runs\ckpt\m100_ko-en_300M_dense.pt (arms B and C need it).
REM   Control mC_wsd is NOT retrained - it is arm A.
REM
REM ***LONG UNATTENDED RUN. About 9.5 GPU hours for three runs.***
REM   The three runs are INDEPENDENT - one failing does not stop the others.
REM
REM WHY - THIS CORRECTS THE READING OF PAST EXPERIMENTS
REM   The parent enters our pipeline through TWO doors and we have never
REM   separated them:
REM     (1) weight transplant  --init-from   needs matching SHAPES
REM     (2) logit distillation --kd          needs only the same VOCAB
REM   Door (1) breaks whenever we change the architecture. It broke in P046
REM   (embedding random, grad_max 19.32, VERDICT INVALID) and in P048 (partial
REM   transplant). So if door (1) carries most of the benefit, every delta we
REM   measured in P046/P048/P049 contains an initialisation handicap and we are
REM   UNDERSTATING those architectures.
REM
REM ARMS - same architecture (m100R1c), same data, steps, seed. Only two flags move.
REM   A  mC_wsd       init YES  kd YES   the baseline. NOT retrained.
REM   B  mC_kdonly    init NO   kd YES   door (2) alone
REM   C  mC_initonly  init YES  kd NO    door (1) alone
REM   D  mC_solo      init NO   kd NO    no parent at all
REM
REM   decomposition, with D as zero:
REM     share of (1) = delta(D) - delta(C)
REM     share of (2) = delta(D) - delta(B)
REM     interaction  = delta(D) - delta(B) - delta(C) + delta(A)
REM
REM ***PREDICTIONS - WRITTEN BEFORE THE RUN***
REM   P1 D lands at +0.15 to +0.30 against A.
REM   P2 ***door (2) beats door (1)*** - B sits closer to A than C does.
REM      Result 030 showed a fully random embedding recovered 93 percent of a
REM      2.63 nat starting gap, and result 027 showed KD already occupies the
REM      per-layer conditioning role.
REM   P3 the two doors are roughly ADDITIVE (interaction under 0.02).
REM   P4 D has the largest grad_max. ***If it exceeds 10 that arm is VERDICT
REM      IMPOSSIBLE*** by the repo decision rule - report that, not the delta.
REM   P5 D leaves a lot of VRAM free (no teacher resident).
REM
REM ***THRESHOLD, FIXED IN ADVANCE***
REM   If share(2) is more than twice share(1), demote parent-init to a
REM   convenience and DO NOT build the depth-expanding transplant P049 needs.
REM
REM   ***--no-ckpt is deliberately NOT used here.*** It would change the speed
REM   condition and pollute the quality comparison (result 015 measured a
REM   -0.0016 grad-ckpt drift). That question is stage 2.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT
if not exist runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt goto NOCTRL

echo =============================================================
echo [P050] parent ablation : 3 runs, about 9.5 hours
echo   [B] mC_kdonly    KD only        no --init-from
echo   [C] mC_initonly  init only      no --kd
echo   [D] mC_solo      neither        no parent at all
echo =============================================================
python scripts\runlog.py --name P050_parent_ablation --note "[P050] parent ablation : which door does the parent enter through"

echo.
echo [guard] cli.py call-keyword sanity
python scripts\check_call_kwargs.py
if errorlevel 1 goto BADKWARGS

echo.
echo [1/3] arm B - KD only (no parent init)
python scripts\runlog.py --name P050_parent_ablation --note "[1/3] arm B mC_kdonly : KD only, random init"
python scripts\runlog.py --name P050_parent_ablation -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --kd --kd-every 4 --tag mC_kdonly
if errorlevel 1 echo [WARN] arm B failed - continuing to arm C

echo.
echo [2/3] arm C - parent init only (no KD)
python scripts\runlog.py --name P050_parent_ablation --note "[2/3] arm C mC_initonly : parent init only, no KD"
python scripts\runlog.py --name P050_parent_ablation -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --tag mC_initonly
if errorlevel 1 echo [WARN] arm C failed - continuing to arm D

echo.
echo [3/3] arm D - solo (no parent at all)
python scripts\runlog.py --name P050_parent_ablation --note "[3/3] arm D mC_solo : no parent at all"
python scripts\runlog.py --name P050_parent_ablation -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --tag mC_solo
if errorlevel 1 echo [WARN] arm D failed - continuing to the comparison

echo.
echo [4/4] paired comparison - all four arms, six pairs
python scripts\runlog.py --name P050_parent_ablation --note "[4/4] paired : all four arms"
python scripts\runlog.py --name P050_parent_ablation -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_kdonly mC_initonly mC_solo
if errorlevel 1 echo [WARN] paired_eval failed - checkpoints are on disk, re-run this step alone

python scripts\runlog.py --name P050_parent_ablation --note "=================================================================" "WHAT TO RECORD" "  0. ***grad_max from the json for EVERY arm.*** Anything over 10 makes that" "     arm VERDICT IMPOSSIBLE (result 030 set this precedent)." "  1. the six paired deltas." "  2. the decomposition:" "       share of parent-init = delta(D) - delta(C)" "       share of KD         = delta(D) - delta(B)" "       interaction         = delta(D) - delta(B) - delta(C) + delta(A)" "  3. peak VRAM for arm D - it has no teacher, so this sizes stage 2." "  4. wall clock. Arm D should be fastest (no teacher forward at all)." "  5. header conditions vs mC_wsd. Only --init-from and --kd may differ." "" "HOW TO READ IT" "  share(KD) ^> 2x share(init)" "      -^> ***parent-init is a convenience, not a foundation.*** Architecture" "         changes are cheap. Do NOT build the depth-expanding transplant that" "         P049 would otherwise need." "  share(init) ^>= share(KD)" "      -^> every delta in P046, P048 and P048-2 contains an initialisation" "         handicap. Those architectures are UNDERSTATED and need re-reading." "  interaction over 0.02" "      -^> the doors are not separable; stop pricing them individually." "" "LIMITS: one seed. One architecture (m100R1c). 300M budget - the parent is" "  probably a convergence accelerator, so its share should SHRINK at longer" "  budgets, and this run cannot see that. No external teacher: our tokenizer" "  is our own, which is the real barrier (see the dependency report section 3)." "================================================================="
echo done.
if not defined TL_NOPAUSE pause
exit /b 0

:BADKWARGS
echo.
echo [STOP] cli.py passes a keyword its target function does not accept.
if not defined TL_NOPAUSE pause
exit /b 6

:NOPARENT
echo.
echo [STOP] parent runs\ckpt\m100_ko-en_300M_dense.pt is missing.
if not defined TL_NOPAUSE pause
exit /b 7

:NOCTRL
echo.
echo [STOP] control runs\ckpt\m100R1c_ko-en_300M_mC_wsd.pt is missing.
if not defined TL_NOPAUSE pause
exit /b 5

:BADROOT
echo.
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 9
