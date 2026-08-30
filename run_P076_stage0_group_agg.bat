@echo off
REM P076 stage 0  -  does averaging cancel inside a tying group.
REM   Tied parent-init averages g dense layers into one shared weight (A1).
REM   Nobody checked whether that averaging destroys magnitude.
REM   Shrink ratio = norm(mean(Wi)) / mean(norm(Wi)).  1.0 means no cancellation.
REM   above 0.9 means A1 equals A4, stage 2 is not worth opening
REM   below 0.7 means build A4 (norm-corrected mean). Open stage 2.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P076_stage0_group_agg --note "[1/2] the dense parent that every tied run initialises from"
python scripts\runlog.py --name P076_stage0_group_agg -- python scripts\diag_group_agg.py --preset m100R1c --data ko-en --tokens 300M --tag dense
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P076_stage0_group_agg --note "[2/2] g=4 as well - the shrink ratio may depend on group size"
python scripts\runlog.py --name P076_stage0_group_agg -- python scripts\diag_group_agg.py --preset m100R1c --data ko-en --tokens 300M --tag dense --group 4
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P076_stage0_group_agg --note "READ IN THIS ORDER" "1. the shrink ratio per kind (mlp / attn). That is the whole experiment." "2. mean cosine. Low cosine explains a low shrink ratio." "3. the verdict line. It decides whether stage 2 (2.7h per arm) opens at all." "4. this measures INITIALISATION geometry only. How much training washes it" "   out is not answered here - that is stage 2."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
