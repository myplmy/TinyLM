@echo off
REM P080 stage 0b  -  the overlap check that never ran, plus the new gate.
REM   About 0.2 hours, no GPU, no training.
REM
REM   TWO THINGS WENT WRONG IN STAGE 0.
REM
REM   1. The tool printed "no tokenizer length bias" and exited 0 while the
REM      same output carried 156/41/73/30 for the correct answer's token
REM      length rank (uniform is 75 each).  A shortest-first selector scores
REM      52.0 percent against a 25 percent chance and a 2.5 point sigma -
REM      that is plus 10.8 sigma.  v2.2 was 46.7, so the v2.3 rewrite made the
REM      token axis WORSE while fixing the character axis.
REM      diag_bench_tokens.py now has a trivial-selector gate and a real exit
REM      code.  Verified on four synthetic sets: uniform 25.0, all-tied 25.0,
REM      answer-always-shortest 100.0, and the 068 pattern 52.0.
REM
REM   2. diag_common_text died because the batch invented a tokenizer path.
REM      The real one is data_cache\tok-ko-en-32768.json, and the last
REM      successful run of that tool (log 060, 2026-08-29) used exactly it.
REM      So the verbatim-overlap check - the one that caught KorQuAD at 94.8
REM      percent of our training stream - has still never run on this
REM      benchmark.
REM
REM   EXPECT THE GATE TO FAIL.  Step 1 should exit 1 now.  That is the tool
REM   working, not the tool breaking.  What we need from this run is the
REM   overlap number and a re-print of the trivial-selector figures for the
REM   result document.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P080_stage0b_overlap_and_gate --note "[1/3] v2.3 through the new trivial-selector gate - exit 1 is EXPECTED"
python scripts\runlog.py --name P080_stage0b_overlap_and_gate -- python scripts\diag_bench_tokens.py --bench datasets/TinyDataset/stage1_dataset/held-out_v2.3/stage1_heldout_benchmark_v2.3_300.json --data ko-en --tokens 300M
if errorlevel 1 echo [WARN] gate reported failure - that is the point, read the numbers
echo.
python scripts\runlog.py --name P080_stage0b_overlap_and_gate --note "[2/3] v2.2 for the same reading"
python scripts\runlog.py --name P080_stage0b_overlap_and_gate -- python scripts\diag_bench_tokens.py --bench datasets/TinyDataset/stage1_dataset/held-out_v2.2/stage1_heldout_benchmark_v2.2_300.json --data ko-en --tokens 300M
if errorlevel 1 echo [WARN] gate reported failure - that is the point, read the numbers
echo.
python scripts\runlog.py --name P080_stage0b_overlap_and_gate --note "[3/3] verbatim overlap with the training stream - correct tokenizer path this time"
python scripts\runlog.py --name P080_stage0b_overlap_and_gate -- python scripts\diag_common_text.py --cache data_cache\ko-en_600000000 --tok data_cache\tok-ko-en-32768.json --jsonl datasets/TinyDataset/stage1_dataset/held-out_v2.3/stage1_heldout_benchmark_v2.3_300.json:candidates --max-docs 300
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P080_stage0b_overlap_and_gate --note "READ IN THIS ORDER" "1. step 3 first, the overlap percentage. Over 10 percent and the benchmark" "   is contaminated and nothing else matters (the result 060 rule)." "2. then the trivial-selector block in steps 1 and 2. The shortest-first" "   accuracy IS the floor for any score on this benchmark." "3. v2.2 against v2.3 on that number. If v2.3 is worse, the character-length" "   rewrite moved the bias into token space rather than removing it." "4. the zero-frequency and bottom 0.1 percent rows should both be 0 of 300." "   Those passed in stage 0 and closing that axis is a real result." "5. do NOT edit the benchmark files. Another model owns that folder." "   What comes out of here is a specification for v2.4, not an edit."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
