@echo off
REM P077 stage 1c  -  the KV value range that decides fp16, plus three retries
REM of tools fixed today.  About 0.7 hours.  No training.
REM
REM   THE FP16 QUESTION.  Result 065 s8 measured fp16 at 2.35e-03 against
REM   bf16 at 1.56e-02 - same two bytes, 6.5x more accurate, argmax mismatch
REM   zero in both, and the MiB accounting identical.  On precision alone
REM   fp16 wins outright.
REM
REM   WHAT STOPS US.  fp16 tops out at 65,504 while bf16 reaches 3.4e38.  We
REM   have never measured max abs K or max abs V, so we do not know the
REM   headroom.  An overflow becomes inf then nan and it is SILENT.
REM   diag_kvcache now prints the range and grades the headroom:
REM     under 100x   :  do not use fp16
REM     100 to 1000x :  possible, re-measure when data or length changes
REM     over 1000x   :  the exponent range is not the problem
REM
REM   THE OTHER THREE STEPS are retries of tools fixed today:
REM     diag_decode_profile  passed the path name 'fp32' as an embedding
REM                          quantisation format.  Both arms died on load.
REM     diag_group_agg       measured zero MLP tensors and printed a verdict
REM                          about attention instead.  P076 asks about MLP.
REM     diag_attention_sink  said "no sink" when it meant "sink too small to
REM                          use", and never printed the discarded mass.
REM
REM   INDEPENDENT VARIABLE: none.  Measurement and retries.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries --note "[1/6] KV value range on the budget candidates - fp16 gate"
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_kvcache.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 mC_cla2_ag4_r20 --kv-dtype fp16 --max-new 24
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries --note "[2/6] the same on the thin winners - a different body may hold different values"
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_kvcache.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_dense --kv-dtype fp16 --max-new 24
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_kvcache.py --preset m100s12 --data ko-en --tokens 300M --models d16_cla2_r20 --kv-dtype fp16 --max-new 24
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries --note "[3/6] a longer decode - the range must be read at the length we deploy"
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_kvcache.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 --kv-dtype fp16 --max-new 96
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries --note "[4/6] P014D retry - emb_quant None, not the string fp32"
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_decode_profile.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 --max-new 32
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_decode_profile.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20 --max-new 32
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries --note "[5/6] P076 retry - MLP tensors are under mid_mlps, not layers.N"
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_group_agg.py --preset m100R1c --data ko-en --tokens 300M --tag dense
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_group_agg.py --preset m100R1c --data ko-en --tokens 300M --tag dense --group 4
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries --note "[6/6] P081 window sweep - how much mass a bigger window buys back"
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_attention_sink.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_dense --seq 1024 --window 128
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_attention_sink.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_dense --seq 1024 --window 512
if errorlevel 1 echo [WARN] step failed - continuing
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries -- python scripts\diag_attention_sink.py --preset m100s8 --data ko-en --tokens 300M --models d12_cla2_r20 d12_dense --seq 1024 --window 768
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P077_stage1c_kv_range_and_retries --note "READ IN THIS ORDER" "1. the KV range lines in steps 1 to 3.  That single headroom multiple" "   decides whether fp16 becomes the deployment default.  Under 100x and" "   the axis closes; the 6.5x precision win is not worth a silent nan." "2. step 3 against step 2.  If headroom shrinks with decode length, the" "   number to quote is the long one." "3. step 5 must now show mlp rows.  Zero mlp rows is an exit 1 and the" "   fix did not land." "4. step 6 as a curve: window 128 / 256 / 512 / 768 against discarded" "   mass.  Result 070 measured 16.3 to 20.1 percent discarded at 256." "   If 512 does not cut that roughly in half, the tail is flat and" "   StreamingLLM has nothing to offer here." "5. step 4 gives the unpack share.  30 to 42 percent is currently a" "   DERIVED number, not a measurement.  This is the measurement." "6. none of this is a quality result.  Teacher-forced evaluation does" "   not use the cache the way generation does."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
