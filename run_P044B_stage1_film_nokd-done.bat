@echo off
REM =============================================================================
REM  P044B stage 1  -  FiLM in the no-KD standard condition.  about 2.7 hours.
REM
REM  WHY  (result 027, and REVIEW2 on 2026-08-22)
REM    P044 rejected FiLM on +0.0003, t=0.65. The stated reason was "KD has
REM    already filled that slot". That reasoning assumes KD. REVIEW2 then took
REM    KD out of the standard condition. If KD was filling the slot, removing
REM    KD empties it.
REM
REM    Three things changed at once - KD off, --no-ckpt on, and the ruler went
REM    from 0.024 to 0.0006. The old +0.0003 was 1/80 of the ruler. On today's
REM    ruler it is 1/2.0. A different order of magnitude.
REM
REM  INDEPENDENT VARIABLE
REM    --mlp-film. One flag against mC_initonly_nc. Nothing else moves.
REM
REM  PREDICTIONS
REM    F1  delta between -0.003 and +0.001. CONFIDENCE IS LOW - the argument is
REM        an analogy, not a measurement. A miss here is itself the result:
REM        FiLM and KD were never the same slot.
REM    F2  resident +0.25 MiB fp32, +0.06 int8. 65,536 parameters times 4B.
REM    F5  the json now carries mlp_film. Before 2026-08-30 it did not, and
REM        this run would have produced a log that cannot prove FiLM was on.
REM        Static gate 20 (check_smoke_fields) closed that.
REM    F3  grad_max between 1.3 and 2.0. Result 027 saw a 2.2x rise over its
REM        baseline; applied to 0.707 that is about 1.5.
REM    F4  ms/step under +1 percent.
REM
REM  RULER
REM    Tied 2 sigma = 0.0006, MEASURED on three seeds (result 039 s9).
REM    NOT 0.0010 - that was the two-seed value in 039 s8 and it was a
REM    systematic OVER-estimate. The gap between two points is not sigma;
REM    it is closer to the expectation of sigma times root two.
REM
REM  DECISION
REM    under -0.0006   withdraw the P044 rejection. Open stage 2.
REM    within ruler    close it. Invalid with or without KD, this time with a
REM                    ruler 40x sharper.
REM    over +0.0006    close it AND record a new fact - FiLM is harmful.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P044B_stage1_film_nokd --note "=============================================================================" "P044B stage 1   FiLM without KD" "P044 rejected FiLM because KD had filled the slot. KD is gone now." "=============================================================================="

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P044B_stage1_film_nokd --note "[1/3] train - standard condition plus --mlp-film"
python scripts\runlog.py --name P044B_stage1_film_nokd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --mlp-film --tag mC_film_nokd
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
set TL_WB_TAG=mC_film_nokd
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing

echo.
python scripts\runlog.py --name P044B_stage1_film_nokd --note "[2/3] paired against the control. One flag apart."
python scripts\runlog.py --name P044B_stage1_film_nokd -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_film_nokd mC_initonly_nc
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P044B_stage1_film_nokd --note "[3/3] F2 - what the 65,536 parameters cost in the deployment accounting"
python scripts\runlog.py --name P044B_stage1_film_nokd -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_film_nokd mC_initonly_nc --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step 3 failed - continuing

echo.
python scripts\runlog.py --name P044B_stage1_film_nokd --note "=============================================================================" "READ IN THIS ORDER" "1. the paired delta against the MEASURED tied ruler 0.0006 (039 s9)," "   not 0.0010 and not 0.024." "2. grad_max from the json, not the printed g. F3 expects 1.3 to 2.0." "3. step 3 - weights plus KV. FiLM adds weights and no KV, so headroom goes" "   from 1.2 to about 0.9 MiB. No quality gain means a net loss." "4. if F1 misses, say so plainly. The analogy was the whole argument." "5. then run paired_eval on mC_wsd and mC_film to fill the 2x2 - ten minutes," "   and it answers whether FiLM and KD were ever the same slot." "=============================================================================="

if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
