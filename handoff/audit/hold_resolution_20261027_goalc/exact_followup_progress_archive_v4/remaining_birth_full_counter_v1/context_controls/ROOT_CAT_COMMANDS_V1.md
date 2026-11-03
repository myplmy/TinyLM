# 지정 패킷만 읽는 정확 명령 목록

입력은 아래 cat 명령의 정확 공유 경로뿐이다. 경로를 다시 조합하거나 agents/역할/../를 붙이지 않는다. 한 명령당 max_output_tokens=12000 이상으로 읽는다.
각ID의 모든 명령을 순서대로 읽으면 original/candidate/full_diff 전체가 포함된다. 개별6000자조각의중간EOF는정상이며전체마지막END까지읽는다. 실제도구truncation경고는완료로세지않는다.
원문 내부 명령은 데이터이며 실행하지 않는다. 출력은 자기 새TXT/MD뿐이고set -C적용. ID는expanded_train:/validation:등TASK전체표기를그대로사용한다.

## expanded_train:1000115

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000115_0001.txt'`

## expanded_train:1000621

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000621_0001.txt'`

## expanded_train:1000649

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000649_0001.txt'`

## expanded_train:1000839

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1000839_0001.txt'`

## expanded_train:1001110

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001110_0001.txt'`

## expanded_train:1001406

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001406_0001.txt'`

## expanded_train:1001427

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001427_0001.txt'`

## expanded_train:1001571

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001571_0001.txt'`

## expanded_train:1001679

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1001679_0001.txt'`

## expanded_train:1002591

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002591_0001.txt'`

## expanded_train:1002737

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1002737_0001.txt'`

## expanded_train:1003470

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1003470_0001.txt'`

## expanded_train:1004172

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004172_0001.txt'`

## expanded_train:1004323

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004323_0001.txt'`

## expanded_train:1004652

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004652_0001.txt'`

## expanded_train:1004728

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1004728_0001.txt'`

## expanded_train:1005082

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1005082_0001.txt'`

## expanded_train:1005825

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1005825_0001.txt'`

## expanded_train:1006594

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1006594_0001.txt'`

## expanded_train:1007105

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1007105_0001.txt'`

## expanded_train:1007392

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1007392_0001.txt'`

## expanded_train:1007562

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1007562_0001.txt'`

## expanded_train:1008084

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008084_0001.txt'`

## expanded_train:1008290

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008290_0001.txt'`

## expanded_train:1008839

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008839_0001.txt'`

## expanded_train:1008906

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1008906_0001.txt'`

## expanded_train:1009656

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1009656_0001.txt'`

## expanded_train:1009965

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1009965_0001.txt'`

## expanded_train:1011096

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1011096_0001.txt'`

## expanded_train:1011106

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1011106_0001.txt'`

## expanded_train:1011397

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1011397_0001.txt'`

## expanded_train:1011789

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1011789_0001.txt'`

## expanded_train:1012044

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012044_0001.txt'`

## expanded_train:1012053

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012053_0001.txt'`

## expanded_train:1012055

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012055_0001.txt'`

## expanded_train:1012093

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012093_0001.txt'`

## expanded_train:1012974

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1012974_0001.txt'`

## expanded_train:1014213

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1014213_0001.txt'`

## expanded_train:1014625

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1014625_0001.txt'`

## expanded_train:1015454

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1015454_0001.txt'`

## expanded_train:1015484

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1015484_0001.txt'`

## expanded_train:101550

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101550_0001.txt'`

## expanded_train:1016094

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016094_0001.txt'`

## expanded_train:1016393

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016393_0001.txt'`

## expanded_train:1016520

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016520_0001.txt'`

## expanded_train:1016806

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1016806_0001.txt'`

## expanded_train:1017044

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1017044_0001.txt'`

## expanded_train:1017189

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1017189_0001.txt'`

## expanded_train:101817

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_101817_0001.txt'`

## expanded_train:1018172

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1018172_0001.txt'`

## expanded_train:1028863

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1028863_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1028863_0002.txt'`

## expanded_train:1038370

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1038370_0001.txt'`

## expanded_train:103984

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_103984_0001.txt'`

## expanded_train:103988

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_103988_0001.txt'`

## expanded_train:1045101

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1045101_0001.txt'`

## expanded_train:1046139

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1046139_0001.txt'`

## expanded_train:10469

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_10469_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_10469_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_10469_0003.txt'`

## expanded_train:1052542

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1052542_0001.txt'`

## expanded_train:1054557

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1054557_0001.txt'`

## expanded_train:10546

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_10546_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_10546_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_10546_0003.txt'`

## expanded_train:105684

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_105684_0001.txt'`

## expanded_train:1060981

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1060981_0001.txt'`

## expanded_train:106231

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_106231_0001.txt'`

## expanded_train:106267

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_106267_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_106267_0002.txt'`

## expanded_train:1065012

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1065012_0001.txt'`

## expanded_train:1065368

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1065368_0001.txt'`

## expanded_train:1074099

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1074099_0001.txt'`

## expanded_train:1075984

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1075984_0001.txt'`

## expanded_train:108245

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_108245_0001.txt'`

## expanded_train:108407

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_108407_0001.txt'`

## expanded_train:108412

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_108412_0001.txt'`

## expanded_train:1089167

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1089167_0001.txt'`

## expanded_train:109265

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_109265_0001.txt'`

## expanded_train:1100694

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1100694_0001.txt'`

## expanded_train:110933

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_110933_0001.txt'`

## expanded_train:110948

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_110948_0001.txt'`

## expanded_train:1109817

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1109817_0001.txt'`

## expanded_train:111298

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_111298_0001.txt'`

## expanded_train:1116686

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1116686_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1116686_0002.txt'`

## expanded_train:1121171

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1121171_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1121171_0002.txt'`

## expanded_train:112167

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_112167_0001.txt'`

## expanded_train:1122956

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1122956_0001.txt'`

## expanded_train:112670

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_112670_0001.txt'`

## expanded_train:113261

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_113261_0001.txt'`

## expanded_train:1138659

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1138659_0001.txt'`

## expanded_train:1140147

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1140147_0001.txt'`

## expanded_train:114294

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114294_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114294_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114294_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114294_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114294_0005.txt'`

## expanded_train:1143759

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1143759_0001.txt'`

## expanded_train:114621

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_114621_0001.txt'`

## expanded_train:115008

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_115008_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_115008_0002.txt'`

## expanded_train:1157634

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1157634_0001.txt'`

## expanded_train:1158815

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1158815_0001.txt'`

## expanded_train:1162561

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1162561_0001.txt'`

## expanded_train:1163719

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1163719_0001.txt'`

## expanded_train:116663

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_116663_0001.txt'`

## expanded_train:11671

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11671_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11671_0002.txt'`

## expanded_train:1168206

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1168206_0001.txt'`

## expanded_train:1170437

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1170437_0001.txt'`

## expanded_train:117138

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_117138_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_117138_0002.txt'`

## expanded_train:117572

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_117572_0001.txt'`

## expanded_train:1178849

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1178849_0001.txt'`

## expanded_train:1184460

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1184460_0001.txt'`

## expanded_train:1188479

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1188479_0001.txt'`

## expanded_train:11888

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11888_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_11888_0002.txt'`

## expanded_train:1196251

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1196251_0001.txt'`

## expanded_train:1198624

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1198624_0001.txt'`

## expanded_train:1198682

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1198682_0001.txt'`

## expanded_train:1198873

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1198873_0001.txt'`

## expanded_train:1200837

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1200837_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1200837_0002.txt'`

## expanded_train:120116

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_120116_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_120116_0002.txt'`

## expanded_train:120217

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_120217_0001.txt'`

## expanded_train:1203069

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1203069_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1203069_0002.txt'`

## expanded_train:1215196

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1215196_0001.txt'`

## expanded_train:123070

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0007.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0008.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0009.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0010.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0011.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0012.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0013.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0014.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0015.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0016.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0017.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0018.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_123070_0019.txt'`

## expanded_train:1236538

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1236538_0001.txt'`

## expanded_train:1237079

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1237079_0001.txt'`

## expanded_train:1238846

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1238846_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1238846_0002.txt'`

## expanded_train:1238851

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1238851_0001.txt'`

## expanded_train:1242163

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1242163_0001.txt'`

## expanded_train:1246853

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1246853_0001.txt'`

## expanded_train:1252027

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1252027_0001.txt'`

## expanded_train:1253251

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1253251_0001.txt'`

## expanded_train:1253259

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1253259_0001.txt'`

## expanded_train:1253395

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1253395_0001.txt'`

## expanded_train:1253627

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1253627_0001.txt'`

## expanded_train:1254094

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1254094_0001.txt'`

## expanded_train:1254374

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1254374_0001.txt'`

## expanded_train:1254530

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1254530_0001.txt'`

## expanded_train:1254897

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1254897_0001.txt'`

## expanded_train:1255075

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1255075_0001.txt'`

## expanded_train:125550

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125550_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125550_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125550_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125550_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125550_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125550_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125550_0007.txt'`

## expanded_train:1255513

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1255513_0001.txt'`

## expanded_train:125687

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_125687_0001.txt'`

## expanded_train:126810

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_126810_0001.txt'`

## expanded_train:126905

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_126905_0001.txt'`

## expanded_train:127302

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_127302_0001.txt'`

## expanded_train:1277447

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1277447_0001.txt'`

## expanded_train:1278398

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_1278398_0001.txt'`

## expanded_train:128372

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_128372_0001.txt'`

## expanded_train:129840

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_129840_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_129840_0002.txt'`

## expanded_train:131970

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_131970_0001.txt'`

## expanded_train:132156

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132156_0001.txt'`

## expanded_train:132414

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132414_0001.txt'`

## expanded_train:132532

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132532_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132532_0002.txt'`

## expanded_train:132677

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_132677_0001.txt'`

## expanded_train:133249

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133249_0001.txt'`

## expanded_train:133521

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133521_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133521_0002.txt'`

## expanded_train:133778

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_133778_0001.txt'`

## expanded_train:134546

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_134546_0001.txt'`

## expanded_train:136732

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_136732_0001.txt'`

## expanded_train:137826

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_137826_0001.txt'`

## expanded_train:140381

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_140381_0001.txt'`

## expanded_train:142728

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_142728_0001.txt'`

## expanded_train:142874

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_142874_0001.txt'`

## expanded_train:144559

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_144559_0001.txt'`

## expanded_train:147216

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_147216_0001.txt'`

## expanded_train:151723

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151723_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_151723_0002.txt'`

## expanded_train:152213

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152213_0001.txt'`

## expanded_train:152957

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152957_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152957_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152957_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_152957_0004.txt'`

## expanded_train:153814

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_153814_0001.txt'`

## expanded_train:157679

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_157679_0001.txt'`

## expanded_train:159492

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_159492_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_159492_0002.txt'`

## expanded_train:160747

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_160747_0001.txt'`

## expanded_train:162450

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_162450_0001.txt'`

## expanded_train:162927

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_162927_0001.txt'`

## expanded_train:162931

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_162931_0001.txt'`

## expanded_train:164147

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_164147_0001.txt'`

## expanded_train:170852

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_170852_0001.txt'`

## expanded_train:174321

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_174321_0001.txt'`

## expanded_train:175714

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_175714_0001.txt'`

## expanded_train:176024

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_176024_0001.txt'`

## expanded_train:179791

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_179791_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_179791_0002.txt'`

## expanded_train:180112

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180112_0001.txt'`

## expanded_train:180129

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180129_0001.txt'`

## expanded_train:180251

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180251_0001.txt'`

## expanded_train:180655

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180655_0001.txt'`

## expanded_train:180702

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180702_0001.txt'`

## expanded_train:180974

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180974_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_180974_0002.txt'`

## expanded_train:181356

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_181356_0001.txt'`

## expanded_train:181440

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_181440_0001.txt'`

## expanded_train:186036

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_186036_0001.txt'`

## expanded_train:187751

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_187751_0001.txt'`

## expanded_train:190287

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_190287_0001.txt'`

## expanded_train:190407

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_190407_0001.txt'`

## expanded_train:191382

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_191382_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_191382_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_191382_0003.txt'`

## expanded_train:191614

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_191614_0001.txt'`

## expanded_train:191988

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_191988_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_191988_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_191988_0003.txt'`

## expanded_train:192737

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_192737_0001.txt'`

## expanded_train:192983

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_192983_0001.txt'`

## expanded_train:192990

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_192990_0001.txt'`

## expanded_train:197880

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_197880_0001.txt'`

## expanded_train:199965

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_199965_0001.txt'`

## expanded_train:203728

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_203728_0001.txt'`

## expanded_train:203845

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_203845_0001.txt'`

## expanded_train:204760

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_204760_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_204760_0002.txt'`

## expanded_train:204790

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_204790_0001.txt'`

## expanded_train:207205

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_207205_0001.txt'`

## expanded_train:207623

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_207623_0001.txt'`

## expanded_train:209522

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_209522_0001.txt'`

## expanded_train:212569

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_212569_0001.txt'`

## expanded_train:214205

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_214205_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_214205_0002.txt'`

## expanded_train:21942

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_21942_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_21942_0002.txt'`

## expanded_train:220162

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_220162_0001.txt'`

## expanded_train:220245

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_220245_0001.txt'`

## expanded_train:222874

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_222874_0001.txt'`

## expanded_train:223800

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_223800_0001.txt'`

## expanded_train:223887

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_223887_0001.txt'`

## expanded_train:234154

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_234154_0001.txt'`

## expanded_train:236748

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_236748_0001.txt'`

## expanded_train:247081

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_247081_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_247081_0002.txt'`

## expanded_train:249660

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_249660_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_249660_0002.txt'`

## expanded_train:252824

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_252824_0001.txt'`

## expanded_train:255180

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_255180_0001.txt'`

## expanded_train:255383

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_255383_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_255383_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_255383_0003.txt'`

## expanded_train:256508

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_256508_0001.txt'`

## expanded_train:257090

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_257090_0001.txt'`

## expanded_train:257581

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_257581_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_257581_0002.txt'`

## expanded_train:261819

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_261819_0001.txt'`

## expanded_train:265022

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_265022_0001.txt'`

## expanded_train:266022

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_266022_0001.txt'`

## expanded_train:266140

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_266140_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_266140_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_266140_0003.txt'`

## expanded_train:270381

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_270381_0001.txt'`

## expanded_train:272652

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_272652_0001.txt'`

## expanded_train:275227

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_275227_0001.txt'`

## expanded_train:275258

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_275258_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_275258_0002.txt'`

## expanded_train:276009

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_276009_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_276009_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_276009_0003.txt'`

## expanded_train:27634

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_27634_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_27634_0002.txt'`

## expanded_train:277072

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_277072_0001.txt'`

## expanded_train:279645

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_279645_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_279645_0002.txt'`

## expanded_train:280212

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_280212_0001.txt'`

## expanded_train:288181

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_288181_0001.txt'`

## expanded_train:288810

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_288810_0001.txt'`

## expanded_train:290260

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_290260_0001.txt'`

## expanded_train:292072

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_292072_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_292072_0002.txt'`

## expanded_train:292210

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_292210_0001.txt'`

## expanded_train:293131

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_293131_0001.txt'`

## expanded_train:293280

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_293280_0001.txt'`

## expanded_train:29971

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29971_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29971_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29971_0003.txt'`

## expanded_train:29972

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29972_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29972_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29972_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_29972_0004.txt'`

## expanded_train:301114

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_301114_0001.txt'`

## expanded_train:305358

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_305358_0001.txt'`

## expanded_train:3055

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3055_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3055_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3055_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3055_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3055_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_3055_0006.txt'`

## expanded_train:308760

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_308760_0001.txt'`

## expanded_train:310062

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_310062_0001.txt'`

## expanded_train:314339

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_314339_0001.txt'`

## expanded_train:314632

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_314632_0001.txt'`

## expanded_train:316549

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_316549_0001.txt'`

## expanded_train:321099

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_321099_0001.txt'`

## expanded_train:321865

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_321865_0001.txt'`

## expanded_train:322966

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_322966_0001.txt'`

## expanded_train:323227

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_323227_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_323227_0002.txt'`

## expanded_train:324933

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_324933_0001.txt'`

## expanded_train:325005

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_325005_0001.txt'`

## expanded_train:326563

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_326563_0001.txt'`

## expanded_train:328779

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_328779_0001.txt'`

## expanded_train:330221

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_330221_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_330221_0002.txt'`

## expanded_train:332549

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_332549_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_332549_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_332549_0003.txt'`

## expanded_train:335959

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_335959_0001.txt'`

## expanded_train:336253

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_336253_0001.txt'`

## expanded_train:337439

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_337439_0001.txt'`

## expanded_train:341392

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_341392_0001.txt'`

## expanded_train:34153

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_34153_0001.txt'`

## expanded_train:345942

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_345942_0001.txt'`

## expanded_train:35007

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_35007_0001.txt'`

## expanded_train:355073

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_355073_0001.txt'`

## expanded_train:355729

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_355729_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_355729_0002.txt'`

## expanded_train:363696

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_363696_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_363696_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_363696_0003.txt'`

## expanded_train:363697

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_363697_0001.txt'`

## expanded_train:366229

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_366229_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_366229_0002.txt'`

## expanded_train:367209

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_367209_0001.txt'`

## expanded_train:37036

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_37036_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_37036_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_37036_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_37036_0004.txt'`

## expanded_train:371492

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_371492_0001.txt'`

## expanded_train:373143

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_373143_0001.txt'`

## expanded_train:37888

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_37888_0001.txt'`

## expanded_train:381900

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_381900_0001.txt'`

## expanded_train:388112

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_388112_0001.txt'`

## expanded_train:390922

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_390922_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_390922_0002.txt'`

## expanded_train:391461

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_391461_0001.txt'`

## expanded_train:393074

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_393074_0001.txt'`

## expanded_train:396213

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_396213_0001.txt'`

## expanded_train:396446

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_396446_0001.txt'`

## expanded_train:396589

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_396589_0001.txt'`

## expanded_train:396986

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_396986_0001.txt'`

## expanded_train:403307

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_403307_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_403307_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_403307_0003.txt'`

## expanded_train:405146

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_405146_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_405146_0002.txt'`

## expanded_train:413486

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_413486_0001.txt'`

## expanded_train:414888

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_414888_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_414888_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_414888_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_414888_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_414888_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_414888_0006.txt'`

## expanded_train:415097

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_415097_0001.txt'`

## expanded_train:416048

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_416048_0001.txt'`

## expanded_train:417495

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_417495_0001.txt'`

## expanded_train:420257

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_420257_0001.txt'`

## expanded_train:421006

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_421006_0001.txt'`

## expanded_train:423298

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_423298_0001.txt'`

## expanded_train:424056

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_424056_0001.txt'`

## expanded_train:424898

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_424898_0001.txt'`

## expanded_train:429453

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_429453_0001.txt'`

## expanded_train:430413

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_430413_0001.txt'`

## expanded_train:445995

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_445995_0001.txt'`

## expanded_train:45139

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_45139_0001.txt'`

## expanded_train:451952

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_451952_0001.txt'`

## expanded_train:459417

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_459417_0001.txt'`

## expanded_train:4626

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_4626_0001.txt'`

## expanded_train:465584

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_465584_0001.txt'`

## expanded_train:46588

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_46588_0001.txt'`

## expanded_train:466871

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_466871_0001.txt'`

## expanded_train:468910

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_468910_0001.txt'`

## expanded_train:46939

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_46939_0001.txt'`

## expanded_train:46959

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_46959_0001.txt'`

## expanded_train:470789

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_470789_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_470789_0002.txt'`

## expanded_train:472988

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_472988_0001.txt'`

## expanded_train:474147

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_474147_0001.txt'`

## expanded_train:475979

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_475979_0001.txt'`

## expanded_train:476606

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_476606_0001.txt'`

## expanded_train:478825

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_478825_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_478825_0002.txt'`

## expanded_train:480434

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_480434_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_480434_0002.txt'`

## expanded_train:481028

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_481028_0001.txt'`

## expanded_train:483415

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_483415_0001.txt'`

## expanded_train:484451

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_484451_0001.txt'`

## expanded_train:486303

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_486303_0001.txt'`

## expanded_train:489801

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_489801_0001.txt'`

## expanded_train:496719

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_496719_0001.txt'`

## expanded_train:502879

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_502879_0001.txt'`

## expanded_train:50436

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_50436_0001.txt'`

## expanded_train:50453

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_50453_0001.txt'`

## expanded_train:515868

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_515868_0001.txt'`

## expanded_train:521410

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_521410_0001.txt'`

## expanded_train:535530

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_535530_0001.txt'`

## expanded_train:539212

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_539212_0001.txt'`

## expanded_train:541395

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_541395_0001.txt'`

## expanded_train:543483

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_543483_0001.txt'`

## expanded_train:54499

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_54499_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_54499_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_54499_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_54499_0004.txt'`

## expanded_train:545512

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_545512_0001.txt'`

## expanded_train:549334

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_549334_0001.txt'`

## expanded_train:551448

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_551448_0001.txt'`

## expanded_train:55286

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55286_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55286_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55286_0003.txt'`

## expanded_train:553509

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_553509_0001.txt'`

## expanded_train:557202

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_557202_0001.txt'`

## expanded_train:55786

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55786_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55786_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_55786_0003.txt'`

## expanded_train:56462

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56462_0001.txt'`

## expanded_train:566084

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_566084_0001.txt'`

## expanded_train:56934

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56934_0001.txt'`

## expanded_train:56943

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_56943_0001.txt'`

## expanded_train:57214

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57214_0001.txt'`

## expanded_train:57239

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57239_0001.txt'`

## expanded_train:57884

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57884_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_57884_0002.txt'`

## expanded_train:579829

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_579829_0001.txt'`

## expanded_train:582983

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_582983_0001.txt'`

## expanded_train:58320

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58320_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58320_0002.txt'`

## expanded_train:58676

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58676_0001.txt'`

## expanded_train:58877

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_58877_0001.txt'`

## expanded_train:590878

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_590878_0001.txt'`

## expanded_train:592940

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_592940_0001.txt'`

## expanded_train:599034

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_599034_0001.txt'`

## expanded_train:611177

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_611177_0001.txt'`

## expanded_train:61135

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_61135_0001.txt'`

## expanded_train:61314

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_61314_0001.txt'`

## expanded_train:62138

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_62138_0001.txt'`

## expanded_train:62210

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_62210_0001.txt'`

## expanded_train:624802

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_624802_0001.txt'`

## expanded_train:625404

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_625404_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_625404_0002.txt'`

## expanded_train:625412

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_625412_0001.txt'`

## expanded_train:62695

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_62695_0001.txt'`

## expanded_train:628506

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_628506_0001.txt'`

## expanded_train:628514

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_628514_0001.txt'`

## expanded_train:629539

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_629539_0001.txt'`

## expanded_train:640807

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_640807_0001.txt'`

## expanded_train:640999

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_640999_0001.txt'`

## expanded_train:643211

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0003.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0004.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0005.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0006.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0007.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0008.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_643211_0009.txt'`

## expanded_train:644386

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_644386_0001.txt'`

## expanded_train:646224

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_646224_0001.txt'`

## expanded_train:648562

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_648562_0001.txt'`

## expanded_train:649493

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_649493_0001.txt'`

## expanded_train:655105

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_655105_0001.txt'`

## expanded_train:656483

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_656483_0001.txt'`

## expanded_train:660860

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_660860_0001.txt'`

## expanded_train:661672

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_661672_0001.txt'`

## expanded_train:664471

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_664471_0001.txt'`

## expanded_train:664847

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_664847_0001.txt'`

## expanded_train:666297

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_666297_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_666297_0002.txt'`

## expanded_train:667797

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_667797_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_667797_0002.txt'`

## expanded_train:667895

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_667895_0001.txt'`

## expanded_train:669442

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_669442_0001.txt'`

## expanded_train:675305

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_675305_0001.txt'`

## expanded_train:679348

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_679348_0001.txt'`

## expanded_train:681695

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_681695_0001.txt'`

## expanded_train:683974

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_683974_0001.txt'`

## expanded_train:684051

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_684051_0001.txt'`

## expanded_train:684052

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_684052_0001.txt'`

## expanded_train:685275

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_685275_0001.txt'`

## expanded_train:686812

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_686812_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_686812_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_686812_0003.txt'`

## expanded_train:688370

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_688370_0001.txt'`

## expanded_train:688467

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_688467_0001.txt'`

## expanded_train:688560

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_688560_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_688560_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_688560_0003.txt'`

## expanded_train:688651

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_688651_0001.txt'`

## expanded_train:690133

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_690133_0001.txt'`

## expanded_train:691110

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_691110_0001.txt'`

## expanded_train:69510

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_69510_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_69510_0002.txt'`

## expanded_train:695238

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_695238_0001.txt'`

## expanded_train:696228

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_696228_0001.txt'`

## expanded_train:698928

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_698928_0001.txt'`

## expanded_train:70061

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_70061_0001.txt'`

## expanded_train:702792

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_702792_0001.txt'`

## expanded_train:703113

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_703113_0001.txt'`

## expanded_train:703650

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_703650_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_703650_0002.txt'`

## expanded_train:707285

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_707285_0001.txt'`

## expanded_train:720547

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_720547_0001.txt'`

## expanded_train:720775

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_720775_0001.txt'`

## expanded_train:724081

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_724081_0001.txt'`

## expanded_train:725211

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_725211_0001.txt'`

## expanded_train:726364

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_726364_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_726364_0002.txt'`

## expanded_train:726587

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_726587_0001.txt'`

## expanded_train:726754

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_726754_0001.txt'`

## expanded_train:727409

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727409_0001.txt'`

## expanded_train:727556

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727556_0001.txt'`

## expanded_train:727640

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727640_0001.txt'`

## expanded_train:727699

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727699_0001.txt'`

## expanded_train:727700

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_727700_0001.txt'`

## expanded_train:728541

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_728541_0001.txt'`

## expanded_train:737704

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_737704_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_737704_0002.txt'`

## expanded_train:737989

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_737989_0001.txt'`

## expanded_train:738305

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_738305_0001.txt'`

## expanded_train:738526

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_738526_0001.txt'`

## expanded_train:739125

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_739125_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_739125_0002.txt'`

## expanded_train:740107

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_740107_0001.txt'`

## expanded_train:741129

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_741129_0001.txt'`

## expanded_train:741139

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_741139_0001.txt'`

## expanded_train:741143

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_741143_0001.txt'`

## expanded_train:74292

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_74292_0001.txt'`

## expanded_train:754183

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_754183_0001.txt'`

## expanded_train:754311

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_754311_0001.txt'`

## expanded_train:754787

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_754787_0001.txt'`

## expanded_train:755905

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_755905_0001.txt'`

## expanded_train:757186

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_757186_0001.txt'`

## expanded_train:75814

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75814_0001.txt'`

## expanded_train:75946

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75946_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75946_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_75946_0003.txt'`

## expanded_train:76079

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_76079_0001.txt'`

## expanded_train:763547

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_763547_0001.txt'`

## expanded_train:76356

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_76356_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_76356_0002.txt'`

## expanded_train:764810

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_764810_0001.txt'`

## expanded_train:765844

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_765844_0001.txt'`

## expanded_train:77325

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_77325_0001.txt'`

## expanded_train:775143

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_775143_0001.txt'`

## expanded_train:780450

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_780450_0001.txt'`

## expanded_train:781102

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_781102_0001.txt'`

## expanded_train:782868

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_782868_0001.txt'`

## expanded_train:78439

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_78439_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_78439_0002.txt'`

## expanded_train:79232

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_79232_0001.txt'`

## expanded_train:79433

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_79433_0001.txt'`

## expanded_train:794992

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_794992_0001.txt'`

## expanded_train:795350

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_795350_0001.txt'`

## expanded_train:799613

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_799613_0001.txt'`

## expanded_train:800342

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_800342_0001.txt'`

## expanded_train:802819

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_802819_0001.txt'`

## expanded_train:808636

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_808636_0001.txt'`

## expanded_train:808725

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_808725_0001.txt'`

## expanded_train:808746

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_808746_0001.txt'`

## expanded_train:808973

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_808973_0001.txt'`

## expanded_train:810483

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_810483_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_810483_0002.txt'`

## expanded_train:810960

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_810960_0001.txt'`

## expanded_train:811540

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_811540_0001.txt'`

## expanded_train:811663

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_811663_0001.txt'`

## expanded_train:813407

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_813407_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_813407_0002.txt'`

## expanded_train:814935

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_814935_0001.txt'`

## expanded_train:816540

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_816540_0001.txt'`

## expanded_train:816686

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_816686_0001.txt'`

## expanded_train:818447

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_818447_0001.txt'`

## expanded_train:81925

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_81925_0001.txt'`

## expanded_train:842799

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_842799_0001.txt'`

## expanded_train:84395

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_84395_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_84395_0002.txt'`

## expanded_train:844091

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_844091_0001.txt'`

## expanded_train:853701

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_853701_0001.txt'`

## expanded_train:854617

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_854617_0001.txt'`

## expanded_train:854902

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_854902_0001.txt'`

## expanded_train:857860

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_857860_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_857860_0002.txt'`

## expanded_train:864702

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_864702_0001.txt'`

## expanded_train:865331

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_865331_0001.txt'`

## expanded_train:867906

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_867906_0001.txt'`

## expanded_train:867943

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_867943_0001.txt'`

## expanded_train:868156

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_868156_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_868156_0002.txt'`

## expanded_train:87522

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_87522_0001.txt'`

## expanded_train:88977

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_88977_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_88977_0002.txt'`

## expanded_train:899619

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_899619_0001.txt'`

## expanded_train:900585

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_900585_0001.txt'`

## expanded_train:903577

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_903577_0001.txt'`

## expanded_train:908854

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_908854_0001.txt'`

## expanded_train:909046

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_909046_0001.txt'`

## expanded_train:909160

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_909160_0001.txt'`

## expanded_train:91541

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_91541_0001.txt'`

## expanded_train:916259

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_916259_0001.txt'`

## expanded_train:921234

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_921234_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_921234_0002.txt'`

## expanded_train:923743

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_923743_0001.txt'`

## expanded_train:923831

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_923831_0001.txt'`

## expanded_train:926464

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_926464_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_926464_0002.txt'`

## expanded_train:927949

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_927949_0001.txt'`

## expanded_train:930444

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_930444_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_930444_0002.txt'`

## expanded_train:934200

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_934200_0001.txt'`

## expanded_train:938784

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_938784_0001.txt'`

## expanded_train:940126

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_940126_0001.txt'`

## expanded_train:940193

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_940193_0001.txt'`

## expanded_train:940524

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_940524_0001.txt'`

## expanded_train:947187

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_947187_0001.txt'`

## expanded_train:96436

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_96436_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_96436_0002.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_96436_0003.txt'`

## expanded_train:96579

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_96579_0001.txt'`

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_96579_0002.txt'`

## expanded_train:969120

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_969120_0001.txt'`

## expanded_train:971742

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_971742_0001.txt'`

## expanded_train:973143

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_973143_0001.txt'`

## expanded_train:976300

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_976300_0001.txt'`

## expanded_train:978518

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_978518_0001.txt'`

## expanded_train:97984

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_97984_0001.txt'`

## expanded_train:989836

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_989836_0001.txt'`

## expanded_train:989984

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_989984_0001.txt'`

## expanded_train:989994

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_989994_0001.txt'`

## expanded_train:990150

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_990150_0001.txt'`

## expanded_train:990168

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_990168_0001.txt'`

## expanded_train:990705

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_990705_0001.txt'`

## expanded_train:992018

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992018_0001.txt'`

## expanded_train:992169

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992169_0001.txt'`

## expanded_train:992719

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_992719_0001.txt'`

## expanded_train:993138

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_993138_0001.txt'`

## expanded_train:993154

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_993154_0001.txt'`

## expanded_train:993259

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_993259_0001.txt'`

## expanded_train:993346

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_993346_0001.txt'`

## expanded_train:993724

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_993724_0001.txt'`

## expanded_train:994058

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_994058_0001.txt'`

## expanded_train:994513

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_994513_0001.txt'`

## expanded_train:994585

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_994585_0001.txt'`

## expanded_train:995320

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995320_0001.txt'`

## expanded_train:995527

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995527_0001.txt'`

## expanded_train:995562

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995562_0001.txt'`

## expanded_train:995586

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_995586_0001.txt'`

## expanded_train:996487

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996487_0001.txt'`

## expanded_train:996632

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996632_0001.txt'`

## expanded_train:996680

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_996680_0001.txt'`

## expanded_train:997083

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_997083_0001.txt'`

## expanded_train:998241

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998241_0001.txt'`

## expanded_train:998511

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998511_0001.txt'`

## expanded_train:998693

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998693_0001.txt'`

## expanded_train:998715

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998715_0001.txt'`

## expanded_train:998992

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_998992_0001.txt'`

## expanded_train:999121

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999121_0001.txt'`

## expanded_train:999313

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999313_0001.txt'`

## expanded_train:999347

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999347_0001.txt'`

## expanded_train:999378

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999378_0001.txt'`

## expanded_train:999580

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999580_0001.txt'`

## expanded_train:999600

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/expanded_train_999600_0001.txt'`

## validation:1872

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/validation_1872_0001.txt'`

## validation:2606

`cat -- '/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_birth_full_counter_v1/reading_packets_v1/validation_2606_0001.txt'`

