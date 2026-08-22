@echo off
REM =============================================================================
REM  P065 stage 2  -  is --no-ckpt safe at 36 layers and under recursion
REM                   2 short runs, 250 steps each, about 0.5 hours total
REM
REM  WHY THIS EXISTS
REM    2026-08-22 user instruction: "use --no-ckpt as the default wherever
REM    memory allows; re-verify at 36 layers and under recursion."
REM    Result 051 s2.3 measured only the 20 layer no-KD case:
REM        reserved 10.31 GiB, headroom 5.69, wall clock -20.6 percent
REM    36 layers and recursion have NO measurement. And the checkpoint cost is
REM    condition dependent - we predicted 2.90 GiB and measured 5.24.
REM    Extrapolating a number we already got wrong once is how a 5 hour run dies
REM    at hour 4.
REM
REM  !! READ ONLY VRAM AND ms/step. DO NOT READ val.
REM    250 steps is a speed and memory probe. Result 046 is the model for this:
REM    it proved steady state with ms_step_spread and never read val.
REM
REM  GATE, fixed in advance
REM    pass  reserved under 14.0 GiB  AND  skip 0  AND  no CUBLAS_STATUS failure
REM    fail  anything above 14.0 - WDDM spills between 13 and 14 and a spill is
REM          silent (trap 30). check_spill.py decides, not the exit code.
REM
REM  WHAT DEPENDS ON THIS
REM    run_S7_recursion_x_depth.bat (36 layers plus R2) uses --no-ckpt. If this
REM    gate fails, that batch must drop --no-ckpt and pay the 20 percent.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P065_stage2_nockpt_vram --note "=============================================================================" "P065 stage 2   --no-ckpt VRAM probe at 36 layers and under recursion" "250 steps each. Read VRAM and ms/step ONLY. val is meaningless here." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P065_stage2_nockpt_vram --note "[1/2] 36 layers, no-KD, --no-ckpt, 250 steps"
python scripts\runlog.py --name P065_stage2_nockpt_vram -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --attn-group 4 --init-from --no-ckpt --tag probe_d36_nock
if errorlevel 1 echo [WARN] probe_d36_nock failed - this IS the answer, continuing

echo.
python scripts\runlog.py --name P065_stage2_nockpt_vram --note "[wait] let WDDM release VRAM before the next run - result 037 s7.3"
timeout /t 15 /nobreak

python scripts\runlog.py --name P065_stage2_nockpt_vram --note "[2/2] 20 layers, recursion R2, no-KD, --no-ckpt, 250 steps"
python scripts\runlog.py --name P065_stage2_nockpt_vram -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --train-repeat 2.0 --init-from --no-ckpt --tag probe_r20_nock
if errorlevel 1 echo [WARN] probe_r20_nock failed - this IS the answer, continuing

echo.
python scripts\runlog.py --name P065_stage2_nockpt_vram --note "[wandb] push both probes - VRAM numbers are worth keeping even at 250 steps"
set TL_WB_TAG=probe_
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P065_stage2_nockpt_vram --note "[3/3] spill check on both - a spill is silent, exit code 0 and loss normal"
python scripts\runlog.py --name P065_stage2_nockpt_vram -- python scripts\check_spill.py
if errorlevel 1 echo [WARN] spill check failed - continuing

echo.
python scripts\runlog.py --name P065_stage2_nockpt_vram --note "=============================================================================" "READ IN THIS ORDER" "1. did either run die. A CUBLAS_STATUS_EXECUTION_FAILED IS an OOM (trap 29)." "2. vram_reserved_gb from the json, not the console. Gate is under 14.0." "3. check_spill p90/p10. Normal is 6.5 to 15.4 percent, a spill was 48.5." "4. ms_step_median only for the record. Do NOT compare it to another day -" "   session drift is 7.5 percent (result 037 s11.4)." "!! DO NOT READ val. 250 steps cannot rank quality." "IF BOTH PASS  --no-ckpt becomes the default for 36 layers and recursion too." "IF EITHER FAILS  that condition keeps grad checkpointing and pays 20 percent." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
