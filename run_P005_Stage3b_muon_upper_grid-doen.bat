@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P005 Stage3b - close the jordan-scale upper bracket at 2289 steps
REM  COST: about 2.9h. Two training arms. User runs this file.
REM  VERDICT: paired full-val only. Ruler for this recursive family is 0.0018.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100s8_ko-en_300M_d12_cla2_r20_muon20.pt goto NOPAIR

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005_stage3b_muon_upper_grid --note "[1/3] jordan x25 at 2289 steps"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage3b_muon_upper_grid -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale jordan --muon-lr-mult 25 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_muon25
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon25
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage3b_muon_upper_grid --note "[2/3] jordan x30 at 2289 steps"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage3b_muon_upper_grid -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale jordan --muon-lr-mult 30 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_muon30
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon30
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage3b_muon_upper_grid --note "[3/3] paired verdict against jordan x20"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage3b_muon_upper_grid -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_r20_muon20 d12_cla2_r20_muon25 d12_cla2_r20_muon30
if errorlevel 1 echo [WARN] paired_eval failed - continuing

python scripts\runlog.py --name P005_stage3b_muon_upper_grid --note "DONE. If x25 and x30 both beat x20, do not extend linearly; redesign a log grid."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:NOPAIR
echo [STOP] required pair d12_cla2_r20_muon20 is missing.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
