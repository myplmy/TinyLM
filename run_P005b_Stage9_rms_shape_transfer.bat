@echo off
setlocal enabledelayedexpansion
REM ============================================================================
REM  P005b Stage9 - RMS4 versus jordan20 across nonrecursive deployment shapes
REM  COST: about 9.6h. Seven new arms; d16 jordan20 comes from P005 Stage3c.
REM  Compare only within each preset. Do not subtract values across presets.
REM ============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100s12_ko-en_300M_d16_cla2_norecur_muon20.pt goto NOPAIR

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[1/11] d12 nonrecursive jordan x20"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale jordan --muon-lr-mult 20 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_norecur_muon20
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_norecur_muon20
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[2/11] d12 nonrecursive RMS x4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_norecur_rms4
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_norecur_rms4
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[3/11] d14 nonrecursive jordan x20"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale jordan --muon-lr-mult 20 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d14_cla2_norecur_muon20
if errorlevel 1 echo [WARN] arm 3 failed - continuing
set TL_WB_TAG=d14_cla2_norecur_muon20
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[4/11] d14 nonrecursive RMS x4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python run100m.py train --preset m100s10 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d14_cla2_norecur_rms4
if errorlevel 1 echo [WARN] arm 4 failed - continuing
set TL_WB_TAG=d14_cla2_norecur_rms4
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[5/11] d16 nonrecursive RMS x4; jordan x20 is reused"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python run100m.py train --preset m100s12 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d16_cla2_norecur_rms4
if errorlevel 1 echo [WARN] arm 5 failed - continuing
set TL_WB_TAG=d16_cla2_norecur_rms4
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[6/11] d18 nonrecursive jordan x20"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python run100m.py train --preset m100s14 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale jordan --muon-lr-mult 20 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d18_cla2_norecur_muon20
if errorlevel 1 echo [WARN] arm 6 failed - continuing
set TL_WB_TAG=d18_cla2_norecur_muon20
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[7/11] d18 nonrecursive RMS x4"
timeout /t 15 /nobreak
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python run100m.py train --preset m100s14 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --optimizer muon --muon-scale rms --muon-lr-mult 4 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d18_cla2_norecur_rms4
if errorlevel 1 echo [WARN] arm 7 failed - continuing
set TL_WB_TAG=d18_cla2_norecur_rms4
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[8/11] paired d12 only"
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_norecur_muon20 d12_cla2_norecur_rms4
if errorlevel 1 echo [WARN] d12 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[9/11] paired d14 only"
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python scripts\paired_eval.py --preset m100s10 --data ko-en --tokens 600M --ckpt-tokens 300M --models d14_cla2_norecur_muon20 d14_cla2_norecur_rms4
if errorlevel 1 echo [WARN] d14 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[10/11] paired d16 only"
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python scripts\paired_eval.py --preset m100s12 --data ko-en --tokens 600M --ckpt-tokens 300M --models d16_cla2_norecur_muon20 d16_cla2_norecur_rms4
if errorlevel 1 echo [WARN] d16 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "[11/11] paired d18 only"
python scripts\runlog.py --name P005b_stage9_rms_shape_transfer -- python scripts\paired_eval.py --preset m100s14 --data ko-en --tokens 600M --ckpt-tokens 300M --models d18_cla2_norecur_muon20 d18_cla2_norecur_rms4
if errorlevel 1 echo [WARN] d18 paired_eval failed - continuing

python scripts\runlog.py --name P005b_stage9_rms_shape_transfer --note "VERDICT: require the same sign in at least three of four nonrecursive shapes."
set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:NOPAIR
echo [STOP] run P005 Stage3c first; d16 jordan x20 is required.
if not defined TL_NOPAUSE pause
exit /b 8

:BADROOT
echo [STOP] run this from the TinyLM working folder.
if not defined TL_NOPAUSE pause
exit /b 9
