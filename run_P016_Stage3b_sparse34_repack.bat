@echo off
setlocal enabledelayedexpansion
REM ==========================================================================
REM  run_P016_Stage3b_sparse34_repack.bat -- re-verify 3:4 after the format fix
REM ==========================================================================
REM
REM   WHY THIS EXISTS (2026-09-06 user instruction 4)
REM     diag_sparse34_pack.py exited 1 on the 2026-09-05 and 2026-09-06 smokes:
REM     round-trip mismatch 234,505 of 1,000,000 and bpw 1.000 instead of 1.250.
REM     The user asked whether Stage3 was therefore not properly validated.
REM
REM   FIRST, WHAT THE BUG WAS AND WHAT IT DID NOT TOUCH
REM     pack_sparse34 put TWO 5-bit codes into ONE uint8 (code0*32 + code1). That
REM     is 10 bits in 8, so code0 lost the top two bits - which are the zero
REM     position. moonshot 92b88f7 rewrote it as 8 codes in 5 bytes. Applied.
REM
REM     NOTE: grep says pack_sparse34 and unpack_sparse34 are called from NOWHERE
REM     except lut.py itself and this one diagnostic. The training-path
REM     --sparse34 lives in ternary.py and only forces one zero per 4-block; it
REM     never packs anything. So the 1.70h Stage3 run is NOT void and +0.04203
REM     stands as a training-log number.
REM
REM   SO WHY RE-RUN ANYTHING? THREE REAL GAPS, NONE NEEDING GPU TRAINING.
REM     1. the fixed format has only ever seen SYNTHETIC tensors. It has never
REM        met a real trained weight. --ckpt is new today and does exactly that.
REM     2. the SAVING was arithmetic, not measurement, and the arithmetic was
REM        wrong by 4.8 percent (1.21/layer includes ~0.057 of non-ternary
REM        items). Corrected to 3.027 and 4.035 MiB. Arm 1 now COUNTS the bytes.
REM     3. the training path itself was never audited on a DENSE body. Arm 2
REM        does that - real nonzero rate, TWN-vs-3:4 decision flips, bpw
REM        conventions. If the training path has its own defect, this is where
REM        it shows, for 0.3h instead of a 1.7h retrain.
REM
REM   WHAT WOULD MAKE A RETRAIN NECESSARY
REM     arm 2 reporting a nonzero rate that is not 75.00 percent, or a bpw
REM     convention mismatch. Then and only then re-run Stage3. Do not retrain
REM     first and audit second - that is the expensive order.
REM
REM   THE THRESHOLD MOVED. Stage3 pre-registered "inside the line at or below
REM     +0.0225", derived as saving(d16) 4.23 x line 0.00531. With the corrected
REM     saving 4.035 that boundary is +0.02143, and for d12 it is 3.027 x
REM     0.00531 = +0.01607. The measured +0.04203 clears BOTH by a wide margin,
REM     so the verdict does not change - but Stage4's paired_eval is what
REM     actually settles it (training-log val is not a verdict, R10).
REM
REM   NO TRAINING. CPU only. COST: about 0.3h.
REM   PLAN: test_plan/P016 (Korean filename) Stage3b
REM ==========================================================================

if not exist run100m.py goto BADROOT

set PYTHONIOENCODING=utf-8

python scripts\runlog.py --name P016_stage3b_sparse34_repack --note "[1/2] fixed packing format against the REAL winner checkpoint - counts bytes"
python scripts\runlog.py --name P016_stage3b_sparse34_repack -- python scripts\diag_sparse34_pack.py --ckpt d12_cla2_r20_s34 --preset m100s8 --data ko-en --tokens 300M --arch dense
if errorlevel 1 echo [WARN] pack diagnostic failed - read which of the six checks

python scripts\runlog.py --name P016_stage3b_sparse34_repack --note "[2/2] training-path audit on a DENSE body - never done before"
python scripts\runlog.py --name P016_stage3b_sparse34_repack -- python scripts\diag_sparse34.py --models d12_cla2_r20_s34 --arch dense --preset m100s8 --data ko-en --tokens 300M --layers 4
if errorlevel 1 echo [WARN] training-path audit failed - continuing

echo.
python scripts\runlog.py --name P016_stage3b_sparse34_repack --note "=================================================================" "READ IN THIS ORDER" "1. arm 1 checks [1] [1b] [2] [3] must all be green. [1b] is the" "   codebook and tail test that the old format could not pass and" "   that the default n=1,000,000 alone would not have caught -" "   1,000,000/4 groups is a multiple of 8, so the tail never ran." "2. arm 1 check [6] is the NEW one and the reason this stage exists." "   Read the measured bpw. It must be 1.250000 on real weights, not" "   just on synthetic ones. Read 'round-trip failures' - must be 0." "3. compare [6] measured MiB with the [4] estimate above it. The" "   estimate is 1.153 MiB per layer times 12 times 1.25/1.60. If" "   they disagree by more than about 1 percent, the ESTIMATE is what" "   is wrong - it has been wrong once already (3.18 vs 3.027)." "4. arm 2 section [B] nonzero rate. It must be 75.00 percent exactly." "   Anything else means the training path forces a different number" "   of zeros than the 5-bit codebook assumes, and THEN Stage3 really" "   is void and needs the retrain." "5. arm 2 section [C] decision flips tells you WHERE the +0.04203" "   came from: weights TWN would have kept that the block rule" "   killed. That is the mechanism, not 'more zeros'." "6. this stage does NOT settle the verdict. Stage4 (paired_eval)" "   does. Do not write a conclusion from arm 2 alone." "================================================================="

set PYTHONIOENCODING=
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo.
echo =================================================================
echo [STOP] run this from the TinyLM working folder (run100m.py not found).
echo =================================================================
if not defined TL_NOPAUSE pause
exit /b 9
