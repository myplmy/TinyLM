@echo off
REM ===== P012 Korean data efficiency: ko-en (raw wiki) vs ko-edu-en (curated) =====
REM Primary metric = bpb (bits-per-byte), which is tokenizer-invariant -> valid cross-dataset.
REM ko-en dense baseline is assumed to already exist (reused). This builds+trains the curated side.
REM NOTE: each dataset trains its own tokenizer; compare bpb (NOT raw val_loss) across the two logs.

echo [1/3] Build curated cache (first run tokenizes eliceai/korean-webtext-edu + fineweb-edu)
python run100m.py prepare --data ko-edu-en --tokens 300M
if errorlevel 1 goto ERROR

echo [2/3] Train dense on curated ko-edu-en (300M, same budget as ko-en dense)
python run100m.py train --arch dense --data ko-edu-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile
if errorlevel 1 goto ERROR

echo [3/3] (optional) Train tied+KD on curated data to see if gains carry to tied
REM python run100m.py train --arch tied --data ko-edu-en --tokens 300M --steps 2289 --micro-bs 8 --accum 16 --lr 1e-3 --compile --kd --init-from --mlp-group 8 --tag t_kd_g8

echo ================================================================
echo COMPARE bpb (lower=better) between the two dense logs:
echo   runs\logs\m100_ko-en_300M_dense.json      (final.bpb)
echo   runs\logs\m100_ko-edu-en_300M_dense.json  (final.bpb)
echo Curated wins if its bpb is lower at the same 300M tokens.
echo ================================================================
echo done.
pause
exit /b 0

:ERROR
echo [WARN] stopped: error during run.
pause
