@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P045B_Stage1_small_g_grid.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     161 tying runs sit on a DIAGONAL. Of the 27 cells in (depth x g) only 10 are filled
REM     and every filled cell lies on a line of constant unique-MLP count. So what we
REM     measured was not the tying axis. Small g is essentially unsampled: g2 has almost
REM     no points and ag2 has none at a matched step.
REM     Every one of those 161 runs used AdamW. Muon transfers at -0.036 to -0.051 in 8 of 8
REM     pairs, so an AdamW tying number cannot decide promotion.
REM
REM   DESIGN
REM     Body fixed: d12 (m100s8), cla_group 2, no recursion, Muon x15, 300M tokens.
REM     A1 g2  - halve unique MLP
REM     A2 g4  - quarter unique MLP
REM     A3 ag2 - halve unique attention. SAME STEP as A1, so A1 vs A3 is the clean test of
REM              "does it matter WHAT you tie, or only HOW MANY uniques you delete".
REM     A0 baseline is an existing run: d12_cla2_norecur_muon15 = 3.54719. No new arm.
REM
REM   READ IN THIS ORDER
REM     1. grad_max and n_skip. Muon plus tying is a combination we have never run.
REM     2. A1 minus A0 against the ruler 0.0024 (norecur 2 sigma).
REM     3. A1 vs A3 - if the gap is inside the ruler, "count of deleted uniques" is the law.
REM     4. Convert to nats per deployment MiB and compare with depth at 0.00614.
REM        Cheaper than depth means promotion candidate. More expensive means do not sell it.
REM
REM   DO NOT
REM     Do not read these against the AdamW tying runs. Different optimiser.
REM     A4 (g2 + ag2) is NOT in this batch. It only runs if both A1 and A3 clear the ruler.
REM
REM   COST: about 9.0h.   PLAN: test_plan/P045B Stage1
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P045B_stage1_small_g_grid --note "[1/3] g2 - halve unique MLP, the first step nobody measured"
timeout /t 15 /nobreak
python scripts\runlog.py --name P045B_stage1_small_g_grid -- python run100m.py train --preset m100s8 --arch tied --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --mlp-group 2 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_g2_muon15
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_g2_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P045B_stage1_small_g_grid --note "[2/3] g4 - quarter unique MLP, the Muon twin of the existing AdamW d12_g4"
python scripts\runlog.py --name P045B_stage1_small_g_grid -- python run100m.py train --preset m100s8 --arch tied --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --mlp-group 4 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_g4_muon15
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_g4_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

REM   arm 3 must use --arch tied. trainer.py line 333 applies --attn-group ONLY when
REM   arch is tied, so --arch dense --attn-group 2 is silently ignored. dryrun_batch
REM   caught that on 2026-09-10. --mlp-group 1 keeps the MLP untied: verified on CPU that
REM   (tied, mlp_group 1) and dense build the same 81,171,224 parameters with identical
REM   state_dict keys and shapes, so arm 3 differs from the baseline in attention only.
python scripts\runlog.py --name P045B_stage1_small_g_grid --note "[3/3] ag2 - halve unique attention. Deletes 4.72M ternary against 18.87M for g2, so compare per deleted million, not raw."
python scripts\runlog.py --name P045B_stage1_small_g_grid -- python run100m.py train --preset m100s8 --arch tied --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --mlp-group 1 --attn-group 2 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_ag2_muon15
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d12_ag2_muon15
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P045B_stage1_small_g_grid --note "[judge] deterministic full-val, paired per crop, against the existing baseline"
python scripts\runlog.py --name P045B_stage1_small_g_grid -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_norecur_muon15 d12_g2_muon15 d12_g4_muon15 d12_ag2_muon15
if errorlevel 1 echo [WARN] judge failed - continuing

python scripts\runlog.py --name P045B_stage1_small_g_grid --note "DONE. A1 vs A3 first. If that gap is inside 0.0024 the law is count of deleted uniques."

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root
exit /b 1
