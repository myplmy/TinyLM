# P107 — 문서 가시성과 shift를 분리한 causal/MNTP 계약

> 계기: 원장58/59의미구현·[P013결과106](../test_result/106_20261027123926_P013-같은토큰의-짧은문맥은-메모리를-줄였지만-느렸다.md). 추가300M금지·본학습전작은지능평가금지유지.

## 1. 왜

TinyLM에는MTP/assistant-only CE가있지만그것이양방향MNTP가아니다. 실제모델의가시성·문서경계·shift가없으면GPT-BERT목적을재현했다고말할수없다. [구현계약과세대안/영향도](../docs/research/20261027_MNTP_가시성과_지도위치_구현계약.md)의선택인자방식을총괄이구현한다. 이미완료한MTP학습·재귀진단을반복하지않는다.

## 2. 질문

| 질문 | 이유 |
|---|---|
| 기본None forward가옛실행과같은가 | 기존추론/호환성보호 |
| 같은문서오른쪽은보이고다른문서는차단되는가 | MNTP와정답누설구분 |
| 가린j의정답이j-1에연결되는가 | MTP/MLM/선택적NTP와구분 |
| CLA/checkpoint·pad에서gradient가일관적인가 | 실제공유구조의조용한오류탐지 |
| 실제기존모델에서목적별시간/메모리·target량은얼마인가 | 별도생산설계의비용근거 |

## 3. 예측

새parameter없이opt-in bool mask를SDPA로연결하면가시성과shift계약을성립시킬수있다. 반면arbitrary문서mask는fast attention을제약하거나메모리/시간을늘릴수있고작은masked target수는학습효율보증이아니다. causal평가·일상대화개선은본학습전판정하지않는다. 기본None불일치나누설이면실제비용실험을열지않는다.

## 4. 단계 설계

### Stage0W — 독립 CPU 계약

기존실제모듈의작은가상shape에서구/신None로짓·전체이름별gradient·동일shape cache,shift·손상·문서/패딩차단·zero-target·checkpoint/mask변조를검증한다. 원형데이터/CP는읽지않고소형초기화fixture는품질시험이아니다. 의미/일반지능채택0이다.

### Stage1W — 기존 모델의 실제 F+B 비용 후보

Stage0실제종료0·명시정적·현재소스전체스모크·원형봉인뒤에만연다. 기존Native595-Q/같은실물체크포인트에서causal기본·문서causal·MNTP의가상입력/문서/target분모와순/역순시간을기록한다. optimizer0·학습자료0·CP저장0·교사0이며최대900초+정리180초이다. 입장예측이17시이내이고여유VRAM에맞을때만수행한다. 실패9/시간HOLD8/기술완결0을분리한다.

### 후속 — 제품 학습·적응형 masking

현재미완이다. 실제문서ID/packing·목표별배치배분·모델/optimizer/RNG정확재개·causal KD와masked CE분리·언어/희귀/숫자편향을확인해야한다. uniform먼저고정하고mask일정/optimizer/context일정을한꺼번에바꾸지않는다. 본학습은정제완료·학습권한뒤에만열고causal기준의공식평가와생성으로최종판정한다.

## 5. 판정 기준

| 항목 | 기준 |
|---|---|
| None호환/shift/정보차단 | 실제회귀의수치·gradient검증; 실패시GPU비용미실행 |
| 기술비용완료 | 고정소스·전체행/목표/유한gradient·원CP/core불변·정리완료 |
| 시간초과 | 부분성과보존·HOLD8;완료/품질통과로승격금지 |
| 지능·효율채택 | 이번범위NOT_RUN;학습계열별기준은본학습설계에서정본대조 |

## 6. 비용

CPU회귀수분·새전체스모크약8분,실제모델F+B최대15분예상이다. 구현·검토는17시창안에서진행하고남은선결은원장에남긴다. 단순짧은실행으로본학습wall절감이나품질향상을확정하지않는다.

## 7. 실행

Stage0/1을실제완료하고두SH는-done으로개명했다. CPU109회귀83769/0·metadata56224/0뒤새전체smoke34481/0·471.601초와명시정적16805/0·70PASS/0ERROR/6NOT_RUN을받았고,실제비용48383/0·111.261초를[결과107§6](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md)에기록했다. source39 SHA `FBCBF5F931827E07D624620E221C5782F77530B0CA1960AAB1242B4BCBBF9E28`,profile SHA `9EF350FC8D5B3814E9AA97C399FC6EE943F2274F0DFD9A74A2A0172CB31EB63C`이며원형44파일/SH명령/SHA를보존했고삭제0이다.

## 8. 한계

공식GPT-BERT전체구조/학습recipe재현이아니다. 최초100%예약ID치환·pad query self-diagonal은SDPA안전이식이다. 작은fixture/가상비용으로일반한국어·benchmark개선·75M완성·추가300M가능을주장하지않는다. 타세션정제·보호TinyDataset·원CP변경·설치/외부취득/Git변경0이다.

## 9. 실행 이력

2026-10-27 설계착수. 기존58항목·공식원문/보조고정commit검토·실제core중복검색을수행했다. 구현/회귀/실제비용은각실제종료를회수한뒤여기에누적한다.

CPU예측대조: 기존세forward의None로짓/전체gradient/동일shape cache가원형AST와일치했고양방향/문서/패딩/가린gold불변과checkpoint복제마스크계약을검산했다. 최초관측훅·단일 logit gradient 기대·독립oracle변수shadowing의시험오류는원소스/로그를보존했다. 제품동작의확정누설로보지않는다. 반검토의독립두모델gradient·토크나이저실물SHA·부분micro·최초오류chain·독립최종검사·audit포함peak분리를반영했고최종109회귀가실제0이다.

실제비용은각micro의backward뒤동기화해성공한micro/입력량을부분실패에도남긴다. F+B peak와후행gradient검사포함peak를별도로기록한다. 내부900초timer뒤정리는내부180초상한으로주장하지않고SH의외부1020초+kill20초로제한한다. 외부중단124/137과최종보고서부재는기술완료가아니다. CPU메타데이터오류도9/시간보류8로분리하고실행시입장실패는별도새보고서에남긴다.

실제비용예측대조: 기본/doccausal/MNTP/8+8혼합의동일131072input 중앙값3.889/4.272/4.216/4.176초,혼합은기본보다약7.38%느렸고F+B peak5339.216MiB다. 가시성과shift/유한gradient·원core/파일/tokenizer·소유정리는실제성립했으나추가목적이무료라는예측은성립하지않는다. 지도target개수/가시성이달라loss로학습효율을비교하지않는다. 본학습품질/제품trainer/causalKD/적응mask는미완이고추가300M금지를유지한다.

### Stage2W — hard 적응형통계와Bernoulli선정의CPU선결

[세대안이상비교와영향도](../docs/research/20261027_적응형_masking의_통계와_재개계약.md)에따라기존uniform을보존하고유형별hard정답률의통계/선정/실패폐기·경계재개를준비한다. 원장59의제품학습효과는완료로세지않는다. 공식MLM의통계위치를MNTP j-1에맞추며row별eligible 기대rate/확률상한/동일RNG를검산한다. 미관측keep/prior는별도명시대안이고rate/optimizer/context를동시에바꾸지않는다.

CPU가상fixture의직접oracle와고정크기두어휘통계비용을실제완료했다. Stage2W83880/0 뒤장기EMA/첫window일관성회귀를추가했고Stage2Wb20761/0·6조건1.565초와CPU27시험85047/0을회수했다. 두SH는전체명령/SHA보존후-done이며삭제0이다. 모델/학습자료/교사/GPU/optimizer/체크포인트저장0이다. 합성그룹을실제한국어/희귀/숫자편향으로보고하지않으며생산trainer/full학습효율은미완이다. [결과107§7](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md).

### Stage3W — 로짓 argmax와 CPU 통계 전달의 GPU 비용

Stage2의 정확한 정책 재개 회귀 뒤 모델 없는 가상 BF16 로짓에서 full/selected argmax를 비교한다. [대안·영향·자원 계약](../docs/research/20261027_적응형_masking의_통계와_재개계약.md)의 B 경로 두 변형이다. 같은 batch8×1024·어휘32768/262144·알려진 정답/오답 ID·고정 선택에 대해 순/역순 warm1/실측3, 준비/gather·reduction·전달·CPU commit·typed peak를 분리한다. 모델 호출·교사·실제 원문·학습·체크포인트0이며 성공은 ID/집계의 직접 oracle·소스 불변·소유 GPU 정리뿐이다. 실제 학습 속도/품질 채택은 하지 않는다. 사전 CPU 회귀·고정 프로필·여유8GiB·300초 내부/360초 외부+kill20초·17시 종결이 선결이다.

실제77194/0·내부1.745초/8블록32회로완료했다.262K full/selected ID획득7.188/4.084ms와peak4096.188/4702.526MiB를분리했고전체known ID/유형histogram/최종소유CUDA0을확인했다. SH전체원문/SHA뒤-done·삭제0이다. 이후check_attrs의별도PolicyConfig.seed오탐을생성자참조세곳으로좁게수리했고,직접검사38976/0·CPU30시험65351/0·현재소스전체smoke69526/0·445.947초/44실행을회수했다. 원smoke55571/1도보존한다. [결과107§8](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md). 제품통합·자료편향·본학습효과는미완이며사용자99에따라새실험을확장하지않는다.
