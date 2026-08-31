@echo off
REM P078 stage 0  -  is the recursion gain spread out or concentrated.
REM   H1 capacity: every crop improves a little. Visits are a flat compute budget.
REM   H2 selectivity: a few crops improve a lot. Then we can spend visits per input.
REM   The mean cannot tell these apart. We need the per-crop distribution.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P078_stage0_visit_selectivity --note "[1/3] dump per-crop losses - cla1 body, R1 vs R2"
python scripts\runlog.py --name P078_stage0_visit_selectivity -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4 mC_cla1_ag4_r20 --match-train-repeat --dump-crops runs/logs/p078_cla1.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P078_stage0_visit_selectivity --note "[2/3] the cla2 body too - 058 s14 says the gain is body dependent"
python scripts\runlog.py --name P078_stage0_visit_selectivity -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 mC_cla2_ag4_r20 --match-train-repeat --dump-crops runs/logs/p078_cla2.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P078_stage0_visit_selectivity --note "[3/3] analysis - no torch, no GPU"
python scripts\runlog.py --name P078_stage0_visit_selectivity -- python scripts\diag_visit_selectivity.py --crops runs/logs/p078_cla1.json --base mC_cla1_ag4 --deep mC_cla1_ag4_r20
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P078_stage0_visit_selectivity -- python scripts\diag_visit_selectivity.py --crops runs/logs/p078_cla2.json --base mC_cla2_ag4 --deep mC_cla2_ag4_r20
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P078_stage0_visit_selectivity --note "READ IN THIS ORDER" "1. the mean gain must match what paired_eval printed. If not, the dump is wrong." "2. top 10 percent share. Uniform is 10 percent." "3. the difficulty-gain correlation." "4. the verdict. H2 opens per-input visit allocation, H1 closes it." "5. compare the two bodies. 058 s14 measured 1.61x more gain on cla2 -" "   if the SHAPE also differs, the mechanism is body dependent too."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
