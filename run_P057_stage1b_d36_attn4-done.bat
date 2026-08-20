@echo off
REM =============================================================================
REM  P057 stage 1b  -  36 layers + attn_group 4    (about 3.3 hours)
REM                    preset m100R1d, tag mC_d36_ag4
REM
REM  WHY 1b AND NOT A RE-RUN OF 1
REM    Stage 1 ran attn_group 2 and passed its line (-0.0138 versus -0.010).
REM    This is a DIFFERENT point on the same axis, not a repeat, so it gets a
REM    new stage letter (ai_dev_tool/03 s7.1, D14).
REM
REM  WHY g=4 IS THE INTERESTING ONE
REM    stage 1 result:  d36 + ag2   57.20M ternary   469.7 MB residency  (+4.0 pct)
REM    computed here:   d36 + ag4   45.43M           about 379.8 MB      (-15.9 pct)
REM    g2 bought quality but still costs MORE residency than the 20-layer
REM    baseline. g4 is the first configuration in this whole repo that would be
REM    36 layers for LESS residency than mC_wsd. That is the shape we have been
REM    looking for since REVIEW1.
REM
REM  !! ADOPTION LINE, FIXED IN ADVANCE
REM    At -15.9 percent residency we are BUYING memory, not spending it, so the
REM    line flips sign. Using the same exchange rate as stage 1 (result 032 s8,
REM    about 0.0044 nats per unique-ternary million):
REM        9.42M fewer than mC_wsd means we can afford up to about +0.041
REM    So: BETTER THAN +0.041 versus mC_wsd = adopt.
REM    Worse than that and attention averaging is too lossy at g=4, and g=2
REM    stands as the usable setting.
REM
REM  !! WHAT STAGE 0b SAID, AND WHAT IT DID NOT
REM    step0 GAP fell from +4.7842 (g2) to +3.9285 (g4) - still inside the band,
REM    but lower. step0 decides GO or NO-GO only, never magnitude (D13).
REM    So this run is genuinely uncertain, which is why it is worth 3.3 hours.
REM
REM  !! WATCH
REM    [attn] line: 32 middle layers share 8 attentions
REM    report() ternary near 45.4M. If it says 57.2M the flag did not change.
REM    the gate probe at the end - does attention still switch off at g=4?
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P057_stage1b_d36ag4 --note "=============================================================================" "P057 stage 1b   36 layers + attn_group 4   about 3.3 hours   -   tag mC_d36_ag4" "Adoption line fixed in advance: better than +0.041 versus mC_wsd." "This would be 36 layers for LESS residency than the 20-layer baseline." "References: mC_wsd 3.6984 / mC_d36 3.6734 / mC_d36_ag2 3.6847" "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P057_stage1b_d36ag4 --note "[P057 stage 1b] m100R1d with attn_group 4, gate_scale transplant, KD k4. 32 middle layers share 8 attentions."

python scripts\runlog.py --name P057_stage1b_d36ag4 -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --kd --kd-every 4 --depth-init gate_scale --attn-group 4 --tag mC_d36_ag4
if errorlevel 1 goto TRAINBAD

echo.
python scripts\runlog.py --name P057_stage1b_d36ag4 --note "[queue] settling 15 s before the evaluation process starts"
timeout /t 15 /nobreak

python scripts\runlog.py --name P057_stage1b_d36ag4 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_d36 mC_d36_ag2 mC_d36_ag4
if errorlevel 1 echo [WARN] paired_eval returned an error - the training run is still valid

python scripts\runlog.py --name P057_stage1b_d36ag4 -- python scripts\diag_layer_gates.py --tag mC_d36_ag4 --preset m100R1d --teacher-preset m100
if errorlevel 1 echo [WARN] gate probe failed - the training run is still valid

echo.
echo.
python scripts\runlog.py --name P057_stage1b_d36ag4 --note "=============================================================================" "READ IN THIS ORDER" "1. report() ternary near 45.4M and residency near 379.8 MB." "2. json attn_group = 4, n_layers = 36, grad_max under 10." "3. paired versus mC_wsd against the fixed line of +0.041." "4. paired versus mC_d36_ag2 - how much did halving the attention again cost?" "5. the gate probe. Attention switched itself off at g=1 and g=2. At g=4 there" "   are only 8 shared modules for 32 layers; if it STILL switches off, the" "   attention depth is doing nothing at all and that is its own finding." "REMINDER: quote residency as fp32 or int8 explicitly (trap 24)." "============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:TRAINBAD
echo.
echo [STOP] training failed. Read the log before retrying.
if not defined TL_NOPAUSE pause
exit /b 1

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
