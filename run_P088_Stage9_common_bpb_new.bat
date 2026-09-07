@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage9_common_bpb_new.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     Eight new tags appeared on 2026-09-07 across two optimisers and two pools.
REM     Log val cannot join them. common_bpb is the only valid cross-pool ruler.
REM     One call, because common_bpb only builds the table when there is more than one model.
REM
REM   READ IN THIS ORDER
REM     1. Does the log-val ordering reproduce on an independent corpus?
REM     2. Result 075 section 11.1 has a precedent where a different pool FLIPPED the order.
REM     3. Read the printed ruler line - it now prints measured per-shape values.
REM     4. Anything smaller than the printed ruler is not ranked.
REM
REM   COST: about 0.6h, no training.   PLAN: test_plan/P088 Stage9
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P088_stage9_common_bpb_new --note "[1/1] all new tags in one call - the table only appears with 2+ models"
timeout /t 15 /nobreak
python scripts\runlog.py --name P088_stage9_common_bpb_new -- python scripts\common_bpb.py --preset m100s8 --data-default ko-en --tokens 300M --micro-bs 2 --ce-chunk 4096 --models d12_cla2_norecur d12_cla2_norecur_s2 d14_cla2_norecur d14_cla2_norecur_s2 d16_cla2_norecur d16_cla2_norecur_s2 d16_cla2_norecur_muon15 d12_cla2_r20_muon15 d12_cla2_r20_adamw
if errorlevel 1 echo [WARN] arm 1 failed - continuing

python scripts\runlog.py --name P088_stage9_common_bpb_new --note "DONE. Anything smaller than the printed ruler is not ranked."

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
