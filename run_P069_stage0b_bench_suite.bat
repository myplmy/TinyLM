@echo off
REM =============================================================================
REM  P069 stage 0b  -  run every benchmark the user asked for. No training.
REM                    about 1.5 hours for the likelihood tasks, plus 1 hour if
REM                    you enable the generation tasks at the bottom.
REM
REM  WHY EVERY TASK AND NOT THE THREE I RECOMMENDED
REM    2026-08-22 user instruction: implement all of them regardless of the
REM    expected result. I had rejected IFEval, GSM8K, HE+, BFCLv3, MuSR and
REM    MMLU-Redux in 10_benchmarks s3.2 on the grounds that they would score
REM    zero. That is a prediction, not a reason to not measure. A prediction you
REM    never test stays true forever. Section 6.5 records the retraction.
REM
REM  !! PREREQUISITE - DATA
REM    python scripts\fetch_bench_data.py --all
REM    Needs network. Some sets are behind an HF licence gate; a failure there
REM    is a RESULT, not a bug. Write the reason down.
REM    python scripts\fetch_bench_data.py --verify   checks row counts against
REM    the official sizes. A mismatch means the wrong split, and a wrong split
REM    cannot be compared to anybody else's number.
REM
REM  TWO CORRECTIONS THAT ONLY CAME FROM READING THE PAPERS (stage 0a-2)
REM    BoolQ  the success floor is the MAJORITY BASELINE 62 percent, not 50.
REM           arXiv:1905.10044. At 50 a model that always answers yes scores 62
REM           and we would read that as ability. Trap 34 exactly.
REM    MuSR   the narratives are about 1000 WORDS. arXiv:2310.16049. At seq 1024
REM           tokens most items will be dropped for length, so a low N there
REM           measures our sequence limit, not the model.
REM
REM  WHAT THE NUMBERS CAN AND CANNOT DO
REM    Result 050 settled this: the bottleneck is not item count, it is TRAINING
REM    SEED. YNAT seed-pair spread was 3 to 5 points against a 9 point model gap.
REM    So: do NOT rank models on these. Ask only whether the direction disagrees
REM    with our val loss. That is answerable with the seeds we have.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P069_stage0b_bench --note "=============================================================================" "P069 stage 0b   every benchmark, no training" "Chance level is printed BEFORE each result. BoolQ floor is 62 not 50." "Do NOT rank models on these - result 050 showed seed noise dominates." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P069_stage0b_bench --note "[0] verify the data first - a wrong split is worse than no data"
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\fetch_bench_data.py --verify
if errorlevel 1 echo [WARN] some sets are missing - those tasks will report no_data and continue

echo.
python scripts\runlog.py --name P069_stage0b_bench --note "[1] LAMBADA first - the purest LM task we have. Accuracy AND perplexity."
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task lambada --n 500 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] lambada failed - continuing

echo.
python scripts\runlog.py --name P069_stage0b_bench --note "[2] likelihood scored multiple choice, 20 layer models"
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task hellaswag --n 300 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] hellaswag failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task piqa --n 300 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] piqa failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task arc_easy --n 300 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] arc_easy failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task arc_challenge --n 300 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] arc_challenge failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task winogrande --n 300 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] winogrande failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task boolq --n 300 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] boolq failed - continuing

echo.
python scripts\runlog.py --name P069_stage0b_bench --note "[3] knowledge and reasoning - chance is the prediction, confirming it is the result"
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task mmlu --n 300 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] mmlu failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task mmlu_redux --n 300 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] mmlu_redux failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task musr --n 250 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] musr failed - continuing

echo.
python scripts\runlog.py --name P069_stage0b_bench --note "[4] the standard model, 36 layers - a different preset so a separate call"
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task lambada --n 500 --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_nokd --wandb
if errorlevel 1 echo [WARN] d36 lambada failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task hellaswag --n 300 --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_nokd --wandb
if errorlevel 1 echo [WARN] d36 hellaswag failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task piqa --n 300 --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_nokd --wandb
if errorlevel 1 echo [WARN] d36 piqa failed - continuing

echo.
python scripts\runlog.py --name P069_stage0b_bench --note "[5] generation tasks. Expected near zero. We measure anyway - that is the point."
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task gsm8k --n 100 --max-new 128 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly mC_r20_nokd --wandb
if errorlevel 1 echo [WARN] gsm8k failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task ifeval --n 100 --max-new 192 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly --wandb
if errorlevel 1 echo [WARN] ifeval failed - continuing

echo.
python scripts\runlog.py --name P069_stage0b_bench --note "[6] code and tool use - we GENERATE and SAVE. We do not execute model output."
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task humaneval --n 164 --max-new 192 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly --out-jsonl smoketest_logs\gen_humaneval.jsonl --wandb
if errorlevel 1 echo [WARN] humaneval failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task humaneval_plus --n 164 --max-new 192 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly --out-jsonl smoketest_logs\gen_humanevalplus.jsonl --wandb
if errorlevel 1 echo [WARN] humaneval_plus failed - continuing
python scripts\runlog.py --name P069_stage0b_bench -- python scripts\eval_bench_suite.py --task bfcl_v3 --n 100 --max-new 128 --preset m100R1c --data ko-en --tokens 300M --models mC_initonly --out-jsonl smoketest_logs\gen_bfcl.jsonl --wandb
if errorlevel 1 echo [WARN] bfcl_v3 failed - continuing

echo.
python scripts\runlog.py --name P069_stage0b_bench --note "=============================================================================" "READ IN THIS ORDER" "1. the chance level printed above each result. Compare against THAT, not 0." "   BoolQ is 62 percent, not 50." "2. the degeneracy line. If one option is picked over 90 percent of the time" "   the accuracy is a bias, not an ability." "3. the excluded count. MuSR will exclude most items - about 1000 word" "   narratives against a 1024 token limit. That measures our seq, not the model." "4. gold CE and its required N. If required N is above the items we ran, the" "   delta cannot rank anything. KorQuAD needed 244040." "5. pass@1 is NOT here for humaneval. Generated code was saved, not executed." "   Score it with the official evalplus harness if you want pass@1." "!! DO NOT RANK MODELS ON THESE. Result 050: seed noise 3-5 points versus a" "   9 point model gap. Ask only whether the DIRECTION disagrees with val." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
