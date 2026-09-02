@echo off
REM P076 stage 0b  -  RETRY.  Stage 0 died in 2 seconds, twice, with
REM   TypeError: build_config() missing 1 required positional argument: 'seq'
REM   diag_group_agg.py called build_config(preset, arch="tied") while the
REM   other six call sites in the repo all pass (preset, arch, seq, ckpt).
REM   Fixed 2026-08-31: --seq added, default 1024.  It does not affect the
REM   result - the tool only reads layer structure - and the help says so.
REM
REM   THE QUESTION IS UNCHANGED.  Parent initialisation for a tied model takes
REM   the ARITHMETIC MEAN of the layers in a group (scheme A1).  If those
REM   layers point in different directions the mean cancels and we are
REM   initialising from something smaller than any of its parts.
REM
REM     shrink ratio = norm(mean(Wi)) / mean(norm(Wi))
REM
REM   over 0.90  gives the layers already agree, A1 equals A4, and there is no
REM                 reason to open stage 2 at 2.7 hours per arm
REM   under 0.70 gives build A4, a norm-corrected mean
REM
REM   A cheap diagnostic gating an expensive training run.  No GPU, no training.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P076_stage0b_group_agg --note "[1/2] the dense parent that every tied run initialises from"
python scripts\runlog.py --name P076_stage0b_group_agg -- python scripts\diag_group_agg.py --preset m100R1c --data ko-en --tokens 300M --tag dense
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P076_stage0b_group_agg --note "[2/2] g=4 as well - the shrink ratio may depend on group size"
python scripts\runlog.py --name P076_stage0b_group_agg -- python scripts\diag_group_agg.py --preset m100R1c --data ko-en --tokens 300M --tag dense --group 4
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P076_stage0b_group_agg --note "READ IN THIS ORDER" "1. the shrink ratio per kind (mlp / attn). That is the whole experiment." "2. mean cosine. Low cosine explains a low shrink ratio." "3. the verdict line. It decides whether stage 2 opens at all." "4. this measures INITIALISATION geometry only. How much training washes it" "   out is not answered here - that is stage 2." "5. if g=8 and g=4 disagree, the group size matters and stage 2 needs both."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
