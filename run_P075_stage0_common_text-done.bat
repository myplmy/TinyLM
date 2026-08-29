@echo off
REM =============================================================================
REM  P075 stage 0  -  is the common text contaminated by our training pool
REM                   no training. about 30 minutes. GPU not required.
REM
REM  WHY  (handoff Q5, plan P075 section 2.1, user instruction 9)
REM    Result 053 s1.7 judged tokenizers and teachers on SQuAD v2 context bpb.
REM    Nobody checked whether that text is inside ko-en. The pool is Korean
REM    Wikipedia plus fineweb-edu, and fineweb-edu is an education classifier that
REM    prefers Wikipedia. SQuAD is English Wikipedia, KorQuAD is Korean Wikipedia.
REM    Both have a reason to overlap.
REM
REM  WHAT IT DOES
REM    O1  token 13-gram hashes of each candidate against the whole train.bin
REM    O2  a control taken from train.bin itself - must come back near 100 percent
REM    O3  sample size after dropping contaminated documents
REM
REM  PREDICTIONS
REM    P1  the O2 control is above 95 percent. If not the tool is broken and O1
REM        means nothing. This gate comes first.
REM    P2  KorQuAD 1.0 has the highest hit rate - Korean Wikipedia, and the pool
REM        is 24.3 percent Korean Wikipedia.
REM    P3  KLUE-MRC is the cleanest Korean candidate - news, not wiki.
REM    P4  SQuAD v2 is above 1 percent on a meaningful share of documents. If it
REM        is clean, result 053 s1.7 stands as measured.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P075_stage0_common_text --note "=============================================================================" "P075 stage 0   common text contamination" "The bpb ruler of result 053 has never been checked against the training pool." "No training. The O2 control decides whether O1 can be believed." "=============================================================================="

echo.
python scripts\runlog.py --name P075_stage0_common_text --note "[1/2] all three candidates plus the O2 control, in one pass"
python scripts\runlog.py --name P075_stage0_common_text -- python scripts\diag_common_text.py --cache data_cache\ko-en_600000000 --tok data_cache\tok-ko-en-32768.json --squad datasets\squad\dev-v2.0.json --korquad datasets\KorQuad\KorQuAD_2.1\KorQuAD_v1.0_dev.json --klue-mrc datasets\KLUE\klue_benchmark\klue-mrc-v1.1\klue-mrc-v1.1_dev.json --max-docs 4000
if errorlevel 1 echo [WARN] step 1 failed - continuing

echo.
python scripts\runlog.py --name P075_stage0_common_text --note "[2/2] the same against the KorQuAD train split - a larger sample"
python scripts\runlog.py --name P075_stage0_common_text -- python scripts\diag_common_text.py --cache data_cache\ko-en_600000000 --tok data_cache\tok-ko-en-32768.json --korquad datasets\KorQuad\KorQuAD_2.1\KorQuAD_v1.0_train.json --max-docs 4000
if errorlevel 1 echo [WARN] step 2 failed - continuing

echo.
python scripts\runlog.py --name P075_stage0_common_text --note "=============================================================================" "READ IN THIS ORDER" "1. the O2 control. Above 95 percent or stop reading." "2. per-candidate drop rate. Over 10 percent means that corpus cannot be the" "   common text without filtering." "3. O3 - after dropping, is each decile still above 100 documents." "4. if SQuAD v2 is contaminated, result 053 s1.7.2 and s1.7.4 are measuring" "   memorisation and the tokenizer ranking there is not a ranking." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
