@echo off
REM P078 stage 1  -  does the SAME crop gain again?  About 0.3 hours, no training.
REM
REM   Stage 0 printed H2 for the cla1 body (top-10 percent share 30.2) and
REM   "undecided" for cla2 (28.6), with the threshold at 30.0.  The threshold
REM   made that call, not the data.  And the difficulty deciles were flat in
REM   both bodies: base loss spreads 2.74 to 4.42 while the gain moves inside
REM   1.31 to 1.34, correlation -0.028 and +0.037.  So the one predictor we
REM   have at inference time - difficulty - does not work.
REM
REM   A free follow-up already answered part of it.  Correlating the two
REM   bodies' per-crop gain vectors gives r = +0.082, r squared 0.7 percent.
REM   Statistically nonzero at 3.1 sigma, practically nothing.
REM
REM   THAT COMPARISON CROSSED BODIES.  This batch does the clean one: the SAME
REM   body, two seeds.  mC_cla1_ag4_r20_s2 (seed 2024) already exists.
REM
REM   READ THE UPPER BOUND HONESTLY.  Both gain vectors share the same base
REM   checkpoint (there is only one mC_cla1_ag4), so the base's own crop
REM   variance appears identically in both and INFLATES r.  Whatever comes out
REM   is therefore an UPPER BOUND on replication.  If even that is small, H2
REM   has no usable predictor and stage 2 does not open.
REM
REM   The accidental cla2 seed pair from P052 stage 4 gives a second, cleaner
REM   look: mC_cla1_ag4_r20_s3 is really a cla2_r20 at seed 777 (result 039
REM   s11), so it pairs against mC_cla2_ag4_r20 on a shared cla2 base.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P078_stage1_seed_replication --note "[1/3] crops - cla1 base plus BOTH recursion seeds"
python scripts\runlog.py --name P078_stage1_seed_replication -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4 mC_cla1_ag4_r20 mC_cla1_ag4_r20_s2 --match-train-repeat --dump-crops runs/logs/p078_cla1_seeds.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P078_stage1_seed_replication --note "[2/3] crops - cla2 base plus its two seeds (s3 is really a cla2 arm, result 039 s11)"
python scripts\runlog.py --name P078_stage1_seed_replication -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 mC_cla2_ag4_r20 mC_cla1_ag4_r20_s3 --match-train-repeat --dump-crops runs/logs/p078_cla2_seeds.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P078_stage1_seed_replication --note "[3/3] the gate - do the same crops gain in both seeds"
python scripts\runlog.py --name P078_stage1_seed_replication -- python scripts\paired_join.py --crops runs/logs/p078_cla1_seeds.json runs/logs/p078_cla2_seeds.json --corr mC_cla1_ag4-mC_cla1_ag4_r20:mC_cla1_ag4-mC_cla1_ag4_r20_s2 mC_cla2_ag4-mC_cla2_ag4_r20:mC_cla2_ag4-mC_cla1_ag4_r20_s3 --pairs mC_cla1_ag4_r20:mC_cla1_ag4_r20_s2 mC_cla2_ag4_r20:mC_cla1_ag4_r20_s3
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P078_stage1_seed_replication --note "READ IN THIS ORDER" "1. the two correlations. Under 0.10 closes per-input visit allocation." "2. remember both are UPPER BOUNDS - the shared base inflates them." "3. the two --pairs lines are seed pairs. They also give a second reading" "   of the recursion ruler on each body (cla1 had 0.0006, cla2 had 0.0016)." "4. r squared, not r. 3.1 sigma on 1464 crops means almost nothing about" "   whether the effect is usable." "5. this does NOT test whether recursion helps. It tests whether the help" "   lands on predictable inputs."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
