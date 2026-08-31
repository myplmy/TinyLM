@echo off
REM P052 stage 4b  -  a third seed for the recursion ruler.  RETRY.
REM
REM   WHY THIS IS 4b AND NOT 4.  Stage 4 ran for 3.6 hours and produced a
REM   checkpoint of the WRONG ARCHITECTURE.  The command line omitted
REM   --cla-group 1, and the m100R1c preset defaults cla_group to 2, so what
REM   trained was a cla2 model wearing a cla1 name (result 039 s11).
REM
REM     seeds 1 and 2 : cla_group 1, kv_entries 36, params 48,755,496, ce_chunk 2048
REM     the "seed 3"  : cla_group 2, kv_entries 18, params 48,165,672, ce_chunk 0
REM
REM   The header of that batch even said "everything else matches
REM   mC_cla1_ag4_r20".  It did not.  A new static gate, check_tag_arch.py,
REM   now compares what a tag CLAIMS against what the json RECORDS.
REM
REM   INDEPENDENT VARIABLE: --seed 777.  Everything else matches
REM   mC_cla1_ag4_r20 - and this time the two flags that were missing are here.
REM   The confound must match too: that arm ran with grad checkpointing ON,
REM   so this one does as well.  Do NOT add --no-ckpt here.
REM
REM   RULER: recursion 2 sigma is 0.0006 from the cla1 pair and 0.0016 from the
REM   accidental cla2 pair.  Three points on cla1 is what this run buys.
REM
REM   PREDICTION: the third value lands within 0.0010 of 3.6748.  If it lands
REM   far away, the ruler really does widen and every recursion judgement gets
REM   re-read - but this time we will know it is the same model.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P052_stage4b_recursion_third_seed --note "[1/2] train - seed 777, cla_group 1 EXPLICIT"
python scripts\runlog.py --name P052_stage4b_recursion_third_seed -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 777 --eval-every 100 --compile --ce-chunk 2048 --cla-group 1 --attn-group 4 --train-repeat 2.0 --init-from --tag mC_cla1_ag4_r20_s3b
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=mC_cla1_ag4_r20_s3b
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P052_stage4b_recursion_third_seed --note "[2/2] paired against the other two seeds"
python scripts\runlog.py --name P052_stage4b_recursion_third_seed -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla1_ag4_r20_s3b mC_cla1_ag4_r20 mC_cla1_ag4_r20_s2 --match-train-repeat --dump-crops runs/logs/p052_cla1_seeds.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P052_stage4b_recursion_third_seed --note "READ IN THIS ORDER" "1. BEFORE anything else, run check_tag_arch.py. If it reports a new" "   contamination, this run is void and nothing below means anything." "2. the three full-val values. Sample sigma over three points, then 2 sigma." "3. compare that to the pair-based 0.0006. If the new ruler is LARGER," "   re-read 039 s10: 20 to 28 visits was -0.0036, which stays significant" "   only while 2 sigma is under 0.0018." "4. seed-pair SE is about 0.0013, twice the architecture-pair SE. Read the" "   ruler, not the t statistic (039 s9.4)." "5. crops are dumped so paired_join can test gain replication for P078."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
