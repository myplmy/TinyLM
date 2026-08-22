@echo off
REM =============================================================================
REM  P062 stage 2b  -  evaluate the inplace checkpoint that stage 2 could not load
REM                    evaluation only, about 5 minutes. NO training.
REM
REM  WHAT HAPPENED IN STAGE 2  (result 047 s stage2)
REM    The 2.8 hour training run SUCCEEDED. mC_r20in_nokd exists on disk.
REM    Then every evaluation died:
REM        config.py __post_init__ assert listed only three modes and
REM        AssertionError from config.py: repeat_mode got 'inplace' but the
REM
REM  !! WHY TRAINING PASSED AND EVALUATION DID NOT
REM    build_config constructs TMTConfig, and THEN trainer assigns
REM    cfg.repeat_mode = "inplace". __post_init__ has already run, so the assert
REM    never sees it. load_model rebuilds with TMTConfig(**st["cfg"]) and the
REM    assert fires - 2.8 hours later.
REM    This is trap 18: the set of valid modes lived in THREE places (cli
REM    choices, transformer._repeat_schedule, config assert) and I updated two.
REM    Fixed: config.REPEAT_MODES is now the single source and all three import it.
REM
REM  !! NOTHING NEEDS RETRAINING
REM    The checkpoint is fine. Only the loader was wrong.
REM
REM  GATES from the original plan
REM    T1  mC_r20in_nokd at even lands within 0.010 of mC_r20_nokd at front
REM    T2  the old +0.0992 gap collapses once training matches
REM    T3  memory identical
REM =============================================================================

if not exist run100m.py cd ..\..
if not exist run100m.py goto BADROOT

echo.
python scripts\runlog.py --name P062_stage2b_inplace_eval --note "=============================================================================" "P062 stage 2b   evaluate the inplace checkpoint   NO training" "Stage 2 trained fine and then could not be loaded - config.REPEAT_MODES did" "not know about inplace. Trap 18. The checkpoint was never the problem." "=============================================================================="
echo.
if not defined TL_NOPAUSE pause

python scripts\runlog.py --name P062_stage2b_inplace_eval --note "[1/2] paired full-val - EACH model at its own trained function"
python scripts\runlog.py --name P062_stage2b_inplace_eval -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20_nokd mC_r20in_nokd mC_initonly --match-train-repeat
if errorlevel 1 echo [WARN] paired eval failed - continuing

echo.
python scripts\runlog.py --name P062_stage2b_inplace_eval --note "[2/2] control - both checkpoints forced onto where=even, to size trap 39"
python scripts\runlog.py --name P062_stage2b_inplace_eval -- python scripts\paired_eval.py --preset m100R1c --data ko-en --tokens 300M --models mC_r20_nokd mC_r20in_nokd --infer-repeat 2.0 --repeat-where even
if errorlevel 1 echo [WARN] control eval failed - continuing

echo.
python scripts\runlog.py --name P062_stage2b_inplace_eval --note "=============================================================================" "READ IN THIS ORDER" "1. that both models LOAD. That alone proves the REPEAT_MODES fix." "2. step [1] mC_r20in_nokd against mC_r20_nokd. Ruler is 2 sigma = 0.0034." "   within 0.010  means the order axis is closed and P070 does not start." "   beyond        means order is a real axis and P070 is worth its 50 lines." "3. step [2] sizes how much of result 047's +0.0992 was pure schedule" "   mismatch rather than a property of even." "!! The training log val for mC_r20in_nokd is 3.9641, but that is the value" "   under its OWN training schedule and is NOT comparable to 3.6573 directly." "   Only step [1] is comparable - that is what --match-train-repeat is for." "=============================================================================="
if not defined TL_NOPAUSE pause
exit /b 0

:BADROOT
echo [STOP] could not locate the repo root - run this from the TinyLM folder
if not defined TL_NOPAUSE pause
exit /b 1
