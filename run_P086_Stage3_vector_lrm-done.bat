@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P086_Stage3_vector_lrm.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Stage1 and Stage2 did not measure the paper's technique. The core of
REM     arXiv:2601.04890 is the VECTOR multiplier of equation 3; we put in the
REM     scalar triple of equation 2, and two of those three duplicated m_scale
REM     and gates[1]. The effective new freedom was 1, not 3 - which is exactly
REM     what the paper's Model placement section warned about. The observed
REM     +0.0003 (t 0.77) is what a pure symmetry direction produces.
REM
REM   READ IN THIS ORDER
REM     1. Arm 1 is a FRESH control. Do not compare against the old d12_cla2_r20_muon15
REM        run - Stage3 changes the multiplier weight decay, so the condition differs
REM        and a cross-session comparison is invalid (trap 2).
REM     2. Arm 2 is the paper's row multiplier: ffn on gate and up, dim on down.
REM        Column multipliers are deliberately absent - m_scale already occupies that slot.
REM     3. Multiplier weight decay is 0 here. That is the paper's own condition
REM        (section 1). The default 0.01 stays bit identical for every other run.
REM     4. Watch the max abs multiplier printed at every eval. If it grows without bound the
REM        symmetry drift the paper warns about in section 4.1 is real, and arm B-prime
REM        (wd 0.01) becomes necessary.
REM     5. The ruler is the recursive family, 0.0018. Adoption needs -0.0036 or better.
REM
REM   COST: about 3.9h.   PLAN: test_plan/P086 stage3
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P086_stage3_vector_lrm --note "[1/2] fresh control - same body, no multipliers"
timeout /t 15 /nobreak
python scripts\runlog.py --name P086_stage3_vector_lrm -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-lr-mult 15 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_vlrm_ctrl
if errorlevel 1 echo [WARN] arm 1 failed - continuing
set TL_WB_TAG=d12_cla2_r20_vlrm_ctrl
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P086_stage3_vector_lrm --note "[2/2] vector multipliers, multiplier weight decay 0 - the paper's arrangement"
timeout /t 15 /nobreak
python scripts\runlog.py --name P086_stage3_vector_lrm -- python run100m.py train --preset m100s8 --arch dense --data ko-en --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --cla-group 2 --train-repeat 2.0 --optimizer muon --muon-lr-mult 15 --mlp-lrm --mlp-lrm-mode vector --mlp-lrm-wd 0 --steps 2289 --tokens 300M --pool-tokens 600M --exact-cache --tag d12_cla2_r20_vlrm
if errorlevel 1 echo [WARN] arm 2 failed - continuing
set TL_WB_TAG=d12_cla2_r20_vlrm
call scripts\batch\tool_wandb_push.bat
set TL_WB_TAG=

python scripts\runlog.py --name P086_stage3_vector_lrm --note "[judge] deterministic full-val, paired per crop"
python scripts\runlog.py --name P086_stage3_vector_lrm -- python scripts\paired_eval.py --preset m100s8 --data ko-en --tokens 600M --ckpt-tokens 300M --models d12_cla2_r20_vlrm_ctrl d12_cla2_r20_vlrm
if errorlevel 1 echo [WARN] judge failed - continuing

python scripts\runlog.py --name P086_stage3_vector_lrm -- python scripts\diag_lrm_values.py --tag d12_cla2_r20_vlrm
if errorlevel 1 echo [WARN] diag_lrm_values failed - continuing

python scripts\runlog.py --name P086_stage3_vector_lrm --note "DONE. Read the max abs multiplier growth before reading the loss. If the multipliers did not move, the loss says nothing."

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
