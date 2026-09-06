@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage6_common_bpb_full.bat -- the cell Stage5 could not see
REM ==========================================================================
REM
REM   WHY THIS EXISTS
REM     the queue ran Stage5 (common_bpb, 8 models) at position 2 and Stage4
REM     (which TRAINS d16_cla2_r20_p12_t300) at position 5. So the model that
REM     closes the 2x2 did not exist yet when the common ruler was applied.
REM     Result 075 section 11.6 records that as a batch-ordering defect of
REM     mine: when you order a queue, ask whether an earlier batch consumes a
REM     later batch's output.
REM
REM   WHAT IT BUYS
REM     the 2x2 of depth x tokens is currently drawn on the 1.2B pool's own
REM     training-log val, which has ZERO Korean. Putting all four cells on
REM     the common English text gives a second, independent reading of the
REM     interaction (-0.00687 on log val, 2.31x the interaction ruler).
REM
REM   THREE MORE MODELS COME ALONG FOR FREE
REM     d12_cla2_r20_s34 (3:4 sparse) has never been on the common ruler, and
REM     neither have the four Muon arms. They are 763-step runs so they are
REM     NOT comparable with the 2289-step ones - but they ARE comparable with
REM     each other, and that is a second ruler on the Muon verdict which so
REM     far rests on one val set.
REM
REM   ONE CALL, NOT THREE
REM     common_bpb only builds a comparison table when a single call carries
REM     more than one model (lint rule 24b). Splitting the call exits 0 and
REM     prints nothing. The 763-step arms go in a SECOND call because mixing
REM     step counts in one table invites exactly the comparison we forbid.
REM
REM   --micro-bs 2 --ce-chunk 4096 ARE NOT OPTIONAL
REM     E22: without them the CE fp32 copy plus logits blows past 8 GiB.
REM
REM   NO TRAINING. Inference only. COST: about 0.3h.
REM   PLAN: test_plan/P088 (Korean filename) Stage6
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P088_stage6_common_bpb_full --note "[1/2] nine 2289-step models - adds d16_cla2_r20_p12_t300 and the 3:4 arm"
python scripts\runlog.py --name P088_stage6_common_bpb_full -- python scripts\common_bpb.py --preset m100s8 --data-default ko-en --tokens 300M --micro-bs 2 --ce-chunk 4096 --models d12_cla2_r20_p300_e1 d12_cla2_r20_p300_e2 d12_cla2_r20_p300_e4 d12_cla2_r20 d16_cla2_r20 d12_cla2_r20_p12_t300 d12_cla2_r20_p12_t600 d16_cla2_r20_p12_t300 d16_cla2_r20_p12_t600 d12_cla2_r20_s34
if errorlevel 1 echo [WARN] main table failed - continuing

python scripts\runlog.py --name P088_stage6_common_bpb_full --note "[2/2] the four 763-step Muon arms - SEPARATE table, different step count"
python scripts\runlog.py --name P088_stage6_common_bpb_full -- python scripts\common_bpb.py --preset m100s8 --data-default ko-en --tokens 300M --micro-bs 2 --ce-chunk 4096 --models d12_cla2_r20_s763_adamw d12_cla2_r20_s763_muon1 d12_cla2_r20_s763_muon5 d12_cla2_r20_s763_muon15
if errorlevel 1 echo [WARN] muon table failed - continuing

echo.
python scripts\runlog.py --name P088_stage6_common_bpb_full --note "=================================================================" "READ IN THIS ORDER" "1. the skipped list in BOTH calls. Ten then four. Any missing name" "   means the global checkpoint search did not resolve it." "2. the 2x2 on the common ruler:" "     d12 t300 / d12 t600 / d16 t300 / d16 t600" "   compute (d16t600 - d12t600) - (d16t300 - d12t300). The log-val" "   value was -0.00687. Same sign means the interaction is real and" "   not an artefact of the Korean-free 1.2B val." "3. d12_cla2_r20_s34 versus d12_cla2_r20. Result 008 section 6 put" "   the cost at +0.04203 nats on log val. bpb has its own ruler" "   (0.008) so convert before judging - do not compare nats to bpb." "4. the Muon table is a SEPARATE reading. Only compare the four" "   763-step arms with each other. Never against the 2289-step rows." "5. absolute bpb is 8.7 percent contaminated (result 053). Valid" "   between OUR models, void against external ones." "================================================================="

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
