@echo off
REM P052 stage 5  -  a third seed for the recursion ruler on the cla2 body.
REM   About 3.6 hours.
REM
REM   WHERE THE cla2 PAIR CAME FROM.  P052 stage 4 was supposed to give the
REM   cla1 arm a third seed and instead trained a cla2 model under a cla1 name
REM   (result 039 s11).  The run is not waste: mC_cla1_ag4_r20_s3 is really
REM   mC_cla2_ag4_r20 at seed 777, so the cla2 body now has TWO seeds -
REM   3.6889 and 3.6900, a gap of 0.0011 giving 2 sigma of about 0.0016.
REM
REM   WHY THE cla2 RULER MATTERS MORE THAN THE cla1 ONE NOW.  The cla2 body is
REM   the one inside the memory budget.  Result 065 put mC_cla2_ag4_r20 at
REM   30.3 MiB with bf16 KV, inside the 32 MiB optimum, and its recursion gain
REM   of -0.0172 is the number that justifies it.  That gain is judged against
REM   this ruler.  Two points is what 039 s9 called a systematic over-estimate
REM   in one direction and, as stage 4 showed, a possible under-estimate in
REM   the other.
REM
REM   INDEPENDENT VARIABLE: --seed 2024.  Everything else matches
REM   mC_cla2_ag4_r20 exactly, including --no-ckpt and --ce-chunk 2048.
REM   Note this arm is grad_ckpt FALSE while the cla1 seeds were TRUE - the
REM   match is to mC_cla2_ag4_r20, not to the cla1 line.
REM
REM   THE cla1 THIRD SEED IS A DIFFERENT BATCH (P052 stage 4b).  Both are
REM   needed; neither substitutes for the other.

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
timeout /t 15 /nobreak
echo.
python scripts\runlog.py --name P052_stage5_cla2_third_seed --note "[1/2] train - cla2 body, R=2.0, seed 2024"
python scripts\runlog.py --name P052_stage5_cla2_third_seed -- python run100m.py train --preset m100R1c --arch tied --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 2024 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --attn-group 4 --train-repeat 2.0 --init-from --tag mC_cla2_ag4_r20_s2
if errorlevel 1 echo [WARN] step failed - continuing
echo.
set TL_WB_TAG=mC_cla2_ag4_r20_s2
call scripts\batch\tool_wandb_push.bat
if errorlevel 1 echo [WARN] wandb push failed - continuing
set TL_WB_TAG=
echo.
python scripts\runlog.py --name P052_stage5_cla2_third_seed --note "[2/2] paired - all three cla2 recursion seeds together"
python scripts\runlog.py --name P052_stage5_cla2_third_seed -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_cla2_ag4_r20_s2 mC_cla2_ag4_r20 mC_cla1_ag4_r20_s3 mC_cla2_ag4 --match-train-repeat --dump-crops runs/logs/p052_cla2_seeds.json
if errorlevel 1 echo [WARN] step failed - continuing
echo.
python scripts\runlog.py --name P052_stage5_cla2_third_seed --note "READ IN THIS ORDER" "1. run check_tag_arch.py first. mC_cla1_ag4_r20_s3 will report as known" "   contamination - that is expected and registered. Anything NEW is not." "2. the three full-val values. Sample sigma over three points, then 2 sigma." "3. compare with the pair estimate 0.0016. If the ruler widens past 0.0086," "   the cla2 recursion gain of -0.0172 stops being 10x the ruler and the" "   30.3 MiB candidate loses its justification." "4. the fourth model is the R=1 base, so this run also re-prints the" "   recursion gain on the same crops." "5. seed-pair SE is about twice the architecture-pair SE. Read the ruler."
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
