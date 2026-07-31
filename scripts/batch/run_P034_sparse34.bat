@echo off
REM ===== relocated to scripts\batch on 2026-07-31 =====
REM   Root now holds only batches for experiments that have NOT run yet. This one is a
REM   REUSABLE tool or a completed run kept for re-verification, so it lives here.
REM   It works from EITHER location: launched from the repo root, or double-clicked here.
REM   No percent-expansion is used (this repo bans the percent sign in .bat files), so the
REM   working directory is fixed by looking for a marker file instead.
if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

REM ===== P034 stage 1.5 : audit the 3:4 sparse ternary path (implementation and accounting)
REM   Plan: test_plan\P034    Trigger: user question 2026-07-31
REM
REM ***** THE QUESTION *****
REM   Result 016 found mA (g4 + 3:4 sparse) has LARGER resident memory than mC (g8), and
REM   result 014 found mA was SLOWER on CPU than dense. The two models differ in tying
REM   degree AND in 3:4 sparsity. Before REVIEW1's winner can be settled we have to know
REM   whether the 3:4 path itself has an implementation or accounting problem.
REM
REM ***** FOUR CHECKS, ALL ON CPU, NO TRAINING *****
REM   [A] unique parameter split - is the resident gap entirely g4 vs g8
REM       Prediction: 3:4 removes ZERO parameters. It only forces values to zero. So the
REM       resident gap should be exactly the tying difference, 4 MLP groups vs 2.
REM   [B] actual nonzero fraction - the important one
REM       The standard path is a TWN threshold, so its sparsity is DATA DEPENDENT. The 3:4
REM       path zeroes exactly 25 percent. If the standard path already zeroes MORE than 25
REM       percent, then 3:4 does not add sparsity at all - it REDUCES it while making the
REM       pattern regular. The technique would then be about PACKABILITY, not sparsity, and
REM       the name is misleading everywhere in our docs.
REM   [C] flipped decisions - how many weights TWN would keep that 3:4 kills, and vice versa
REM       The first number is the candidate mechanism for result 008's quality cost.
REM   [D] bpw accounting - this is the one that can move the REVIEW1 decision
REM       Our docs say g128 ternary is 1.71 bpw and the deployed GGUF density is 1.95, so
REM       1.95 = codes + group scale + container overhead. But the 1.25 used for sparse34 is
REM       the BARE code space, C(4,3) times 2^3 equals 32 equals 2^5. It includes neither the
REM       group scale nor the container. Numerator and denominator use different conventions,
REM       which inflates the 2.64x reduction. The script recomputes storage MB under three
REM       conventions and reports whether the ORDER survives.
REM
REM ***** WHAT THIS CANNOT DO *****
REM   It reads trained latent weights. mA was trained WITH 3:4, so applying TWN to its
REM   weights answers "what would TWN do to these weights now", not "what if it had been
REM   trained with TWN". Read the WITHIN-model comparison, not the across-model one.
REM   Causality needs training runs, not this.
REM
REM COST: minutes, CPU only, no GPU. Writes nothing to runs.
REM ERRORLEVEL POLICY: nothing here is a hard stop - every check only warns.

echo ============================================================
echo [P034-1.5] 3:4 sparse ternary audit
echo ============================================================

echo.
echo [guard] checking whether scripts\diag_sparse34.py exists
if not exist scripts\diag_sparse34.py goto NOTIMPL

echo.
echo ============================================================
echo [1/2] full audit, all three models, summary level
echo ============================================================
python scripts\diag_sparse34.py --models mA_g4s34_k4 mC_g8_k4 p6d
if errorlevel 2 echo [WARN] some checkpoints were missing - read which ones above
if errorlevel 1 echo [WARN] audit reported a problem - continuing

echo.
echo ============================================================
echo [2/2] per-layer detail for the sparse model, first 8 layers
echo   Watch whether the nonzero fraction is uniform across layers or whether some layers
echo   are far more affected. A large spread means the single global 1.25 bpw number hides
echo   real variation.
echo ============================================================
python scripts\diag_sparse34.py --models mA_g4s34_k4 --layers 8
if errorlevel 1 echo [WARN] per-layer pass failed - continuing

echo.
echo ================================================================
echo WHAT TO RECORD
echo   1. [A] unique ternary params per model, and whether the resident gap from result 016
echo      is fully explained by the tying difference
echo   2. [B] measured nonzero percentage, standard TWN vs 3:4, and which one is sparser
echo   3. [C] the "TWN keeps, 3:4 kills" percentage and the relative reconstruction error
echo   4. [D] the three-convention storage table, and whether the ORDER changed
echo.
echo HOW TO ACT
echo   order unchanged across conventions
echo       the storage-based argument survives. mA stays smaller on storage, and the
echo       REVIEW1 debate stays purely about storage versus resident.
echo   order changes, or the gap collapses
echo       the reported 2.64x was partly an artefact of mixing accounting conventions.
echo       Fix mem_breakdown to use ONE convention, restate result 008 and the review, and
echo       only then decide the winner.
echo   3:4 turns out to be LESS sparse than the TWN path
echo       rename the technique in the docs. It is a packability constraint, not a sparsity
echo       lever, and the quality cost in result 008 comes from killing weights TWN kept.
echo.
echo LIMITS: this reads trained weights and compares two RULES on them. It is a
echo   correlational diagnostic. The container overhead in convention C is BACK-COMPUTED
echo   from our own docs, and whether a real packed format keeps 1.25 bpw for 3:4 codes is
echo   still unverified - the same caveat P016 already recorded.
echo ================================================================
echo done.
pause
exit /b 0

:NOTIMPL
echo.
echo ================================================================
echo [STOP] scripts\diag_sparse34.py is missing.
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
