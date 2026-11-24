# Bonsai2B와 기존 Prism 서버의 입장 계약

사용자158의2026-11-17 17시 승인으로 원장39의 정확 Bonsai2B 확인과45~47/68의 native 선결을 진행한다. CPU1 타이밍 중 실행은 하지 않는다. 이 문서는 실행 전 판단이며 모델 로딩·우도·벤치마크 성공을 뜻하지 않는다.

## 정확 대상과 세 대안

대상은 기존 `HF/benchmark_20261023/bonsai2_2b_ptq1/manifest.json`과 같은 폴더의 `Ternary-Bonsai-2-2B-PTQ1_0.gguf`다. 기존 반입 기록은 revision683f7be2629342a50987627b40881e54761a2430·429183456B·Apache-2.0이다. 실제 manifest·GGUF·런타임의 SHA와 형식은 CPU1 종료 후 대조한다. 기존 `diag_p106_bonsai_assets.py`의27B 자산을2B 확인에 사용하지 않는다.

| 안 | 이득 | 제약 | 판단 |
|---|---|---|---|
| A, 기존 matching C API | 원 logits에서 직접 전체어휘 logsumexp/선택 token 우도를 계산 | 정확 Prism ABI의 기존 header가 필요; stock b11396 구조체를 추측할 수 없음 | 현재 bundle의 알려진 header 위치는 없음. 새 header/라이브러리 취득은 이번에 하지 않음 |
| B, 기존 localhost 서버 | 기존 binary만으로 모델·tokenizer·원분포를 검사; 새 패키지/ABI 추측 없음 | 원분포/강제 token/상태 초기화/비용을 실제로 대조해야 함 | 첫 기술 카나리로 선택 |
| C, 자료/설치 승인 후 별도 환경 | 정식 native adapter를 새로 구성 가능 | 사용자 최종 확인 전 실행 불가 | 선결 미충족이면 보류 |

## 원 소스에서 확인한 것과 추론

기존 binary 폴더 이름은 `llama-prism-b10743-adfffbe`다. 원격 commit의 정식 ID는 `adfffbe41b2cabcd51fff326ab045662265062bb`로 확인했지만 폴더 이름만으로 실제 binary 일치를 선언하지 않는다. 기존 binary의 version과 SHA를 별도로 검사한다. 다음은 GitHub 연결의 읽기 전용 원문 조회이며 코드/패키지 checkout·설치가 아니다.

- [server-context.cpp](https://github.com/PrismML-Eng/llama.cpp/blob/adfffbe41b2cabcd51fff326ab045662265062bb/tools/server/server-context.cpp): pre-sampling 확률 요청은 backend sampling을 끄고 원 context logits에서 확률을 구한다. 요청 top 수와 별개로 반환 내부 배열 전체에서 실제 선택 token의 확률을 찾는다.
- [server-common.cpp](https://github.com/PrismML-Eng/llama.cpp/blob/adfffbe41b2cabcd51fff326ab045662265062bb/tools/server/server-common.cpp): 전체 원 logits에 FP32 softmax를 계산한 뒤 요청 top 수만 응답 목록에 쓴다. 이 경로의 분모는 top-k 재정규화가 아니다.
- [sampling.cpp](https://github.com/PrismML-Eng/llama.cpp/blob/adfffbe41b2cabcd51fff326ab045662265062bb/common/sampling.cpp): sampler는 context logits를 별도 후보 배열로 복사한다. bias와 다른 sampler는 그 배열에 적용된다.
- [server-task.cpp](https://github.com/PrismML-Eng/llama.cpp/blob/adfffbe41b2cabcd51fff326ab045662265062bb/tools/server/server-task.cpp): 주 선택 token과 top 목록의 logprob를 응답한다. 확률0은 매우 작은 유한 sentinel로 직렬화하므로 단순 finite 검사만으로 정상 우도라고 하면 안 된다.

이 구조에서 목표 token을 bias로 강제 선택하면서 `n_probs=1, post_sampling_probs=false`를 요청하면 응답의 주 token 우도는 원 전체어휘 분포에 남을 수 있다고 추론한다. **실제 binary와의 일치, bias 독립성, EOS/특수 token, hybrid 상태·prefix 재사용은 아직 확인하지 않았다.** 첫 카나리는 한 문맥의 전체어휘 응답과 사전 고정 rank0/7/중간 token의 강제 응답을 독립 대조한다. 비최빈 token 우도와 원 greedy를 분리한다.

## 변경 권한과 영향

| 축 | 범위와 조치 |
|---|---|
| 코드/caller | 새 `scripts/p106b_prism_http.py`와 시험/전용 카나리만 추가. 기존 공식 평가 adapter/제품 코드/CPU1 동결 소스 변경0 |
| 자료 | 위2B 자산과 소유 시험 문맥만 읽기. 보호 데이터·타정제·기존 CP/원로그 변경0 |
| 검사 | localhost 제한/redirect·proxy 금지/응답 cap/전체어휘 분모/중복 ID/zero sentinel/강제 token 일치와 원 raw 우도 대조 |
| 문서 | P106B 계획→새 원로그/JSON→결과101·원장39/45~47/68·두 목록/방법론/기준표/COMPASS |
| 부채 | HTTP 기술 카나리는 정식 전체 benchmark adapter를 대신하지 않음. 전체보기 우도·공식 토큰 경계·절단·시간 예산은 별도 |
| 실행/보호 | CPU1 종료 후 GPU 직렬. 소유 localhost process만 종료하고 다른 PID는 건드리지 않음. 새 다운로드/환경/전역설정/Git/삭제0 |
| 비교/지표 | 동일 binary·GGUF·prompt token·원 logits 분포. 모델 간 tokenizer/학습량/IT 차이를 방법 기여로 바꾸지 않음 |

## 사전 게이트와 비용

서버는127.0.0.1의 소유 빈 port에만 묶는다. 외부 network/자동 모델 취득을 사용하지 않는다. 정확 CLI flag는 기존 `--help`로 먼저 확인하고 지원하지 않는 flag를 추측해 실행하지 않는다. 원본 모델/런타임 SHA를 전후 대조하고 서버를 실제 회수한다.

전체어휘 확률은 한 문맥만 받아 응답 크기64MB를 상한으로 한다. 저장은20MB 미만 shard로 나눈다. 모든 V개 ID의 유일성/범위와 전체 확률 합을 검산하고, 강제 응답의 주 token logprob가 전체 응답의 같은 ID와 원 atol1e-5/rtol1e-4에서 같은지 대조한다. 원분포 확률 합의 FP32 허용오차는5e-4로 사전 고정한다. 선택 token의 underflow sentinel·불완전 응답·경계 불일치·상태 미복구는 HOLD다. sentinel을 정식 우도로 사용하지 않는다.

단일 phase 최대20분, 서버 startup5분·요청별60초·실패 회수 포함이며 정확 자원은 후속 frozen profile에 봉인한다. 카나리를 통과해도 전체 평가 비용을 먼저 측정한다. 현재 설치된 공식 harness/정확 자료만 사용하며 본학습·모델 품질 향상은 판정하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 현재 입장과 고정한 첫 서버 검사

2026-11-17 11:19KST의 `Stage8pr0Wa_bonsai2b_asset_runtime`은 실제 종료0이다. 기존2B 파일429183456B/SHA36061AD4…9929FA와GGUF3을현재확인했고기존server/cli는각각commit adfffbe를보고했다. 기존8 binary/library SHA를봉인했으며model load0이다. 정확근거는 `test_result/evidence/p106b_bonsai2b_prism_assets_v1_20261117/report.json`이다.

첫 서버 진단은 새 `diag_p106b_bonsai2b_prism_canary.py`만 caller로 사용한다. 기존10 프로토콜 CPU계약의동일source SHA를재사용하고새5계약은native vocabulary/원문맥전량처리·pre-sampling/소유process group종료를검사한다. 기존header parser `p106b_mtp_teacher.gguf_metadata`로2B의native embedding/output 어휘를읽되그모듈의27B모델·LoRA는읽거나실행하지않는다.

정확기존CLI help에서확인한offline/model/127.0.0.1:19861/parallel1/context1024/GPU all·fit off/flash-attn off/cache-ram0/cache-reuse0/no-cache-prompt/no-context-shift/no-warmup/no-mmproj만명시한다. `LLAMA_ARG_`와`GGML_`의상속설정은소유child환경에서제거한다. CUDA disk cache는비활성화하고외부다운로드·MTP·LoRA는사용하지않는다.

문맥A는 `The capital of France is`, B는 `한국의 수도는`이다. raw tokenization의무손실복원과native add-special token IDs를기록한다. 같은A의전체V원확률응답뒤 **순위0/7/V정수중간** token을사전에고정한규칙으로강제선택하고동일원확률을비교한다. target이underflow/sentinel이면임의다른순위로교체하지않고HOLD다. B를끼운뒤A의순위7을다시강제해원문맥/길이/처리token전량과원우도불변을확인한다. 이6요청은전문항·긴continuation·EOS/부분byte경계검증을대신하지않는다.

전체V응답은64MB수신cap과20MB미만JSONL shard로보존하고메타응답을별도기록한다. phase18분·종료회수포함20분/startup5분/request60초/총180MB·server log10MB를상한으로한다. free8GiB점조회와소유PID/new-session process group을기록하며그group만회수한다. source/model/runtime의전후SHA·종료후NVML점조회를닫아야한다. 동결전CPU5/기계preflight를통과한뒤에만첫실제모델을입장시킨다.
