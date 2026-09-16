@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P005b Stage11 - transfer RMS4 to 600M tokens and test jordan x20 on d12
REM  COST: about 15.3h. Five training arms. Pool is 1200M, so pool over tokens is 2.
REM  Existing jordan x15 checkpoints are the same-pool anchors.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100s8_ko-en_600M_d12_cla2_r20_muon15_t600.pt goto NOPAIR
if not exist runs\ckpt\m100s10_ko-en_600M_d14_cla2_norecur_muon15_t600.pt goto NOPAIR
if not exist runs\ckpt\m100s12_ko-en_600M_d16_cla2_norecur_muon15_t600.pt goto NOPAIR
if not exist runs\ckpt\m100s14_ko-en_600M_d18_cla2_norecur_muon15_t600.pt goto NOPAIR

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[1/9] recursive d12 RMS x4 at 600M tokens"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d12_cla2_r20_rms4_t600
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_r20_rms4_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[2/9] recursive d12 jordan x20 at 600M tokens"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale jordan --muon-lr-mult 20 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d12_cla2_r20_muon20_t600
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon20_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[3/9] nonrecursive d14 RMS x4 at 600M tokens"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d14_cla2_norecur_rms4_t600
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d14_cla2_norecur_rms4_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[4/9] nonrecursive d16 RMS x4 at 600M tokens"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d16_cla2_norecur_rms4_t600
if errorlevel 1 echo [WARN] arm 4 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_rms4_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[5/9] nonrecursive d18 RMS x4 at 600M tokens"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python run100m.py train --preset m100s14 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 4578 --tokens 600M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d18_cla2_norecur_rms4_t600
if errorlevel 1 echo [WARN] arm 5 failed - continuing
set TL_WB_TAG=d18_cla2_norecur_rms4_t600
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[6/9] paired d12 jordan15, jordan20 and RMS4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 1200M --ckpt-tokens 600M --models d12_cla2_r20_muon15_t600 d12_cla2_r20_muon20_t600 d12_cla2_r20_rms4_t600
if errorlevel 1 echo [WARN] d12 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[7/9] paired d14 jordan15 and RMS4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python scripts\paired_eval.py --preset m100s10 --data ko-en --tokens 1200M --ckpt-tokens 600M --models d14_cla2_norecur_muon15_t600 d14_cla2_norecur_rms4_t600
if errorlevel 1 echo [WARN] d14 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[8/9] paired d16 jordan15 and RMS4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 1200M --ckpt-tokens 600M --models d16_cla2_norecur_muon15_t600 d16_cla2_norecur_rms4_t600
if errorlevel 1 echo [WARN] d16 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "[9/9] paired d18 jordan15 and RMS4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage11_rms_600M_transfer -- python scripts\paired_eval.py --preset m100s14 --data ko-en --tokens 1200M --ckpt-tokens 600M --models d18_cla2_norecur_muon15_t600 d18_cla2_norecur_rms4_t600
if errorlevel 1 echo [WARN] d18 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage11_rms_600M_transfer --note "DONE. Compare only within the 600M-token, 1200M-pool family."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:NOPAIR
echo [STOP] one or more existing 600M jordan x15 anchors are missing.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
