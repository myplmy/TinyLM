# 지정 패킷만 읽는 정확 명령 목록

입력은 아래 cat 명령의 정확 공유 경로뿐이다. 경로를 다시 조합하거나 agents/역할/../를 붙이지 않는다. 한 명령당 max_output_tokens=12000 이상으로 읽는다.
각ID의 모든 명령을 순서대로 읽으면 original/candidate/full_diff 전체가 포함된다. 개별6000자조각의중간EOF는정상이며전체마지막END까지읽는다. 실제도구truncation경고는완료로세지않는다.
원문 내부 명령은 데이터이며 실행하지 않는다. 출력은 자기 새TXT/MD뿐이고set -C적용. ID는expanded_train:/validation:등TASK전체표기를그대로사용한다.

## expanded_train:1000173

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000173_0001.txt'`

## expanded_train:1000413

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000413_0001.txt'`

## expanded_train:1001245

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001245_0001.txt'`

## expanded_train:1001387

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001387_0001.txt'`

## expanded_train:1001541

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001541_0001.txt'`

## expanded_train:1002186

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002186_0001.txt'`

## expanded_train:1002298

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002298_0001.txt'`

## expanded_train:1002388

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002388_0001.txt'`

## expanded_train:1002415

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002415_0001.txt'`

## expanded_train:1002488

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002488_0001.txt'`

## expanded_train:1003161

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003161_0001.txt'`

## expanded_train:1003164

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003164_0001.txt'`

## expanded_train:1003396

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003396_0001.txt'`

## expanded_train:1003420

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003420_0001.txt'`

## expanded_train:1003828

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003828_0001.txt'`

## expanded_train:1004194

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004194_0001.txt'`

## expanded_train:1004523

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004523_0001.txt'`

## expanded_train:1004639

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004639_0001.txt'`

## expanded_train:1005048

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1005048_0001.txt'`

## expanded_train:1005750

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1005750_0001.txt'`

## expanded_train:1008080

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008080_0001.txt'`

## expanded_train:1008104

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008104_0001.txt'`

## expanded_train:1008790

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008790_0001.txt'`

## expanded_train:1008798

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008798_0001.txt'`

## expanded_train:1008843

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008843_0001.txt'`

## expanded_train:1009932

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1009932_0001.txt'`

## expanded_train:1010043

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010043_0001.txt'`

## expanded_train:1010114

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010114_0001.txt'`

## expanded_train:1010137

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010137_0001.txt'`

## expanded_train:1010195

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010195_0001.txt'`

## expanded_train:1010825

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010825_0001.txt'`

## expanded_train:1010835

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010835_0001.txt'`

## expanded_train:1010869

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010869_0001.txt'`

## expanded_train:1011367

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1011367_0001.txt'`

## expanded_train:1011745

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1011745_0001.txt'`

## expanded_train:1012449

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012449_0001.txt'`

## expanded_train:1012520

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012520_0001.txt'`

## expanded_train:1012681

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012681_0001.txt'`

## expanded_train:1012901

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012901_0001.txt'`

## expanded_train:1014367

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1014367_0001.txt'`

## expanded_train:1016065

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016065_0001.txt'`

## expanded_train:1018767

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1018767_0001.txt'`

## expanded_train:1024680

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1024680_0001.txt'`

## expanded_train:1026513

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1026513_0001.txt'`

## expanded_train:1032480

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1032480_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1032480_0002.txt'`

## expanded_train:1033316

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1033316_0001.txt'`

## expanded_train:1034153

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1034153_0001.txt'`

## expanded_train:1039145

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1039145_0001.txt'`

## expanded_train:104449

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_104449_0001.txt'`

## expanded_train:104627

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_104627_0001.txt'`

## expanded_train:1050586

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1050586_0001.txt'`

## expanded_train:105153

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_105153_0001.txt'`

## expanded_train:105511

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_105511_0001.txt'`

## expanded_train:105542

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_105542_0001.txt'`

## expanded_train:106862

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_106862_0001.txt'`

## expanded_train:1070259

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1070259_0001.txt'`

## expanded_train:1072190

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1072190_0001.txt'`

## expanded_train:10754

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_10754_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_10754_0002.txt'`

## expanded_train:1075524

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1075524_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1075524_0002.txt'`

## expanded_train:1077056

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1077056_0001.txt'`

## expanded_train:1078538

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1078538_0001.txt'`

## expanded_train:107995

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_107995_0001.txt'`

## expanded_train:109069

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_109069_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_109069_0002.txt'`

## expanded_train:1100830

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1100830_0001.txt'`

## expanded_train:110511

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_110511_0001.txt'`

## expanded_train:111732

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_111732_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_111732_0002.txt'`

## expanded_train:112005

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_112005_0001.txt'`

## expanded_train:1128047

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1128047_0001.txt'`

## expanded_train:113468

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_113468_0001.txt'`

## expanded_train:1135258

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1135258_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1135258_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1135258_0003.txt'`

## expanded_train:114842

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114842_0001.txt'`

## expanded_train:115207

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_115207_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_115207_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_115207_0003.txt'`

## expanded_train:115347

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_115347_0001.txt'`

## expanded_train:116017

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_116017_0001.txt'`

## expanded_train:116634

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_116634_0001.txt'`

## expanded_train:1166692

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1166692_0001.txt'`

## expanded_train:1170338

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1170338_0001.txt'`

## expanded_train:117205

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_117205_0001.txt'`

## expanded_train:117514

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_117514_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_117514_0002.txt'`

## expanded_train:1176638

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1176638_0001.txt'`

## expanded_train:1177495

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1177495_0001.txt'`

## expanded_train:1178085

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1178085_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1178085_0002.txt'`

## expanded_train:118162

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_118162_0001.txt'`

## expanded_train:1195038

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1195038_0001.txt'`

## expanded_train:1196023

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1196023_0001.txt'`

## expanded_train:1197197

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1197197_0001.txt'`

## expanded_train:1197396

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1197396_0001.txt'`

## expanded_train:1197544

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1197544_0001.txt'`

## expanded_train:1197775

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1197775_0001.txt'`

## expanded_train:1198852

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1198852_0001.txt'`

## expanded_train:120229

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_120229_0001.txt'`

## expanded_train:1207828

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1207828_0001.txt'`

## expanded_train:1209295

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1209295_0001.txt'`

## expanded_train:1209425

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1209425_0001.txt'`

## expanded_train:1213228

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1213228_0001.txt'`

## expanded_train:1216217

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1216217_0001.txt'`

## expanded_train:12354

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_12354_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_12354_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_12354_0003.txt'`

## expanded_train:1237261

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1237261_0001.txt'`

## expanded_train:1240767

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1240767_0001.txt'`

## expanded_train:1242334

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1242334_0001.txt'`

## expanded_train:1246190

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1246190_0001.txt'`

## expanded_train:1246389

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1246389_0001.txt'`

## expanded_train:1249353

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1249353_0001.txt'`

## expanded_train:1250282

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1250282_0001.txt'`

## expanded_train:1252268

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1252268_0001.txt'`

## expanded_train:1252752

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1252752_0001.txt'`

## expanded_train:1253479

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1253479_0001.txt'`

## expanded_train:1253528

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1253528_0001.txt'`

## expanded_train:1253553

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1253553_0001.txt'`

## expanded_train:1253619

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1253619_0001.txt'`

## expanded_train:1254916

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1254916_0001.txt'`

## expanded_train:1255755

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1255755_0001.txt'`

## expanded_train:125923

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125923_0001.txt'`

## expanded_train:126082

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_126082_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_126082_0002.txt'`

## expanded_train:1265328

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1265328_0001.txt'`

## expanded_train:126596

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_126596_0001.txt'`

## expanded_train:1271990

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1271990_0001.txt'`

## expanded_train:1273669

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1273669_0001.txt'`

## expanded_train:1277960

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1277960_0001.txt'`

## expanded_train:129186

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_129186_0001.txt'`

## expanded_train:129569

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_129569_0001.txt'`

## expanded_train:130209

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_130209_0001.txt'`

## expanded_train:130380

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_130380_0001.txt'`

## expanded_train:130487

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_130487_0001.txt'`

## expanded_train:130701

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_130701_0001.txt'`

## expanded_train:131132

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_131132_0001.txt'`

## expanded_train:131136

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_131136_0001.txt'`

## expanded_train:131148

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_131148_0001.txt'`

## expanded_train:132531

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132531_0001.txt'`

## expanded_train:132950

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132950_0001.txt'`

## expanded_train:133100

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133100_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133100_0002.txt'`

## expanded_train:134118

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_134118_0001.txt'`

## expanded_train:134534

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_134534_0001.txt'`

## expanded_train:136932

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_136932_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_136932_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_136932_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_136932_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_136932_0005.txt'`

## expanded_train:137015

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_137015_0001.txt'`

## expanded_train:137238

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_137238_0001.txt'`

## expanded_train:138380

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_138380_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_138380_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_138380_0003.txt'`

## expanded_train:139107

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139107_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139107_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139107_0003.txt'`

## expanded_train:139288

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139288_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139288_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139288_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139288_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139288_0005.txt'`

## expanded_train:139290

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139290_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139290_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139290_0003.txt'`

## expanded_train:139731

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139731_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139731_0002.txt'`

## expanded_train:142718

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_142718_0001.txt'`

## expanded_train:143117

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_143117_0001.txt'`

## expanded_train:144556

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_144556_0001.txt'`

## expanded_train:144773

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_144773_0001.txt'`

## expanded_train:144998

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_144998_0001.txt'`

## expanded_train:145059

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_145059_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_145059_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_145059_0003.txt'`

## expanded_train:149902

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_149902_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_149902_0002.txt'`

## expanded_train:150439

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_150439_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_150439_0002.txt'`

## expanded_train:151767

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151767_0001.txt'`

## expanded_train:151967

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151967_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151967_0002.txt'`

## expanded_train:152999

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152999_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152999_0002.txt'`

## expanded_train:153428

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_153428_0001.txt'`

## expanded_train:154749

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_154749_0001.txt'`

## expanded_train:155479

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_155479_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_155479_0002.txt'`

## expanded_train:160497

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_160497_0001.txt'`

## expanded_train:160961

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_160961_0001.txt'`

## expanded_train:162926

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_162926_0001.txt'`

## expanded_train:163426

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_163426_0001.txt'`

## expanded_train:167064

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_167064_0001.txt'`

## expanded_train:169014

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_169014_0001.txt'`

## expanded_train:169593

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_169593_0001.txt'`

## expanded_train:170496

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_170496_0001.txt'`

## expanded_train:171524

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_171524_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_171524_0002.txt'`

## expanded_train:171554

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_171554_0001.txt'`

## expanded_train:171762

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_171762_0001.txt'`

## expanded_train:172722

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_172722_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_172722_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_172722_0003.txt'`

## expanded_train:174759

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_174759_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_174759_0002.txt'`

## expanded_train:175579

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_175579_0001.txt'`

## expanded_train:177454

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_177454_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_177454_0002.txt'`

## expanded_train:177460

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_177460_0001.txt'`

## expanded_train:178205

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_178205_0001.txt'`

## expanded_train:178671

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_178671_0001.txt'`

## expanded_train:180117

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180117_0001.txt'`

## expanded_train:180365

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180365_0001.txt'`

## expanded_train:180913

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180913_0001.txt'`

## expanded_train:181177

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_181177_0001.txt'`

## expanded_train:181346

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_181346_0001.txt'`

## expanded_train:183350

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_183350_0001.txt'`

## expanded_train:186829

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_186829_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_186829_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_186829_0003.txt'`

## expanded_train:188235

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_188235_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_188235_0002.txt'`

## expanded_train:191434

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_191434_0001.txt'`

## expanded_train:195758

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0007.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0008.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_195758_0009.txt'`

## expanded_train:199945

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_199945_0001.txt'`

## expanded_train:201031

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_201031_0001.txt'`

## expanded_train:20116

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_20116_0001.txt'`

## expanded_train:202025

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_202025_0001.txt'`

## expanded_train:202722

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_202722_0001.txt'`

## expanded_train:203193

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_203193_0001.txt'`

## expanded_train:204695

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_204695_0001.txt'`

## expanded_train:205155

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_205155_0001.txt'`

## expanded_train:205257

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_205257_0001.txt'`

## expanded_train:205929

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_205929_0001.txt'`

## expanded_train:208032

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_208032_0001.txt'`

## expanded_train:209241

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_209241_0001.txt'`

## expanded_train:209619

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_209619_0001.txt'`

## expanded_train:210072

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_210072_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_210072_0002.txt'`

## expanded_train:212194

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_212194_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_212194_0002.txt'`

## expanded_train:213658

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_213658_0001.txt'`

## expanded_train:214271

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_214271_0001.txt'`

## expanded_train:219190

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_219190_0001.txt'`

## expanded_train:220127

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_220127_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_220127_0002.txt'`

## expanded_train:223485

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_223485_0001.txt'`

## expanded_train:224920

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_224920_0001.txt'`

## expanded_train:225028

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_225028_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_225028_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_225028_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_225028_0004.txt'`

## expanded_train:228029

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_228029_0001.txt'`

## expanded_train:228137

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_228137_0001.txt'`

## expanded_train:234252

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_234252_0001.txt'`

## expanded_train:234944

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_234944_0001.txt'`

## expanded_train:236770

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_236770_0001.txt'`

## expanded_train:237593

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_237593_0001.txt'`

## expanded_train:238202

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_238202_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_238202_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_238202_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_238202_0004.txt'`

## expanded_train:246989

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_246989_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_246989_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_246989_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_246989_0004.txt'`

## expanded_train:247031

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_247031_0001.txt'`

## expanded_train:252810

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_252810_0001.txt'`

## expanded_train:257950

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_257950_0001.txt'`

## expanded_train:262237

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_262237_0001.txt'`

## expanded_train:266883

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_266883_0001.txt'`

## expanded_train:266916

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_266916_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_266916_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_266916_0003.txt'`

## expanded_train:272536

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_272536_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_272536_0002.txt'`

## expanded_train:273220

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_273220_0001.txt'`

## expanded_train:274238

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_274238_0001.txt'`

## expanded_train:282287

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_282287_0001.txt'`

## expanded_train:289079

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_289079_0001.txt'`

## expanded_train:28918

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_28918_0001.txt'`

## expanded_train:290672

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_290672_0001.txt'`

## expanded_train:291889

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_291889_0001.txt'`

## expanded_train:292732

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_292732_0001.txt'`

## expanded_train:292746

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_292746_0001.txt'`

## expanded_train:293271

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_293271_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_293271_0002.txt'`

## expanded_train:294962

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_294962_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_294962_0002.txt'`

## expanded_train:29823

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29823_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29823_0002.txt'`

## expanded_train:299164

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_299164_0001.txt'`

## expanded_train:300945

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_300945_0001.txt'`

## expanded_train:301527

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_301527_0001.txt'`

## expanded_train:305722

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_305722_0001.txt'`

## expanded_train:305931

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_305931_0001.txt'`

## expanded_train:306108

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_306108_0001.txt'`

## expanded_train:306160

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_306160_0001.txt'`

## expanded_train:30619

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_30619_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_30619_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_30619_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_30619_0004.txt'`

## expanded_train:307579

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_307579_0001.txt'`

## expanded_train:309578

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_309578_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_309578_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_309578_0003.txt'`

## expanded_train:310298

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_310298_0001.txt'`

## expanded_train:312420

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_312420_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_312420_0002.txt'`

## expanded_train:312663

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_312663_0001.txt'`

## expanded_train:313069

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_313069_0001.txt'`

## expanded_train:321541

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_321541_0001.txt'`

## expanded_train:322298

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_322298_0001.txt'`

## expanded_train:322517

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_322517_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_322517_0002.txt'`

## expanded_train:324218

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_324218_0001.txt'`

## expanded_train:324936

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_324936_0001.txt'`

## expanded_train:324963

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_324963_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_324963_0002.txt'`

## expanded_train:329778

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_329778_0001.txt'`

## expanded_train:331210

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_331210_0001.txt'`

## expanded_train:331293

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_331293_0001.txt'`

## expanded_train:336412

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_336412_0001.txt'`

## expanded_train:341349

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_341349_0001.txt'`

## expanded_train:341734

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_341734_0001.txt'`

## expanded_train:341884

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_341884_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_341884_0002.txt'`

## expanded_train:341890

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_341890_0001.txt'`

## expanded_train:341949

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_341949_0001.txt'`

## expanded_train:343498

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_343498_0001.txt'`

## expanded_train:345076

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_345076_0001.txt'`

## expanded_train:345589

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_345589_0001.txt'`

## expanded_train:345911

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_345911_0001.txt'`

## expanded_train:348425

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_348425_0001.txt'`

## expanded_train:348714

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_348714_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_348714_0002.txt'`

## expanded_train:348986

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_348986_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_348986_0002.txt'`

## expanded_train:361408

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_361408_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_361408_0002.txt'`

## expanded_train:365084

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_365084_0001.txt'`

## expanded_train:365510

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_365510_0001.txt'`

## expanded_train:366269

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_366269_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_366269_0002.txt'`

## expanded_train:36632

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_36632_0001.txt'`

## expanded_train:374248

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_374248_0001.txt'`

## expanded_train:374369

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_374369_0001.txt'`

## expanded_train:379623

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_379623_0001.txt'`

## expanded_train:385541

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_385541_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_385541_0002.txt'`

## expanded_train:385665

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_385665_0001.txt'`

## expanded_train:38865

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_38865_0001.txt'`

## expanded_train:3895

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3895_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3895_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3895_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3895_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3895_0005.txt'`

## expanded_train:389651

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_389651_0001.txt'`

## expanded_train:391802

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_391802_0001.txt'`

## expanded_train:396430

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_396430_0001.txt'`

## expanded_train:397006

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_397006_0001.txt'`

## expanded_train:397181

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_397181_0001.txt'`

## expanded_train:397988

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_397988_0001.txt'`

## expanded_train:40201

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_40201_0001.txt'`

## expanded_train:402509

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_402509_0001.txt'`

## expanded_train:407721

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_407721_0001.txt'`

## expanded_train:40835

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_40835_0001.txt'`

## expanded_train:40906

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_40906_0001.txt'`

## expanded_train:409761

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_409761_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_409761_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_409761_0003.txt'`

## expanded_train:411389

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_411389_0001.txt'`

## expanded_train:411521

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_411521_0001.txt'`

## expanded_train:415353

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_415353_0001.txt'`

## expanded_train:417701

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_417701_0001.txt'`

## expanded_train:419484

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_419484_0001.txt'`

## expanded_train:421368

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_421368_0001.txt'`

## expanded_train:422141

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_422141_0001.txt'`

## expanded_train:422570

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_422570_0001.txt'`

## expanded_train:43105

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_43105_0001.txt'`

## expanded_train:431356

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_431356_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_431356_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_431356_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_431356_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_431356_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_431356_0006.txt'`

## expanded_train:435302

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_435302_0001.txt'`

## expanded_train:44194

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_44194_0001.txt'`

## expanded_train:44215

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_44215_0001.txt'`

## expanded_train:445481

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_445481_0001.txt'`

## expanded_train:451427

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_451427_0001.txt'`

## expanded_train:45156

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_45156_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_45156_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_45156_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_45156_0004.txt'`

## expanded_train:452798

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_452798_0001.txt'`

## expanded_train:455242

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_455242_0001.txt'`

## expanded_train:457189

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_457189_0001.txt'`

## expanded_train:458358

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_458358_0001.txt'`

## expanded_train:465742

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_465742_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_465742_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_465742_0003.txt'`

## expanded_train:467043

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_467043_0001.txt'`

## expanded_train:467065

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_467065_0001.txt'`

## expanded_train:467713

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_467713_0001.txt'`

## expanded_train:46809

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_46809_0001.txt'`

## expanded_train:46811

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_46811_0001.txt'`

## expanded_train:468133

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_468133_0001.txt'`

## expanded_train:477789

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_477789_0001.txt'`

## expanded_train:478856

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_478856_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_478856_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_478856_0003.txt'`

## expanded_train:479861

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_479861_0001.txt'`

## expanded_train:483368

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_483368_0001.txt'`

## expanded_train:48813

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_48813_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_48813_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_48813_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_48813_0004.txt'`

## expanded_train:493650

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_493650_0001.txt'`

## expanded_train:495236

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_495236_0001.txt'`

## expanded_train:496286

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_496286_0001.txt'`

## expanded_train:499961

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_499961_0001.txt'`

## expanded_train:500440

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_500440_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_500440_0002.txt'`

## expanded_train:502547

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_502547_0001.txt'`

## expanded_train:508709

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_508709_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_508709_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_508709_0003.txt'`

## expanded_train:514361

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_514361_0001.txt'`

## expanded_train:515767

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_515767_0001.txt'`

## expanded_train:516498

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_516498_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_516498_0002.txt'`

## expanded_train:518574

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_518574_0001.txt'`

## expanded_train:520439

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_520439_0001.txt'`

## expanded_train:531601

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_531601_0001.txt'`

## expanded_train:538569

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_538569_0001.txt'`

## expanded_train:543281

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_543281_0001.txt'`

## expanded_train:548847

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_548847_0001.txt'`

## expanded_train:55353

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55353_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55353_0002.txt'`

## expanded_train:558267

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_558267_0001.txt'`

## expanded_train:566109

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_566109_0001.txt'`

## expanded_train:573872

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_573872_0001.txt'`

## expanded_train:575195

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_575195_0001.txt'`

## expanded_train:575700

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_575700_0001.txt'`

## expanded_train:57640

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57640_0001.txt'`

## expanded_train:580142

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_580142_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_580142_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_580142_0003.txt'`

## expanded_train:580269

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_580269_0001.txt'`

## expanded_train:58598

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58598_0001.txt'`

## expanded_train:591409

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_591409_0001.txt'`

## expanded_train:595151

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_595151_0001.txt'`

## expanded_train:598542

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_598542_0001.txt'`

## expanded_train:599306

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_599306_0001.txt'`

## expanded_train:604070

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_604070_0001.txt'`

## expanded_train:604517

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_604517_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_604517_0002.txt'`

## expanded_train:605141

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_605141_0001.txt'`

## expanded_train:605198

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_605198_0001.txt'`

## expanded_train:608423

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_608423_0001.txt'`

## expanded_train:613685

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_613685_0001.txt'`

## expanded_train:622700

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_622700_0001.txt'`

## expanded_train:625398

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_625398_0001.txt'`

## expanded_train:625652

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_625652_0001.txt'`

## expanded_train:626742

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_626742_0001.txt'`

## expanded_train:626779

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_626779_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_626779_0002.txt'`

## expanded_train:626847

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_626847_0001.txt'`

## expanded_train:628854

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_628854_0001.txt'`

## expanded_train:62898

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_62898_0001.txt'`

## expanded_train:629084

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_629084_0001.txt'`

## expanded_train:632494

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_632494_0001.txt'`

## expanded_train:640833

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_640833_0001.txt'`

## expanded_train:646761

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_646761_0001.txt'`

## expanded_train:648823

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_648823_0001.txt'`

## expanded_train:653732

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_653732_0001.txt'`

## expanded_train:656240

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_656240_0001.txt'`

## expanded_train:658026

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_658026_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_658026_0002.txt'`

## expanded_train:658120

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_658120_0001.txt'`

## expanded_train:658298

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_658298_0001.txt'`

## expanded_train:659074

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_659074_0001.txt'`

## expanded_train:659152

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_659152_0001.txt'`

## expanded_train:669438

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_669438_0001.txt'`

## expanded_train:672012

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_672012_0001.txt'`

## expanded_train:67371

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_67371_0001.txt'`

## expanded_train:674370

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_674370_0001.txt'`

## expanded_train:677867

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_677867_0001.txt'`

## expanded_train:678896

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_678896_0001.txt'`

## expanded_train:681504

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_681504_0001.txt'`

## expanded_train:682206

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_682206_0001.txt'`

## expanded_train:690374

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_690374_0001.txt'`

## expanded_train:691934

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_691934_0001.txt'`

## expanded_train:692206

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_692206_0001.txt'`

## expanded_train:701339

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_701339_0001.txt'`

## expanded_train:70221

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_70221_0001.txt'`

## expanded_train:703735

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_703735_0001.txt'`

## expanded_train:706351

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_706351_0001.txt'`

## expanded_train:709327

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_709327_0001.txt'`

## expanded_train:709812

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_709812_0001.txt'`

## expanded_train:710935

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_710935_0001.txt'`

## expanded_train:712198

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_712198_0001.txt'`

## expanded_train:714199

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_714199_0001.txt'`

## expanded_train:714207

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_714207_0001.txt'`

## expanded_train:718799

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_718799_0001.txt'`

## expanded_train:720650

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_720650_0001.txt'`

## expanded_train:722783

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_722783_0001.txt'`

## expanded_train:724473

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_724473_0001.txt'`

## expanded_train:727454

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727454_0001.txt'`

## expanded_train:727482

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727482_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727482_0002.txt'`

## expanded_train:727693

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727693_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727693_0002.txt'`

## expanded_train:729562

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_729562_0001.txt'`

## expanded_train:730129

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_730129_0001.txt'`

## expanded_train:73113

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_73113_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_73113_0002.txt'`

## expanded_train:735092

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_735092_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_735092_0002.txt'`

## expanded_train:738914

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_738914_0001.txt'`

## expanded_train:738923

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_738923_0001.txt'`

## expanded_train:738938

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_738938_0001.txt'`

## expanded_train:739286

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_739286_0001.txt'`

## expanded_train:739344

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_739344_0001.txt'`

## expanded_train:740071

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_740071_0001.txt'`

## expanded_train:744095

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_744095_0001.txt'`

## expanded_train:744102

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_744102_0001.txt'`

## expanded_train:74418

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74418_0001.txt'`

## expanded_train:744199

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_744199_0001.txt'`

## expanded_train:746303

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_746303_0001.txt'`

## expanded_train:74934

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74934_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74934_0002.txt'`

## expanded_train:750095

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_750095_0001.txt'`

## expanded_train:753513

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_753513_0001.txt'`

## expanded_train:754732

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_754732_0001.txt'`

## expanded_train:757323

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_757323_0001.txt'`

## expanded_train:757419

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_757419_0001.txt'`

## expanded_train:757551

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_757551_0001.txt'`

## expanded_train:758950

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_758950_0001.txt'`

## expanded_train:761374

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_761374_0001.txt'`

## expanded_train:761544

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_761544_0001.txt'`

## expanded_train:761638

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_761638_0001.txt'`

## expanded_train:763564

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_763564_0001.txt'`

## expanded_train:770235

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_770235_0001.txt'`

## expanded_train:776128

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_776128_0001.txt'`

## expanded_train:776215

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_776215_0001.txt'`

## expanded_train:776465

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_776465_0001.txt'`

## expanded_train:778807

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_778807_0001.txt'`

## expanded_train:784798

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_784798_0001.txt'`

## expanded_train:787395

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_787395_0001.txt'`

## expanded_train:788081

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_788081_0001.txt'`

## expanded_train:789159

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_789159_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_789159_0002.txt'`

## expanded_train:79360

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_79360_0001.txt'`

## expanded_train:794492

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_794492_0001.txt'`

## expanded_train:795704

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_795704_0001.txt'`

## expanded_train:795781

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_795781_0001.txt'`

## expanded_train:795932

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_795932_0001.txt'`

## expanded_train:797492

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_797492_0001.txt'`

## expanded_train:799923

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_799923_0001.txt'`

## expanded_train:800785

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_800785_0001.txt'`

## expanded_train:801309

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_801309_0001.txt'`

## expanded_train:801993

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_801993_0001.txt'`

## expanded_train:808631

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_808631_0001.txt'`

## expanded_train:808770

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_808770_0001.txt'`

## expanded_train:809685

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_809685_0001.txt'`

## expanded_train:810639

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_810639_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_810639_0002.txt'`

## expanded_train:812951

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_812951_0001.txt'`

## expanded_train:813165

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_813165_0001.txt'`

## expanded_train:814727

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_814727_0001.txt'`

## expanded_train:814788

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_814788_0001.txt'`

## expanded_train:81482

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_81482_0001.txt'`

## expanded_train:81640

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_81640_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_81640_0002.txt'`

## expanded_train:821534

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_821534_0001.txt'`

## expanded_train:822486

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_822486_0001.txt'`

## expanded_train:829742

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_829742_0001.txt'`

## expanded_train:832922

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_832922_0001.txt'`

## expanded_train:83356

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_83356_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_83356_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_83356_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_83356_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_83356_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_83356_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_83356_0007.txt'`

## expanded_train:834341

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_834341_0001.txt'`

## expanded_train:83849

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_83849_0001.txt'`

## expanded_train:842153

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_842153_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_842153_0002.txt'`

## expanded_train:844141

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_844141_0001.txt'`

## expanded_train:844710

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_844710_0001.txt'`

## expanded_train:84493

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_84493_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_84493_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_84493_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_84493_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_84493_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_84493_0006.txt'`

## expanded_train:846249

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_846249_0001.txt'`

## expanded_train:849889

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_849889_0001.txt'`

## expanded_train:849893

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_849893_0001.txt'`

## expanded_train:853230

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_853230_0001.txt'`

## expanded_train:865233

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_865233_0001.txt'`

## expanded_train:86760

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_86760_0001.txt'`

## expanded_train:867624

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_867624_0001.txt'`

## expanded_train:867857

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_867857_0001.txt'`

## expanded_train:868110

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_868110_0001.txt'`

## expanded_train:869758

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_869758_0001.txt'`

## expanded_train:87844

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0007.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0008.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0009.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0010.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0011.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0012.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87844_0013.txt'`

## expanded_train:87891

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87891_0001.txt'`

## expanded_train:883478

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_883478_0001.txt'`

## expanded_train:886705

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_886705_0001.txt'`

## expanded_train:88897

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_88897_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_88897_0002.txt'`

## expanded_train:899615

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_899615_0001.txt'`

## expanded_train:909064

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_909064_0001.txt'`

## expanded_train:912594

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_912594_0001.txt'`

## expanded_train:916250

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_916250_0001.txt'`

## expanded_train:919792

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_919792_0001.txt'`

## expanded_train:920426

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_920426_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_920426_0002.txt'`

## expanded_train:929781

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_929781_0001.txt'`

## expanded_train:931709

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_931709_0001.txt'`

## expanded_train:932483

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_932483_0001.txt'`

## expanded_train:935041

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_935041_0001.txt'`

## expanded_train:935379

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_935379_0001.txt'`

## expanded_train:935917

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_935917_0001.txt'`

## expanded_train:93868

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_93868_0001.txt'`

## expanded_train:940412

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_940412_0001.txt'`

## expanded_train:944833

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_944833_0001.txt'`

## expanded_train:96026

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_96026_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_96026_0002.txt'`

## expanded_train:971805

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_971805_0001.txt'`

## expanded_train:973822

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_973822_0001.txt'`

## expanded_train:975506

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_975506_0001.txt'`

## expanded_train:990380

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_990380_0001.txt'`

## expanded_train:99100

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_99100_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_99100_0002.txt'`

## expanded_train:991629

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_991629_0001.txt'`

## expanded_train:992056

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992056_0001.txt'`

## expanded_train:992091

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992091_0001.txt'`

## expanded_train:992096

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992096_0001.txt'`

## expanded_train:992298

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992298_0001.txt'`

## expanded_train:992490

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992490_0001.txt'`

## expanded_train:993794

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_993794_0001.txt'`

## expanded_train:994350

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_994350_0001.txt'`

## expanded_train:995046

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995046_0001.txt'`

## expanded_train:995133

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995133_0001.txt'`

## expanded_train:995218

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995218_0001.txt'`

## expanded_train:995389

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995389_0001.txt'`

## expanded_train:995695

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995695_0001.txt'`

## expanded_train:995699

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995699_0001.txt'`

## expanded_train:995748

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995748_0001.txt'`

## expanded_train:995900

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995900_0001.txt'`

## expanded_train:995914

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995914_0001.txt'`

## expanded_train:996634

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996634_0001.txt'`

## expanded_train:996647

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996647_0001.txt'`

## expanded_train:99686

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_99686_0001.txt'`

## expanded_train:996906

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996906_0001.txt'`

## expanded_train:997241

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_997241_0001.txt'`

## expanded_train:998223

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998223_0001.txt'`

## expanded_train:998669

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998669_0001.txt'`

## expanded_train:998731

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998731_0001.txt'`

## expanded_train:998737

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998737_0001.txt'`

## expanded_train:998928

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998928_0001.txt'`

## expanded_train:999034

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999034_0001.txt'`

## expanded_train:999065

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999065_0001.txt'`

## expanded_train:999178

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999178_0001.txt'`

## expanded_train:999322

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999322_0001.txt'`

## expanded_train:999392

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999392_0001.txt'`

## expanded_train:999433

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999433_0001.txt'`

## expanded_train:999493

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999493_0001.txt'`

## expanded_train:999729

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999729_0001.txt'`

## expanded_train:999740

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999740_0001.txt'`

## validation:2885

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/validation_2885_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/validation_2885_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/validation_2885_0003.txt'`

## validation:3385

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/validation_3385_0001.txt'`

