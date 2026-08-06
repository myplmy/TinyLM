@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P039_vocab_diag.bat -- P039 : vocabulary utilisation and under-trained
REM                             tokens
REM  Basis: docs\methods\08_paper_review_202608.md section 4
REM         Fishing for Magikarp, arXiv:2405.05417
REM =============================================================================
REM
REM PRECONDITION: scripts\diag_vocab.py IMPLEMENTED 2026-08-06. No GPU needed
REM   except optionally loading a checkpoint on CPU for the embedding norms.
REM
REM WHY IT MATTERS HERE - THREE SEPARATE REASONS
REM   memory : after int8 (stage 3), 33.0 MB of mC's 86.9 MB residency is fp32,
REM            and 32.0 MB of that is emb.weight alone. That weight is TIED to
REM            the output head, so int8-ing it is not simple. Shrinking the
REM            VOCABULARY is the one path that reduces it without a kernel.
REM   data   : result 018 found SEO spam inside the 200k documents the tokeniser
REM            was trained on. Product codes may hold vocabulary slots.
REM   filter : result 023 section 8 removed that spam FROM TRAINING. So the
REM            filtered corpus may have MORE under-trained tokens than the
REM            unfiltered one. That is why [3/3] exists.
REM
REM ***EXPECTATION BEFORE THE NUMBER.***
REM   A partial sandbox scan (60M of the 600M ko-en cache) already showed only
REM   93 of 32,768 tokens unused, i.e. 0.28 percent, and 25 of those are byte
REM   fallbacks or specials. If the full scan agrees, the honest conclusion is
REM   ***vocabulary reduction is NOT a memory lever here*** and P034 stage 5
REM   has to solve the head-tying problem instead. A negative result closes an
REM   option, which is worth the five minutes.
REM
REM COST: a few minutes. GPU 0.
REM DEPENDS ON NOTHING. Reads caches and one checkpoint. Writes nothing.
REM ERRORLEVEL POLICY: independent scans, so failures warn and continue.
REM =============================================================================

if not exist run100m.py goto BADROOT

echo =============================================================
echo [P039] vocabulary utilisation - is shrinking the vocab a lever
echo =============================================================
python scripts\runlog.py --name P039-vocab --note "[P039] vocabulary utilisation - is shrinking the vocab a lever"

echo.
echo =============================================================
echo [1/3] ko-en full cache + embedding norms from p6d
echo =============================================================
python scripts\runlog.py --name P039-vocab --note "[1/3] ko-en full cache + embedding norms from p6d"
python scripts\runlog.py --name P039-vocab -- python scripts\diag_vocab.py --data ko-en --tokens 600M --ckpt runs\ckpt\m100_ko-en_300M_p6d.pt --top-unused 40
if errorlevel 1 echo [WARN] ko-en scan failed - continuing

echo.
echo =============================================================
echo [2/3] ko-edu-en - a different tokeniser on a different corpus
echo       result 011 section 1.3 measured an 8.1 percent compression gap
echo =============================================================
python scripts\runlog.py --name P039-vocab --note "[2/3] ko-edu-en - different tokeniser, different corpus"
python scripts\runlog.py --name P039-vocab -- python scripts\diag_vocab.py --data ko-edu-en --tokens 300M --top-unused 40
if errorlevel 1 echo [WARN] ko-edu-en scan failed - continuing

echo.
echo =============================================================
echo [3/3] the filtered cache - did removing spam CREATE dead tokens
echo =============================================================
python scripts\runlog.py --name P039-vocab --note "[3/3] filtered cache - did removing spam create dead tokens"
python scripts\runlog.py --name P039-vocab -- python scripts\diag_vocab.py --data ko-edu-en --tokens 600M --suffix _filtered --top-unused 40
if errorlevel 1 echo [WARN] filtered scan failed - continuing

python scripts\runlog.py --name P039-vocab --note "=================================================================" "WHAT TO RECORD" "  1. the 'frequency 0' count and percentage for each of the three scans." "  2. the per-kind table, especially which KIND the dead tokens sit in." "  3. the embedding norm ratio from [1/3], if the checkpoint loaded." "  4. ***the difference between [2/3] and [3/3].*** Same tokeniser, one" "     corpus filtered and one not. Any increase in dead tokens is a COST of" "     filtering that result 023 section 8 did not measure." "" "HOW TO READ IT" "  frequency 0 under 1 percent" "      -^> vocabulary reduction is NOT a memory lever. Record that and close" "         option (c) of P034 stage 5. The 33 MB has to come from the head" "         tying problem or from a fused kernel (P014)." "  frequency 0 over 5 percent, or under-100 over 20 percent" "      -^> 32,768 -^> 24,000 would cut the embedding by 26.7 percent. But that" "         needs a tokeniser retrain AND a full model retrain - price it before" "         recommending it." "  dead tokens concentrated in symbols or digits" "      -^> tokeniser training sample problem, and result 018's spam is the" "         prime suspect. Feeds docs\\methods\\07_corpus_selection.md." "" "LIMITS: frequency is per CACHE, not universal / the norm signal is WEAK here" "  because the head is tied to the embedding, so every token appears in the" "  softmax denominator and gets gradient even at frequency 0 / this tool only" "  MEASURES, it changes no vocabulary." "================================================================="
echo done.
pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
