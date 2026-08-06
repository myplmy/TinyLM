@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P008_stage0_gate.bat -- P008 STAGE 0 : does s=0 really cost nothing
REM  Plan: test_plan\P008_...md section 7
REM =============================================================================
REM
REM PRECONDITION: --lora-decay IMPLEMENTED 2026-08-07. Default 0 = off.
REM
REM ***RUN THIS BEFORE STAGE 1.*** Stage 1 costs six GPU hours and its entire
REM   memory argument rests on one unverified assumption.
REM
REM THE ASSUMPTION UNDER TEST
REM   The pitch for annealed LoRA is "training gets per-layer freedom, and the
REM   adapter VANISHES by the end so deployment pays nothing". The vanishing part
REM   is only half true by construction:
REM     the CONTRIBUTION goes to zero, because forward multiplies by _scale
REM     the PARAMETERS stay in the state_dict, because nobody removed them
REM   mem_breakdown() counts a "lora" term from the parameters, so report() may
REM   still charge for them and print 1.71x instead of 1.82x.
REM
REM   If that happens the memory claim is FALSE as implemented, and stage 1
REM   would produce a quality number attached to a benefit that does not exist.
REM   Result 016 section 13 was exactly this shape of error - a feature that
REM   looked fine because the accounting could not see what it was doing.
REM
REM WHAT TO LOOK FOR - two lines, nothing else
REM   [1/2] the report() header block, specifically:
REM         "LoRA(r=32, 2bit)" row and the total, and the tied-MLP reduction
REM   [2/2] the same with --lora-rank 0, which is the reference
REM
REM   The question is whether [1/2] and [2/2] agree on deployment memory once
REM   the scale has annealed to zero. They will NOT agree on the parameter
REM   count - that is expected and is the point.
REM
REM COST: a few minutes on the tiny preset. No real training, no checkpoints
REM   that matter. Uses synthetic data so it touches no cache.
REM ERRORLEVEL POLICY: two independent probes, failures warn and continue.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P008-0] does s=0 really cost nothing
echo =============================================================
python scripts\runlog.py --name P008-stage0 --outdir smoketest_logs --note "[P008-0] does s=0 really cost nothing"

echo.
echo [guard] is --lora-decay wired into the CLI
python scripts\runlog.py --name P008-stage0 --outdir smoketest_logs --note "[guard] is --lora-decay wired into the CLI"
python -c "import sys; sys.exit(0 if '--lora-decay' in open('tinylm/cli.py',encoding='utf-8').read() else 7)"
if errorlevel 1 goto NOTIMPL

echo.
echo =============================================================
echo [1/2] tiny run WITH annealed LoRA - read the report() block
echo =============================================================
python scripts\runlog.py --name P008-stage0 --outdir smoketest_logs --note "[1/2] tiny run WITH annealed LoRA"
python scripts\runlog.py --name P008-stage0 --outdir smoketest_logs -- python run100m.py train --tiny --arch tied --data synthetic --tokens 2M --steps 30 --micro-bs 2 --accum 1 --seq 256 --lr 1e-3 --eval-every 999 --lora-rank 32 --lora-decay 0.5 --tag p8gate_anneal
if errorlevel 1 echo [WARN] annealed probe failed - continuing

echo.
echo =============================================================
echo [2/2] the same with NO LoRA - this is the memory reference
echo =============================================================
python scripts\runlog.py --name P008-stage0 --outdir smoketest_logs --note "[2/2] the same with NO LoRA - memory reference"
python scripts\runlog.py --name P008-stage0 --outdir smoketest_logs -- python run100m.py train --tiny --arch tied --data synthetic --tokens 2M --steps 30 --micro-bs 2 --accum 1 --seq 256 --lr 1e-3 --eval-every 999 --tag p8gate_none
if errorlevel 1 echo [WARN] reference probe failed - continuing

python scripts\runlog.py --name P008-stage0 --outdir smoketest_logs --note "=================================================================" "WHAT TO RECORD" "  1. the LoRA row and the total MB from the report() block of [1/2]." "  2. the same total from [2/2]." "  3. whether they match." "" "***DO NOT READ THE LOSS.*** 30 steps of tiny on synthetic data means nothing." "  Synthetic data is a memorisation benchmark, not a quality signal." "" "HOW TO READ IT" "  totals match" "      -^> s=0 costs nothing as accounted. Stage 1 is safe to run." "  [1/2] total is larger" "      -^> the LoRA parameters are still charged. Two options before stage 1:" "         (a) add a deployment path that reloads with lora_rank=0, or" "         (b) make mem_breakdown skip LoRA when the scale is zero." "         (a) is honest, (b) is a lie unless the export actually drops them." "         Pick (a). Then re-run this gate." "" "LIMITS: tiny preset, so absolute MB values mean nothing - only the COMPARISON" "  between the two runs matters. This gate says nothing about quality." "================================================================="
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
