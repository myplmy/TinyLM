@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P005b Stage12 - RMS4 at 1200M tokens on nonrecursive d16
REM  COST: about 5.9h. One new arm.
REM  HARD PREREQUISITE: P088 Stage10 must be fully finished, not merely running.
REM  LIMIT: pool over tokens is 1.0. Every result quote must carry this caveat.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\logs\m100s12_ko-en_1200M_d16_cla2_norecur_muon15_t1200.json goto NOSTAGE10
if not exist runs\ckpt\m100s12_ko-en_1200M_d16_cla2_norecur_muon15_t1200.pt goto NOSTAGE10
if not exist runs\ckpt\m100s12_ko-en_1200M_d16_cla2_norecur_t1200.pt goto NOPAIR

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005b_stage12_rms_1200M_transfer --note "[1/2] nonrecursive d16 RMS x4 at 1200M tokens; pool ratio is 1.0"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage12_rms_1200M_transfer -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 9156 --tokens 1200M --ckpt-tokens 300M --pool-tokens 1200M --exact-cache --tag d16_cla2_norecur_rms4_t1200
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_rms4_t1200
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage12_rms_1200M_transfer --note "[2/2] paired AdamW, jordan x15 and RMS4; all use pool ratio 1.0"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage12_rms_1200M_transfer -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 1200M --ckpt-tokens 1200M --models d16_cla2_norecur_t1200 d16_cla2_norecur_muon15_t1200 d16_cla2_norecur_rms4_t1200
if errorlevel 1 echo [WARN] paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage12_rms_1200M_transfer --note "VERDICT: compare the three same-pool arms; pool over tokens is 1.0."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:NOSTAGE10
echo [STOP] P088 Stage10 is not fully finished. Do not overlap this run with it.
if not defined TL_NOPAUSE pause
exit /b 8

:NOPAIR
echo [STOP] the P088 Stage8 AdamW pair is missing.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
