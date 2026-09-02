@echo off
REM P080 stage 0c  -  measure v2.4 ourselves, and run the overlap audit that
REM has now failed twice.  About 0.3 hours.  No training.
REM
REM   WHY.  Result 068 s9 retracted the 52.0 percent figure - it was a
REM   competition-rank table read as an accuracy.  The tie-aware gate says
REM   v2.3 is 30.3 percent shortest, z +2.1, which PASSES.  The dataset team
REM   then built v2.4 on top of the wrong number and reports 26.9 percent.
REM   That number came from our tool but was run by them.  We measure it here.
REM
REM   THE OVERLAP AUDIT HAS NEVER RUN.  Stage 0 gave a tokenizer path that did
REM   not exist.  Stage 0b fixed the path and died on the file format - the
REM   loader assumed JSONL and the benchmark is a pretty-printed records
REM   object.  Behind that sat a second defect: candidates is a LIST and the
REM   loader only accepted str, so a successful parse would have reported
REM   zero documents and 0.0 percent contamination.  Both are fixed and the
REM   loader now exits 2 on zero documents.
REM
REM   AND THE SQuAD SPLIT IS WRONG.  common_bpb.py reads
REM   datasets/squad/train-v2.0.json but the P075 audit measured dev-v2.0.
REM   The 12 percent overlap figure does not apply to the corpus we actually
REM   score on.  Step 4 audits the real one.
REM
REM   INDEPENDENT VARIABLE: none.  This is measurement, not an experiment.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P080_stage0c_v24_and_overlap --note "[1/4] v2.4 through our own gate - the number we will quote"
python scripts\runlog.py --name P080_stage0c_v24_and_overlap -- python scripts\diag_bench_tokens.py --bench datasets/TinyDataset/stage1_dataset/held-out_v2.4/stage1_heldout_benchmark_v2.4_300.json --data ko-en --tokens 300M
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P080_stage0c_v24_and_overlap --note "[2/4] v2.3 again on the same run - the two must be read side by side"
python scripts\runlog.py --name P080_stage0c_v24_and_overlap -- python scripts\diag_bench_tokens.py --bench datasets/TinyDataset/stage1_dataset/held-out_v2.3/stage1_heldout_benchmark_v2.3_300.json --data ko-en --tokens 300M
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P080_stage0c_v24_and_overlap --note "[3/4] overlap - the fixed loader, third attempt"
python scripts\runlog.py --name P080_stage0c_v24_and_overlap -- python scripts\diag_common_text.py --cache data_cache\ko-en_600000000 --tok data_cache\tok-ko-en-32768.json --jsonl datasets/TinyDataset/stage1_dataset/held-out_v2.4/stage1_heldout_benchmark_v2.4_300.json:candidates datasets/TinyDataset/stage1_dataset/held-out_v2.3/stage1_heldout_benchmark_v2.3_300.json:candidates --max-docs 300
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P080_stage0c_v24_and_overlap --note "[4/4] SQuAD train-v2.0 - the split common_bpb actually scores on"
python scripts\runlog.py --name P080_stage0c_v24_and_overlap -- python scripts\diag_common_text.py --cache data_cache\ko-en_600000000 --tok data_cache\tok-ko-en-32768.json --squad datasets\squad\train-v2.0.json --max-docs 4000
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P080_stage0c_v24_and_overlap --note "READ IN THIS ORDER" "1. step 3 and 4 first.  The O2 control hit rate must be near 100 percent." "   Under 50 and the tool is broken and nothing else in the log counts." "2. step 4 gives the overlap of the corpus common_bpb really uses.  If it" "   is far from the 12 percent measured on dev, every cross-tokenizer bpb" "   number in the repo needs a caveat and methods 03 must be corrected." "3. THEN the trivial selectors in steps 1 and 2.  Token axis decides -" "   the model sees tokens, not characters." "4. v2.4 should read about 26.9 percent shortest and v2.3 about 30.3." "   If our numbers differ from the team's by more than a point, the two" "   sides are not running the same tokenizer and that comes first." "5. do NOT promote v2.4 on this log alone.  The semantic check - do the" "   720 edited distractors still violate their forbidden relation - is a" "   human read of v2.4_changes.json and no tool replaces it."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
