@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P028_stage3_filtered_retrain.bat -- P028 STAGE 3 : does training ON the
REM         filtered corpus actually make a better model
REM  Plan: test_plan\P028_...md   Basis: result 023 section 8 / result 011 section 1
REM =============================================================================
REM
REM PRECONDITION: IMPLEMENTED 2026-08-06.
REM   train() now forwards --doc-filter to prepare(). Before today the filter
REM   could BUILD a cache that nothing could TRAIN on - the same class of gap as
REM   result 023 section 2 ("separating it and reading the separated thing are
REM   two different jobs"). Verified: tinylm/cli.py passes doc_filter into
REM   trainer.train, trainer.train passes it into prepare.
REM
REM ***THIS IS A LONG UNATTENDED RUN. START IT AND WALK AWAY.***
REM   about 30 min tokenising + about 2 hours training + 1 min eval.
REM   It needs no decisions in the middle and depends on no other experiment.
REM
REM THE QUESTION
REM   Result 023 section 8 measured val loss 6.0879 -^> 4.4771 after filtering.
REM   That was NOT a model improvement - the model was unchanged and only the
REM   val set moved. It means "26 percent of the pre-filter loss was spam".
REM   Nobody has ever trained on the filtered data. This run does that.
REM
REM WHY THE CONTROL IS THE EXISTING CHECKPOINT
REM   m100_ko-edu-en_300M_dense.pt : 300M pool, 2289 steps, lr 1e-3, cosine,
REM   NO filter. This run matches all of that and changes ONE thing, the filter.
REM   --exact-cache is required so prepare cannot silently pick up the unrelated
REM   ko-edu-en_600000000_filtered cache through the superset-reuse path.
REM
REM ***HOW IT IS JUDGED - AND WHY NOT BY val_loss.***
REM   Filtering REMOVES documents, so the stream shifts, and val is the last
REM   0.5 percent of the stream. The filtered run and the control therefore have
REM   DIFFERENT val sets. Comparing their val_loss would repeat exactly the
REM   mistake result 006 section 5 documents.
REM   So the verdict comes from common_bpb.py on SQuAD: same source text, same
REM   bytes, val set never enters. The control number already exists:
REM   ko-edu-en dense bpb = 1.5182 (result 011 section 1).
REM
REM ***EXPECTATION BEFORE THE NUMBER.***
REM   bpb resolution is about 0.008. Removing 13 percent of characters that were
REM   unpredictable spam should help, but the training budget is unchanged, so
REM   the model also sees 13 percent LESS unique text. Both signs are plausible.
REM   A gap under 0.008 means "the filter bought nothing measurable at 300M",
REM   which is a real answer and closes the question cheaply.
REM
REM COST: about 2.5 hours total, one GPU run of about 2 hours.
REM ERRORLEVEL POLICY: prepare and train are prerequisites, so they stop the
REM   batch. The final eval only warns.
REM =============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100_ko-edu-en_300M_dense.pt goto NOCTRL

echo =============================================================
echo [P028-3] train ON the filtered corpus - the never-measured half
echo =============================================================
python scripts\runlog.py --name P028-stage3 --note "[P028-3] train ON the filtered corpus - the never-measured half"

echo.
echo =============================================================
echo [1/3] build the filtered 300M cache (about 30 min, no GPU)
echo       CHECK THE [filter] AND [mix] LINES BEFORE LEAVING
echo =============================================================
python scripts\runlog.py --name P028-stage3 --note "[1/3] build the filtered 300M cache - check the [filter] and [mix] lines"
python scripts\runlog.py --name P028-stage3 -- python run100m.py prepare --data ko-edu-en --tokens 300M --exact-cache --doc-filter
if errorlevel 1 goto PREPBAD

echo.
echo =============================================================
echo [2/3] train dense on the filtered cache (about 2 hours)
echo       the log header must say ..._300000000_filtered
echo =============================================================
python scripts\runlog.py --name P028-stage3 --note "[2/3] train dense on the filtered cache - header must say _filtered"
python scripts\runlog.py --name P028-stage3 -- python run100m.py train --arch dense --data ko-edu-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --eval-every 100 --compile --exact-cache --doc-filter --tag densef
if errorlevel 1 goto TRAINBAD

echo.
echo =============================================================
echo [3/3] the verdict - common source text, val set never enters
echo =============================================================
python scripts\runlog.py --name P028-stage3 --note "[3/3] verdict on common source text"
python scripts\runlog.py --name P028-stage3 -- python scripts\common_bpb.py --models dense densef --data ko-edu-en ko-edu-en --tokens 300M --max-docs 4000
if errorlevel 1 echo [WARN] common_bpb failed - the checkpoint is still on disk, re-run this step alone

python scripts\runlog.py --name P028-stage3 --note "=================================================================" "WHAT TO RECORD" "  1. the [filter] line from [1/3]: how many documents and characters went." "     Result 023 removed 1,959 docs / 388.0M chars at the 600M pool." "  2. the [mix] line from [1/3]. If a source is flagged EXHAUSTED, the" "     comparison to the control is weaker than it looks - say so." "  3. the bpb column from [3/3]. dense is the control (1.5182 in result 011" "     section 1), densef is the filtered-trained model." "  4. final val_loss for the record, marked NOT COMPARABLE to the control." "" "HOW TO READ IT" "  densef bpb lower by more than 0.008" "      -^> filtering buys real quality. Then the ko-en pipeline deserves the" "         same treatment and P037 gets a new stage." "  gap under 0.008" "      -^> the filter cleans the METRIC but not the MODEL at this budget." "         That closes the question. Keep the filter anyway - a val set that" "         measures spam is worth removing on its own." "  densef clearly worse" "      -^> 13 percent less unique text hurt more than the spam did. Record it;" "         it bounds how aggressive future filters should be." "" "LIMITS: one seed / 300M budget only / ENGLISH-ONLY verdict text (SQuAD) while" "  the filter targeted Korean-side spam - so this can UNDERSTATE the benefit." "  The val_loss of the two runs is NOT comparable (different val sets)." "================================================================="
echo done.
pause
exit /b 0

:NOCTRL
echo.
echo =================================================================
echo [STOP] control checkpoint runs\ckpt\m100_ko-edu-en_300M_dense.pt
echo        is missing. Without it there is nothing to compare against.
echo =================================================================
pause
exit /b 5

:PREPBAD
echo.
echo =================================================================
echo [STOP] prepare failed. No GPU time was spent.
echo =================================================================
pause
exit /b 3

:TRAINBAD
echo.
echo =================================================================
echo [STOP] training failed. The filtered cache is built and reusable,
echo        so a re-run skips step [1/3].
echo =================================================================
pause
exit /b 4

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
