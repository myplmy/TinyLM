@echo off
REM ===== P030 stage 1.5-A : DISCRIMINATE why the KV cache gate failed =====
REM   Plan: test_plan\P030 (stage 1.5)    Evidence: test_result\014 section 8
REM
REM ***** WHAT THIS ANSWERS *****
REM   The [0/4] gate failed on mA_g4s34_k4 (2 of 5 prompts) but PASSED on p6d (5 of 5).
REM   The two places the old STOP message blamed - RoPE slicing and the SDPA mask - are
REM   SHARED by dense and tied. If either were wrong, p6d would have failed too. It did not.
REM   So they are not the cause. Two hypotheses remain:
REM
REM     H1 NUMERICS   sample() runs bf16 autocast on cuda, and the two paths take DIFFERENT
REM                   SDPA kernels (is_causal flash vs bool attn_mask). bf16 has 8 mantissa
REM                   bits. Greedy decoding over 24 steps turns ONE argmax flip into a
REM                   completely different string. Both failures happened at near-tie spots.
REM     H2 CLA CACHE  mA has cla_group=2 while dense_baseline forces cla_group=1, so ONLY
REM                   the tied models exercise the owner-keyed cache. That path is unproven.
REM
REM   sample() disables autocast when the device is not cuda, so running the SAME gate on
REM   CPU is a pure fp32 run. That one change separates H1 from H2:
REM     CPU passes  : H1. The cache is probably fine and the GATE is what is too strict.
REM     CPU fails   : H2. Real bug, and it lives in the CLA owner-keyed cache path.
REM
REM   mC_g8_k4 is included on purpose. It is tied (cla_group=2) but NOT sparse34, so it
REM   splits "tying and CLA" from "sparse34" if the pattern is architectural.
REM
REM ***** THIS IS A DIAGNOSTIC, NOT A PROOF *****
REM   Passing on CPU does NOT prove the cache is correct. Only the teacher-forced logit
REM   comparison proves that - see run_P030_cachegate.bat (stage 1.5-B). Run that next
REM   whichever way this one lands.
REM
REM ***** PREREQUISITE NOT YET IMPLEMENTED *****
REM   scripts\probe_prompts.py has NO --device flag today. load_model picks cuda whenever a
REM   GPU is visible, so the gate cannot be forced onto CPU yet. The guard below detects
REM   that and stops cleanly. Implementation needed (two lines):
REM     1. ap.add_argument("--device", default=None, help="cpu forces fp32, autocast off")
REM     2. pass it through: load_model(arch=arch, ckpt_path=str(ck), device=a.device)
REM
REM COST: no training. The decisive step needs no GPU. Tens of minutes at most - the
REM   no-cache path recomputes the whole sequence for every token, so it is the slow half.
REM ERRORLEVEL POLICY: the guard is a hard stop. Both measurements only record.

echo ============================================================
echo [P030 1.5-A] KV cache gate : bf16-on-cuda vs fp32-on-cpu
echo ============================================================

echo.
echo [guard] checking whether probe_prompts.py accepts --device
python -c "import sys,pathlib; s=pathlib.Path('scripts/probe_prompts.py').read_text(encoding='utf-8'); sys.exit(0 if '--device' in s else 3)"
if errorlevel 3 goto NOTIMPL
if errorlevel 1 echo [WARN] guard check errored - continuing anyway

echo.
echo ============================================================
echo [1/2] REPRODUCE on cuda (bf16 autocast) - failure here is EXPECTED
echo   This is the same run that produced test_result\014 section 8. It is here so both
echo   numbers live in ONE log and nobody has to trust a remembered result.
echo ============================================================
python scripts\probe_prompts.py --check-cache --device cuda --models mA_g4s34_k4 mC_g8_k4 p6d
if errorlevel 1 echo [INFO] mismatch on cuda - expected, this is the thing being explained

echo.
echo ============================================================
echo [2/2] DECIDING RUN : same gate on cpu (fp32, autocast off)
echo   THIS IS THE ONE THAT MATTERS. Read its verdict, not the one above.
echo ============================================================
python scripts\probe_prompts.py --check-cache --device cpu --models mA_g4s34_k4 mC_g8_k4 p6d
if errorlevel 1 goto FP32BAD

echo.
echo ================================================================
echo VERDICT : H1 NUMERICS. fp32 agrees, bf16 does not.
echo.
echo   What this means
echo     The cache and the no-cache path compute the SAME function. The disagreement on
echo     cuda comes from bf16 plus two different SDPA kernels, amplified by 24 steps of
echo     greedy feedback. mA fails more than p6d because mA is the more repetitive model
echo     (result 013), so it sits on near-ties more often.
echo.
echo   What this does NOT mean
echo     It does NOT mean the cache is proven correct. Agreement on 5 prompts is evidence,
echo     not a proof. The proof is teacher-forced logit equivalence.
echo.
echo   NEXT, in this order
echo     1. run_P030_cachegate.bat   (stage 1.5-B - the actual invariant)
echo     2. run_P030_infer.bat       (stage 2 - only after 1.5-B passes)
echo ================================================================
echo done.
pause
exit /b 0

:FP32BAD
echo.
echo ================================================================
echo VERDICT : H2 CLA CACHE. fp32 still disagrees, so this is a REAL BUG.
echo.
echo   Precision is now ruled out, and RoPE plus the SDPA mask were already ruled out by
echo   p6d passing. What is left is the one path only the tied models take:
echo.
echo     tinylm\model\transformer.py forward()
echo       - kv_bank is keyed by self.owner[i], not by i
echo       - only layers where i equals self.owner[i] call compute_kv and concat the past
echo       - non-owner layers read kv_bank[self.owner[i]]
echo     Check FIRST whether the returned kv_bank keys match the past_kv keys fed back in
echo     on the next step, and whether a non-owner layer can ever read a stale entry.
echo.
echo   Also check which models failed above. If mC_g8_k4 failed too, the trigger is
echo   cla_group=2 itself. If only mA failed, look at sparse34 as well.
echo.
echo   Do NOT run run_P030_infer.bat until this is fixed. Speed numbers from a wrong
echo   cache are meaningless.
echo ================================================================
pause
exit /b 1

:NOTIMPL
echo.
echo ================================================================
echo [STOP] scripts\probe_prompts.py has no --device flag, so the gate cannot be
echo        forced onto CPU and this batch cannot decide anything.
echo.
echo   Add these two lines to scripts\probe_prompts.py, then re-run this batch:
echo     1. ap.add_argument("--device", default=None)
echo     2. load_model(arch=arch, ckpt_path=str(ck), device=a.device)
echo        (both call sites: the --check-cache branch and the main loop)
echo.
echo   Nothing was measured. No files were written.
echo ================================================================
pause
exit /b 3
