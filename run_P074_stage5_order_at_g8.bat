@echo off
REM =============================================================================
REM  P074 stage 5  -  does "cycle beats block" survive a different grouping
REM                   2 training runs plus paired eval, about 3.5 hours
REM
REM  WHY
REM    Stage 2 found cycle-wise visiting beats block-wise by -0.0157 at 4.6 sigma.
REM    That is ONE point: 4 unique middle MLPs, 4 unique attentions, 20 visits.
REM    Two points do not make a curve and one point does not open an axis - this
REM    repository has written that rule down after being burned by it (result 032
REM    section 8.3, decision trap on convexity from a single point).
REM    If the effect holds at a different grouping it is a property of visit order.
REM    If it does not, it is a property of that particular configuration.
REM
REM  ARMS - parameter-matched again, at HALF the unique blocks
REM    E2'  m100R1c tied, --attn-group 8 --cla-group 1
REM         2+16+2 = 20 visits, 2 unique middle MLPs (g8), 2 unique attentions
REM         order: block-wise  1 1 1 1 1 1 1 1  2 2 2 2 2 2 2 2
REM    E3'  m100s2 dense, --train-repeat 8.0
REM         2+2x8+2 = 20 visits, 2 unique middle MLPs, 2 unique attentions (cla 1)
REM         order: cycle-wise  1 2 1 2 1 2 1 2 1 2 1 2 1 2 1 2
REM    (E1' m100s2 dense at 6 visits already exists as d6_dense, 3.7278)
REM
REM  PREDICTIONS
REM    Q1  resident identical between E2' and E3'. Check first. The unique blocks
REM        and the prelude/coda are the same; only visit order differs.
REM    Q2  cycle wins again, by 0.010 to 0.025. Stage 2 got -0.0157 at 4 blocks.
REM    Q3  the gap is LARGER at 2 blocks than at 4. Block-wise repeats the same
REM        function 8 times in a row here instead of 4, so the composition
REM        mismatch that result 041 section 17 described should be worse.
REM    Q4  if cycle does NOT win here, stage 2's finding is configuration-specific
REM        and must be restated as such in result 059 and REVIEW3.
REM
REM  !! --match-train-repeat for E3' (trap 39).
REM  !! E3' keeps grad checkpointing ON - dense x recursion has no VRAM measurement.
REM     Drift is -0.0014 (051 stage 3), inside the ruler. State it in the writeup.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P074_stage5_order_at_g8 --note "=============================================================================" "P074 stage 5   does cycle-beats-block survive a different grouping" "Stage 2 measured one point (4 unique blocks). This is the 2-block point." "One point does not open an axis. About 3.5 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

echo.
python scripts\runlog.py --name P074_stage5_order_at_g8 --note "[1/4] E2 prime - tied 2+16+2 with attn_group 8, block-wise order"
python scripts\runlog.py --name P074_stage5_order_at_g8 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --attn-group 8 --cla-group 1 --init-from --tag eq_t20_ag8
if errorlevel 1 echo [WARN] eq_t20_ag8 failed - continuing
set TL_WB_TAG=eq_t20_ag8
call scripts\batch\tool_wandb_push.bat

timeout /t 15 /nobreak

echo.
python scripts\runlog.py --name P074_stage5_order_at_g8 --note "[2/4] E3 prime - dense 2+2+2 trained at R=8, cycle-wise order"
python scripts\runlog.py --name P074_stage5_order_at_g8 -- python run100m.py train --preset m100s2 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --ce-chunk 2048 --train-repeat 8.0 --init-from --depth-init role --tag eq_d6_r80
if errorlevel 1 echo [WARN] eq_d6_r80 failed - continuing
set TL_WB_TAG=eq_d6_r80
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P074_stage5_order_at_g8 --note "[3/4] paired - the 2-block pair, plus the 4-block pair for the slope"
python scripts\runlog.py --name P074_stage5_order_at_g8 -- python scripts\paired_eval.py --preset m100s2 --data ko-en --tokens 300M --models eq_d6_r80 eq_t20_ag8 eq_d8_r40 eq_t20_ag4 --match-train-repeat
if errorlevel 1 echo [WARN] paired failed - continuing

echo.
python scripts\runlog.py --name P074_stage5_order_at_g8 --note "[4/4] residency - Q1"
python scripts\runlog.py --name P074_stage5_order_at_g8 -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s2 --models eq_d6_r80 eq_t20_ag8 --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P074_stage5_order_at_g8 --note "=============================================================================" "READ IN THIS ORDER" "1. Q1 - resident identical for the pair. If not, the arms are not matched and" "   nothing below means anything." "2. Q2 - cycle minus block at 2 unique blocks. Stage 2 got -0.0157 at 4." "3. Q3 - is the gap larger at 2 blocks than at 4. Two points make a slope and" "   that slope is the actual finding, not either point alone." "4. Q4 - if cycle does NOT win, go back to result 059 section 11 and REVIEW3" "   section 12 and restate the stage 2 result as configuration-specific." "   DO THAT BEFORE anything else is built on it." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
