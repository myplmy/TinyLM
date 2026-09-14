@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P035B Stage1 - approved proposal A3 anneal trajectories
REM  COST: 0.3-0.8 GPU-h. Three fresh 250-step arms, about 5.6 GiB worst case.
REM  E60-on versus E80-on is dynamics only. E80-on versus E80-off audits bias.
REM  These 250-step losses must not select the default anneal endpoint.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100_ko-en_300M_dense.pt goto NOPARENT

if exist runs\logs\m100s8_ko-en_300M_p35b_a3_e60.json goto OUTPUTEXISTS
if exist runs\logs\m100s8_ko-en_300M_p35b_a3_e80.json goto OUTPUTEXISTS
if exist runs\logs\m100s8_ko-en_300M_p35b_a3_off80.json goto OUTPUTEXISTS
if exist runs\ckpt\m100s8_ko-en_300M_p35b_a3_e60.pt goto OUTPUTEXISTS
if exist runs\ckpt\m100s8_ko-en_300M_p35b_a3_e60_best.pt goto OUTPUTEXISTS
if exist runs\ckpt\m100s8_ko-en_300M_p35b_a3_e80.pt goto OUTPUTEXISTS
if exist runs\ckpt\m100s8_ko-en_300M_p35b_a3_e80_best.pt goto OUTPUTEXISTS
if exist runs\ckpt\m100s8_ko-en_300M_p35b_a3_off80.pt goto OUTPUTEXISTS
if exist runs\ckpt\m100s8_ko-en_300M_p35b_a3_off80_best.pt goto OUTPUTEXISTS
if exist runs\audit\p35b_a3_e60.jsonl goto OUTPUTEXISTS
if exist runs\audit\p35b_a3_e60.contract.json goto OUTPUTEXISTS
if exist runs\audit\p35b_a3_e80.jsonl goto OUTPUTEXISTS
if exist runs\audit\p35b_a3_e80.contract.json goto OUTPUTEXISTS

set PYTHONIOENCODING=utf-8
set TL_FAILED=0

python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories --note "[1/3] end 0.60 with anneal audit"
timeout /t 15 /nobreak
python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.2 --seed 1337 --eval-every 250 --compile --no-ckpt --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag p35b_a3_e60 --anneal-audit runs\audit\p35b_a3_e60.jsonl --anneal-audit-every 10 --anneal-audit-max-modules 8
if errorlevel 1 (
  python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories --note "WARN: arm 1 failed; continuing with independent arms."
  set TL_FAILED=1
)
set TL_WB_TAG=p35b_a3_e60
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories --note "[2/3] end 0.80 with anneal audit"
timeout /t 15 /nobreak
python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --compile --no-ckpt --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag p35b_a3_e80 --anneal-audit runs\audit\p35b_a3_e80.jsonl --anneal-audit-every 10 --anneal-audit-max-modules 8
if errorlevel 1 (
  python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories --note "WARN: arm 2 failed; continuing with independent arms."
  set TL_FAILED=1
)
set TL_WB_TAG=p35b_a3_e80
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories --note "[3/3] end 0.80 with anneal audit disabled"
timeout /t 15 /nobreak
python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --compile --no-ckpt --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 250 --tokens 300M --pool-tokens 600M --exact-cache --tag p35b_a3_off80
if errorlevel 1 (
  python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories --note "WARN: arm 3 failed."
  set TL_FAILED=1
)
set TL_WB_TAG=p35b_a3_off80
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

if "!TL_FAILED!"=="1" goto RUNFAIL
python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories --note "COMPLETE: return two audit JSONL, two contract JSON, three run JSON, and this runlog. Do not use 250-step loss for quality."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:RUNFAIL
python scripts\runlog.py --name P035B_stage1_anneal_a3_trajectories --note "INCOMPLETE: at least one arm failed. Preserve all outputs and design a new Stage1b attempt only after diagnosis."
set PYTHONIOENCODING=
echo [STOP] At least one arm failed. Preserve every output and report the log.
if not defined TL_NOPAUSE pause
exit /b 8

:OUTPUTEXISTS
echo [STOP] P035B Stage1 output already exists. Nothing was overwritten.
echo        Preserve it and use a new Stage1b only after diagnosis.
if not defined TL_NOPAUSE pause
exit /b 7

:NOPARENT
echo [STOP] Missing parent: runs\ckpt\m100_ko-en_300M_dense.pt
if not defined TL_NOPAUSE pause
exit /b 6

:BADROOT
echo [STOP] Run this batch from the TinyLM repository root.
if not defined TL_NOPAUSE pause
exit /b 9
