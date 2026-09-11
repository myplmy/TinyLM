@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P005b Stage10 - seed-2024 replication of jordan20 versus RMS4
REM  COST: about 6.2h. Four training arms on recursive d12 and nonrecursive d16.
REM  A sign reversal opens a third-seed gate; do not average it away.
REM ============================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005b_stage10_rms_seed_transfer --note "[1/6] recursive d12 seed 2024 jordan x20"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage10_rms_seed_transfer -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale jordan --muon-lr-mult 20 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_muon20_s2
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_r20_muon20_s2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage10_rms_seed_transfer --note "[2/6] recursive d12 seed 2024 RMS x4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage10_rms_seed_transfer -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_rms4_s2
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_rms4_s2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage10_rms_seed_transfer --note "[3/6] nonrecursive d16 seed 2024 jordan x20"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage10_rms_seed_transfer -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale jordan --muon-lr-mult 20 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_cla2_norecur_muon20_s2
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_muon20_s2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage10_rms_seed_transfer --note "[4/6] nonrecursive d16 seed 2024 RMS x4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage10_rms_seed_transfer -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_cla2_norecur_rms4_s2
if errorlevel 1 echo [WARN] arm 4 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_rms4_s2
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage10_rms_seed_transfer --note "[5/6] paired recursive d12 seed 2024"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage10_rms_seed_transfer -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_r20_muon20_s2 d12_cla2_r20_rms4_s2
if errorlevel 1 echo [WARN] d12 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage10_rms_seed_transfer --note "[6/6] paired nonrecursive d16 seed 2024"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage10_rms_seed_transfer -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 600M --ckpt-tokens 300M --models d16_cla2_norecur_muon20_s2 d16_cla2_norecur_rms4_s2
if errorlevel 1 echo [WARN] d16 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage10_rms_seed_transfer --note "VERDICT: if the sign differs from seed 1337, open a third seed instead of averaging."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
