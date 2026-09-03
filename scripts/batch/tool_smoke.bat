@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  tool_smoke.bat  --  instrumentation contract smoke test (tiny preset, synthetic data)
REM  *** MODULE. NOT AN EXPERIMENT. ***
REM
REM  Do not point a user at this file to "run experiment X". It has no experiment
REM  number, no plan reference and no place in test_result. An experiment is a
REM  batch in the REPO ROOT that sets the variables below and calls this. That is
REM  what makes a run identifiable later; a bare tool invocation is not.
REM
REM  WHY THIS SHAPE
REM    These files used to be run_P0NN_*.bat - a plan number welded to a tool. So
REM    reusing the tool for a different plan meant either lying in the log name or
REM    copying the file. Both happened. The tool now carries only the function and
REM    the caller carries the identity.
REM
REM  CALLING IT
REM    set TL_LOGNAME=P0NN-stageM
REM    set TL_NOPAUSE=1
REM    call scripts\batch\tool_smoke.bat
REM    if errorlevel 1 echo [WARN] ... - continuing
REM
REM  CONTRACT - inputs are ENVIRONMENT VARIABLES, not arguments.
REM    This repo bans the percent sign in .bat files (lint_bat.py E3), which rules
REM    out both the usual argument syntax AND for-loop variables. Delayed expansion
REM    with exclamation marks is the equivalent that stays inside the rule, so lists
REM    are passed as numbered slots instead of being iterated.
REM
REM    TL_LOGNAME  runlog name   default: smoke
REM    (no other inputs - the whole point is that it is a FIXED contract check)
REM    TL_NOPAUSE  set to anything to skip the pause    (callers should set it)
REM
REM  EXIT CODES: 0 ok / 9 could not find the repo root / see below for others.
REM  Every python call goes through scripts\runlog.py so the log survives a crash.
REM =============================================================================

REM  Locate the repo root. Works from the root or from this folder (double-click).
REM  A marker file is used because the percent sign is banned here.
if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ***A smoke is NEVER an experiment, so its log NEVER belongs in test_result.***
REM   Until 2026-08-07 this file passed no --outdir at all and all 13 runlog calls
REM   wrote to test_result, while run_smoke_check.bat's header claimed otherwise.
REM   The caller normally sets TL_OUTDIR; this default makes the module correct on
REM   its own too, so the invariant does not depend on who calls it.
if not defined TL_OUTDIR set TL_OUTDIR=smoketest_logs
if not defined TL_LOGNAME set TL_LOGNAME=smoke

echo =============================================================
echo [tool] instrumentation contract smoke test
python scripts\runlog.py --name !TL_LOGNAME! --note "[tool] instrumentation contract smoke test"
echo   Runs the tiny preset on synthetic data and then verifies that every
echo   field a result document depends on was actually written to the json.
echo   Minutes here, versus discovering a missing field after a long run.
echo   RUN THIS BEFORE USING ANY NEW SCRIPT.
echo =============================================================

echo.
echo [pre] static attribute check - catches cfg.WRONG_NAME without loading torch
python scripts\runlog.py --name !TL_LOGNAME! --note "[pre] static attribute check - catches cfg.WRONG_NAME without loading torch"
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_attrs.py
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_diag_data.py
if errorlevel 1 echo [WARN] check_diag_data found problems - continuing

REM  check_handoff - the handoff format drifted (4 fixed sections missing in the
REM  latest one, 2026-08-13). Convention lives in ai_dev_tool/02; this checks it.
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_handoff.py

REM  check_links - result docs get RENAMED when their conclusion changes
REM  (ai_dev_tool/03 s8). 26 broken links were found on 2026-08-13.
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_links.py
if errorlevel 1 echo [WARN] attribute check found problems - FIX THEM FIRST

echo.
echo [1] baseline
python scripts\runlog.py --name !TL_LOGNAME! --note "[1] baseline"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --tag sm_base
if errorlevel 1 echo [WARN] sm_base failed - continuing

echo.
echo [2] seed path
python scripts\runlog.py --name !TL_LOGNAME! --note "[2] seed path"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --seed 4242 --tag sm_seed
if errorlevel 1 echo [WARN] sm_seed failed - continuing

echo.
echo [3] 3:4 path
python scripts\runlog.py --name !TL_LOGNAME! --note "[3] 3:4 path"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --sparse34 --tag sm_s34
if errorlevel 1 echo [WARN] sm_s34 failed - continuing

echo.
echo [4] wsd schedule path
python scripts\runlog.py --name !TL_LOGNAME! --note "[4] wsd schedule path"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --tag sm_sched
if errorlevel 1 echo [WARN] sm_sched failed - continuing

echo.
REM  Rule 5 (result 037 s7.3): Windows/WDDM holds VRAM for a few seconds after a
REM  run exits, so a --no-ckpt arm started immediately can die with
REM  CUBLAS_STATUS_EXECUTION_FAILED. Let the previous run settle first.
timeout /t 15 /nobreak
echo [5] no grad checkpoint path
python scripts\runlog.py --name !TL_LOGNAME! --note "[5] no grad checkpoint path"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --no-ckpt --tag sm_nockpt
if errorlevel 1 echo [WARN] sm_nockpt failed - continuing

echo.
echo [6] KD path - needs a tiny dense parent first
python scripts\runlog.py --name !TL_LOGNAME! --note "[6] KD path - needs a tiny dense parent first"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15
if errorlevel 1 echo [WARN] tiny dense parent failed - sm_kd will be skipped
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --kd --init-from --mlp-group 4 --kd-every 4 --tag sm_kd
if errorlevel 1 echo [WARN] sm_kd failed - continuing

REM =============================================================================
REM  ARMS 7 AND 8 EXIST BECAUSE OF A REAL INCIDENT (2026-08-14).
REM    transformer.py called build_attention() without importing it. Only the
REM    branch taken when attn_group is 2 or more calls it, so every arm above
REM    passed and the contract
REM    check reported 0 errors - then P057 stage 0 died three times with
REM    NameError in the experiment log (044). The smoke was run. It was clean.
REM    It simply never CONSTRUCTED a model on the new axes.
REM    Lesson: a field being recorded is not the same as a code path being taken.
REM    These two arms take the path. --init-from also covers the group-average
REM    transplant in init_utils, which is the other half of P057/P061.
REM    They need the tiny dense parent that arm [6] creates, so they come after it.
REM =============================================================================

echo.
echo [7] P057 attention tying path - construction plus group-average transplant
python scripts\runlog.py --name !TL_LOGNAME! --note "[7] P057 attention tying path - construction plus group-average transplant"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --attn-group 2 --init-from --tag sm_ag
if errorlevel 1 echo [WARN] sm_ag failed - continuing

echo.
echo [8] P061 uneven tying path - split boundary plus per-group transplant
python scripts\runlog.py --name !TL_LOGNAME! --note "[8] P061 uneven tying path - split boundary plus per-group transplant"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --mlp-split 1 --init-from --tag sm_split
if errorlevel 1 echo [WARN] sm_split failed - continuing

echo.
echo [9] P068 A1 _wq bf16 storage path - trap 37: a recorded field is not a run path
python scripts\runlog.py --name !TL_LOGNAME! --note "[9] P068 A1 _wq bf16 storage path - trap 37"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --wq-dtype bf16 --init-from --tag sm_wqbf16
if errorlevel 1 echo [WARN] sm_wqbf16 failed - continuing

echo.
echo [10] P049 17.3 reuse-attn-on-dup - trap 37: the arm must actually TURN THE AXIS ON
python scripts\runlog.py --name !TL_LOGNAME! --note "[10] P049 17.3 reuse-attn on dup - train-repeat 2.0 plus reuse"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --train-repeat 2.0 --reuse-attn-on-dup --init-from --tag sm_reuseattn
if errorlevel 1 echo [WARN] sm_reuseattn failed - continuing

echo.
echo [11] P062 stage2 inplace repeat mode - the training pair of inference where=even
python scripts\runlog.py --name !TL_LOGNAME! --note "[11] P062 stage2 repeat-mode inplace"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --train-repeat 2.0 --repeat-mode inplace --init-from --tag sm_inplace
if errorlevel 1 echo [WARN] sm_inplace failed - continuing

echo.
echo [12] P073 cla-group - trap 37: cla_group is set BEFORE the model is built
python scripts\runlog.py --name !TL_LOGNAME! --note "[12] P073 cla-group 1 - the axis must actually be ON"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --cla-group 1 --init-from --tag sm_cla1
if errorlevel 1 echo [WARN] sm_cla1 failed - continuing

echo.
echo [13] P071 ce-chunk - the plain CE path had never been chunked before 2026-08-22
python scripts\runlog.py --name !TL_LOGNAME! --note "[13] P071 ce-chunk 256 - plain CE chunking on the common path"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --ce-chunk 256 --tag sm_cechunk
if errorlevel 1 echo [WARN] sm_cechunk failed - continuing

echo.
echo [14] P074 dense student parent-init - the arm that P074 stage 1 died on
REM  ------------------------------------------------------------------------
REM  2026-08-27. run_P074_stage1_dense_depth_curve.bat lost ALL FOUR training
REM  arms to a ZeroDivisionError inside init_from_dense. Cause: config.py
REM  answered the grouping question two different ways - n_mlp_groups honoured
REM  tie_mlp, mlp_group_index did not. Every dense preset was affected.
REM  It survived every smoke run to date because no batch had ever combined
REM  --arch dense with --init-from: dense was always the scratch PARENT.
REM  This arm makes a dense student adopt the dense parent, which is the
REM  exact shape that died. --depth-init role is the mapping P074 used.
REM  ------------------------------------------------------------------------
REM  Flags match what run_P074_stage1 actually runs: gate 15 (check_smoke_coverage)
REM  reported --no-ckpt and --ce-chunk as never having been exercised under
REM  arch=dense. One arm covers the whole combination rather than the one flag
REM  that happened to break.
timeout /t 15 /nobreak
python scripts\runlog.py --name !TL_LOGNAME! --note "[14] P074 dense student + parent init - the ZeroDivisionError shape"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --no-ckpt --ce-chunk 256 --init-from --depth-init role --tag sm_denseinit
if errorlevel 1 echo [WARN] sm_denseinit failed - continuing

echo.
echo [19] --arch tied with --depth-init  (P079 - tied plus shrinking transplant)
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --no-ckpt --ce-chunk 256 --init-from --depth-init role --mlp-group 2 --tag sm_tieddepth
if errorlevel 1 echo [WARN] sm_tieddepth failed - continuing

echo.
echo [15] P074 stage 2 - dense student WITH recursion. Never combined before.
REM  ------------------------------------------------------------------------
REM  Gate 15 (check_smoke_coverage) flagged arch=dense with --train-repeat as
REM  an axis pair no smoke arm had ever run, on the day run_P074_stage2 was
REM  written and before it was queued. That is the gate doing its job.
REM  Recursion has only ever been exercised on tied models; P074 stage 2 needs
REM  it on a shallow dense one, where visit order is cycle-wise rather than
REM  block-wise.
REM  ------------------------------------------------------------------------
python scripts\runlog.py --name !TL_LOGNAME! --note "[15] P074 dense student + recursion - cycle-wise visit order"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --train-repeat 2.0 --init-from --depth-init role --tag sm_denserep
if errorlevel 1 echo [WARN] sm_denserep failed - continuing

echo.
echo [16] P075 emb-rank - the embedding factorisation rank axis
REM  ------------------------------------------------------------------------
REM  Gate 15 flagged --emb-rank as an axis that batches use but smoke has never
REM  run, on the day run_P075_stage3 was written. It also exercises the branch
REM  where the student embedding shape differs from the parent, which is where
REM  emb_init becomes svd or random - the field added on 2026-08-27 for
REM  confession A13. One arm covers both.
REM  ------------------------------------------------------------------------
python scripts\runlog.py --name !TL_LOGNAME! --note "[16] P075 emb-rank 64 + parent init - shape mismatch branch, emb_init field"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --emb-rank 64 --init-from --tag sm_embrank
if errorlevel 1 echo [WARN] sm_embrank failed - continuing

echo [17] P067 kd-chunk and teacher-dtype - the two axes gate 15 flagged
REM  ------------------------------------------------------------------------
REM  Gate 15 flagged --kd-chunk and --teacher-dtype on 2026-08-29, the day
REM  run_P067_stage2a was written. Both are KD-path axes and both CAN run on
REM  tiny/synthetic - unlike --tokenizer-hf and --kd-teacher-hf, which need real
REM  external weights and are on the ALLOW list.
REM  --kd-chunk splits the KD loss over the vocabulary. --teacher-dtype casts the
REM  teacher. Neither had ever executed in smoke, so a shape bug in either would
REM  have surfaced only after hours of a P067 run.
REM  ------------------------------------------------------------------------
python scripts\runlog.py --name !TL_LOGNAME! --note "[17] P067 kd-chunk 256 + teacher-dtype bf16 - both on the KD path"
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --kd --kd-every 4 --kd-chunk 256 --teacher-dtype bf16 --init-from --mlp-group 4 --tag sm_kdchunk
if errorlevel 1 echo [WARN] sm_kdchunk failed - continuing

echo.
echo [18] --mlp-film  (P044B - FiLM was rejected under KD; REVIEW2 removed KD)
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --init-from --mlp-group 4 --mlp-film --tag sm_film
if errorlevel 1 echo [WARN] sm_film failed - continuing

echo.
echo [21] --arch dense with --cla-group  (P079 stage 3 - CLA on a dense body, never smoked)
REM  ------------------------------------------------------------------------
REM  The axis exists and the arch exists, but never together. That is exactly
REM  the shape in which the four P074 arms died (log 059).
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --no-ckpt --ce-chunk 256 --cla-group 2 --tag sm_densecla
if errorlevel 1 echo [WARN] sm_densecla failed - continuing

echo.
echo [22] --no-cla-edges  (P084 - prelude and coda keep their own K/V)
REM  ------------------------------------------------------------------------
REM  Until 2026-09-03 owner[i] = i - (i % cla_group) ran over EVERY layer, so
REM  the head and the tail shared K/V even though every other convention here
REM  treats them as independent. The new flag groups inside the middle only.
REM  What this arm proves: the KV owner count actually CHANGES. If the flag
REM  does not reach the model the count stays put and check_smoke fails.
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --no-ckpt --ce-chunk 256 --cla-group 2 --no-cla-edges --tag sm_claedge
if errorlevel 1 echo [WARN] sm_claedge failed - continuing

echo [23] --mlp-lrm  (P086 - per-layer scalar multipliers on the shared MLP)
REM  ------------------------------------------------------------------------
REM  Learnable multipliers (arXiv:2601.04890). The parameters live on the
REM  LAYER, not on the shared MLP, so a tied stack can finally vary its scale
REM  with depth. They also carry weight decay 0.01 - without it the scale
REM  symmetry drifts and the norm grows without bound.
REM  What this arm proves: mlp_lrm lands in the json as True, which means the
REM  Layer actually built the parameters instead of silently skipping them.
python scripts\runlog.py --name !TL_LOGNAME! -- python run100m.py train --arch dense --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --no-ckpt --ce-chunk 256 --mlp-lrm --tag sm_lrm
if errorlevel 1 echo [WARN] sm_lrm failed - continuing

echo.
echo [20] return_probs diagnostic path  (P081 - SDPA does not hand back probs)
REM  ------------------------------------------------------------------------
REM  This axis CANNOT be a training arm - return_probs is blocked in train()
REM  by an assert, because the probability matrix is batch x heads x T x T.
REM  So the trap-37 arm for this axis is a standalone check instead.
REM  It asserts the whole claim: logits are BIT IDENTICAL with it on.
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_return_probs.py
if errorlevel 1 echo [WARN] return_probs check FAILED - the diagnostic path leaks into output

echo.
echo =============================================================
echo [VERIFY] every instrumentation field was recorded
python scripts\runlog.py --name !TL_LOGNAME! --note "[VERIFY] every instrumentation field was recorded"
echo =============================================================
python scripts\runlog.py --name !TL_LOGNAME! -- python scripts\check_smoke.py
if errorlevel 1 echo [WARN] contract check FAILED - read which field is missing


echo.
echo =================================================================
echo VERDICT - read the LAST line of the contract check, which reports the
echo   total error count, plus the per-run blocks above it (each is [OK] or
echo   names the field it could not find). That is the whole result.
echo.
echo   The [VERIFY] banner is just a SECTION TITLE - it is not the answer.
echo   Everything else is noise: losses from 30 steps on synthetic data mean
echo   NOTHING. Do not read them, compare them, or record them anywhere.
echo.
echo   Logs are written to smoketest_logs, deliberately not test_result.
echo =================================================================
goto DONE

:DONE
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] could not locate the repo root (run100m.py not found).
echo   Launch this from the TinyLM working folder, or let a root-level
echo   experiment batch call it. Nothing was executed.
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
