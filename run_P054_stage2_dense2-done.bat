@echo off
REM =============================================================================
REM  P054 stage 2  -  option C: does the PARENT matter
REM                   2 training runs, about 3.2 hours
REM
REM  THE PROBLEM  (user, 2026-08-22)
REM    runs\logs\m100_ko-en_300M_dense.json is old format. seed, pool_tokens,
REM    micro_bs, accum, grad_ckpt, anneal_end, decay_frac are all null. We cannot
REM    reproduce the condition that produced our canonical teacher.
REM    And result 049 s9.4 measured that dense beats all four regenerations by
REM    0.0055 to 0.0098, four out of four - with no explanation, because the
REM    condition cannot be reproduced.
REM
REM  WHY NOT JUST REPLACE THE PARENT
REM    --init-from is the starting point of every tied run. Changing it
REM    invalidates mC_initonly (3.6776, the reference for every delta), the five
REM    rows of the lever table, the three no-KD levers, both model candidates and
REM    the two sigma runs. Thirteen runs, about twenty hours, plus a condition
REM    banner on every result document (trap 2).
REM
REM  WHAT THIS BATCH DOES INSTEAD
REM    Trains dense2 with EVERY field recorded, then trains one tied model from
REM    it, and asks whether that tied model differs from mC_initonly.
REM      delta under 0.0034  means  the parent does not matter. We can switch any
REM                              time, and every existing result stays valid.
REM      delta at or above    means  the parent moves results. Then the 0.0055 to
REM                              0.0098 in result 049 is a real bias and the
REM                              twenty hour option deserves a serious look.
REM
REM    !! This is not an alternative to replacing the parent. It is the thing
REM       that decides whether spending twenty hours is worth it, and it costs
REM       3.2. Either way dense2 remains - a fully recorded dense.
REM
REM  RECORDING RULE adopted 2026-08-22 (cost zero, applied here)
REM    Every flag is written out explicitly. No reliance on defaults. Defaults
REM    change silently when code changes; that is how dense ended up
REM    unreproducible in the first place.
REM
REM  !! dense IS NOT DELETED OR OVERWRITTEN
REM    --tag dense2 keeps it in its own checkpoint namespace. checkpoints.tsv
REM    marks the original PROTECTED.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P054_stage2_dense2 --note "=============================================================================" "P054 stage 2   option C   does the parent matter" "3.2 hours to decide whether a 20 hour parent swap is worth it." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P054_stage2_dense2 --note "[1/3] dense2 - a dense teacher with EVERY field written out explicitly"
python scripts\runlog.py --name P054_stage2_dense2 -- python run100m.py train --preset m100 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.60 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --tag dense2
if errorlevel 1 goto ERROR

echo.
python scripts\runlog.py --name P054_stage2_dense2 --note "[wandb] push dense2"
set TL_WB_TAG=dense2
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P054_stage2_dense2 --note "[wait] let WDDM release VRAM - result 037 s7.3"
timeout /t 15 /nobreak

python scripts\runlog.py --name P054_stage2_dense2 --note "[2/3] mC_init2 - identical to mC_initonly except the parent is dense2"
python scripts\runlog.py --name P054_stage2_dense2 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --init-from --init-from-tag dense2 --tag mC_init2
if errorlevel 1 echo [WARN] mC_init2 failed - continuing

echo.
python scripts\runlog.py --name P054_stage2_dense2 --note "[wandb] push mC_init2"
set TL_WB_TAG=mC_init2
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P054_stage2_dense2 --note "[3/3] the whole question in one line - paired full-val, mC_init2 against mC_initonly"
python scripts\runlog.py --name P054_stage2_dense2 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_init2 mC_initonly
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P054_stage2_dense2 --note "=============================================================================" "READ IN THIS ORDER" "1. dense2 json must have seed, pool_tokens, micro_bs, accum, grad_ckpt," "   anneal_end and decay_frac ALL non-null. That was the point." "2. dense2 full-val against dense. Result 049 s9.4 says regenerations land" "   0.0055 to 0.0098 WORSE. If dense2 lands there too, the pattern holds and" "   it is a property of regeneration, not of any one run." "3. step [3] is the answer. Ruler is 2 sigma = 0.0034 (no-KD)." "   under 0.0034  means the parent does not matter. Every existing result stays" "                    valid and we can switch parents whenever we like." "   at or above   means the parent moves results. Result 049 s9.4 is a real bias" "                    and the 20 hour parent swap deserves a serious look." "!! Whatever the answer, dense2 stays. It is our first fully recorded dense." "!! dense was NOT touched. Different tag, different checkpoint file." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:ERROR
echo.
python scripts\runlog.py --name P054_stage2_dense2 --note "[STOP] dense2 failed. mC_init2 initialises FROM it, so there is nothing to" "run next. Fix dense2 first."
if not defined TL_NOPAUSE pause
exit /b 2

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
