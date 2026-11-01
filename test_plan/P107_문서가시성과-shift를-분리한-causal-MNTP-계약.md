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
