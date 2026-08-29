@echo off
REM =============================================================================
REM  P074 stage 3  -  the visit curve at FIXED parameters and FIXED memory
REM                   3 training runs plus paired eval and residency
REM                   about 3.8 hours
REM
REM  WHY THIS IS THE HIGHEST VALUE RUN WE CAN MAKE RIGHT NOW
REM    Stage 2 found that at equal parameters and equal visits, cycle-wise visiting
REM    beats block-wise by -0.0157. Result 014 section 12.2 found that decode time
REM    depends only on visit count. Put those together and one curve answers the
REM    deployment question directly:
REM
REM        parameters FIXED at 49.55M, resident FIXED at 410.8 MiB,
REM        vary ONLY the number of visits
REM        -^> quality as a function of decode cost, at zero memory cost
REM
REM    We have two points already (R=1 at 8 visits 3.6776, R=4 at 20 visits 3.6413).
REM    Three more make it a curve instead of a line through two dots.
REM
REM  ARMS (all preset m100s4 dense = 2+4+2, 4 unique middle MLPs, cla 1)
REM    R=2   visits 2 + 4x2  + 2 = 12
REM    R=3   visits 2 + 4x3  + 2 = 16
REM    R=6   visits 2 + 4x6  + 2 = 28
REM    (existing: R=1 -^> 8, R=4 -^> 20)
REM
REM  PREDICTIONS
REM    S1  resident IDENTICAL across all five. Recursion stores nothing. Check first.
REM    S2  monotone improvement in visits, with diminishing returns. Result 047
REM        measured the 20-layer recursion curve at R1 to R2 -0.0202 and R2 to R3
REM        -0.0069, a factor of 0.34 - expect the same shape here.
REM    S3  R=6 (28 visits) beats mC_d36_ag4_nokd (36 visits, 3.6848, resident 379.7)
REM        by a wide margin. If it does not, depth in distinct layers is buying
REM        something that repeated visits cannot.
REM    S4  the curve saturates before R=6. If R=4 to R=6 is under 0.0034 then
REM        R=4 is the operating point and we stop.
REM
REM  !! EVALUATE EACH AT ITS OWN TRAINED SCHEDULE - --match-train-repeat (trap 39).
REM  !! grad checkpointing stays ON for the recursion arms: dense x recursion has no
REM     VRAM measurement and 36-layer recursion is known to OOM without it (051).
REM     The ckpt drift is -0.0014 (051 stage 3), inside the 0.0034 ruler. SAY SO in
REM     the result document rather than letting the reader assume matched conditions.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P074_stage3_visit_curve --note "=============================================================================" "P074 stage 3   the visit curve at fixed parameters and fixed memory" "Parameters 49.55M and resident 410.8 MiB are held constant." "Only the number of visits changes: 12, 16, 28 (we already have 8 and 20)." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P074_stage3_visit_curve --note "[1/5] R=2 - 12 visits"
python scripts\runlog.py --name P074_stage3_visit_curve -- python run100m.py train --preset m100s4 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --ce-chunk 2048 --train-repeat 2.0 --init-from --depth-init role --tag eq_d8_r20
if errorlevel 1 echo [WARN] eq_d8_r20 failed - continuing
set TL_WB_TAG=eq_d8_r20
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P074_stage3_visit_curve --note "[2/5] R=3 - 16 visits"
python scripts\runlog.py --name P074_stage3_visit_curve -- python run100m.py train --preset m100s4 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --ce-chunk 2048 --train-repeat 3.0 --init-from --depth-init role --tag eq_d8_r30
if errorlevel 1 echo [WARN] eq_d8_r30 failed - continuing
set TL_WB_TAG=eq_d8_r30
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P074_stage3_visit_curve --note "[3/5] R=6 - 28 visits. The deep end. S3 and S4."
python scripts\runlog.py --name P074_stage3_visit_curve -- python run100m.py train --preset m100s4 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --ce-chunk 2048 --train-repeat 6.0 --init-from --depth-init role --tag eq_d8_r60
if errorlevel 1 echo [WARN] eq_d8_r60 failed - continuing
set TL_WB_TAG=eq_d8_r60
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P074_stage3_visit_curve --note "[4/5] paired - the whole curve on one ruler, each at its own trained schedule"
python scripts\runlog.py --name P074_stage3_visit_curve -- python scripts\paired_eval.py --preset m100s4 --data ko-en --tokens 300M --models eq_d8_dense eq_d8_r20 eq_d8_r30 eq_d8_r40 eq_d8_r60 --match-train-repeat
if errorlevel 1 echo [WARN] paired failed - continuing

echo.
python scripts\runlog.py --name P074_stage3_visit_curve --note "[5/5] residency - S1 says these are all identical"
python scripts\runlog.py --name P074_stage3_visit_curve -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s4 --models eq_d8_dense eq_d8_r20 eq_d8_r30 eq_d8_r40 eq_d8_r60 --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P074_stage3_visit_curve --note "=============================================================================" "READ IN THIS ORDER" "1. S1 first. Five identical resident numbers or the accounting is wrong." "2. plot full-val against VISITS (8, 12, 16, 20, 28). Result 014 section 12.2" "   says decode time is linear in visits, so this plot IS the quality against" "   speed frontier at fixed memory. That plot is what REVIEW3 needs." "3. S4 - is R=4 to R=6 under 0.0034. If yes we have the operating point." "4. S3 - R=6 against mC_d36_ag4_nokd 3.6848. Both cost about the same at" "   decode (28 vs 36 visits) but R=6 uses 410.8 MiB against 379.7." "5. val minus train_ce will be large for every arm - trap 39, expected." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
