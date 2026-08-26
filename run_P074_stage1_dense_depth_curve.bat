@echo off
REM =============================================================================
REM  P074 stage 1  -  the counterfactual we never ran: SHALLOW DENSE
REM                   4 training runs plus paired eval and residency, about 3.8 h
REM
REM  THE QUESTION  (user, 2026-08-26)
REM    Our whole thesis is "tying reduces resident memory". But every comparison
REM    we have made is against ourselves at the same depth. Nobody ever asked:
REM        what if you just made the model SHALLOWER instead?
REM    Tied 20 layers at mlp_group 8 sits at 451.5 MiB resident. A dense model
REM    with 9 layers lands at about 458. Those are the same number. We do not
REM    know which one is better.
REM
REM  !! IF TIED LOSES, THE PROGRAM LOSES ITS PREMISE
REM    That is the point of running it. A negative result here is worth more
REM    than another lever measurement.
REM
REM  WHAT THE FOUR ARMS ARE
REM    d6_dense   m100s2   6 layers  (2+2+2)   about 317 MiB resident
REM    d8_dense   m100s4   8 layers  (2+4+2)   about 411
REM    d10_dense  m100s6  10 layers  (2+6+2)   about 505
REM    d12_dense  m100s8  12 layers  (2+8+2)   about 600
REM    Four points make a curve. The tied models already on disk get plotted on
REM    the same axes, and "who wins at equal memory" is read by interpolation.
REM    We do NOT bend the layer count to hit a target - integers do not allow it.
REM
REM  !! THE TRANSPLANT IS THE RISK, NOT THE TRAINING
REM    These students are SHALLOWER than the parent. _depth_map handles both
REM    directions but init_utils line 116 says the shallow direction must be
REM    asked for explicitly with --depth-init role. That option has never been
REM    measured - result 041 section 13 only priced prop, gate_scale and
REM    identity. Step [1] is a step0 gate for exactly this reason.
REM    !! diag_depth_init.py has no --depth-init flag of its own; it reports the
REM       step0 anchor for the student/teacher pair, which is what the gate
REM       needs. The role choice is exercised by the training arms themselves.
REM
REM  PREDICTIONS, fixed in advance
REM    N1  the dense curve is convex in resident memory - getting shallower
REM        hurts faster than linearly.
REM    N2  at equal resident, tied 20 layers BEATS dense 9. If it does not, the
REM        tying program needs a new justification.
REM    N3  the margin is 0.02 to 0.10 nats. Under that, tying and shallowness
REM        are practically the same trade.
REM    N4  mC_d36_ag4_nokd (379.7) beats d8_dense (about 411) on BOTH axes.
REM        That is the REVIEW3 plan B premise stated as a falsifiable claim.
REM    N5  dense is much faster per step. The real price of tying is TIME, not
REM        memory, and this table shows it for the first time.
REM
REM  !! CONFOUND WE CANNOT REMOVE HERE
REM    dense_baseline() forces cla_group 1; the tied models run cla_group 2.
REM    Result 058 measured that gap at 0.0268 (20 layers) and 0.0136 (36 layers).
REM    Subtract it when reading N2 - do not pretend it is not there.
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "=============================================================================" "P074 stage 1   shallow dense - the counterfactual we never ran" "Tied 20 layers and dense 9 layers cost the same resident memory." "Nobody has ever asked which one is better. About 3.8 hours." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[1/6] GATE - does the shallow transplant work at all. step0 must land in 5.0 to 9.3972"
python scripts\runlog.py --name P074_stage1_dense_depth_curve -- python scripts\diag_depth_init.py --preset m100s4 --teacher-preset m100
if errorlevel 1 echo [WARN] depth gate failed - READ IT before trusting any arm below

echo.
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[2/6] d6_dense - 6 layers, the shallow end"
python scripts\runlog.py --name P074_stage1_dense_depth_curve -- python run100m.py train --preset m100s2 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d6_dense
if errorlevel 1 echo [WARN] d6_dense failed - continuing
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[wandb] push d6_dense"
set TL_WB_TAG=d6_dense
call scripts\batch\tool_wandb_push.bat

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[3/6] d8_dense - the arm that brackets mC_d36_ag4_nokd"
python scripts\runlog.py --name P074_stage1_dense_depth_curve -- python run100m.py train --preset m100s4 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d8_dense
if errorlevel 1 echo [WARN] d8_dense failed - continuing
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[wandb] push d8_dense"
set TL_WB_TAG=d8_dense
call scripts\batch\tool_wandb_push.bat

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[4/6] d10_dense - the arm that brackets mC_initonly"
python scripts\runlog.py --name P074_stage1_dense_depth_curve -- python run100m.py train --preset m100s6 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d10_dense
if errorlevel 1 echo [WARN] d10_dense failed - continuing
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[wandb] push d10_dense"
set TL_WB_TAG=d10_dense
call scripts\batch\tool_wandb_push.bat

echo.
timeout /t 15 /nobreak
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[5/6] d12_dense - the deep end of the curve"
python scripts\runlog.py --name P074_stage1_dense_depth_curve -- python run100m.py train --preset m100s8 --arch dense --data ko-en --tokens 300M --pool-tokens 600M --exact-cache --steps 2289 --micro-bs 8 --accum 16 --seq 1024 --lr 1e-3 --sched wsd --anneal-end 0.80 --decay-frac 0.2 --seed 1337 --eval-every 100 --compile --no-ckpt --ce-chunk 2048 --init-from --depth-init role --tag d12_dense
if errorlevel 1 echo [WARN] d12_dense failed - continuing
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[wandb] push d12_dense"
set TL_WB_TAG=d12_dense
call scripts\batch\tool_wandb_push.bat

echo.
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "[6/6] residency for all four - the x axis of the whole plot"
python scripts\runlog.py --name P074_stage1_dense_depth_curve -- python scripts\mem_runtime.py --device cpu --max-new 32 --preset m100s4 --models d6_dense d8_dense d10_dense d12_dense --drop-latent --int8-store
if errorlevel 1 echo [WARN] mem_runtime failed - continuing

echo.
python scripts\runlog.py --name P074_stage1_dense_depth_curve --note "=============================================================================" "READ IN THIS ORDER" "1. step [1] and every arm's step0 ce. Band is 5.0 to 9.3972. Outside it the" "   role transplant failed and that arm measured transplant, not depth." "2. grad_max under 10 on all four. Shallow dense has a different LR optimum" "   and we did NOT redo lrfind - result 017 says batch changes move it." "3. json n_layers must read 6, 8, 10, 12. If any reads 20 the preset did not" "   land and that arm is a reseed of p6d." "4. plot the four against mC_initonly (451.5 / 3.6776) and mC_d36_ag4_nokd" "   (379.7 / 3.6848). N2 says tied wins at equal resident." "5. SUBTRACT the CLA confound before judging N2 - dense runs cla_group 1 and" "   tied runs 2. Result 058 puts that at 0.0268 at 20 layers." "IF TIED WINS  the program premise holds and we can finally say so with a" "  counterfactual instead of an assumption." "IF DENSE WINS AT EQUAL MEMORY  stop and read REVIEW3 again from the top." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
