@echo off
REM P067 stage 2  -  the full external-teacher run. About 8.8 hours.
REM
REM   Stage 2b proved the shape survives: 14.77 GiB reserved, 57.8 minutes for
REM   250 steps, step0 CE 12.4917 against the 12.4766 anchor.
REM
REM   The original question is whether KD was useless because knowledge
REM   distillation does not work here, or because OUR teacher was bad - our
REM   dense teacher scores 3.8080, worse than the 3.6984 student it taught.
REM
REM   WARNING ON EXPECTATIONS.  Result 041 already measured that even a good
REM   teacher fails to clear the ruler (-0.0078 bpb). So the prior here is low
REM   and this run costs 8.8 hours. It is worth running because it closes the
REM   axis either way, not because we expect a win.
REM
REM   VRAM headroom is 0.23 GiB. Do not add any other axis to this run.
REM
REM   CROSS-COMPARISON.  Different tokenizer means different val token
REM   boundaries. CE is NOT comparable to any existing run (trap 2).
REM   Only scripts/common_bpb.py is valid.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P067_stage2_gemma270m_full --note "[1/3] train - 2289 steps with the gemma-3-270m teacher"
python scripts\runlog.py --name P067_stage2_gemma270m_full -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 2 --accum 64 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --ce-chunk 1024 --kd --kd-every 4 --kd-chunk 512 --teacher-dtype bf16 --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29 --kd-teacher-hf HF\models--google--gemma-3-270m --tag G270Tfull
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=G270Tfull
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
echo.
python scripts\runlog.py --name P067_stage2_gemma270m_full --note "[2/3] common-text bpb - the ONLY valid cross-tokenizer comparison"
python scripts\runlog.py --name P067_stage2_gemma270m_full -- python scripts\common_bpb.py --preset m100R1c --models G270Tfull --tokenizer-hf HF\models--google--gemma-3-1b-pt\snapshots\fcf18a2a879aab110ca39f8bffbccd5d49d8eb29
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P067_stage2_gemma270m_full --note "[3/3] and our standard baseline on the same common text"
python scripts\runlog.py --name P067_stage2_gemma270m_full -- python scripts\common_bpb.py --preset m100R1c --models mC_initonly_nc
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P067_stage2_gemma270m_full --note "READ IN THIS ORDER" "1. reserved GiB during the run. Headroom was 0.23 in the probe. If it OOMs," "   the narrow shape (micro-bs 1, accum 128) costs 13.1 hours instead." "2. grad_max from the json, not the printed printed g." "3. do NOT compare val_loss to any existing run. Different tokenizer." "4. steps 2 and 3 together. That difference is the whole result: does a real" "   external teacher beat our no-KD baseline on common text." "5. result 041 says a good teacher still fell short by -0.0078 bpb. If this" "   lands in the same place, the KD axis closes for good and that is worth" "   the 8.8 hours."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
