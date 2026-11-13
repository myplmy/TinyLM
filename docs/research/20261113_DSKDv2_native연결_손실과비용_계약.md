# DSKDv2 native 연결 — 투영 신호·실제 양공간 미분·추가 비용

사용자115의17시까지 총괄 CPU/GPU 위임 범위다. 기존 CPU13·head/VJP·교사128행과
복구4행을 반복 성과로 세지 않는다. 새로 확인하는 것은 실제 교사 표현의 초기 투영,
고정 native head에서의 shape 수치 계약, 학생 본체까지의 실제 양공간 손실/미분과 비용이다.

| 안 | 방법 | 근거·한계 | 영향·비용 |
|---|---|---|---|
| A, 선택 | 실제 cached hidden538/원CE772를 사용해 native head·양공간 연결, update0 | 전량 본학습 전 구현·메모리 선결을 분리 | 새 helper/driver/CPU6·SH4, GPU 약5~15분 상한30분 |
| B | 투영기를 먼저 최적화 | 초기 근사를 개선할 수 있으나 노출·학습 선택이 추가됨 | 추가 학습/검증 비용, 이번 미실행 |
| C | 초기 오차만 보고 폐기 | 비용은 없으나 실제 hidden과 미분을 확인하지 않음 | 새 증거 없음 |

권장 A를 총괄이 선택한다. 작은 학습을 지능 성과로 평가하지 않으며 이 실행은 optimizer0이다.
원 TinyLM factor768→256→32768과 교사 native248320×1024 head를 사용한다. 공통23302는
초기화 열에만 쓰고 양공간 softmax 전체 vocabulary는 자르지 않는다. 원교사 모델 본체는
올리지 않고 이미 원형 검증한 정규화 표현과 동결 head 텐서만 사용한다. 원CE·단일 shift·
owner·zero-lookahead와 보류234를 보존한다. 수락538은 의미 정답률이 아니다.

## 단계와 판정

1. CPU6: 독립 dense 수식 대비 native factor 손실/VJP, stop-gradient, 고정 frame의 원위치
   scatter/gather, 범위/중복 거부, chunk/global 분모, 완전 토큰 label 범위를 검사한다.
2. CPU native: 동일 완료93M 모델의 head만 CPU에서 로드하고 이미 검증한 pinv 초기화를
   재구성한다. 실제 teacher hidden538의 투영 top1/교사 native mapped top1 일치를 언어와
   mapping 유형별로 기록한다. 기존 head 연산/VJP와 동일 연산자를 확인한다. 품질 문턱은 없다.
3. GPU head: 첫 한영/UTF8 조각 두 위치가 속한 같은4행의 cached hidden을 사용한다.
   full1024 head와 원 native top1/fullLSE를 확인하고, 원위치1024 scatter 및 작은 chunk를
   원허용오차1e-5/1e-4와 같은 argmax로 대조한다. chunk가 실패하면 문턱을 바꾸지 않고
   원위치 고정 frame을 선택한다. 고정 frame도 실패하면 후속 손실은 중단한다.
4. GPU student: 같은128행·m8×a16·폭1024·BF16 eager·checkpoint-on·MTP-off, 결정론 정책으로
   CE/KD/KD/CE의4회 backward를 측정한다. 본체 CE는 기존 consumer를 그대로 재사용한다.
   KD는 전체538분모로 student-space KL+teacher-space KL+projector CE를 더한다. 계수1은
   기술 진단용이며 생산 recipe 채택이 아니다. 교사 hidden/head와 역방향 투영은 동결한다.
   교사→학생 투영만 projector CE에서 미분되고 학생 본체/head는 원 CE와 KD에서 미분된다.
   실제 gradient 반복은157개와 새투영을 비교하고 finite/nonzero·stop-gradient·원CP/core불변·
   CUDA0/0을 닫는다. 수치 실패도 원판정으로 남기며 허용오차를 늘리지 않는다.

## 영향·보호

새 namespace `p106b_dskdv2_bridge_v1_20261113`의 작은 보고서와 프로파일만 추가한다.
feature는 기존 캐시를 읽고 원본을 변경하지 않는다. head FP32970MiB와 투영/미분 버퍼가
추가될 수 있다. CPU RSS, GPU allocated/reserved, 첫 사용/정상상태 시간은 따로 기록한다.
학습/optimizer/CP 저장0, 추가300M0, 제품·공용 checker·타정제·TinyDataset·설치·Git변경0이다.
기존 별도 head 초기화/교사 수집/실패 finalizer는 덮어쓰지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 순증분: 큰 gradient의 출처 분리

실제계수1의전체norm122.2505에는추가투영이들어있어학생본체의과대신호인지아직모른다.
A(선택)는원128의한body forward pass와 CE/학생KL/교사KL/투영CE의개별미분을구한다.
B는지금계수1그대로교육하지만초기투영70/538·큰신호를해소하지못하고, C는norm만으로
방법을폐기하지만어느그룹이문제인지알수없다. A가최소순증분이다. 새GPU예상1~3분/상한30분,
학생파라미터공간과별도투영을나누고입력/출력공유embedding은공유그룹이라고표기한다.
원코드의CE/native KL을재사용하고autograd.grad로독립분기gradient를모아norm/dot/cosine을
계산한다. 동일128·CE772·KD538·BF16/ckpt/결정론을유지하고native chunk적격이선결이다.
생산계수를자동선택하지않고동일norm·0.1배norm의계산값만진단후보로보존한다. CE와다른
방향이라고정답/오답을판정하지않는다. 제품/원CP/타정제/원cache/Git/설치/추가300M변경0이다.

## 초기 투영 수리 선결 — 새 투영 행렬만100회 보정

실제교사top1은원지도target468/538과일치하지만초기투영은교사top1의70/538만재현했다.
A(선택)는원TRAIN의선언semantic_root SHA를mod5로분리해학습/보류근을정하고새투영만
100회보정한다. B는작은계수만사용하지만잘못된초기분포가남고, C는원본체까지곧바로
같이교육하지만어떤변화가효과를냈는지알수없다. A는원본체를동결하고cold projection을
분리하는가장작은진단이다. 이것은DSKDv2전체교과/원저자학습의완전재현이아니다.

CPU5→분리/봉인→actual576이다. head와원학생/교사본체는변경하지않고순전파0, 새Pt786432개만
AdamW lr1e-3/betas.9,.999/eps1e-8/WD0/clip1/seed1337·full-calibration-batch100update한다.
0/25/50/75/100에서mapped native top1과CE·원지도token일치를기록하나보류점수로종료점/LR을
고르지않는다. 선언된root만분리하며원문서전체누설0인증이아니다. 전체538은새corpus가아니고
반복노출되므로과적합가능성을명시한다. 원최종평가/공식bench정답/다른세션원문은사용0이다.

GPU예상1~2분/상한30분,학생모델은CPUhead읽기만하고GPU에는headfactor/작은Pt/표현만둔다.
저장된feature/원CP/core와source불변·CUDA0/0을닫는다. 새Pt는RAM에서만사용후버리고
최종SHA/조건만남긴다. 학생update0/새투영update100/CP저장0을구분한다. 작은투영맞춤은
모델지능/학습방법채택/본학습완료의근거가아니다. 전량교육과별도독립평가가후속이다.

## 보정 표본 확장의 기술 선결 — 기존 동결 TRAIN1024만 사용

작은402위치투영은학습100퍼센트지만보류CE19.23으로악화해생산에채택하지않았다.
A(선택)는이미완료된 `HF/sft_ready/p106b_alm_train_ternary_v1_s1337`의원형1024행만검산해
한영512씩의기존스냅샷에서표현을확장한다. B는128에서LR/랭크를여러번바꾸지만작은근의
반복선택위험이남고, C는새원천을수집하지만권리/정제/비용축이늘어난다. A는새데이터수집이나
corpus편입승인이아니다. 원128은root/source/record/정확teacherids/studentowner를전량대조한뒤
기존feature/원native위치를참조하여모델호출을중복하지않는다. net new는896행이하이다.

CPU6→1024원형/단일shift/exact/HOLD봉인→qualified Qwen B1×1024 FP32/MATH/TF32off 수집이다.
옛128회teacher는재실행0이며새한영각1prefix만추가검사한다. 긴teacher행은잘라넣지않고
원CE전체HOLD다. 새로운teacherargmax는완전한exactmode1/명시specialmode3만수락한다.
기존75M/학생학습/원CP/타정제/보호TinyDataset/최종평가정답/Git/설치변경0이다.
캐시는data_cache의새태그에작은npy로만추가하고원캐시는불변이다. 예상디스크1GiB내외·
GPU8~15분/상한30분·여유12288MiB, CPU10분상한이다. 모델해제/원형/SHA/독립실제종료와
CUDA0/0을닫는다. 큰feature수집도모델지능성과가아니며전체DSKD효과는본학습뒤별도평가다.

## 같은 투영 커널의 표본128→1024 대조

동일새Pt100step/LR1e-3/clip1·원head동결·원본체0의최적화함수를그대로재사용한다.
A(선택)는새4113위치에서동일선언root mod5와기존보류136을계속보류한다. B는원128에서
LR/정규화만변경하므로자료다양성부족이남고, C는바로원본체를교육하므로초기투영문제와
학생변화를가르기어렵다. 이대조는자료축만확장하나full-batch의한step노출위치도늘어난다.
총계수/노출을숨기지않고같은old136을보조대조로분리한다. dev는탐색용이며최종독립평가가아니다.

CPU3로기존함수code객체재사용·전역모듈불변·출력격리를검사하고새prepare에서원1024의
feature dtype/shape/finite/SHA·원source/exact/CE·teacher수락4113을전량검산한다. 실제최적화는
기존함수의private globals만새selector/출력으로연결하며원함수·공용모듈을변경하지않는다.
학생update0·투영update100·새CP0, 동일0/25/50/75/100보고와dev선택0을유지한다.
GPU예상1~3분/상한30분이고기존native값으로만실행한다. 작은보정의지능/방법채택은하지않는다.
