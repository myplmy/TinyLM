@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P089 Stage2b - rerun the two width-quality arms after CLA-aware init repair
REM  COST: about 4.6h. Two training arms plus deterministic paired full-val.
REM  The old Stage2 tags are preserved as failed-history names; this uses _b.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100w512s16_ko-en_300M_w512_d20_parent.pt goto NOPARENT
if not exist runs\ckpt\m100s10_ko-en_300M_d14_cla2_norecur_muon15.pt goto NOBASE

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P089_stage2b_width_three_points --note "[1/3] width-only decomposition arm: dim512 L14"
timeout /t 15 /nobreak
python scripts\runlog.py --name P089_stage2b_width_three_points -- python run100m.py train --preset m100w512s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from-tag w512_d20_parent --depth-init role --cla-group 2 --optimizer muon --muon-scale jordan --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag w512_d14_muon15_b
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=w512_d14_muon15_b
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P089_stage2b_width_three_points --note "[2/3] equal-residency candidate: dim512 L28"
timeout /t 15 /nobreak
python scripts\runlog.py --name P089_stage2b_width_three_points -- python run100m.py train --preset m100w512s24 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from-tag w512_d20_parent --depth-init role --cla-group 2 --optimizer muon --muon-scale jordan --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag w512_d28_muon15_b
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=w512_d28_muon15_b
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P089_stage2b_width_three_points --note "[3/3] deterministic full-val: width cost, depth recovery, net benefit"
timeout /t 15 /nobreak
python scripts\runlog.py --name P089_stage2b_width_three_points -- python scripts\paired_eval.py --preset m100w512s24 --data ko-en --tokens 600M --ckpt-tokens 300M --models w512_d14_muon15_b w512_d28_muon15_b d14_cla2_norecur_muon15
if errorlevel 1 echo [WARN] paired_eval failed - continuing

python scripts\runlog.py --name P089_stage2b_width_three_points --note "VERDICT: report width cost=A-base, depth recovery=A-B, and net benefit=base-B separately."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:NOPARENT
echo [STOP] required narrow parent checkpoint is missing.
if not defined TL_NOPAUSE pause
exit /b 8

:NOBASE
echo [STOP] required dim768 L14 comparison checkpoint is missing.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
