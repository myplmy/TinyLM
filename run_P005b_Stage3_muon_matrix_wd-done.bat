@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P005b Stage3 - separate Muon scale from matrix weight decay
REM  COST: about 3.3h. Two new arms, each paired with its no-WD twin.
REM  Only matrix WD changes. Vector, norm, embedding and LRM groups stay unchanged.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100s8_ko-en_300M_d12_cla2_r20_muon15.pt goto NOPAIR
if not exist runs\ckpt\m100s8_ko-en_300M_d12_cla2_r20_rms4.pt goto NOPAIR

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005b_stage3_muon_matrix_wd --note "[1/3] jordan x15 with explicit matrix WD 0.1"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage3_muon_matrix_wd -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale jordan --muon-lr-mult 15 --matrix-weight-decay 0.1 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_muon15_mwd01
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon15_mwd01
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage3_muon_matrix_wd --note "[2/3] RMS x4 with explicit matrix WD 0.1"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage3_muon_matrix_wd -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale rms --muon-lr-mult 4 --matrix-weight-decay 0.1 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_rms4_mwd01
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_rms4_mwd01
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage3_muon_matrix_wd --note "[3/3] paired two-by-two scale and WD decomposition"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage3_muon_matrix_wd -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_r20_muon15 d12_cla2_r20_muon15_mwd01 d12_cla2_r20_rms4 d12_cla2_r20_rms4_mwd01
if errorlevel 1 echo [WARN] paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage3_muon_matrix_wd --note "DONE. Read WD within each scale before comparing scales."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:NOPAIR
echo [STOP] a required no-WD pair is missing.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
