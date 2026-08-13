@echo off
REM =============================================================================
REM  F-1  -  GQA via SDPA enable_gqa   (equivalence gate + VRAM, about 45 min)
REM
REM  WHAT
REM    Attention.forward has always expanded K/V with repeat_interleave, turning
REM    (B,3,T,64) into (B,12,T,64). At our standard shape that copy is roughly
REM    0.4 to 0.5 GiB of activation memory across 20 layers. enable_gqa=True
REM    lets the kernel ride one KV head on several Q heads with no copy.
REM
REM    Default is OFF and OFF is bit identical. This batch decides whether ON
REM    is safe, then measures what it buys.
REM
REM  GATES  (stage A, no training, minutes)
REM    G-a  logit max abs diff  ^<  1e-3     (bf16 accumulation, result 028 s11)
REM    G-b  SDPA accepts enable_gqa
REM    G-c  Flash / mem-efficient backends do not reject it
REM    G-d  KV cache path is bit identical (the flag must not touch it)
REM    ***If stage A fails, stage B does not run.***
REM
REM  STAGE B  250-step VRAM pair, off vs on, same session, same shape.
REM    Expect about -0.4 to -0.5 GiB reserved.
REM    !! 250-step val is NOT a quality number (baselines s2.3). Read VRAM only.
REM    !! Ignore ms/step across sessions - drift is 7.5 percent (result 037 s11.4).
REM       Compare only the two runs inside this batch.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT


echo.
echo.
python scripts\runlog.py --name P060_gqa --note "================= STAGE A  equivalence gate (no training) =================="
python scripts\runlog.py --name P060_gqa --note "[F-1 stage A] enable_gqa equivalence gate - logits, backends, kv-cache path"
python scripts\runlog.py --name P060_gqa -- python scripts\diag_gqa_equiv.py --preset m100R1c
if errorlevel 1 goto GATEBAD


echo.
echo.
python scripts\runlog.py --name P060_gqa --note "================= STAGE B  VRAM pair  250 steps x 2 ========================" "About 40 minutes. Do not run anything else on the GPU."
echo.

python scripts\runlog.py --name P060_gqa_vram --note "[F-1 stage B] 250-step VRAM pair, sdpa_gqa off vs on. Read reserved only, not val."

python scripts\runlog.py --name P060_gqa_vram -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --compile --init-from --tag mC_gqa_off250
if errorlevel 1 echo [WARN] gqa off run returned an error - continuing

echo.
echo.
python scripts\runlog.py --name P060_gqa --note "[queue] settling 15 s - WDDM holds VRAM for a few seconds after exit" "(result 037 s7: the next run started 1 second later and died with" "CUBLAS_STATUS_EXECUTION_FAILED, which is an OOM under another name)"
timeout /t 15 /nobreak

python scripts\runlog.py --name P060_gqa_vram -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 250 --compile --init-from --sdpa-gqa --tag mC_gqa_on250
if errorlevel 1 echo [WARN] gqa on run returned an error - continuing

echo.
echo.
python scripts\runlog.py --name P060_gqa --note "=============================================================================" "Read from runs\logs\*.json, not from the console:" "peak_reserved_gib   off vs on      expect about -0.4 to -0.5" "ms_step_median      off vs on      NEW field from T-1, same session only" "ms_step_spread      both           normal band is 0.065 to 0.154" "sdpa_gqa            must be false then true, else the flag did nothing" "Do NOT read val - 250 steps decides nothing about quality." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:GATEBAD
echo.
echo [STOP] stage A gate failed. Do not adopt --sdpa-gqa.
echo        Stage B is skipped on purpose - measuring VRAM of a wrong kernel
echo        path would give a number that looks fine and means nothing.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root (run100m.py not found).
if not defined TL_NOPAUSE pause
exit /b 1
