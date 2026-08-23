@echo off
REM =============================================================================
REM  P046 stage 5  -  embedding rank 128 under the CURRENT standard, and on the
REM                   deployment model.  2 training runs plus eval, about 5.1 h
REM
REM  WHY THIS IS NOT A REPEAT
REM    mC_e128svd exists on disk but its json says kd = true. Every embedding
REM    rank number we have was measured under KD, which REVIEW2 then removed from
REM    the standard condition. The only no-KD point we own is E=192 (result 051,
REM    plus 0.0155). E=128 under the standard condition does not exist, and E on
REM    the 36 layer deployment model does not exist at all.
REM
REM  WHY IT MATTERS NOW
REM    REVIEW3 s1 says the LUT took the ternary term from 44.7 to 8.88 MiB and
REM    THE REMAINING TERM IS THE EMBEDDING (33.2 of 42.1 MiB). Result 016 s16
REM    then found the embedding accounting itself was false. P034 stage 5b
REM    re-measures the QUANTISATION side. This batch measures the RANK side,
REM    which is the only embedding lever that is trained rather than applied.
REM
REM  THE TWO ARMS ANSWER DIFFERENT QUESTIONS
REM    arm 1  mC_e128_nokd        does E=128 still cost what it cost under KD
REM    arm 2  mC_d36_ag4_e128     does that price hold on the deployment model
REM
REM  PREDICTIONS, fixed in advance
REM    C1  arm 1 lands between plus 0.020 and plus 0.045 versus mC_initonly
REM        3.6776. E=192 cost plus 0.0155 and the spectrum term is roughly
REM        0.0055 nats per percent of lost spectrum (result 030 s10).
REM    C2  arm 1 is NOT judged unusable. Result 030 was judged unusable because
REM        grad_max hit 19.32 with a randomly initialised embedding. --init-from
REM        now routes through _svd_emb_init. If grad_max is again over 10, the
REM        SVD transplant did not happen and that is the finding.
REM    C3  arm 2 costs MORE than arm 1 in nats. Convexity again (result 032 s8.3)
REM        - the 36 layer model already gave up its slack.
REM    C4  resident drops about 18.8 percent on the int8 path and only about 3.6
REM        on fp32 (result 032 s4.3, trap 24). REPORT BOTH OR NEITHER.
REM
REM  WHAT THIS CANNOT DECIDE
REM    Whether E=128 is adopted. That needs the P034 stage 5b quantisation number
REM    in the same table, because rank and quantisation multiply on the same term.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P046_stage5_emb_nokd --note "=============================================================================" "P046 stage 5   embedding rank 128 under the no-KD standard, twice" "Every E number we own was measured under KD, which is no longer standard." "The embedding is the largest remaining resident term (REVIEW3 s1)." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P046_stage5_emb_nokd --note "[1/4] mC_e128_nokd - one flag different from mC_initonly"
python scripts\runlog.py --name P046_stage5_emb_nokd -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --emb-rank 128 --init-from --tag mC_e128_nokd
if errorlevel 1 echo [WARN] mC_e128_nokd failed - continuing

python scripts\runlog.py --name P046_stage5_emb_nokd --note "[wandb] push arm 1"
set TL_WB_TAG=mC_e128_nokd
call scripts\batch\tool_wandb_push.bat

echo.
timeout /t 15 /nobreak

python scripts\runlog.py --name P046_stage5_emb_nokd --note "[2/4] mC_d36_ag4_e128 - the same flag on the deployment model, ckpt ON"
python scripts\runlog.py --name P046_stage5_emb_nokd -- python run100m.py train --preset m100R1d --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --attn-group 4 --ce-chunk 2048 --emb-rank 128 --init-from --tag mC_d36_ag4_e128
if errorlevel 1 echo [WARN] mC_d36_ag4_e128 failed - continuing

python scripts\runlog.py --name P046_stage5_emb_nokd --note "[wandb] push arm 2"
set TL_WB_TAG=mC_d36_ag4_e128
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P046_stage5_emb_nokd --note "[3/4] paired full-val - each arm against ITS OWN control"
python scripts\runlog.py --name P046_stage5_emb_nokd -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_e128_nokd mC_e192_nokd mC_initonly
if errorlevel 1 echo [WARN] paired eval 20 layer failed - continuing
python scripts\runlog.py --name P046_stage5_emb_nokd -- python scripts\paired_eval.py --preset m100R1d --data ko-en --tokens 300M --models mC_d36_ag4_e128 mC_d36_ag4_nokd
if errorlevel 1 echo [WARN] paired eval 36 layer failed - continuing

echo.
python scripts\runlog.py --name P046_stage5_emb_nokd --note "[4/4] residency on BOTH paths - trap 24 says the ranking flips"
python scripts\runlog.py --name P046_stage5_emb_nokd -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_e128_nokd mC_initonly --drop-latent
if errorlevel 1 echo [WARN] mem_runtime fp32 failed - continuing
python scripts\runlog.py --name P046_stage5_emb_nokd -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100R1c --models mC_e128_nokd mC_initonly --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime int8 failed - continuing

echo.
python scripts\runlog.py --name P046_stage5_emb_nokd --note "=============================================================================" "READ IN THIS ORDER" "1. json emb_rank must read 128 in both arms, and kd must read false." "2. grad_max FIRST, before any quality number. Result 030 died here (19.32)." "   Over 10 means the SVD transplant did not happen (C2) and the delta is NOT" "   a rank measurement - do not write it into the lever table." "3. step0 ce. Near ln V = 10.397 means the embedding started random, which is" "   exactly the 030 failure mode. The band is 5.0 to 9.3972." "4. paired deltas against C1 and C3. Ruler 2 sigma = 0.0034." "5. step [4] prints fp32 AND int8 residency. Quote BOTH (trap 24, C4). The" "   lever ranking is different on the two deployment paths." "!! arm 1 and arm 2 have DIFFERENT controls and DIFFERENT presets. Do not put" "   their deltas in one column without saying which control each used." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
