@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P005b Stage2b - close the RMS upper bracket with x6 and x8
REM  COST: about 3.3h. Two training arms. User runs this file.
REM  STOP before later high-scale work if n_skip is nonzero or gradients are abnormal.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100s8_ko-en_300M_d12_cla2_r20_rms4.pt goto NOPAIR

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005b_stage2b_muon_rms_upper --note "[1/3] RMS x6 on the result-078 body"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage2b_muon_rms_upper -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale rms --muon-lr-mult 6 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_rms6
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_r20_rms6
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage2b_muon_rms_upper --note "[2/3] RMS x8 on the result-078 body"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage2b_muon_rms_upper -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale rms --muon-lr-mult 8 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_rms8
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_rms8
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage2b_muon_rms_upper --note "[3/3] paired RMS curve with jordan x20 anchor"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage2b_muon_rms_upper -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_r20_muon20 d12_cla2_r20_rms2 d12_cla2_r20_rms4 d12_cla2_r20_rms6 d12_cla2_r20_rms8
if errorlevel 1 echo [WARN] paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage2b_muon_rms_upper --note "VERDICT: if x6 and x8 both improve, redesign the scale grid instead of extrapolating."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:NOPAIR
echo [STOP] required RMS4 checkpoint from result 078 is missing.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
