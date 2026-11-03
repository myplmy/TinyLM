# 정확 고정 reader 명령 TASK_059

총괄이 만든 자기역할 readonly 도구만 실행한다. source-id와packet외의경로나코드를만들지않는다.
이 tool은 실제원문/후보/diff만출력하며 코드실행/해시계산권한이아니다. 출력예산8000이상,piece는1이다.
동일증명ID는원문전문실제판독+후보동일연결+최종diff끝을확인하고,다른후보는모든packet을읽는다.
아래중복후보의생략앞뒤를연속후보전문으로합치지않는다. 도구잘림은동일정확명령으로재판독한다.

## expanded_train:757315
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 7 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 8 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 9 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 10 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 11 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 12 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 13 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 14 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 15 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 16 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 17 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 18 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 19 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 20 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 21 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 22 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 23 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 24 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 25 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 26 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 27 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 28 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 29 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 30 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 31 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 32 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 33 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 34 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 35 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 36 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 37 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 38 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 39 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 40 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 41 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 42 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 43 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 44 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 45 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 46 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 47 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 48 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 49 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 50 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 51 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 52 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 53 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 54 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 55 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 56 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 57 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 58 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 59 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:757315 --packet 118 --piece 1
```

## expanded_train:768125
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:768125 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:768125 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:768125 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:768125 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:768125 --packet 8 --piece 1
```

## expanded_train:772762
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:772762 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:772762 --packet 2 --piece 1
```

## expanded_train:777834
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 7 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 8 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 9 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 10 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 11 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 12 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 13 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 14 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 15 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 16 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 17 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 18 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 19 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 20 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 21 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 22 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 43 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:777834 --packet 44 --piece 1
```

## expanded_train:784667
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:784667 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_historical_review_literal_packet_v2.py --source-id expanded_train:784667 --packet 2 --piece 1
```

