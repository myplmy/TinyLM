@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P088_Stage7_common_bpb_ruler.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     The bpb resolution we quote, 0.008, is a conversion of the RETIRED 0.024
REM     fallback. Converting the measured family rulers instead gives 0.00069 for
REM     dense - 11.6 times smaller. Nobody has ever measured seed noise on the
REM     common corpus. Result 075 section 14.2 shows what that costs: we ran a
REM     test whose target effect was one fifth of the ruler, i.e. zero power.
REM
REM   HOW: seed replicas already exist for three families. One call, all models,
REM     because common_bpb only builds the comparison table when a single call
REM     has two or more models.
REM
REM   ARM 2 fills the two Muon multipliers Stage6 left out (x30 and x45). They go
REM     in their own call because they are 763-step runs and must never share a
REM     table with 2289-step runs.
REM
REM   MEMORY: --micro-bs 2 --ce-chunk 4096 on both calls. Vocab 32,768 is small,
REM     but the flags cost nothing and E22 was paid for twice already.
REM
REM   READ IN THIS ORDER
REM     1. the skipped list. Any missing name means the global ckpt search failed.
REM     2. within each family, the absolute bpb difference between seeds. THAT is
REM        the ruler. Take the largest per family.
REM     3. compare it with 0.008. If it lands near 0.0007 to 0.003, the printed
REM        0.008 is 3 to 11 times too big and result 075 section 14.2 reopens.
REM     4. do NOT compare across families here. Different architectures.
REM
REM   NO TRAINING. COST: about 0.6h.   PLAN: test_plan/P088 Stage7
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P088_stage7_common_bpb_ruler --note "[1/2] seed replicas across three families - this measures the ruler"
python scripts\runlog.py --name P088_stage7_common_bpb_ruler -- python scripts\common_bpb.py --preset m100s8 --data-default ko-en --tokens 300M --micro-bs 2 --ce-chunk 4096 --models d8_dense d8_dense_s2 d8_dense_s3 d12_dense d12_dense_s2 d16_dense d16_dense_s2 d12_cla2_r20 d12_cla2_r20_s2 d16_cla2_r20 d16_cla2_r20_s2 mC_initonly mC_initonly_s2 mC_initonly_s3 mC_cla2_ag4_r20 mC_cla2_ag4_r20_s2 mC_cla2_ag4_r20_s3
if errorlevel 1 echo [WARN] seed ruler call failed - read the skipped list - continuing

python scripts\runlog.py --name P088_stage7_common_bpb_ruler --note "[2/2] Muon x30 and x45 - the two arms Stage6 left out of the 763-step table"
python scripts\runlog.py --name P088_stage7_common_bpb_ruler -- python scripts\common_bpb.py --preset m100s8 --data-default ko-en --tokens 300M --micro-bs 2 --ce-chunk 4096 --models d12_cla2_r20_s763_adamw d12_cla2_r20_s763_muon15 d12_cla2_r20_s763_muon30 d12_cla2_r20_s763_muon45
if errorlevel 1 echo [WARN] Muon bracket call failed - continuing - continuing

python scripts\runlog.py --name P088_stage7_common_bpb_ruler --note "DONE. The ruler is the LARGEST within-family seed gap, not the mean. n is 2 or 3 so the ruler itself has a relative sd near 52 or 36 percent."

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
