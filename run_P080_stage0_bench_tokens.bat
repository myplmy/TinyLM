@echo off
REM P080 stage 0  -  can the low-density dataset be used as a benchmark.
REM
REM   v2.3 balanced CHARACTER length (trivial strategies max 27.0 percent,
REM   0.8 sigma from chance). But the model does not read characters, it reads
REM   TOKENS, and a forced-choice scorer using log likelihood is sensitive to
REM   token count directly.
REM
REM   Second question: were those tokens seen enough during training
REM   (Fishing for Magikarp, arXiv 2405.05417).
REM
REM   NOTE.  We do NOT use the embedding-norm heuristic. Result 025 measured
REM   the sign reversal in our tied-head model: unused tokens have LARGER
REM   norms (0.8315 vs 0.5201, ratio 1.599). We count frequency directly.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P080_stage0_bench_tokens --note "[1/3] token-level audit of held-out v2.3"
python scripts\runlog.py --name P080_stage0_bench_tokens -- python scripts\diag_bench_tokens.py --bench datasets/TinyDataset/stage1_dataset/held-out_v2.3/stage1_heldout_benchmark_v2.3_300.json --data ko-en --tokens 300M
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P080_stage0_bench_tokens --note "[2/3] the same for v2.2, to see whether v2.3 changed token balance too"
python scripts\runlog.py --name P080_stage0_bench_tokens -- python scripts\diag_bench_tokens.py --bench datasets/TinyDataset/stage1_dataset/held-out_v2.2/stage1_heldout_benchmark_v2.2_300.json --data ko-en --tokens 300M
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P080_stage0_bench_tokens --note "[3/3] verbatim overlap with the training stream - the result 060 check"
python scripts\runlog.py --name P080_stage0_bench_tokens -- python scripts\diag_common_text.py --cache data_cache\ko-en_600000000 --tok data_cache\ko-en_600000000\tokenizer.json --jsonl datasets/TinyDataset/stage1_dataset/held-out_v2.3/stage1_heldout_benchmark_v2.3_300.json:candidates --max-docs 300
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P080_stage0_bench_tokens --note "READ IN THIS ORDER" "1. token length ratio median. Character length was balanced; token length" "   may not be. 0.95 to 1.05 passes." "2. the correct answer's token-length rank distribution. Uniform is 75 each." "3. items using bottom 0.1 percent tokens. Under 5 percent passes, over 15" "   percent means those items become a separate slice." "4. items using zero-frequency tokens. This must be 0." "5. step 3 overlap. Over 10 percent and the benchmark is contaminated" "   (result 060 rule)." "6. v2.2 versus v2.3 in step 2. If token balance is identical, then the v2.3" "   rewrite fixed characters only and this axis was never touched."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
