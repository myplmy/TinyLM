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

### Stage4aW/Stage4bW/Stage4cW — 실제 갱신·통계·전체 경계 재개

사용자104가 2026-11-01 11:00 KST까지 이쪽 VRAM8GB 이내 주도 연구를 승인했다.
[독립 방법/영향/사전 판정](../docs/research/20261101_P107_실제갱신과_경계재개_계약.md)을 따른다.
현재 원장59의 미완인 실제 model/optimizer와 통계 결합을 새 opt-in 어댑터로 연결한다.
기존 loader의 문서 경계를 추정하지 않고 명시 가상 source만 쓴다. 제품 CLI/정제자료·causalKD·
scheduler/GradScaler/compile·본학습 품질은 이 단계의 성공으로 완료 처리하지 않는다.

Stage4aW는 실제 optimizer·observer-only 동률·dropout과 RNG/source 재개·부분 실패 dirty
거부를 CPU로 검증한다. source를 고정하고 통과한 뒤에만 Stage4bW에서 기존 native595-q의
micro8×accum16×seq1024, causal8/MNTP8, 같은 Muon RMS4+AdamW·상수 LR·clip으로
uniform/observe/adaptive-keep를 순/역순 비교한다. 각 warm1/실측3·총24 실제 갱신이다.
Stage4cW는 완료2회 경계를 BytesIO 직렬화한 뒤 후속2회와 복원 후2회의 모든 상태를 대조한다.
디스크CP 저장0이며 메모리 직렬화가 전원장애 복구 증거는 아니다.

PyTorch allocator6GiB 상한과 8,000,000,000바이트 증가 감시를 둔다. NVML은 공유 GPU의
시작값 대비 증가를 표본 감시하므로 정확한 프로세스별 물리 peak로 이름 붙이지 않는다.
각 GPU worker 내부900초/외부1020초+kill20초·마감120초 여유를 요구한다. CPU 계약 실패,
정합 불일치, 원CP/소스 변경은 오류9; 시간·자원 감시 중단은 보류8이며 원실패를 보존한다.
이전 가상 로짓/optimizer 없는 F+B를 새 결과로 재사용하거나 반복 학습 성과로 세지 않는다.

실제 회수: CPU44→45시험·독립CE 갱신 oracle 뒤 새전체smoke106동작/44child/오류0·
428.255초와 정적70PASS/0ERROR/6NOT_RUN을 확인했다. Stage4bW 실제24갱신은 종료0이며
uniform/observe/adaptive 중앙값10.163822/10.404444/10.275837초다. 관측만 켜면 모델/optimizer
갱신이 exact이고 adaptive의 두 순서도 exact였다. Stage4cW 실제6갱신/종료0은 전체 다섯
상태 해시와 후속loss·선정량의 정확한 메모리 재개를 확인했다. 최대Torch reserved6,417,285,120B·
공유GPU 표본 증가6,712,983,552B·원CP/source불변·최종 소유CUDA0이다.
[결과107§12~14](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md)에
원로그·전체SH/SHA를 보존했고 네SH는 -done이다. 실제 삭제/디스크CP/언어품질 판정0이다.
사전 정합 예측은 충족했으나 제품 CLI/실제 문서/causal KD/scheduler/GradScaler/compile과
본학습 효율은 미완이며, 적응형 통계가 무료인 것으로 채택하지 않는다.

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

### Stage5W — 명시 문서·LR 스케줄과 분할 디스크 재개

[사전 설계](../docs/research/20261101_P107_문서원천과_디스크재개_설계.md)의 A안을 구현했다.
원장59의 완료30갱신/메모리재개는 반복하지 않고, 새 명시문서 source·cosine/warmup·실제 디스크 전체재개를 독립 기술선결로 검증한다.
기존 AdaptiveMNTPTrainer와 LR식·strict 원형 로더·source/정리 helper를 재사용하며 기본 trainer/CLI는 변경하지 않는다.

새 CPU15/0은 실제 부분 optimizer 실패·다른 source/스케줄·손상/부분 shard·overwrite 거부와
dropout 포함 전체 재개의 exact를 확인했다. 새profile은8BDA8C4334925C178B83856F3DC02A3002888F13E193FAA8B0329F2E79DB8ECD,
source는0FFBF25801BBAB27D0DEDE10504342A6A5DEF77743C29F1A229E7049A62CAF78다.
프로필의6갱신/1snapshot은 계획량이며 CPU 준비에서 실제 Native/GPU는0이다.

실제 GPU는 현재 Falcon5 전량 종료·정리 뒤 단일GPU로만 연다. 같은 Native 복사본에서
명시 합성4문서·micro8×accum16×1024·causal8/MNTP8·BF16AMP/FP32master·MuonRMS4+AdamW를 사용한다.
prefix2 뒤 새디스크snapshot을16MB 이하 조각으로 저장하고 계속2회와 새optimizer/source/session 복원 후2회를 대조한다.
8회 지평·warmup2·cosine LR, loss·target·model/optimizer/policy/source/RNG가 같아야 한다.
원모델/소스 불변·최종CUDA0·실제파일 크기/전체SHA를 검산한다. 디스크 실패 산출물과 연구snapshot은 삭제하지 않는다.

최대900초+정리예비·15시마감, 보수적6GiBallocator/8GB공유증가를 유지한다.
예상GPU2~5분은 기존 비용으로부터의 추정이며 실제 디스크 시간·약781MB 상태크기는 실측 후 확정한다.
다른프로세스/정전 복구·실제코퍼스/언어편향·causalKD·생산CLI·본학습지능은 이 기술 게이트로 완료하지 않는다.
실행SH는 run_P107_Stage5W_document_schedule_disk_resume.sh 이며 현재GPU미실행이다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

<a id="p107-v11-frozen-mask-selection"></a>
### 2026-11-21 정제 원문의 마스크 선택률을 동결 모형에서 검산한다

원장 58·59의 작성 원문 네 건을 실제 정제본의 분할 내 위치로 넓힌다. v1.1 기준판 TRAIN의 서로 다른 위치에서 512개 참조와 64개 오답 관측, 64개 확인 문서를 고정한다. 같은 chat32의 원문 오프셋에서 십진 숫자를 찾고, 참조 표본에서 1~2회 나온 ID를 희귀로 정의한다. 한글 음절과 ASCII 문자 비중은 문자 집계용 대용 지표다. 언어 분류기 판정으로 사용하지 않는다. 원문·검증·보호 파일, 모델 가중치, 정식 학습 캐시를 갱신하지 않는다.

무부모 300M 균등 R2 완주본을 고정하고, 실제 양방향 마스크 입력의 예측으로 오답 관측을 쌓는다. 같은 관측 상태·난수에서 확인 위치의 균등 선택과 적응 선택을 비교한다. 집단별 분모·기대·실제 선택률과 총 마스크 예산을 회수한다. 예측은 오류가 집중된 희귀·숫자 집단이 달라지면 적응 선택의 기대률도 움직인다는 것이다. 작은 참조 집합에서 처음 나온 ID가 많으면 이를 별도 집계한다. 최대 GPU 한 장·4분·카드 12,390MiB로 제한한다. 가중치 갱신은 0회이며 학습 후 causal 품질과 장기 편향은 별도 실험이다. [실행기](../scripts/diag_p107_v11_frozen_mask_selection.py)



### Stage6W — 같은 어휘 교사 causal KL의 실제 연결 비용

- 사용자 105의 2026-11-01 15시까지 CPU/GPU 권한으로 준비한다. 정제 원천·추가 300M·품질 학습은 수행하지 않는다.
- 설계는 [교사 연결 설계](../docs/research/20261101_P107_causal_KD_연결_설계.md)를 따른다. 기존 teacher KL 함수를 재사용하고 기본 None 경로를 보존한다. masked micro에는 교사를 호출하지 않는다.
- 같은 Native595 복사본의 본체·삼진 경로·토크나이저·micro8×accum16·길이1024·checkpoint-on·BF16 AMP·FP32 master·Muon RMS4/AdamW를 고정한다. 명시 합성 문서 4개와 스케줄을 고정하고 None/KL/KL/None 네 블록을 각각 4업데이트한다. 각 블록 첫 회는 준비 비용으로 구분하고 남은 3회씩을 비교한다.
- 두 팔 모두 같은 동결 교사가 상주한다. 교사 상주 자체의 메모리는 별도 계측한다. 교사는 동일 Native의 기술 대조로서 더 유능한 정답 교사가 아니며, 결과에서 지식·지능 향상이나 Gemma 간 어휘 정렬의 성공을 주장하지 않는다.
- causal loss는 CE + 0.1×KL(T1)이고 행청크256이다. 기존 causal/masked 각각 절반 가중·clip·optimizer·통계 갱신은 유지한다. 이 계수는 기술 시험 조건이며 최적값 채택이 아니다.
- 시행 전 CPU 원로그·소스 SHA·원 부모 SHA·토크나이저 SHA를 동결한다. 반복 블록의 loss/model/optimizer/source/policy/RNG가 같고 교사 parameter와 gradient가 불변이어야 한다. 정합 실패는 기술 실패로 보존하며 품질 음성으로 대신하지 않는다.
- 실제 실행 상한900초, 종료 준비120초, 15시 마감이다. GPU allocator12GiB·공유 시작값 대비 증가14GB·단일 GPU·기존 경쟁 compute 없음으로 제한한다. 실제 여유량이14GB 이하이면 실행하지 않는다. 제한을 없애는 사용자 승인과 물리적 안전 확인은 구분한다.
- 런처: run_P107_Stage6W_causal_teacher_kl_cost.sh. 새 profile과 출력만 사용한다. 체크포인트 파일은 쓰지 않는다. 정확한 호출·종료코드·원로그·최대 메모리·동결 교사 비용·최종 CUDA 해제를 결과 107에 기록한다.


### Stage5W/6W 실행 회수 — 2026-11-01 오후

Stage5W Native 합성6갱신·새디스크 snapshot1개는69640/0·독립76538/0으로 source/RNG/optimizer/모델/정책/스케줄 exact를 확인했다. Stage6W는 CPU40 뒤 합성16갱신10664/0·독립24560/0으로 causal-only KL과 반복 경로 exact·교사 동결을 확인했다. 결과107§15~16이 수치·비용·한계의 정본이다. 완료 SH는 -done과 원형 SHA로 보존했다. 실제 코퍼스·품질·생산 CLI는 미완이고 추가300M은 금지 상태다.


### Stage7W — 새 프로세스에서 기존 V1 디스크 경계 재현

Stage5W는 같은 프로세스의 새 optimizer/source/session을 시험했고 OS 프로세스 재시작은 미확인이었다. 원장59의 전체 재개 선결을 위해 이미 종료한 세션69640의 snapshot을 읽기 전용으로 새 Python worker에 로드하고2업데이트만 수행한다. 새 파일 checkpoint를 저장하지 않는다. 이전 실행의 계속 경로와 loss/target/LR 및 model/optimizer/policy/source/RNG/세션 전체 SHA를 대조한다.

기존 snapshot은 KD가 없는 V1 경계다. 현재 코드에서 달라진 원소스는 optional causal KD hook 하나뿐이어야 하며, 원형을 정확 바이트로 보존하고 CPU에서 None 기본4업데이트의 전체 상태 일치를 먼저 증명한다. 저장된 source/스케줄 서명은 의도적으로 보존하되 새 실행 profile은 현재 코드·옛 profile·옛 보고서·독립 판독·디스크 manifest와 CPU 원로그를 모두 SHA로 묶는다. 소스 차이를 무시하거나 옛 source profile을 그대로 현재 실행 승인으로 쓰지 않는다.

대안은 A 기존49조각 읽기 전용 새 프로세스 재현, B 새 snapshot을 만들고 두 프로세스를 새로 학습, C CPU 재개만 유지다. 동일 원형을 활용하면서 추가781MB 저장과 중복 prefix 갱신을 피하는 A를 택한다. 근거·문서 경계·스케줄·토크나이저·micro8×accum16/1024/ckpt-on/BF16·정책은 Stage5W 그대로이며 causal KD는 None이다.

현재 사용자105의 CPU/GPU 권한 안에서300초 상한·마감120초 예비·15시 종료·단일 GPU·할당6GiB/공유증가8GB를 적용한다. 런처는 run_P107_Stage7W_fresh_process_disk_resume.sh이며 출력/태그는 새로 만든다. 정합이 달라지면 결과를 보존하고 임의 허용오차를 추가하지 않는다. 정제 원천·추가300M·의미 품질·전원장애·GPU KD 재개는 시험하지 않는다.


### Stage7W 실행 회수 — 2026-11-01 오후

CPU39/0 뒤 새 프로세스 GPU84306/0·독립root86955/0으로 이전 V1 snapshot 읽기 전용2회 재개가 전체 exact였다. 기존49조각은 불변이고 새checkpoint0이다. 실제 정전/본학습 품질은 시험하지 않았다. 결과107§17과 완료 SH/manifest_v4가 원형을 소유한다.

### Stage8aW/8bW/8cW — 명시 입력 파일과 opt-in CLI 연결: 기술 완료

2026-11-04 사용자107의 선행 연구 뒤 미완료 작업 착수다. [파일별 권한·세 안·영향도](../docs/research/20261104_P107_명시입력과_CLI_연결설계.md)에 따라 기존 source/trainer/session/store를 재사용한다. 기본 run100m와 모델 구조는 바꾸지 않는다. 다른 세션의 정제/보호 데이터·추가300M은 제외한다.

Stage8aW는 입력 파일 SHA·토크나이저·TRAIN split·입장 선언·경로·크기·문서 ID·예약 mask·오류 차단과 기존 source의 경계/재개를 CPU에서 확인한다. 입력 모듈20회귀는0.898초/실제0이며 모델 품질 시험이 아니다. CLI 연결 회귀와 명시 소유 정적·현재 전체 smoke를 마친 뒤에만 GPU를 연다.

새 태그 p107_document_cli_v1_20261104를 첫 GPU 전에 예약한다. 정해진 네 합성 문서 JSONL과 명시 manifest만 사용하고, 원문 의미/권리/누설을 입장 코드가 증명한다고 주장하지 않는다. 실제 TRAIN 입력에는 별도 명시 승인과 정확한 shard/토크나이저를 묶은 근거가 필요하다. 이번 worker는 합성 목적만 허용한다. 구현은16M token/128MB 입력 상한이며75M 전량 streaming 완료가 아니다.

Stage8bW는 기존 Native595-Q·micro8×accum16×seq1024·checkpoint-on·BF16 AMP/FP32 master·Muon RMS4+AdamW·causal8/MNTP8·adaptive keep를 고정한다. 같은 기존8회 지평·warmup2/cosine의 첫2회만 기술 갱신한다. 첫 완료 경계를 새16MB 이하 조각에 저장한 뒤 두번째 경계의 전체 해시를 남긴다. Stage8cW는 새 Python 프로세스에서 같은 입력과 첫 경계를 읽고 두번째 갱신을 재현한다. 원본 model 파일·입력·소스가 불변이고 loss/target/LR/모델/optimizer/정책/source/RNG가 같아야 한다.

논리 입력은2×8×16×1024=262144토큰이다. 새 프로세스의 replay1회를 포함한 물리3갱신/393216토큰은 별도 센다. 작은 합성 풀은 기술 fixture여서 품질 학습의2배 풀 조건을 만족한 것으로 해석하지 않는다. 이미 끝난 적응 통계 비용 격자를 다시 비교하지 않는다. 새 질문은 파일/입장/CLI를 통한 실제 연결·거부·재개가 같은가다.

각 GPU phase600초·마감120초 예비, allocator6GiB·공유 GPU 시작 대비 증가8GB·단일 idle 장치를 확인한다. 예상전체GPU3~10분과 full smoke약8분은 비용 예측이다. 오류9/시간·자원HOLD8/기술종결0을 나누며 정합 실패에 임의 허용오차를 넣지 않는다. CPU/GPU 기술 성공은 본학습 효율·한국어/일상대화·benchmark 개선이 아니다.

예측은 파일 입력의 sampler 계약이 같은 바이트/RNG로 재개될 수 있다는 것이다. 잘못된 입장/토크나이저/부분 파일은 모델 로딩 전에 거부해야 한다. 실제 corpus 편입·편향·전체 학습/GradScaler/compile·외부 교사 결합은 미완으로 남는다. 새 CLI는 기본값에 붙이지 않는다. 실행용 SH는 CPU/메타데이터 봉인 뒤 작성한다.

실행 회수: CPU30/0과 현재 전체 canonical smoke106동작/44자식0 뒤 Stage8b와8c를 실제 수행했다. 새 파일 입력의 논리2회/262144입력과 replay 포함 물리3회/393216입력을 분리한다. run25.721747초·resume14.598884초이고 두번째 갱신 loss/target/LR 및 전체 model/optimizer/policy/source/RNG/세션이 EXACT였다. 새 경계781352215B를49조각으로 보존했고 원 CP/입력/source 불변·최종 CUDA0/0을 독립 root로 검산했다. 파일 거부와 전체 재개의 예측은 확인했으며 자연어 품질·75M streaming·실제 corpus 입장은 확인하지 않았다. [결과107§18](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md)이 실제 수치·명령·한계를 소유한다. 두 전체 worker 시간은 수행량이 달라 가속비로 계산하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## Stage9W — Explicit complete optimizer-group loss scaling

### 1. Why

Continue original58/59 GradScaler contact under current161. Preserve old P107 sources/defaults. Follow [scope/options/authority](../docs/research/20261118_scaled_optimizer_group_contract.md).

### 2. Question

Can complete accumulation/unscale/clip and all-group overflow skip preserve clean checkpoint/fresh-scaler restore?

### 3. Prediction

Expect synthetic finite update agreement within explicit FP32 tolerance and no optimizer step when either group's gradients overflow. No Native quality prediction.

### 4. Stages

Ownership/config -> fixed-scale backward -> unscale all -> global finite gate -> clip/step or skip all -> update once -> clean state/fresh restore.

### 5. Judgment

Require reference agreement/overflow no-step, clean-boundary validation and fail-closed handling of partial optimizer exceptions. Caller source/policy/schedule skip semantics remain separate.

### 6. Cost

CPU thread1/120 seconds; small new parameters, language tokens/model/GPU0. Tag p107_scaled_optimizer_group_v1_20261118 collision0; no install/new environment.

### 7. Execution

New synthetic controller contracts become result107 Stage9W raw evidence. No model/training launcher.

### 8. Limits

No Native/Muon/causal-KD integration, CUDA/FSDP/compile, full source/model/optimizer/RNG resume, quality or adoption claim.

### 9. History

[107 section19](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-scaled-optimizer-group-cpu) closes CPU14/0, synthetic finite reference/whole-group overflow no-step, growth/backoff and fresh scaler-state restore. Predictions supported at numerical scope. P107 skip/source/policy/schedule and Native/Muon/CUDA/full-training integration remain NOT_RUN.

## Stage10W — Explicit consumed-group scaler integration, CPU only

### 1. Why

Continue original58/59 after section19 numerical component. Follow [scope/options/policy](../docs/research/20261118_P107_scaled_group_integration_contract.md). Preserve old None defaults and exact before-source evidence.

### 2. Question

Can explicit consume-group overflow semantics bind scaler/data/policy/schedule and fresh complete-state restore without changing None behavior?

### 3. Prediction

Expect identical None loss/targets/full-state hashes. Finite opt-in should match synthetic FP32 control, overflow should advance one consumed group with zero optimizer steps, and a resumed following step should match.

### 4. Stages

Before-source/None oracle -> pure controller validation -> optional bound factory/exact policy -> enabled schema -> CPU default/overflow/KD/schedule/fresh-restore regressions -> result recovery.

### 5. Judgment

Require explicit policy, exact owner/run/micro binding, pre-copy invalid-state rejection, separate consumed/optimizer counters and fresh controller restoration. Arbitrary optimizer exceptions remain dirty failures.

### 6. Cost

CPU thread1/120 seconds; tiny new fixtures, no Native/GPU/old CP/corpus. Tag p107_scaled_trainer_v1_20261118 requires collision preflight. No package/env changes.

### 7. Execution

Owned before-source/None oracle and new CPU suites only. No model/training launcher.

### 8. Limits

Actual Native/Muon/teacher/CUDA/FSDP/compile, full75M source/corpus rights, quality and default adoption remain NOT_RUN. Disclose logical groups and applied optimizer steps separately.

### 9. History

[107 section20](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-scaled-trainer-consumed-group-cpu) closes the before-source three-mode/four-update None oracle and CPU51 opt-in consumed-group/fresh scaler integration. None state hashes and synthetic resume predictions supported. Actual Native/Muon/BF16-CUDA/CLI/75M/corpus/quality remain NOT_RUN; consumed groups and optimizer steps stay separate.

## Stage11W: bounded indexed document source, CPU contract

### 1. Why

Existing input/source retain all token tuples/tensors. [Impact/three options and contract](../docs/research/20261118_P107_indexed_document_source_contract.md) selects a separate offset index preserving uniform document/crop sampling, under original58/59 and current161.

### 2. Question

Can bounded record reads preserve resident token/document-ID/RNG draws and exact fresh CPU trainer resume?

### 3. Prediction

Expect exact sampler and tiny trainer equality. Metadata remains O(documents), startup requires a full byte scan and random I/O may be slower; no language-quality prediction.

### 4. Stages

Freeze existing pins -> strict existing manifest/admission/row validation and bounded offsets -> distinct source state -> resident/negative/read-budget tests -> tiny trainer/scaler/fresh restore -> result recovery.

### 5. Judgment

Require exact draws/RNG/resume, whole-file and selected-row identity, quota/path/admission gates and failed-update cursor/RNG rollback. Report payload/index counters separately from RSS. Existing source/input/trainer defaults must remain unchanged.

### 6. Cost

CPU thread1/120 seconds, at most roughly1M new synthetic tokens. No Native/pretrained model/corpus/GPU. Tag p107_indexed_document_v1_20261118 collision and similar-plan queries found none; actual language tokens0.

### 7. Execution

New owned synthetic CPU helper only. No training launcher, CLI flag or batch. No package/environment change.

### 8. Limits

Actual75M/8-hour production, source rights/semantic admission, Native/Muon/BF16-CUDA/compile/FSDP, full RSS/quality and default adoption remain NOT_RUN.

### 9. History

[107 section21](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-indexed-document-source-cpu) closes CPU15/source-current13: exact resident draws/RNG, three tiny trainer modes and fresh scaled CPU resume supported the predictions. The1M technical pool reports bounded row/index counters, not process RSS or actual75M. Native/quality/corpus/CLI/default adoption remain NOT_RUN.

## Stage12W. 새 Native에서 GPU 스케일러와 세 masking 경로

### 1. 비교 방법

원장 58·59의 새 학습 경계를 검증한다. 기존 checkpoint를 복사한 두 갱신과 CPU51 결과를 재사용한다. 이번에는 새 Native dense14 모델에서 `CONSUME_SCALED_GROUP`으로 실제 갱신한다. 사용자161의 현재 GPU 승인에 따라 기존 파일이나 설정을 변경하지 않는 연구 실행으로 한정한다.

| 방법 | 판단 |
|---|---|
| `uniform` | 토큰 관측이 없는 원 균등 방법. 학습 대조의 기준으로 사용한다. |
| `observe` | 같은 균등 분포와 원 토큰 관측을 수행한다. 통계 비용과 동일성 대조에 사용한다. |
| `adaptive` | 두 그룹마다 실제 관측에서 가중치를 갱신한다. 입력 원천, 기대 mask-rate와 updater는 맞춘다. |

### 2. 자원·판정

태그 `p107_native_scaled_uniform_observe_adaptive_v1_20261118`. 새 합성 원천 64문서에서 독립 검증 4문서를 따로 만든다. batch4·128×4회, 앞2 causal과 뒤2 MNTP, 목표 masking 확률 .15, 세 조건마다 여섯 그룹, 같은 95.33M 초기값과 matched Muon/AdamW 경로를 사용한다. 비어 있는 옵티마이저 그룹 두 개는 소유를 정하기 전에 제외한다. 원 데이터·하이퍼파라미터·분모와 causal likelihood의 초기 공통값, RNG·입력·완료/skip 수, 실제 GPU wall·할당·토큰 통계 비용을 측정한다. 정확 일치가 깨지면 어느 축인지 먼저 보존한다. 합성 검증 손실로 한국어, 실제 자료 편향, 채택을 판정하지 않는다. CPU1로 input source를 확인하고 GPU 1장에서 300초 이내 자식을 직렬 실행한다. 새로운 checkpoint는 작성하지 않는다.

13:32:16 KST 종료 0. 관측과 균등의 실제 여섯 갱신 결과가 비트 일치했고 적응형은 3차부터 마스킹 수가 달라졌다. 세 팔의 검증 분모와 장치 비용, 실제 갱신 18회를 회수했다. [결과107 §22](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-native-scaled-three-actual)

2026-11-19 후속 P102A는 같은 적응 학습기의 FP32 CE와 관측 ID를 G4 R1에서 재계산했다. 동일한 마스크 및 학습 상태와 최대 할당 절감을 확인했다. 실제 언어 평가와 R2 명시 가시성은 기존 선결을 따른다. [결과093 §45](../test_result/093_20260925_P102A-기능통과-T1-단일순서-속도관측.md#p102a-adaptive-fp32-target-head)

<a id="p107-g4-fixed-r2-visibility-plan"></a>
### StageR2W — G4 고정 R2의 문서 경계와 적응 재계산 기술 검증 완료

P109의 고정 R2 학습에 P107 가시성을 적용할 수 있는지 검증한다. 기존 2+12+2, G4·CLA2의 기본 순회와 같은 28개 방문만 실험에 입장시킨다. 각 순회에 독립된 KV가 적용되므로, 토큰과 미분의 문서 경계를 유지하리라고 예상한다. 인과·MNTP에서 어떤 문서의 로짓이 다른 문서 토큰을 바꿔도 일치하고, 다른 문서·PAD의 입력 임베딩 미분은 0이어야 한다. 같은 경계를 의도적으로 열면 변화와 교차 미분이 관측되어야 한다. 순전파 뒤 호출자 마스크를 바꾼 경우의 체크포인트 역전파도 원 경계와 대조한다.

CPU 작은 모델과 실제 P079 G4 CUDA에서 가시성·미분·틀린 순서 거부부터 확인한다. 현 모델 가시성은 기본 R1 계약을 사용하며, R2 검증용 런처가 그 형상·순서만 검사한다. 이어서 결과093 §45의 자료와 8×512·4micro·6갱신·BF16 AMP·FP32 CE·스케일러를 고정한다. G4 R2의 전체 CE와 행 재계산을 비교하며 이미 완료한 R1 두 팔은 재사용한다. 각 팔 98,304 위치에서 손실·마스크·argmax·최종 모델과 두 optimizer·RNG·정책을 대조하고 학습 할당·시간을 기록한다. 정식 TRAIN 및 방문 순서가 변하는 조건은 별도다. GPU 전용 진단 창은 200초 이내, 각 학습 팔 상한은 90초, 예상 1분 내외다. 1분이 넘는 실제 큐는 기존 감시 역할을 적용한다. [시험 런처](../scripts/diag_p107_g4_r2_visibility.py)

**결과 회수.** CPU와 실제 P079 G4 CUDA의 인과·MNTP에서 차단된 문서의 영향과 입력 미분은 0이었고, 경계를 열면 두 값이 달라졌다. 마스크 변경 뒤 체크포인트 역전파도 재현됐다. 고정 R2 두 팔의 마스크·예측·FP32 손실·최종 상태가 일치하고 학습 할당은 35.84% 낮아졌다. 42초 GPU에서 12회 실제 갱신과 장치 반환을 회수했다. 고정 R2의 해당 기술 범위가 검증됐다. 변형 순회와 언어 품질은 별도다. [결과107 §23](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-g4-fixed-r2-visibility)

<a id="p107-g4-policy-visibility-plan"></a>
### StagePolicyW — P109 변형 순회의 CPU 문서 격리 검증

고정 R2 대조를 재사용하고, 같은 합성 두 문서에서 P109 `balanced_count`의 16·40 방문과 `second_shuffle_r2`의 28 방문을 검증한다. 실제 P109 학습 래퍼의 절대 갱신별 순서를 사용하고 그 순서만 실험에서 마스크 검사를 통과시킨다. 작은 CPU 장치에서 인과·MNTP와 관측 문서를 교차한 12조건의 문서 밖 로짓·입력 미분 불변, 호출자 마스크 변경 뒤 체크포인트 미분 일치, 열린 경계에서의 양성 대조를 판정한다. `p107_g4_policy_visibility_cpu_v1_20261119`는 GPU 호출과 체크포인트 로딩 없이 실행한다. GPU 적응 학습과 자연어 성능은 별도다. [진단 코드](../scripts/diag_p107_g4_policy_visibility_cpu.py)

**결과 회수.** 순서 검증기의 튜플 입력을 목록으로 고친 뒤 같은 세 순서의 12조건에서 문서 격리와 스냅샷 미분을 확인했다. 경계를 연 9조건에서 로짓과 미분이 모두 변했다. 실제 G4의 변형 순회 GPU와 적응 학습 검증은 이어받는다. [결과107 §24](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-g4-policy-visibility-cpu)

### StagePolicyCudaW — 실물 G4 CUDA의 변형 순회 문서 격리

새 태그 `p107_g4_policy_visibility_cuda_v1_20261119`는 CPU에서 회수한 16·40·28 방문과 가시성 조건을 P079 실물 16층 G4 R2·CLA2 모델에 적용한다. 같은 합성 두 문서에서 BF16 AMP와 math SDPA를 사용한다. 닫힌 12조건에서 가려진 문서의 로짓 영향과 금지 위치 미분이 0이어야 하며 스냅샷 역전파를 재현해야 한다. 열린 9조건은 양성 대조다. 사용자 176의 승인 범위에서 단일 GPU로 1분 이내 예상, 실행 상한 55초다. 체크포인트 로딩은 기존 P079 하나에 한정하며 optimizer 갱신과 모델 저장은 0회다. [GPU 진단](../scripts/diag_p107_g4_policy_visibility_cuda.py)

**결과 회수.** 첫 장치 문맥은 임베딩 기록을 중복 호출했다. 관측 입력만 명시적으로 CUDA에 둔 v2에서 닫힌 12조건과 열린 9조건을 회수했고, GPU는 14초에 종료 0이었다. 변형 순회 적응 학습은 별도다. [결과107 §25](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-g4-policy-visibility-cuda)

<a id="p107-g4-policy-adaptive-plan"></a>
### StagePolicyAdaptiveW — P109 변형 순회에 맞춰 적응 마스킹을 학습한다

P109의 균등 방문 배분과 둘째 순회 셔플을 각각 실제 G4 학습에 적용한다. 학습기의 절대 갱신마다 P109 순서를 계산해 causal·MNTP의 네 순전파와 네 역전파, 해당 갱신의 옵티마이저 적용까지 고정한다. 기존 고정 R2와 같은 P079 초기 상태, 합성 문서 소스·시드 1337·순서, 기존 적응 마스크 시드와 스케일러, BF16 AMP·FP32 CE·math SDPA를 사용한다. 기존 고정 R2의 양팔과 둘째 순회 가시성은 재사용한다.

각 변형 정책에서 기존 전체 출력부와 512행 재계산 출력부를 나란히 둔다. 양팔의 마스크·관측 ID·손실·미분 노름·최종 모델·두 optimizer·정책·RNG·소스·스케일러가 일치해야 한다. 모든 팔의 8×512·4micro·6갱신은 98,304위치와 2,752,512 위치·층 방문을 소비한다. 균등 배분은 16·28·40방문을 사용하되 전체 평균 28을 맞춘다. 셔플은 둘째 순회의 공유 소유자 쌍만 바꾼다. 고정 R2와의 마스크·예측·상태 차이는 변형 순회가 실제 갱신에 반영됐는지 확인하는 근거로 사용한다.

새 태그 `p107_g4_policy_adaptive_v1_20261119`로 네 팔을 같은 GPU에 직렬 실행한다. 예상 약 1~2분, 가용 12GiB 이상, 팔당 상한 85초다. CPU에서 원본과 일정, 실제 총 방문 예산 및 이전 실험의 종료·수치를 봉인한다. 저장하는 새 모델 파일은 없다. 합성 적응 갱신과 메모리 대조 이후 정식 자연어 학습·평가는 P109의 자료 입장 조건을 따른다. [실행 코드](../scripts/diag_p107_g4_policy_adaptive.py)

**결과 회수.** 네 팔의 24갱신이 종료 0이었다. 두 정책 모두 대응 기준의 선택 마스크·예측·손실·미분 노름과 최종 상태를 재현했다. 학습 할당은 균등 방문 34.59%, 둘째 순회 셔플 35.84% 줄었다. 기존 고정 R2와 두 정책의 최종 상태는 달랐고, 셋째 갱신부터 각각 마스크 선택도 달랐다. [결과107 §26](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-g4-policy-adaptive)

<a id="p107-lexical-mask-audit-plan"></a>
### 원장 58·59 후속. 문서 언어와 숫자 토큰을 MNTP 마스크 위치에 대응한다

기존 합성 실험의 자리·토큰 ID 라벨은 실제 언어와 숫자 위치를 확인할 수 없다. 원문을 다시 인코딩하는 진단기를 사용한다. 문서 언어는 명시된 메타데이터로 분류하고, 숫자는 토크나이저의 원문 문자 범위에 유니코드 십진 문자가 포함된 토큰으로 정의한다. 빈도는 해당 분할의 마스킹 전 참조 토큰 수에서 얻는다. 실제 마스크를 누적한 횟수와 분리한다. 학습기 내장 계측은 경로 비용을 바꾸고, 토큰 표기만으로 라벨을 추정하면 원문 위치를 잃는다. CPU 진단은 기존 정책과 eligibility를 직접 호출하면서 그 두 경로를 건드릴 필요가 없다.

`p107_lexical_mask_selection_audit_v1_20261120`는 기존 32K 토크나이저와 직접 작성한 한·영·혼합·미분류 문장 4개만 사용한다. 같은 위치와 같은 RNG 상태에서 균등과 적응을 대조한다. 동일한 문서 수, 토크나이저, 기대 마스크 비율 .15를 유지한다. 숫자 예측을 틀리도록 만든 기술 관측을 먼저 주면 적응이 숫자 위치에 더 높은 기대 할당을 줄 것으로 예상한다. 버킷별 적격 수, 기대 선택 수, 실제 선택 수를 내고 문서 첫 토큰, PAD, 마지막 전체 토큰 및 없는 버킷을 검사한다. 실제 선택 수는 난수에 의존한다. 문서 언어가 같아도 개별 단어 언어는 다를 수 있다.

CPU 1스레드, 상한 60초, 모델 로딩·optimizer·GPU 실행 0회다. 등록 태그와 유사 런을 조회했고 기존 §7 가상 라벨과 관측 변수가 다르다. 정식 TRAIN 빈도 임계값, 원문 권리·출처·분할, optimizer와 causal 생성·likelihood 대조는 별도 게이트다. [CPU 진단](../scripts/diag_p107_lexical_mask_audit.py)

**2026-11-20 결과.** CPU 집계 검증을 완료했다. 992개 적격 위치와 모든 버킷의 분모·선택 수가 독립 위치별 회계와 일치했다. 숫자 오답을 넣은 양성 대조에서 숫자 기대 선택은 늘었고 전체 기대율은 .15로 유지됐다. 정식 TRAIN 편향·causal 품질은 대기다. [결과107 §27](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-lexical-mask-audit)

<a id="p107-adopted-v11-mask-pair"></a>
### 원장 58·59. 정제 v1.1의 같은 무부모 학습에서 균등과 적응을 비교한다

최종 채택 TRAIN·VAL의 uint16 캐시에서 조립기가 문서마다 붙인 EOS 위치를 색인한다. 양 분할의 전체 문서 수와 바이트·지문을 대조하고 같은 seed의 문서 표지가 일치하는지 확인한다. 오래된 합성 CLI와 최대 75M의 JSON 문서 도구는 기존 범위를 유지한다. 새 바이너리 소스는 승인된 분할 전체에서 창을 추출하고, 경계를 넘는 정답과 어텐션을 각각 차단한다. [최종판 분할](../test_result/109_20261119004016_P109-기존G4-방문-세정책-실제갱신.md#p109c-adopted-v11-split-result) · [바이너리 문서 색인](../scripts/p107_v11_binary_documents.py)

활성 16층 G4 R2, 무부모 초기값과 원문 창, 1,024 문맥, micro 4×누적 32, 인과·MNTP 각 16마이크로배치, BF16과 512행 재계산 CE, Muon RMS4·AdamW 및 WSD를 맞춘다. 명시 문서 가시성을 쓰는 MATH 어텐션의 1,024 길이 중간값을 버리고 역전파에 재계산하도록 양팔 모두 활성값 체크포인트를 쓴다. 균등 팔도 같은 예측 통계를 모은다. 적응 팔에서만 그 통계를 다음 위치 확률에 반영한다. 전체 기대 마스크율은 .15다. 선택 확률과 실제 마스크 수를 구분한다. 독립 VAL의 문서 격리 causal NLL 및 실제 지도 토큰, 시간·VRAM을 기록한다. 독립 생성과 선택지 성적은 추가 품질 증거다.

양팔 각 16갱신을 실제 실행하여 시작 상태와 샘플러의 일치, 시점 복원, 자원과 시간에 필요한 비용을 확인한다. 그 상태에서 이어서 최대 각 2,289갱신·300,023,808슬롯을 목표로 한다. 잔여 시간으로 전량을 완료하기 어렵다면 같은 진행 경계와 원래 학습률 일정에서 가능한 두 팔의 동일 구간을 회수한다. 이 구간의 결과는 300M 완주 성적으로 분류하지 않는다. GPU 감독 최고 12,390MiB, 승인 종료 전 중단, 평가는 P109C 종료 후 직렬 인계다. [실행기](../scripts/run_p107_v11_mask_pair.py) · [동결 위치 진단](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-v11-frozen-mask-selection-result)

공통 부분 경계에 도달하고 두 팔의 최신 실측으로 추가 진행이 가능하면 같은 가중치·옵티마이저·적응 통계·원문 추출 상태에서 자동으로 이어서 학습한다. 다음 공통 경계는 양팔 각 300M에 제한한다. 먼저 전량을 마친 경우 후속 프로세스는 결과 확인에서 종료한다. [부분 경계 재개 실행기](../scripts/continue_p107_v11_mask_pair.py)

같은 갱신에서 닫힌 두 팔에 별도 CPU 인과 평가를 적용한다. 기존 GPU의 64개 검증 창과 다른 고정 시드로 VAL 128창을 선정했다. 최종 TRAIN 전체에서 센 토큰 빈도와 한글·라틴 문자·십진 숫자 포함 여부로 목표를 묶고, 문서 경계를 차단한 28방문 FP32 우도와 다음 토큰 적중을 잰다. 채팅 CPU 첫 실사용 16문항에서는 실제 답과 정상 종료를 같은 방식으로 잰다. 자연 추출한 검증 창의 저빈도 목표는 결과에 실제 분모를 표시한다. [동결 프로필](../data_cache/p107_v11_causal_group_profile_v1_20261121.json) · [평가 실행기](../scripts/eval_p107_v11_causal_groups_cpu.py)

자연 추출의 희귀 표본을 보완하려고 학습 중 빈도로 분류한 VAL 목표를 전량 센다. 기존 두 평가의 창에 들어간 목표 위치는 제외하고, 문서 첫 토큰을 제외한 1~32회 등장 토큰과 미등장 토큰을 전량 후보로 보존한다. 33~1,024회, 1,024회 초과와 숫자 포함 그룹은 같은 시드에서 문서당 하나씩 최대 96개씩 뽑는다. 같은 문서에서 실제 직전 최대 128토큰만 모델에 주고 정답 NLL·순위·최고 선택을 기록한다. 이는 정해진 저빈도 위치에 대한 조건부 대조다. 전체 VAL과 다른 문맥 길이의 일반 성과는 기존 자연 추출에서 확인한다.

### 문서 격리 어텐션의 연산과 임시 메모리 후속 대조

현재 MATH 경로는 1,024 전체 마스크와 활성값 체크포인트를 사용한다. 단일 문서 마이크로배치만 기본 경로를 쓰는 대안은 실제 예정 훈련에서 약 2%에 적용된다. 각 행의 실제 문서 구간을 묶는 대안은 모든 창에 적용할 수 있다. 현재 설치한 PyTorch 2.10의 `varlen_attn`을 이용해 RoPE 적용 뒤의 Q·K·V 순서, 각 문서의 누적 오프셋과 인과·양방향 조건을 보존한다. 먼저 실제 GPU의 해당 GQA 형상에서 순전파와 미분, 자원을 확인한다. 이후 같은 원문·가시성·목표와 갱신을 통제해 속도·메모리·causal VAL을 따로 잰다. [실제 창과 CPU 산술](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-v11-document-local-attention-geometry) · [PyTorch 2.10 문서](https://docs.pytorch.org/docs/2.10/nn.attention.varlen.html)

같은 실물 G4 896갱신 가중치와 v1.1 인과·MNTP 각 한 마이크로배치로 순전파와 역전파를 교차 실행한다. 기존 MATH·K/V 반복·활성값 체크포인트, 문서 구간 Flash·12:3 GQA·활성값 체크포인트, 같은 Flash에서 활성값 체크포인트 해제를 비교한다. `4×1,024`, 28방문, 512행 재계산 CE, 같은 인과·MNTP 입력과 지도 위치를 유지한다. 각 경로의 처음 두 묶음을 준비로 두고 순서를 반대로 반복해 시간·할당·손실·미분·마스크 위치의 예측 ID를 확인한다. 체크포인트를 변경하거나 옵티마이저를 적용하지 않는다. 실측 경로가 GPU 메모리 한도를 넘으면 해당 설정의 한계로 기록한다.

실제 F+B에서 체크포인트를 유지한 Flash가 두 배치 모두 짧았다. 1,152 균등 팔의 동일한 본체·옵티마이저·관측·원문 저장점을 원래 MATH와 Flash로 각각 16회 재개한다. 두 팔의 균등 마스킹, 절대 학습 일정과 감독 위치를 맞춘다. 새 실행에서는 중간 저장을 만들지 않고 본체 지문, 구간 시간, 기존 MATH 검증과 장치 사용량을 회수한다. 완료 여부와 시간은 실제 로그로 판단하며 이식의 전체 학습 품질은 장기 대조에서 시험한다.

**결과 회수.** v1.1의 균등·적응은 각각 150,994,944슬롯을 마쳤다. CPU 인과 전체 NLL은 4.29713·4.29759, 독립 첫 답은 두 팔 0/16이다. 문서별 Flash의 후속 16갱신에서 중앙시간 16.740→6.881초, 같은 MATH 인과 NLL 4.349812→4.351236을 관측했다. 원장 58·59의 다음 진행점은 두 1,152 네이티브 원본이다. 원래 전체 지평과 노출을 유지하고, 새 연산 경로를 양쪽에 함께 적용할 때의 장기 품질을 기록한다. [151M CPU 대조](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-v11-matched-1152-cpu-result) · [실제 갱신 비용](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-v11-packed-optimizer-actual)

<a id="p107-v11-flash-continuation-300m"></a>
### v1.1 두 1,152갱신 저장점의 문서별 Flash 연장

사용자 215 승인에서 기존 두 저장점을 그대로 이어 학습한다. 두 팔에 같은 문서별 Flash GQA를 적용하고 독립변수는 균등·적응 마스킹이다. 동일 문서 위치·인과 타깃과 원래 WSD 절대 2,289갱신을 고정한다. 팔당 잔여 1,137갱신은 149,028,864슬롯이며 완주 누계는 300,023,808슬롯이다. 검증은 기존 MATH 인과 경로와 최종 공통 CPU 문항을 사용한다. 출발점의 원문·스케줄과 저장된 적응 통계를 재사용하고, 같은 노출에서 관측한 정책 차이를 판정한다. Flash의 장기 인과효과는 별도 대조에 해당한다.

태그 `p107_v11_mask_pair300_flash_resume1152_v1_20261122`와 기존 프로필 및 16갱신 Flash 영수증의 지문을 봉인한다. 이전 실제 16갱신의 6.881초를 기준으로 두 팔의 갱신 구간을 약 4시간 20분으로 추정한다. 적응 팔과 긴 구간의 시간 변화를 고려해 측정된 상위 갱신 시간에 여유를 포함한 동등 경계를 먼저 정한다. 이 실행의 마감은 11월 23일 07:00 KST, 카드 상한은 기존 12,390MiB다. 절대 갱신·누적 인과 노출·원문 RNG·두 완전 저장점·종료와 GPU 반환을 확인한다. [재개 실행기](../scripts/continue_p107_v11_mask_pair.py) · [사용자 215와 작업원장](../handoff/WIP_20261022_작업원장-done.md)

완료 모델의 점수 JSON에서 같은 문서·위치·타깃을 짝짓는다. 희귀 목표 패널에서 문서를 10,000회 복원 추출한 NLL 차이의 95% 범위와 최고 선택의 득실을 보고한다. 1,152갱신 저장 점수에서 0~32회 훈련 빈도 목표는 합계 1개였다. 나머지 각 96개 위치의 문서 재표집 범위에는 모두 0이 들어갔다. 기존 점수로 비교기를 검증했으며 평가 모델을 다시 실행할 필요는 없다. [쌍 비교기](../scripts/compare_p107_v11_scored_arms.py) · [1,152 저장 점수의 추정 범위](../handoff/audit/P107_V11_1152_SAVED_PAIRED_INTERVALS_20261123.json)

**완료 · 결과107 §§41~42.** 두 팔의 300,023,808슬롯과 각 저장점, 장치 반환, 독립 자연 창·희귀 및 첫 실사용 평가를 회수했다. 전체 인과 NLL은 적응에서 −0.00167이었고 최고 선택 적중은 89개 줄었다. 숫자 자연 창과 별도 표본의 방향이 달랐다. 균등을 기본으로 유지하며 독립 시드와 충분한 희귀 표본이 있는 대조로 조건부 효과를 확인한다. [결과107 §§41~42](../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-v11-flash-full-300m-gpu-result)
