# 2026-10-22 공개 벤치마크 재사용·신규 표본 읽기 전용 감사

상태: `SOURCE_AUDITED / NEW_MODEL_EVALUATION_NOT_RUN`. 기존 실행 결과와 공개 캐시를 읽고, 표준 라이브러리로 JSON·행수·ID·본문 중복·해시·기준선을 계산했다. 이번 감사가 쓴 파일은 이 문서 하나다. 프로젝트 코드 실행/import, 실제 tokenizer/model/CP tensor 로딩, GPU, 학습, 다운로드, Git, 보호 `datasets/TinyDataset` 접근은 하지 않았다. 아래 새768은 문서에 고정한 선택안이며 아직 별도 실행 패킷 파일이나 새 평가 결과가 아니다.

## 1. 결론과 세 경로

| 경로 | 이번에 주장할 수 있는 것 | 추가 준비/제약 |
|---|---|---|
| A: 기존 결과 재집계 + 로컬 문법48/대화48 | 기존 공개 MC의 정확한 조건·분모·raw lineage를 재사용하고 새 국소 진단을 별도로 추가 | 기존768 재추론 불필요. 로컬96은 공개 벤치마크 수행이나 공식 BabyLM을 대신하지 않는다. 최종 fixture의 GPU 진단은 총괄 확인 시점 `NOT_RUN` |
| B: 다른 고정 공개 문항768 | 같은 로컬 공개 평가 split에서 옛768과 ID/정규문맥이 겹치지 않는 PIQA/HellaSwag/ARC-Easy 각256의 새 표본을 측정 | 권장. 기존 literal adapter/scorer + strict UI loader를 호출하는 얇은 실행 orchestration만 필요. source freeze/CPU mock·회귀 준비30~60분은 작업량 추정이며 구현 완료 주장이 아니다 |
| C: 공식 BabyLM | 공식 과제·자료·scorer를 확인한 별도 벤치마크 | 다운로드 미승인/대기. BLiMP/MSGS/EWoK 계약 및 공식 학습·평가 규정 확인 전 로컬 문법 점수를 공식 점수로 부르지 않는다 |

총괄이 선택한 우선순위는 B의 신규768 준비다. 새3모델은 기존 평가와 같은 가중치이므로 새768과 옛768의 점수 차이는 학습 향상이 아니라 **다른 공개 표본에서 새로 측정한 변별력**이다. 사전학습 전체 오염과 과거 다른 평가에서의 미사용 여부는 감사하지 못했다. 기존 모델 선택에 옛768 점수가 사용됐으므로 옛셋은 모델 선택용 관측이고 새셋도 데이터·평가 설계가 보이는 개발 평가이지 자동으로 certified blind가 아니다.

## 2. 기존 9,216요청의 실제 범위

원천 계약은 [authorized benchmark](/home/uranus/tinyLM/scripts/diag_p106b_authorized_benchmark.py:33)의 `SEED=20261016`, `MC_N=256`, `GEN_N=64`, `CONTEXT=1024`다. [sampled_indices](/home/uranus/tinyLM/scripts/diag_p106b_authorized_benchmark.py:85)는 각 원천의 전체 0-based index를 `random.Random(20261016).shuffle`한 뒤 처음256/64개를 골라 정렬한다. [source_items](/home/uranus/tinyLM/scripts/diag_p106b_authorized_benchmark.py:98)는 MC `_iid=task#index`를 보존한다.

원천·옛 선택 index 전체의 정본은 [frozen report](/home/uranus/tinyLM/HF/sft_ready/p106b_authorized_validation_v1_s1337/public_benchmark/report.json)의 `sources.<task>.indices`다. 이 report 실물 SHA256은 `a2d57c8e2a8f767eba4d679a1660ab2a85a0b756a713fb0196d013dfb2e3a926`. [cases_000000.jsonl](/home/uranus/tinyLM/HF/sft_ready/p106b_authorized_validation_v1_s1337/public_benchmark/cases_000000.jsonl)은 고유1920행, 실물 SHA256 `547691812812c73250b8b1bd19dcd088a1f69c1c831562e1f4f1430ff5386b77`: MC7×256=1792, KorQuAD/GSM 생성2×64=128이다. KorQuAD 원 qa id와 평탄화 index는 별개이며 `korquad_free#index`가 평가 case 식별자다.

| 공개 benchmark id | strict UI exact name | 요청/채점 | PIQA/HellaSwag/ARC 각256 정답 | 영어 합계 |
|---|---|---:|---|---:|
| native595_float | native595-f | 768/768 | 161 / 72 / 112 | 345/768 |
| native595_ternary | native595-q | 768/768 | 147 / 69 / 108 | 324/768 |
| newbroad_float | new595-broad-f | 1920/1919 | 156 / 70 / 107 | 333/768 |
| newbroad_ternary | new595-broad-q | 1920/1919 | 148 / 67 / 97 | 312/768 |
| oldbroad_float | old299-broad-f | 1920/1919 | 150 / 66 / 109 | 325/768 |
| oldbroad_ternary | old299-broad-q | 1920/1919 | 140 / 71 / 97 | 308/768 |

직접 읽은 정본은 [native595-f report](/home/uranus/tinyLM/test_result/evidence/p106b_native595_public_v1_s1337/evaluate_native595_float/report.json)를 비롯한 같은 디렉터리의 `evaluate_<benchmark id>/report.json` 6개다. 모두 `CURRENT_PUBLIC_MODEL_COMPLETE`. 요청 합계는 2×768+4×1920=**9216**이고 채점 합계는9212다. Broad4개의 각1행 제외는 `full_prompt_plus128_exceeds1024`인 KorQuAD다. 9216을 고유 질문 수나 MC만의 수로 쓰지 않는다.

[독립 raw 감사](/home/uranus/tinyLM/test_result/evidence/p106b_native595_public_independent_audit_v2_s1337/report.json)는 위9216/9212와 같은 합계이며 상태는 `SIX_CLOSED_MODELS_RAW_RECOUNTED_ORIGINAL_FAMILY_READBACK_HOLD`다. 이는 여섯 모델 raw 재집계와 기존 가족 정규 readback의 HOLD를 구별한다. 이 문서에서는 저장된 report/독립 감사 결과를 대조했으며 이번에 9216 raw 전부를 새로 재집계했다고 주장하지 않는다. 과거 Falcon398/768은 동일 옛 영어768의 캐시 재사용이고 새 호출0이다. **Falcon398을 새768과 직접 비교하지 않는다.**

## 3. 실제 원천·옛 ID 범위·잔여량

아래 수량은 공개 캐시 실물의 LF 기반 JSON 레코드를 직접 세고, 옛 report의256개 index 집합을 뺀 것이다. 모두 0-based index이며 min~max는 연속 범위가 아니라 선택 index의 끝점이다. 원천 repo/split 이름은 [로컬 fetch 선언](/home/uranus/tinyLM/scripts/fetch_bench_data.py:112)의 provenance다. 이번 감사에서 외부 최신 revision을 검증하지 않았다.

| task / 로컬 자료 | 로컬 declared source / split | 전체 | 옛 선택 min~max | 옛256 외 잔여 |
|---|---|---:|---|---:|
| piqa / datasets/bench/piqa.jsonl | ybisk/piqa / validation | 1838 | 0~1814 | 1582 |
| hellaswag / datasets/bench/hellaswag.jsonl | Rowan/hellaswag / validation | 10042 | 2~10025 | 9786 |
| arc_easy / datasets/bench/arc_easy.jsonl | allenai/ai2_arc ARC-Easy / test | 2376 | 0~2368 | 2120 |
| kobest_copa / datasets/bench/kobest_copa.jsonl | skt/kobest_v1 copa / test | 1000 | 2~994 | 744 |
| kobest_hellaswag / datasets/bench/kobest_hellaswag.jsonl | skt/kobest_v1 hellaswag / test | 500 | 2~499 | 244 |
| klue_nli / datasets/bench/klue_nli.jsonl | klue/klue nli / validation | 3000 | 0~2992 | 2744 |
| klue_ynat / datasets/bench/klue_ynat.jsonl | klue/klue ynat / validation | 9107 | 2~9072 | 8851 |

**7 MC 전체27,863행, 옛1,792행, 잔여26,071행이며 영어3과제 잔여는13,488행이다.** 한국어4과제 잔여는12,583행이다. 자유 생성은 KorQuAD v1 dev 평탄화5774 중 옛64를 뺀5710, GSM8K test1319 중 옛64를 뺀1255가 남는다. 이들은 새로운 생성 평가 비용/채점 계약이 필요하므로 새 MC768에 합산하지 않는다.

영어 원천 SHA256:

| task | 원천 실물 SHA256 | 옛256 index 배열 SHA256 |
|---|---|---|
| piqa | `61533005e22f175534909b1ec8eacb6da03c233933558d1bafb15787453b1f55` | `e21bf779c51a7b8fc98440739c41403b7a19d254c8639816eeee296879461e04` |
| hellaswag | `d5c08c3e5771307e73886dc9d2744df8ca5f372a7857f32fe77df8c58942f950` | `fda92dda8d12d770e60bab2cd8e58ceec31488f0fe4d0792c0c545e1002932e8` |
| arc_easy | `874354cf372667530bd6cbd2d78dca2d657c5e2e746f53cf01d1e9d3a90cbc3d` | `aba23c619ce09c55d5c8dea72a331de9a3a0a4d7759ec9812bf262cb47fb8482` |

index 배열 해시는 `json.dumps(indices,separators=(',',':')).encode('utf-8')`의 SHA256이다. 원천 SHA가 바뀌면 row index만 같아도 같은 질문으로 인정하지 않는다.

## 4. 신규 영어768의 고정 선택·중복 통제

실행 전 선택안: seed20261022, task 순서 `piqa,hellaswag,arc_easy`. 본문 정규화는 `NFKC → re.sub(r'\s+',' ',text) → strip → casefold`다. PIQA는 `goal`, ARC는 `question`, HellaSwag는 adapter와 같은 `(ctx_a+' '+ctx_b.capitalize()) if ctx_b else ctx`를 본문으로 쓴다. Hella의 activity label/보기 차이로 같은 본문을 새 질문처럼 인정하지 않도록 본문만 비교한다. 이는 exact normalized-context 중복 차단이지 paraphrase·부분 문맥·출처 단위 중복 제거가 아니다.

1. 옛3과제768의 정규본문 합집합을 먼저 차단한다.
2. 각 원천에서 옛 index를 제외하고, 차단 본문이 아닌 index를 오름차순으로 열거한다.
3. task마다 새 `random.Random(20261022)`로 이 목록을 shuffle한다.
4. 전역 seen=옛 본문 및 앞 task의 신규 본문을 유지하며 처음256개 서로 다른 본문을 greedy 선택하고, 최종256 index는 정렬한다.
5. gold/예측/정답 여부는 선택에 사용하지 않았다. 아래 기준선은 선택 후 계산했다. 아직 tokenizer 길이 적격성을 측정하지 않았으므로 실행 전1024 초과·빈 continuation 검산과 제외 사유/분모 고정이 필요하다. 길이 초과분을 결과를 본 뒤 유리한 문제로 교체하지 않는다.

| task | 옛 index 제외 후 | 옛 본문과 중복 추가 제외 | 잔여행 / 고유본문 | 새 선택 | 옛 ID/본문 중복 |
|---|---:|---:|---:|---:|---|
| piqa | 1582 | 12 | 1570 / 1547 | 256 | 0 / 0 |
| hellaswag | 9786 | 0 | 9786 / 9762 | 256 | 0 / 0 |
| arc_easy | 2120 | 0 | 2120 / 2115 | 256 | 0 / 0 |

신규768 내부에도 위 정규본문 중복0. source index/정규본문 차단은 이 감사의 옛768 범위에 대한 증거이며 모든 역사적 평가 및 학습 데이터와의 중복0 주장이 아니다.

canonical 객체 해시는 전부 `json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')`의 SHA256이다. 새 ID 목록은 아래 task 순서와 오름차순 index에 대해 `task+'#'+str(index)`로 구성한다.

| task | 신규256 ordered IDs SHA256 | 신규256 원천 row 배열 SHA256 |
|---|---|---|
| piqa | `78509609c29596effa521c12785f74e2b9dc1cf5579b4274a116af0de5aca12e` | `b14908cce8a92c55909b83e9346c8076c47c4a3160c4ff0a82833947b40c182b` |
| hellaswag | `036b9e80df27760ec54691406a313697ae4086abf110b54335b2e019335c0c7b` | `c4d2dbcdc257bd766fab0df39f34ac4a4b84ad11b8de9da97660bc61f8f10245` |
| arc_easy | `24259278591a854d1cb6128d3595788da0191a6ca222653100e3359af5fb4e09` | `f52c69db5c9bdfeaa9f1d173cbd44009b56628e8f6c76b298620662bc5bac6ac` |

전체 ordered768 ID SHA256=`b53f6b3430bb376e91aa3859f9266888c72320db5f85aba5256aabf29c9af5d5`.

선택 계약 객체는 `{schema:'P106B_PUBLIC_NEW768_SELECTION_AUDIT_V1',seed:20261022,task_order:[...],source_sha256:{task:소문자원천SHA},indices:{task:아래정렬배열}}`이며 SHA256=`e127c90a0dda31ca6ec608c50a93b65aca8c344a89d99cc9e404382a5bb9d763`이다. 논리 원천 패킷은 task 순서대로 `[{task:task,index:i,source_row:원천원본객체}, ...]`이며 canonical UTF8 505286bytes, SHA256=`660cd423be22905f325405fbbee471f0dff9c06424de5b2dffcdd98bf5db2ab2`. 이는 **메모리에서 계산한 객체 해시**다. 아직 존재하지 않는 packet 파일의 실물 SHA나 adapted-items SHA라고 표시하지 않는다. 후속 구현은 이 계약을 검증하고 실제 JSONL bytes/manifest SHA를 별도로 남겨야 한다.

### 고정 index 전체

각 배열 원소의 실제 ID는 해당 `task#index`다. 새768 모두를 생략 없이 기록한다.

```json
{"task":"piqa","indices":[5,16,21,34,36,40,51,52,54,56,60,66,75,77,123,142,153,154,172,183,193,197,198,206,231,239,242,244,246,248,258,271,274,275,278,295,306,315,333,337,342,350,352,356,363,367,375,377,382,387,388,390,393,394,405,412,419,433,435,437,444,450,463,473,476,493,497,501,503,508,511,513,522,525,534,576,599,612,619,622,627,644,645,663,665,683,707,731,748,751,756,768,771,774,783,784,787,790,794,834,845,847,853,863,868,875,890,919,938,940,943,946,951,953,971,974,978,982,988,991,997,998,1001,1004,1005,1015,1019,1020,1024,1028,1031,1043,1050,1076,1105,1121,1123,1124,1127,1131,1137,1143,1149,1150,1163,1165,1167,1176,1178,1180,1181,1184,1190,1192,1195,1197,1199,1212,1213,1220,1238,1244,1251,1254,1263,1265,1285,1295,1312,1316,1318,1319,1322,1328,1342,1350,1353,1354,1358,1359,1372,1376,1380,1389,1396,1399,1418,1419,1426,1435,1438,1463,1467,1469,1474,1477,1480,1486,1499,1505,1512,1514,1517,1525,1531,1533,1535,1537,1543,1545,1548,1554,1556,1571,1577,1586,1589,1592,1596,1597,1599,1601,1622,1633,1635,1658,1667,1669,1670,1677,1679,1682,1689,1697,1708,1712,1716,1718,1728,1729,1730,1736,1738,1758,1760,1765,1785,1790,1791,1795,1801,1809,1816,1819,1826,1828]}
{"task":"hellaswag","indices":[25,46,110,118,171,301,334,394,564,572,577,645,679,686,687,788,824,842,915,956,979,1045,1201,1260,1319,1333,1334,1338,1396,1402,1479,1562,1574,1624,1630,1637,1668,1719,1726,1742,1755,1790,1841,1889,1921,1927,2052,2094,2221,2281,2328,2330,2389,2425,2491,2516,2523,2602,2664,2686,2811,2833,2847,2877,2919,2921,2943,3008,3016,3043,3058,3115,3121,3231,3292,3307,3364,3415,3422,3424,3443,3454,3464,3465,3519,3567,3572,3599,3626,3630,3708,3738,3753,3765,3781,3824,3830,3896,3909,3932,3961,3991,4172,4194,4211,4235,4277,4292,4398,4428,4450,4516,4582,4613,4617,4653,4684,4719,4721,4759,4763,4871,4908,4929,4953,4972,5012,5020,5113,5123,5170,5239,5295,5305,5309,5335,5371,5374,5404,5464,5582,5616,5629,5644,5685,5705,5738,5751,5752,5758,5783,5802,5922,5995,6015,6082,6171,6232,6295,6350,6367,6382,6395,6419,6495,6554,6624,6628,6632,6726,6736,6836,6917,6994,7014,7028,7036,7064,7069,7095,7289,7298,7329,7403,7435,7478,7517,7526,7546,7572,7641,7710,7751,7760,7775,7819,7845,7894,7901,8052,8069,8072,8125,8143,8226,8256,8274,8304,8367,8464,8497,8525,8547,8551,8552,8590,8613,8672,8705,8735,8848,8863,8881,8893,8976,9059,9125,9179,9210,9231,9233,9372,9425,9446,9460,9467,9524,9537,9543,9562,9649,9713,9751,9753,9763,9782,9800,9908,9912,9915,9926,9964,9970,9997,10011,10040]}
{"task":"arc_easy","indices":[7,11,14,19,32,33,41,59,65,66,85,96,100,105,106,112,113,118,119,131,136,137,148,153,166,168,172,178,181,182,189,217,222,227,241,250,251,255,258,264,267,275,280,282,289,290,294,299,301,309,323,372,390,401,413,416,421,435,442,443,447,455,456,473,474,477,489,490,517,521,524,535,540,561,574,582,602,626,639,645,657,658,661,688,690,695,705,719,729,733,746,749,754,761,772,776,794,797,800,804,819,821,839,848,891,896,897,899,902,906,942,948,955,964,1002,1007,1012,1018,1026,1031,1038,1044,1046,1051,1073,1085,1086,1098,1144,1145,1159,1162,1163,1175,1193,1199,1201,1204,1221,1228,1250,1262,1269,1284,1300,1332,1336,1350,1351,1359,1361,1374,1392,1405,1412,1423,1431,1435,1439,1448,1450,1455,1481,1495,1510,1517,1526,1552,1559,1564,1565,1573,1582,1591,1601,1603,1609,1618,1627,1638,1660,1671,1677,1721,1727,1749,1757,1768,1776,1782,1794,1807,1827,1831,1839,1858,1868,1869,1875,1900,1924,1926,1927,1931,1948,1967,1973,1985,1986,1989,2002,2018,2033,2043,2045,2046,2050,2057,2062,2066,2070,2091,2099,2108,2110,2135,2149,2150,2171,2173,2186,2189,2192,2213,2215,2220,2227,2239,2243,2254,2257,2273,2277,2283,2299,2303,2305,2307,2320,2328,2333,2335,2346,2355,2371,2374]}
```

## 5. 기준선과 실제 추론 예산

후보 순서는 기존 adapter 그대로다. 문자길이 기준선은 **adapter continuation 전체의 Python len**, 동률은 scorer와 같이 작은 후보 index를 먼저 택한다. token 길이 기준선은 실제 tokenizer가 필요하므로 이 감사에서는 계산하지 않았다. 짧음/김 기준의 동률 건수도 버리지 않는다.

| task | 새 gold 분포(index:count) | 옛 gold 최빈 index 고정 → 새 정답 | 새 표본 최빈 상한 | 최단/최장 문자 후보 | 최단/최장 동률 문항 | 후보 forward |
|---|---|---:|---:|---|---|---:|
| piqa | 0:124,1:132 | 0 →124 | 132 | 136 /121 | 31 /31 | 512 |
| hellaswag | 0:79,1:60,2:62,3:55 | 0 →79 | 79 | 67 /54 | 6 /2 | 1024 |
| arc_easy | 0:65,1:63,2:72,3:56 | 1 →63 | 72 | 69 /70 | 40 /45 | 1023 |
| 합계 | 768문항 | 266/768 | 283/768 | 272/768 /245/768 | 과제별 보존 | 2559/model |

`새 표본 최빈 상한`은 새 정답 라벨을 본 뒤 선택한 oracle diagnostic이므로 사전 고정 예측기의 점수로 제시하지 않는다. 대신 옛 표본의 최빈 index를 고정한266/768을 함께 낸다. 새 ARC는255문항4지선다+1문항3지선다다. 보기 수를 무조건4로 고쳐1024회라고 예산을 쓰지 않는다.

top3 `native595-f/native595-q/new595-broad-f`의 전체 예정 요청은2304문항, 후보 forward는**7677회**, strict load는각1회다. 각 후보는 teacher-forced 전체 prompt+continuation 점수화1회이며 생성 토큰 수·batch 수가 아니다. PMI off여서 무문맥 baseline forward를 추가하지 않는다. 1024 적격성 제외가 있으면 실제 forward/분모/사유가 달라질 수 있으며 요청768을 채점768로 미리 쓰지 않는다.

옛 native F/Q의 `whole_seconds`는 각각46.322579/48.425419초이고 newBroadF는200.061496초지만 후자는 MC1792+생성127까지 포함한다. 이 수치를 신규 MC768의 확정 시간으로 복사하지 않는다. strict CPU/GPU core SHA·I/O·길이 분포도 비용이다. 총괄이 첫 고정 prefix의 실측으로 나머지 입장/시간cap을 판단하는 것이 적절하다. 비용 확인용 prefix도 본768의 일부로 회수해 불필요한 같은 질문 재실행을 막는다.

## 6. 기존 scorer/API를 그대로 연결할 정확한 경로

현재 연구6종을 strict UI context와 MC로 함께 노출한 완성 CLI는 발견하지 못했다. 그러나 새 모델 loader나 task adapter, NLL scorer를 만들 필요는 없다. 아래는 향후 얇은 orchestration의 **호출 계약**이며 이번 감사에서 실행하지 않았다.

- 로컬 row 읽기: [eval_bench_suite.load_rows(task, heldout_version='latest')](/home/uranus/tinyLM/scripts/eval_bench_suite.py:142). LF file iteration으로 JSON을 읽는다.
- 원본 adapter: [suite.ADAPTERS[task](raw_row)](/home/uranus/tinyLM/scripts/eval_bench_suite.py:195). 별도 prompt 재작성/ChatML wrapping 없이 결과에 `_iid=f'{task}#{source_index}'`만 원래 규약대로 붙인다.
- strict loader: [ui.resolve_model(name)](/home/uranus/tinyLM/scripts/interactive_research_infer.py:89), [ui.selected_runtime(spec,root=ROOT)](/home/uranus/tinyLM/scripts/interactive_research_infer.py:392). manifest/header/실제 CPU·GPU core/정확 Q-F route를 검산하며 과거 family 권한 함수를 호출하지 않는다. top3의 exactname은 위와 같다. `old299-broad-q/f`, `new595-broad-q`, `native595-q/f`까지 등록6종이 정본이다.
- FP32 wrapper: [diag_p106b_current_benchmark.FP32Forward(active['model'])](/home/uranus/tinyLM/scripts/diag_p106b_current_benchmark.py:395). `seq_ce`의 바깥 CUDA BF16 autocast도 닫고 실제 FP32 logits를 검사한다. ui context의 TF32 OFF 유지.
- 직접 호출: `suite.run_mc(task,items,wrapped,active['tokenizer'],'cuda',1024,active['torch'],F,True)`. 마지막 `True`는 **no_pmi=True**이며 `F`는 `torch.nn.functional`. [현재 공개 평가의 실제 호출](/home/uranus/tinyLM/scripts/diag_p106b_current_benchmark.py:563)과 같다.
- primary는 `result['h_ok']` 및 `result['rows'][i]['pred_harness']`, 즉 SUM_NLL argmin이다. `result['ok']`/`pred_internal`은 mean/PMI 내부 규약이라 primary로 잘못 읽지 않는다. secondary `pred_harness_norm`은 문자길이 정규화이며 `mean_nll`과 별개다. literal scorer의 동률은 첫 index다. 동률 진단을 별도 보존하되 primary를 조용히 바꾸지 않는다.
- [seq_ce](/home/uranus/tinyLM/scripts/eval_bench_suite.py:427)는 prefix/continuation을 별도 tokenize하고 continuation만 CE를 합산한다. BOS/EOS 임의 추가 없음; 빈 prompt만 newline 첫 token fallback. 빈 continuation/전체길이1024 초과는 `None`, 자르지 않음. 문장전체 최소쌍 likelihood와 이 MC continuation likelihood는 다른 측정이다.
- `active['route'].assert_active()`를 각 chunk에서 확인한다. checkpoint/core/tokenizer/manifest SHA와 `sum_nll/mean_nll/n_tokens/n_chars`, 선택 ID·원천 SHA·gold·skips를 원답(raw score)으로 보존한다. `selected_runtime`의 종료 검산 전에는 성공 report를 쓰지 않는다. 종료 뒤 active dict가 clear되므로 lineage를 context 안에서 copy한다.

과거 `diag_p106b_native595_public.py`에는 [END=2026-10-21 08:00UTC](/home/uranus/tinyLM/scripts/diag_p106b_native595_public.py:45)가 있으므로 과거 family runner를 다시 열거나 기한/authority를 monkeypatch하지 않는다. `eval_bench_suite.py`의 generic 모델 CLI로 scalar float CP를 읽는 우회도 하지 않는다. 후속 작은 controller가 맡을 일은 source freeze/인자·시간cap 검증/strict context orchestration/기존 ShardWriter(<20MB)/atomic 종료 report/CPU mock 시험뿐이다.

## 7. 로컬 신규 진단과 다른 공개 캐시의 실제 규모

최종 fixture는 [문법48](/home/uranus/tinyLM/scripts/fixtures/p106b_grammar_pairs48_20261022.jsonl)과 [대화48](/home/uranus/tinyLM/scripts/fixtures/p106b_daily_chat48_20261022.jsonl)이다. 문법은 영어 subject_verb_agreement24+agreement_attraction24이며 source가 `ROOT_AUTHORED_LOCAL_DIAGNOSTIC_20261022_NOT_OFFICIAL_BABYLM`, split이 `evaluation_only_development_not_certified_blind`로 명시돼 있다. SHA256=`dc9112fa1a3224618913a5edfb36becfae9684a1d27f61a7bbd3772b2eb3ea49`. 대화는 KO/EN24씩, code-defined expected_exact31+manual17이며 SHA256=`4c177f0d467f81e50c723c327a2509a102d14e7fe53457920c8fadcd429a646b`. 설명형17개는 자동 정확도 점수를 붙이지 않는다.

`data_cache/p106b_text_work_20261022/evaluation/daily_chat48.jsonl`에는 expected_exact36인 옛 초안이 남아 있다. 최종 fixture와 혼용하지 않는다. 예정 출력 namespace는 `test_result/evidence/p106b_existing_probes_20261022/`이며 이 감사에서 실행·완료를 확인하지 않았다. 문법48은 국소 문법 선택 진단, 대화48은 single-turn 첫답/종료/원답 인간 검토다. 공식 BabyLM, 장문·멀티턴 대화, 일반 지능을 대체하지 않는다.

추가로 로컬에 존재하고 LF JSON 파싱을 확인한 공개 MC 캐시는 ARC-Challenge1172, WinoGrande1267, BoolQ3270, MMLU14042, MMLU-Redux5700, MuSR250이다. 이들은 **이번 옛7과제 pack 밖**이라는 뜻이지 모든 과거 평가에서 미사용이라는 뜻이 아니다. BoolQ 라벨 불균형/길이, WinoGrande의 후보별 prefix+suffix 특수 adapter, MuSR 긴 문맥과1024 제한, MMLU-Redux 수정정답 규약은 별도 준비 대상이다. 기존 `run_mc`는 WinoGrande의 `pairs`를 이미 지원한다.

중복 수치: `arc_easy_full.jsonl`5197의 ID 집합에 `arc_easy` test2376 전체가 들어 있다. 나머지2821은 선언상 train2251+validation570이므로 독립 신규 test5197로 합산하지 않는다. MMLU는 question exact 고유13869, Redux는5648, 교집합5463이며 Redux에만 있는 exact question은185다. 완전 동일 JSON row 중복은 MMLU27/Redux2다. Redux5700을 독립 신규 지식문항5700으로 더하지 않는다. `stage1_heldout` 여러 버전4500과 HumanEval/HumanEval+164도 단순 합계 고유량으로 세지 않는다.

계수 중 도구 오류와 정정: 첫 시도에서 `str.splitlines()`가 MMLU/Redux 문자열 안 Unicode 줄구분 문자까지 나눠 JSON 파싱 오류를 냈다. LF 기반 file iteration으로 다시 세면 각각14042/5700 전 행 유효, 오류0이며 원본 손상이 아니다. 실제 `suite.load_rows`도 LF iteration이므로 이 오판을 코드 결함으로 보고하지 않는다. 원천 수정 없이 정정했다.

## 8. 남은 승인·실행 경계

이 문서는 source-only 분석과 고정 선택을 끝냈다. 새768 실제 JSONL/manifest, 얇은 controller/CPU mock, tokenizer 길이 적격성 freeze, 실모델 새 점수/시간 측정, 공식 BabyLM 자료 취득·원논문 scorer 검증은 아직 별도 단계다. GPU/CP 실행은 총괄만 수행한다. 후속 결과에는 옛768/새768/로컬 문법48/대화48을 다른 표로 보존하고, raw 결과·선택 ID·원천과 actual CP/core/tokenizer/precision lineage를 함께 남긴다.
