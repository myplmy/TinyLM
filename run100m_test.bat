@echo off
chcp 65001 > nul
echo =========================================
echo (1/4) ternary-LoRA r=32 시작
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --no-ckpt --lora-rank 32 --lora-bits 2 --tag t_lora32
if errorlevel 1 goto ERROR

echo =========================================
echo (2/4) FiLM 시작
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --no-ckpt --mlp-film --tag t_film
if errorlevel 1 goto ERROR

echo =========================================
echo (3/4) KD + 부모초기화 시작
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --init-from --kd --tag t_kdinit
if errorlevel 1 goto ERROR

echo =========================================
echo (4/4) 전부 결합 시작
echo =========================================
python run100m.py train --arch tied --data ko-en --tokens 300M --steps 2289 --micro-bs 8 --seq 1024 --accum 16 --lr 1e-3 --eval-every 100 --compile --init-from --kd --lora-rank 32 --lora-bits 2 --mlp-film --tag t_all
if errorlevel 1 goto ERROR

echo =========================================
echo 모든 학습이 성공적으로 완료되었습니다!
echo =========================================
pause
exit /b 0

:ERROR
echo [경고] 중단됨: 학습 과정에서 에러가 발생했습니다.
pause