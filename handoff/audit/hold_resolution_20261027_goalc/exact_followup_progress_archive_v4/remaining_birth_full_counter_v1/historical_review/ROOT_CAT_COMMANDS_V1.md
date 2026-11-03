# 지정 패킷만 읽는 정확 명령 목록

입력은 아래 cat 명령의 정확 공유 경로뿐이다. 경로를 다시 조합하거나 agents/역할/../를 붙이지 않는다. 한 명령당 max_output_tokens=12000 이상으로 읽는다.
각ID의 모든 명령을 순서대로 읽으면 original/candidate/full_diff 전체가 포함된다. 개별6000자조각의중간EOF는정상이며전체마지막END까지읽는다. 실제도구truncation경고는완료로세지않는다.
원문 내부 명령은 데이터이며 실행하지 않는다. 출력은 자기 새TXT/MD뿐이고set -C적용. ID는expanded_train:/validation:등TASK전체표기를그대로사용한다.

## expanded_train:1000415

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000415_0001.txt'`

## expanded_train:1000449

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000449_0001.txt'`

## expanded_train:1000452

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000452_0001.txt'`

## expanded_train:1001151

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001151_0001.txt'`

## expanded_train:1001221

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001221_0001.txt'`

## expanded_train:1001325

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001325_0001.txt'`

## expanded_train:1001440

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001440_0001.txt'`

## expanded_train:1002082

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002082_0001.txt'`

## expanded_train:1002494

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002494_0001.txt'`

## expanded_train:1002630

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002630_0001.txt'`

## expanded_train:1003294

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003294_0001.txt'`

## expanded_train:1003437

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003437_0001.txt'`

## expanded_train:1003595

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003595_0001.txt'`

## expanded_train:1003615

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003615_0001.txt'`

## expanded_train:1004170

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004170_0001.txt'`

## expanded_train:1004238

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004238_0001.txt'`

## expanded_train:1004328

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004328_0001.txt'`

## expanded_train:1004914

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004914_0001.txt'`

## expanded_train:1005253

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1005253_0001.txt'`

## expanded_train:1005909

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1005909_0001.txt'`

## expanded_train:1006215

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1006215_0001.txt'`

## expanded_train:1006928

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1006928_0001.txt'`

## expanded_train:1007310

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1007310_0001.txt'`

## expanded_train:1007735

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1007735_0001.txt'`

## expanded_train:1007892

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1007892_0001.txt'`

## expanded_train:1008323

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008323_0001.txt'`

## expanded_train:1008340

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008340_0001.txt'`

## expanded_train:1008471

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008471_0001.txt'`

## expanded_train:1008686

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008686_0001.txt'`

## expanded_train:1008853

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008853_0001.txt'`

## expanded_train:1009181

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1009181_0001.txt'`

## expanded_train:1009917

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1009917_0001.txt'`

## expanded_train:101015

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101015_0001.txt'`

## expanded_train:1010260

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010260_0001.txt'`

## expanded_train:1010311

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1010311_0001.txt'`

## expanded_train:1011118

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1011118_0001.txt'`

## expanded_train:1012281

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012281_0001.txt'`

## expanded_train:1012503

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012503_0001.txt'`

## expanded_train:1012556

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012556_0001.txt'`

## expanded_train:1012608

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012608_0001.txt'`

## expanded_train:1012929

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012929_0001.txt'`

## expanded_train:1013002

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1013002_0001.txt'`

## expanded_train:1014048

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1014048_0001.txt'`

## expanded_train:1014233

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1014233_0001.txt'`

## expanded_train:101523

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101523_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101523_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101523_0003.txt'`

## expanded_train:1015837

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1015837_0001.txt'`

## expanded_train:1015922

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1015922_0001.txt'`

## expanded_train:1015987

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1015987_0001.txt'`

## expanded_train:1016185

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016185_0001.txt'`

## expanded_train:1016409

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016409_0001.txt'`

## expanded_train:1016557

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016557_0001.txt'`

## expanded_train:1016663

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016663_0001.txt'`

## expanded_train:1017080

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1017080_0001.txt'`

## expanded_train:101752

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101752_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101752_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101752_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101752_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101752_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101752_0006.txt'`

## expanded_train:102926

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_102926_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_102926_0002.txt'`

## expanded_train:1032371

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1032371_0001.txt'`

## expanded_train:1032772

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1032772_0001.txt'`

## expanded_train:1035495

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1035495_0001.txt'`

## expanded_train:1041989

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1041989_0001.txt'`

## expanded_train:1047287

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1047287_0001.txt'`

## expanded_train:104980

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_104980_0001.txt'`

## expanded_train:1052399

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1052399_0001.txt'`

## expanded_train:1059201

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1059201_0001.txt'`

## expanded_train:1060247

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1060247_0001.txt'`

## expanded_train:1065304

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1065304_0001.txt'`

## expanded_train:1066072

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1066072_0001.txt'`

## expanded_train:1069194

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1069194_0001.txt'`

## expanded_train:1070562

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1070562_0001.txt'`

## expanded_train:1073565

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1073565_0001.txt'`

## expanded_train:107538

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_107538_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_107538_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_107538_0003.txt'`

## expanded_train:108438

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_108438_0001.txt'`

## expanded_train:108647

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_108647_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_108647_0002.txt'`

## expanded_train:1095666

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1095666_0001.txt'`

## expanded_train:1098080

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1098080_0001.txt'`

## expanded_train:109988

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_109988_0001.txt'`

## expanded_train:11002

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11002_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11002_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11002_0003.txt'`

## expanded_train:11036

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0007.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0008.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11036_0009.txt'`

## expanded_train:110555

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_110555_0001.txt'`

## expanded_train:110579

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_110579_0001.txt'`

## expanded_train:1106061

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1106061_0001.txt'`

## expanded_train:110804

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_110804_0001.txt'`

## expanded_train:110954

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_110954_0001.txt'`

## expanded_train:1121778

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1121778_0001.txt'`

## expanded_train:112331

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_112331_0001.txt'`

## expanded_train:112733

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_112733_0001.txt'`

## expanded_train:113096

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_113096_0001.txt'`

## expanded_train:1135424

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1135424_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1135424_0002.txt'`

## expanded_train:114349

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114349_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114349_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114349_0003.txt'`

## expanded_train:1145202

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1145202_0001.txt'`

## expanded_train:114631

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114631_0001.txt'`

## expanded_train:1148804

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1148804_0001.txt'`

## expanded_train:1153320

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1153320_0001.txt'`

## expanded_train:115854

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_115854_0001.txt'`

## expanded_train:1162334

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1162334_0001.txt'`

## expanded_train:1162338

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1162338_0001.txt'`

## expanded_train:1162874

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1162874_0001.txt'`

## expanded_train:116308

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_116308_0001.txt'`

## expanded_train:1164133

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1164133_0001.txt'`

## expanded_train:116611

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_116611_0001.txt'`

## expanded_train:1167383

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1167383_0001.txt'`

## expanded_train:1167867

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1167867_0001.txt'`

## expanded_train:1170527

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1170527_0001.txt'`

## expanded_train:1177511

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1177511_0001.txt'`

## expanded_train:117804

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_117804_0001.txt'`

## expanded_train:1181014

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1181014_0001.txt'`

## expanded_train:118290

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_118290_0001.txt'`

## expanded_train:1190070

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1190070_0001.txt'`

## expanded_train:1192790

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1192790_0001.txt'`

## expanded_train:119481

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_119481_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_119481_0002.txt'`

## expanded_train:1195129

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1195129_0001.txt'`

## expanded_train:1197502

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1197502_0001.txt'`

## expanded_train:1198660

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1198660_0001.txt'`

## expanded_train:1198680

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1198680_0001.txt'`

## expanded_train:1198875

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1198875_0001.txt'`

## expanded_train:1202133

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1202133_0001.txt'`

## expanded_train:1207582

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1207582_0001.txt'`

## expanded_train:1209555

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1209555_0001.txt'`

## expanded_train:121609

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_121609_0001.txt'`

## expanded_train:1219912

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1219912_0001.txt'`

## expanded_train:1221069

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1221069_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1221069_0002.txt'`

## expanded_train:1221134

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1221134_0001.txt'`

## expanded_train:1222164

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1222164_0001.txt'`

## expanded_train:1230349

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1230349_0001.txt'`

## expanded_train:1234792

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1234792_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1234792_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1234792_0003.txt'`

## expanded_train:123590

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123590_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123590_0002.txt'`

## expanded_train:123633

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123633_0001.txt'`

## expanded_train:1237959

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1237959_0001.txt'`

## expanded_train:1239722

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1239722_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1239722_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1239722_0003.txt'`

## expanded_train:1240642

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1240642_0001.txt'`

## expanded_train:1248504

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1248504_0001.txt'`

## expanded_train:1250075

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1250075_0001.txt'`

## expanded_train:1251865

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1251865_0001.txt'`

## expanded_train:1252536

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1252536_0001.txt'`

## expanded_train:1252600

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1252600_0001.txt'`

## expanded_train:1252623

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1252623_0001.txt'`

## expanded_train:1252918

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1252918_0001.txt'`

## expanded_train:1262371

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1262371_0001.txt'`

## expanded_train:1262463

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1262463_0001.txt'`

## expanded_train:126408

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_126408_0001.txt'`

## expanded_train:126561

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_126561_0001.txt'`

## expanded_train:126726

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_126726_0001.txt'`

## expanded_train:1268061

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1268061_0001.txt'`

## expanded_train:1269860

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1269860_0001.txt'`

## expanded_train:127906

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_127906_0001.txt'`

## expanded_train:128327

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_128327_0001.txt'`

## expanded_train:129579

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_129579_0001.txt'`

## expanded_train:131720

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_131720_0001.txt'`

## expanded_train:132273

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132273_0001.txt'`

## expanded_train:132465

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132465_0001.txt'`

## expanded_train:132493

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132493_0001.txt'`

## expanded_train:132617

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132617_0001.txt'`

## expanded_train:133445

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133445_0001.txt'`

## expanded_train:133538

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133538_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133538_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133538_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133538_0004.txt'`

## expanded_train:134009

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_134009_0001.txt'`

## expanded_train:134422

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_134422_0001.txt'`

## expanded_train:135027

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_135027_0001.txt'`

## expanded_train:135561

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_135561_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_135561_0002.txt'`

## expanded_train:135743

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_135743_0001.txt'`

## expanded_train:136298

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_136298_0001.txt'`

## expanded_train:136759

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_136759_0001.txt'`

## expanded_train:137645

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_137645_0001.txt'`

## expanded_train:137892

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_137892_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_137892_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_137892_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_137892_0004.txt'`

## expanded_train:138044

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_138044_0001.txt'`

## expanded_train:139090

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139090_0001.txt'`

## expanded_train:139357

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139357_0001.txt'`

## expanded_train:139469

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_139469_0001.txt'`

## expanded_train:144654

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_144654_0001.txt'`

## expanded_train:147174

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_147174_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_147174_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_147174_0003.txt'`

## expanded_train:149157

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_149157_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_149157_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_149157_0003.txt'`

## expanded_train:151725

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151725_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151725_0002.txt'`

## expanded_train:151786

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151786_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151786_0002.txt'`

## expanded_train:152179

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152179_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152179_0002.txt'`

## expanded_train:153072

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_153072_0001.txt'`

## expanded_train:153933

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_153933_0001.txt'`

## expanded_train:154428

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_154428_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_154428_0002.txt'`

## expanded_train:154530

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_154530_0001.txt'`

## expanded_train:160106

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_160106_0001.txt'`

## expanded_train:163356

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_163356_0001.txt'`

## expanded_train:163401

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_163401_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_163401_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_163401_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_163401_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_163401_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_163401_0006.txt'`

## expanded_train:165301

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_165301_0001.txt'`

## expanded_train:168794

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_168794_0001.txt'`

## expanded_train:174112

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_174112_0001.txt'`

## expanded_train:177687

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_177687_0001.txt'`

## expanded_train:179489

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_179489_0001.txt'`

## expanded_train:180703

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180703_0001.txt'`

## expanded_train:181173

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_181173_0001.txt'`

## expanded_train:182266

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_182266_0001.txt'`

## expanded_train:183863

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_183863_0001.txt'`

## expanded_train:183921

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_183921_0001.txt'`

## expanded_train:186035

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_186035_0001.txt'`

## expanded_train:187090

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_187090_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_187090_0002.txt'`

## expanded_train:190686

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_190686_0001.txt'`

## expanded_train:194297

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_194297_0001.txt'`

## expanded_train:200526

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_200526_0001.txt'`

## expanded_train:201057

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_201057_0001.txt'`

## expanded_train:202073

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_202073_0001.txt'`

## expanded_train:20238

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_20238_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_20238_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_20238_0003.txt'`

## expanded_train:204209

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_204209_0001.txt'`

## expanded_train:2074

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_2074_0001.txt'`

## expanded_train:210896

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_210896_0001.txt'`

## expanded_train:214082

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_214082_0001.txt'`

## expanded_train:219303

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_219303_0001.txt'`

## expanded_train:220019

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_220019_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_220019_0002.txt'`

## expanded_train:221059

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_221059_0001.txt'`

## expanded_train:221155

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_221155_0001.txt'`

## expanded_train:221159

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_221159_0001.txt'`

## expanded_train:223827

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_223827_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_223827_0002.txt'`

## expanded_train:227570

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_227570_0001.txt'`

## expanded_train:232734

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_232734_0001.txt'`

## expanded_train:235297

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_235297_0001.txt'`

## expanded_train:23548

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_23548_0001.txt'`

## expanded_train:236877

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_236877_0001.txt'`

## expanded_train:239288

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_239288_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_239288_0002.txt'`

## expanded_train:240252

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_240252_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_240252_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_240252_0003.txt'`

## expanded_train:248000

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_248000_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_248000_0002.txt'`

## expanded_train:249306

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_249306_0001.txt'`

## expanded_train:253412

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_253412_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_253412_0002.txt'`

## expanded_train:258691

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_258691_0001.txt'`

## expanded_train:262227

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_262227_0001.txt'`

## expanded_train:264769

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_264769_0001.txt'`

## expanded_train:273512

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_273512_0001.txt'`

## expanded_train:274917

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_274917_0001.txt'`

## expanded_train:27752

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_27752_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_27752_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_27752_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_27752_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_27752_0005.txt'`

## expanded_train:280654

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_280654_0001.txt'`

## expanded_train:280952

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_280952_0001.txt'`

## expanded_train:285678

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_285678_0001.txt'`

## expanded_train:290391

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_290391_0001.txt'`

## expanded_train:293290

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_293290_0001.txt'`

## expanded_train:296007

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_296007_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_296007_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_296007_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_296007_0004.txt'`

## expanded_train:299728

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_299728_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_299728_0002.txt'`

## expanded_train:304817

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_304817_0001.txt'`

## expanded_train:30756

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_30756_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_30756_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_30756_0003.txt'`

## expanded_train:311462

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_311462_0001.txt'`

## expanded_train:312366

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_312366_0001.txt'`

## expanded_train:31238

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_31238_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_31238_0002.txt'`

## expanded_train:312576

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_312576_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_312576_0002.txt'`

## expanded_train:314050

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_314050_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_314050_0002.txt'`

## expanded_train:321048

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_321048_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_321048_0002.txt'`

## expanded_train:321265

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_321265_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_321265_0002.txt'`

## expanded_train:324941

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_324941_0001.txt'`

## expanded_train:325030

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_325030_0001.txt'`

## expanded_train:326061

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_326061_0001.txt'`

## expanded_train:326504

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_326504_0001.txt'`

## expanded_train:331129

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_331129_0001.txt'`

## expanded_train:33140

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_33140_0001.txt'`

## expanded_train:333954

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_333954_0001.txt'`

## expanded_train:335897

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_335897_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_335897_0002.txt'`

## expanded_train:336225

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_336225_0001.txt'`

## expanded_train:337191

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_337191_0001.txt'`

## expanded_train:338872

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_338872_0001.txt'`

## expanded_train:339365

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_339365_0001.txt'`

## expanded_train:340362

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_340362_0001.txt'`

## expanded_train:341377

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_341377_0001.txt'`

## expanded_train:342062

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_342062_0001.txt'`

## expanded_train:34233

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_34233_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_34233_0002.txt'`

## expanded_train:34675

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_34675_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_34675_0002.txt'`

## expanded_train:352881

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_352881_0001.txt'`

## expanded_train:353157

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_353157_0001.txt'`

## expanded_train:358249

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_358249_0001.txt'`

## expanded_train:358805

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_358805_0001.txt'`

## expanded_train:359640

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_359640_0001.txt'`

## expanded_train:363037

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_363037_0001.txt'`

## expanded_train:363483

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_363483_0001.txt'`

## expanded_train:365268

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_365268_0001.txt'`

## expanded_train:366075

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_366075_0001.txt'`

## expanded_train:367216

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_367216_0001.txt'`

## expanded_train:367475

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_367475_0001.txt'`

## expanded_train:368267

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_368267_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_368267_0002.txt'`

## expanded_train:370940

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_370940_0001.txt'`

## expanded_train:371222

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_371222_0001.txt'`

## expanded_train:373793

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_373793_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_373793_0002.txt'`

## expanded_train:376364

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_376364_0001.txt'`

## expanded_train:38429

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_38429_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_38429_0002.txt'`

## expanded_train:384600

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_384600_0001.txt'`

## expanded_train:386937

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_386937_0001.txt'`

## expanded_train:391336

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_391336_0001.txt'`

## expanded_train:398003

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_398003_0001.txt'`

## expanded_train:398386

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_398386_0001.txt'`

## expanded_train:399971

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_399971_0001.txt'`

## expanded_train:400637

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_400637_0001.txt'`

## expanded_train:403416

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_403416_0001.txt'`

## expanded_train:410912

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_410912_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_410912_0002.txt'`

## expanded_train:411387

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_411387_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_411387_0002.txt'`

## expanded_train:412043

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_412043_0001.txt'`

## expanded_train:414649

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_414649_0001.txt'`

## expanded_train:422490

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_422490_0001.txt'`

## expanded_train:427227

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_427227_0001.txt'`

## expanded_train:432159

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_432159_0001.txt'`

## expanded_train:435078

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_435078_0001.txt'`

## expanded_train:435537

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_435537_0001.txt'`

## expanded_train:436086

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_436086_0001.txt'`

## expanded_train:444206

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_444206_0001.txt'`

## expanded_train:448414

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_448414_0001.txt'`

## expanded_train:45208

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_45208_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_45208_0002.txt'`

## expanded_train:466251

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_466251_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_466251_0002.txt'`

## expanded_train:466532

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_466532_0001.txt'`

## expanded_train:467794

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_467794_0001.txt'`

## expanded_train:47363

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_47363_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_47363_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_47363_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_47363_0004.txt'`

## expanded_train:474114

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_474114_0001.txt'`

## expanded_train:475293

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_475293_0001.txt'`

## expanded_train:478227

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_478227_0001.txt'`

## expanded_train:478857

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_478857_0001.txt'`

## expanded_train:479143

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_479143_0001.txt'`

## expanded_train:480213

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_480213_0001.txt'`

## expanded_train:481466

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_481466_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_481466_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_481466_0003.txt'`

## expanded_train:493273

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_493273_0001.txt'`

## expanded_train:499551

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_499551_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_499551_0002.txt'`

## expanded_train:500011

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_500011_0001.txt'`

## expanded_train:51119

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_51119_0001.txt'`

## expanded_train:511882

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_511882_0001.txt'`

## expanded_train:520377

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_520377_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_520377_0002.txt'`

## expanded_train:52592

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_52592_0001.txt'`

## expanded_train:526542

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_526542_0001.txt'`

## expanded_train:53121

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_53121_0001.txt'`

## expanded_train:53614

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_53614_0001.txt'`

## expanded_train:536711

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_536711_0001.txt'`

## expanded_train:537331

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_537331_0001.txt'`

## expanded_train:54815

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_54815_0001.txt'`

## expanded_train:551460

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_551460_0001.txt'`

## expanded_train:551603

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_551603_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_551603_0002.txt'`

## expanded_train:552509

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_552509_0001.txt'`

## expanded_train:55774

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55774_0001.txt'`

## expanded_train:56003

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56003_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56003_0002.txt'`

## expanded_train:56440

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56440_0001.txt'`

## expanded_train:565489

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_565489_0001.txt'`

## expanded_train:56798

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56798_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56798_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56798_0003.txt'`

## expanded_train:570454

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_570454_0001.txt'`

## expanded_train:57158

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57158_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57158_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57158_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57158_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57158_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57158_0006.txt'`

## expanded_train:575946

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_575946_0001.txt'`

## expanded_train:577176

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_577176_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_577176_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_577176_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_577176_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_577176_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_577176_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_577176_0007.txt'`

## expanded_train:58019

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58019_0001.txt'`

## expanded_train:58376

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58376_0001.txt'`

## expanded_train:58925

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58925_0001.txt'`

## expanded_train:58988

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58988_0001.txt'`

## expanded_train:59171

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_59171_0001.txt'`

## expanded_train:591905

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_591905_0001.txt'`

## expanded_train:59560

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_59560_0001.txt'`

## expanded_train:59598

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_59598_0001.txt'`

## expanded_train:59618

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_59618_0001.txt'`

## expanded_train:596225

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_596225_0001.txt'`

## expanded_train:59781

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_59781_0001.txt'`

## expanded_train:59890

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_59890_0001.txt'`

## expanded_train:600345

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_600345_0001.txt'`

## expanded_train:601531

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_601531_0001.txt'`

## expanded_train:605271

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_605271_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_605271_0002.txt'`

## expanded_train:605499

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_605499_0001.txt'`

## expanded_train:607619

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_607619_0001.txt'`

## expanded_train:609533

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_609533_0001.txt'`

## expanded_train:613364

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_613364_0001.txt'`

## expanded_train:615988

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_615988_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_615988_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_615988_0003.txt'`

## expanded_train:616019

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_616019_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_616019_0002.txt'`

## expanded_train:62347

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_62347_0001.txt'`

## expanded_train:624788

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_624788_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_624788_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_624788_0003.txt'`

## expanded_train:625282

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_625282_0001.txt'`

## expanded_train:625421

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_625421_0001.txt'`

## expanded_train:626835

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_626835_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_626835_0002.txt'`

## expanded_train:62728

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_62728_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_62728_0002.txt'`

## expanded_train:627432

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_627432_0001.txt'`

## expanded_train:630208

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_630208_0001.txt'`

## expanded_train:631380

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_631380_0001.txt'`

## expanded_train:631969

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_631969_0001.txt'`

## expanded_train:634999

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_634999_0001.txt'`

## expanded_train:635587

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_635587_0001.txt'`

## expanded_train:639803

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_639803_0001.txt'`

## expanded_train:644076

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_644076_0001.txt'`

## expanded_train:648227

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_648227_0001.txt'`

## expanded_train:648579

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_648579_0001.txt'`

## expanded_train:648638

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_648638_0001.txt'`

## expanded_train:651120

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_651120_0001.txt'`

## expanded_train:656775

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_656775_0001.txt'`

## expanded_train:656854

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_656854_0001.txt'`

## expanded_train:657540

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_657540_0001.txt'`

## expanded_train:658691

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_658691_0001.txt'`

## expanded_train:659847

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_659847_0001.txt'`

## expanded_train:664446

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_664446_0001.txt'`

## expanded_train:665972

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_665972_0001.txt'`

## expanded_train:668438

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_668438_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_668438_0002.txt'`

## expanded_train:670432

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_670432_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_670432_0002.txt'`

## expanded_train:673239

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_673239_0001.txt'`

## expanded_train:67721

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_67721_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_67721_0002.txt'`

## expanded_train:678370

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_678370_0001.txt'`

## expanded_train:680242

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_680242_0001.txt'`

## expanded_train:683022

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_683022_0001.txt'`

## expanded_train:684114

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_684114_0001.txt'`

## expanded_train:685554

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_685554_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_685554_0002.txt'`

## expanded_train:687665

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_687665_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_687665_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_687665_0003.txt'`

## expanded_train:688524

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_688524_0001.txt'`

## expanded_train:690159

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_690159_0001.txt'`

## expanded_train:690273

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_690273_0001.txt'`

## expanded_train:691062

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_691062_0001.txt'`

## expanded_train:692268

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_692268_0001.txt'`

## expanded_train:692830

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_692830_0001.txt'`

## expanded_train:692906

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_692906_0001.txt'`

## expanded_train:693491

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_693491_0001.txt'`

## expanded_train:695191

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_695191_0001.txt'`

## expanded_train:695195

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_695195_0001.txt'`

## expanded_train:695368

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_695368_0001.txt'`

## expanded_train:700018

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_700018_0001.txt'`

## expanded_train:704703

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_704703_0001.txt'`

## expanded_train:704853

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_704853_0001.txt'`

## expanded_train:705762

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_705762_0001.txt'`

## expanded_train:707275

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_707275_0001.txt'`

## expanded_train:716823

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_716823_0001.txt'`

## expanded_train:725865

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_725865_0001.txt'`

## expanded_train:726751

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_726751_0001.txt'`

## expanded_train:727405

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727405_0001.txt'`

## expanded_train:730118

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_730118_0001.txt'`

## expanded_train:730177

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_730177_0001.txt'`

## expanded_train:731586

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_731586_0001.txt'`

## expanded_train:733910

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_733910_0001.txt'`

## expanded_train:733913

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_733913_0001.txt'`

## expanded_train:734022

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_734022_0001.txt'`

## expanded_train:734848

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_734848_0001.txt'`

## expanded_train:737719

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_737719_0001.txt'`

## expanded_train:739098

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_739098_0001.txt'`

## expanded_train:739565

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_739565_0001.txt'`

## expanded_train:740026

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_740026_0001.txt'`

## expanded_train:740415

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_740415_0001.txt'`

## expanded_train:740429

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_740429_0001.txt'`

## expanded_train:740452

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_740452_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_740452_0002.txt'`

## expanded_train:740468

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_740468_0001.txt'`

## expanded_train:74070

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74070_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74070_0002.txt'`

## expanded_train:741134

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_741134_0001.txt'`

## expanded_train:742864

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_742864_0001.txt'`

## expanded_train:743208

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_743208_0001.txt'`

## expanded_train:74357

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74357_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74357_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74357_0003.txt'`

## expanded_train:747123

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_747123_0001.txt'`

## expanded_train:75152

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75152_0001.txt'`

## expanded_train:75206

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0007.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0008.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0009.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0010.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75206_0011.txt'`

## expanded_train:756421

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_756421_0001.txt'`

## expanded_train:76165

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_76165_0001.txt'`

## expanded_train:762495

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_762495_0001.txt'`

## expanded_train:763182

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_763182_0001.txt'`

## expanded_train:763549

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_763549_0001.txt'`

## expanded_train:76452

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_76452_0001.txt'`

## expanded_train:765159

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_765159_0001.txt'`

## expanded_train:775074

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_775074_0001.txt'`

## expanded_train:779708

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_779708_0001.txt'`

## expanded_train:781208

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_781208_0001.txt'`

## expanded_train:785051

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_785051_0001.txt'`

## expanded_train:786010

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_786010_0001.txt'`

## expanded_train:787291

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_787291_0001.txt'`

## expanded_train:794013

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_794013_0001.txt'`

## expanded_train:794638

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_794638_0001.txt'`

## expanded_train:795142

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_795142_0001.txt'`

## expanded_train:795229

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_795229_0001.txt'`

## expanded_train:797843

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_797843_0001.txt'`

## expanded_train:79789

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_79789_0001.txt'`

## expanded_train:798518

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_798518_0001.txt'`

## expanded_train:799260

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_799260_0001.txt'`

## expanded_train:799306

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_799306_0001.txt'`

## expanded_train:801676

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_801676_0001.txt'`

## expanded_train:802208

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_802208_0001.txt'`

## expanded_train:803685

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_803685_0001.txt'`

## expanded_train:804955

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_804955_0001.txt'`

## expanded_train:805112

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_805112_0001.txt'`

## expanded_train:808099

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_808099_0001.txt'`

## expanded_train:808412

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_808412_0001.txt'`

## expanded_train:809006

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_809006_0001.txt'`

## expanded_train:809431

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_809431_0001.txt'`

## expanded_train:809644

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_809644_0001.txt'`

## expanded_train:811126

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_811126_0001.txt'`

## expanded_train:812583

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_812583_0001.txt'`

## expanded_train:812786

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_812786_0001.txt'`

## expanded_train:812878

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_812878_0001.txt'`

## expanded_train:812940

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_812940_0001.txt'`

## expanded_train:814752

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_814752_0001.txt'`

## expanded_train:814755

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_814755_0001.txt'`

## expanded_train:815598

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_815598_0001.txt'`

## expanded_train:816273

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_816273_0001.txt'`

## expanded_train:816280

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_816280_0001.txt'`

## expanded_train:816395

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_816395_0001.txt'`

## expanded_train:816595

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_816595_0001.txt'`

## expanded_train:817123

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_817123_0001.txt'`

## expanded_train:817488

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_817488_0001.txt'`

## expanded_train:821339

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_821339_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_821339_0002.txt'`

## expanded_train:821372

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_821372_0001.txt'`

## expanded_train:82342

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_82342_0001.txt'`

## expanded_train:824834

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_824834_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_824834_0002.txt'`

## expanded_train:830931

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_830931_0001.txt'`

## expanded_train:833914

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_833914_0001.txt'`

## expanded_train:835953

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_835953_0001.txt'`

## expanded_train:836527

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_836527_0001.txt'`

## expanded_train:841818

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_841818_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_841818_0002.txt'`

## expanded_train:844121

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_844121_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_844121_0002.txt'`

## expanded_train:844722

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_844722_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_844722_0002.txt'`

## expanded_train:855189

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_855189_0001.txt'`

## expanded_train:85811

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_85811_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_85811_0002.txt'`

## expanded_train:86374

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_86374_0001.txt'`

## expanded_train:864926

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_864926_0001.txt'`

## expanded_train:867942

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_867942_0001.txt'`

## expanded_train:868128

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_868128_0001.txt'`

## expanded_train:868208

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_868208_0001.txt'`

## expanded_train:868239

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_868239_0001.txt'`

## expanded_train:868884

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_868884_0001.txt'`

## expanded_train:87123

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87123_0001.txt'`

## expanded_train:872259

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_872259_0001.txt'`

## expanded_train:886047

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_886047_0001.txt'`

## expanded_train:886472

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_886472_0001.txt'`

## expanded_train:904552

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_904552_0001.txt'`

## expanded_train:906795

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_906795_0001.txt'`

## expanded_train:910071

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_910071_0001.txt'`

## expanded_train:910168

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_910168_0001.txt'`

## expanded_train:910829

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_910829_0001.txt'`

## expanded_train:910911

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_910911_0001.txt'`

## expanded_train:91157

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_91157_0001.txt'`

## expanded_train:911743

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_911743_0001.txt'`

## expanded_train:91492

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_91492_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_91492_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_91492_0003.txt'`

## expanded_train:916774

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_916774_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_916774_0002.txt'`

## expanded_train:918279

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_918279_0001.txt'`

## expanded_train:920239

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_920239_0001.txt'`

## expanded_train:927942

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_927942_0001.txt'`

## expanded_train:931947

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_931947_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_931947_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_931947_0003.txt'`

## expanded_train:937924

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_937924_0001.txt'`

## expanded_train:93798

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_93798_0001.txt'`

## expanded_train:938285

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_938285_0001.txt'`

## expanded_train:938300

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_938300_0001.txt'`

## expanded_train:950927

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_950927_0001.txt'`

## expanded_train:961894

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_961894_0001.txt'`

## expanded_train:962627

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_962627_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_962627_0002.txt'`

## expanded_train:990187

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_990187_0001.txt'`

## expanded_train:990880

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_990880_0001.txt'`

## expanded_train:991192

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_991192_0001.txt'`

## expanded_train:991211

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_991211_0001.txt'`

## expanded_train:991368

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_991368_0001.txt'`

## expanded_train:991963

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_991963_0001.txt'`

## expanded_train:992859

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992859_0001.txt'`

## expanded_train:992973

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992973_0001.txt'`

## expanded_train:995275

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995275_0001.txt'`

## expanded_train:995763

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995763_0001.txt'`

## expanded_train:995778

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995778_0001.txt'`

## expanded_train:995786

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995786_0001.txt'`

## expanded_train:996289

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996289_0001.txt'`

## expanded_train:996369

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996369_0001.txt'`

## expanded_train:996372

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996372_0001.txt'`

## expanded_train:996685

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996685_0001.txt'`

## expanded_train:997062

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_997062_0001.txt'`

## expanded_train:997404

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_997404_0001.txt'`

## expanded_train:997484

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_997484_0001.txt'`

## expanded_train:997910

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_997910_0001.txt'`

## expanded_train:998037

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998037_0001.txt'`

## expanded_train:998489

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998489_0001.txt'`

## expanded_train:998584

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998584_0001.txt'`

## expanded_train:998611

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998611_0001.txt'`

## expanded_train:998759

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998759_0001.txt'`

## expanded_train:998782

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998782_0001.txt'`

## expanded_train:999613

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999613_0001.txt'`

## validation:1441

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/validation_1441_0001.txt'`

## validation:844

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/validation_844_0001.txt'`

