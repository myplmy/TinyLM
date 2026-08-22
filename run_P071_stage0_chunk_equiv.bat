@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  P071 stage 0  -  is loss chunking actually equivalent
REM                   5 tiny runs on synthetic data, about 6 minutes. No real GPU load.
REM
REM  WHY THIS EXISTS  (user, 2026-08-22)
REM    "_ce_chunked and _kd_kl are on the path every training run takes - is it
REM     safe to introduce them with no experiment at all?"
REM    The answer was no, and the risk was not where I expected it.
REM
REM  !! WHAT I BROKE AND THEN FIXED
REM    My first fix put an unconditional .float() inside the _kd_kl chunk loop.
REM    But the old path runs under autocast(bf16), so BOTH student and teacher
REM    logits were bf16. Promoting unconditionally changes the numbers of every
REM    existing --kd-chunk run (P053 family), and result 042 measured the
REM    effective alpha of 0.288 at that precision.
REM    Second fix: fp32 is now opt-in and only the external HF teacher path turns
REM    it on - that path has no published result yet, so changing it breaks
REM    nothing. This batch proves the default path went back to identical.
REM
REM  ALSO FOUND
REM    F.cross_entropy(reduction="mean") divides by the number of NON-IGNORED
REM    targets, not by N. With any ignore_index, sum/N is not mean, and the
REM    difference shows up as a slightly SMALLER loss - silently. We do not pad,
REM    so it is fine today; an assert now pins that assumption.
REM
REM  GATES, fixed in advance
REM    E1  ce_c0 val_loss EXACTLY equals sm_base       chunk 0 is the same call
REM    E2  ce_c64 vs ce_c0 relative difference under 1e-5
REM    E3  ce_c16 vs ce_c64 under 1e-5                     finer chunks must not drift
REM    E4  kd_c64 vs kd_c0 under 1e-5                      the second fix reverted it
REM    E5  no NaN or Inf anywhere
REM
REM  !! E1 IS "EXACTLY", NOT "CLOSE"
REM    The chunk 0 branch is literally the same call as before. Close is not
REM    good enough - if it differs at all, I wrote the branch wrong.
REM
REM  !! WHAT THIS CANNOT DECIDE
REM    How much chunking saves at real size. Tensors here are tiny.
REM    P065 stage 2b owns that question.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P071_stage0_chunk_equiv --note "=============================================================================" "P071 stage 0   is loss chunking equivalent   tiny + synthetic, about 6 min" "The user asked whether these can go in with no experiment. They could not." "E1 is EXACTLY equal, not close - chunk 0 is the same call as before." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P071_stage0_chunk_equiv --note "[1/5] ce_c0 - chunking OFF. Must reproduce sm_base exactly (E1)."
python scripts\runlog.py --name P071_stage0_chunk_equiv -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --seed 1337 --ce-chunk 0 --tag ce_c0
if errorlevel 1 echo [WARN] ce_c0 failed - continuing

python scripts\runlog.py --name P071_stage0_chunk_equiv --note "[2/5] ce_c64 - one flag different from ce_c0 (E2)"
python scripts\runlog.py --name P071_stage0_chunk_equiv -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --seed 1337 --ce-chunk 64 --tag ce_c64
if errorlevel 1 echo [WARN] ce_c64 failed - continuing

python scripts\runlog.py --name P071_stage0_chunk_equiv --note "[3/5] ce_c16 - finer chunks. Does the error accumulate (E3)"
python scripts\runlog.py --name P071_stage0_chunk_equiv -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --seed 1337 --ce-chunk 16 --tag ce_c16
if errorlevel 1 echo [WARN] ce_c16 failed - continuing

python scripts\runlog.py --name P071_stage0_chunk_equiv --note "[4/5] kd_c0 - KD with chunking OFF, the reference for E4"
python scripts\runlog.py --name P071_stage0_chunk_equiv -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --seed 1337 --kd --kd-every 4 --init-from --kd-chunk 0 --tag kd_c0
if errorlevel 1 echo [WARN] kd_c0 failed - continuing

python scripts\runlog.py --name P071_stage0_chunk_equiv --note "[5/5] kd_c64 - KD chunking ON. THIS is the one that proves the revert (E4)."
python scripts\runlog.py --name P071_stage0_chunk_equiv -- python run100m.py train --arch tied --tiny --data synthetic --tokens 2M --steps 30 --micro-bs 4 --seq 128 --accum 2 --eval-every 15 --seed 1337 --kd --kd-every 4 --init-from --kd-chunk 64 --tag kd_c64
if errorlevel 1 echo [WARN] kd_c64 failed - continuing

echo.
python scripts\runlog.py --name P071_stage0_chunk_equiv --note "[verify] compare the five json files against E1 to E5"
python scripts\runlog.py --name P071_stage0_chunk_equiv -- python scripts\check_chunk_equiv.py
if errorlevel 1 echo [WARN] equivalence check FAILED - read WHICH gate

echo.
python scripts\runlog.py --name P071_stage0_chunk_equiv --note "=============================================================================" "READ IN THIS ORDER" "1. E1. If ce_c0 does not EXACTLY match sm_base, the chunk 0 branch is not" "   the same call and nothing below matters. Stop and fix the branch." "2. E4. This is the one that proves my second fix reverted the first one." "   If it fails, --kd-chunk runs from P053 onward are not comparable to each" "   other and result 042's effective alpha 0.288 needs re-checking." "3. E2 and E3. Expect 1e-6. Above 1e-3 means the accumulation is wrong, not" "   that floating point is noisy." "4. ms/step across the five arms. Y4 predicts -1 to -3 percent from the python" "   loop. Above 10 percent means chunk should be larger." "!! VRAM here means nothing - tiny preset. P065 stage 2b owns that." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
