@echo off
setlocal enabledelayedexpansion
REM =============================================================================
REM  run_P007B_stage2_commonbpb.bat -- P007B STAGE 2 : re-judge p6d vs p12d on
REM                                    a COMMON source text
REM  Plan: test_plan\P007_...md   Basis: result 006 section 5
REM =============================================================================
REM
REM PRECONDITION: none. Both checkpoints exist, the tool exists (result 011
REM   section 1 used it), and nothing here needs new code.
REM
REM WHY THIS EXISTS
REM   Result 006 section 5 measured p12d (pool 1200M) at +0.0614 versus p6d
REM   (pool 600M) and then found the comparison INVALID: prepare() takes val
REM   from the LAST 0.5 percent of the stream, and Korean Wikipedia runs out at
REM   about 300M tokens, so the 1200M val set contains ZERO Korean while the
REM   600M val set has 5.5 percent. Two different exam papers.
REM
REM   common_bpb.py sidesteps that entirely: SAME source text, SAME bytes, each
REM   model with its own tokeniser. bpb = loss / ln2 / bytes-per-token, so the
REM   val set never enters. This is the ONLY valid p6d vs p12d number available
REM   today, and it costs about one minute.
REM
REM ***EXPECTATION BEFORE THE NUMBER.***
REM   The bpb resolution is about 0.008. Result 006 section 5.5 corrected the
REM   raw gap from +0.0252 to +0.0038 once the bytes-per-token bias was removed,
REM   i.e. BELOW resolution. So expect a SMALL gap here, and be ready for the
REM   honest answer being "these two are indistinguishable on English".
REM
REM ***AND READ THE LIMIT.*** This benchmark is ENGLISH ONLY. p12d saw 75
REM   percent English against p6d's roughly 50 percent, so if p12d wins on
REM   English that is an exposure result, not a pool-size result. The Korean
REM   half needs P028 stage 2 (a Korean common text), which does not exist yet.
REM
REM COST: about 1 minute. GPU only for the forward passes (tiny).
REM DEPENDS ON NOTHING. Reads two checkpoints, writes nothing but the log.
REM ERRORLEVEL POLICY: a missing checkpoint stops the batch (nothing to compare).
REM =============================================================================

if not exist run100m.py goto BADROOT
if not exist runs\ckpt\m100_ko-en_300M_p12d.pt goto NOCKPT
if not exist runs\ckpt\m100_ko-en_300M_p6d.pt goto NOCKPT
if not exist datasets\squad\train-v2.0.json goto NOSQUAD

echo =============================================================
echo [P007B-2] p6d vs p12d on common source text - the only valid comparison
echo =============================================================
python scripts\runlog.py --name P007B-stage2 --note "[P007B-2] p6d vs p12d on common source text - the only valid comparison"

echo.
echo =============================================================
echo [1/2] the pool comparison, done properly
echo =============================================================
python scripts\runlog.py --name P007B-stage2 --note "[1/2] the pool comparison, done properly"
python scripts\runlog.py --name P007B-stage2 -- python scripts\common_bpb.py --models p6d p12d --data ko-en ko-en --tokens 300M --max-docs 4000
if errorlevel 1 goto RUNBAD

echo.
echo =============================================================
echo [2/2] cache language composition - the evidence for WHY the
echo       original comparison was invalid (no GPU, no model)
echo =============================================================
python scripts\runlog.py --name P007B-stage2 --note "[2/2] cache language composition - why the original comparison was invalid"
python scripts\runlog.py --name P007B-stage2 -- python scripts\diag_val_lang.py --data ko-en --pools 100M 300M 600M 1200M
if errorlevel 1 echo [WARN] language diagnostic failed - continuing

python scripts\runlog.py --name P007B-stage2 --note "=================================================================" "WHAT TO RECORD" "  1. the bpb column for p6d and p12d, and the gap." "  2. the val Hangul percentage table from [2/2]. That table is the reason" "     result 006 section 5 calls the original comparison invalid." "" "HOW TO READ IT" "  gap under 0.008 bpb" "      -^> the two pools are INDISTINGUISHABLE on English prose. The +0.0614" "         from result 006 section 5 was the val set swap, not the pool." "  p12d clearly better" "      -^> consistent with p12d seeing 75 percent English versus roughly 50." "         That is an EXPOSURE result. It does not say a bigger pool is better." "  p6d clearly better" "      -^> a real pool effect survives even the English handicap. Record it," "         but still do not restate '2x pool buys 0.12' - that number came" "         from a different measurement that is confounded." "" "LIMITS: ENGLISH ONLY / one seed each / SQuAD context is Wikipedia prose /" "  this does NOT rehabilitate the p6d vs p12d val_loss comparison - that one" "  stays invalid regardless of what comes out here." "================================================================="
echo done.
pause
exit /b 0

:NOCKPT
echo.
echo =================================================================
echo [STOP] need runs\ckpt\m100_ko-en_300M_p6d.pt and ..._p12d.pt
echo =================================================================
pause
exit /b 5

:NOSQUAD
echo.
echo =================================================================
echo [STOP] datasets\squad\train-v2.0.json not found. Nothing was executed.
echo =================================================================
pause
exit /b 3

:RUNBAD
echo.
echo =================================================================
echo [STOP] common_bpb failed. Nothing to record.
echo =================================================================
pause
exit /b 4

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
pause
exit /b 9
