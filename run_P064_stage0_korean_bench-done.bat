@echo off
REM =============================================================================
REM  P064 stage 0  -  do KLUE and KorQuAD see what val_loss sees?
REM                   (NO TRAINING, GPU eval only, roughly 20-40 minutes)
REM
REM  THE PROBLEM
REM    Every judgement in this repo rests on ONE number - val_loss on our own
REM    ko-en crop set. P037 asked whether that set itself distorts the ranking
REM    and got no answer. We have never measured these models with another ruler.
REM
REM  WHY NOT EM / F1
REM    Our models are 100M base LMs with no instruction tuning. Generative
REM    scoring returns almost zero for all of them, and zero cannot rank
REM    anything - the differences we are chasing are 0.008. The KorQuAD 2.0
REM    paper itself reports BERT-multilingual at F1 46.0 against human 85.7.
REM    So we score by LIKELIHOOD instead, which a base LM can legitimately do.
REM
REM  THE THREE TASKS
REM    korquad  gold-answer conditional CE, paired per item  - the sensitive one
REM    ynat     7-way topic, label likelihood argmax        chance 14.3 percent
REM    nli      3-way entailment, same                      chance 33.3 percent
REM
REM  WHY PAIRED MATTERS MORE THAN SAMPLE SIZE
REM    Result 049 measured SE 0.0011 to 0.0014 on paired full-val. Unpaired,
REM    100 items tells us nothing. Paired on the SAME 100 items, it tells us a
REM    lot. Item selection is seed 99 and every guid is printed to the log.
REM
REM  THE MODELS - the three REVIEW2 candidates plus the dense reference
REM    mC_wsd        current standard   tied g8, parent-init, KD
REM    mC_initonly   candidate B        tied g8, parent-init, NO KD
REM    mC_d36_ag4    candidate C        36 layers, attn-group 4, lowest residency
REM    p6d           dense reference    no tying at all
REM    mC_initonly_s2, mC_wsd_s2   seed repeats - these two pairs ARE the
REM                  sigma of this ruler. The external review of this design
REM                  never asked what the sigma was; result 049 says that is
REM                  the first question, not the last.
REM
REM  PREDICTIONS, fixed in advance
REM    P1  ynat and nli land near chance for every model. If so the tasks are
REM        too hard for this scale and only korquad CE is usable.
REM    P2  korquad CE ranks the four models in the SAME order as full-val.
REM    P3  if P2 fails, that is the interesting outcome, not a broken tool -
REM        it is the first evidence for P037's worry.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    Which model is BETTER. CE on a QA prompt is still a likelihood, not a
REM    capability. And this is a checkpoint comparison, not an architecture
REM    comparison - the same limit paired_eval carries.
REM    Do NOT compare korquad CE against val_loss numerically. Different
REM    distribution, different ruler (trap 1).
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P064_stage0_kobench --note "=============================================================================" "P064 stage 0   KLUE and KorQuAD likelihood scoring   NO TRAINING" "A second ruler for the three REVIEW2 candidates plus dense." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P064_stage0_kobench --note "[1/3] KorQuAD 1.0 - answer-token CE, 100 items, paired. THE SENSITIVE ONE."
python scripts\runlog.py --name P064_stage0_kobench -- python scripts\eval_korean_bench.py --task korquad --n 100 --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_initonly mC_d36_ag4 p6d mC_initonly_s2 mC_wsd_s2
if errorlevel 1 echo [WARN] korquad failed - continuing

echo.
python scripts\runlog.py --name P064_stage0_kobench --note "[2/3] KLUE YNAT - 7-way topic by label likelihood, 500 items. Chance is 14.3 percent."
python scripts\runlog.py --name P064_stage0_kobench -- python scripts\eval_korean_bench.py --task ynat --n 500 --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_initonly mC_d36_ag4 p6d mC_initonly_s2 mC_wsd_s2
if errorlevel 1 echo [WARN] ynat failed - continuing

echo.
python scripts\runlog.py --name P064_stage0_kobench --note "[3/3] KLUE NLI - 3-way entailment, 500 items. Chance is 33.3 percent."
python scripts\runlog.py --name P064_stage0_kobench -- python scripts\eval_korean_bench.py --task nli --n 500 --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_initonly mC_d36_ag4 p6d mC_initonly_s2 mC_wsd_s2
if errorlevel 1 echo [WARN] nli failed - continuing

echo.
echo.
python scripts\runlog.py --name P064_stage0_kobench --note "=============================================================================" "READ IN THIS ORDER" "0. the naming banner. These are AUXILIARY metrics, not official benchmark" "   scores. Official YNAT is macro F1, official NLI is accuracy." "1. the SKIPPED count per model. If many items were dropped for length," "   the sample is not what we designed and nothing below is comparable." "2. ynat and nli against chance. At or below chance means the task is out of" "   reach at this scale - say so and stop using it, do not tune the prompt." "3. korquad paired deltas with SD, SE, 95pct CI, t and REQUIRED N." "   If required N exceeds what we ran, this was a PILOT - measure again with a bigger --n." "4. the context-utilisation line. Near zero means this metric is measuring" "   lexical prior, not reading comprehension." "5. the seed-pair rows (initonly vs s2, wsd vs s2). THAT is this ruler sigma." "   Do not judge rank agreement before reading it." "6. does the korquad order match full-val (3.6776 3.6984 3.7062 3.7608)?" "   A mismatch is the RESULT, not a bug." "REMINDER  do not compare korquad CE with val_loss numerically." "=============================================================================="
   above the sample we ran, this was a PILOT and the real measurement"
   needs a bigger --n (external review s7 was right about this)." "4. does the korquad order match full-val (3.6776 3.6984 3.7062 3.7608)?" "   A mismatch is the RESULT, not a bug." "REMINDER  do not compare korquad CE with val_loss numerically." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
