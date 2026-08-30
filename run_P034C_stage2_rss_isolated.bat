@echo off
REM P034C stage 2  -  RSS again, this time one model per process.
REM
REM   Stage 1 (result 061) failed all three gates. The reason was the design,
REM   not the models: running several models in ONE process meant each later
REM   model reused pages the previous one had freed. RSS increase came out as
REM   1133 / 875 / 525 MB while the tensor sums were 310 / 427 / 315 - the
REM   largest model showed the SMALLEST increase.
REM
REM   Two fixes here.
REM     1. one mem_runtime call per model, so every load starts from a clean
REM        interpreter (pre-load RSS must land in 385 to 390 MB).
REM     2. max-new 4096 instead of 512, so the KV signal is 56 MB rather than
REM        7 MB. Stage 1 had 7 MB of signal against 80 to 125 MB of noise.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P034C_stage2_rss_isolated --note "[1/6] mC_cla2_ag4 at max-new 32 - fresh process"
python scripts\runlog.py --name P034C_stage2_rss_isolated -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla2_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P034C_stage2_rss_isolated --note "[2/6] mC_cla2_ag4 at max-new 4096 - fresh process"
python scripts\runlog.py --name P034C_stage2_rss_isolated -- python scripts\mem_runtime.py --device cpu --max-new 4096 --preset m100R1c --models mC_cla2_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P034C_stage2_rss_isolated --note "[3/6] mC_initonly_nc at max-new 32 - fresh process"
python scripts\runlog.py --name P034C_stage2_rss_isolated -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_initonly_nc --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P034C_stage2_rss_isolated --note "[4/6] mC_initonly_nc at max-new 4096 - fresh process"
python scripts\runlog.py --name P034C_stage2_rss_isolated -- python scripts\mem_runtime.py --device cpu --max-new 4096 --preset m100R1c --models mC_initonly_nc --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P034C_stage2_rss_isolated --note "[5/6] mC_cla1_ag4 at max-new 32 - fresh process"
python scripts\runlog.py --name P034C_stage2_rss_isolated -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_cla1_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P034C_stage2_rss_isolated --note "[6/6] mC_cla1_ag4 at max-new 4096 - fresh process"
python scripts\runlog.py --name P034C_stage2_rss_isolated -- python scripts\mem_runtime.py --device cpu --max-new 4096 --preset m100R1c --models mC_cla1_ag4 --drop-latent --lut --emb-quant int8 --kv-seq 1024
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P034C_stage2_rss_isolated --note "READ IN THIS ORDER" "1. pre-load RSS on every row. If it is not 385 to 390 MB the process was not" "   clean and that row is void. Stage 1 had rows starting at 1356 MB." "2. per model: RSS at 4096 minus RSS at 32. Expected = kv_mb x 4000/1024." "   cla2 expects about 58 MB, initonly 58 MB, cla1 117 MB." "3. if that difference is still negative, the allocator wins again and RSS is" "   simply not the instrument for this. Say so plainly - it is a real finding." "4. only if 2 passes: safety factor = RSS increase over load / (runtime + kv)." "   THAT is the number every budget statement has been missing."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
