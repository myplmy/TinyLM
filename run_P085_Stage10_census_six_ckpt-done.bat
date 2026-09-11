@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage10_census_six_ckpt.bat
REM ==========================================================================
REM   WHY THIS EXISTS
REM     The first census (2026-09-10) ran with FOUR checkpoints. With four,
REM     an item's accuracy can only be 0, 1/4, 2/4, 3/4 or 1, so the D9 band
REM     0.3 to 0.7 admits exactly one cell: 2 of 4 correct. Even exchangeable
REM     models top out at 37.5 percent there, so the 60 percent threshold
REM     could not be met by construction. The request that set 60 percent
REM     assumed SIX checkpoints: cells 2/6, 3/6, 4/6, ceiling 78.1 percent.
REM     Result 074 section 24.3. The tool now withholds the D9 verdict unless
REM     exactly six checkpoints are given.
REM
REM   WHAT RUNS
REM     Two census calls on the same six checkpoints: held-out v2.8, then
REM     v2.9 (same 4,500 ids, rewritten text). All six are Muon x15 at 300M
REM     tokens with six different architectures. Seed pairs are left out on
REM     purpose - a seed flip is noise, not discrimination.
REM       d12_cla2_norecur_muon15  m100s8     d12_cla2_r20_muon15      m100s8
REM       d14_cla2_norecur_muon15  m100s10    d16_cla2_norecur_muon15  m100s12
REM       d16_cla2_r20_muon15      m100s12    d18_cla2_norecur_muon15  m100s14
REM
REM   READ IN THIS ORDER
REM     1. The D9 line and its verdict - it is a real verdict now (n is six).
REM     2. The pair table: read the relation-family CI column, not the
REM        discordant counts. Rule 56 - items share relation templates, so
REM        item-level McNemar overstates. The CI is printed per pair now.
REM     3. The relation table. Conditions and time order were below chance for
REM        all four models in the first census (074 section 24.6).
REM     4. The json keeps every model's chosen index (per_pick), which says
REM        which wrong option pulls the models - open question Q14.
REM
REM   OUTPUT  runs/census/stage1_heldout.v2.8_census.json and the v2.9 one,
REM           kept apart (the file name carries the version since 2026-09-10).
REM   COST    about 1.2h, no training.   PLAN: test_plan/P085 Stage10
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage10_census_six_ckpt --note "[1/2] census on held-out v2.8 with six checkpoints - the D9 threshold assumes six"
python scripts\runlog.py --name P085_stage10_census_six_ckpt -- python scripts\census_heldout_discrimination.py --heldout-version 2.8 --models d12_cla2_norecur_muon15=m100s8 d12_cla2_r20_muon15=m100s8 d14_cla2_norecur_muon15=m100s10 d16_cla2_norecur_muon15=m100s12 d16_cla2_r20_muon15=m100s12 d18_cla2_norecur_muon15=m100s14 --n 4500
if errorlevel 1 echo [WARN] census v2.8 failed - continuing

python scripts\runlog.py --name P085_stage10_census_six_ckpt --note "[2/2] census on held-out v2.9 with the same six checkpoints"
python scripts\runlog.py --name P085_stage10_census_six_ckpt -- python scripts\census_heldout_discrimination.py --heldout-version 2.9 --models d12_cla2_norecur_muon15=m100s8 d12_cla2_r20_muon15=m100s8 d14_cla2_norecur_muon15=m100s10 d16_cla2_norecur_muon15=m100s12 d16_cla2_r20_muon15=m100s12 d18_cla2_norecur_muon15=m100s14 --n 4500
if errorlevel 1 echo [WARN] census v2.9 failed - continuing

python scripts\runlog.py --name P085_stage10_census_six_ckpt --note "DONE. Read the D9 verdict, then the family CI column of the pair table (rule 56), then the relation table."

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
