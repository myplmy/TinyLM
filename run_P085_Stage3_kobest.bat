@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P085_Stage3_kobest.bat -- the Korean axis, which has been zero
REM ==========================================================================
REM
REM   WHY
REM     every benchmark we run is English - hellaswag, arc_easy, piqa - while
REM     the training corpus is ko-en. Nothing measures Korean at all. The
REM     held-out set was supposed to but it is blocked on two items with two
REM     correct answers. KoBEST has no prerequisite: the paper is in article/
REM     and the data is already under HF/datasets--skt--kobest_v1.
REM
REM   ONLY TWO OF THE FIVE TASKS
REM     KoBEST paper (arXiv:2204.04541) Table 4 gives KoGPT3-39B zero-shot,
REM     which is our exact setting - a base LM picking the lowest-perplexity
REM     candidate (their section 4.2.1, same procedure as our likelihood acc):
REM       KB-COPA       76.8   chance 50   gives real signal
REM       KB-HellaSwag  59.8   chance 25   gives real signal
REM       KB-SentiNeg   57.7   chance 50   gives weak, needs a verbalizer
REM       KB-WiC        34.7   chance 50   gives BELOW chance
REM       KB-BoolQ      33.1   chance 50   gives BELOW chance
REM     A 39B model falls below chance on two of them. An 81M model will not
REM     do better. We do not run tasks that cannot rank anything.
REM
REM   WHAT TO EXPECT
REM     accuracy will not separate these three models - test splits are 1000
REM     and 500 and result 074 measured that we need thousands. Read gold CE.
REM     Human performance is 98.1 and 92.4, so a large gap is normal.
REM
REM   CONTAMINATION
REM     KB-HellaSwag contexts come from Korean wikipedia and youtube, and
REM     Korean wikipedia is half of our pool. The overlap is NOT measured.
REM     Arm 1 fetches, arm 2 scores; treat a suspiciously good number as a
REM     contamination signal first (KorQuAD was 94.8 percent of our stream).
REM
REM   NO TRAINING. Download plus inference. COST: about 0.7h.
REM   PLAN: test_plan/P085 (Korean filename) section 3.3b, Stage3
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P085_stage3_kobest --note "[1/3] fetch the two KoBEST tasks into datasets/bench"
python scripts\runlog.py --name P085_stage3_kobest -- python scripts\fetch_bench_data.py --only kobest_copa kobest_hellaswag
if errorlevel 1 echo [WARN] fetch failed - the two arms below will say so

python scripts\runlog.py --name P085_stage3_kobest --note "[1b/3] overlap - KB-HellaSwag comes from Korean wikipedia, half our pool"
python scripts\runlog.py --name P085_stage3_kobest -- python scripts\diag_bench_overlap.py --task kobest_hellaswag --data ko-en --tokens 600M --sample 400 --k 12
if errorlevel 1 echo [WARN] overlap check reported contamination - read the rate first

python scripts\runlog.py --name P085_stage3_kobest --note "[2/3] KB-COPA - 1000 items, chance 50 percent"
python scripts\runlog.py --name P085_stage3_kobest -- python scripts\eval_bench_suite.py --task kobest_copa --n 5000 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] kobest_copa failed - continuing

python scripts\runlog.py --name P085_stage3_kobest --note "[3/3] KB-HellaSwag - 500 items, chance 25 percent"
python scripts\runlog.py --name P085_stage3_kobest -- python scripts\eval_bench_suite.py --task kobest_hellaswag --n 5000 --preset m100s8 --models d12_cla2_r20 d16_cla2_r20 mC_cla2_ag4_r20 --wandb
if errorlevel 1 echo [WARN] kobest_hellaswag failed - continuing

echo.
python scripts\runlog.py --name P085_stage3_kobest --note "=================================================================" "READ IN THIS ORDER" "1. the fetch arm printed row counts. They must be 1000 and 500." "   Anything else means the split was wrong and the scores are void." "2. chance level is printed BEFORE the results. Read it first." "3. gold CE, not accuracy. 1000 and 500 items cannot separate these" "   three models on argmax - result 074 measured that." "4. if any accuracy lands far above the 39B zero-shot number in the" "   paper (76.8 and 59.8), suspect contamination, not intelligence." "5. do NOT write F1 anywhere. The paper uses F1, we use likelihood" "   accuracy and gold CE. Different quantities, same-looking table." "================================================================="

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
