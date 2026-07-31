@echo off
REM ===== LOGGING (added 2026-07-31) =====
REM   Every python command below is run through scripts\runlog.py, which prints to the
REM   console in real time AND appends to test_result\log_YYYYMMDD_NAME.txt line by line,
REM   flushing and fsync-ing as it goes. If this batch dies halfway, or the machine loses
REM   power, everything up to the last couple of seconds is already on disk.
REM   Losing the log of a long run costs the whole run, so this is not optional.
REM   Exit codes pass through unchanged, so every `if errorlevel` below still works.

REM ===== relocated to scripts\batch on 2026-07-31 =====
REM   Root now holds only batches for experiments that have NOT run yet. This one is a
REM   REUSABLE tool or a completed run kept for re-verification, so it lives here.
REM   It works from EITHER location: launched from the repo root, or double-clicked here.
REM   No percent-expansion is used (this repo bans the percent sign in .bat files), so the
REM   working directory is fixed by looking for a marker file instead.
if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ===== P030 stage 1.5-B : the REAL cache gate - teacher-forced logit equivalence =====
REM   Plan: test_plan\P030 (stage 1.5)    Evidence: test_result\014 section 8
REM
REM ***** WHY THE OLD GATE HAD TO BE REPLACED *****
REM   P030 stage 1 asked for one thing: the LOGITS must agree with and without the cache.
REM   check_cache_equivalence implemented that as "the DECODED STRINGS must be identical".
REM   That substitution is not safe. It passes the comparison through
REM     (a) bf16 autocast on cuda,
REM     (b) 24 steps of autoregressive feedback, where one argmax flip changes everything
REM         after it, and
REM     (c) the tokenizer decode.
REM   So the old gate measures "did greedy decoding happen to agree", which is a different
REM   quantity from the invariant we care about. This is the SECOND time in this project
REM   that a measurement was not measuring what it claimed - result 014 was the first.
REM
REM ***** WHAT THE NEW GATE MEASURES *****
REM   Feed the SAME fixed token sequence down both paths - no sampling, no feedback:
REM     path A  one forward over the whole sequence, no cache
REM     path B  prefill a prefix with use_cache, then feed the remaining tokens one at a
REM             time, always appending the KNOWN next token (teacher forcing)
REM   Compare logits position by position. This is deterministic and it does not amplify.
REM
REM   HARD GATE   fp32, max abs logit difference below 1e-3
REM   REPORT ONLY bf16 greedy divergence, printed together with the top-2 logit gap at the
REM               first divergent position. A gap smaller than the observed logit error is
REM               a tie-break, not a bug, and must not fail the build.
REM
REM   The error pattern also localises a real bug, which the old gate could not do:
REM     grows with position          the RoPE offset is wrong
REM     uniformly large after prefill the attention mask is wrong
REM     flat around 1e-6            correct
REM
REM ***** PREREQUISITE NOT YET IMPLEMENTED *****
REM   scripts\diag_kvcache.py does not exist yet. Required interface:
REM     python scripts\diag_kvcache.py --models TAG [TAG ...] --device cpu --tol 1e-3
REM     options: --max-new N (teacher-forced steps, default 24)
REM              --report-greedy (also run the bf16 greedy comparison, report only)
REM     exit code: 0 pass, 1 logit tolerance exceeded, 3 not implemented
REM     output per model: per-position max abs logit delta, mean delta, argmax agreement,
REM                       and for greedy mode the first divergent index plus its top-2 gap
REM   Reuse tinylm.infer.generate - do NOT write a second sampling or forward loop.
REM   CLAUDE.md already records what copying that loop cost us once (P029, cfg.seq_len).
REM
REM COST: no training, seconds to minutes per model. CPU is enough and is also the fp32 path.
REM ERRORLEVEL POLICY: the guard is a hard stop. The fp32 gate is a hard stop. bf16 only warns.

echo ============================================================
echo [P030 1.5-B] teacher-forced logit equivalence gate
echo ============================================================

echo.
echo [guard] checking whether scripts\diag_kvcache.py exists
if not exist scripts\diag_kvcache.py goto NOTIMPL

echo.
echo ============================================================
echo [1/3] HARD GATE : fp32 on cpu, tolerance 1e-3
echo   All three models. mC_g8_k4 is tied but not sparse34, which separates
echo   "tying plus CLA" from "sparse34" if something does fail.
echo ============================================================
python scripts\runlog.py --name P030-cachegate -- python scripts\diag_kvcache.py --models mA_g4s34_k4 mC_g8_k4 p6d --device cpu --tol 1e-3 --max-new 24
if errorlevel 1 goto GATEBAD

echo.
echo ============================================================
echo [2/3] SAME GATE on cuda (bf16 autocast) - measures how big the precision gap is
echo   Failing here is not a defect. It quantifies the headroom the old gate ignored.
echo ============================================================
python scripts\runlog.py --name P030-cachegate -- python scripts\diag_kvcache.py --models mA_g4s34_k4 mC_g8_k4 p6d --device cuda --tol 1e-3 --max-new 24
if errorlevel 1 echo [INFO] bf16 exceeds the fp32 tolerance - record the number, do not treat as failure

echo.
echo ============================================================
echo [3/3] GREEDY divergence, REPORT ONLY, with the tie margin
echo   This is the old gate, demoted. Read the top-2 gap next to each divergence.
echo ============================================================
python scripts\runlog.py --name P030-cachegate -- python scripts\diag_kvcache.py --models mA_g4s34_k4 mC_g8_k4 p6d --device cuda --report-greedy --max-new 24
if errorlevel 1 echo [INFO] greedy strings differ - check the tie margin before calling it a bug

echo.
echo ================================================================
echo WHAT TO RECORD
echo   1. fp32 max abs logit delta per model (the gate number)
echo   2. bf16 max abs logit delta per model (the precision headroom)
echo   3. for every greedy divergence: position, top-2 gap, and whether that gap is
echo      SMALLER than the bf16 delta from line 2
echo.
echo JUDGEMENT
echo   fp32 delta under 1e-3 and argmax agreement 100 percent
echo       the cache is CORRECT. Proceed to run_P030_infer.bat.
echo   fp32 delta grows with position
echo       RoPE offset. transformer.forward must slice [past_len : past_len+T].
echo   fp32 delta uniformly large only after the prefill boundary
echo       attention mask. Attention.forward needs tril(kv_len - q_len), not is_causal.
echo   fp32 fine but bf16 delta larger than the observed top-2 gaps
echo       the greedy mismatches are TIE-BREAKS. Keep them as report-only forever.
echo.
echo THEN update the gate wiring
echo   run_P030_infer.bat step [0/4] should call THIS script, and its CACHEBAD message must
echo   stop blaming RoPE and the mask - p6d passing already cleared both.
echo ================================================================
echo done.
pause
exit /b 0

:GATEBAD
echo.
echo ================================================================
echo [STOP] fp32 logit equivalence FAILED. This is a real cache bug.
echo.
echo   Unlike the old gate, this one is deterministic - precision cannot explain it.
echo   Read the per-position deltas printed above and match them to the pattern:
echo     delta grows with position          RoPE absolute offset
echo     delta large only past the prefill  SDPA mask alignment
echo     delta only on tied models          CLA owner-keyed cache (kv_bank keys)
echo.
echo   Nothing downstream is worth running until this is green.
echo ================================================================
pause
exit /b 1

:NOTIMPL
echo.
echo ================================================================
echo [STOP] scripts\diag_kvcache.py is not implemented yet.
echo.
echo   The required interface is written in the REM header at the top of this file.
echo   Build it on tinylm.infer.generate - do not write a second forward or sampling loop.
echo.
echo   Suggested order:
echo     1. implement scripts\diag_kvcache.py
echo     2. run run_smoke.bat
echo     3. re-run THIS batch
echo.
echo   Nothing was measured. No files were written.
echo ================================================================
pause
exit /b 3

:BADROOT
echo.
echo ================================================================
echo [STOP] could not locate the repo root (run100m.py not found).
echo   Run this batch from the TinyLM working folder, or double-click it where it lives
echo   (scripts\batch). Nothing was executed.
echo ================================================================
pause
exit /b 9
