@echo off
REM ===== P029 : qualitative probe - what does val 3.70 actually generate? =====
REM   Plan: test_plan\P029  ***READ THE EXPECTATION SECTION FIRST***
REM
REM WHY: every model so far was judged by val cross-entropy alone. That is fine for comparing
REM   architecture A vs B, but we have never LOOKED at what these models produce.
REM   Cheapest possible sanity check before any real downstream benchmark.
REM
REM WHY A PYTHON DRIVER AND NOT PROMPTS IN THIS FILE
REM   .bat must be pure ASCII (Korean breaks under the cmd code page, and forcing the page
REM   then breaks Python output). The prompts must be Korean, so they live in
REM   scripts\probe_prompts.py
REM   which is UTF-8 Python. Bonus: the model is loaded ONCE per model instead of once per
REM   prompt, which is what a pure-batch version would have done 15 times.
REM
REM ***** CALIBRATE EXPECTATIONS BEFORE READING THE OUTPUT *****
REM   132M ternary params on 300M tokens = about 2.3 tokens per parameter.
REM   Chinchilla suggests ~20. GPT-2 (124M) saw 40B tokens, roughly 130x more.
REM   No instruction tuning either, so it cannot answer questions or follow orders.
REM
REM   DO NOT EXPECT: correct facts, dates, numbers, multi-sentence reasoning, Q and A.
REM   DO EXPECT (this is what we check): plausible Korean particles and endings,
REM     script consistency, wiki-style inertia, local grammar, no repetition loop.
REM
REM MODELS: mA_g4s34_k4 (11.7MB, result 012 says INDISTINGUISHABLE from dense)
REM         vs p6d (dense, 30.9MB) on the same prompts, to see the compression cost by eye.
REM
REM COST: inference only, a few minutes. Writes nothing to runs\.
REM NOTE: generate has no KV cache (recomputes the full sequence each step). Do NOT time it.

echo ============================================================
echo [P029] qualitative probe
echo ============================================================
echo.
echo [0] prompts and what each one checks
python scripts\probe_prompts.py --list
if errorlevel 1 echo [WARN] listing failed - continuing

echo.
echo [1/1] generating (mA_g4s34_k4 and p6d, temps 0.7 and 1.0)
python scripts\probe_prompts.py
if errorlevel 1 echo [WARN] probe failed - see the traceback above

echo.
echo ================================================================
echo The checklist is printed at the end of the python output. Fill it in BY EYE.
echo.
echo   all boxes empty              -^> suspect the pipeline, not the model
echo   boxes filled but facts wrong -^> NORMAL for 2.3 tokens per parameter
echo   mA visibly worse than p6d    -^> first qualitative sign of the compression cost,
echo                                   but 5 prompts is an impression, not a measurement
echo.
echo Sampling is stochastic - re-run to see the spread before concluding anything.
echo This probe does NOT choose an architecture. REVIEW1 and val_loss do that.
echo ================================================================
echo done.
pause
