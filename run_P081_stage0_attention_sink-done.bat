@echo off
REM P081 stage 0  -  is there an attention sink in OUR model?  About 0.3 hours.
REM
REM   THE LAST OPEN KV AXIS.  KV = entries x tokens x bytes.
REM     entries : closed by result 062 (repeat-kv-reuse costs 5.4x its gain)
REM     bytes   : halved by result 065 (bf16, exactly 0.500, no argmax change)
REM     tokens  : this.  StreamingLLM (arXiv:2309.17453) keeps a few sink
REM               tokens plus a recent window and throws the middle away,
REM               which makes KV CONSTANT in context length instead of linear.
REM
REM   WHY IT TOOK THIS LONG.  SDPA does not hand back attention probabilities,
REM   and the Flash backend never materialises them.  Recomputing them from a
REM   hook would define RoPE, QK-norm, GQA expansion and the causal mask in a
REM   SECOND place (trap 18) - and if that copy drifted, the sink numbers would
REM   be silently wrong.  So the file sat as an exit-2 stub.
REM
REM   PRECONDITION NOW DONE (2026-08-31).  cfg.return_probs makes
REM   Attention.forward compute the probabilities from the q, k and mask it
REM   ALREADY BUILT.  It is read-only - the output tensor is still whatever
REM   SDPA produced - so logits stay bit identical with it on.  Training is
REM   blocked by an assert because the matrix is batch x heads x T x T.
REM   scripts/check_return_probs.py asserts all of that and now runs as
REM   smoke arm [20].
REM
REM   THE BASELINE MATTERS MORE THAN THE NUMBER.  Four tokens out of 1024 is
REM   0.39 percent if attention were uniform.  Ten percent would be 26 times
REM   that.  The tool prints the baseline next to every figure.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P081_stage0_attention_sink --note "[1/3] the budget candidate - cla2, 20 visits"
python scripts\runlog.py --name P081_stage0_attention_sink -- python scripts\diag_attention_sink.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 --seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P081_stage0_attention_sink --note "[2/3] the recursive arm - does a second pass over the same layer change it"
python scripts\runlog.py --name P081_stage0_attention_sink -- python scripts\diag_attention_sink.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20 --seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P081_stage0_attention_sink --note "[3/3] a dense body for contrast - tying and CLA are not in the way here"
python scripts\runlog.py --name P081_stage0_attention_sink -- python scripts\diag_attention_sink.py --preset m100s8 --data ko-en --tokens 300M --models d12_dense --seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P081_stage0_attention_sink --note "READ IN THIS ORDER" "1. the uniform baseline line at the top. Without it no mass figure means" "   anything - 4 of 1024 is 0.39 percent." "2. average sink mass against that baseline, as a multiple." "3. the sink-plus-window column. That is what StreamingLLM would KEEP." "   One minus it is what we would throw away." "4. the depth trend. The paper says deeper layers sink harder. If ours" "   does not, our sink is a different phenomenon and the paper's window" "   sizes do not transfer." "5. tied and dense should be compared carefully - CLA means fewer KV" "   owners, so the module count differs between arms." "6. mass is necessary, not sufficient. A 1 percent tail can still be" "   decisive. Cutting and measuring the loss is stage 1."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
