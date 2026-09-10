@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage11_bpb_two_families.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     We now have two token families and no way to compare them.
REM       300M tokens on a 600M pool  - val is ko-en_300M/val.bin
REM       600M tokens on a 1200M pool - val is ko-en_600M/val.bin
REM     Different val sets, so the training-log numbers CANNOT be subtracted
REM     across the two (trap 2). common_bpb is the only valid bridge: same
REM     SQuAD text, same bytes, bpb = loss / ln2 / bytes-per-token.
REM
REM     This was structurally impossible until 2026-09-10. --tokens was a
REM     single value and it is part of the checkpoint FILENAME, so one call
REM     could only ever hold one family - and common_bpb only prints a
REM     comparison table when a single call holds two or more models.
REM     --tokens now takes one value per model, the same way --data does.
REM     Give it one value and nothing changes.
REM
REM   READ IN THIS ORDER
REM     1. The ruler is 0.0038 unless the shape is in _rulers.BPB_BY_SHAPE.
REM     2. Subtract within a depth: d12 300M minus d12 600M, and so on.
REM        Four pairs. If all four clear the ruler the token gain is confirmed
REM        on an independent corpus.
REM     3. If the ORDER flips, that is the headline. Result 075 section 11.1
REM        has a precedent - a different pool flipped the order once already.
REM     4. Watch d18_t600 against d16_t600. The training log says -0.00906.
REM        If the independent ruler does not see it, the 40 MiB quality
REM        verdict goes back on hold.
REM     5. Absolute bpb is optimistic - 8.7 percent of the 4,000 documents
REM        overlap our training stream. Our models share that, so comparing
REM        THEM is valid; comparing to an outside model is not.
REM
REM   NOT A CONFOUND-FREE COMPARISON
REM     The 600M family doubled BOTH the tokens and the pool. This table
REM     cannot separate those two. Say so when quoting it.
REM
REM   NO --tokenizer-hf HERE. All eight models use our native ko-en tokenizer.
REM     That flag has a different contract in this tool (TAG=folder) and it
REM     cost 9.2 hours once. It is simply not needed, so it is not given.
REM
REM   COST: about 0.3h, no training.   PLAN: test_plan/P088 Stage11
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P088_stage11_bpb_two_families --note "[1/1] eight models, one call - the only bridge between the two token families"
timeout /t 15 /nobreak
python scripts\runlog.py --name P088_stage11_bpb_two_families -- python scripts\common_bpb.py --preset m100s8 --data-default ko-en --models d12_cla2_r20_muon15 d14_cla2_norecur_muon15 d16_cla2_norecur_muon15 d18_cla2_norecur_muon15 d12_cla2_r20_muon15_t600 d14_cla2_norecur_muon15_t600 d16_cla2_norecur_muon15_t600 d18_cla2_norecur_muon15_t600 --tokens 300M 300M 300M 300M 600M 600M 600M 600M --max-docs 4000 --seq 1024 --micro-bs 8
if errorlevel 1 echo [WARN] common_bpb failed - continuing

python scripts\runlog.py --name P088_stage11_bpb_two_families --note "DONE. Subtract within a depth. Ruler 0.0038. An order flip is the headline."

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
