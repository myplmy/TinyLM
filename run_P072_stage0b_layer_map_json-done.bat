@echo off
REM =============================================================================
REM  P072 stage 0b  -  the same map, with exact numbers this time
REM                    diagnostics only, no training, about 25 minutes
REM
REM  WHY A SECOND RUN
REM    Stage 0 printed the U1 and U4 matrices as a 10-level glyph heatmap. That
REM    is fine to LOOK at - result 057's figures are reconstructed from it and
REM    the picture is faithful - but each glyph covers about 0.05 of cosine, so
REM    the numbers are not usable for design work.
REM    Result 057 section 5.3 wants layer-wise uneven compression, and REVIEW3
REM    section 5 item 6 is waiting on it. That needs real numbers.
REM
REM  WHAT CHANGED
REM    diag_layer_map.py gained --dump-json (2026-08-24). Printing is unchanged;
REM    the flag only adds a json sidecar with the full matrices plus the U2 and
REM    U3 tables. Nothing about the measurement moves.
REM
REM  !! THIS IS A RE-RUN OF A PASSING EXPERIMENT
REM    Stage 0 did not fail. Its verdicts stand and are written up in result 057.
REM    This exists to make the data machine-readable, so it gets a new stage
REM    name rather than reopening stage 0 (ai_dev_tool/03 section 7.1, D14).
REM
REM  PREDICTIONS, fixed in advance
REM    K1  every printed number reproduces exactly. Same checkpoints, same seed,
REM        same crops - this is deterministic. A difference means the diagnostic
REM        is not deterministic and result 057 has to be re-read.
REM    K2  the json U4 matrix confirms the three tie-able pairs in
REM        mC_d36_ag4_nokd (L4-L5, L8-L9, L10-L11) at input cos above 0.99.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P072_stage0b_layer_map_json --note "=============================================================================" "P072 stage 0b   the same layer map, dumped as json" "The glyph heatmap is 10-level quantised - good picture, unusable numbers." "Layer-wise uneven compression needs the real matrices. About 25 minutes." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P072_stage0b_layer_map_json --note "[1/4] dense - the untied reference"
python scripts\runlog.py --name P072_stage0b_layer_map_json -- python scripts\diag_layer_map.py --preset m100 --models dense --n-crops 8 --abl-crops 16 --dump-json test_result/fig/P072_layermap_dense.json
if errorlevel 1 echo [WARN] dense failed - continuing

echo.
python scripts\runlog.py --name P072_stage0b_layer_map_json --note "[2/4] mC_initonly - the standard control, mlp_group 8"
python scripts\runlog.py --name P072_stage0b_layer_map_json -- python scripts\diag_layer_map.py --preset m100R1c --models mC_initonly --n-crops 8 --abl-crops 16 --dump-json test_result/fig/P072_layermap_mC_initonly.json
if errorlevel 1 echo [WARN] mC_initonly failed - continuing

echo.
python scripts\runlog.py --name P072_stage0b_layer_map_json --note "[3/4] mC_d36_ag4_nokd - the standard model, where uneven compression pays most"
python scripts\runlog.py --name P072_stage0b_layer_map_json -- python scripts\diag_layer_map.py --preset m100R1d --models mC_d36_ag4_nokd --n-crops 8 --abl-crops 16 --dump-json test_result/fig/P072_layermap_mC_d36_ag4_nokd.json
if errorlevel 1 echo [WARN] mC_d36_ag4_nokd failed - continuing

echo.
python scripts\runlog.py --name P072_stage0b_layer_map_json --note "[4/4] mC_r20_nokd - recursion, evaluated at its own trained schedule"
python scripts\runlog.py --name P072_stage0b_layer_map_json -- python scripts\diag_layer_map.py --preset m100R1c --models mC_r20_nokd --infer-repeat 2.0 --n-crops 8 --abl-crops 16 --dump-json test_result/fig/P072_layermap_mC_r20_nokd.json
if errorlevel 1 echo [WARN] mC_r20_nokd failed - continuing

echo.
python scripts\runlog.py --name P072_stage0b_layer_map_json --note "=============================================================================" "READ IN THIS ORDER" "1. K1 - compare the printed M3, M4 and the U4 pair counts against result 057." "   They must match exactly. If they do not, the diagnostic is not" "   deterministic and 057 needs re-reading before anything else." "2. the four json files land in test_result/fig/. Then run" "   python scripts/plot_results.py --fig layermap  for exact heatmaps." "3. K2 - in the d36 json, L4-L5, L8-L9 and L10-L11 should read above 0.99" "   on input cos and above 0.96 on delta cos." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
