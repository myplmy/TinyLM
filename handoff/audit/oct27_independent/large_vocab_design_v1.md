# 큰 어휘 실제 학생의 packed 경로 — 착수 영향도와 선택

사용자96/97의27일17시까지 독립 미완 작업 중 원장65다. 다른 세션 정제·추가300M 금지를 유지하며 기존 완료 G270Tfull만 읽는다. 메타데이터12029/실제0·2.622초에서 V262144/E256·20물리층·중간16/g8 공유·FP32 저장·2289step과 원CP SHA0AC6D2E1…를 확인했다. 이는 외부 Gemma270M 모델이 아니라 해당 교사로 과거 학습한 TinyLM이다. 기존053§13의 같은 해시·반복/오답을 보존한다.

## 세 방안과 선택

| 안 | 내용 | 장점 | 단점/영향 | 비용 |
|---|---|---|---|---|
|A 권장|기존 G270Tfull의 원scale 몸체와 기존 per-row TWN 표를 같은 codec/loader로 실제 내보내기·CPU/CUDA 대조|새학습 없이 실제 큰V lookup/head·storage·속도·원답을 확인|학습 tokenizer SHA는CP에 없어 현재 지정표의 범위 호환만 확인. 기존 오답 모델의 품질향상 증거는 아님|새얇은driver/회귀·최대5단계 합10200초+종결, 실제비용 입장|
|B|V248320/262144의 합성 표 연산만 검사|기하/패딩/큰ID 검사는 저렴|실제 공유 본체·임베딩/헤드·cache·원답·상주를 확인하지 못함|CPU 소형 회귀에서만 사용|
|C|새 교사 어휘와 정확한SHA로 본학습 후 패킹|직접KL/같은tokenizer·새품질 목표까지 연결 가능|현재 추가300M 금지·정제/교사 계약·본학습 시간이 먼저 필요|현재 실행하지 않음|

A를 선택한다. 현재32K 완료 모듈을 재사용하며 새학생/새코덱/원33소스 수정은 하지 않는다. 직접KL·Qwen/Bonsai tokenizer 동일성·전체40MiB는 별도 미완이다. 기존 G270Tfull과 현재 Gemma4 교사의 token ID가 같다고 가정하지 않는다.

## 파일별 허용과 제외

| 경로 | 동작 | 근거 | 제외 |
|---|---|---|---|
|scripts/diag_p014e_large_vocab_deploy.py·대응 test|신설|현재96/97의 미완65 구현/실측|제품 기본/기존33코드 변경0|
|새 Stage4Wg/h/i SH·experiments.tsv|신설/해당3행만 추가|같은 실행 위임·기존 배치 절차|기존완료 SH 재실행/삭제0|
|runs/ckpt/m100R1c_ko-en_300M_G270Tfull.pt|정확 바이트/가중치 읽기|기존 결과/CP 재사용|원CP·optimizer 쓰기/새학습0|
|지정 Gemma1B tokenizer JSON|읽기/해시/API 범위 검사|과거 사용자 지정과 원장65|새 취득/다른 tokenizer 추정0|
|runs/deploy/p014e_g270_large_vocab_v1_20261027|새 payload/oracle만|실물패킹 결과|Git/staging/원형 덮기0|
|test_result/evidence의 같은 고유tag·audit|작은보고/해시/원답|기존 결과 보존 절차|단일 결과/로그20MB 미만|
|P014E/결과099·목록/기준표/방법론/COMPASS/WIP|해당축 갱신|기존 사용자 절차|타정제 축·09 수정0|

## 영향도

| 축 | 영향과 처리 |
|---|---|
|코드/중복|이미 있는 p014e_packed_g128의codec/export/load/alias복구, resource의FP32 wrapper/관찰·storage·정리와 product sample을 재사용. 새 loader bridge는 기존resource의32K untied 전용 guard를 완화하지 않고 정확한 옛tied/V262144 CP만 검산|
|데이터|학습자료/정제 변경0. 새배포파일 두형식과 기기/형식/문맥별 oracle만 생성. 큰모델 payload는runs에 두고 262K×16로짓 oracle은 문맥별로 나눔|
|시험|잘못된 source/header·범위 밖 이미지ID·Gemma EOS1/forced종료·공유 alias·타일/원scale 대응을 CPU회귀로 검증. 정적 뒤 실제 모델/해제 확인|
|정본|P014E/099와연쇄 문서의 현재범위/예측/실제를 구분. 기존32K 결과/음성·053의오답을 보존|
|기술부채/우선|정확단일 옛CP bridge의 범위를 명시. 임의 큰V 일반지원/새학습 loader로 확장하지 않음. 직접packed커널이 아닌 느린 참조언팩을 가속으로 채택하지 않음|
|GPU/승인|현재96/97·17시 이전만. 하나씩/현재free 확인·강제상한/정리, 추가300M0|
|소유권|정제세션 전용 경로·원장/프로세스0, 원형/원CP 수정0. tmp로큰CPU/I/O 공유부하 통보|
|비교유효성|같은CP/현재지정tokenizer/원body scale, FP32표와기존TWN표는각자별도 기준. 옛32K와품질차이비교0|
|증거수준|실제storage/KV/allocator/RSS·TTFT/속도/원답과 기술수치·정답성을 분리|
|문서연쇄|결과→계획→목록→기준표→방법론→COMPASS/WIP에서 미완을 완료로 바꾸지 않음|

## 고정 실행 계약과 preflight

신규학습0으로 steps×micro×accum·풀2배·학습sigma는 비적용이다. 레지스트리의 tag/유사조건을 각각 별도 조회했고, 기존32K 완료 실험과 새 V262144 실물은 다른 입력이다. 새tag의출력만 허용한다.

두표형식은 FP32 그대로와 기존 per-row TWN의5트릿 패킹이다. 본체 g128 원scale은그대로이며전체행 타일4096을 쓴다. packed 표의head는1024행씩, lookup은실제입력ID행만복원한다. 어휘전체FP32표를packed runtime이 보유하지 않으며 output logits 자체와동시에필요한작업버퍼는별도계수한다. 원형의FP32표 보존 기준선은그자체로큰상주다.

Gemma tokenizer의기본262144와추가image special1개를 product의명시 extra-special 계약으로검사하고매입력0..262143범위를검사한다. 지우거나재매핑하지않는다. 자연답은실제EOS1,forced16은EOS정지off이며기존chat32의EOS2를재사용하지않는다. 한영4문맥은현재표로128/512native ID를고정,예열1/실측3/관찰1,자연4질문최대32다. 관찰/무관찰의ID·종료를대응한다.

같은기기/형식 기준선의전체어휘16위치 로짓을rtol2e-5/atol2e-6로확인하고허용오차는바꾸지않는다. 표양자화로생긴품질변화와패킹동률은구별한다. CPU/gpu의모든출력이같을필요는없다. 기준선과packed의경로차이·원답·KV/상주와해제·원CP/소스불변을남긴다. 미완예산8·오류9·전체기술0은따로보존한다.

상한은export900/baseCPU1200/baseCUDA900/packedCPU5400/packedCUDA1800초다. 각단계와종결180초가현재17시안에들어야시작한다. packed비용은prefill과추가decode를분리한4토큰관찰에서보수적으로전체고정량을예측하며한도를넘으면축소대신HOLD다. 속도나메모리이득은실측전보장하지않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 실행 전 반 검토 반영

문헌/정/반 역할은 읽기만 수행했고 총괄이 새2코드에만 반영했다. legacy_source의로드·이동을포함한전체구간을보호하고최초오류를보존한채각final검산/해제를독립시도한다. fingerprint/clear/toCPU의복합실패에도원CP최종해시가시도되는회귀를추가했다. baseline CUDA도형식별conversion+suite peak를실패경로의finally에서기록하며복구용원FP32표가남는범위를명시한다. 입력은이름뿐아니라정확한언어/128·512길이/질문ID·순서/중복을검사한다. 기존33모듈/오류문턱변경0이다.

최종CPU10회귀42798/실제0과프로필v3·metadata19418/0을회수했다. 앞fixture차원/KV오류의v1/v2실패는원로그로남기고모델실패로세지않는다. profiles v1/v2는미실행준비이력이며실제사용후보는source35 SHA841A8FB7…·v3 profile SHA82C18522…다. 전체소스/SH봉인과정적이실제모델실행전남은선결이다.
