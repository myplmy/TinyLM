# 2026-10-24 공식 평가 누락 회수의 확장 preflight

현재 변경 권한/파일별 표는 NIGHT_SCOPE, 전체 본학습 자료 미충족은 FULL_TRAIN_AND_EVAL_READINESS가
소유한다. 이 문서는 새 native·통계·Falcon문법·LAMBADA의 설계 체크이며 실제 통과를 대신하지 않는다.

| 항목 | 판정 | 근거·한계 |
|---|---|---|
| A 계산 | 해당 없음/평가 분모 검산 | 학습0/optimizer0/CP0. Core6=19965문항/67106보기; 문법59875+5218쌍/67+5UID; LAMBADA5153행 |
| B 풀 | 평가 전용 | 같은고정공식원형을읽고train/teacher로연결하지않는다. 본학습풀2배 충족의주장이아님 |
| C 출력 | 독립 namespace·exclusive | nativeGGUFv1/pairs v1/Falcon window v1/LAMBADAdefault v1과sourceSHA를고정한다. 기존full/cost/partial덮기거부 |
| D 중복 | 누락 회수만 | 기존Tiny3/Falcon Core6와Tiny3문법은재실행하지않는다. 실패한HF writer 원형을보존했고새source cost 재입장만실행 |
| E 비교 | 원task/metric 유지 | 모델/tokenizer/사전학습/native Q4와HF FP32 차이를명시. 같은문항CI는doc/prompt/target/choices대응확인뒤만계산 |
| F 자원 | 직렬·유계 | GPU 한 작업, cost/수치canary 최대600초/full7200초, 과제별실측외삽과정리예비 및08:40 KST 입장마감 |
| G 판정 | 사전 고정 | 전체분모·raw재계수·입력/소스/가중치불변·예외/정리가닫혀야full. 비용표본/입장보류/실행오류는점수0아님 |

공식소스의함수·평가prompt를고치지않는다. 새runtime이필요한native는compiler/headers/lib/model과
shift/BPE/빈prefix/KVclear/미래token/fullCE 수치검사를별도수행한다. 기존GGUFLM의다른default를
조용히이식하지않고현재공식Core6의TemplateLM과plan_tokens 계약을재사용한다.

Falcon은원3600초와옛16:30마감만새제어기에서7200/08:40로분리하고 원계산·seed·동점RNG·
자료/UID순서는유지한다. source18개를고정한새prepare는0.753413초에완료했다. 새14CPU회귀도
통과했으나모델cost/full은아직미실행이다. 원cost의5013.3101초는새실행시간보장이아니다.

LAMBADAdefault 원격LFS와로컬en의SHA동일성을실제조회/재해시해고정했고alias영수증을보존한다.
행수만같은다른config를같은점수로취급하지않는다. 완성된각모델의전량평가는작은학생학습
성과판정이아니며 새로운TinyLM지능개선/일상대화정상화를주장하지않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 02:38 후속 두 독립 범위의 사전 점검

| 축 | Belebele Stage8o0W/8oW | GPT2 Stage8p0W/8pW |
|---|---|---|
| 목적·중복 | 공식900×2의누락회수; 기존실행을찾지못함 | 이미통과한v2 canary/cost재사용; full만미실행 |
| 이름 | p106b_belebele_v1_s1337 registry충돌0 | p106b_native_window_v1_s1337 registry충돌0 |
| 계산 | 1800문항/7200labelLL;900대응키/488지문 | 19965문항/67106보기; 기존전체공식계산 |
| 자료·코드 | 기존허가의공식원JSONL2개만취득; 기존공식YAML/함수불변 | 새다운로드0; 원v2source42713/worker/asset/원보고서SHA고정 |
| 정규화 | 실제delimiter붙인전체labelLL·문자acc_norm | 원acc/acc_norm/continuation경계와strict문턱불변 |
| 검산 | 7모델원_encode_pair+plan_tokens토큰열SHA와무절단교집합을점수전에고정 | 원canary/cost완결과후검사/새controller실패정리/전량raw재계수 |
| 실행 | root직렬;각모델canary/cost후시간입장 | root직렬;10800전체가08:40전에들어갈때만입장 |
| 해석 | 전량과공통무절단보조분모분리·clusterCI미구현 | 옛7200HOLD보존·시간창변경만으로수치통과를만들지않음 |

학습토큰·초기화·optimizer 비교는 학습0이라 해당없다. TinyLM의 작은 학습을 새로 추가하지
않으며 본학습 전 지능 채택 금지를 유지한다. 기존 칸의 v1 namespace와7200초는 당시
기록이며 새 두 단계는 이 추가 표가 별도 소유한다. 실제source동결/CPU시험/GPU종결은
후속 실제 영수증이 없으면 완료로 표시하지 않는다. 보호원천·타세션·Git·환경·원로그 변경0이다.
