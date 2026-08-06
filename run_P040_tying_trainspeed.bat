@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P040_tying_trainspeed.bat -- P040 : does tying actually make TRAINING
REM                                   faster, and if so why
REM  Basis: docs\ 2026-08-06 tying analysis report, section 3
REM =============================================================================
REM
REM PRECONDITION: none. Everything used here already exists.
REM
REM THE QUESTION
REM   EXPERIMENT_BASELINES section 2.1 shows dense 97.5 / g4 94.9 / g8 89.9 min,
REM   i.e. g8 is 7.8 percent faster. But TWO g4 runs in the same table differ by
REM   3.5 min (3.7 percent), and those are old logs with no grad-ckpt or EMA
REM   field, so the conditions are not actually known.
REM
REM   Theory says tying should buy almost nothing here. Forward and backward
REM   both traverse ALL 20 layers either way - report()'s FLOPs formula has no
REM   mlp_group term and prints 0.248 GFLOP/token for both. The only thing that
REM   shrinks is the AdamW step, which is about 0.13 percent of a 3057 ms step.
REM
REM   So: if -7.8 percent is real, the cause is CACHE, not parameter count. That
REM   would match the inference finding (per-layer cost g8 0.913 ^< g4 1.022 ^<
REM   dense 1.163 ms, result 014 section 11).
REM
REM ***EXPECTATION BEFORE THE NUMBER.***
REM   Two outcomes are informative and neither is a failure:
REM     under 2 percent -^> the old table was noise. Stop saying tying speeds up
REM                        training. Memory is the whole story.
REM     5 to 10 percent -^> real, and attributable to cache locality because
REM                        parameter count cannot explain it.
REM
REM MEASUREMENT HYGIENE
REM   run ALONE (result 015: a co-running job cost 14 percent).
REM   idle 5 minutes first (result 016 section 12: a finished job cost 2-9 pct).
REM   250 steps is a SPEED probe. ***DO NOT READ val_loss FROM THIS RUN.***
REM   CLAUDE.md: at 250 steps grad_max sits in the 10-35 unstable band and the
REM   loss means nothing.
REM
REM ***CONVERT THE ms/step.*** The printed value is a CUMULATIVE MEAN including
REM   the torch.compile first step. Steady state = (mean x N - step0) / (N - 1).
REM   Comparing the printed means directly is the error this project has made
REM   before.
REM
REM CONDITIONS - identical except --mlp-group
REM   ko-en / 300M name / pool 600M exact / 250 steps / mb8 accum16 seq1024
REM   lr 1e-3 / cosine / grad-ckpt ON for BOTH / no KD / no init-from / seed 1337
REM   grad-ckpt must match: --no-ckpt is worth -17.3 percent on its own and
REM   would swamp the effect being measured.
REM
REM COST: about 30 to 40 minutes total. Writes two throwaway tags.
REM ERRORLEVEL POLICY: independent runs, so a failure warns and continues.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P040] tying and TRAINING speed - is the 7.8 percent real
echo =============================================================
python scripts\runlog.py --name P040-trainspeed --note "[P040] tying and TRAINING speed - is the 7.8 percent real"

echo.
echo [pre] run this alone, after 5 minutes idle. Close other GPU users.
python scripts\runlog.py --name P040-trainspeed --note "[pre] solo run + 5 min idle required"

echo.
echo =============================================================
echo [1/2] dense, 250 steps
echo =============================================================
python scripts\runlog.py --name P040-trainspeed --note "[1/2] dense, 250 steps"
python scripts\runlog.py --name P040-trainspeed -- python run100m.py train --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 999 --compile --seed 1337 --tag ts_dense
if errorlevel 1 echo [WARN] dense run failed - continuing

echo.
echo =============================================================
echo [2/2] tied g8, 250 steps - ONLY --mlp-group differs
echo =============================================================
python scripts\runlog.py --name P040-trainspeed --note "[2/2] tied g8, 250 steps - only --mlp-group differs"
python scripts\runlog.py --name P040-trainspeed -- python run100m.py train --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 250 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 999 --compile --seed 1337 --mlp-group 8 --tag ts_g8
if errorlevel 1 echo [WARN] tied run failed - continuing

python scripts\runlog.py --name P040-trainspeed --note "=================================================================" "WHAT TO RECORD" "  1. wall clock minutes for each run, from the runlog footer." "  2. STEADY-STATE ms/step, converted: (printed mean x N - step0) / (N - 1)." "     The printed number is a cumulative mean and includes the compile step." "  3. the toklen-per-FLOPs line from each report() header. It should read" "     0.248 GFLOP for BOTH - that is the point." "  4. peak VRAM. Tying should cut optimiser state roughly in half; that is a" "     CAPACITY win and it is real even if the time win is not." "" "***DO NOT RECORD val_loss.*** 250 steps is a speed probe only." "" "HOW TO READ IT" "  gap under 2 percent" "      -^> EXPERIMENT_BASELINES section 2.1 was noise. Correct the wording" "         everywhere: tying buys memory, not training time." "  gap 5 to 10 percent, same direction as g" "      -^> real. Attribute it to CACHE LOCALITY, not parameter count - the" "         AdamW step is only 0.13 percent of a step, so it cannot be the cause." "         Then a g4 arm is worth adding to see if it is monotone in g." "  tied SLOWER" "      -^> also informative. Gradient accumulation into a shared tensor is" "         extra work that dense does not do." "" "LIMITS: one seed / 250 steps / one machine / grad-ckpt ON for both (with" "  --no-ckpt the answer could differ, and -17.3 percent would swamp it)." "================================================================="
echo done.
pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
