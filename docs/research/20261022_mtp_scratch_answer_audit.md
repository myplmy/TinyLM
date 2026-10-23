# 2026-10-22 V3 scratch NTP/MTP 원답 감사

이 두 팔은 실제704업데이트를 마쳤지만, 제공된 문맥 QA를 정확히 답하는 모델로 채택할 근거는 확보하지 못했다. 주석 strict match는 각각0/512이고 추출 실패는0이다. MTP의 종료율·NTP DEV CE는 더 좋았으나 실제로 읽은 고정 원답에서는 한국어 무관 단편과 영어 반복이 남았다. 이 관측을 일반지능0이나 모든512답의 의미상 정답0으로 바꾸지 않는다.

**V3 자료 계약 정정이 선행한다.** PUBLIC source_index192와198의 첫 assistant가 실제 감독에 포함돼 있었다. “교정 전 오답은 모두 제외했다/clean”이라는 전역 주장은 성립하지 않는다. 태그명과 기존 영수증은 역사 원형으로 보존하고, 이 V3 결과를 정제 교과의 품질 채택 증거로 쓰지 않는다.

## 1. 실제로 읽은 범위와 권한

- 학습 report 두 개, first-answer report 두 개, 해당 raw JSONL·manifest를 읽었다. 모델·GPU·CP tensor·평가/학습 코드 재실행0이며, 원본 자료/코드/기록은 수정하지 않았다.
- 자연 QA는 **512×2=1,024개 저장 원답**을 JSON으로 읽어 원형/순서/strict/추출 상태/종료/빈 답/문자 빈도를 전량 검산했다. 이는 전량 의미 검수가 아니다.
- 사전에 지정한 0-based `0,16,...,496` **32문항×두 팔=64개 자연 QA 답**은 질문·원래 지문·주석/alias와 함께 직접 읽었다. 모델답을 보고 표본을 다시 고르지 않았다. 나머지960개 자연 QA 답의 개별 의미 판독은 수행하지 않았다.
- 학습 후 고정8문항의 **attempt1만 두 팔 합16개** 직접 읽었다. 초기8문항·다른 재시도를 모두 직접 판독했다고 주장하지 않는다.
- 추가로 MTP의 유일한 rubric 재시도 성공인 attempt2의 “5”를 확인했다. 따라서 직접 내용 판독은 **첫답80개 + 재시도1개**다.
- 문서 쓰기는 이 감사 파일 하나다. 정식 결과092·계획·기준표·COMPASS의 연쇄 갱신은 총괄 소유다.

`log-to-result`의 JSON 정본/조건/원답 구분 절차를 적용했다. 이번 파일은 별도 결과번호의 신설이 아니라 제한된 읽기 감사이며, 원본 closure·정식 판정을 대신하지 않는다.

## 2. 영수증 결합과 비교 조건

| 축 | scratch NTP | scratch MTP |
|---|---|---|
| status | SFT_MTP_TRAINED_EVAL_PENDING | 동일 |
| 공통 본체 초기 SHA | `028C46B232D6D4C5205CAF15A7C259E3B1687347FC4838D00B3F3CB938C0D1C5` | 동일 |
| corpus SHA | `7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20` | 동일 |
| 실제 업데이트 |704|704|
| 실제 입력 x |21,621,776|21,621,776|
| 주 NTP assistant target |2,210,436|2,210,436|
| 보조 head tensor |0 bytes|2,359,296 bytes|
| horizon2/3/4 nonzero-gradient update |0/0/0|703/703/703|
| 최종 NTP DEV CE,2977 targets |6.973029001|6.899358927|
| 고정 native32 CE,32768 targets |7.904592454|7.879828334|
| 첫 회 제외 update 평균초 |1.894434|2.080285|
| 전체 학습 driver초 |1482.217034|1603.633880|
| reserved MiB |3012|3022|
| CP SHA | `3AAC7E1A2F968D7EADA8103AE83CE3373318C3EBF9676CB17950E0C9327A8605` | `B54DA41C139D835CCDE663EC2BB5746610408161485FE1F5DFB53752B8415410` |

공통 초기 SHA는 보조 head를 제외한 본체 fingerprint다. 모든 파라미터/계산량이 같다는 뜻은 아니다. MTP는 추가 미래 horizon 감독·head·계산을 가진다. 같은 source512와 순서는 raw에서 정확히 일치했다.

첫답 평가 영수증은 각 학습 report SHA를 NTP `B827AF49531D6F32169BAF48345DFB42C9507F99A490769ECBD515AE7B77C193`, MTP `FE821A5ECE916D3A0BBF48AC6FC9F020939F688B2EF1BFF5EBFDB9F578ABC110`로 참조하며 실제 작은 report 바이트 해시와 일치했다. 평가 CP SHA도 위 학습 영수증과 같았다. 본 감사에서 실물 CP를 다시 해시하거나 tensor-load하지 않았다.

raw512 JSONL의 실제 행수·연속 index0~511·바이트/concat SHA는 manifest와 일치했다.

- NTP raw: `0E7F6C32AD478A17783EA6DC46FB29CC37F82AEB1D8DC65FB3FF74134392E8C8`
- MTP raw: `DD07FD481F7CE95BE90F5B9ECF3389405125F261266621BA45FECB17088ED461`

DEV 및 native32 CE는 BF16 forward/FP32 CE 계열의 고정 평가이며, 아래 자유 첫답은 FP32 MATH/TF32 OFF/cache ON/MTP inference OFF/greedy다. 고정 native32는 전체 native VAL이 아니다. 학습 driver 시간에는 인코딩/compile/학습/추가 답안/저장 등이 포함되므로 순수 학습 속도 비율로 읽지 않는다. 단일 seed이고 이 조건의 반복 학습 노이즈는 미측정이다.

## 3. 자연512 전량: strict·추출·종료를 분리한다

평가는 `split=val`, `DEV_USED_BY_TRAINING_VALIDATION`이다. 학습 중 CE 검증에 이미 사용한 DEV512이며 새 독립 TEST가 아니다. 기준은 마지막 주석 문자열과 `answer.strip()`의 완전 일치다. 저장된 모든 alias 목록은 한 개였고, 그 alias와의 완전 일치도 각각0이었다. 더 넓은 동의어·함의·형식 차이를 포괄한 의미 채점은 아니다.

| 팔·언어 | n | strict | 추출 실패 | STOP_SEQUENCE | MAX_NEW128 | 빈 답 | 평균 생성 token(EOT 포함) | 서로 다른 원답 문자열 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NTP KO |256|0|0|256|0|0|2.230469|6|
| MTP KO |256|0|0|256|0|0|3.101563|9|
| NTP EN |256|0|0|41|215|0|116.636719|60|
| MTP EN |256|0|0|103|153|0|109.132813|155|
| NTP 전체 |512|0|0|297|215|0|—|—|
| MTP 전체 |512|0|0|359|153|0|—|—|

추출0은 저장된 추출 영수증을 전량 재집계한 값이다. 실제 tokenizer를 다시 열어 prefix 추출 경로를 재실행한 것은 아니다. 빈 답도 모두0이라 strict0을 빈 추출만으로 설명할 수 없다.

영어 종료 대응표는 NTP MAX→MTP MAX139, STOP→STOP27, MAX→STOP76, STOP→MAX14다. 따라서 순증62건의 종료가 있었지만 모든 사례에서 일방적으로 좋아진 것도 아니다. 종료 증가는 정확한 답 생성 증가로 이어지지 않았다.

한국어 전체 출력 빈도도 확인했다.

- NTP: `이`199, `이든`35, `4월`18, `4`2, `4월 1월 1`1, `189년`1.
- MTP: `이든`163, `이성`62, `4월 1일`10, `4월`6, `1.1`6, `이`3, `2.2`3, `4`2, `3월 1일`1.

이는 문맥/인물/기간/단체/직업이 서로 다른 질문을 소수 출력으로 처리한 붕괴 징후다. 출력 종류가 늘거나 “이” 대신 “이든”이 된 것을 정답/지능 향상으로 해석하지 않는다.

## 4. 사전 등간격32문항을 직접 읽은 판정

아래 index는0-based이고 JSONL의 실제 줄은 index+1이다. 두 팔의 원문 지문까지 읽었으며, 표의 긴 영어 출력은 **표시용 앞부분 발췌**다. 답의 나머지를 삭제하거나 원본을 정정한 것이 아니다.

| index | 언어 | 질문 | 주석 답 | NTP 원답/종료/token | MTP 원답/종료/token | 직접 판독 |
|---:|---|---|---|---|---|---|
|0|ko|프로젝트 조직 성과에 영향을 끼치는 요소 세 가지는?|내재적 보상, 커뮤니케이션, 피드백|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|16|ko|현존하는 어류 종들 중 970개로 이루어지는 물고기 종은 뭐라고 불리는가?|연골어류|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|32|ko|저격수 패턴에서 시간계산에 신경을 써야 하는 이유는 무엇이 복잡해서인가?|맵 구조|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|48|ko|김기춘은 2017년에 징역 몇 년을 선고받았는가?|3년|이 / STOP_SEQUENCE / 2|2.2 / STOP_SEQUENCE / 4|무관한 단편/값; alias 차이 아님|
|64|ko|2004년 조용호가 옮긴 팀은?|KT 롤스터|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|80|ko|스튜디오 지브리가 설립된 것은 몇 년인가?|1985년|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|96|ko|구조 접착제와 달리, 단순하게 접착제와 접착면을 붙이기 위한 압력만 필요한 접착제의 이름은?|감압식 접착제|이 / STOP_SEQUENCE / 2|이성 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|112|ko|진경준의 직업은?|검사|이 / STOP_SEQUENCE / 2|이성 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|128|ko|말러음악 생활중에 터닝 포인트로 할 수 있는 해는 언제인가요?|1901년|이든 / STOP_SEQUENCE / 3|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|144|ko|사나칸이 세이프 가드의 모습일 때 자아는 무엇에 의해 통제되는가?|중앙 세이프 가드|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|160|ko|스틸하트에 보컬리스트 이름은?|메이티제빅|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|176|ko|양 무제가 불교의 계율을 따르며 소식하기를 견지했기에, 당시 황제를 가리켰던 칭호는?|황제보살|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|192|ko|오바마는 어느 단체의 이사회 창립회원이었나?|공공 동맹|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|208|ko|TV로 가장 즐겨보는 스포츠 중 최고 인기 스포츠는?|축구|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|224|ko|무라타는 1982년 어디에 이상이 생긴것인가?|팔꿈치|이 / STOP_SEQUENCE / 2|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|240|ko|프로 배구 출범 이래 처음으로 해외에 진출한 여자 배구 선수는 누구인가?|김연경|이든 / STOP_SEQUENCE / 3|이든 / STOP_SEQUENCE / 3|무관한 단편/값; alias 차이 아님|
|256|en|How many races were people asked to mark on the US Census after OMB revised their standards in 1997?|one or more|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|272|en|As far as Australian nationality law goes, Norfolk Island is considered a part of what?|Australia|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|288|en|What have studies shown regarding climate change?|timing changes in migration|The first time of the world of the world of the world of the world of th… / MAX_NEW / 128|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / STOP_SEQUENCE / 46|상투어 반복/문장 붕괴; 요청 답 아님|
|304|en|Prior to 1997, where were racial categories declared for the U.S. Census?|OMB directive no. 15|The "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / STOP_SEQUENCE / 104|상투어 반복/문장 붕괴; 요청 답 아님|
|320|en|On May 3, 1856, how many Pitcairners left for Norfolk Island?|193|The "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|336|en|Where do the European pied flycatcher breed?|Asia and Europe|The "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|352|en|In ethnic classification for the U.S. Census, What option do respondents have other than not Hispanic or Latino?|Hispanic or Latino|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|368|en|Organisms in the Arthropoda group have bodies that are divided into what?|repeating segments|The "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|384|en|When did Stein win a Pulitzer?|1998|The "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-… / STOP_SEQUENCE / 120|상투어 반복/문장 붕괴; 요청 답 아님|
|400|en|How many people were buried under rubble in Mianyang City?|1,700|the "The "P" and the region of the region of the most of the world of th… / MAX_NEW / 128|the "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / STOP_SEQUENCE / 66|상투어 반복/문장 붕괴; 요청 답 아님|
|416|en|What was the object to use first in widespread manner process of vacuum?|incandescent light bulb|The first, the world of the world of the world of the world of the world… / MAX_NEW / 128|the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|432|en|What did they try to establish?|time prediction method|The "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|The first the world of the world of the world of the world of the world … / STOP_SEQUENCE / 54|상투어 반복/문장 붕괴; 요청 답 아님|
|448|en|What do young birds form attachments to?|potential breeding sites|The first time of the most of the most of the most of the most of the wo… / MAX_NEW / 128|the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|464|en|Outside of France, where are the other three branches of the Sorbonne library located?|Malesherbes, Clignancourt-Championnet, Michelet-Institut d'Art et d'Archéologie, Serpente-Maison de la Recherche, and Institut des Etudes Ibériques|The "The "The "The "The "The "The "The "The "The "The "The "The "The "Th… / MAX_NEW / 128|the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|480|en|What geographical barriers to land birds try to avoid?|large water bodies or high mountain ranges|The first, the world of the world of the world of the world of the world… / MAX_NEW / 128|the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-the-… / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|
|496|en|Where is the headquarters for the Prefecture of Police of Paris?|Place Louis Lépine on the Île de la Cité|The first, the world of the world of the world of the world of the world… / MAX_NEW / 128|the of the world of the world of the world of the world of the world of … / MAX_NEW / 128|상투어 반복/문장 붕괴; 요청 답 아님|

두 팔×32답의 직접 판독에서, 단순 alias/맞는 뜻의 다른 표현으로 해소되는 사례는 발견하지 못했다. 질문 문장을 그대로 복제한 사례나 사용자가 제공하지 않은 재질문을 요구한 사례도 이64답에서는 발견하지 못했다. 억지로 그 분류를 채우지 않는다. 주된 실패는 KO의 무관한 짧은 단편/숫자와 EN의 `The "The "`, `the-the-`, `of the world` 반복이었다. 영어32답은 모두 반복/구문 붕괴가 있었다. 이64답의 주석·지문 요구를 충족한 내용 정답은 확인되지 않았다.

자연64답과 아래 고정16첫답을 함께 보아 대표 실패를 한 개씩 배정한 수는 다음과 같다. 이는 직접 읽은80답의 후행 기술 분류이며, 자동 채점기·전체 모집단 오류율이 아니다. 무관성은 영어 반복/JSON 실패와도 겹치지만 아래 합계에서는 중복 세지 않았다.

| 대표 실패 | 자연64 | 고정16첫답 | 합계 |
|---|---:|---:|---:|
| 무관한 한국어 단편·숫자/값 |32|8|40|
| 영어 반복·구문 붕괴 |32|6|38|
| JSON 키/값 또는 구문 요구 실패 |0|2|2|
| 단순 alias만 다른 의미 정답 확인 |0|0|0|
| 질문 그대로 복제 확인 |0|0|0|
| 답 대신 과잉 재질문 확인 |0|0|0|

“영어 퇴행”은 여기서는 관측된 반복/붕괴 양상을 가리킬 뿐, 이전에 보유하던 영어 능력에서 얼만큼 악화됐는지를 확정하는 인과 판정이 아니다. 초기 원답을 같은 의미 기준으로 전수 판독하지 않았고 scratch는 약21.6M 입력의 제한된 학습이다.

주석/문항 자체도 무조건 정답성을 보장하지 않는다. index464는 질문의 “Outside of France / other three branches”와 지문·주석의 Paris/Sorbonne 및 다섯 지명 나열이 맞물리지 않아 원형 질문 전제와 주석 검토가 필요하다. 그렇다고 두 팔의 반복문이 그 질문의 의미상 정답이 되는 것은 아니다. index160의 인명은 원래 전체 이름/음역 등 가능한 별칭 범위를 추가 검토할 수 있지만 실제 출력은 “이/이든”이어서 이 표본의 실패를 그 별칭 문제로 설명할 수 없다.

## 5. 고정8 첫답: 재시도를 첫답 성공으로 세지 않는다

고정8은 별도의 좁은 rubric이며 각 최종 답 attempt1만 보았다. 자연512의 max_new128과 달리 여기 max_new는160이다.

| 문항 | NTP 첫 답 요약 | MTP 첫 답 요약 | 직접 판독 |
|---|---|---|---|
| 2+3, 숫자만 |18|137|두 답 모두 실제 값/요청 실패|
| 7−4, 한 자리 |긴 영어 반복문|짧아진 world 반복문|둘 다3이 아님|
| 한국어 과일2개 |이든|183|목록/대상 요구 실패|
| result:5 JSON |유효 JSON이지만 answer:P|깨진 JSON 형태|키·타입·값/구문 실패|
| 물이 얼면 |이든|13|질문 내용과 무관|
| 사는 행성, 한 단어 |긴 영어 반복문|world 반복문|world라는 관련 어휘가 있어도 한 단어 planet 답/내용 요구를 충족하지 않음|
| 비밀 단어 별빛 복사 |이든|18|명시 정보 재현 실패|
| 빨간상자→무거움 yes/no |긴 영어 반복문|world 반복문|판정/요청 형식 실패|

두 팔의 첫 rubric는 모두0/8이다. MTP의 `pass_within_three=1/8`은 arithmetic_ko의 **attempt2**에서 “5”가 나온 것으로, temperature0.8·seed20261002이며 첫 greedy 답의137과 다르다. 새 질문에 대한 독립 첫답 성공이나 재현 가능한 산수 능력으로 합치지 않는다. 이 추가 원답1건은 실제 문자열까지 확인했다.

### 5.1 고정8 첫답 원문 보존 발췌

아래는 최종 고정 probe JSONL의 `answer_text` **전체 필드**이며 요약/문장 수리하지 않았다. 원문 prompt와 full decoded text·다른 재시도는 기존 JSONL에 남아 있다.

#### arithmetic_ko

원래 prompt:

```text
<|im_start|>user
2 더하기 3의 값만 숫자로 답하세요.<|im_end|>
<|im_start|>assistant

```

NTP attempt1 (STOP_SEQUENCE, 2tokens):

```text
18
```

MTP attempt1 (STOP_SEQUENCE, 3tokens):

```text
137
```

#### arithmetic_en

원래 prompt:

```text
<|im_start|>user
What is 7 minus 4? Answer with one digit.<|im_end|>
<|im_start|>assistant

```

NTP attempt1 (MAX_NEW, 160tokens):

```text
The "The "The "The "The "The "The "The "The "The "The "The "The "" is a few of the "The "The "The "The "The "" of the "" of the "" of the "The "The "" of the "" of the "" of the "" of the "The "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the
```

MTP attempt1 (STOP_SEQUENCE, 30tokens):

```text
The first, the world is a few of the world, the world, and the world of the world, and the world of the world.
```

#### format_ko

원래 prompt:

```text
<|im_start|>user
한국어 과일 두 개를 쉼표로 구분해서만 쓰세요.<|im_end|>
<|im_start|>assistant

```

NTP attempt1 (STOP_SEQUENCE, 3tokens):

```text
이든
```

MTP attempt1 (STOP_SEQUENCE, 3tokens):

```text
183
```

#### format_en

원래 prompt:

```text
<|im_start|>user
Return only JSON with key result and integer value 5.<|im_end|>
<|im_start|>assistant

```

NTP attempt1 (STOP_SEQUENCE, 11tokens):

```text
{"answer": "P"}
```

MTP attempt1 (STOP_SEQUENCE, 13tokens):

```text
{"answer": "": ""}
```

#### knowledge_ko

원래 prompt:

```text
<|im_start|>user
물이 얼면 무엇이 되나요? 한 문장으로 답하세요.<|im_end|>
<|im_start|>assistant

```

NTP attempt1 (STOP_SEQUENCE, 3tokens):

```text
이든
```

MTP attempt1 (STOP_SEQUENCE, 2tokens):

```text
13
```

#### knowledge_en

원래 prompt:

```text
<|im_start|>user
Name the planet humans live on, in one word.<|im_end|>
<|im_start|>assistant

```

NTP attempt1 (MAX_NEW, 160tokens):

```text
The "The "The "The "The "The "The "The "The "The "The "" is a few of the "The "The "The "The "The "" of the "" of the "" of the "" of the "The "The "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the ""
```

MTP attempt1 (STOP_SEQUENCE, 30tokens):

```text
The first, the world is a few of the world, the world, and the world of the world, and the world of the world.
```

#### memory_ko

원래 prompt:

```text
<|im_start|>user
내가 정한 비밀 단어는 별빛입니다. 비밀 단어만 다시 쓰세요.<|im_end|>
<|im_start|>assistant

```

NTP attempt1 (STOP_SEQUENCE, 3tokens):

```text
이든
```

MTP attempt1 (STOP_SEQUENCE, 2tokens):

```text
18
```

#### logic_en

원래 prompt:

```text
<|im_start|>user
All red boxes are heavy. This box is red. Is it heavy? Answer yes or no.<|im_end|>
<|im_start|>assistant

```

NTP attempt1 (MAX_NEW, 160tokens):

```text
The "The "The "The "The "The "The "The "The "The "The "The "The "The "The "The "The "The "The "" is a few of the "The "The "The "The "The "" is a few of the "The "The "The "The "" of the "The "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "" of the "
```

MTP attempt1 (STOP_SEQUENCE, 39tokens):

```text
The first, the world is a few of the world, and the world of the world. It is a few of the world, and the world, and the world of the world.
```

## 6. V3 미마스크 두 행: 오류 범위와 해석 경계

총괄의 후행 확인과 새 [supervision_audit.json](../../data_cache/p101a_sft_mtp_supervision_v4_s1337/corpus/supervision_audit.json)을 읽었다. 여기서192/198은 비율이 아니라 `HF/sft_ready/p090_public_v3_train.canonical.jsonl`의 **0-based source_index 두 개**다. 본 감사가 그 원형 전체를 다시 판독/수리한 것은 아니다.

| source_index / source_id | 확인된 문제 | V3 첫 응답 target/pass | 수리 범위 |
|---|---|---:|---|
|192 /012069b9-79e2-45ad-8b56-dcf1d1caa854|분산을 제곱 없는 편차 합으로 쓴 설명이 같은 답의 식과 모순|91|첫 assistant 전체 감독 제외, 두 번째 응답52targets는 유지|
|198 /019ad050-0b9e-4494-b27c-9e1d5169411c|OpenAI 회사로 답한 뒤 사용자가 open-source 모델을 뜻했다고 정정|365|의도 오해 첫 assistant 전체 감독 제외, 두 번째404targets 유지|

합456targets/pass, 원552,609의 약0.0825%다. 이것은 첫 응답 전체를 감독에서 제외한 토큰 수이며 **456개 토큰이 전부 사실 오류라는 뜻이 아니다**. 두 번째 행의 첫 응답은 회사에 관한 참인 정보까지 포함할 수 있으나 그 대화의 실제 의도와 달랐다.

수리 감사는 메시지 변경0·metadata2행의 `meta.supervised_assistant_turns`만 변경·행순서/split/x 동일을 기록한다. H1 target이552,609→552,153으로456 줄었고 VAL은512/2977targets 그대로다. 감사파일 SHA는 `C91639CDDFD398F20D2F1D52E5BB0DF86AAAAC02FE34A9713E91775CABC11033`이다. 이는 후행 준비의 기록이지 V3 학습을 소급하여 clean으로 만드는 조치가 아니다.

원 `masked_record`는 allowlist가 있는 행에서만 그 제한을 적용하고, allowlist가 없으면 기본 Record를 그대로 반환한다. 따라서 일부 교정 주석의 성공을 “모든 오답 첫 턴 제외”로 확대한 것이 과잉 주장이었다. V3 report의 `train_wrong_assistant=False`·`EXCLUDED_BY_EXPLICIT_ALLOWLIST` 같은 전역 문구는 해당 경계로 정정해야 한다. 이전 정/반 감사의 광범위한 clean 해석도 이 후행 발견이 제한한다.

이 두 행이 KO 단편 붕괴나 EN 반복의 주원인인지,456targets를 제거하면 실제 답이 회복되는지는 아직 알 수 없다. 두 팔이 똑같이 이 감독을 받았다는 사실은 조건부 수치 비교를 보존하지만, 데이터 품질·clean 조건·일반 답변 능력 인증을 회복하지 않는다. 수리판을 준비한 것과 수리판의 실제 학습/효과는 별개다.

## 7. 허용 결론과 남은 것

관측한 긍정 방향은 MTP의 더 낮은 NTP DEV CE, 더 많은 종료, 더 다양한 출력 문자열이다. 반대 증거는 같은 DEV512 strict0·고정 첫답0/8·직접 판독80첫답의 미회복이며, 이 방향을 숨기지 않는다. 보조 head가 실제 gradient를 받았다는 구현 증거도 내용 정답성과 다르다.

따라서 현재 판정은 **V3 실험 실행/원답 회수 완료, V3 clean 주장 정정 필요, 품질/배포 채택 불가**다. MTP 자체의 보편적 무효·모든512답의 의미상0·부모 초기화 팔의 결과·수리판 성공·새 독립 benchmark는 이 감사에서 주장하지 않는다.

남은 의미 판독은 자연 QA960답, 그리고 전체 데이터 품질/일반화·추가 학습 seed다. 사전 등간격 표본의 결과를 전체 의미 정답률 추정치나 통계적 구조 우열로 일반화하지 않는다.

## 8. 읽은 실제 정본 위치

- [scratch NTP 학습 report](../../test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/scratch_ntp/report.json)
- [scratch MTP 학습 report](../../test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/scratch_mtp/report.json)
- [NTP 자연512 report](../../test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/first_answer_scratch_ntp/report.json) / [raw JSONL](../../test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/first_answer_scratch_ntp/first_answers_000000.jsonl)
- [MTP 자연512 report](../../test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/first_answer_scratch_mtp/report.json) / [raw JSONL](../../test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/first_answer_scratch_mtp/first_answers_000000.jsonl)
- [NTP 최종 고정8/재시도 raw](../../test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/scratch_ntp/answers_final_scratch_ntp_000000.jsonl)
- [MTP 최종 고정8/재시도 raw](../../test_result/evidence/p101a_sft_mtp_cleanbilingual_v3_s1337/scratch_mtp/answers_final_scratch_mtp_000000.jsonl)
- [저장 strict/추출 판정 코드](../../scripts/diag_p101a_clean_eval.py) 21~35·126~142행은 읽기만 했다.
