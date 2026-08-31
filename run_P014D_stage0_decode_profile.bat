@echo off
REM P014D stage 0  -  where does decode time actually go?  About 0.3 hours, no GPU.
REM
REM   USER DECISION C2 (2026-08-31): put this BEFORE the LUT kernel work.
REM   docs/methods/12_inference_speed.md section 12.4 had already ordered it that
REM   way. Two things are unknown and both gate a 6-hour kernel:
REM
REM     1. Of 76.2 ms per decoded token, 13.67 ms (17.9 percent) is intercept -
REM        fixed cost that does not scale with visits. On the fp32 path the same
REM        intercept was 3.3 to 4.3 ms. Nobody knows why it quadrupled on the
REM        deployment path, and because it is fixed, SHORT answers pay it most.
REM
REM     2. The unpack share is written as 30 to 42 ms, a 40 percent wide band,
REM        and every number in it is DERIVED. A profiler has never been run.
REM
REM   Writing a 6-hour kernel against a band that wide is a gamble. This batch
REM   replaces the band with a measurement.
REM
REM   HOW TO ACT ON IT
REM     unpack share 40 to 55 percent means the derivation holds, P014D is worth 6h
REM     unpack share under 20 percent means the ceiling is small, look elsewhere
REM     either way means the top-12 list is where the intercept has to be hiding
REM
REM   DO NOT QUOTE tok/s FROM THIS RUN.  The profiler itself slows everything
REM   down. Shares and rankings are the output; absolute speed belongs to
REM   mem_runtime and the CPU benchmark path.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P014D_stage0_decode_profile --note "[1/2] the budget candidate - fp32 vs int8 vs LUT on one checkpoint"
python scripts\runlog.py --name P014D_stage0_decode_profile -- python scripts\diag_decode_profile.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4 --max-new 32
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P014D_stage0_decode_profile --note "[2/2] the recursive arm - visits multiply everything except the intercept"
python scripts\runlog.py --name P014D_stage0_decode_profile -- python scripts\diag_decode_profile.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20 --max-new 32
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P014D_stage0_decode_profile --note "READ IN THIS ORDER" "1. the unpack share for int8 and lut. That is the whole gate for P014D." "2. the top-12 self CPU time list for fp32. Whatever is large there and NOT" "   a GEMM is a candidate for the intercept." "3. compare arm 1 and arm 2. Visits scale the per-layer work but NOT the" "   intercept, so the intercept share should FALL in the recursive arm." "   If it does not, it is not an intercept and 12_inference_speed section" "   12.1 needs rewriting." "4. do not quote tok/s. The profiler distorts absolute time." "5. this decides whether P014D opens. It does not open it."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
