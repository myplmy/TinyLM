@echo off
REM =============================================================================
REM  P064 stage 0b  -  rerun the label tasks with PMI normalisation
REM                    (NO TRAINING, GPU eval, about 40 minutes)
REM
REM  WHAT WENT WRONG IN STAGE 0 (result 050 s3, s4)
REM    All six models scored exactly 32.2 percent on NLI and every per-item
REM    delta was exactly zero. 32.2 percent is the neutral label share in our
REM    500-item sample, so every model always picked the neutral label.
REM    Cause: we length-normalised, and a LONG label wins under mean log
REM    likelihood because its later tokens are almost free to predict. The
REM    external review warned about the OPPOSITE bias (sum favours short
REM    labels) and we over-corrected.
REM
REM  THE FIX
REM    Score by CE(label given context) minus CE(label given no context). That removes
REM    the label's own prior. The no-context term is the same computation we
REM    already built for the KorQuAD context-utilisation control, so it cost
REM    about fifteen lines.
REM    Also added: a degeneracy warning that fires when one label takes 90
REM    percent or more of the picks. Stage 0 printed a clean table while every
REM    model was degenerate - the tool should have caught that itself.
REM
REM  PREDICTIONS, fixed in advance
REM    N1  the pick distribution is no longer one label. If it still is, PMI
REM        is not the cause and the prompt itself is the problem.
REM    N2  NLI accuracy moves off 32.2 and the models SEPARATE.
REM    N3  YNAT changes too - it was less biased (labels are 2 to 4 chars) but
REM        not unbiased. Expect a few points of movement.
REM    N4  the seed pairs still differ by 3 to 5 points. PMI fixes the bias,
REM        not the variance - and result 050 s2.2 said variance is what blocks
REM        the ranking claim.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Whether YNAT rank disagrees with full-val. That needs more SEEDS, not a
REM    better estimator (result 050 s2.2). This only removes a known bias.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P064_stage0b_pmi --note "=============================================================================" "P064 stage 0b   label tasks with PMI normalisation   NO TRAINING" "Stage 0: six models, one number, zero deltas. The tool was biased." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P064_stage0b_pmi --note "[1/2] KLUE NLI with PMI. Chance 33.3 percent. Watch the pick distribution."
python scripts\runlog.py --name P064_stage0b_pmi -- python scripts\eval_korean_bench.py --task nli --n 500 --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_initonly mC_d36_ag4_nokd p6d mC_initonly_s2 mC_wsd_s2
if errorlevel 1 echo [WARN] nli failed - continuing

echo.
python scripts\runlog.py --name P064_stage0b_pmi --note "[2/2] KLUE YNAT with PMI. Chance 14.3 percent. Stage 0 gave 30.4 to 39.4."
python scripts\runlog.py --name P064_stage0b_pmi -- python scripts\eval_korean_bench.py --task ynat --n 500 --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_initonly mC_d36_ag4_nokd p6d mC_initonly_s2 mC_wsd_s2
if errorlevel 1 echo [WARN] ynat failed - continuing

echo.
echo.
python scripts\runlog.py --name P064_stage0b_pmi --note "=============================================================================" "READ IN THIS ORDER" "1. the pick distribution line for every model. If one label is still at 90" "   percent the tool prints a degeneracy warning - stop and read nothing else." "2. NLI accuracy. Stage 0 gave 32.2 for all six. Any spread is progress." "3. the seed pairs (initonly vs s2, wsd vs s2). THAT is the noise floor of" "   this ruler. Model gaps smaller than it cannot be read." "4. YNAT against stage 0 (34.2 / 36.0 / 30.4 / 39.4 / 39.0 / 39.2)." "REMINDER  PMI removes a BIAS. It does not reduce VARIANCE. Ranking claims" "          still need more seeds, not more items (result 050 s2.2)." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
