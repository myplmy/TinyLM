@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P008_stage1_lora_anneal.bat -- P008 STAGE 1 : can an ANNEALED LoRA
REM        replace knowledge distillation
REM  Plan: test_plan\P008_...md
REM =============================================================================
REM
REM PRECONDITION: --lora-decay IMPLEMENTED 2026-08-07 (LoRA._scale buffer,
REM   Transformer.set_lora_scale, trainer schedule, cli flag). Default 0 = off.
REM
REM ***RUN run_P008_stage0_gate.bat FIRST.*** That gate checks the one thing
REM   that would invalidate this whole plan: whether s=0 really costs nothing.
REM   The LoRA PARAMETERS stay in the state_dict even when the scale is zero, so
REM   report() may still charge for them. If the reduction ratio does not read
REM   1.82x at s=0, the memory claim is false and these six hours are wasted.
REM
REM WHAT THIS TESTS
REM   LoRA can be used two completely different ways:
REM     fixed   - stays at inference, costs memory (2.07x -^> 1.94x for g8)
REM     ANNEALED - scale s(t) goes 1 -^> 0 during training, so it VANISHES.
REM                Training gets per-layer freedom early, deployment gets pure
REM                tying, and the memory cost is ZERO.
REM   That is the same idea as our ternary anneal: do not impose the constraint
REM   from step 0, tighten it as training proceeds.
REM
REM WHY IT MATTERS NOW - THE GAP IS ALREADY CLOSED, SO THIS IS ABOUT COST
REM   Result 021: mC (with KD) already BEATS dense, -0.0215. So "close the gap"
REM   is done. What is NOT done is doing it cheaply:
REM     KD path   : dense teacher 117.4 min + student 141.0 min = 258.4 min
REM     this path : student only, about 95 min
REM   If the annealed run lands within the 0.024 resolution of the KD run, the
REM   pipeline gets 2.7x cheaper, and that multiplies across every future
REM   campaign (P041 stage 2 is about 28 GPU hours).
REM
REM ***EXPECTATIONS - WRITE THEM DOWN BEFORE READING ANYTHING.***
REM   P1  p8_anneal beats p8_base by 0.03 to 0.06     (fixed LoRA gave -0.0338)
REM   P2  it still LOSES to KD, which is a -0.13 class effect
REM   P4  p8_film is below resolution on its own
REM   ***P2 losing is NOT a failure.*** Confirming "KD is not replaceable" is a
REM   result, the same way results 019 and 022 closed their lines.
REM
REM CONDITIONS - matched to mC_wsd (result 024) so stage 2 can compare
REM   m100R1c / ko-en / pool 600M exact / 300M tokens / 2289 steps
REM   mb8 accum16 seq1024 / lr 1e-3 / sched wsd / anneal-end 0.80 / seed 1337
REM   ***NO KD and NO --init-from*** - the claim under test is "without KD"
REM
REM COST: about 6 GPU hours, 4 runs of roughly 1.5h. Independent of everything.
REM ERRORLEVEL POLICY: four independent runs, so a failure warns and continues.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P008-1] annealed LoRA - can it replace KD
echo =============================================================
python scripts\runlog.py --name P008-stage1 --note "[P008-1] annealed LoRA - can it replace KD"

echo.
echo [guard] is --lora-decay wired into the CLI
python scripts\runlog.py --name P008-stage1 --note "[guard] is --lora-decay wired into the CLI"
python -c "import sys; sys.exit(0 if '--lora-decay' in open('tinylm/cli.py',encoding='utf-8').read() else 7)"
if errorlevel 1 goto NOTIMPL

echo.
echo =============================================================
echo [1/4] p8_base - plain tied g8, the control
echo =============================================================
python scripts\runlog.py --name P008-stage1 --note "[1/4] p8_base - plain tied g8, the control"
python scripts\runlog.py --name P008-stage1 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --tag p8_base
if errorlevel 1 echo [WARN] p8_base failed - continuing

echo.
echo =============================================================
echo [2/4] p8_anneal - LoRA r32 with scale annealed to zero at 0.6
echo       THIS IS THE MAIN CONDITION
echo =============================================================
python scripts\runlog.py --name P008-stage1 --note "[2/4] p8_anneal - LoRA r32, scale annealed to zero at 0.6 - MAIN"
python scripts\runlog.py --name P008-stage1 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --lora-rank 32 --lora-decay 0.6 --tag p8_anneal
if errorlevel 1 echo [WARN] p8_anneal failed - continuing

echo.
echo =============================================================
echo [3/4] p8_fixed - LoRA r32 held at 1.0, separates anneal from LoRA
echo =============================================================
python scripts\runlog.py --name P008-stage1 --note "[3/4] p8_fixed - LoRA r32 held at 1.0"
python scripts\runlog.py --name P008-stage1 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --lora-rank 32 --tag p8_fixed
if errorlevel 1 echo [WARN] p8_fixed failed - continuing

echo.
echo =============================================================
echo [4/4] p8_film - FiLM alone, 0.13 MB so it is nearly free
echo =============================================================
python scripts\runlog.py --name P008-stage1 --note "[4/4] p8_film - FiLM alone"
python scripts\runlog.py --name P008-stage1 -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --mlp-film --tag p8_film
if errorlevel 1 echo [WARN] p8_film failed - continuing

echo.
echo =============================================================
echo [5/5] paired comparison against the KD winner
echo =============================================================
python scripts\runlog.py --name P008-stage1 --note "[5/5] paired comparison against the KD winner"
python scripts\runlog.py --name P008-stage1 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models p8_base p8_anneal p8_fixed p8_film mC_wsd
if errorlevel 1 echo [WARN] paired_eval failed - the checkpoints are on disk, re-run this step alone

python scripts\runlog.py --name P008-stage1 --note "=================================================================" "WHAT TO RECORD" "  1. final val for all four, NOT best. Result 015 flipped a sign that way." "  2. grad_max from the json, not the printed 10-step sample. The old" "     t_lora32 run hit 6.20 while everything else sat at 0.5 to 1.5, so LoRA" "     raises gradients and nobody knows yet whether annealing helps or hurts." "  3. the report() reduction ratio for p8_anneal. At s=0 it should read 1.82x." "     If it reads 1.71x the LoRA parameters are still being charged and the" "     whole memory argument for this plan collapses - say so loudly." "  4. paired_eval deltas against mC_wsd (3.6442)." "" "HOW TO READ IT" "  p8_anneal beats p8_base by more than 0.024" "      -^> annealing works. Then the question is only whether it reaches KD." "  p8_anneal within 0.024 of mC_wsd" "      -^> ***the headline***. KD becomes optional and the pipeline drops from" "         258 minutes to about 95. Re-plan P041 and P033 around that." "  p8_anneal loses clearly to mC_wsd" "      -^> KD is not replaceable at this scale. Record it and close the line." "         That is a real answer, not a failure." "  p8_fixed beats p8_anneal" "      -^> the benefit needs LoRA to STAY, which costs memory. Then option (1)" "         in the plan comes back and this becomes a memory tradeoff question." "" "LIMITS: one seed / g8 only / 300M budget / no KD arm inside this batch (the" "  KD comparison reuses mC_wsd from result 024, so the schedule had to match" "  exactly - check the log headers say sched=wsd and anneal_end=0.80)." "================================================================="
echo done.
pause
exit /b 0

:NOTIMPL
echo.
echo =================================================================
echo [STOP] --lora-decay is not in the CLI. Nothing was executed.
echo =================================================================
pause
exit /b 7

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
