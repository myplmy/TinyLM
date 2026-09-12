@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P005 Stage3c - transfer jordan x20 from recursive d12 to nonrecursive d16
REM  COST: about 1.9h. One new arm; jordan x15 is reused.
REM  VERDICT: paired full-val only. Ruler for the nonrecursive family is 0.0024.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100s12_ko-en_300M_d16_cla2_norecur_muon15.pt goto NOPAIR

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005_stage3c_norecur_muon20 --note "[1/2] nonrecursive d16, jordan x20"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage3c_norecur_muon20 -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale jordan --muon-lr-mult 20 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_cla2_norecur_muon20
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_muon20
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005_stage3c_norecur_muon20 --note "[2/2] paired verdict against existing jordan x15"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005_stage3c_norecur_muon20 -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 600M --ckpt-tokens 300M --models d16_cla2_norecur_muon15 d16_cla2_norecur_muon20
if errorlevel 1 echo [WARN] paired_eval failed - continuing

python scripts\runlog.py --name P005_stage3c_norecur_muon20 --note "DONE. Do not transfer the recursive scale verdict if the sign reverses here."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:NOPAIR
echo [STOP] required pair d16_cla2_norecur_muon15 is missing.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
