@echo off
REM =============================================================================
REM  P057 stage 1  -  attention tying on the depth axis   (about 3.3 hours)
REM                   preset m100R1d, attn_group 2, tag mC_d36_ag2
REM
REM  WHY THIS COMBINATION
REM    P049 stage 1 bought -0.0250 with 36 layers but paid +35.9 percent
REM    residency, and the pre-fixed threshold was -0.075. So it closed.
REM    Two later measurements say the money went to the wrong place:
REM      result 041 s15  the DUPLICATED layers' attention gates SHRANK 49.5
REM                      percent from the transplanted value while the MLP
REM                      gates GREW 43.8 percent. The attention we paid for
REM                      turned itself off.
REM      result 044 s7   36 layers with attn_group 2 has step0 CE 5.6449,
REM                      identical to the no-tying anchor to four decimals.
REM    Sharing something that switches itself off should be nearly free, and
REM    two independent measurements say it is.
REM
REM  ARITHMETIC (computed; report() checks it at runtime)
REM    mC_wsd   54.85M ternary   451.5 MiB residency   packed 13.050 MB
REM    mC_d36   76.10M           613.7      (+35.9 pct)
REM    this run about 57.2M      about 469.6 (+4.0 pct vs the 20 layer baseline)
REM
REM  !! ADOPTION THRESHOLD, FIXED IN ADVANCE
REM    P049's -0.075 was derived from "does it justify +35.9 percent residency".
REM    At +4.0 percent that derivation gives a different number. Using the same
REM    exchange rate (result 032 s8: about 0.0044 nats per unique-ternary
REM    million, subtracting direction):
REM        2.38M more unique ternary than mC_wsd gives about -0.010
REM    So: BETTER THAN -0.010 versus mC_wsd = the combination pays for itself.
REM    Between -0.010 and 0 = better but not worth it, same verdict as P049.
REM    Above 0 = the attention averaging broke something. Read result 041 s15
REM    again before concluding.
REM
REM  !! KD IS ON, deliberately
REM    mC_d36 ran with --kd --kd-every 4. Keeping it makes this comparable to
REM    that run. If REVIEW2 removes KD from the standard condition, this run
REM    still compares correctly against mC_d36 and mC_wsd, which are both KD.
REM
REM  !! WATCH
REM    [attn] line saying 32 middle layers share 16 attentions
REM    the [init] P057 group-average lines, 16 of them
REM    report() ternary near 57.2M - if it says 76.1M the flag did nothing
REM    grad_max from json, not the printed abs-g
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
echo.
python scripts\runlog.py --name P057_stage1_d36ag2 --note "=============================================================================" "P057 stage 1   36 layers + attn_group 2   about 3.3 hours   -   tag mC_d36_ag2" "Threshold fixed in advance: better than -0.010 versus mC_wsd." "References: mC_wsd 3.6984 / mC_d36 3.6734 / mC_g16 3.7145" "============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P057_stage1_d36ag2 --note "[P057 stage 1] m100R1d 2+32+2 g16 with attn_group 2, gate_scale transplant, KD k4. Attention 32 modules become 16."

python scripts\runlog.py --name P057_stage1_d36ag2 -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --init-from --kd --kd-every 4 --depth-init gate_scale --attn-group 2 --tag mC_d36_ag2
if errorlevel 1 goto TRAINBAD

echo.
echo.
python scripts\runlog.py --name P057_stage1_d36ag2 --note "[queue] settling 15 s before the evaluation process starts"
timeout /t 15 /nobreak

python scripts\runlog.py --name P057_stage1_d36ag2 -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_wsd mC_d36 mC_d36_ag2
if errorlevel 1 echo [WARN] paired_eval returned an error - the training run is still valid

echo.
echo.
python scripts\runlog.py --name P057_stage1_d36ag2 -- python scripts\diag_layer_gates.py --tag mC_d36_ag2 --preset m100R1d --teacher-preset m100
if errorlevel 1 echo [WARN] gate probe failed - the training run is still valid

echo.
echo.
python scripts\runlog.py --name P057_stage1_d36ag2 --note "=============================================================================" "READ IN THIS ORDER" "1. report() ternary. About 57.2M, not 76.1M. If 76.1M the flag did nothing." "2. json attn_group = 2 and n_layers = 36." "3. grad_max under 10, else no judgement is possible (result 030)." "4. paired mC_d36_ag2 versus mC_wsd against the fixed line of -0.010." "5. paired versus mC_d36 - did halving the attention cost anything at all?" "6. the gate probe - do the duplicated layers still switch attention off when" "   the attention is SHARED? That is a different question and it is open." "REMINDER: residency is the point. Quote report()'s runtime number, and say" "fp32 or int8 when you do (trap 24)." "============================================================================="
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
