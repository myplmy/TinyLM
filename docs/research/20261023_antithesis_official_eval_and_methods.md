# 2026-10-23 반 검토 — 공식 평가의 최소 경로와 방법 효과의 귀속

상태: `SOURCE_AUDITED / OFFICIAL_MODEL_EVALUATION_NOT_RUN`. 작성자는 총괄이 지정한 반 담당이다. 최초 §1~9는 로컬 소스·공식 웹·설치 메타데이터를 읽고 이 연구문서를 신설한 감사다. 뒤이은 추가 승인에 따른 문헌 교차검토·자산 반입은 §10~11에 따로 기록한다. 모델·tokenizer 로딩, torch import, 학습, GPU, 설치, Git, 삭제, 보호 `datasets/TinyDataset/**` 접근은 하지 않았다. 최초 외부 웹의 `main`은 열람 당시 snapshot이며 실행용 코드 commit 고정과 실제 평가 parity를 뜻하지 않는다.

## 1. 현재 결론과 권한 범위

공식 BabyLM 2026과 공통 Core6를 시작할 수는 있으나, 기존 MC768을 다시 집계하거나 더 많은 문항에 같은 scorer를 적용하는 것으로 공식 평가를 완료할 수는 없다. 현재 학습 환경에는 공식 harness와 여러 필수 의존성이 없다. 우선 평가 전용 자료·공식 입력 계약·adapter를 준비하고, 실제 설치는 별도 승인 범위로 분리하는 것이 타당하다.

| 파일·경로 | 예정/실제 동작 | 근거 | 제외 |
|---|---|---|---|
| 이 연구문서 | 신설·동일 문서 보완 | 총괄이 지정한 반 산출물 경로 | 계획서/결과 정본 대체 아님 |
| `scripts/eval_bench_suite.py`, `scripts/p106b_public_mc_extension.py`, 공개 평가 캐시 | 읽기·행수/계약 확인 | 공식 평가 재사용 감사 | 원본·평가 코드 수정 없음 |
| 공식 저장소·논문 | 웹 열람 | 공식 방법과 문헌 주장 검증 | 로컬 설치/코드 실행 없음 |
| 학습 환경 | 표준 라이브러리 `importlib.metadata`로 버전 조회 | 설치 필요성 확인 | torch·모델 모듈 import 없음 |

영향도: 제품 코드·데이터·체크포인트·기존 점수·정본 수치는 바꾸지 않는다. 새 연구문서의 제안은 구현/설치/학습 완료가 아니다. 모델 쌍의 입력·문항·토큰화·정밀도·평가 경로가 다르면 비교 결론이 달라진다는 과학적 영향이 있다. 실제 결과가 없으므로 COMPASS·기준표·실험 결과 목록의 상태 변경은 하지 않았다.

### 가능한 세 경로

| 안 | 내용 | 장점 | 단점 | 영향·비용 |
|---|---|---|---|---|
| A — 지금 준비 | 공식 소스/문항 revision·입력 계약·평가 전용 저장 위치를 정하고 TinyLM adapter 차이를 명세 | 학습 환경과 과거 결과를 보존하며 공식 평가의 정확한 선결을 닫음 | 공식 모델 점수는 아직 없음 | 문서·새 평가 namespace, 낮음~중간 |
| B — 승인 후 공식 실행 | 격리 평가 환경에 고정 harness/BabyLM 의존성을 설치하고 adapter parity 확인 후 full 평가 | 가장 직접적인 공식 파이프라인 증거 | 설치 승인·환경 호환·TinyLM adapter 작업과 실제 모델 시간이 필요 | 환경·평가 코드, 중간~높음 |
| C — 무설치 재현 | 기존 런타임과 공개 캐시로 공식 prompt/metric을 독립 재현 | 새 설치 없이 가능한 부분부터 측정 가능 | 공식 구현과의 동작 동등성이 확인되기 전 `LOCAL_REPRODUCTION`; 공식 pipeline 완료라고 부를 수 없음 | 별도 평가 코드/정합 감사, 중간 |

권장: A를 먼저 마치고 설치 권한이 닫히면 B로 진행한다. C는 설치가 막힌 동안의 명시적 대안이다. 모델/문항 다운로드 승인과 패키지 설치 승인은 같은 것이 아니다. 공식 평가를 쓴다는 이유로 학습 환경의 라이브러리를 일괄 교체할 필요도 없다.

## 2. 실제 로컬 자산과 비어 있는 부분

2026-10-23 조회한 실제 환경은 `/home/uranus/miniforge3/envs/tlm_torch/bin/python`, Python 3.10.19다. 설치 메타데이터 기준 torch 2.10.0+cu130, transformers 5.14.1, datasets 5.0.0, huggingface_hub 1.24.0, numpy 2.2.6, pandas 2.3.3, wandb 0.28.2가 있다. 이는 모델 로딩 성공 증거가 아니다.

`lm_eval`, `evaluate`, `scikit-learn`, `scipy`, `statsmodels`, `nltk`, `langdetect`, `immutabledict`, `pytablewriter`, `rouge-score`, `sacrebleu`, `sqlitedict`, `word2number`, `more_itertools`, `accelerate`, `peft`는 해당 환경의 설치 메타데이터에서 찾지 못했다. 시스템 `/usr/bin/python3` 3.12.3도 별도로 확인했으며 학습 환경과 혼용하지 않는다.

현재 harness의 소스 버전 표시는 `0.4.14.dev0`, Python 하한은 3.10이다. base·HF backend·IFEval extra의 의존성이 구분된다. 따라서 Python 버전만으로 실행 가능을 판정하지 않는다. [공식 pyproject](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/pyproject.toml)

| 평가 자산 | 실제 로컬 확인 | 추가 준비 |
|---|---|---|
| Core6 | `datasets/bench/`의 piqa 1,838 / hellaswag 10,042 / arc_easy 2,376 / arc_challenge 1,172 / winogrande 1,267 / boolq 3,270 LF행, 합 19,965 | 현 공식 dataset revision과 행/필드/ID 대응 확인. 파일 존재·행수만으로 동일 revision을 증명하지 않음 |
| KoBEST | `kobest_copa.jsonl` 1,000 / `kobest_hellaswag.jsonl` 500 LF행 | boolq·wic·sentineg 추가 필요. COPA/HellaSwag도 공식 prompt와 다름 |
| IFEval | `ifeval.jsonl` 541 LF행 | 공식 25종 checker와 dependencies/NLTK 자원 필요. 로컬 자체 8종 검사로 대체 불가 |
| Belebele | 이번 `datasets/bench/` 파일 목록에서 없음 | `facebook/belebele`의 `kor_Hang`, `eng_Latn`, test 각 900의 고정 revision·대응키 |
| BabyLM 2026 strict | 이번 공개 캐시와 지명된 평가 코드에서 공식 설치·평가 자료 경로를 확인하지 못함 | 공식 코드 snapshot + `BabyLM-community/BabyLM-2026-Strict-Evals` + 필요 과제별 추가 자료. 시스템 전체에 없다는 전수 부재 주장은 아님 |
| 외부 GGUF 엔진 | `/home/uranus/llama-b11396/llama-server` 및 지명된 Prism 디렉터리의 `llama-server` 파일 존재 | 각 엔진의 지원 포맷·확률 API·실행 commit·실제 동작 확인. 파일 존재는 backend 성공이 아님 |

로컬 `scripts/fetch_bench_data.py:125`는 과거 예상 점수를 이유로 KoBEST BoolQ/WiC/SentiNeg를 제외했다. 이번 사용자 요청은 5과제이므로 그 과거 선택을 현재 전수 평가의 제한으로 승계하지 않는다. 이 문서는 downloader를 수정하지 않았다.

## 3. Core6와 한국어 평가의 현재 공식 계약

아래 문항 수는 사용자가 정한 full 평가 대상이며 로컬 Core6 LF행과 일치했다. 실제 실행에서는 dataset revision과 순서를 함께 동결해야 한다.

| 과제 | 공식 데이터·평가 split | 이번 주지표·특수 처리 |
|---|---|---|
| PIQA | `baber/piqa`, validation | 사용자 결정 `acc`; `acc_norm` 보조. 현재 공식 경로는 로컬 downloader의 `ybisk/piqa`와 이름이 다름. [YAML](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/piqa/piqa.yaml) |
| HellaSwag | `Rowan/hellaswag`, validation | `acc_norm`. 공식 전처리는 `[title]` 치환, 대괄호 내용 제거, 중복 공백 수리까지 포함. [YAML](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/hellaswag/hellaswag.yaml), [전처리](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/hellaswag/utils.py) |
| ARC-Easy/Challenge | `allenai/ai2_arc`, 각 test | `acc_norm`. 보기 text 전체가 continuation이며 보기 수를 무조건 4로 고치지 않음. [Easy](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/arc/arc_easy.yaml), [Challenge](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/arc/arc_challenge.yaml) |
| WinoGrande | `allenai/winogrande`, `winogrande_xl` validation | `acc`. 후보를 빈칸에 넣은 후보별 prefix에 대해 공통 suffix를 채점. 일반 MC처럼 후보 단어 자체만 점수화하지 않음. [YAML](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/winogrande/default.yaml), [전처리](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/winogrande/preprocess_winogrande.py) |
| BoolQ | `aps/super_glue`, boolq validation | `acc`; `no/yes` 우도. 로컬 캐시는 `google/boolq`의 `answer` 필드이므로 직접 교체하면 `label` 대응이 필요. [YAML](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/super_glue/boolq/default.yaml) |

Core6 동일 가중치 평균은 위에서 선택한 각 과제 주지표의 산술평균이다. 모든 행의 `acc`만 평균하거나 문항 수로 가중하면 다른 통계가 된다. BoolQ의 균등 무작위 50%와 라벨 최빈 기준은 서로 다르다. ARC는 문항별 `1/선택지수`를 사용하고, 비교 표본이 달라지면 무작위 기준도 다시 산출한다. 기존 로컬 `TASKS['boolq']`의 0.62를 균등 무작위 확률로 복사하지 않는다.

### Belebele

현 harness는 지문·질문·네 보기 본문을 prompt에 모두 쓰고, continuation은 `A/B/C/D`다. 따라서 “모든 선택지를 채점”은 이 YAML에 정의된 네 라벨 문자열 각각의 전체 조건부 우도를 구한다는 뜻이다. 자유 생성한 글자를 채점하거나, 정답 라벨만의 top-logprob를 읽거나, 임의로 보기본문 continuation으로 바꾸는 방식은 현 공식 harness 계약과 다르다. 문자 라벨이 여러 token으로 나뉘면 그 전부를 합산한다. [공식 template](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/belebele/_default_template_yaml), [한국어 config](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/belebele/belebele_kor_Hang.yaml)

원 데이터의 language/config·test split·900문항과 라이선스는 공식 dataset에서 확인한다. 한국어/영어 대응은 독립 1,800문항이라고만 세지 말고 `link`, `question_number` 등 실제 대응키와 같은 지문 묶음을 보존한다. 이 문서에서는 문항 본문을 train 교사에게 전달하지 않았다. [공식 데이터](https://huggingface.co/datasets/facebook/belebele)

### KoBEST

공식 harness의 5개 task는 `kobest_boolq`, `kobest_copa`, `kobest_hellaswag`, `kobest_sentineg`, `kobest_wic`다. README의 `kobest_hallawag` 표기는 실제 YAML 식별자와 다르므로 실행 task 이름으로 복사하지 않는다. 모든 과제에서 accuracy와 macro-F1을 과제별로 보고한다. `kobest` group의 `weight_by_size: true` 집계는 사용자 요청의 과제별 macro-F1과 구분한다. [그룹](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/kobest/_kobest.yaml), [공식 원천](https://huggingface.co/datasets/skt/kobest_v1)

현재 로컬 COPA는 “그 원인/결과(으)로 알맞은 것은?”을 붙이나 공식 utils는 원인/결과에 따라 “왜냐하면/그래서”를 쓴다. HellaSwag도 공식은 `문장:` prefix를 쓴다. 같은 원천·같은 합우도라도 prompt가 다르므로 과거 점수를 현 공식 점수로 개명할 수 없다. [공식 utils](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/kobest/utils.py), [COPA](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/kobest/kobest_copa.yaml), [HellaSwag](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/kobest/kobest_hellaswag.yaml)

### IFEval

현재 공식 harness는 `google/IFEval`의 이름이 `train`인 541문항을 평가로 쓰며, greedy·0-shot·`max_gen_toks=1280`이다. prompt-level strict와 instruction-level strict를 주/보조로 보존하고 loose는 따로 보고한다. 공식 max generation보다 작은 **총 문맥 1,024**를 모든 모델에 강제하면 같은 공식 full 설정이라고 부를 수 없다. 공식 설정 트랙과 사용자 공통 cap 트랙을 별도 표시하고, 후자는 입력/출력 cap·제외 수·완주 여부를 공개한다. [공식 YAML](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/ifeval/ifeval.yaml)

공식 checker는 `nltk>=3.9.1`, `langdetect`, `immutabledict`가 필요하다. `instructions_util.py`는 import 때 `punkt_tab` 존재를 확인하고 없으면 다운로드를 시도한다. 단순 import 점검도 다운로드 없는 읽기 검증으로 취급해서는 안 된다. 기존 8종 검사는 부분 평가이며 미구현을 실패 또는 전체 IFEval 점수에 섞지 않는다. [필수 자원 처리](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/ifeval/instructions_util.py), [공식 checker](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/tasks/ifeval/utils.py)

## 4. SUM_NLL이라는 이름이 같아도 공식 parity가 아닌 이유

현재 `scripts/eval_bench_suite.py:427`의 `seq_ce`와 `:566`의 `run_mc`를 읽었다. `p106b_public_mc_extension.py:186`의 준비·`:218`의 검산은 해당 로컬 literal 계약을 잘 고정하지만 공식 harness와의 동등성을 검증하는 코드는 아니다.

| 항목 | 현재 로컬 | 공식 계약 또는 필요한 확인 | 결론 |
|---|---|---|---|
| 채점 합 | `pred_harness`는 SUM_NLL argmin, PMI 없음 | harness `acc`는 조건부 logprob 합 argmax | 수학적 방향만 대응 |
| `acc_norm` 분모 | continuation에 미리 붙인 공백까지 `len(c)`에 포함 | `doc_to_choice` 원문 길이. harness가 붙이는 target delimiter는 분모 밖 | +1 차이가 있어 순위 동등성을 보장하지 않음 |
| 토큰화 | prompt와 continuation을 각각 encode한 뒤 연결 | causal TemplateLM은 prompt+continuation 전체 encode에서 continuation을 나눔; prompt 끝 공백도 이동 | BPE/SentencePiece 경계 차이 가능 |
| 빈 prompt | newline의 첫 token을 prefix로 사용 | 공식 TemplateLM의 BOS/EOS/custom prefix 처리 | 문장 최소쌍 우도를 그대로 옮길 수 없음 |
| BOS/EOS | scorer가 임의 추가하지 않음; 실제 tokenizer 동작은 별도 | HF의 `add_bos_token=None`은 tokenizer 규약에 위임. 모델별 필수 special token 확인 | 전 모델 BOS 일괄 off도 무조건 정합이 아님 |
| 긴 입력 | 1,024 초과 item을 건너뜀 | 공식 backend별 길이 처리 확인. 전수/공통 subset을 구분 | 모델별 서로 다른 제외분모 금지 |
| HellaSwag | strip 중심 | 공식 bracket/title 정제 | input bytes 불일치 |
| KoBEST | 로컬 prompt | 공식 한국어 prompt | input bytes 불일치 |

위 공식 채점·구분자·토큰화 근거는 [task.py](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/api/task.py), [TemplateLM](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/api/model.py), [HF backend](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/models/huggingface.py)다. 특히 `acc_norm`은 token 수·UTF-8 byte 수와 다르다. 한국어에서 Python 문자열 길이와 byte 길이를 혼용하지 않는다.

기존 MC768의 raw SUM_NLL, 평균 NLL, 문자 정규화·ID·source hash는 당시 로컬 계약의 결과로 보존한다. 새 공식 prompt/토큰화로 다시 평가한 결과와 절대 점수를 직접 이어 붙이거나 “기존 대비 향상”으로 차감하지 않는다. 과거 같은 checkpoint의 다른 표본 점수 차이 역시 학습 효과가 아니다. 과거 근거는 [2026-10-22 재사용 감사](20261022_public_benchmark_reuse_audit.md)를 따른다.

## 5. TinyLM·HF·GGUF adapter가 충족해야 할 것

TinyLM에는 공식 `LM`/`TemplateLM` 계약을 받는 전용 adapter 또는 HF 호환 wrapper가 필요하다. 순전파를 호출할 수 있다는 것만으로 충분하지 않다. 모델 선택은 기존 strict loader의 정확 checkpoint·실제 ternary route·tokenizer 계보를 유지해야 하며 float fallback으로 점수만 얻어서는 고정 삼진 배포본의 결과가 아니다.

최소 계약은 `(context, continuation)`별 전체 조건부 logprob와 greedy 여부를 입력 순서대로 반환하는 `loglikelihood`, 독립 요청별 상태 초기화, 실제 모델 길이·tokenizer·BOS/EOS 처리다. 생성 과제에는 별도로 `generate_until`이 필요하고 문서 perplexity에는 `loglikelihood_rolling`이 필요하다. 미구현 method는 명시 실패해야 한다. [공식 LM API](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/api/model.py)

정합 확인에는 정답을 공개할 필요 없는 합성 한영 입력으로 prefix 끝 공백, 한 글자/여러 token 보기, 빈 prefix, special token 중복, 동일 prefix의 서로 다른 보기, 긴 문맥을 넣는다. 실제 tokenizer ID·continuation 시작 offset·원 logprob 합·정규화 분모를 읽어, 기존 루틴과 공식 루틴 중 무엇을 사용했는지 확인해야 한다. 이 문서는 canary를 실행하지 않았다.

공식 API guide는 MC/loglikelihood에 completion endpoint를 요구하고 chat-completions만의 생성 응답은 지원하지 않는다고 구분한다. 교사가 생성한 문장의 top-logprobs만으로 임의 정답 continuation의 전체 우도를 복원할 수는 없다. [API guide](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/docs/API_guide.md)

다만 현 harness에는 `gguf` backend가 실제로 있다. llama-server의 `/tokenize`, `/props`, `/v1/completions`를 이용하며, 각 target token을 강제 선택해 pre-sampling logprob를 읽는 구현이다. continuation 길이에 비례해 요청이 늘어나므로 짧은 출력 생성의 tok/s를 전수 MC 시간으로 복사하지 않는다. 해당 소스는 `loglikelihood_rolling`을 지원하지 않는다. [현재 GGUF backend](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/models/gguf.py)

이 backend의 주석이 “unbiased”라고 한 것은 현재 두 로컬 엔진의 확률 정합 실행 증거가 아니다. 먼저 실제 엔진에서 강제 token과 자연 다음-token 분포의 logprob가 같고, sampler bias/temperature가 채점 확률에 섞이지 않는지 확인해야 한다. `/tokenize`의 special token 규약, 모델별 max context, state/slot 초기화도 확인한다. upstream의 pre-sampling 경로 존재는 확인했지만 로컬 바이너리의 같은 구현을 실행 검증하지 않았다. [upstream server](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/server-context.cpp)

## 6. BabyLM 2026 공식 평가를 시작하는 정확한 범위

2026 공식 정본은 `babylm-org/babylm-eval`이며 2025 evaluation-pipeline을 현재 pipeline으로 고정하지 않는다. Strict/Strict-small은 전용 `evaluation_pipeline`, multilingual zero-shot은 harness와 추가 task를 사용한다. multilingual의 주 언어는 영어·네덜란드어·중국어이며 한국어 점수를 제공하는 공통 한국어 벤치를 대신하지 않는다. [공식 저장소](https://github.com/babylm-org/babylm-eval), [multilingual 설명](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/multilingual/README.md)

Strict에서는 BLiMP·supplement·EWoK·Entity Tracking·COMPS의 zero-shot, reading/AoA, (Super)GLUE fine-tuning이 분리된다. fast는 중간 checkpoint용 축소 평가이며 최종 모델 full과 같지 않다. fine-tuning 점수는 task 파생 모델의 점수로 따로 보고한다. 새 자료 다운로드 승인으로 fine-tuning까지 실행됐다고 해석하지 않는다. [Strict README](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/README.md)

### 자료·설치·실행 준비의 분리

| 단계 | 정확한 소유 자산/입구 | 주의할 점 |
|---|---|---|
| 코드 snapshot | 공식 repo `strict/` | 웹 열람만 했으며 실행용 checkout 경로/commit은 아직 없음 |
| 주요 평가 자료 | `BabyLM-community/BabyLM-2026-Strict-Evals`; `python -m scripts.download_evals` | 공식 downloader는 snapshot 전체를 현재 디렉터리 `.`에 받음. 기존 프로젝트 루트에 무심코 실행하지 말고 평가 전용 경로를 먼저 확정. [download source](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/scripts/download_evals.py) |
| EWoK | `ewok-core/ewok-core-1.0` 약관과 `evaluation_pipeline.ewok.dl_and_filter` | 사용자 계정 약관 수락/접근 권한 확인. 실패를 모델 0점으로 기록하지 않음 |
| GlobalPIQA | `mrlbenchmarks/global-piqa-parallel` 및 `global-piqa-nonparallel`, `eng_latn`, test | 전용 downloader/scorer 사용. [download source](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/evaluation_pipeline/global_piqa/dl.py) |
| 의존성 | strict requirements와 실제 import 요구 | Python 3.13 환경에서 작성된 과거 pinned snapshot: torch 2.7.0/transformers 4.51.3/datasets 3.6.0 등은 현재 학습 환경과 다름. 그대로 일괄 설치하는 방식은 호환 보장이 아님. [requirements](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/requirements.txt) |
| TinyLM 입력/출력 | `sentence_zero_shot/dataset.py`, `compute_results.py`, `run.py` | `AutoProcessor`/offset mapping/attention mask와 dict·tuple logits 계약. 현재 TinyLM을 자동 HF 모델로 간주하지 않음. [dataset](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/evaluation_pipeline/sentence_zero_shot/dataset.py), [entry](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/evaluation_pipeline/sentence_zero_shot/run.py) |

시작할 최소 유닛은 한 checkpoint의 causal BLiMP full 평가다. 이는 BabyLM 전체 완료가 아니며, 자료→tokenizer/phrase mask→checkpoint/route→점수/원답을 연결하는 첫 공식 과제다. 코드의 default batch 64를 작은 모델이라는 이유만으로 무조건 안전하다고 가정하지 않는다. 모델 실행 시간은 실제 첫 비용 측정 전 `UNMEASURED`다.

`scripts/eval_zero_shot.sh`에는 BLiMP/supplement/EWoK/entity/COMPS/reading이 있으나 GlobalPIQA는 들어 있지 않다. 전용 GlobalPIQA shell은 main 뒤 다수의 `chck_*M` revision을 자동 순회한다. 현재 TinyLM에 그 revision이 없으면 이를 그대로 실행해 동일 모델 로딩 실패를 반복하지 말고 **main 한 번의 모듈 호출**부터 준비해야 한다. [zero-shot shell](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/scripts/eval_zero_shot.sh), [GlobalPIQA shell](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/scripts/eval_zero_shot_global_piqa.sh)

BabyLM strict의 GlobalPIQA 정규화는 **completion token 수**이며 다른 sentence task는 지정 phrase의 logprob 합을 쓴다. 이름이 `acc_norm`이라고 해서 harness의 문자 정규화를 대입하지 않는다. BLiMP는 문장 전체를 대상으로 하고 EWoK는 지정 suffix/문맥 쌍을 대상으로 하므로 기존 MC continuation scorer 하나로 덮지 않는다. [BabyLM 채점 source](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/evaluation_pipeline/sentence_zero_shot/compute_results.py), [task 해독 source](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/strict/evaluation_pipeline/sentence_zero_shot/read_files.py)

공식 multilingual에는 baseline tokenizer의 자동 EOS 때문에 continuation 경계가 틀어지는 문제를 고치는 `hf-bos` 경로가 별도로 있다. 이를 TinyLM에 무조건 적용하지 말고 실제 학습 BOS 규약을 확인한다. 공식 구현도 모델/tokenizer 조합에 따라 검증이 필요하다는 직접 사례다. [BOS fix 설명](https://raw.githubusercontent.com/babylm-org/babylm-eval/main/multilingual/README.md#bos-tokenization-fix)

### 평가와 대회 적격성

평가 수행은 공식 대회 적격성/순위가 아니다. Guidelines의 strict 100M·strict-small 10M은 학습 자료 budget, CFP의 1B·100M은 반복 노출을 포함한 training-duration 상한이다. word와 tokenizer token을 섞지 않는다. 승인 외부 teacher 목록과, 분포/hidden/weights를 이용한 KD가 교사 사전학습 자료량 산입을 유발하는 규칙도 별도다. 이 규정 때문에 사용자가 승인한 TinyLM 대형 교사 개발을 막지 않되 공식 출품 적격이라고 주장하지 않는다. [Guidelines](https://babylm.github.io/guidelines.html), [CFP v2 §4.1~4.2](https://arxiv.org/html/2602.20092v2), [FAQ](https://babylm.github.io/faqs.html)

## 7. 문헌 후보에 대한 반 검토

아래는 문헌·소스의 주장 범위와 우리 실험에서 혼동하면 안 되는 요인을 정리한 것이다. 새 실험의 실제 수행/채택 판정이 아니다. 남은 시간의 우선순위는 기존 미완 복구 → 같은 chat32 가속 → 같은 chat32 증류 → 기존 recurrent의 필요한 변경이라는 사용자 순서를 따른다.

| 후보 | 인정할 수 있는 기여 | 과장/교락 위험 | 비교 전에 고정할 것 |
|---|---|---|---|
| CCE | vocabulary 차원의 log-sum-exp를 타일로 계산하여 전체 logits 저장을 줄임 | 현 위치 chunk/checkpoint까지 새 기여로 세거나 논문 GPU의 메모리 배수를 TinyLM에 복사 | 같은 유효 target·tied gradient·loss reduction·dtype·whole wall/peak |
| Liger fused CE | chunk logits buffer의 CE/gradient 융합·재사용 | CCE와 동일하게 vocabulary logits를 전혀 만들지 않는다고 표현 | 실제 `[chunk,V]` logits와 backward 방식, 기존 chunk 대비 추가 이득 |
| progressive context | 짧은 문맥 구간의 처리 효율과 노출 순서 변경 | step 시간만 비교하고 총 token·원문 bytes·문서 경계·최종 긴 문맥 품질을 제외 | update뿐 아니라 유효 NTP target·input bytes/tokens·최종 동일 문맥 |
| NorMuon/AdaMuon | 기존 Muon과 다른 정규화/second moment 후보 | 기존 RMS multiplier를 이름만 바꾸거나 논문 버전과 main 코드 혼합 | 정확 버전·parameter groups·optimizer state·전체 step·time-to-quality |
| causal+MNTP/adaptive mask | 목표와 visibility가 다른 데이터 효율 후보 | 순수 커널 가속이라 하거나 양방향 학생/causal 교사를 같은 증거 조건으로 처리 | causal 생성·우도 평가; 마스크율·문맥·optimizer 동시변경 분리 |
| ALM | 같은 byte 구간의 teacher/student likelihood matching | 임의 logprob MSE를 ALM으로 개명; all-logits/hidden이 무조건 필요하다고 단정 | teacher-forced 실제 token logprob·shift·byte 경계·special tokens·공식 목적식 |
| ACTD | teacher top-k anchor와 학생 non-anchor 질량 억제 | teacher tail을 보존하는 full-vocab KL이라고 표현 | anchor mapping collision·top-k 정규화·student residual·target 수 |
| GSQ 유래 QAT/KD | 이산 선택 logits를 end-to-end 손실에 적용할 연구 가능성 | 원 PTQ 재현이라고 부르거나 code logits/optimizer 메모리를 배포 삼진 크기에 묻음 | hard 삼진 forward와 같은 CE/KD의 STE 대조·학습/배포 회계 분리 |
| looped/MTP/router | 반복 계산·보조 목표·조건별 계산 배분의 독립 후보 | 고유 parameter 절감=총 compute/latency 절감, MTP=진실 검증으로 해석 | 같은 고유/적용 parameter·노출·학습/추론 compute·정확한 iteration KV |

### 가속의 실제 신규 부분

로컬 `tinylm/train/mtp_sft.py:117`은 이미 ignore target을 head 전에 제외하고 위치별 chunk와 checkpoint를 쓴다. CCE/Liger의 효과는 이 경로 위에서 얼마나 더 줄이는지를 재야 한다. CCE와 달리 현 Liger source는 `[chunk,V]` logits를 matmul로 만들고 CE/gradient용 buffer를 재사용한다. [CCE 공식 설명](https://raw.githubusercontent.com/apple-aiml-research/ml-cross-entropy/main/README.md), [Liger source](https://raw.githubusercontent.com/linkedin/Liger-Kernel/main/src/liger_kernel/ops/fused_linear_cross_entropy.py)

factorized tied head에서는 output gradient뿐 아니라 input embedding과 공유 projection의 gradient까지 보존해야 한다. fused scalar CE만 얻으면 ALM의 per-target logprob나 ACTD의 anchor 확률을 잃을 수 있다. CE만 잘 돌아간 결과를 KD까지 fused했다고 부르지 않는다. stack 전체 speedup과 한 방법의 독립 speedup은 별개이며 다른 논문의 배수를 곱하지 않는다.

NorMuon 공식 main 소스에는 Newton–Schulz 뒤 second moment와 정규화가 별도로 들어 있다. 기존 TinyLM RMS 스케일과 동일하다는 증거가 아니다. optimizer 시간·state가 늘면 step 일부 개선도 전체 개선과 달라질 수 있다. 문헌담당의 v1/main 차이 지적을 수용하며 구현에는 선택한 버전을 명시해야 한다. [NorMuon 공식 source](https://raw.githubusercontent.com/zichongli5/NorMuon/main/normuon.py)

### ALM: 가능 조건과 수학적 주장 구분

ALM v4 §3와 Appendix I를 직접 열람했다. 기본 likelihood 목적에는 동일 텍스트를 teacher forcing한 실제 next-token logprob를 chunk마다 합한 값이 필요하며, optional hidden-state/debias 항과 구분된다. 따라서 GGUF가 **실제 reference token**의 올바른 logprob를 제공하면 기본 ALM 신호의 후보가 된다. 반대로 generated token의 top-k에 reference가 없는데 임의 값을 채우거나 문자열 확률 MSE만 계산하면 원 방법이 아니다. 정규화·BOS·한영 byte 경계 실패를 먼저 점검한다. [ALM v4 §3/App I](https://arxiv.org/html/2503.20083v4)

해당 v4 본문은 binarized divergence를 upper bound라 쓰지만 Appendix E는 Jensen/data-processing으로 lower bound를 증명한다. 둘을 함께 읽었으므로 원문의 내부 불일치를 숨기지 않는다. 여기서는 bound 방향을 근거로 구현/성능을 보증하지 않으며, 정합된 전체분포를 사건 묶음으로 축약하면 divergence가 커지지 않는다는 방향과 구별한다. 유한 학습 span의 loss 감소는 교사 지능 전체 이식 비율이 아니다.

공식 tokenkit은 JAX 중심이며 별도 harness fork 의존성이 있다. 이 전체 stack 설치가 TinyLM 최소 ALM 구현의 필수조건은 아니다. 구현 참고와 실제 라이브러리 도입을 나눈다. [tokenkit README](https://raw.githubusercontent.com/bminixhofer/tokenkit/main/README.md)

### ACTD: residual의 의미와 코드 가용성

v1 §3.2를 직접 확인했다. teacher는 top-k만 남겨 재정규화하며 long tail의 개별 값은 버린다. 학생의 anchor 밖 질량은 0으로 향하게 억제한다. 이는 teacher의 실제 tail mass를 별도 bin으로 보존하는 KL과 다르다. first-subtoken many-to-one mapping의 중복 anchor를 어떻게 취급했는지도 구현에서 밝혀야 한다. entropy가 낮아졌다는 이유만으로 정답성·한국어 능력이 좋아졌다고 판정하지 않는다. [ACTD v1 §3](https://arxiv.org/html/2608.29662v1)

현재 공식 저장소는 README와 “code soon” 안내만 확인됐다. 따라서 향후 만들 최소 구현은 논문 기반 신규 구현이며 공개 reference code의 재현 완료가 아니다. 문헌의 Avg@8과 이번 greedy 첫답/usable rate를 같은 지표로 바꾸지 않는다. [ACTD 공식 저장소](https://github.com/hyhy892/ACTD)

### GSQ: 시작 조건과 원 논문 범위

GSQ v1 §3.5는 원래 PTQ이며, layer/block 재구성과 task-aware 목적을 원리상 구분한다. 보조 code logits의 메모리 때문에 큰 모델에서 전체 공동 최적화가 비싸다고 설명한다. 외부 teacher CE/KD와 함께 TinyLM을 end-to-end 고정 삼진 학습하는 안은 **GSQ의 이산 최적화를 차용한 새 설계**로 명시해야 한다. [GSQ v1 §3~4](https://arxiv.org/html/2604.18556v1)

정상 자유답변이 나오지 않는 학생도 verified target의 teacher forcing으로 학습을 시작할 수 있다. 따라서 “정상 답변을 먼저 얻어야 GSQ를 시작”이라는 필요조건은 추가하지 않는다. 반대로 학습 시작 가능성은 성공 보장이 아니다. soft relaxation의 CE 개선을 hard ternary 배포 성능으로 승격하거나 기존 local 복원 실패를 새 QAT/KD 전체의 불가능 증거로 확장하지 않는다. 같은 손실·같은 teacher signal·같은 노출의 STE와 비교해야 이산 최적화 효과를 말할 수 있다.

### 반복 구조: 숫자와 단일 효과

Part I Table 2의 sandwich topology 단독 비교는 ARC-C와 HumanEval+에서 음성이다. 최종 Huginn 조합이 더 좋다는 결과를 topology 하나의 모든 과제 우위로 귀속시키지 않는다. [Part I Table 2](https://arxiv.org/html/2610.23036v1)

Closing the Loop Appendix I는 310B 토큰 recipe가 오래된 Ouro schedule보다 적은 compute를 쓴다고 계산하지만, 같은 토큰의 dense 1.4B와는 학습 FLOPs가 다르다. Table 21의 LoopLM 32.0 대 dense 1.4B 8.0 GFLOPs/token은 4배이고 dense 3.9B 22.8과는 약 1.4배다. “25배 적은 학습 토큰”을 “같은 예산 dense보다 25배 빠름”으로 바꾸지 않는다. [Closing the Loop Appendix I](https://arxiv.org/html/2610.00673v1)

STARS Table 2는 **5개 수학 과제** 평균이며 첨부의 “6개 과제”와 다르다. 보고된 STARS R4 74.18, R8 65.55에서는 더 반복하면 점수가 여전히 낮아진다. 원문은 JVP proxy를 설명하나 현재 공식 addition 예제는 detach한 마지막 상태에서 `autograd.grad`로 VJP를 계산하며 기본 1회의 `norm(Jᵀv)²`를 쓴다. JVP 블록은 주석이고, 이 addition 코드를 Ouro 학습기에 그대로 귀속시키지 않는다. 어느 쪽도 정확한 fixed-point 안정성이나 정답의 보증으로 읽지 않는다. 표의 수치는 Ouro 결과이며 TinyLM/Huginn 재현이 아니다. [STARS §6/Table 2](https://arxiv.org/html/2605.26733v1), [공식 addition source](https://raw.githubusercontent.com/njuyxw/STARS/main/train_addition/train.py)

LoopCD의 logits 보정·가변 반복 종료·LRM 선택·terminal-state KV 근사는 원 next-token 분포와 계산 경로를 바꿀 수 있다. 기본 고정 반복/정확한 iteration별 KV와 별도 행으로 두고, MTP 검증 분포와 cache rollback까지 동일 정의를 사용해야 한다. 이번 반 검토에서는 이 네 후속 방법의 구현 또는 성능 재현을 수행하지 않았다.

## 8. 오염·노출·온라인 검증에 대한 최종 반례

1. **같은 update 수만으로 같은 학습량이 아니다.** trace와 direct, MNTP와 causal, tokenizer 변경은 input tokens·유효 주 target·보조 target·원문 bytes·생성된 교사 token을 모두 바꿀 수 있다. 동일 노출과 동일 wall-clock 비교를 따로 제시한다. teacher cache 생성·설치/compile·검증·저장 비용을 숨기지 않는다.
2. **한 학생에서의 점수 차이가 구조 일반화가 아니다.** 같은 checkpoint/seed의 대응 문항 bootstrap은 문항 표본 변동이며 학습 seed 변동을 포함하지 않는다. Core6는 과제 동일 가중치 계층 bootstrap, Belebele은 지문/대응 문항 묶음을 고려한다. 기준표의 다른 과제/가족용 판정자를 복사하지 않는다.
3. **online/on-policy는 현실 진위 검사라는 뜻이 아니다.** 학생이 생성한 prefix에서 teacher signal을 얻는 학습 방식은 생성한 사실이 참인지 확인하는 절차와 다르다. ALM/ACTD의 teacher confidence, 낮은 entropy, hidden classifier, 반복 수렴은 현실 정답 verifier가 아니다.
4. **MTP verify는 주모델 분포 정합 검사다.** draft–verify가 일치해도 주모델이 틀릴 수 있다. 별도 정답·지문·실행 가능한 규칙의 검증 없이는 “실시간 사실 검증”이라 부르지 않는다.
5. **공식/final 문항은 train 교사에게 주지 않는다.** 평가 ID·원문·정답·teacher cache namespace와 학습/SFT/KD를 분리하고 final holdout으로 데이터 선별·중간 튜닝을 하지 않는다. 평가문항을 총괄 교사 생성 파이프라인에 넘기지 않았다.
6. **목표 모델의 정확 파일이 필요하다.** Qwen IQ2 목표와 Gemma 한국어 목표는 선택한 정확 파일·Base/IT·정밀도·template·같은 문항의 실제 점수가 있어야 계산할 수 있다. BF16 모델 카드나 기존 Falcon MC768로 대신하지 않는다. 현재 이 문서에는 새 실측 목표 달성 판정이 없다.

## 9. 최초 소스 감사의 미완료와 인계

최초 소스 감사에서 완료한 것은 공식 소스·로컬 자산/의존성·채점 차이의 감사와 이 문서 작성이다. 당시 공식 모델 평가·설치·자료 반입·TinyLM 공식 adapter 구현·tokenizer parity·새 full 점수·속도·메모리·통계 실행은 모두 `NOT_RUN`이었다. 이후 자료 반입만 추가 승인되어 §11에 기록한다. 어떤 외부 수치도 TinyLM 결과로 옮기지 않았다.

총괄의 다음 결정은 평가용 설치 범위를 확인한 뒤 A/B/C 중 실제 가능한 경로를 정하는 것이다. 실행용 source commit·dataset revision 고정이 남았으며, 웹 API/commit 목록 열람 실패 때문에 현재 `main`의 정확 SHA를 추정해 기재하지 않았다. 경로·버전·허가가 닫히기 전 복사 실행 가능한 것처럼 가상의 로컬 공식 CLI를 안내하지 않는다.

## 10. 문헌 최종판 교차검토 — 최소 실험을 반증할 조건

교차검토 대상은 [당일 문헌 대조](20261023_acceleration_distillation_literature.md)의 §3~5와 관련 로컬 `mtp_sft.py`, `muon.py`, `transformer.py`다. 문헌 담당의 “구현할 수 있음”을 실험 PASS로 올리지 않았다. 아래는 실행 명령·새 채택 문턱이 아니라 각 가설을 식별하기 위해 필요한 대조와 반례다.

| 순서·후보 | 실제로 새로 묻는 질문 | 가장 작은 반증/위험 | 총괄이 결과와 함께 남길 것 |
|---|---|---|---|
| 1. exact CCE 또는 Liger | 기존 위치선택/chunk/checkpoint 위에서 손실 소비기만 바꾸면 추가 순이득이 있는가 | scalar CE는 같아도 위치별 upstream gradient나 tied input/output의 합산 gradient가 틀릴 수 있음. compile·재계산·호출 overhead로 whole update가 더 느릴 수 있음 | 같은 hidden/target의 값·gradient·한 update 정합, 유효 target 수, warm 포함/제외 시간·peak; 아직 설치되지 않은 커널을 실행했다고 쓰지 않음 |
| 2. ALM core | 같은 verified 답 CE에 byte-chunk likelihood 신호를 추가하면 전이가 좋아지는가 | tokenizer/template/shift가 다르거나 긴 chunk 확률이 수치상 0에 몰리면 “정렬 완료”만 남고 신호가 약함. CE gradient를 건드리지 않고 teacher cache만 더한 비용일 수 있음 | no-hidden/no-debias의 정확한 명명, chunk coverage·길이/한영·비정상 값·분모, 같은 CE 자료·초기화·노출과 teacher 비용 |
| 3. NorMuon | 행별 적응의 이득이 최종 RMS/학습률/None-gradient 정책 변경과 구분되는가 | 공식 main은 `grad=None`도 0으로 바꿔 과거 momentum/weight decay가 작동할 수 있으나 현재 TinyLM은 skip. 비활성 head까지 업데이트하면 비교가 달라짐 | 논문형 또는 main형 명명, 사각 행렬의 업데이트 norm·gradient 보존·None/0 처리·state resume, LR 크기와 time-to-quality |
| 후속 ACTD | 매핑된 top-k anchor와 residual 억제가 잘못된 mass 이동보다 유익한가 | 여러 teacher token이 같은 student ID로 충돌, 자동 BOS 삽입, non-anchor인 정답 억제. entropy 감소만으로 성공처럼 보일 수 있음 | 충돌 목적함수·빈/특수 token 처리·anchor/residual 합, same-CE/ALM와 분리된 head/노출·실제답 |
| 후속 GSQ 유래 QAT | 같은 hard 삼진 함수와 CE/KD에서 이산 선택의 gradient 설계가 기존 STE보다 나은가 | 공식 GSQ soft forward와 hard 추출의 gap, 보조 logits 포화/붕괴. head 정밀도까지 함께 바꾸면 GSQ의 단독 효과를 모름 | 동일 초기 hard codes/scales, body/head 적용범위, soft/hard 양쪽 결과, code 변경률·점유·gradient·학습 메모리 |

권장 순서는 문헌 담당의 A(손실 소비기) → B(같은 교사답 CE/ALM)를 조건부 수용한다. A가 새 설치/호환으로 막혀도 기존 CE를 이용한 reference scoring·ALM 준비까지 막을 필요는 없다. C(optimizer)는 B와 동시에 바꾸지 않는다. 이 순서 의견은 GPU 실행이나 패키지 설치 권한을 추가하지 않는다.

### ALM의 optional 항과 수치 반례

no-hidden/no-outcome-debias는 원문이 허용하는 최소 likelihood 목적이다. hidden이 없다는 이유만으로 불가능하다고 결론내리지 않는 문헌 담당의 설명은 타당하다. 다만 byte 경계가 같다는 사실은 teacher/student prefix의 special tokens·normalizer·loss mask가 같다는 뜻이 아니다. `C_T`, `C_S`가 모두 매우 작은 확률로 가면 유한온도 binarized loss의 작은 변화와 실제 정답 개선은 분리해서 본다. 안정적인 log 공간 구현과 실제 gradient 관측이 필요하며, 이를 해결하려고 목적을 logprob MSE나 다른 온도 극한으로 바꾸면 그 변형을 명명해야 한다.

### ACTD 충돌에 대한 분석적 toy — 실행 결과 아님

teacher top-k 확률 `(0.6, 0.4)`가 모두 같은 student token A에 매핑된다고 하자. `p=p_S(A)`, residual 가중치 1에서 논문 Eq7/8을 문자 그대로 쓰면 `|0.6-p|+|0.4-p|+(1-p)`이고 최소는 `p=0.6`이다. 반면 teacher 질량을 A에 먼저 합쳐 dedup한 목적은 `|1-p|+(1-p)`로 최소가 `p=1`이다. 두 구현은 동치가 아니다.

따라서 “충돌은 합치면 끝”이라고 자동 수정해서는 안 된다. 공식 코드가 아직 공개되지 않은 상태에서는 논문의 중복 항/집합 residual을 literal하게 재현할지, 합산 변형을 별도 비교할지 총괄이 목적함수와 함께 고정해야 한다. 이는 ACTD가 실패한다는 실험 증거도, 논문 오류 확정도 아니며 구현의 해석 갈림이다. [ACTD §3.2](https://arxiv.org/html/2608.29662v1)

### GSQ 최신판과 고정 삼진 forward

문헌 담당의 최신 v2 설명을 [원문](https://arxiv.org/html/2604.18556v2)과 [공식 ternary source](https://raw.githubusercontent.com/IST-DASLab/GSQ/main/src/quantization/gumbel_quantizer_ternary.py)로 추가 확인했다. forward는 noisy sigmoid의 soft mask/sign 곱이며 `get_hard_weights`가 별도다. 따라서 사용자가 요구한 hard 삼진 forward를 지키는 QAT는 reference 코드를 그대로 실행하는 방식과 다르다. soft 모델의 loss만 좋아진 결과를 hard 배포본의 개선으로 채택할 수 없다. 문헌 §5.5의 이 구분은 타당하다.

최소 검증에서 body 이산 최적화, 입력/head 삼진화, 새 KD 손실을 한 번에 바꾸지 않아야 한다. 현재 FP32 접근자 경로를 삼진으로 바꾸는 영향과 Gumbel 선택 방식의 영향을 각각 식별한다. 정상 답변 0%여도 teacher forcing 목적은 정의되므로 실험의 시작을 막는 새로운 품질 선결을 만들지 않는다.

## 11. 추가 승인된 비교 자산 inventory와 실제 반입

### 11.1 지명 모델의 기존 자산 — source/metadata 확인

아래 확인은 `HF`, `HF/hub`, 지명 GGUF 하위의 **지명 모델 패턴만** 대상으로 했다. 다른 HF 원천 전수나 보호 데이터 열거를 하지 않았다. safetensors는 header dtype와 파일 크기만 읽었고 tensor 데이터/모델을 로딩하지 않았다. dtype는 저장 타입이며 실제 평가의 계산 dtype와 다르다.

| 모델 | 실제 기존 경로/파일 | revision | 저장 dtype·크기 | 엔진/미확인 |
|---|---|---|---|---|
| Falcon90M Base | `HF/models--tiiuae--Falcon-H1-Tiny-90M-Base/snapshots/7994372e93b62822ae25f8bfb19f653649cea3a3/model.safetensors` | `7994372e93b62822ae25f8bfb19f653649cea3a3` | BF16, 182,304,120 B | 기존 `diag_p106b_night_falcon.py`는 Transformers built-in fallback·FP32 MATH로 실행한 별도 로컬 평가. 새 공식 실행 아님 |
| Qwen3-0.6B Base | `HF/models--Qwen3-0.6B-Base/model.safetensors` | local download metadata 세 파일에서 `da87bfb608c14b7cf20ba1ce41287e8de496c0cd` | BF16, 1,192,135,096 B | HF `Qwen3ForCausalLM` 후보. 이 감사의 모델 실행 없음 |
| Qwen3.5-0.8B Base | `HF/models--Qwen--Qwen3.5-0.8B-Base/snapshots/dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68/model.safetensors-00001-of-00001.safetensors` | `dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68` | BF16+F32, 1,746,942,600 B | HF conditional-generation/text model 경로 확인 필요. hybrid state/FP32 예외 포함 |
| Gemma3-270M Base | `HF/models--google--gemma-3-270m/snapshots/9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1/model.safetensors` | `9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1` | BF16, 536,223,056 B | HF `Gemma3ForCausalLM` 후보; IT 점수를 대신하지 않음 |
| Gemma3-1B PT | `HF/models--google--gemma-3-1b-pt/snapshots/fcf18a2a879aab110ca39f8bffbccd5d49d8eb29/model.safetensors` | `fcf18a2a879aab110ca39f8bffbccd5d49d8eb29` | BF16, 1,999,811,208 B | HF `Gemma3ForCausalLM` 후보 |
| GPT2 / Bonsai2B / 정확 Qwen0.8 IQ2 | 최초 scoped 검색에서 없음 | 신규 반입은 아래 별도 기록 | 기존 BF16 다섯 종을 Q4로 다시 받을 필요 없음 | 정확 IQ2 목표는 Base BF16로 대체 불가 |

별도 Falcon Instruct GGUF snapshot `578d134817c19bc48991ccff9a14709d664261cc`의 IQ3_S/IQ3_XS/Q2_K/Q3_K_S/TQ1_0/TQ2_0 파일은 GGUF v3 magic을 확인했다. 이것만으로 엔진 호환/내용 무결성/모델 품질을 검증한 것은 아니다. **IQ2_M과 IQ3_XXS는 각각 12,668,800 B이나 첫 8 byte가 모두 0**이다. 이 두 파일은 정상 GGUF로 세지 않고 원본 그대로 보존했다. Base/Instruct도 구분한다.

### 11.2 BabyLM 공개 평가자료 실제 반입

총괄의 파일별 추가 승인 뒤 `data_cache/p106b_official_eval_assets/babylm_2026_strict_8d52da9/`에 다음 **82개, 66,319,987 B**만 받았다. 고정 revision은 `8d52da9424a9ff30b9e8266c4f751aba9c504233`이다. 완료 시각 UTC `2026-10-22T21:03:09.343123+00:00`는 KST 2026-10-23 06:03이다. [파일별 반입 manifest](../../data_cache/p106b_official_eval_assets/babylm_2026_strict_8d52da9/manifest.json)

| 원격 경로 prefix | 파일 수 | 실제 bytes |
|---|---:|---:|
| `evaluation_data/full_eval/blimp_filtered/` | 67 | 21,607,612 |
| `evaluation_data/full_eval/supplement_filtered/` | 5 | 1,384,705 |
| `evaluation_data/full_eval/comps/` | 4 | 33,236,854 |
| `evaluation_data/full_eval/entity_tracking/` | 3 | 7,519,163 |
| `evaluation_data/full_eval/reading/` | 1 | 615,013 |
| `evaluation_data/full_eval/aoa/` | 2 | 1,956,640 |

각 파일은 manifest에 원격 경로/고정 URL·local 경로·revision·size·실제 SHA256을 기록했다. 원격 LFS SHA256 또는 Git blob SHA1과 추가 대조했다. 파일명·크기만 맞춘 반입이 아니다. manifest의 82는 자료 파일 수이며 manifest 자체는 그 분모 밖이다. 문항·정답 내용은 보고/학습 교사/Luna로 전달하지 않았다.

공식 API는 public·gated=false를 보이지만 cardData/루트 README/LICENSE 파일/license tag가 없었다. **이 평가 저장소의 배포 LICENSE는 미명시**다. 다른 BabyLM 훈련 저장소의 MIT를 복사하지 않는다. 원격 전체 175개·151,948,457 B 중 GLUE fine-tuning·fast·멀티모달 파일은 받지 않았다. full EWoK/GlobalPIQA도 이 snapshot 밖이므로 받지 않았고 약관 동의도 하지 않았다. [고정 revision의 공식 API metadata](https://huggingface.co/api/datasets/BabyLM-community/BabyLM-2026-Strict-Evals/revision/8d52da9424a9ff30b9e8266c4f751aba9c504233?blobs=true)

이 단계는 `ASSET_DOWNLOADED_HASH_VERIFIED`다. 패키지 설치·tokenizer/model 로딩·공식 평가·성능 향상은 `NOT_RUN`이며, 무설치 기존 런타임에서 가능한 후속 실행의 결정은 총괄이 소유한다.

### 11.3 추가 승인한 비교 GGUF 3개 — 실제 반입 완료

BabyLM 반입 완료 후 총괄이 정확 파일별 반입을 추가 승인했다. 다음 세 파일만 새 `HF/benchmark_20261023/` 아래 지명 폴더에 받았고 각 폴더에 파일 하나와 `manifest.json` 하나를 보존했다. 기존 파일 교체는 없다. 완료는 KST 2026-10-23 06:05이며 총 880,269,536 B다.

| 모델·실제 새 파일 | 고정 repo revision | 실제 bytes·라이선스 metadata | manifest |
|---|---|---|---|
| GPT2 `gpt2_q4km/gpt2-q4_k_m.gguf` | `enacimie/gpt2-Q4_K_M-GGUF` @ `f273bb57fe6ccad3d9ef415577a1b5c8d051544e` | 112,858,624 B · MIT | [반입 기록](../../HF/benchmark_20261023/gpt2_q4km/manifest.json) |
| Bonsai2B `bonsai2_2b_ptq1/Ternary-Bonsai-2-2B-PTQ1_0.gguf` | `prism-ml/Ternary-Bonsai-2-2B-gguf` @ `683f7be2629342a50987627b40881e54761a2430` | 429,183,456 B · Apache-2.0 | [반입 기록](../../HF/benchmark_20261023/bonsai2_2b_ptq1/manifest.json) |
| 정확 Qwen0.8 IQ2 `qwen35_08b_iq2xxs/Qwen3.5-0.8B-UD-IQ2_XXS.gguf` | `unsloth/Qwen3.5-0.8B-GGUF` @ `6ab461498e2023f6e3c1baea90a8f0fe38ab64d0` | 338,227,456 B · Apache-2.0 | [반입 기록](../../HF/benchmark_20261023/qwen35_08b_iq2xxs/manifest.json) |

각 manifest는 다운로드 URL/원격 파일명·repo/revision·실제 bytes·SHA256·upstream LFS SHA256·GGUF v3 magic·시각·라이선스 출처를 포함한다. 세 파일의 실제 SHA256은 각각 `67027f93ace5b0af66c4ffceeb529e556facd9968e63c4f822d7b4a351e835e1`, `36061ad406df8a4903a6db005be350c50fabfaf717f9ef0acf4b76adcd9929fa`, `a369165c8ec45a92d55cbad98b5377e2c32ca8dfc824c899d9d05b33b6b53e54`이며 upstream 값과 일치했다.

Bonsai PTQ1_0는 지명 Prism 엔진의 호환 확인이 필요하고, 나머지도 단지 파일명/magic으로 엔진 성공을 주장하지 않는다. **세 모델 모두 모델 로딩·tokenizer 실행·벤치마크·품질/메모리/속도·설치는 `NOT_RUN`**이다. 파일 확보를 목표 점수 달성이나 엔진 PASS로 승격하지 않는다. 원격 모델 API/card metadata의 라이선스 표시는 각 고정 repo의 표기이며 TinyLM 자체 배포 라이선스를 대신하지 않는다.

### 11.4 최종 재검사와 teacher-forcing API의 정적 계약

다운로드 후 별도 읽기 전용 재검사에서 BabyLM 자료 82개의 실제 SHA256과 upstream LFS SHA256 또는 Git blob SHA1, 세 GGUF의 실제/upstream SHA256·정확 bytes·v3 magic이 모두 일치했다. 승인된 새 폴더에 manifest 외 다른 파일이나 남은 `.part`는 없었다. 이는 **반입 무결성 검사**이지 모델 품질·엔진·평가 PASS가 아니다.

현재 공식 harness `GGUFLM._score_position`은 `/v1/completions`로 `prompt` token-ID 배열, `temperature:0`, `max_tokens:1`, `logprobs:2`, `logit_bias:[[target_id,100]]`를 보낸다. `model`과 `id_slot`은 지정 시 추가된다. `choices[0].logprobs.content[0]`의 `id == target_id`를 요구하고 그 항목의 `logprob`를 합산한다. `top_logprobs`는 원 argmax 여부 진단이며 target 우도를 대신하지 않는다. [공식 harness source](https://raw.githubusercontent.com/EleutherAI/lm-evaluation-harness/main/lm_eval/models/gguf.py)

native `/completion`은 `n_predict:1`, `n_probs:2`, `stream:false`, `post_sampling_probs:false`를 명시할 수 있다. 위와 같은 token-ID prompt/temperature/logit_bias에서 비스트리밍 응답의 target 항목은 `completion_probabilities[0]`이며 내부 키는 `id`, `logprob`, `top_logprobs`다. 현재 upstream은 OAI 길이/확률 키를 alias로 받아들이지만 로컬 엔진이 같은 버전이라고 가정하지 않는다. `post_sampling_probs:true`면 `prob`/`top_probs`로 바뀌므로 두 의미를 섞는 permissive parser를 쓰지 않는다. [native/OAI serializer](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/server-task.cpp), [request schema](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/server-schema.cpp)

총괄의 별도 canary를 위한 반증 조건은 다음과 같다. 이 담당은 API를 호출하거나 canary를 실행하지 않았다.

1. 평가 문항 아닌 합성 텍스트로 원 top-2를 구하고, 가능하면 비-argmax인 top-2 token을 target으로 골라 무bias logp 대조값을 확보한다. 실제 target의 ID 일치·한 항목·정상 logprob·top-ID/우도 대조를 함께 확인한다. target이 top-k 밖이면 top-k 누락을 확률 0으로 채우지 않는다.
2. 같은 prefix IDs·서버 model/revision·slot 상태에서 bias 20/100/200 중 **실제로 target을 강제한 요청끼리** 원 target logp와 unbiased top-logprobs가 수치 오차 범위에서 보존되어야 한다. 20에서 강제 실패는 `NOT_FORCED`이며 모델 오답이나 임의 0점이 아니다. bias가 커질수록 target logp가 0으로 이동하면 post-bias 확률 또는 서버 의미 차이를 의심한다. 불변만으로 절대 정확성을 입증하지 않으므로 무bias 대조값도 남긴다.
3. `n_predict:1`만으로 MTP OFF가 보장되지 않는다. 현재 upstream은 request별 speculative parameter 조정이 비활성화된 블록 안에 있으므로 기존 Session의 실제 OFF 경로/로그를 확인해야 한다. main 웹 소스가 로컬 지명 fork의 성공 증거는 아니다.
4. 현재 serializer는 확률 0을 `-3.402823…e38` float-lowest sentinel로 반환할 수 있다. 따라서 단순 finite 검사만으로 유효 logp라 판정하지 않고 sentinel/underflow를 따로 기록·거부한다. 현재 pre-sampling 경로는 원 logits의 softmax로 target 확률을 찾으므로 이 정밀도 한계가 남는다. [확률 계산](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/server-common.cpp), [pre-sampling target 추출](https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/server-context.cpp)

이 API 계약 검토는 ALM core의 교사 reference scoring 가능성을 준비한 것이며 full-vocab teacher logits·hidden API가 확보됐다는 뜻은 아니다. 설치 승인, 실제 교사 Session 실행과 공식 full-benchmark 평가는 여전히 이 담당의 수행 범위 밖이다.

## 12. 추가 승인 Core6 평가 split의 고정·실제 반입

### 12.1 실제 자산과 권리 표기

고정 harness commit은 `d6de81643928d653435c431bae19945d41d32520`이며 [도구/최소 의존성 보고](20261023_official_eval_minimal_dependencies.md)와 source manifest를 참조한다. 이번에는 그 정확 YAML이 지정하는 다음 평가 split만 새 `data_cache/p106b_official_eval_assets/core6_d6de816_20261023/`에 받았다. **기존 `datasets/bench`를 덮어쓰거나 다른 mirror로 바꾸지 않았다.**

| task·공식 repo | 고정 데이터 revision | config / 평가 split | 실제 Parquet bytes·footer 행 수 | 고정 repo의 라이선스 표기 |
|---|---|---|---|---|
| PIQA · `baber/piqa` | `142f6d7367fd9877f0fb3b5734ea6a545f54cdd1` | default(YAML name=null) / validation | 299,694 B · 1,838 | 카드/README/LICENSE 미명시 |
| ARC-Easy · `allenai/ai2_arc` | `210d026faf9955653af8916fad021475a3f00453` | ARC-Easy / test | 346,257 B · 2,376 | 카드 `cc-by-sa-4.0`; 설명의 licensing 절은 정보 부족 |
| ARC-Challenge · 같은 repo | 같은 고정 revision | ARC-Challenge / test | 203,808 B · 1,172 | 위와 같음 |
| HellaSwag · `Rowan/hellaswag` | `218ec52e09a7e7462a5400043bb9a69a41d06b76` | default(YAML name=null) / validation | 6,315,951 B · 10,042 | 카드 license 필드는 없지만 고정 README:201에 MIT와 원본 링크 명시 |
| WinoGrande · `allenai/winogrande` | `01e74176c63542e6b0bcb004dcdea22d94fb67b5` | winogrande_xl / validation | 85,928 B · 1,267 | 카드 미명시, README licensing 절은 정보 부족 |
| BoolQ · `aps/super_glue` | `3de24cf8022e94f4ee4b9d55a6f539891524d646` | boolq / validation | 1,313,731 B · 3,270 | root `other`; README는 각 원 데이터 권리를 참조하며 BoolQ 별도 정확 라이선스는 이 snapshot에 미확정 |

평가 Parquet는 **6개·8,565,369 B·19,965행**이고 README 4개를 합한 실제 upstream 반입은 **10개·8,612,294 B**다. train·다른 config/task의 자료는 받지 않았다. schema/권리 확인용 선택 metadata 5개와 footer audit 1개, 전체 manifest는 파생 영수증으로 따로 구분한다. 원본/파생 파일 모두 20,000,000 B 미만이며 최대 자료도 6.32MB 이하다. 완료 시각은 KST 2026-10-23 06:42다.

[전체 manifest](/home/uranus/tinyLM/data_cache/p106b_official_eval_assets/core6_d6de816_20261023/manifest.json)는 repo/revision·고정 원격 URL·정확 파일명·upstream LFS SHA256 또는 Git blob SHA1·실제 SHA256/bytes·config/split·행수·YAML SHA·라이선스 출처와 미명시를 기록한다. 반입 뒤 별도 재해시에서도 upstream/파생 파일이 모두 일치했고 공식 source tree도 불변이었다. 데이터 취득 승인으로 재배포권을 추정하지 않는다. HellaSwag의 README 표기는 [그 고정 snapshot](https://huggingface.co/datasets/Rowan/hellaswag/blob/218ec52e09a7e7462a5400043bb9a69a41d06b76/README.md#licensing-information), SuperGLUE의 별도 권리 지시는 [그 고정 snapshot](https://huggingface.co/datasets/aps/super_glue/blob/3de24cf8022e94f4ee4b9d55a6f539891524d646/README.md#licensing-information)에 근거한다.

### 12.2 실제 footer 관측과 schema 한계

모든 Parquet의 `PAR1` magic, `FileMetaData.num_rows`, row-group별 `num_rows` 합을 **표준라이브러리로 footer만 읽어** 대조했고 위 행 수와 일치했다. data page/문항 값은 디코딩하지 않았다. [footer metadata 기록](/home/uranus/tinyLM/data_cache/p106b_official_eval_assets/core6_d6de816_20261023/parquet_footer_metadata.json)에 물리 schema·내장 `huggingface` features·writer 버전·footer SHA를 남겼다. 이는 datasets/PyArrow의 실제 loader 검증과 다르다. [Apache Parquet metadata 정의](https://raw.githubusercontent.com/apache/parquet-format/master/src/main/thrift/parquet.thrift), [Apache compact protocol 정의](https://raw.githubusercontent.com/apache/thrift/master/doc/specs/thrift-compact-protocol.md)

여섯 파일 모두 `ARROW:schema` 및 `huggingface.info.features`가 들어 있다. 특히 PIQA label은 물리 INT64이지만 의미상 ClassLabel `['0','1']`, BoolQ label도 INT64/ClassLabel `['False','True']`다. HellaSwag label은 문자열이며 ARC의 choices는 **text/label 각각의 list를 가지는 struct**다. 이를 일반 pandas/JSON 변환으로 plain int·list-of-dicts로 바꿔도 동일 schema라고 단정할 수 없다. WinoGrande의 answer도 문자열을 유지한다.

현재 설치된 datasets 5.0.0의 parquet builder는 `Features.from_arrow_schema`를 부르며, 이 함수는 embedded HF features와 실제 Arrow type이 맞는 필드에 ClassLabel 등을 복원하는 경로를 갖는다. 따라서 **정확한 로컬 Parquet에서 같은 schema를 복원할 source 경로는 있다.** 하지만 현재는 그 loader를 import/실행하지 않았고 실제 `features`/row 순서/정규화·prompt의 동등성은 `NOT_RUN`이다. footer가 맞는다는 사실을 공식 end-to-end parity PASS로 올리지 않는다.

### 12.3 datasets loader가 필요한 범위와 train 취득 방지

반입·해시·footer 행수 확인에는 datasets loader가 필요하지 않았다. 반면 **원본 공식 harness의 `ConfigurableTask`를 그대로 사용할 때는 datasets 객체/loader 계약이 필요**하며, 단순 raw Parquet 보존만으로 이를 없앤 것이 아니다. 앞으로 가능한 경로는 다음처럼 구분한다. 어느 경로도 이번에 실행하지 않았다.

| 경로 | 계약·장점 | 남는 차이/선결 |
|---|---|---|
| A. 공식 repo 경로·config 보존 + local data_files | 별도 task config/adapter에서 정확 `revision`과 `{평가 split: 정확 로컬 파일}`을 `dataset_kwargs`로 명시. 원 prompt/process_docs/metric source 보존 | repo metadata와 실제 loader 호환·아래 빈 fewshot sampler를 확인해야 함. local 파일 외 취득 허용하지 않음 |
| B. local `parquet` builder | 같은 파일/embedded HF features로 dataset 객체를 만들 수 있는 source 경로. 완전 로컬 취득 제어가 쉬움 | dataset_path/builder fingerprint·DatasetInfo가 원 repo 경로와 달라짐. features/행수/순서/공식 prompt를 대조하기 전 `LOADER_PARITY_NOT_RUN` |
| C. source-only 자산 유지 | 현재 승인 범위 그대로, 설치·loader·평가 0 | 실제 공식 채점 착수는 못 함. 자산 완성과 평가 완료를 분리 |

실행을 준비할 때는 A를 우선 검토하되 원본 source는 수정하지 않는다. 중요한 두 함정이 있다.

1. `api/task.py:869`는 기본적으로 `load_dataset(path=repo,name=config,**dataset_kwargs)`를 **split 없이** 호출한다. eval 목적이라도 기본 config의 train 등까지 준비할 수 있으므로 평가 파일만의 명시 allowlist가 필요하다. 또한 여기에 `split='validation'`만 전달하면 반환이 Dataset이 되어, task가 기대하는 `self.dataset[split]`의 DatasetDict와 달라질 수 있다. split 이름을 key로 하는 data_files mapping과 DatasetDict 계약을 지킨다.
2. `ConfigurableTask.__init__:782`는 0-shot이어도 `fewshot_docs()`를 즉시 호출하고, 기본 fallback `Task.fewshot_docs:204`는 training_docs를 먼저 읽는다. 따라서 train 없이 평가 파일만 주는 것과 `--num_fewshot 0`만으로는 초기화가 보장되지 않는다. **선택한 평가가 0-shot일 때** 별도 config에 `num_fewshot:0`와 `fewshot_config:{samples:[]}`를 초기화 전에 명시하는 안은 source상 빈 sampler 분기를 사용한다(`fewshot_docs:906`, 실제 sample은 `num_fewshot>0`일 때만). train 데이터를 추가로 받거나 평가 split을 train으로 개명하지 않는다. 이 설정의 실제 초기화·request parity도 아직 미실행이다. few-shot 평가를 요구하면 다른 자료/승인이 필요하다.

### 12.4 현재 완성 상태

Core6 source commit·지명 데이터 revision·평가 파일·upstream/로컬 해시·footer 행수/schema metadata까지 확보했다. BabyLM 82개, 비교 GGUF 3개는 앞 절의 별도 상태를 유지한다. **패키지 설치/등록, lm_eval/datasets/PyArrow import, 모델/GPU, dataset row 디코딩, 실제 공식 평가와 점수는 `NOT_RUN`**이다. 평가 문항/정답을 train 교사나 Luna로 전달하지 않았다. 공유 계획·결과·기준표 갱신은 총괄이 소유한다.

## 13. Stage7b ALM core와 명시 문맥 QA 대조의 source-only 반 검토

### 13.1 범위·판독 snapshot·원문과의 대응

총괄이 추가 지시한 `tinylm/train/alm.py`, `scripts/test_p106b_alm_core.py`, P106B 계획의 Stage7b0W/7bW를 읽고 [ALM v4 §3·App. A/B/H/I](https://arxiv.org/html/2503.20083v4)와 대조했다. QA 후보의 구체적 source 계약은 `scripts/p106b_night_qa_data.py`의 코드만 읽었다. 원천 QA/평가 문항·정답과 보호 데이터는 열지 않았다. 이 절만 보완하며 구현·시험·계획 정본·활성 byte helper는 수정하지 않는다.

| 경로 | 이번 동작·권한 | 증거·제외 |
|---|---|---|
| 이 문서 §13 | 총괄이 요청한 반 검토 저장 | 연구 검토이지 실행 결과 아님 |
| `tinylm/train/alm.py` | 읽기·파일 SHA256 | `bff4c3a094c60bfb032e60df19c909639256d3f14193d73d328eb02ad5e803f2`; import/수정 0 |
| `scripts/test_p106b_alm_core.py` | 읽기·파일 SHA256 | `540b889ed33c4ba5fd8343732994e40ce1a62b622b76a770b046e704cabc5ae3`; 이 snapshot에 시험 함수 11개, 실행 0 |
| Stage7b 계획·QA builder·모델 head source | 필요한 절만 읽기 | source 판독; 데이터·tokenizer·모델·torch 로딩 0 |
| `scripts/p106b_alm_bytes.py` | 문헌 담당 활성 소유권 존중 | 이번 코드 검토 대상/수정 대상 아님 |

총괄이 처음 전달한 CPU oracle 8개 PASS는 **총괄의 실행 보고**이며 이 담당의 재실행 증거가 아니다. 뒤이은 수정과 시험 추가를 source에서 확인했으므로 옛 결함을 현재 결함으로 반복 보고하지 않는다. 아래는 현재 snapshot의 계산 판독이다.

| 축 | 판독 | 남는 구분 |
|---|---|---|
| 방향 | `binary_kl_logq`는 `KL(Bern(qT)||Bern(qS))`; 교사 tensor는 detach | reverse KL/교사 CE/MSE가 아님 |
| temperature | chunk 안 자연로그 우도를 합한 뒤 `/tau`; `exp(C/tau)` | API sampling temperature나 vocabulary softmax temperature와 다름. `tau²`를 곱하지 않은 것이 원문 누락 버그는 아님 |
| 로그 안정 | `log1mexp`에서 두 분기를 먼저 나누고 `log1p`/`expm1` 사용; 작은 scalar vector만 FP64 | head FP32에서 이미 반올림된 NLL을 FP64로 복구하지는 못함 |
| 분모 | CE는 실제 assistant target 수, KD는 실제 유효 chunk 수; optimizer-update 전체 분모를 호출자가 전달 | 논문 padded 행렬 평균과 비트 단위 동일 recipe라고 부르지 않음. EOT는 CE만 포함하는 별도 선택 |
| head·shift | 원 `_head_logits`와 `return_hidden` 경로를 사용하고 hidden을 detach하지 않음; 이미 shift된 target 계약 | raw index `i→i−1`, 두 native tokenization과 turn/EOT 매핑은 caller의 별도 책임 |
| 경계 | `qT=1`은 별도 분기; `qS=1,qT<1`은 `StudentProbabilityBoundary`; nonfinite/양의 teacher logp 거부 | 진짜 0확률·sampler sentinel·수치 underflow·FP32 반올림을 같은 관측으로 기록하지 않음 |

outcome debias/hidden이 없는 binary core 자체는 원문에서 배제되지 않는다. 다만 원문 기본 조합은 GradMag를 쓰고, 이번은 고정 계수·assistant-only·유효 chunk 평균·별도 GGUF scoring의 축약 실험이다. 논문 전체 recipe나 full-vocabulary KL 재현이 아니다. [ALM v4](https://arxiv.org/html/2503.20083v4)

### 13.2 이미 반영된 지적과 남는 경계 시험

초기 판독 당시의 finite sampler sentinel 수용, CE 합만의 tied-head 시험, 균등 micro만의 분모 시험은 총괄에게 먼저 보냈다. 최신 source에는 `teacher_logprob > -1e30` 거부, q1 원인 분류, **불균등 CE/KD 수와 KD 0인 micro**, **비선형 KL→per-token NLL→모든 원 모델 parameter gradient** 비교 시험이 추가되어 있다. 이는 수정/시험 존재 확인이며 새 시험 PASS나 실제 학생 학습 PASS를 대신하지 않는다.

남는 source 계약과 후속 시험 소유 항목은 다음과 같다.

1. `chunk_kl:122–132`는 위치 범위·중복·boolean 감독 mask를 보지만 `[0,2]` 같은 비연속 위치나 같은 mask 안의 두 assistant turn을 구분하지 않는다. 정렬 helper에서 **연속 native chunk, 동일 prefix/continuation bytes, 같은 turn, special 경계, raw→shifted index**를 증명한 영수증이 필요하다. core의 위임 설계 자체를 오류라고 단정하지 않되, 임의 위치 목록을 올바른 ALM 정렬로 받아들이지 않는다.
2. `target_nll:35`의 `hidden[...,0]*0`은 finite hidden일 때만 masked 위치의 정확 0을 보장한다. PAD/비감독 위치 hidden이 NaN이면 `0*NaN`도 NaN이다. 이 사건은 기존 backbone/PAD 수치 실패로 분류하고, KD cache 불량이나 ALM 효과 음성과 섞지 않는다. 마스크가 수치 안정성을 고쳤다는 주장도 금지한다.
3. `qS=0`의 로그 `-inf`는 입력 거부 대상이다. 유한한 매우 작은 logq를 exp한 수치 underflow와 sampler의 유한 floor는 별개다. API/parser/cache→학습 입력의 전체 경로에서 sentinel/불변 검증 실패를 확률 0으로 치환하지 않는다. `-1e30`은 새 유효성 guard이지 확률 보정이나 의미 품질 기준이 아니다.
4. `qS=1,qT<1`의 무한 KL은 맞는 수학적 경계다. 다만 FP32 CE가 작은 양의 NLL을 0으로 반올림한 경우도 같은 곳에 도달하므로 현재 예외 이름처럼 exact/rounded를 구분 가능한 raw evidence로 남긴다. 임의 epsilon clipping으로 loss를 유한하게 만들어 PASS하지 않는다.
5. 계획의 동일 분포 gradient=0은 **`0<q<1` 내부의 logq 좌표**에 한정해야 한다. 현재 `qS=qT=1` 시험의 logqS 한쪽 미분 `−1`은 의도된 경계값이며 내부 oracle와 모순되는 실패가 아니다. 거의 같은 분포의 cancellation·내부/끝점·zero target/zero KD·EOT-only·마지막 잘린 chunk는 별도 분류가 유용하다.

정적 caller 검색에서 이 core의 호출은 당시 합성 시험 안에서만 확인했다. 따라서 실제 고정1024 학생 학습기 접속, mixed precision/전체 gradient accumulation, 실제 cache 정렬·교사값 검증은 여전히 `NOT_RUN`이다.

### 13.3 좁힌 TRAIN QA 선별안의 적합성과 leakage 한계

총괄의 수정안은 V3 전량이나 출처가 불명한 669행을 학습시키는 안이 아니다. `meta.source=explicit_public_context_qa`, `wrapper_view=0`에서 기존 KorQuAD/SQuAD **TRAIN** 원천의 문자 검산이 있는 문맥 QA만, 원천 문항당 한 번, hash 순서·한영 동수·학생 길이와 짧은 답 cap으로 동결하는 안으로 이해했다. 이 범위는 불명 SFT 혼합보다 새 binary 신호의 대조에 적합하다. 다만 선별 파일을 실제 검산하거나 의미 정답을 전수 확정한 것은 아니다.

- `answer_start`로 원문 substring을 확인하는 것은 기계적 span 일치다. 질문에 대한 적합성·완전성·유일 정답·최신 사실을 보장하지 않는다. 실제 builder는 `answers[0]['text']`를 assistant로 택하므로 다른 허용 alias의 teacher 우도가 높은 경우도 있다. teacher가 이 reference를 덜 확신한다고 정답 오류로 자동 판정하지 않는다.
- wrapper 0 하나만 남겨도 같은 context의 다른 질문·원천 복제·유사 문맥이 남을 수 있다. 문항 root, context ID, 원 source SHA/QA ID의 소유 단위를 구분한다. parent가 정한 V3 val root와 context 제외는 모두 필요하다. builder에 이미 있는 정규화 문맥·문항·같은 언어 연속 구간 overlap 검사를 새 동결본과 연결할 수 있으나, 이것도 모든 의역·번역 중복의 부재 증명은 아니다. 원문을 정규화한 텍스트로 교체하지 않는다.
- 단지 `meta.split=train`을 믿는 대신 원천 TRAIN 계보와 현 V3val/원천 held-out 제외 영수증을 보존한다. 새 단계의 비중복은 초기 checkpoint가 과거에 어떤 자료를 보았는지까지 소급 보증하지 못한다. 이미 V3에서 본 자료라면 **반복 노출 하의 loss 기여 대조**이지 새 지식 원천 유입 실험이 아니다.
- `assistant<=64`의 단위가 학생 native target 수인지, EOT 포함인지 명시한다. 학생 1024 이하여도 교사 native prompt+reference 길이는 다르다. 실제 렌더와 가능한 window/truncation 뒤 답 근거·질문·정답이 온전히 남아 있어야 한다. 원천 문자 offset이 원문에서 맞았다는 것만으로 잘린 학습 입력의 적합성을 대신하지 않는다.
- 한영 **행 수**는 CE target 수·KD chunk 수·bytes·교사 요청 수가 아니다. cap/정렬/오류별 거절 수, 언어별 CE/KD 실제 분모와 KD 미포함 target 수를 별도 기록한다. chunk 평균은 여러 chunk로 갈리는 행/언어에 더 많은 항을 준다. 한영 가중치를 자동으로 보정하면 다른 독립변수가 되므로 별도 선택 없이 변경하지 않는다.
- hash 선정은 teacher 점수·성공·속도를 보기 전에 동결한다. 16행 canary에서 느리거나 실패한 행을 쉬운 행으로 교체하고 원 실패를 지우면 비용/유효성 추정이 편향된다. 성공·실패·미시도·부분 저장을 최초 16행 분모에 보존한다.

이 자료가 검토하는 능력은 짧은 명시 문맥 QA에 제한된다. 답을 문맥에서 조건부 추출하는 대조를 자유 대화·장문 추론·일반 지능·한국어 전반으로 확대하지 않는다. 공식 Core6/BabyLM 자료와 namespace를 분리하며 평가 문항·정답은 teacher/cache/Luna로 보내지 않는다.

### 13.4 GradMag OFF에서 단일 효과를 해석하는 방법

다음은 원문 수치를 옮긴 것이 아니라, 현재 코드 목적함수를 손으로 미분한 해석이다. `s=C_S/tau`, `t=C_T/tau`, `qS=exp(s)`, `qT=exp(t)`라 두면 내부에서

`d KL(T||S)/ds = (qS−qT)/(1−qS)`

이고 chunk 안의 학생 target NLL 각각에는 같은 계수

`d KL/d NLL_i = (qT−qS) / [tau·(1−qS)]`

가 전달된다. 그러므로 `CE/N_CE + lambda·KL/N_chunk`의 해당 NLL 계수는

`1/N_CE + lambda/N_chunk · (qT−qS)/[tau·(1−qS)]`

다. 미포함 target은 CE 항만 받는다. 긴 chunk와 짧은 chunk의 가중치, 언어별 분모, temperature가 실효 신호를 함께 바꾼다. 큰 tau에서 항상 강해진다는 주장이나 CE/KD scalar loss가 비슷하니 gradient도 같다는 주장은 성립하지 않는다. teacher가 reference에 덜 확신하는 `qT<qS`이면 KD가 CE 반대 방향으로 NLL을 올릴 수도 있으며 이는 calibration 목적의 결과이지 온라인 진위 검증이 아니다.

현 단계에서 GradMag를 새로 구현하는 대신, 별도 허용된 TRAIN-only 진단에서 같은 parameter 집합의 `||lambda·gKD||/||gCE||`, cosine, finite 여부와 KD coverage를 기록하는 선택지가 있다. 이 진단은 자동 계수 적응이 아니며 GradMag 구현이라고 부르지 않는다. 공유 `emb.weight`/`emb_up` gradient에는 입력 경로와 head 경로가 함께 섞이므로 그것을 순수 마지막 독립 head의 GradMag norm이라고 표기하지 않는다. 학습 hidden을 detach해 싸게 얻은 head-only 진단 역시 전체 학습 gradient와 구분한다.

현재 고정 tau/lambda와 OFF 항목을 사전 동결하고, 약한/강한 gradient 신호, 데이터 문제, API 비용을 따로 보고해야 한다. 결과가 작거나 음성이어도 **이 축약 조건의 음성**이지 GradMag 포함 ALM 전체의 반증은 아니다. 반대로 짧은 TRAIN KL 감소만으로 일반화 이득을 주장하지 않는다. [원문 gradient balancing의 범위](https://arxiv.org/html/2503.20083v4)

### 13.5 비용을 적게 쓰는 확인 순서와 회계

1. **teacher 실행 전** 새 TRAIN 선별본/원천·row 순서/SHA, val 제외, 길이 cap, assistant·EOT 규약을 동결한다. 이미 허용된 byte 도구의 원문 round-trip과 공통 chunk/shift 계약이 먼저다. 실제 helper 검산 결과는 소유 담당과 총괄이 회수한다.
2. 학생 64cap 대신 **교사 native target 수 K와 해당 첫 target의 prefix 길이 P**로 scoring 요청 예산을 센다. reference prefix를 매번 새로 처리하는 `cache_prompt=false`에서 K개 연속 target은 대략 `K·P + K(K−1)/2`개의 prefix token 위치를 재처리하고 K번 HTTP 요청·K개 추가 생성 처리가 필요하다. 이는 소스 호출 방식에서의 비용식이지 실제 초/토큰 실측은 아니다. 짧은 정답은 K를 줄이지만 긴 문맥의 P는 남는다.
3. 16행 canary에서 교사 기동·자산 해시, tokenize/정렬, 실제 성공/실패 요청, prefill/decode, 저장 시간을 가능 범위에서 분리한다. 최초 결과가 나오기 전의 장시간 해시/기동도 hard deadline 예산에 포함한다. 이전 14요청의 기술 canary를 전체 TRAIN throughput으로 복사하지 않는다.
4. 필요한 공통 chunk의 교사 target만 채점하더라도 각 요청의 prefix에는 **그 target 이전의 모든 정확한 reference native ID**가 있어야 한다. 채점하지 않은 이전 token을 빼거나 교사 자유 생성으로 대체하면 다른 조건부 확률이다. top-k 누락을 0으로 채우지 않는다. 20/100/200 불변 검산과 실제 reference scoring은 서로 다른 회계이며 검증된 forcing 조건을 쓸 때 매 target에 3중 검산이 필수인 것은 아니다.
5. state/slot prefix 재사용은 잠재 가속안이지만 hybrid/GDN/MTP 조건의 정확성을 추가 대조해야 한다. `cache_prompt=true`만 켜서 같은 source라고 가정하지 않는다. 현재 cache 재사용 OFF·MTP OFF의 검증 계약을 효과 실험 도중 바꾸지 않는다.
6. teacher logp cache는 동일 teacher/engine/tokenizer/요청 의미가 고정되면 CE/ALM 비교 전에 한 번 확보할 수 있다. 저장은 새 shard와 provenance로 남기고 파일당20MB 제한을 지킨다. 본 학습과 무관한 원본 API 응답을 생략해 성공으로 보이게 하지 않는다.
7. 후속 matched-exposure 대조는 **같은 새 선별본·부모 weight·optimizer 초기 상태·seed/row 순서·update/target 노출·head/ckpt 경로**에서 CE-only 대 CE+binary KL만 다르게 한다. 기존 다른 풀·예산의 CE 결과는 이 대조군을 대체하지 못한다. CE-only도 같은 per-token NLL 경로에서 lambda 0을 쓰는 안은 loss 외 경로 교락을 줄일 수 있으나 실제 접속은 총괄의 별도 작업이다.
8. student 학습 비용과 추가 teacher scoring 비용을 따로, 그리고 합쳐 보고한다. 같은 update 수의 단일효과 비교와 teacher precompute까지 포함한 같은 총 벽시계 경쟁은 다른 질문이다. 둘을 동시에 고정했다고 쓰지 않는다. 시간 부족으로 cache feasibility에서 끝나도 미실행 학습/일반화 효과를 추정 점수로 채우지 않는다.

### 13.6 지금 선택할 세 경로와 권고

| 안 | 내용 | 장점 | 단점·영향 | 수행비용 |
|---|---|---|---|---|
| A — bounded cache canary | 동결16행의 provenance/byte/교사 raw target scoring 비용·실패를 회수하고 종료 | 새 loss를 쓰기 전 자료/API/시간 문제 분리 | 학습/일반화 효과는 전혀 판정 못 함; 새 TRAIN cache·연구 기록만 영향 | 낮음~중간, teacher K/P 실측에 의존 |
| B — 선결 후 matched CE/ALM | A와 수치/실제 학생 접속 확인 뒤 fixed tau/lambda의 두 팔을 같은 노출로 비교 | 새 binary 신호의 한정된 기여를 식별 가능 | GradMag OFF·짧은 QA의 한계; 새 학습 권한/시간/평가 계획 필요 | 중간~높음, 두 학습 팔과 독립 평가 |
| C — full recipe/엔진 최적화 확장 | GradMag·debias·추가 teacher backend/상태 재사용까지 별도 검산 | 논문 충실도나 총비용 개선 질문을 더 넓게 다룸 | 여러 축이 동시에 늘어 현재 단일효과와 분리 필요; 설치/모델/시간 권한 추가 가능 | 높음, 이번 제한시간의 우선 대상 아님 |

**현재 권장: A를 먼저 닫고 실제 비용·신호를 본 뒤 B의 가능 여부를 총괄이 판단한다.** 자료 cap을 줄여 비용이 들어오지 않거나 q1/API/정렬 실패가 남으면 A의 음성/미완료를 보존하고 학습은 열지 않는다. C를 서둘러 끼워 넣거나 CE-only 결과를 ALM 실행으로 대체하지 않는다.

이 검토는 `SOURCE_REVIEW_ONLY`다. torch/모델/GPU/실제 시험·교사 요청/학습/패키지 설치는 이 담당이 실행하지 않았다. `exp-preflight`의 자동 registry 조회·태그 충돌·실제 토큰/VRAM 검산도 현재 실행 금지 범위에 따라 수행하지 않았으므로 전체 preflight PASS를 선언하지 않는다. 본 절은 총괄 소유 계획·결과·기준표를 대신하지 않으며 보호 원천·CP·평가자료·기존 source는 변경하지 않았다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 14. BabyLM 2026 Strict의 BLiMP full zero-shot만 여는 최소 경로

### 14.1 현재 결론·추가 승인된 source만의 반입

**현재 상태에서 공식 BLiMP 모듈을 그대로 추가 설치 없이 실행할 수 있다고 확인하지 못했다.** 구체적인 알려진 blocker는 `compute_results.py:9`의 무조건적인 `scipy.stats.spearmanr` import이며, KST 07시대 읽은 `tlm_torch` 설치 metadata에 SciPy가 없었다. BLiMP 계산 자체는 SciPy를 쓰지 않지만 공식 파일의 import 선결은 남는다. TinyLM은 HF 모델/processor 계약에 맞춘 adapter도 아직 필요하다. 공식 소스를 고쳐 import를 제거하거나 기존 scorer를 공식이라고 재명명하는 방식은 이 결론을 해소하지 못한다.

총괄의 추가 승인 범위는 공식 source 취득·방법 검토뿐이다. 새 평가 코드 구현, source 실행/등록, torch/transformers/tokenizer import, 모델/GPU/학습/평가, BabyLM 전체 requirements 설치는 하지 않았다. `impact-analysis`의 다안 비교를 적용하되 공유 계획·결과 정본은 총괄 소유로 유지한다.

공식 `babylm-org/babylm-eval` main의 조회 시 commit은 **`6f825c291e2c4c78ad33b1935fd64d45f52642dc`**, commit date는 `2026-07-19T06:49:13Z`, Git tree는 `099787c0e6e8960ff7951bb02c8465bc2dd6f42d`였다. 전체 5,532파일·80,870,015 B를 받지 않고 다음 새 폴더에 필요한 source/readme/requirements/shell 14개와 `strict/LICENSE` 1개만 받았다. [공식 고정 commit](https://github.com/babylm-org/babylm-eval/commit/6f825c291e2c4c78ad33b1935fd64d45f52642dc)

`data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp/`

총 **15 source 파일·130,686 B**이며 upstream Git blob SHA1·bytes와 실제 SHA256을 각각 확인했다. [최초 14파일 manifest](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp/manifest.json)의 SHA256은 `75b0dae39e1938073be5a7275e1d805fb2e64f78bc42cc3c3110b1ba6742b9a5`다. 이를 덮어쓰지 않고 [LICENSE 추가 영수증](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp/license_addendum_manifest.json)을 별도로 남겼다. 추가 영수증 SHA256은 `65901b3ed1e9b9cc3e88dcc12df91527e2afd440060150ac18fdf145b13be54f`, 15파일 결합 source digest는 `69cf93b56d65e8bef531a18a0ed77381f409830296437d4c24bed98c0981b748`다. 각 digest 정의는 영수증에 명시했다.

`strict/LICENSE`는 Apache-2.0, copyright 2025 BabyLM Organization Team을 명시한다. 이는 **평가 코드**의 권리 표기이며, 앞서 받은 HF 평가자료 repo의 배포 LICENSE 미명시를 해소하거나 그 자료의 재배포권을 부여하는 근거로 쓰지 않는다. source와 자료의 출처/권리를 분리한다. [고정 LICENSE](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/LICENSE)

### 14.2 causal BLiMP의 정확한 점수·BOS/EOS·mask 계약

이 절의 source 경로는 모두 위 commit의 `strict/evaluation_pipeline/sentence_zero_shot/` 아래다. 원본은 수정하지 않았다.

| 항목 | 고정 source의 실제 동작 | 기존 scorer를 쓸 때의 위험 |
|---|---|---|
| 파일/후보 | `read_files.py:35–41,92–130`: data_path의 각 JSONL을 읽고 good/bad 순서, label0, prefix None, completion=문장 전체 | 일반 MC prompt/보기 문자열을 넣는 과제가 아님. chat wrapper/번역/정제를 추가하지 않음 |
| 토큰화 | `dataset.py:25–34,69–80`: AutoProcessor 또는 fast-tokenizer fallback이 **전체 sentence**를 한 번 처리, offsets/attention mask 요청 | source는 `add_special_tokens=False`나 BOS/EOS 일괄 ON/OFF를 강제하지 않음. 모델 processor 규약을 따름 |
| phrase mask | `dataset.py:89–100`: completion의 문자 범위와 겹치는 token을 mask1 | BLiMP는 전체 문장이지만 offset `(0,0)` special token은 보통 제외됨. token 개수/문자 길이 정규화 없음 |
| shift | `dataset.py:428–438`: inputs=`tokens[:-1]`, targets=`tokens[1:]`, phrase mask도 `[1:]` | 첫 native token 자체는 점수화되지 않음. BOS가 있으면 뒤의 첫 text token을 채점하지만 BOS가 없으면 첫 text token도 빠짐 |
| causal 점수 | `compute_results.py:105–132`: 각 후보를 독립 forward, `log_softmax(logits/temperature)`에서 target 값을 gather하고 phrase mask와 곱해 **합** | BLiMP는 mean NLL·token/문자/byte 정규화가 아님. `acc_norm`을 끼워 넣지 않음 |
| EOS | score 여부는 tokenizer 출력과 offsets에서 결정 | `(0,0)` EOS는 mask0이면 채점하지 않음. 별도 EOS 우도를 덧붙이지 않음 |
| temperature | `run.py:36–38,62–71`: 기본 1.0 하나만 사용 | max_temperature를 주면 sweep 후 같은 평가 정확도 최댓값을 선택함(`run.py:164–177`). 기본 T1과 구분하고 무보고 tuning 금지 |
| 출력/dtype | `compute_results.py:107–120,126`: `input_ids`, `attention_mask` 인자와 tuple[0] 또는 dict['logits']를 기대; logits dtype을 명시 FP32로 올리지 않음 | TinyLM Tensor 반환·`tokens` 인자와 직접 호환 아님. 모델/engine precision·TF32·저장 dtype를 별도로 기록 |
| 길이/패딩 | `dataset.py:428–438,597`: 오른쪽 padding, shuffle=False; tokenizer 호출에 truncation/max_length 지정 없음 | 임의 1024 초과 건너뛰기·앞 자르기를 공식 full과 합치지 않음. 기본 batch64의 비용/NaN 안전도 미검증 |

따라서 “문장 전체 sumLL”은 **processor가 만든 token sequence의 next-token 예측 가능 위치 중 phrase mask가 1인 부분의 합**이라는 뜻이다. 예컨대 BOS 없는 `[w0,w1,w2]`는 `log p(w1|w0)+log p(w2|w0,w1)`이고, `[BOS,w0,w1,w2]`이면 첫 text token `log p(w0|BOS)`도 포함된다. 기존 newline prefix를 붙인 우도는 이와 다르다. 이 예는 코드의 손계산 해석이며 모델 실행 결과가 아니다. [dataset source](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/evaluation_pipeline/sentence_zero_shot/dataset.py), [causal scoring source](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/evaluation_pipeline/sentence_zero_shot/compute_results.py)

**동점과 비정상값은 중요한 별도 계약이다.** `compute_results.py:65–75`는 NaN을 `−inf`로 바꾼 다음, 최댓값 동점이면 `torch.randint`로 임의 후보를 고른다. good가 앞이라 자동 정답으로 처리하거나 모든 동점을 오답으로 처리하지 않는다. source에 seed 설정은 없고 `read_files`의 디렉터리 순회도 명시 정렬이 없으므로 정확 재현에는 순서·random state/seed·tie 건수 기록이 필요하다. 두 후보가 모두 NaN인 경우에도 `−inf` 동점이 될 수 있으므로, 숫자 accuracy가 출력됐다는 사실만으로 유효한 모델 평가라고 판정하지 않는다. nonfinite/빈 scoreable mask/미완료 건수는 companion 유효성 증거로 분리하고 임의로 정상 우도나 0점으로 채우지 않는다.

### 14.3 full 표본 분모와 공식 그룹 평균

이미 승인·반입한 자료 revision은 `8d52da9424a9ff30b9e8266c4f751aba9c504233`로 유지했다. 이번에는 BLiMP/supplement 72파일만 원 bytes SHA를 기존 manifest와 재대조하고, 문장 본문을 출력하지 않는 행/UID metadata 검사를 수행했다. 원자료 변경·질문/정답의 교사/Luna 전달은 없다.

| 별도 평가 디렉터리 | 실제 파일/UID 수 | 실제 문장쌍 수 | UID별 최소~최대 쌍 수 |
|---|---:|---:|---:|
| `evaluation_data/full_eval/blimp_filtered/` | 67 / 67 | **59,875** | 681~986 |
| `evaluation_data/full_eval/supplement_filtered/` | 5 / 5 | **5,218** | 64~3,867 |

blank line은 없었고 BLiMP UID와 파일 stem 불일치는 0이었다. 따라서 이 snapshot은 원 BLiMP의 관용적 `67×1000=67,000`이나 fast subset으로 계산하면 안 된다. supplement는 별도 source 분기에서 UID=file stem으로 만든다. 두 디렉터리를 같은 `--task blimp`로 호출하더라도 `scripts/eval_zero_shot.sh:16–17`처럼 **별도 실행·별도 결과**다. 72개를 한 번에 micro-average해서 BLiMP라고 부르지 않는다.

`compute_results.py:77–81`은 UID/field/linguistics_term별 correct/total을 집계한다. `run.py:83–94`의 주 평균은

`BLiMP(%) = (1/67) · sum_uid [100 · correct_uid / total_uid]`

이다. **그룹별 정확도 단순평균**이지 59,875쌍의 micro accuracy도, 넓은 field 몇 개의 평균도 아니다. UID별 표본 수가 실제로 다르므로 둘은 일반적으로 다르다. supplement도 같은 규칙의 5 UID macro 평균이다. 모든 요청 문장쌍의 raw score/선택·UID/원천행 순서와 실제 완료/제외/비정상 분모를 보존해야 full 여부를 판정할 수 있다. 새 모델 결과는 아직 하나도 없다. [공식 집계 source](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/evaluation_pipeline/sentence_zero_shot/run.py)

### 14.4 실제 import 선결과 현재 환경 — 일괄 설치 근거가 아님

아래 현재값은 `/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages`의 distribution metadata만 표준라이브러리로 읽은 것이다. 패키지를 import하거나 실행 호환성을 시험하지 않았다. 총괄의 별도 Core6 설치가 진행 중이므로 후속 시점에는 현재값을 다시 확인해야 하며 그 승인 범위를 이 담당이 넓히지 않는다.

| 명시 import/소유 파일 | 현재 metadata | BLiMP에 필요한 이유·현재 판단 |
|---|---|---|
| torch / run·dataset·compute | 2.10.0+cu130 | forward/자료 batch/LL·집계. 설치 존재만 확인 |
| transformers / run·dataset·package init | 5.14.1 | AutoModel/AutoProcessor·tokenizer fallback. 모델별 lazy/optional import 호환 `NOT_RUN` |
| datasets / read_files:8 | 5.0.0 | BLiMP는 로컬 JSONL이지만 top-level import가 있음 |
| aiohttp / read_files:9 | 3.14.3 | images=None인 BLiMP도 top-level import; 실제 이미지 다운로드 안 함 |
| tqdm / compute:12 | 4.70.1 | progress loop의 top-level import |
| **scipy** / compute:9 | **미설치 metadata** | `spearmanr`가 BLiMP 경로에서 쓰이지 않아도 무조건 import됨. 원 source 그대로 실행하려면 알려진 부족 필수 |
| stdlib | Python 3.10.19 | pathlib/json/argparse/typing/collections/math 등 |

기존 metadata로 numpy2.2.6/tokenizers0.22.2/huggingface_hub1.24.0/Pillow12.3.0/safetensors0.8.0도 확인했다. 이는 Transformers/datasets의 모든 전이 의존성이나 AutoProcessor 성공을 보증하지 않는다. 공식 strict requirements의 `scipy==1.15.2`, torch2.7.0/transformers4.51.3 등은 원 개발 환경의 전체 freeze다. 이번 판독만으로 전체 버전 교체·다운그레이드·설치를 권고하거나 시행하지 않는다. **BabyLM package의 pip 설치/등록 자체는 이 경로의 필수 아님**이며 `strict/` source의 모듈 경로와 정확한 local data_path가 필요하다. AutoModel/processor에는 `trust_remote_code=True`가 들어 있으므로 후속 모델/코드 revision·로컬 자산만 사용한다는 경계도 별도로 확인해야 한다. Core6용 lm_eval 설치는 이 별도 pipeline의 source/adapter 검증을 대신하지 않는다.

### 14.5 기존 최소쌍 도구 재사용의 정확한 경계

읽은 `scripts/p106b_minimal_pair_benchmark.py` SHA256은 `1cee5d48c1f32358337f16d986afa538468fce5ac31da93d8e18683b088cabbe`, `scripts/eval_bench_suite.py`는 `7f38b4828745ff3115f5f6ed8e79f07473f5769918bdac7f47ae5b5b52f1b129`다. 다음 차이는 source에서 직접 확인했고 원 도구는 수정/실행하지 않았다.

| 기존 도구 | 재사용 후보 | 공식 BLiMP로 그대로 재사용 불가한 부분 |
|---|---|---|
| minimal_pair `protocol:113–129` | 실제 tokenizer·CP·정밀도·route의 provenance 고정 | explicit newline 또는 지정 BOS prefix + separately encoded sentence; 공식 processor/BOS/offset 규약과 다름 |
| `seq_ce:427–444`, `make_scorer:180–191` | 유효 native ID 전체를 같은 모델로 teacher-force하는 수학적 기본 아이디어, strict FP32 loader | prefix를 추가해 모든 sentence token을 채점하며 offsets/phrase mask 없음. 기본 seq_ce에는 autocast도 있어 minimal_pair의 FP32 wrapper까지 구분 필요 |
| `_decision:147–148`, `summarize:211–251` | tie/skip/raw score를 독립 보존하는 안전장치 | ties는 오답이며 context 초과는 제외. 공식 random tie와 UID macro 분모를 그대로 재현하지 않음 |
| ShardWriter·해시·원본보존·strict route | 새 평가 namespace의 저장/감사 도구 | 여섯 필드의 experimental 입력 schema/phenomenon과 BabyLM UID/field metadata가 다름. 단순 포맷 변환만으로 scoring parity가 되지 않음 |

TinyLM `TiedMLPTransformer.forward`는 현재 `tokens`를 받아 Tensor logits를 반환하고 `input_ids`/`attention_mask` 인자를 받지 않는다. 공식 `compute_causal_results`는 HF형 인자·출력을 요구하므로 원 torch 모델을 그냥 넘기는 것으로는 접속되지 않는다. 추후 별도 허용된 adapter는 원 CP·BOS/processor/offsets·native head·ternary route·attention/padding·dtype·UID/ranking을 보존해야 한다. batch1로 padding 영향을 줄이는 것 역시 접속/score parity를 자동 입증하지 않는다. 원 source를 수정하지 않는 별도 adapter와 합성/작은 parity 검증이 필요한 **설계 항목**이며 이번 구현 0이다.

또한 공식 `run.py:154–155,176,140`는 같은 출력 경로가 있으면 report/predictions를 `w`로 쓸 수 있고 파일당20MB guard도 없다. 후속 실행은 새 namespace·기존 파일 보존·분할/크기 계약을 별도로 닫아야 한다. 전체 shell을 실행하면 BLiMP 외 EWoK/다른 과제/reading도 호출하므로 이번 최소 범위의 입구로 쓰지 않는다.

### 14.6 대회 트랙·TinyLM 600M·허용 가능한 보고명

2026 공식 트랙은 Strict, Strict-Small, Multilingual이며 standalone Multimodal/Interaction은 제거됐다. strict 자료량 기준은 100M/10M **words**이고 Multilingual은 BabyBabelLM의 영어·네덜란드어·중국어 mixture와 Byte Premium 조정 기준이다. 한국어/영어 TinyLM이 BLiMP를 평가했다는 사실이 multilingual 출품 적격을 뜻하지 않는다. [현재 Guidelines](https://babylm.github.io/guidelines.html)

TinyLM의 **600M tokenizer tokens라는 pool/노출 표기만으로** strict 100M words 준수/위반을 자동 판정할 수 없다. unique corpus words, 실제 반복 노출 input/generated words, teacher/tool 계보, 허용된 중간 checkpoint가 별도다. repo 기준표의 일반 표준에서도 pool600M과 training300M은 다른 항목이므로 숫자 600M을 곧바로 실제 학습량 또는 word 수로 바꾸지 않는다. 이번 검토는 보호 학습 원천을 읽어 재계산하지 않았고 TinyLM의 대회 자격을 검증하지 않았다.

CFP v2 §4.2는 반복 노출 상한을 strict1B/strict-small100M whitespace words로 설명하지만, 같은 문서 §4.1의 external-model 문단은 100M/10M 노출 문구를 함께 사용해 해석상 충돌도 있다. 이를 편리한 쪽으로 조용히 합치지 않는다. 분포/hidden/weight를 사용하는 KD는 teacher 사전학습 자료량 산입 규정도 따로 있다. 이런 자격 문제는 benchmark를 **외부 연구 비교**로 쓰는 것을 막는 사유가 아니며, 적격성/공식 순위 주장만 별도로 보류한다. [CFP v2 §4.1–4.2](https://arxiv.org/html/2602.20092v2)

기존 strict README에는 2025 leaderboard와 옛 multimodal-track 표현도 남아 있다. 따라서 실행 함수의 채점 규칙은 고정 source로 확인하되 트랙 자격은 현재 Guidelines/CFP와 분리해 읽는다. BLiMP59,875쌍을 유효하게 완주한 뒤에도 보고명은 **“BabyLM2026 Strict 공개 filtered BLiMP full zero-shot, 고정 source/자료 revision, 대회 자격 미검증”** 정도가 맞다. supplement·COMPS·Entity·EWoK·GlobalPIQA·human-likeness·fine-tuning·중간 checkpoint/hidden-target 제출까지 완료했다는 뜻이 아니다. 현 상태에는 그 BLiMP 실제 결과도 없으므로 `SOURCE_PINNED / DATA_HASH_AND_COUNTS_VERIFIED / MODEL_EVALUATION_NOT_RUN`으로 남긴다.

### 14.7 세 경로와 최소 권고

| 안 | 내용 | 장점 | 단점·영향 | 수행비용 |
|---|---|---|---|---|
| A — 공식 최소 source+별도 adapter | 원 source를 보존하고 SciPy/현재 import 선결을 총괄 승인 범위에서 닫은 뒤, HF형 모델은 직접 경로·TinyLM은 별도 adapter 검증 | 공식 점수/집계와 가장 가까움; 전체 pipeline 설치 불필요 | 현재 SciPy 부족·TinyLM 접속/실제 parity는 미완료; 구현/실행 권한 별도 | 중간, 핵심 source 수 개와 adapter·회귀 |
| B — 무설치 독립 재현 | 현재 Torch로 위 규약을 별도 구현하고 공식 함수와 parity를 나중에 대조 | 불필요한 import 의존을 피하는 대안 | 새 평가 코드가 필요해 이번 승인 밖; parity 전에는 `LOCAL_REPRODUCTION` | 중간~높음, endpoint/tie/UID/processor 회귀 책임 |
| C — 기존 experimental 최소쌍 유지 | 현재 scorer 규약과 기존 결과를 그대로 보존 | 추가 구현/설치 부담이 가장 작음 | 공식 BabyLM BLiMP full 점수를 제공하지 못함; 과거 점수 승격 불가 | 낮음, 해석 범위 제한 |

**권장: 지금은 A의 source/자료/방법 고정까지만 회수하고, 총괄이 현재 설치 metadata와 접속 선결을 확인해 다음 단계를 정한다.** SciPy 하나의 알려진 부족 때문에 BabyLM 전체 requirements를 설치하지 않는다. B는 별도 구현 허가가 있을 때만 검토한다. 이번 실제 완료는 source15개 추가 반입·해시 및 기존 BLiMP/supplement 분모 감사·본 절 기록이며, 평가 코드/원자료/모델/CP 수정과 실제 평가/설치/등록은 0이다.

## 15. 추가 승인된 Core6 제한 설치의 독립 원형·metadata 감사

### 15.1 범위와 결론

총괄이 사용자 승인 아래 수행한 **정확 6종 + lm_eval, `--no-deps` 설치**를 읽기 전용으로 감사했다. 이 담당은 설치·삭제·수정·package import·모델/GPU·평가·Git을 실행하지 않았다. 네트워크는 지명된 6개 PyPI exact-release JSON metadata만 조회했고 추가 asset을 다운로드하지 않았다. 실행 중인 총괄 GPU adapter에는 관여하지 않았다.

결론은 **승인된 local distribution 집합·wheel 출처·원형 source와 설치된 harness 코드/YAML의 byte 일치가 확인되었다**는 것이다. 동시에 **배포 전체 base 요구사항은 7종 부족으로 미충족**이다. 이를 공식 평가 전체/품질 PASS나 완전히 의존성이 닫힌 독립 환경으로 확대하지 않는다.

허용된 [독립 감사 JSON](/home/uranus/tinyLM/handoff/audit/WIP_20261023_EVAL_INSTALL_AUDIT.json)을 새 파일로 보존했다. 실제 18,594 B, SHA256 `f365c2a36f8a32f2da6fb5cb4c0aa57964490f09b66cfff477d41158cfc2c4b3`이며 표준라이브러리 JSON 재파싱·허용 파일 크기를 확인했다. 감사 시각은 KST 2026-10-23 07:16~07:17이다. 모든 해시·선택 receipt 필드·개별 PyPI URL·현재 metadata·제외 범위는 이 JSON이 소유한다.

### 15.2 승인 설치 범위와 base 분리

대상 local metadata 경로는 `data_cache/p106b_official_eval_runtime/core6_env_20261023/lib/python3.10/site-packages`다. distribution metadata를 표준라이브러리로 직접 읽은 집합은 아래 **7개뿐**이며 추가 이름·버전 불일치는 0이었다.

| local distribution | 실제 version | 지명 wheel의 실제 bytes | exact-release SHA·size·wheel metadata |
|---|---|---:|---|
| sacrebleu | 2.6.0 | 100,785 | 모두 일치 · [PyPI JSON](https://pypi.org/pypi/sacrebleu/2.6.0/json) |
| portalocker | 4.4.1 | 129,702 | 모두 일치 · [PyPI JSON](https://pypi.org/pypi/portalocker/4.4.1/json) |
| tabulate | 0.10.0 | 39,814 | 모두 일치 · [PyPI JSON](https://pypi.org/pypi/tabulate/0.10.0/json) |
| colorama | 0.4.6 | 25,335 | 모두 일치 · [PyPI JSON](https://pypi.org/pypi/colorama/0.4.6/json) |
| lxml | 6.1.3 | 5,296,830 | cp310·manylinux x86_64 exact filename까지 일치 · [PyPI JSON](https://pypi.org/pypi/lxml/6.1.3/json) |
| accelerate | 1.15.0 | 394,295 | 모두 일치 · [PyPI JSON](https://pypi.org/pypi/accelerate/1.15.0/json) |
| lm_eval | 0.4.14.dev0 | 로컬 고정 source build | PyPI wheel 설치가 아니라 아래 byte 대조와 pip direct_url로 추적 |

6개 wheel 합계는 **5,986,761 B**다. 실제 파일 SHA256·size를 pip six receipt와 각 정확 버전의 공식 PyPI `urls` 항목에 대조했다. 모두 같은 filename·SHA256·bytes이고 yanked=false이며, wheel ZIP 안의 distribution name/version도 일치했다. wheel은 읽기만 했고 재설치·압축 해제는 하지 않았다.

`core6_install_six_receipt.json`은 정확 6개, `core6_install_harness_receipt.json`은 lm_eval 하나의 설치를 기록한다. 각각 SHA256은 `8d7b15931af222514d631cde3d4e06c20b14b318bbb4f8f08d746977c44d754e`, `807247cfa489731fd912dd61dadd14af4234675aac4ad1d046e540192cca3eed`다. 전체 description/사용자 환경을 출력하지 않고 필요한 이름·버전·파일 출처·해시만 감사 JSON에 보존했다.

기존 `/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages`에는 이 **7종 모두 등록 metadata가 없다**. 이것은 현재 이 7종이 base에 추가되지 않았다는 확인이며, base 전체 파일/모든 package의 역사적 불변성을 전수 입증한 것은 아니다. `pyvenv.cfg`는 `include-system-site-packages=true`라 기존 Torch/Transformers 등의 base package를 상속한다. 따라서 **별도 local 설치 범위**와 **완전 독립·self-contained 환경**을 혼동하지 않는다.

### 15.3 공식 archive·보존 source·build copy·installed package 대조

기준은 기존 고정 commit `d6de81643928d653435c431bae19945d41d32520`의 `official_source.tar.gz`다. 표준라이브러리 tar stream으로 regular member의 bytes를 읽고 각 SHA256을 계산했으며 디스크 재추출·원본 수정은 0이다.

| 비교 | 기대/실제 파일 수 | 누락 / 추가 / 내용 변경 | 결과 범위 |
|---|---:|---:|---|
| archive 모든 regular member ↔ 보존 `source/` 모든 파일 | 16,415 / 16,415 | 0 / 0 / 0 | 전체 source byte 일치 |
| archive `lm_eval/**/*.py,*.yaml,*.yml` ↔ build copy 같은 package 범위 | 14,739 / 14,739 | 0 / 0 / 0 | build 복사본의 code/YAML 원형 일치 |
| 위 archive package 범위 ↔ installed site-packages의 `lm_eval/` | 14,739 / 14,739 | 0 / 0 / 0 | 설치된 code/YAML 원형 일치 |

원 source 총 bytes는 **13,907,399 B**이며 archive SHA256 `c60d18c7dcedb03fdd95d43cd2f0bc4a575862a64eb8c9b390e96f5129e442a4`도 최초 반입 기록과 일치했다. archive nonregular member와 해당 source/package symlink는 없었다. 이는 기존 공식 취득 archive와의 내용 일치이며 별도 upstream 전자서명 검증은 아니다.

최초 acquisition tree hash는 path에 `source/` prefix를 포함하는 정의다. 같은 정의로 재계산한 값은 기존 `798fa248b3c3a2342ca733fb89ccb507e938d955fd6d7b26f8405a89af43fc54`와 일치했다. 별도 archive-vs-source 비교에서 source root 상대경로로 계산한 값 `5437008585c0dce70735c9daf18bfb56c16eeab8c4be09aa3c7e0507ab3648aa`와는 **경로 namespace가 다르다**. 이 둘의 차이를 파일 변경으로 오인하지 않도록 JSON에 정의를 함께 남겼다.

package `.py/.yaml/.yml` digest는 원 archive·build copy·installed 세 경로 모두 `e3905db08f6ddfd280c5783f844749c99e051bddf618f822587e0e9b7f134906`으로 일치했다. installed `direct_url.json`은 승인된 `data_cache/p106b_official_eval_runtime/lm_eval_build_d6de816_20261023`의 local build를 가리키며 editable install 표시가 없다. 원본 official source를 build 장소로 썼다는 주장이 아니라, **별도 build 경로와 실제 내용 대조**가 함께 남아 있다.

설치가 생성한 `.pyc`, dist-info metadata/entry-point script 및 package의 모든 비-code resource까지 archive와 같은 것으로 주장하지 않는다. 6개 외부 package의 설치 후 전체 payload나 binary 실행을 전수 검증한 것도 아니며, 여기서 확인한 것은 원 wheel 출처/metadata와 요청된 harness code/YAML 범위다.

### 15.4 남는 의존성 음성과 증거 수준

installed lm_eval의 extra 없는 `Requires-Dist`를 local+상속 base metadata에 대조하면 다음 **7종이 없다**: `evaluate>=0.4.0`, `pytablewriter`, `rouge-score>=0.0.4`, `scikit-learn>=0.24.1`, `sqlitedict`, `word2number`, `more_itertools`. 따라서 `--no-deps`의 **전체 배포 base 요구 충족은 아니다**. 특히 pytablewriter가 필요한 공식 CLI 경로와 총괄의 선택된 direct/API Core6 경로를 같은 설치 선결로 합치지 않는다.

이 담당은 `pip check`를 실행하지 않았다. 위 표시는 metadata에서 직접 확인한 미충족이며, 전체 PEP508 marker/버전 범위·모든 상속 package 의존성까지 해결한 resolver 검증이나 `pip check PASS`가 아니다. 기록은 `KNOWN_UNSATISFIED_DECLARED_BASE`로 남긴다. 임의로 부족 7종을 추가 설치하지 않았고 현재 승인 6종 범위를 넓히지 않았다.

총괄이 보고한 `prepare_harness` 실제 import와 6-task CPU 계약 PASS는 **총괄의 별도 실행 증거**다. 이 감사의 범위는 `READ_ONLY_METADATA_AND_BYTE_AUDIT`이며 GPU adapter 성공/실패, full benchmark 완주, 점수·품질·속도, BabyLM 전체 의존성/평가 완료를 뜻하지 않는다. 이번 수정은 이 문서 §15와 지정 감사 JSON 한 파일뿐이고 source/빌드/설치 환경/모델/평가자료는 읽기 전용으로 보존했다.

## 16. 공식 Core6 전량 설계의 source-only 반 검토

### 16.1 검토 대상과 현재 판정

고정 harness commit `d6de81643928d653435c431bae19945d41d32520`의 실제 `simple_evaluate`·`ConfigurableTask`·`TemplateLM`·`HFLM`과 총괄의 별도 task builder/adapter/runner를 대조했다. 후보는 사전 고정 `native595-f`, `native595-q`, `new595-broad-f`, `falcon90m`이고, 외부 모델은 `tiiuae/Falcon-H1-Tiny-90M-Base` snapshot `7994372e93b62822ae25f8bfb19f653649cea3a3`다. 모델 수/순서를 실제 점수로 바꾸는 설계가 아니다.

이번에는 **읽기 전용 방법·원형 검토만** 수행했다. `impact-analysis`와 `exp-preflight`의 비교 조건·대조군·증거 구분을 적용하되, 명시적 실행 금지에 따라 registry 도구/회귀/CPU oracle/모델·tokenizer·torch·lm_eval import/GPU/평가를 실행하지 않았다. 이것을 자동 preflight PASS나 실제 benchmark 성공으로 표시하지 않는다. 총괄의 회귀·GPU canary·비용 측정은 별도 소유 증거다.

KST 2026-10-23 07:34 이후 읽은 runner는 출력 namespace가 `p106b_official_core6_v2`이고 파일 SHA256은 다음과 같다. 이후 실행 영수증은 자신의 `source_identity`를 기준으로 이 검토 snapshot과 차이를 확인해야 한다.

| 별도 접속 source | SHA256 |
|---|---|
| `scripts/diag_p106b_official_core6.py` | `9c2aad219a7b4b0eab40d396c0a107f6486fb5c4d123cbb3e16771d5d78771d8` |
| `scripts/test_p106b_official_core6.py` | `2f60014b445de7f9d377f6a6d3714fab4aab051a57e19ca879c72f754cae3df9` |
| `scripts/p106b_official_lm_adapter.py` | `e9fa2b17b5e8e27453c39889b6a3c5f97444b87550db850b3d3fbc38e570cbc5` |
| `scripts/p106b_official_tasks.py` | `ae1f222e5050b1c3b90d6e4577bd1f6c23b2dfce17079e0b706de71f23badb15` |
| `scripts/prepare_p106b_official_eval.py` | `b15d06201ceccc2e367e3a54240759febd940fb5646364082b39d6f01301df03` |
| `scripts/p106b_shards.py` | `30cbd7d6b5be09d4c8b8983cdd607ef07ba379cc3892067c41d3a06df22e1da4` |

**현재 source에서 즉시 실행을 막을 새 우도·집계 계산 결함은 발견하지 못했다.** 아래 두 회수/시간 결함은 검토 중 총괄에게 알렸고, 현재 source에서 수정된 것을 재확인했다. 원 공식 source 및 이 담당 소유가 아닌 코드는 수정하지 않았다.

### 16.2 공식 task 객체·0-shot·문항 분모

task builder는 고정 공식 YAML을 `resolve_func=True`로 읽어 실제 `ConfigurableTask` 객체를 만든다. `doc_to_text`/choice/target, `process_docs`, metric list, target delimiter 등 원 입력·채점 계약을 보존한다. 승인된 변경은 local 고정 eval parquet 경로, 사용하지 않는 train/fewshot split 제거, `num_fewshot=0`, 빈 fewshot samples 같은 저장·초기화 계약이다. 원 source/YAML 자체를 편집한 것이 아니다. [공식 task 구현](https://github.com/EleutherAI/lm-evaluation-harness/blob/d6de81643928d653435c431bae19945d41d32520/lm_eval/api/task.py)

`ConfigurableTask`는 0-shot이어도 초기화 중 fewshot 문서를 조회할 수 있다. 따라서 단지 `simple_evaluate(num_fewshot=0)`만 추가하고 원 train 경로를 남기는 대신, 이번 builder처럼 `fewshot_config.samples=[]`까지 명시한 이유가 있다. 전체 train을 추가 반입하지 않는다. 실제 model runner는 이 객체를 `tasks=[task]`로 넘기므로 이름만 넘겨 원 원격 YAML/loader로 다시 생성하는 경로와 구별된다. task manager는 모델당 한 번 만들고 각 호출에 명시 전달한다.

Python/NumPy/Torch/fewshot 네 seed를 모두 1337로 명시한다. 네 기본 seed가 자동으로 같다고 가정하지 않는다. `apply_chat_template=False`, `fewshot_as_multiturn=False`, request cache OFF이며 과제별 호출 시 원 요청 목록을 새로 구성한다. 별도 `Task`를 전달했을 때 `simple_evaluate`의 batch/device 인수가 이미 열린 adapter를 다시 설정해 준다고 기대하지 않고, adapter/HFLM 생성 단계에서 batch8/max1024를 고정한다. [공식 evaluator](https://github.com/EleutherAI/lm-evaluation-harness/blob/d6de81643928d653435c431bae19945d41d32520/lm_eval/evaluator.py)

전량 분모는 PIQA1,838 / ARC-Easy2,376 / ARC-Challenge1,172 / HellaSwag10,042 / WinoGrande1,267 / BoolQ3,270, 합 **19,965문항**이다. 비용 표본은 과제별 첫32문항, 합192문항이며 full에서 `limit=None`으로 돌아간다. full은 “192 결과를 확대 추정한 점수”가 아니다. 보기별 likelihood 요청 수는 문항 수보다 크고 ARC의 보기 수도 원 자료대로이므로 19,965를 forward/후보 수로 쓰지 않는다.

### 16.3 BOS·전 continuation 우도·1,024 좌측 절단

공식 `TemplateLM._encode_pair:393–431`는 prompt 끝의 `rstrip()` 공백류를 continuation 앞으로 옮기고, causal 모델에서는 **prompt+continuation의 joint tokenization**을 문맥 token 길이로 나눈다. native adapter는 이 상위 구현을 그대로 상속한다. prompt/보기를 독립 encode해 이어 붙이거나 한 글자/보기 첫 token만 채점하는 기존 루틴으로 바꾸지 않는다. 빈 prompt는 모델의 prefix ID를 쓰고 이미 첫 token이 prefix이면 중복을 제거하는 공식 분기를 따른다. [고정 TemplateLM](https://github.com/EleutherAI/lm-evaluation-harness/blob/d6de81643928d653435c431bae19945d41d32520/lm_eval/api/model.py#L393)

선택된 규약은 **nonempty 문맥에 추가 BOS 없음**, 빈 문맥에 native BOS 또는 EOS prefix다. Falcon에는 `add_bos_token=False`를 명시한다. 임의 EOS를 정답 끝에 붙이지 않는다. 이는 이번 비교의 사전 고정 규약이며 모든 HF 모델의 tokenizer 기본값이 원래 BOS OFF라는 일반 명제가 아니다. WinoGrande도 후보 단어 자체를 채점하지 않고 공식 후보별 prefix에서 같은 suffix의 전체 우도를 비교한다.

native `plan_tokens:176–190`와 HFLM `:1426–1437`은 같은 계획이다. 문맥 길이를 C, continuation 길이를 K라고 할 때 `removed=max(0,C+K−1025)`, 입력은 `(context+continuation)[-1025:][:-1]`이고 K개 target 전체를 채점한다. K>1024/빈 target/불가능한 prefix는 실패로 남기며 후보를 자르거나 문항을 skip하지 않는다. 원 HFLM warning 문구의 `total−max+1`은 실제 slice가 버린 수보다 2 크므로, **경고 문자열의 숫자 대신 실제 식**을 저장한 별도 length observer가 타당하다. [고정 HFLM](https://github.com/EleutherAI/lm-evaluation-harness/blob/d6de81643928d653435c431bae19945d41d32520/lm_eval/models/huggingface.py#L1413)

같은 원문 task/같은 token cap이어도 tokenizer가 다르면 절단 시 남는 **원문 bytes가 다를 수 있다**. Falcon의 원래 최대 문맥 262,144를 이번에는1,024로 제한하므로 결과 명칭은 `official tasks / common max_length1024 track`이 적절하다. 실제 전량 length 영수증에서 절단0이 확인되기 전에는 “모델별 입력 근거가 완전히 같았다” 또는 “native 문맥 상한을 모두 썼다”고 주장하지 않는다. 현재 length observer는 모델 호출 **전에 계획된 요청 전체**를 적으므로 ERROR 실행의 length rows를 완료된 채점 수로 읽어서는 안 된다. 완료 분모는 닫힌 task의 raw sample 감사가 소유한다. 현재 요약은 전체6과제 합이며 과제별 절단량이 필요하면 raw 요청/task 경계와 함께 별도로 복원·표시해야 한다.

| 비교 경로 | 장점 | 해석 한계·비용 |
|---|---|---|
| A — 전량·공통1024, 현재 선택 | 모든 모델 같은 task/문항 분모와 제한으로 비교; 기존 adapter와 공식 crop 정합 | 절단된 원문 근거는 tokenizer마다 달라질 수 있음; 전량 비용 필요 |
| B — 모델별 native 문맥 | 각 모델 최대 문맥 능력을 보존 | 같은 문맥 예산 비교가 아니며 Falcon의 긴 상한으로 비용/입력 조건이 달라짐 |
| C — 전 모델 무절단 공통 subset | 실제 같은 원문 근거를 유지하는 보조 분석 | 선택된 subset이지 full Core6가 아니며 subset 선정/행수 공개와 추가 집계 필요 |

권장 A를 주 결과로 유지하고 실제 절단 통계를 공개한다. B/C는 지금 조건을 조용히 바꾸는 대체안이 아니라 별도 승인·이름의 보조 비교다. 모델 간 token NLL의 절대값이나 token 노출량을 tokenizer 불변 척도로 비교하지 않는다.

### 16.4 Falcon의 cache·FP32·커널과 비용 공정성

서로 다른 네 cache를 구분해야 한다.

| 계층 | 끄는 실제 위치 | 이번 source 확인 |
|---|---|---|
| 모델 KV/Mamba state cache | 열린 모델의 `config.use_cache=False`; 독립 full-sequence 호출 | Falcon strict loader가 인메모리 False로 설정·검산. 원 config 파일은 보존 |
| HFLM continuation-prefix logits 재사용 | HFLM `logits_cache=False` | 명시 OFF; 같은 prefix+마지막 token만 다른 후보의 계산 공유를 하지 않음 |
| 응답 SQLite cache | `simple_evaluate(use_cache=None)` | OFF. `policy.use_cache=False`와 API의 실제 None 인수는 같은 이름이지만 다른 층 |
| task/request cache | `cache_requests=False` | OFF; cost/full이 캐시된 제한 요청 목록을 공유하지 않음 |

HFLM causal `_model_call`은 단순히 `self.model(inps).logits`를 부르므로 외부 `use_cache=False` 옵션이 모델에 자동 전달된다고 가정하면 틀린다. 이번 사전 개방 loader는 `AutoModelForCausalLM`에 FP32/eager/cacheFalse/local-files-only/remote-code-OFF를 명시하고 loading_info의 missing/unexpected/mismatch/error를 거부하며 모든 parameter dtype과 열린 config를 확인한다. HFLM에 이미 열린 모델을 넘겼을 때는 HFLM `dtype=`만으로 원 BF16 weight가 바뀐다고 믿지 않는 경로다. `softmax_dtype=float32`, `mixed_precision_dtype=None`, TF32 OFF, outer SDPA MATH도 명시했다. [HFLM causal model call](https://github.com/EleutherAI/lm-evaluation-harness/blob/d6de81643928d653435c431bae19945d41d32520/lm_eval/models/huggingface.py#L1111)

실제 Transformers Falcon-H1 source에서 eager 선택은 attention 경로를 정하며 **모든 Mamba/causal-conv 커널 선택을 정하는 옵션은 아니다**. 현재 지명 metadata 감사에서는 `mamba-ssm`, `causal-conv1d`, `kernels`, `flash-attn`, `peft`가 없었다. 선택 API/Core6를 위해 이 선택 가속 package를 자동 추가할 이유로 보지 않는다. `USE_HUB_KERNELS=0`과 HF offline 세 환경값은 Transformers import 이전에 설정되며, 원격 lazy kernel 취득을 막는 경계다. 실제 fast-path 여부는 runner의 `fast_mamba_path`와 실제 실패/성공을 보고 확인한다. source만 보고 GPU backend 성능을 보장하지 않는다. 이 항목은 §15의 `KNOWN_UNSATISFIED_DECLARED_BASE`를 해제하지도 않는다.

동일 full-label CE의 합성 한/영·빈 prefix 대조, batch 결과/greedy/FP32 전체 logits shape 검산을 선택한 모델마다 먼저 하도록 되어 있다. outer context를 `no_grad()`로 둔 것은 strict loader가 `Parameter._version`을 검산할 수 있게 하는 선택으로, parameter 생성까지 `inference_mode()`로 감싸는 것과 구별된다. 기존 native route 검산과 모델 전후 core fingerprint는 별도이며, 실패로 context가 빠져나가 최종 fingerprint가 없으면 불변성 확인까지 완료된 것으로 승격하지 않는다.

기능적 우도 계약이 같아도 두 backend의 비용 경로는 같지 않다. HFLM은 요청을 길이순으로 정렬하고 전체 `[B,T,V]`에 FP32 log-softmax를 적용한 뒤 continuation을 선택한다. native는 현 요청 순서로 batch를 만들고 full logits에서 continuation 위치만 골라 log-softmax한다. HFLM right pad는0, native는 native pad ID이므로 causal mask 하의 유효 위치 정합을 실제 mixed-length canary가 담당한다. 따라서 wall/메모리 차이를 **아키텍처나 삼진화만의 단일효과**라고 부를 수 없다. Falcon 기준 B8×T1024×V32768 FP32 logits 하나만 1GiB이고 HFLM full softmax 버퍼도 따로 생길 수 있다. 첫32문항의 무OOM이 긴 tail의 최대 메모리를 증명하지 않는다.

### 16.5 공식 집계·비유한값·원답 보존

공식 `process_results`의 `acc`는 raw continuation sumLL argmax, `acc_norm`은 sumLL을 **원 `doc_to_choice` 문자열의 Python 문자 길이**로 나눈 argmax다. target delimiter는 분모 밖이며 token 수/UTF-8 bytes/반복 평균 NLL로 바꾸지 않는다. 동점은 NumPy argmax의 첫 후보다. BabyLM BLiMP의 random tie 규칙을 여기로 옮기지 않는다. [공식 MC 채점](https://github.com/EleutherAI/lm-evaluation-harness/blob/d6de81643928d653435c431bae19945d41d32520/lm_eval/api/task.py#L1489)

공식 HFLM 자체에는 모든 sumLL의 finite를 강제하는 이 경로의 gate가 없으므로, NaN이 argmax/accuracy로 변해도 그냥 숫자 점수가 생길 수 있다. 별도 runner는 원보기 수와 정확히 같은 LL 응답, finite·비양수 점수, 정수 gold 범위, sample doc_id 연속·정확 분모를 독립 거부·재집계하고 공식 per-item/mean 값과 대조한다. 이것은 **의미/정답성 재판정기가 아니라 수치·집계 보존 감사**다. 잘못된 우도는 0점으로 바꾸지 않고 ERROR로 남겨야 한다.

선택 주지표는 §3의 PIQA acc / ARC-Easy·Challenge·HellaSwag acc_norm / WinoGrande·BoolQ acc이며 Core6는 이6개의 동일 가중 산술평균이다. 개별 task 객체로 호출하면 harness가 자동으로 이 사용자 선택 Core6 group을 만들어 주지는 않는다. 공식 반환 dict를 과제별 원형으로 보존하고 Core6 평균은 명시된 별도 파생 통계로 계산한다. 모든 task의 acc만 합치거나 문항수 가중, acc/acc_norm 중 큰 것 고르기, posthoc 최빈 라벨·shortest/longest 진단을 학습된 prior로 부르는 것은 다른 주장이다. mean의 stderr는 이 경로에서 analytic mean stderr여서 `bootstrap_iters=100000`이 곧 10만 번 Core6 재평가라는 뜻도 아니다.

`log_samples=True`는 반환 dict에 문항·gold·arguments·all/filtered 응답을 넣는 옵션이지 자동 파일 저장이 아니다. runner는 이를 과제별 write-once shard와 SHA/행수 manifest로 저장하고, samples를 뺀 공식 반환 dict와 독립 재집계를 report에 남긴다. 평가 문항/정답은 평가 전용 경로에 유지하고 학습·교사·Luna에는 전달하지 않는다. 공식 result의 cwd `git_hash`가 TinyLM commit을 가리킬 수 있으므로 이를 harness commit으로 읽지 않고, 별도 framework commit/고정 archive SHA/설치 원형 감사 §15를 출처로 사용한다.

### 16.6 수정 회수·비용 입장권·남는 한계

최초 동결판의 task 결과/timing/audit dict는 local에만 쌓이다 6과제가 모두 끝난 뒤 report에 연결되어, 다음 과제 실패 때 이미 완료한 과제의 공식 반환 dict·재집계가 error report에서 빠질 수 있었다. 이를 총괄에게 즉시 알렸고 현재 `execute:274–278/:300`에서 dict 참조와 완료 분모를 task별로 report에 연결하는 것을 재확인했다. **정정:** 기존 `ShardWriter.close:84`는 별도 manifest 파일도 직접 저장하므로, 최초 지적 때 붙인 “close가 반환만 한다면 manifest도 사라질 수 있다”는 조건은 실제 구현에 해당하지 않았다. 닫힌 이전 task의 raw shard와 manifest는 당시 구현에서도 남았고, 결함은 주로 error report의 공식 결과·집계·시간 회수였다.

최초 마감 검사는 CPU task/import 초기화 전에만 있었고 실제 timer는 그 뒤 시작했다. 현재 `execute:266–270`은 초기화 뒤 남은 마감시간을 재계산하고 60초 미만이면 모델 진입을 거부한다. 두 지적은 source상 닫혔지만 이 담당이 실패 주입/마감 regression을 실행한 것은 아니다. Linux SIGALRM 기반 guard는 CUDA native call을 즉시 강제 종료하는 외부 watchdog의 증명이 아니며 예외 후 모델 CPU 회수·원본 보존 정리는 별도 시간도 쓸 수 있다. 따라서 “16:30에 어떤 GPU kernel도 절대로 남지 않는다”는 강한 보장으로 표현하지 않는다.

전량 입장권은 같은 모델명·source identity·정책과 정확32×6 완료 cost report를 요구한다. 예상시간은 **`Σ(N_task × t32_task /32) ×1.5 +60초`**, 2h/model 및 KST16:30 안에 드는지 검사한다. 초기 단순 `t192×19965/192` 방식은 HellaSwag의 full 비중 약50.3%와 표본 비중16.7% 차이를 반영하지 못하므로 채택하지 않았고 총괄이 과제별 측정으로 수정했다. 실제 task wall에는 공식 토큰화/요청 생성/집계·GPU 동기화 등이 포함되어 순수 forward tok/s와 다르며, 별도 raw 감사·저장시간은 그 task timer 밖이다.

1.5배+60초는 사전 정한 **운영 여유**이지 통계적 상한/신뢰구간이 아니다. 첫32는 길이층화/최악 tail을 대표하지 않는다. full이 gate/timeout/OOM으로 막히면 `NOT_RUN`/부분 ERROR로 보존하고 cost 표본의 정확도나 축소 분모를 full 결과로 쓰지 않는다. 현재 source identity를 바꾸면 기존 cost 입장권과 달라지므로 이후 개선은 별도 revision/출력 namespace로 분리해야 한다. 현재 raw length log는 계획 요청 기록이고 진행 중인 task의 모든 완료 forward를 실시간 원답 checkpoint로 보존하는 설계까지는 아니므로, 실패 보고는 **이미 닫힌 과제**와 **진행 중 미회수 과제**를 구분한다.

검토 완료 상태는 `SOURCE_CONTRACT_REVIEWED / MODEL_EVALUATION_NOT_RUN_BY_REVIEWER`다. 총괄이 실행한 full19,965행 원답/영수증을 아직 이 검토에서 회수하지 않았으므로 공식 Core6 전량 완료, TinyLM 우위, 가속·KD 효과, 학습 오염 부재, BabyLM 완료 어느 것도 주장하지 않는다. 기존 MC768 SUM_NLL 결과를 새 공식 점수로 변환하거나 두 절대 점수를 직접 차감하지 않는다. 이번 추가 수정은 본인 연구문서 §16뿐이다.

## 17. ALM fixed16 교사 캐시의 실행 선결 독립 감사

### 17.1 범위와 증거 수준

총괄 요청에 따라 `scripts/diag_p106b_alm_cache.py` 1,128행과 `scripts/test_p106b_alm_cache.py` 611행을 **전부 읽었다**. 연결된 순수 byte helper, Stage7a TF 확률 parser/요청/session, 기존 Qwen lifecycle·shard writer·원 주석 생성 source 및 ALM 소비 계약도 필요한 범위에서 대조했다. 이 담당은 source/회귀/실제 tokenizer/모델/GPU 실행을 하지 않았고 원 corpus·selection의 문항 전문을 열람하지 않았다. 수정은 본인 문서 이 절뿐이다.

검토 시작 snapshot SHA256은 cache 도구 `84dbcbdca70c36ac9b5efebd6b8336181a2d34e3b36f14ea834eb0116331108c`, 회귀 `42b5001cfeaee1f49aed20058c9ba326c613d4365fe15d26b16ef284aeb275f0`, byte helper `de95a294a3cdefc38a2a57c669c545d3da914823873deecccb9632098f1b876b`, ALM 손실 `bff4c3a094c60bfb032e60df19c909639256d3f14193d73d328eb02ad5e803f2`다. 총괄의 **CPU45회귀 PASS / V3 TRAIN 한영512씩1024행 SELECTION_FROZEN** 보고는 총괄 소유 실행 증거이며 이 담당이 재실행·원문 전수 검증한 결과가 아니다. 교사 GPU fixed16은 검토 요청 시점 `NOT_RUN`이었다.

`impact-analysis`로 읽기/쓰기·데이터·소비 계약 영향을 분리하고 `exp-preflight`의 비교 유효성·대조·시간/원형 보존 기준을 적용했다. 기준표의 표준/레지스트리·비교 유효성/확정 사실을 참고하되 새 ALM 신호가 과거 KD 결과를 계승한다고 보지 않는다. 이번 명시적 실행 금지 때문에 registry/회귀 도구도 실행하지 않아 자동 preflight PASS로 부르지 않는다. 이 검토는 의미 정답 심사·confidence 품질 판정·formal TRAIN_READY가 아니다.

### 17.2 source/VAL 분리 — 닫힌 것과 닫히지 않은 것

`candidate_reason:157–188`은 지명 V3 TRAIN에서 `meta.source=explicit_public_context_qa`, **정수** wrapper_view0, user/assistant 두 턴, 언어 ko/en, original split과 source split 모두 train을 요구한다. semantic root/context ID·원 context/question·source path/SHA·답 annotation 필드가 있어야 하고, 원 context/question 문자열이 실제 user에 포함되어야 한다. 잘못된 것/teacher 점수에 따라 원문을 고치는 루틴이나 품질 점수 선별은 아니다.

`validation_index`는 V3 VAL **전체**를 대상으로 semantic_root_id/parent_concept_id/root, context_id, canonical 전체 messages hash, 첫 user text hash를 모아 배제한다. root별 한 행만 남기고 고정 SHA순 ko/en 교대로512씩 고른다. 부족하면 quota·조건을 완화하지 않는다. 입력 report/tokenizer/원 train·val shard가 지명 SHA와 일치해야 하며 교사 진입 전후 그 입력을 다시 해시한다. `source_inputs`는 지명 corpus/tokenizer 밖 원천을 자동 순회하지 않는다. 공식 Core6/BabyLM 평가 자산을 학습·교사 입력으로 연결하는 경로도 이 도구에는 없다.

다만 이번 selector 자체는 `answer_start`의 **정수 여부**만 확인하고 `context[start:start+len(answer)]==answer`나 assistant==원 answer를 다시 검사하지 않는다. 원 생성기 `scripts/p106b_night_qa_data.py:302–319`는 nonempty 답·음수 offset·문자 substring 검산을 수행하고 `:160–177`에서 첫 원 답을 assistant로 렌더링한다. 따라서 여기의 주장은 **고정 corpus와 원 주석 생성 계보를 보존**한다는 것이며, selector에서 새로운 전수 정답 검산을 끝냈다는 주장이 아니다. 회귀의 toy `source_row`도 실제 context와 answer_start가 맞는 원천 검산 oracle는 아니다.

context_id는 원 생성기에서 언어+정규화 context hash로 만들지만, VAL의 다른 자료 계열에 context_id가 없거나 root가 끊긴 경우까지 모든 본문 부분중복/의미 paraphrase를 검출하는 것은 아니다. selected1024 roots도1024 독립 문맥을 뜻하지 않는다. source QA의 서로 다른 질문이 같은 지문을 공유할 수 있다. 한영 **행수** 동수는 CE targets/정렬 KD chunks/bytes/교사 호출량 동수와 다르므로 후자의 실제 합계는 별도로 보고한다. teacher 사전학습 기억/전체 학습오염 부재도 이 split gate가 증명하지 않는다.

### 17.3 같은 full ChatML의 native-ID·piece·UTF8·마스크

`pack_student:286–323`은 원 `encode_record`와 `encode_conversation`의 ids/labels/full text, full next-token shift, segments, x/target 수를 직접 대조한다. tokenizer char offset에서 assistant span containment를 만들고 원 label과 일치해야 한다. char span을 실제 UTF8 byte offset으로 바꾸며, student ByteLevel piece는 표시 문자를 UTF8 encode하는 대신 원 byte alphabet의 역변환을 쓴다. 같은 token ID의 piece/원문 재구성 불일치는 실패한다.

교사는 같은 **완성된 full ChatML 원문**을 `/tokenize`에 `add_special=False, parse_special=True`로 보내고 native ID 요청과 native piece 요청의 ID열을 대조한다. special literal 각각이 한 native ID/같은 literal bytes인지 별도로 probe한다. template 재적용·BOS 덧붙이기·문자 정규화·teacher 문장 재생성은 하지 않는다. teacher token/piece는 str 또는 integer byte-array를 그대로 복원하고 full UTF8 원문 전체와 정확히 같아야 한다. 각 teacher target i는 원 native prefix `ids[:i]`와 target `ids[i]`를 쓰며, 학생/교사 shifted index는 각각 i−1을 별도 저장한다. 평가 후보/정답이 아니라 지명 TRAIN 원 reference만 이 경로로 들어간다.

`align_assistant_chunks`는 양쪽 token 끝이 만나는 가장 짧은 공통 byte 구간 중 두 stream 모두 assistant supervision·같은 양의 turn ID에 완전히 들어오는 chunk만 수락한다. special token·unsupervised·turn 경계·예측 불가능한 raw0은 명시 reject 사유다. 학생 assistant `<|im_end|>`는 **CE에는 남고 KD에서는 빠지며**, assistant role header·user 내용·EOT 뒤 newline은 기존 loss span 규약을 바꾸지 않는다. teacher token이 assistant 경계를 걸치면 일부 bytes만 억지로 잘라 사용하지 않는다. chunk 제외량/covered bytes/학생·교사 supervised bytes 및 target 수를 함께 기록하는 이유다.

student1024/CE64 선별은 teacher native token 수도1024/64라는 보장이 아니다. 교사 full native ID가1024를 넘으면 fixed row를 자르거나 교체하지 않고 해당 호출을 실패시킨다. 16행 canary 성공은 나머지1008행의 native tokenizer·special·문맥 상한·정렬 성공까지 증명하지 않는다. Byte helper가 제공하는 것은 structural alignment이며 실제 logp 정합·의미 지능·답의 참 여부가 아니다.

### 17.4 raw chosen logp와 cold/warm 검산

실제 payload는 native `/completion`, `n_predict=1`, `n_probs=2`, temperature0, `post_sampling_probs=False`, seed1337, penalty 중립, top_p1/top_k0/min_p0이다. 강제 bias는100 한 번, 실제 chosen ID가 reference target과 다를 때만200 한 번으로 제한한다. 응답은 정확 한 토큰의 `completion_probabilities`에서 **chosen ID/logprob**를 읽고 top2에 target이 없다고 확률을0으로 만들거나 top2 재정규화하지 않는다. 전체 후보 분포/hidden/정답 생성이 아니라 quantized main teacher의 reference-token logp 신호다. MTP는 기존 TF `session_for`/command의 명시 `--spec-type none`으로 끈다.

Stage7a prerequisite는 두 원 synthetic 사례의 성공·MTP OFF·고정 source·raw manifest를 요구한다. 이는 특정 binary/API에서 pre-sampling logp 보존을 확인한 **선결**이지 모든 QA token의 bias100/200별 불변성을 새로 독립 측정한 것은 아니다. 현재 force path는100 성공 시200을 추가 호출해 비교하지 않는다. 임의 tail token의 절대 unbiased 확률까지 독립 full-logit oracle로 측정했다는 주장도 하지 않는다.

cache_prompt ON이면 각 row의 **첫 정렬 teacher target**은 OFF로 받고 같은 prefix/성공 bias를 ON으로 한 번 재요청한다. chosen ID/raw logp 및 top 목록 ID/logp가 abs1e-5 안에 같아야 하며 mismatch 때 cold fallback으로 통과시키지 않는다. cold가200으로 성공했으면 warm도200으로 바로 보내므로 불필요한100 시도는 하지 않는다. 이후 target은 증가하는 원 prefix에 cache_prompt ON을 사용한다. unique reference targets, 검산 추가 호출, bias200 물리 요청은 별도 counter이며 bias200 counter에는 warm 검산도 들어가므로 이를 그대로 retry 횟수라고 부르지 않는다.

**범위 주의:** 이것은 first-target OFF/ON parity이고 실제 KV/cache hit나 이후 더 긴 prefix의 모든 target parity까지 증명하지 않는다. 현 비교는 cache hit/tokens reused를 assert하지 않으므로 `warm`은 요청 설정명이다. 원답은 보존되지만 실제 cache reuse/가속 주장은 원답의 관측 가능한 재사용·비용 근거를 더 회수한 뒤 해야 한다. 서버 source 고정 tag의 추가 공식웹 열람은 접속 오류로 확보하지 못해 이 감사에서는 cache hit 내부 동작을 새로 확인했다고 주장하지 않는다.

### 17.5 새 발견 — logp 수용 범위의 소비 계약 불일치

**P2, 실제 후속 소비 위험:** 공유 `diag_p106b_teacher_tf.probability_entry:83–86`는 유한한 `−1e30 < logp <= +1e-6`를 허용한다. 그러나 `tinylm/train/alm.py:121–128`의 `chunk_kl`은 teacher chunk logp를 `<=0`으로 요구한다. 예를 들어 chosen logp가 **+5e-7**인 한 token chunk는 cache parser/row/완주 상태에서는 거부되지 않지만 후속 ALM 소비에서는 실패한다. 실제 서버에서 그 값이 관측됐다는 뜻은 아니고, 허용 입력에 대한 **두 source 계약이 서로 다름**을 찾은 것이다. 정상 log probability의 수학적 상한은0이다.

현재 회귀 `test_sentinel_nonfinite_and_positive_logp_rejected`는 +1.0/NaN/Inf/bool/sentinel을 검사하지만 +5e-7·정확0·음의 매우 작은 값의 cache→chunk 소비 경계를 검사하지 않는다. 원 raw logp를 임의 clamp하거나 확률을 다시 정규화해 소리 없이 PASS로 바꾸는 수정은 권하지 않는다. 최소 방향은 raw 보존을 유지하면서 cache의 train-consumable 판정을 `<=0` 계약과 명시 일치시키는 것이다. 현재 모듈 그대로 canary만 수행한다면 결과명은 운영/API canary로 제한하고 후속 `chunk_kl` 수용까지 자동 PASS로 승격하지 않는다. 총괄에게 실행 전에 이 불일치를 전달했다.

### 17.6 새 발견 — 영속성·thread 종료·600초의 주장 범위

**P2 조건부 경쟁:** recorder의 append는 RLock으로 main/log/sampler 간 직렬화하고 background 실패를 latch한다. 다만 실제 lifecycle의 `Session.__exit__`는 worker별 `join(timeout=6)` 후 alive 여부를 검사하지 않는다. 최종 `writer.close`/manifest 생성도 recorder lock 아래 있지 않다. 정상 종료가6초 안에 thread를 모두 닫으면 문제가 없지만, timeout 뒤 살아 있는 log worker가 늦게 append하면 최종 raw manifest와 경쟁하거나 close 뒤 새 shard를 만들 수 있다. 현재 `verify`는 manifest에 **열거된** 파일을 확인하며 추가 미열거 shard 자체는 검사하지 않는다. 이 경쟁이 실측됐다는 주장은 아니며, mock의 일반 threaded append/정상 exit 검산은 timeout 후 worker 생존 경로를 검증하지 않는다. source상 완전한 background quiescence gate가 빠져 있다는 지적이다.

**P3 보존 표현:** `test_request_is_on_disk_before_transport...`는 `MemoryWriter`의 append 순서만 관찰한다. 실제 `ShardWriter.append:68`은 Python buffered file write이고 flush는 `_finish:49`의 rotation/close에서 한다. 따라서 정상 Python 예외를 잡아 finally로 닫는 원답 회수와, SIGKILL/전원 손실에도 요청 직전 durable 저장이 끝났다는 보장은 다르다. 현재 source는 후자를 구현·검증한 것으로 부르지 않는다. fsync가 필요하다면 별도 비용·정책 선택이며 회귀 이름만으로 충족되었다고 보지 않는다.

시간·소유권 guard는 대체로 명시돼 있다. Budget은 source/준비 읽기·Stage7a 선결 검증을 포함하고 최대600초/aware hard stop KST16:30을 요구한다. 서버 개방 전 원 inputs/teacher 모델·7개 binary-library를 해시하며 idle을 검사한다. 요청 timeout은 남은 시간에서30초 shutdown reserve를 뺀 값 이하이고, 기존 owned Session만 사용해 시작/종료/200ms 메모리·server log·HTTP 실패 원형을 보존한다. teardown 뒤 모델 full SHA·inputs/source를 재검산하고 불완전 end hash는 `NOT_VERIFIED_AFTER_PARTIAL_FAILURE`다. 생존 PID/telemetry/영속 오류를 통과로 숨기지 않는다. 실제 모델 파일 한 번은8,771,311,680B라 전후 해시·기동·종료 비용을 teacher tok/s에 묻지 않고 따로 기록하는 것이 맞다.

그렇지만 SIGALRM은 native GPU 작업의 즉시 강제 중단을 증명하는 외부 watchdog은 아니다. kill helper도 SIGKILL 뒤 별도 wait가 없으며, report의 생존 PID 검산이 그 음성을 잡는 경로다. 최종 raw/cache close·manifest 검산·report 기록은 wall_limit 밖의 finally에 있고, `wall_seconds`/600초 판정은 최종 report를 쓰기 **직전**에 계산한다. 그러므로 600초/16:30을 완료 보고서 flush까지 포함한 절대 실행 상한으로 확대하지 않는다. timeout/작업 중단 시 기존/부분 디렉터리는 보존하고 resume/overwrite를 거부하는 정책은 타당하다.

### 17.7 source 동결·대안·우선순위

현재 준비 report는 **소비 도구/회귀까지 포함한 전체 CODE SHA map**을 동결한다. 위 gate나 회귀를 고치면 `load_prepared:466`에서 기존 report와 달라져 즉시 거부된다. 기존 SELECTION_FROZEN report를 덮어 source hash만 새 것으로 바꾸는 복구는 하지 않는다. 더구나 `root_order:192`의 hash 입력에는 SCHEMA가 들어가므로, 단순 V1→V2 schema 변경은1024행과 fixed16 자체를 바꿀 수 있다. 수치/API 복구를 데이터 재선별과 섞지 않도록, 별도 경로/소비 revision으로 가면서 원 선택 hash 계약 또는 원 prepared row SHA 목록을 명시 보존해야 한다.

| 안 | 내용 | 장점 | 단점·영향 | 수행비용 |
|---|---|---|---|---|
| A — 기존 snapshot의 운영 canary만 | 기존 fixed16/cache ON/600초를 유지하고 위 한계를 결과명에 명시; 후속 KD 수용은 별도 gate | 선택/소스 동결과 현 준비물을 그대로 보존 | 작은 양수 계약 차이·thread/drain/cache-hit 미검증은 남음; formal train-ready 아님 | 낮음, 실제 교사16행 시간은 미측정 |
| B — 같은 row SHA를 유지한 독립 복구 revision | raw nonpositive 소비 계약·thread 종료/최종 저장·필요한 prefix-extend parity를 별도 source/출력 버전에서 보강 | 정렬·확률·회수 선결을 좁혀 실제 KD 전 검증 가능 | 원 준비 source 동결과의 호환을 명시 처리해야 함; schema 변경 재선별 금지 | 중간, CPU 회귀/준비 계보와 소수 추가 요청 |
| C — cache OFF cold 기준부터 | 같은16행의 원 prefix를 cold로만 점수화하고 ON 비교는 이후 독립 실험으로 분리 | cache reuse 내부 상태 문제와 raw 확률 경로를 더 직접 분리 | prefix 재계산으로 느릴 수 있고600초에 완주 못할 수 있음; ON 가속 증거 없음 | 중간~높음, 실제 target 수·prefix 길이에 의존 |

권장: **실제 KD/cache train-consumable 판정 전에는 B**로 수치 수용·thread 종료를 닫는다. 총괄이 현 snapshot의 첫 canary부터 관측하기로 하면 A의 범위를 지켜 운영 증거만 회수하고, 그 성공을 ALM 학습/답의 정답성/양질 교사 확률/캐시 전체 완료로 쓰지 않는다. 어느 안이든 Core6 작업과 모델을 겹쳐 띄우지 않고 actual idle 확인 뒤 한 owned teacher만 개방한다. 16행 비용에서는 unique targets와 검산/재시도, native tokenization·hash·기동·shutdown을 분리하며, 첫16으로64 batch 최악 비용을 보장하지 않는다. 전체 cache는1024행/64 batch의 각 완료 영수증이 필요하고 canary를1024행 완료로 올리지 않는다.

이 담당의 상태는 `SOURCE_ONLY_REVIEW_COMPLETE / TEACHER_CACHE_AND_KD_NOT_RUN_BY_REVIEWER`다. 발견은 총괄에게 전달했고 원 코드·frozen source/VAL·준비물·모델·평가자료·Git 상태를 변경하지 않았다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 17.8 총괄의 storage-v2 수정 회수와 남는 cache 경계

위 §17.1~17.7은 최초 snapshot의 보존 감사다. 검토 중 총괄이 source를 수정했고, 이 담당은 해당 구간을 다시 읽어 **KST07:48 무렵 cache source `7e259a58e083d200199bb5bb75c3dd9fe4d61cd8970b2de7ad1c04a67fe84acb` / 회귀 `fb5765746d789bdcda328e419c12b49709eadf1181bb34d091e2cf38156b4ece`**에서 다음을 확인했다. 총괄 수정의 실행 결과를 대신 판정하지 않으며 이 담당의 코드 편집/실행은 여전히0이다.

- `force_target:775–776`이 원 target attempt를 먼저 기록하고 **모든 양수 logp를 거부**한다. 임의 clamp 없이 +5e-7 실패/raw 보존 회귀가 추가되어 §17.5의 소비 범위 차이는 source상 닫혔다.
- `thread_exit_proof:692–697`이 생존 worker를 latch하고, `closed_batch`가 `owned_threads_closed=True`를 요구한다. recorder를 lock 아래 seal한 뒤 manifest를 닫아 late append가 새 raw shard를 만들지 못하게 했다. worker 생존·seal 후 append 실패 회귀도 추가되었다. §17.6의 원 경쟁 gate 누락은 source상 보강되었다.
- 요청 attempt 뒤 `Recorder.flush()`를 수행해 transport 이전 buffered bytes가 파일에서 보이도록 했다. 실제 shard를 읽는 회귀가 추가되었고 report는 `USER_BUFFER_FLUSH_BEFORE_HTTP; NOT_FSYNC_OR_CRASH_DURABILITY`를 명시한다. 따라서 정상 read-after-flush 보존과 fsync/power-loss 보장은 계속 구분한다.
- 새 저장 경로는 `HF/sft_ready/p106b_alm_context_v2_s1337`지만 **SCHEMA와 root_order 입력은 V1 그대로**다. 이를 위한 source 주석도 있어 버전 이름 때문에 원1024/fixed16 선택을 조용히 바꾸는 위험을 피했다. 새 준비 실행 및 원 prepared-row SHA 목록과의 실제 일치는 총괄이 회수해야 한다.

추가로 canary는 `verify_all_cache=True`로 각 selected teacher target마다 OFF/ON을 비교하게 확장되었다. 그러나 현 호출 순서는 **`OFF_i → ON_i → OFF_(i+1) → ON_(i+1)`**다. 이는 모든 target의 **같은-prefix replay parity**를 보는 강화이며, 생산 cache의 **`ON_i → 더 긴 prefix의 ON_(i+1)`** 연속 상태를 그대로 재생한 것은 아니다. 별도 cold-all pass 후 warm 증가-prefix-all pass를 대조하면 같은2K 기본 요청으로 후자도 확인할 수 있지만, 이는 이 담당이 구현한 변경이 아니라 총괄에게 전달한 대안이다. 실제 cache hit/가속 여부를 assert하지 않는 한 `ALL_SELECTED_TARGETS`를 cache 내부 모든 동작·성능 PASS로 확대하지 않는다.

또한 `--canary`에 `--cache-prompt`를 붙이지 않는 CLI 경로도 허용되는데, 현재 row/report의 `cache_verification_scope`는 verify_all_cache/canary 여부만 보고 `ALL_SELECTED_TARGETS`라고 적는다. 실제 cache_prompt OFF이면 검산0건이다. **요청된 ON 실행에는 직접 해당하지 않는 metadata 경계**지만 OFF 결과는 `NOT_REQUESTED/NO_CACHE_VERIFICATION` 같은 명시 상태 또는 검산 개수 gate가 필요하다고 총괄에게 보고했다. 실제600초/종료 report flush의 상한, 문항 정답성·전체1024 cache 완료·KD 효능을 분리해야 한다는 나머지 한계는 유지한다.

### 17.9 storage-v3 두 번 순회 검산·OFF 표기 정정 회수

총괄의 추가 수정 요청에 따라 **변경된 좁은 cache_row·scope·저장 경로·회귀 구간만** 다시 읽었다. 검토 source는 cache `9a84a555939a98162a953ed86d9ec8b742bcbc9736ab3770d92680fd8fd8a7e9`, 회귀 `2b693383edcc76501de36cf86901aa3d7204f121e5cafa75d50a8927cff693a8`다. 이 담당은 source 수정·테스트/모델 실행을 하지 않았다.

`cache_row:825–832`는 선택된 teacher raw index의 정렬 순서대로 **모든 cold reference를 OFF로 먼저 저장**한다. 그 뒤 `:833–845`의 별도 순회가 원 native prefix를 증가시키면서 ON 결과 각각을 같은 raw index의 cold reference·성공 bias와 대조한다. 이제 호출 순서는 **`OFF_1,…,OFF_K → ON_1,…,ON_K`**여서 §17.8의 interleave 때문에 증가-prefix warm-chain을 직접 검산하지 못하던 경계는 source상 닫혔다. 기존의 chosen ID·raw logp·top ID/logp abs1e-5 비교와 mismatch 실패/원형 보존도 유지된다. canary row의 학습용 chunk 합에는 cold reference를 쓰고 warm 결과/비교를 별도 원답으로 보존하므로 두 값을 평균하거나 교사 확률을 다시 정규화하지 않는다.

row `:869–870`와 invocation report `:1018–1019` 모두 cache_prompt OFF를 먼저 분기해 **`NO_CACHE_VERIFICATION`**, ON canary를 `ALL_COLD_THEN_INCREMENTAL_WARM`, 일반 ON batch를 `FIRST_SELECTED_TARGET_PER_ROW`로 기록한다. 따라서 OFF에서 검산0건인데 전체 검산으로 표시되던 metadata 경계도 source상 닫혔다. source의 mock 회귀는 두 target에 대해 `[False,False,True,True]` 호출 순서·검산2건·새 scope를 확인하고, OFF row의 새 scope를 확인하도록 바뀌었다. 이는 회귀 source 판독이며 이 담당이 그 회귀를 실행해 PASS를 관측한 것은 아니다.

저장 경로만 `HF/sft_ready/p106b_alm_context_v3_s1337`로 분리하고 SCHEMA/root_order 계약 V1은 유지했다. 총괄은 v1/v2 준비본 보존 및 원1024/첫16 prepared-row SHA 동일성 CPU검산 예정이라고 고지했다. 현재 source를 통해 hash 선택 계약의 유지를 확인했지만 그 실물 준비·동일성 CPU 검산은 총괄의 후속 증거로 남긴다. 실패한 canary를 다른16행으로 바꾸는 승인이 아니다.

두 좁은 수정에서 즉시 canary 진입을 막을 새 계산 결함은 발견하지 못했다. 실제 cache hit·warm 정확도·시간/메모리·teacher 전체1024행·KD 학습은 여전히 새 실행 전에는 `NOT_RUN`이다. 특히 partial canary의 unique_targets_completed는 warm 비교까지 완료한 target 수이므로, cold pass 중 이미 응답받은 서로 다른 target의 수와 다를 수 있다. 실패 시 물리 요청과 완료 검산량은 raw event로 구분하고 counter 차이를 전부 중복/검산 overhead로 해석하지 않는다.

총괄은 최종 report 쓰기까지 정확600초라는 주장을 하지 않고 외부630초 및16:30 모델중지 여유, worker wall 초과 PARTIAL을 유지한다고 명시했다. 이 담당은 외부 watchdog을 실행·검증하지 않았고 §17.6의 절대 시간/강제중단/최종 저장 보장 한계를 유지한다. §17.8의 두 미해결 항목을 현재 v3의 열린 결함으로 다시 보고하지 않는다. 상태는 `SOURCE_CORRECTIONS_REVIEWED / REAL_CANARY_NOT_RUN_BY_REVIEWER`다.

## 18. 공식 Core6 v2 전량 영수증·원답 독립 재검산 — TinyLM 세 모델

### 18.1 범위·미완료·원형

KST2026-10-23 **08:08:47 최초 조회**에서 `native595-f`, `native595-q`, `new595-broad-f`의 `full/report.json`은 존재했고 각각 `OFFICIAL_CORE6_FULL_COMPLETE / returncode0`였다. 같은 조회에서 `falcon90m/full/report.json`은 **없었다**. 요청에 따라 Falcon을 재실행하거나 대기·polling하지 않고 이 절은 **TinyLM3만** 기술한다. 따라서 이 절은 네 모델 비교 전체 완료나 Falcon 대비 순위·격차 보고가 아니다. 이 시점 이후 Falcon의 상태는 여기서 재조회하지 않았다.

`log-to-result`의 JSON 수치 정본·조건 서명 선행·관측/해석 분리를 적용했다. 현재 승인된 쓰기 범위는 본인 연구문서 새 절뿐이므로 정식 결과번호 신설, 실행/검사기 호출, 계획·기준표·COMPASS/공유 원장 연쇄 수정은 하지 않았다. 해당 정본 반영은 총괄 소유다. 모델·torch/lm_eval/외부 package import·GPU·평가 재실행·학습·설치·Git·원 코드/자료 수정은0이며, 표준라이브러리로 닫힌 JSON/JSONL을 읽고 해시·원답·파생 통계만 재계산했다. 평가 원문/정답을 학습·교사·Luna에 전달하지 않았다.

| 모델 | 독립 재판독한 full report | report SHA256 |
|---|---|---|
| native595-f | [report](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/report.json) | `56167eb44003f6859e952234ae91b936826bdf0f224f1440b914c7c2387a07a8` |
| native595-q | [report](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/report.json) | `0538084c70fa0a8db92368bac830726cd9d8216ee4f114ce29370ea2ddcc80aa` |
| new595-broad-f | [report](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/report.json) | `d976efc8371739537a57d69269a42add1ff63555b986dec421b834d38155c5b3` |

세 report의 task sample과 token length **27개 shard / 208,986,992 B**를 독립 재검산했다. 각 파일은 실제로20,000,000B 미만이고 파일 SHA·bytes·LF행수, manifest의 순서/총행수/합산 SHA와 일치했다. 각 task의 별도 manifest JSON도 report 내 manifest와 같았다. 이것은 모든 eval 샘플·길이 기록의 byte 검산이며 원 모델 weight를 다시 해시하거나 실행한 것이 아니다. 감사 전후 위 세 report SHA는 변하지 않았다.

### 18.2 공식 계약·정확 분모·같은 입력 확인

세 모델의 framework commit은 `d6de81643928d653435c431bae19945d41d32520`, data manifest SHA는 `431A096364D44980A7D0C6E072E8A06C2FAA109946FAA07E56F7687CADFEA60B`, evaluator source identity는 `F6FB22CA9B1F4A54BF1F5DFB350FEF3A7391E0A0A85845169EB166B5B8DC3FA6`로 같았다. source identity가 열거한9개 파일을 현재 source bytes와 대조해 모두 일치했다. `sources_unchanged=True`, 실제 학습False/optimizer0/checkpoint write0, 0-shot·chat OFF·batch8·max1024·FP32 MATH/TF32 OFF·cache4층 OFF 정책이 같았다. §16의 공식 task/evaluator/adapter 계약에 대응하는 source identity를 가진 실행 영수증이며 이 담당의 모델 재실행 증거는 아니다.

18개 과제별 공식 반환 설정에서도 Python/NumPy/Torch/fewshot 네 seed가 전부1337, batch8/device CUDA, `limit=None`, 응답 SQLite `use_cache=None`인 것을 확인했다. 비용32행의 제한이나 기본 fewshot seed가 전량에 남은 것으로 해석할 차이는 없었다.

원답 재계산은 official package를 import하지 않고 고정 YAML/함수 source를 직접 대조했다. PIQA sol1/sol2, ARC 원 text/label과 answerKey index, HellaSwag bracket/title 전처리 및 query/choices, Wino 후보별 prefix+공통 suffix, BoolQ no/yes를 원 doc에서 복원했다. 모든 arguments·target이 원형과 같았고, 보기마다 정확 하나의 유한·비양수 sumLL과 bool greedy가 있었다. raw resps의 반복은1회이며 filtered_resps와 같았다. doc_id는0부터N−1까지 정확하고 누락/재정렬/중복은 없었다. 공식 per-item acc/acc_norm, 독립 correct 수, 공식 반환 mean/분모와 모두 일치했다.

세 모델 모든19,965문항의 **doc·arguments·target을 포함한 독립 identity hash**가 문항별로 같았다. tokenizer SHA도 모두 `9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E`이고 prefix/BOS/평가 source가 같다. 따라서 이 세 모델의 문항 대응 비교는 성립한다. 학습 조건까지 통제된 아키텍처 인과 대조라는 뜻은 아니다.

실제 보기별 요청은 PIQA3,676 / ARC-Easy9,501 / ARC-Challenge4,687 / HellaSwag40,168 / WinoGrande2,534 / BoolQ6,540, 합 **67,106요청/모델**이다. ARC-Easy는3지선다7·4지선다2,365·5지선다4, Challenge는3지선다4·4지선다1,165·5지선다3으로, 보기 수를 전부4로 둔 재집계가 아니다. 전량 문항 분모는 아래 표대로 **19,965/모델**, 세 모델 합59,895 평가 행이다.

### 18.3 사전 선택 주지표의 실제 점수

백분율은 독립 correct/N과 공식 반환값이 일치한 값을 반올림했다. metric은 §3/§16에서 **평가 전 고정한** PIQA acc, ARC-Easy/Challenge·HellaSwag acc_norm, WinoGrande·BoolQ acc를 유지했다.

| 과제·주지표 | N | native595-f | native595-q | new595-broad-f |
|---|---:|---:|---:|---:|
| PIQA acc | 1,838 | 1,078 / **58.6507%** | 1,045 / **56.8553%** | 1,078 / **58.6507%** |
| ARC-Easy acc_norm | 2,376 | 907 / **38.1734%** | 879 / **36.9949%** | 899 / **37.8367%** |
| ARC-Challenge acc_norm | 1,172 | 262 / **22.3549%** | 265 / **22.6109%** | 281 / **23.9761%** |
| HellaSwag acc_norm | 10,042 | 2,748 / **27.3651%** | 2,713 / **27.0165%** | 2,765 / **27.5344%** |
| WinoGrande acc | 1,267 | 621 / **49.0134%** | 629 / **49.6448%** | 635 / **50.1184%** |
| BoolQ acc | 3,270 | 1,828 / **55.9021%** | 1,820 / **55.6575%** | 1,840 / **56.2691%** |
| 선택6지표의 동일 가중 산술평균 | 6과제 | **41.9099%** | **41.4633%** | **42.3976%** |

마지막 행은 공식 task별 dict에 자동 생성된 group score가 아니라, 사전 선택한6개 공식 metric의 **명시적 파생 평균**이다. 모든 raw acc를 평균하거나19,965문항을 한꺼번에 가중한 통계와 다르다. 이 평균에서 Broad−nativeF는 **+0.4876%p**, nativeQ−nativeF는 **−0.4466%p**, Broad−nativeQ는 **+0.9342%p**다. 수치 관측은 보존하지만 선택적 상위 metric/문항 제외로 다시 개선하지 않는다.

### 18.4 문자 정규화와 실제 절단 — 중요한 해석 반례

원 `acc_norm` 분모는 target delimiter를 제외한 원 보기 문자열의 Python 문자 수다. token 수/UTF8 bytes가 아니다. 동일 raw LL에서 계산한 공식 문자 정규화 재집계도 일치했다. 예를 들어 nativeF ARC-Easy는 raw999→norm907, Challenge는201→262여서 정규화가 항상 점수를 올리는 연산이 아니다.

더 강한 반례는 nativeF HellaSwag다. raw/norm의 **총 정답 수는 둘 다2,748**이지만, 예측 선택지는 **5,768/10,042문항**에서 달랐다. 같은 집계값은 같은 응답/같은 scorer를 뜻하지 않는다. 모든 모델·과제에서 raw/norm 최고값의 정확 동점은0건으로 확인했으므로 이 관측은 tie 처리 차이가 아니다.

BoolQ의 공식 주지표는 raw acc다. 여기서 평가 뒤 문자 norm으로 바꾸면 nativeF2035/3270, Q2032/3270, Broad2032/3270이라는 별도 진단값이 생긴다. 그러나 원 보기 `no`는2글자, `yes`는3글자라 그 분모가 긴 yes를 강하게 유리하게 만든다. 실제 norm 예측은 yes가 각각 **3,268/3,270, 3,269/3,270, 3,263/3,270**이고, 평가 라벨의 yes는2,033이다. 따라서 약62% norm을 새로운 독해 향상으로 선택하는 것은 거의 항상 yes라는 길이/라벨 prior를 점수에 섞는 사후 조건 변경이다. 이 값은 공식 BoolQ 결과 표에 주지표로 추가하지 않는다.

세 모델의 token length manifest 내용 SHA는 모두 `A6F749BC0D082AAF57AF9E445B328CD16BEE17A26B71207FD3F668609869833B`로 같았다. 실제 raw arguments의 request key hash를67,106개 길이 row에 순서대로 대응해 검산했다. **BoolQ doc_id3154의 두 보기만** C1161/K1에서 문맥137token씩 잘렸고, 합274token/2요청이다. continuation은 두 경우 모두1token 전체를 채점했다. 나머지 모든 과제·문항 요청은 절단0이다. 따라서 이 세 모델은 같은 절단 입력으로 비교했지만, 무절단 full-input 평가라고 부르지는 않는다. Falcon tokenizer의 동일/상이 절단 여부는 이 절에서 아직 관측하지 않았다.

### 18.5 균등 무작위·사후 최빈·길이 기준의 재집계

아래는 같은 평가 집합의 **진단 기준**이다. uniform은 실제 난수로 예측한 관측 점수가 아니라 문항별 `1/보기 수`의 기대값이다. majority는 평가 gold를 본 뒤 고른 최빈 고정 라벨의 성적이지 TRAIN에서 배운 prior가 아니다. shortest/longest는 원 보기 문자 길이로 고르고 길이 동점은 첫 보기를 택한다. Wino의 보기 문자열은 후보를 넣은 prefix다. 이 기준을 보고 source/학습자료/지표/평가 조건을 다시 고르지 않는다.

| 과제 | 균등 무작위 기대 | 사후 최빈 고정 라벨 | 가장 짧은 보기 | 가장 긴 보기 |
|---|---:|---:|---:|---:|
| PIQA | 50.0000% | 50.4897% | 53.4276% | 48.4766% |
| ARC-Easy | 25.0161% | 26.6414% | 24.4949% | 26.5572% |
| ARC-Challenge | 25.0156% | 26.5358% | 19.1980% | 27.2184% |
| HellaSwag | 25.0000% | 25.7319% | 25.4033% | 24.0888% |
| WinoGrande | 50.0000% | 50.4341% | 50.9077% | 49.2502% |
| BoolQ | 50.0000% | 62.1713% | 37.8287% | 62.1713% |
| 동일 가중 과제 평균 | 37.5053% | 40.3340% | 35.2100% | 39.6271% |

PIQA·ARC-Easy·HellaSwag는 세 모델 모두 위 네 진단 기준보다 높다. 반대로 ARC-Challenge는 세 모델 모두 uniform 기대보다 낮고 longest27.2184%에도 못 미친다. WinoGrande는 세 모델 모두 shortest50.9077%/majority50.4341%보다 낮다. BoolQ는 uniform50%는 넘지만 항상 yes인62.1713%보다 모두 낮다. 따라서 평균41~42%만으로 전체6과제에서 내용 추론을 확보했다고 표현할 수 없다. uniform 기대보다 낮다는 관측도 곧 통계적 유의 열세·지식 전무의 증명은 아니다. report의 random_independent_sd는 독립 uniform 무작위 분류기의 정답수 표준편차이며 모델 자체의 신뢰구간/학습 seed 노이즈가 아니다.

### 18.6 문항 대응 차이 — 같은 총점도 같은 문항이 아니다

모든 쌍에서 원 doc/arguments/target identity가19,965개 전부 같음을 확인한 뒤 주지표의 정오를 대응했다. 아래 각 셀은 **B만 정답/A만 정답; Δ(B−A)%p**다. 선택지 변경 수 전체와 달리 둘 다 오답인 선택지 이동은 이 정답수 차이에 들어가지 않는다.

| 과제 | Q−F | Broad−F | Broad−Q |
|---|---|---|---|
| PIQA | 103/136; −1.7954 | 39/39; 0.0000 | 143/110; +1.7954 |
| ARC-Easy | 157/185; −1.1785 | 77/85; −0.3367 | 197/177; +0.8418 |
| ARC-Challenge | 65/62; +0.2560 | 44/25; +1.6212 | 82/66; +1.3652 |
| HellaSwag | 392/427; −0.3485 | 153/136; +0.1693 | 447/395; +0.5178 |
| WinoGrande | 212/204; +0.6314 | 56/42; +1.1050 | 206/200; +0.4736 |
| BoolQ | 523/531; −0.2446 | 213/201; +0.3670 | 558/538; +0.6116 |

특히 PIQA에서 Broad와 F는 정답 수가 같은1,078이지만 서로 다른39문항씩에서 정오가 바뀌었다. BoolQ의 Q와 F도 총점 차이는8문항뿐이지만 F만 정답531/Q만 정답523으로 **1,054문항**의 정오가 달랐다. 따라서 평균이나 주변 비율만 비교해 원답이 같거나 양자화 오차가 없거나 기능적으로 동등하다고 결론내리지 않는다.

단순 문항독립을 가정한 exact McNemar 양측 p도 참고 계산했다. 사후18대조(3쌍×6과제) 중 명목 p<0.05인 것은 Q−F PIQA **0.03824**, Broad−F ARC-Challenge **0.02949**, Broad−Q PIQA **0.04403** 세 개뿐이었다. 그18대조에 Holm 보정을 적용하면 첫 문턱0.05/18부터 통과하지 못하므로 모두5% 기각은 없다. 이는 사전에 등록된 품질 gate나 전체 가족·seed 변동을 반영한 판정이 아니다.

참고로 문항 대응 Bernoulli 차의 단순95% normal interval은 Broad−F ARC-Challenge **[+0.2345,+3.0078]%p**, Q−F PIQA **[−3.4424,−0.1484]%p**다. 이 interval/p는 문항·source cluster 의존성/다중모델 선택/학습 seed를 반영하지 않은 **설명용 사후 통계**다. aggregate의 독립 stderr 두 개를 단순 합쳐 paired CI로 쓴 것이 아니다. 미기각은 동등성 증명도 아니며, 임의의 과거 σ/기준표 자를 새 Core6 정확도에 복사하지 않는다. Core6의6과제를 무작위 독립 표본으로 놓은 전체 macro 우위 신뢰구간도 여기서는 만들지 않았다.

### 18.7 조건 서명과 허용 주장

| 비교 축 | 확인/미확인 | 이 절의 주장 등급 |
|---|---|---|
| 평가 source/data/split/전량 분모/문항·arguments/주지표 | 세 TinyLM에서 모두 같고 원답 재검산 일치 | 같은 고정 평가집합의 문항 대응 관측은 성립 |
| tokenizer/BOS/context cap/crop/FP32/cache/batch | 세 TinyLM 공통, crop2요청도 동일 | scorer 차이·서로 다른 subset의 효과로 점수를 설명할 근거는 발견 못함 |
| 초기화·학습 source/pool·실제 draw·WSD horizon·언어 노출·훈련 route·추가 SFT | 이 평가 report만으로 전 조건 통제가 증명되지 않음; 서로 다른 checkpoint SHA | `DESCRIPTIVE_ONLY`; Q/F의 독립 학습·route와 Broad 추가학습을 배포 양자화 또는 한 방법의 단일효과로 분해하지 않음 |
| 원 모델 weight 불변/strict loading | 총괄 실행 영수증과 고정 strict loader 계약을 읽음; 이 담당은 weight/model 재실행0 | runtime 소유 증거와 이번 JSON/raw 감사 분리 |
| Falcon | 최초 조회에서 full report 없음, 이번 재검산 제외 | 전량 비교 `NOT_RUN_BY_REVIEWER / UNFINISHED_AT_CUTOFF` |
| 학습오염·권리·언어/자유 생성·미포함 benchmark | report가 `NOT_AUDITED_ALL_PRETRAINING`; Core6는 영어 MC | contamination-free·한국어 품질·일반대화/진위검사·Belebele/KoBEST/IFEval/BabyLM 완료를 주장하지 않음 |

Broad의 macro+0.4876%p는 이 체크포인트 묶음에서 관측한 값이고 ARC-Easy 하락·PIQA 총점 동일·약한 ARC-C/Wino/BoolQ 기준을 함께 보존한다. 새 ALM/KD 학습 결과, optimizer/architecture 단독 개선, 일반 추론 확보, 외부 Falcon 우위로 이름을 바꾸지 않는다. 기존 내부 MC768/SUM_NLL 점수를 새 공식19,965 결과로 변환하거나 두 절대 점수를 빼서 향상량으로 부르지 않는다. 이 담당의 완료는 **`THREE_MODELS_FULL_RAW_RECOUNT_AND_PAIRED_AUDIT`**이며 공식 평가 실행 자체는 총괄의 기존 수행이다.

## 19. Falcon90M 전량 합류 — 네 모델의 같은 평가 계약과 다른 인코딩

### 19.1 추가 회수·독립 재검산 범위

§18의 최초 조회 당시 Falcon 부재 기록은 그대로 보존한다. 이후 총괄이 닫힌 Falcon 영수증의 추가 감사를 요청하여 [Falcon full report](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/report.json)를 새로 읽었다. `ended_at=2026-10-22T23:19:24.030428+00:00`, 즉 KST2026-10-23 08:19:24이며 `OFFICIAL_CORE6_FULL_COMPLETE / returncode0`다. report SHA256은 `33cd985eda2f1bb1e113627ec80b2bf938011b1863ef2c8c52cd3d4bde74bcec`이고 감사 전후 같았다.

Falcon의 sample/length **9개 shard / 69,661,488 B**를 독립 재검산했다. 파일별 SHA·bytes·LF행수·20,000,000B 미만, 연결 SHA·전체 행수·별도 manifest와 report 내 manifest의 일치가 모두 확인되었다. 원 doc에서 공식 전처리/질문·보기·gold를 복원해 모든 arguments/target을 대조하고, 각 보기의 전체 sumLL·정오·문자 norm·진단 기준을 다시 집계했다. Wino/BoolQ의 `acc_norm`은 공식 task 반환 metric이 아니므로 원답에서 계산한 진단값과 공식 metric을 구분했다. 이 담당의 일부 감사 코드 작성 중 임시 hash 오타·reader 수명·없는 선택 metric 접근 오류는 고쳐 다시 읽었으며, **성공한 마지막 독립 재집계의 exit0**을 근거로 아래를 기록한다. 원 실행/샤드를 변경한 복구나 평가 재실행이 아니다.

`log-to-result`의 JSON/원답 정본·조건 서명 원칙을 사용했으며 모델·torch/lm_eval import·GPU·설치·Git·원 코드/자료 변경은0이다. 보호 데이터 및 다른 HF 원천을 열거하지 않았고 평가 원문·정답을 학습/교사/Luna에 전달하지 않았다. 정식 결과·계획·공유 원장의 연쇄 반영은 총괄 소유로 남긴다.

### 19.2 공통 정책·분모·문항 대응과 실제 Falcon 고정 자산

네 report의 `policy`, `framework_commit`, `data_manifest_sha256`, `source_identity`, `task_specs`가 **전체 dict 기준 동일**했다. framework `d6de81643928d653435c431bae19945d41d32520`, source identity `F6FB22CA9B1F4A54BF1F5DFB350FEF3A7391E0A0A85845169EB166B5B8DC3FA6`이며 열거9개 source의 현재 bytes도 일치했다. 0-shot/chat OFF/batch8/max1024/FP32/TF32 OFF/네 seed1337/응답·request·logits·model cache OFF 계약이다. Falcon의6개 공식 반환 config도 `limit=None`, batch8, CUDA, dtype FP32, 네 seed1337, SQLite `use_cache=None`으로 일치했다. `source_assets_unchanged=True`, `initial_core_sha256=final_core_sha256`, synthetic full-label CE 대조3개 `close=True`는 **총괄 실행 영수증의 관측**이며 이 담당이 모델을 다시 열어 확인한 것은 아니다.

Falcon 분모는 PIQA1,838 / ARC-Easy2,376 / ARC-Challenge1,172 / HellaSwag10,042 / WinoGrande1,267 / BoolQ3,270, 합 **19,965행**이다. 보기 요청은67,106개로 TinyLM3와 같고, ARC의3/4/5지선다 구성도 같다. 모든 원답의 doc_id 연속성·원 response 한 회·filtered 일치·유한 비양수 LL·공식 mean/정답수·분모가 재계산과 맞았다. 최고 raw/norm 정확 동점은 모두0건이었다.

특히 Falcon과 **각 TinyLM 전19,965문항**의 `[doc_id,doc,arguments,target]` 독립 hash가 문항별로 같았다. 따라서 같은 문항에 대한 paired 정오 비교는 가능하다. 그러나 원 문자열이 같은 것과 tokenizer가 만든 입력 ID·좌측 절단 후 읽은 bytes까지 같은 것은 구분한다.

Falcon은 `FalconH1ForCausalLM`, **91,131,072 parameters**, FP32/eager, `config.use_cache=False`, `fast_mamba_path=False`, HFLM logits cache OFF다. 실제 로컬 모델은 [고정 snapshot](/home/uranus/tinyLM/HF/models--tiiuae--Falcon-H1-Tiny-90M-Base/snapshots/7994372e93b62822ae25f8bfb19f653649cea3a3)이다. model safetensors SHA는 `EE1D547C2D78DF42A52AFD55B23459301CA21126851B82E0900F1E313DBCF5EF`, tokenizer SHA는 `605C664925653E3FBF2F35EA063847DB441BA5B7A6AF04378880409C3AB311FC`가 영수증에 있다. 공식 HFLM 반환 config의 `model_revision="main"`/빈 `model_sha`는 이 preloaded 객체의 불충분한 자동 메타데이터이지 실제 입력이 원격 main에서 다시 취득되었다는 증거가 아니다. 반대로 그 두 자동 필드만으로 commit 고정을 입증해서도 안 되며 위 로컬 snapshot/asset SHA 증거를 함께 보존한다.

### 19.3 같은 사전 주지표로 네 모델 합류

Falcon의 주지표도 **PIQA acc / ARC-Easy·Challenge·HellaSwag acc_norm / Wino·BoolQ acc**를 유지한다. 아래 TinyLM 값은 §18 원형, Falcon은 이번 독립 correct/N 재계산이다.

| 과제·주지표 | N | native595-f | native595-q | new595-broad-f | Falcon90M |
|---|---:|---:|---:|---:|---:|
| PIQA acc | 1,838 | 58.6507% | 56.8553% | 58.6507% | 1,193 / **64.9075%** |
| ARC-Easy acc_norm | 2,376 | 38.1734% | 36.9949% | 37.8367% | 1,161 / **48.8636%** |
| ARC-Challenge acc_norm | 1,172 | 22.3549% | 22.6109% | 23.9761% | 330 / **28.1570%** |
| HellaSwag acc_norm | 10,042 | 27.3651% | 27.0165% | 27.5344% | 3,762 / **37.4627%** |
| WinoGrande acc | 1,267 | 49.0134% | 49.6448% | 50.1184% | 654 / **51.6180%** |
| BoolQ acc | 3,270 | 55.9021% | 55.6575% | 56.2691% | 1,934 / **59.1437%** |
| 동일 가중6과제 파생 평균 | 6과제 | 41.9099% | 41.4633% | 42.3976% | **48.3588%** |

마지막 행은 공식 자동 group score가 아니라 사전6개 metric의 동일 가중 산술평균이다. Falcon−nativeF **+6.4488%p**, Falcon−nativeQ **+6.8954%p**, Falcon−Broad **+5.9612%p**다. Falcon이 이 고정 여섯 주지표에서 TinyLM3보다 각각 높다는 **배포 checkpoint 묶음의 관측**은 가능하지만 더 작은 parameter 수가 단독 원인이라는 인과 주장은 아니다. 사전학습 토큰/풀·언어 노출·훈련 schedule·아키텍처·tokenizer·추가 SFT·오염이 통제된 실험이 아니다.

### 19.4 길이 norm·입력 절단·기준선의 반증 한계

Falcon의 raw 정답수→문자 norm 정답수는 PIQA1193→1198, ARC-Easy1287→1161, Challenge285→330, Hella3245→3762, Wino654→626, BoolQ1934→2030이다. 원 보기 문자 길이가 분모이며 token 수/UTF8 byte가 아니다. raw/norm 예측 변경 수는 각각415/1066/534/5519/210/620문항이다. 두 진단 중 좋은 것을 사후 선택하지 않는다. 특히 BoolQ norm2030/3270은 yes 예측3239/3270의 별도 진단이며 공식 raw acc1934를 대체하지 않는다.

Falcon length manifest SHA는 `27B1A1D8F5054DCE7BE7ED3CCBC8EFA25AAC7F9E882B7FA09C0D5F893DB95078`다. 원 arguments의 request key hash와 **67,106개 길이 row**를 순서대로 대조했다. continuation은총 **1,486,120 token**으로 TinyLM의1,458,397과 다르다. 절단은 역시 **BoolQ doc_id3154 두 보기만**이지만 Falcon은 C1389/K1에서 문맥365token씩, 합730token을 버렸다. TinyLM의 C1161/K1·137token씩/합274와 다른 tokenizer 조건이다. 제거 token 수를 직접 빼서 제거된 문맥 bytes 차이로 환산할 수는 없다. 두 모델 모두 continuation 전체1token은 남겼으나 이 문항을 무절단·완전히 같은 encoded evidence로 부를 수 없다. 나머지19,964문항은 어느 모델도 context cap 때문에 잘리지 않았다.

§18.5의 uniform/사후 최빈/문자 shortest·longest 기준은 같은 원 doc/gold라 이번 독립 재계산에서도 **정답수까지 전부 같았다**. Falcon은 PIQA·ARC-Easy·Challenge·Hella·Wino에서 네 진단 기준을 모두 넘었다. 다만 Challenge330 대 longest319는 **11문항/+0.9386%p**, Wino654 대 shortest645는 **9문항/+0.7103%p**에 불과하고 그 차이의 통계적 유의성·내용 추론을 별도 입증한 것은 아니다. BoolQ1934는 uniform1635보다 높지만 항상 yes인2033보다 **99문항/−3.0275%p** 낮다. 여섯 주지표 모두 TinyLM보다 높다는 사실을 여섯 과제 모두 단순 prior를 넉넉히 넘었다는 표현으로 확대하지 않는다.

### 19.5 paired 차이와 교차 모델 비교 등급

각 셀은 **Falcon만 정답/해당 TinyLM만 정답; Δ(Falcon−TinyLM)%p**다. 문항 identity를 실제 대조한 뒤 집계했으며 아래에서 별도 유의성 gate를 만들지 않았다.

| 과제 | Falcon−nativeF | Falcon−nativeQ | Falcon−Broad |
|---|---|---|---|
| PIQA | 224/109; +6.2568 | 260/112; +8.0522 | 226/111; +6.2568 |
| ARC-Easy | 422/168; +10.6902 | 445/163; +11.8687 | 420/158; +11.0269 |
| ARC-Challenge | 147/79; +5.8020 | 147/82; +5.5461 | 139/90; +4.1809 |
| HellaSwag | 1424/410; +10.0976 | 1499/450; +10.4461 | 1421/424; +9.9283 |
| WinoGrande | 320/287; +2.6046 | 292/267; +1.9732 | 316/297; +1.4996 |
| BoolQ | 499/393; +3.2416 | 647/533; +3.4862 | 558/464; +2.8746 |

예를 들어 Falcon−Broad Wino는 총19문항 차이지만 정오 교환은316+297=613문항이다. 같은 높은 aggregate가 모든 문항 우위나 답변 동등성을 뜻하지 않는다. §18.6의 Holm 결과는 **당시 TinyLM3×6과제=18대조**의 보고다. Falcon을 포함한4모델 전쌍×6이면36대조이므로 과거18대조의 보정 결과를 새 전체 가족의 판정처럼 재사용하지 않는다. 현재 새18개 Falcon 대조에는 p/유의성·학습 seed 안정성·일반화 CI를 붙이지 않았다.

FP32·max1024·batch8·0-shot·같은 문항은 비교에 필요한 공통 조건이지 같은 연산 경로라는 뜻은 아니다. HFLM은 길이 정렬/전체 logits softmax를 쓰는 경로이고 native adapter는 별도 요청 정렬/continuation 처리 경로이며 Falcon은 fast Mamba kernel OFF의 eager fallback이다. Falcon wall **1828.5094s**, task evaluation 합 **1785.0589s**를 TinyLM wall259~263s와 나눠 아키텍처나 CPU/모바일 추론의 인과 속도비로 부르지 않는다. cross-tokenizer raw LL 절대값도 같은 확률 척도의 우열로 비교하지 않는다.

판정은 **`FOUR_MODELS_FULL_RAW_RECOUNT_COMPLETE / CROSS_MODEL_DESCRIPTIVE_ONLY`**다. 공식 source/task metric을 고정한 이 로컬1024/F32 조건의 전량 Core6 결과이며 BabyLM·한국어·자유 생성·진위검사·ALM/KD 효능/사전학습 오염 해소를 입증하지 않는다. source/data/모델 원형·과거 실패/미완료 기록·평가 밖 자료는 그대로 보존했다.

## 20. ALM v3 실제 실패와 v4 native no-think/cold 대안의 조건부 타당성

### 20.1 실패 영수증을 그대로 보존하는 판독

[v3 canary report](/home/uranus/tinyLM/HF/sft_ready/p106b_alm_context_v3_s1337/canary/batch_000000/report.json)의 SHA는 `6cb44c6b57163dc259a25cfa14b248a8598fb4595413a37beb6cd222d05ad755`다. `ALM_CACHE_EXECUTION_PARTIAL / returncode9 / ValueError`, 오류는 `cold/warm native ID/raw chosen logp/top2 mismatch; no cold fallback`다. 16행 중 **완료0행/검산 완료 unique target0**, 물리 completion3회 성공/그중 warm 검산1회, bias200 0회다. 총 HTTP16회 중 성공9/시작 health 실패7을 유지한다. 이 실패는 모델이 열리지 않은 `NOT_RUN`도, 전체 canary PASS도 아니다.

원 [raw shard](/home/uranus/tinyLM/HF/sft_ready/p106b_alm_context_v3_s1337/canary/batch_000000/raw_000000.jsonl)는 **323,030 B/395행**, SHA `BB023F29C8A2B3FE230CD501ED9104B375555EF71FBEED2B7552C3C7121F7FB4`로 manifest와 일치했다. 첫 한국어 TRAIN 행 `alm_000000`의 원 text SHA는 `5B3DBA986B04D47B7F1383FA3831707C2EE4F8405338105636BAF56B117884D0`다. 문맥/질문 전문은 여기 복제하지 않고 요청/정렬/확률에 필요한 token만 판독했다.

| 요청 | native target/prefix | cache_prompt | chosen 원 logp | top1 / top2 | 실제 timing |
|---|---|---|---:|---|---|
| 14 cold | raw326/shift325, ID21, `6`, bytes[54]; prefix326 | OFF | −27.074506759643555 | 248068 `<think>`/0.0; 248045/−19.157493591308594 | cache_n0, prompt_n326, prompt_ms768.961 |
| 15 cold | raw327/shift326, ID173905, `억원`; prefix327 | OFF | −0.12733370065689087 | 173905/−0.12733370065689087; 152049/−2.578768730163574 | cache_n0, prompt_n327, prompt_ms522.321 |
| 16 warm | 요청14와 같은 원 prefix/ID21 | ON | −27.118831634521484 | 248068 `<think>`/0.0; 248046/−19.083480834960938 | cache_n323, prompt_n3, prompt_ms130.789 |

세 요청 모두 bias100/n_predict1/n_probs2/temperature0/seed1337/`post_sampling_probs=False`, penalty 중립, truncateFalse다. `6억원`이라는 실제 token 본문을 `6`의 숫자 의미에 대한 기억/추정으로 바꾸지 않는다. top2의 빈 표시 문자열/bytes[]도 원 ID248045/248046을 제거하거나 같은 token으로 합치지 않는다. `<think>`의 logp0.0은 응답 정밀도로 반올림된 값이지 정확 확률1이라는 수학적 증명은 아니다.

원 chosen 차이는 **−0.04432487487792969 nat**, abs1e−5의 약4,432배다. 확률비 warm/cold는 약0.956643으로, 작은 절대 tail 확률이라도 기존 원 logp invariance gate는 명백히 실패했다. ID21은 cold/warm 모두 성공적으로 강제되었으므로 target 선택 실패/bias200 재시도와 이 수치 불일치는 다른 실패 축이다. 원 top2 ID도 바뀌었다. 전 행 실패를 무시하고 cold 두 token만 학습 cache로 승격하는 fallback은 원 계약과 다르다.

`timings.cache_n=323/prompt_n=3`은 실제 prefix 재사용의 관측이다. `tokens_cached=326`은 cold에도326이므로 그 필드만으로 cache hit를 입증할 수 없다는 §17의 주의를 실제 raw가 뒷받침했다. 종료는 owned exitcode0/threads_closedTrue/13회 memory sample/telemetry·raw persistence 오류0으로 보고되었다. 반면 source/input/teacher asset 종료 불변은 null/`NOT_VERIFIED_AFTER_PARTIAL_FAILURE`다. 정상 모델 종료 관측을 전후 자산 완전 검증 PASS로 올리지 않는다. wall30.7144s/startup1.7787s 및 부분 실패 원형을 보존한다.

### 20.2 두 문제를 한 원인으로 합치지 않는다

**관측 A — 조건부 입력 계약:** 원 full ChatML의 assistant 접두부는 `<|im_start|>assistant\n`이고 raw full text에 `<think>`/`</think>`가 없다. 본문 첫 `6` 직전 teacher top1이 `<think>`였다. 따라서 지금 probability는 명시 no-think 답변 모드의 정답 본문 분포라고 볼 근거가 없고, no-think 교사 prefix를 점검할 이유가 충분하다. 다만 이 한 token의 높은 `<think>` 확률이 원 QA의 의미 정답성/오답성 또는 모든 tail 확률의 무효를 증명하지는 않는다. 실제 답을 만들기 전 reasoning marker를 기대하는 조건과 짧은 정답만 바로 teacher-force하는 과제가 어긋났다는 운영 계약 지적이다.

**관측 B — 같은 원 prefix의 cold/warm 수치 차이:** 요청14와16은 같은 prefix·target·bias인데 다른 원 logp를 냈다. 그 사이 요청15의 더 긴 cold prefix327이 실행되어 warm 첫 요청326은 되감기/재사용 경계도 포함한다. 숫자 kernel/batch 경로·recurrent state rewind·서버 cache 구현 중 어느 것이 원인인지는 이 raw만으로 분해되지 않는다. 공식 b11396 README도 cache_prompt의 batch 크기 차이에 따라 logits가 bit-identical하지 않을 수 있음을 경고한다. 이것은 현 차이의 원인 후보를 뒷받침하지만 특정 Mamba cache 버그를 확정하는 증거는 아니다. [공식 cache_prompt 계약](https://github.com/ggml-org/llama.cpp/blob/b11396/tools/server/README.md#L535-L536)

따라서 **bad template가 warm 수치 차이를 일으켰다**, **cache OFF가 reasoning prefix까지 고친다**, **temperature0/seed 고정이면 원 logits도 결정적이다** 중 어느 주장도 아직 성립하지 않는다. 새 v4의 no-think+cache OFF는 두 축을 같이 바꾸는 실용적 복구 후보이며 단일원인 확인 실험은 아니다. 과거 v3 실패는 별도 이름/경로/영수증을 그대로 남기고, 새 v4 성공이 생겨도 `v3_CACHE_ON_PARITY_FAILED`를 취소하지 않는다.

### 20.3 공식 native apply-template의 정확 요청·반환 계약

§17.4의 당시 공식 source 접속 실패 기록은 보존한다. 이번에는 다른 가용 웹 열람 경로로 **동일 고정 release b11396의 원 source**를 읽었다. `/apply-template` handler는 chat parser를 그대로 부른 뒤 **`{"prompt": ...}`만** 반환한다. parser는 `add_generation_prompt` 기본True, template kwargs의 JSON boolean `enable_thinking`을 읽어 override한다. 정확 요청 위치는 **`"chat_template_kwargs":{"enable_thinking":false}`**다. top-level `"enable_thinking":false`나 문자열 `"false"`를 같은 요청이라고 추정하지 않는다. 문자열은 parser가 타입 오류로 거부한다. `reasoning_effort="none"`도 별도 공식 off 경로지만 두 옵션을 무조건 섞지 않고 한 계약으로 고정한다. [고정 handler](https://github.com/ggml-org/llama.cpp/blob/b11396/tools/server/server-context.cpp#L4805-L4815), [kwargs·generation prompt parser](https://github.com/ggml-org/llama.cpp/blob/b11396/tools/server/server-common.cpp#L1222-L1293)

이 공식 source는 현재 고정 binary의 API 후보 계약을 읽은 것이며 실제 native response를 대신하지 않는다. full GGUF 사전 metadata에 chat_template 원문이 보존되지 않은 상태라 교사의 실제 template bytes/no-think 분기·runtime jinja 설정을 이 담당이 직접 확인했다고 부르지 않는다. v4의 첫 row부터 아래 증거가 필요하다.

- 원 TRAIN messages 중 **assistant gold 이전의 user/system 메시지만** apply-template에 보낸다. original gold assistant를 완결 메시지로 보낸 뒤 새 generation prompt를 얻거나, history 안에 정답을 중복 넣어 첫 token이 자기 답을 미리 보게 하지 않는다. 문맥/질문 본문·메시지 순서·system 삽입 유무를 원본과 대조한다.
- `add_generation_prompt=True`, no-think boolean kwargs, tools/grammar/continue-final-message 등 불필요한 제어 없음과 **반환 prompt 원형/UTF8 SHA**를 기록한다. 실제 반환 suffix/think 상태·BOS/EOT·자동 system·시각 등 template가 삽입한 조건을 점검한다. 종료 marker를 수동으로 추정해 붙이거나 원 답 본문에 새 설명을 섞지 않는다. template가 no-think를 지원/반영하지 않았으면 조용히 동일 모드라 부르지 않는다.
- 반환값의 `prompt`에 **같은 원 assistant 본문 bytes만** 붙이고 full 문자열을 native tokenize한다. prefix와 body를 독립 tokenize해 ID를 이어 붙이는 방식은 경계 BPE merge를 놓친다. parse_special/add_special/BOS 정책을 고정하고 native integer ID prompt가 자동 BOS를 대신 넣어줄 것으로 기대하지 않는다. 일반 문서상 string과 native ID array의 BOS 처리가 다르므로 실제 전체 ID/첫 token도 보존한다. [공식 prompt 입력 계약](https://github.com/ggml-org/llama.cpp/blob/b11396/tools/server/README.md#L449-L456)
- apply-template는 model 내부의 추론 없는 포맷 호출이지만 모델 기동/HTTP/로그 비용0이라는 뜻은 아니다. payload와 반환을 raw에 남기고 실제 변경 없는 prefix가 반복해 같은 bytes인지도 확인한다. 새로운 template의 `<think>` 확률이 낮아졌다는 한 관측을 정답성/교사 품질 PASS의 대체 gate로 추가하지 않는다.

### 20.4 다른 native prefix의 body-byte ALM은 가능하되 더 좁은 계약이다

ALM v4 Appendix H는 모델 고유 special token 보존을 허용하고 Appendix I는 **같은 bytes의 chunk 경계**와 shifted target logp 합산을 사용한다. 공식 tokenkit도 모델별 header/special replacement와 일반 token index를 분리한다. 그러므로 student/teacher native header가 다르다는 이유만으로 body-byte alignment를 ALM 불가라고 단정하지 않는다. 반대로 이 근거가 arbitrary prefix 교체의 조건부 분포 동일성·교사 성능을 보장하지도 않는다. [ALM v4 Appendix H/I](https://arxiv.org/html/2503.20083v4#A8), [공식 tokenkit encode_prompt](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/utils.py#L485-L568)

현재 계획은 기존 full-input byte 동일성 helper와 다른 **본문 한정 native-template ALM-core 후보**다. 정담당의 새 helper 구현/회귀는 이 절에서 읽거나 실행하지 않았으므로 `DESIGNED / HELPER_NOT_VERIFIED_BY_THIS_REVIEWER`로 제한한다. 최소 확인은 다음과 같다.

- 원1024행/한영512씩/first16 원 row ID·원 text/답 bytes SHA·VAL root/context 차단 목록을 유지한다. teacher prefix를 바꾸는 일과 root_order/row 재선별·teacher confidence로 행 제외를 섞지 않는다. 실패 행도 남긴다. v3 준비/실패본은 덮거나 이동하지 않고 새 storage/소비 source identity로 분리한다.
- student/teacher 각각 full text/ID/piece의 SHA와 **자기 stream에서의 body 시작·끝 byte offset**을 따로 둔다. teacher prefix 길이를 student 원 offset으로 대입하지 않는다. 대응하는 본문 bytes는 전량 완전히 같아야 하고 문자 index/byte offset을 혼용하지 않는다. raw token index i의 target score는 자기 stream의 i−1이다.
- teacher/user/system/header/think prefix와 학생 header는 KD 대상에서 제외한다. 본문 EOT도 종전처럼 KD에서 제외하고 CE EOT 감독은 유지한다. 경계 token이 prefix와 body를 가로지르면 그 token 확률의 일부분을 본문 확률로 잘라 쓰지 말고 실패 또는 사전에 정한 제외/coverage 정책으로 명시한다. 제외 때문에 supervised ordinary bytes가 줄면 full coverage PASS로 표기하지 않는다.
- student CE의 원 전체 target 분모와 KD의 실제 aligned chunk 분모, 언어별 covered ordinary bytes/target 수를 따로 유지한다. 새 helper가 `6` 앞에 no-think token을 더 넣었다고 CE token 예산·학습 row순서·비교 초기화를 바꾸지 않는다. 두 native conditional context가 다르다는 사실은 recipe 차이로 적고 binary KL 방향/teacher detach/온도·가중치도 그대로 명시한다.

hidden/outcome-debias/GradMag OFF는 계속 별도 한계다. 다른 template에서 유효한 확률 cache를 얻어도 **논문 전체 recipe 재현**, 의미 정답 전수검수, confidence calibration, 학생 KD 효과는 아니다. no-think 올바른 답의 확률도 작을 수 있으며 낮은 chosen 확률을 답이 거짓이라는 온라인 진위검사로 쓰지 않는다. CE-only 대 ALM 비교에는 같은 초기화/동결 row순서/학생 token 노출·업데이트 예산이 필요하고 teacher scoring은 별도 준비비로 보고한다.

### 20.5 cache OFF·동일 cold 반복의 선결과 비용 함정

cache OFF는 관측 B의 재사용 경로를 피하는 합리적 대안이다. 다만 cold0 **원 logp 결정성은 새로 관측해야 하는 선결**이다. 동일 prefix IDs·같은 target/bias·동일 payload/seed로 연속 반복하고, 가능하면 사전에 고른 별도 prefix를 사이에 둔 재반복도 구분하면 이전 요청 상태 의존을 더 직접 볼 수 있다. 대상/반복 수는 결과를 보기 전에 고정하고 실패 뒤 쉬운 token만 남기지 않는다. temperature0에서 강제 chosen ID가 같았다는 것만으로 raw chosen/top logp의 일치를 PASS로 만들지 않는다.

각 반복에서 chosen ID/raw logp·top ID/logp·finite/nonpositive·길이/truncatedFalse 및 **`timings.cache_n=0`, 전체 prefix의 prompt_n**을 원형으로 보존한다. bias100/200, n_predict1, pre-sampling 확률·MTP OFF 및 raw→shifted index 계약은 유지한다. cold 반복에서도 불일치하면 template/재사용 해결과 별개로 `COLD_REPEATABILITY_FAILED`이며 cache/train-consumable 판정은 중단한다. top2가 극소 확률 영역에서 순위 교환할 가능성과 원 chosen 허용오차는 서로 다른 숫자 정책이므로, 반복 성공을 위해 abs1e−5/top ID 규칙을 사후 완화하지 않는다. 필요하면 새 허용정책/보정 실험으로 분리하고 과거 실패는 유지한다.

v3 첫 row는 ordinary body7byte가 학생/교사 모두 완전히 정렬되어도 teacher target2개와 물리3요청만에 warm 검산이 실패했다. 그 비용을16행/1024행 완료 속도라고 부를 수 없다. teacher native K개 target, 첫 body 이전 prefix 길이 P이면 cold 요청의 총 prefill은 대략 **K·P+K(K−1)/2 token**이며 실제 token 경계/row 길이를 써야 한다. 학생64 target 상한이 교사도64 target이라는 보장은 없다. 전 target cold 반복이면 기본 비용이 다시 약2배가 되고, bias200·tokenize/apply-template·raw/telemetry·shutdown이 추가된다. v3 warm의 prompt_n3을 cold326의 비용 추정으로 대체하지 않는다.

원 GGUF는8,771,311,680 B이고 이번 실패에서 시작 full SHA만 **24.6698s**였다. 전후 해시가 같은 시간이라 단순 가정해도 약49.34s이며 기동/종료/준비물 읽기·검산이 별도로 든다. 실패 후 종료 identity가 미검증된 과거 report를 새 cache의 asset 불변 증거로 재사용하지 않는다. fixed16 실측 wall/행별 K·prefix 길이·한영 비용을 먼저 회수하고 64 batch 전체에는 batch별 기동/해시 overhead와 긴 행을 반영한다. 600초/외부630초/16:30 중지 guard는 완주 보장이 아니며 PARTIAL을 보존한다.

### 20.6 선택지·권장과 실행 전 상태

`impact-analysis`의 조건/영향·3안 구분과 `exp-preflight`의 단일효과/선결 원칙을 이번 읽기 감사에 적용했다. 새 구현·명령·학습 실행 권한으로 확대하지 않았다.

| 안 | 변경 축·목적 | 장점 | 한계·비용 |
|---|---|---|---|
| A | v3 원 template 유지 + cache OFF 동일 cold 재검산 | 원 prefix를 고정해 재사용/반복성 문제만 좁힘 | no-think 조건 불일치 남음; 성공해도 지금 원하는 교사 모드 cache 아님; 별도 canary 비용 |
| B | 새 native no-think template + cache OFF + body 동일 정렬/동일 cold 반복 | 목표인 짧은 원답 모드에 더 맞고 재사용 경로를 피함 | 두 축 동시 변경이므로 원인 분리 아님; helper·prefix·cold 안정성 모두 새 선결; prefill 비용 증가 |
| C | B의 cold 안정성을 닫은 뒤 cache ON 재개 | 이후 큰 cache의 재사용 비용 가능성 탐색 | 과거 실패로 ON 선결 미충족; 증가-prefix/되감기 parity와 전 target 검산을 다시 닫아야 함; 오늘 최소 경로보다 추가 비용 큼 |

권장: 총괄이 짧은 유효 KD 준비 경로를 우선한다면 **B를 조건부 최소 운영 후보**로 삼는 것은 타당하다. 먼저 실제 native prefix/body 정렬과 사전 고정 cold 반복을 통과해야 하며, A 미수행 때문에 template와 cache 각 단일 원인은 미분해라고 남긴다. C나 전체1024 cache/학습으로 자동 진입하지 않는다. B가 실패하면 v3/v4를 섞거나 기준을 낮춰 PASS를 만들지 않고 별도 실패 영수증을 회수한다.

이 담당의 상태는 **`V3_ACTUAL_FAILURE_AUDITED / V4_PROPOSAL_SOURCE_ONLY / V4_TEACHER_AND_KD_NOT_RUN_BY_REVIEWER`**다. 새 v4 구현/실제 모델/테스트는 총괄·정담당 소유이고 이 담당은 실행·코드 수정0이다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 21. P078 완료된 두704 학습·실제8답 판독과 남은 실행의 권한 경계

### 21.1 이번 감사의 범위와 실행 원형

2026-10-23 KST08:55~09시 무렵, 총괄이 지정한 **이미 완료된** uniform_r2/balanced_count 두 팔의 report·원 update JSONL·activity·최종8답씩을 읽었다. `log-to-result`의 JSON 수치 정본/조건 서명/예측 대조와 `exp-preflight`의 중복 금지/원형·권한 경계, `impact-analysis`의 파일별 권한·영향 구분을 적용한다. 이것은 **새 학습 제안이나 완료된 두 팔의 재수행 요청이 아니다**. 연구문서 이 절 외의 코드/자료/계획/결과/원장 수정·모델/torch/프로젝트 모듈 import·테스트/검사기/SH 실행·GPU·설치·Git·하위 에이전트는0이다. 표준라이브러리로 지정 JSON/JSONL의 byte·합계·hash만 다시 계산했다. 정식 결과·계획·기준표/공유 원장 연쇄 반영은 총괄 소유다.

| 팔 | 닫힌 학습 report | report SHA256 | update raw SHA256 |
|---|---|---|---|
| uniform_r2 | [report](/home/uranus/tinyLM/test_result/evidence/p078_route_training_v1_s1337_cleanv3/train_uniform_r2/report.json) | `5BDBE586E1F0479020771B46D52ABC6072B32E1B306FE36BE00AEFE3968CE4FA` | `04645E5C82FC7AA86161ED6E1D4C00FE515065D2F08752FC48358F0B7094142D` |
| balanced_count | [report](/home/uranus/tinyLM/test_result/evidence/p078_route_training_v1_s1337_cleanv3/train_balanced_count/report.json) | `C6DF14CA7D2B37AC3B39C72A58F235441E4BBFB6FB80C62C7F0CBEF2B2B0C099` | `9B2E76404542892626188540DB256926ACAEC67880D9D8021749071F0443A1E7` |

각 status는 `ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED`다. [uniform raw](/home/uranus/tinyLM/runs/eval/p078_route_training_v1_s1337_cleanv3/train_uniform_r2/updates_000000.jsonl)는1,756,066B/704행, [balanced raw](/home/uranus/tinyLM/runs/eval/p078_route_training_v1_s1337_cleanv3/train_balanced_count/updates_000000.jsonl)는1,748,456B/704행이며 SHA·bytes·LF행수·연결 manifest/별도 manifest가 report와 맞았다. report↔activity SHA, input·authorization·canonical hash, 완료True/returncode0, PGID=PID, 당시 만료 전 종료를 독립 대조했다. activity SHA는 uniform `DB81BF8768ED61EAA8C85215EE0B00899BE679875189F9DFADAC87485D77704F`, balanced `583E40066A42D9377BBF5D483026A2D9DCBDC6A5DD9F87A0229586D3E6DB8E27`이다. 각 arm의704 update에서 model ID와 optimizer ID tuple은 각각 하나였다. source에 기록된44개 파일도 현재 bytes와 모두 같았다. 모델 weight/checkpoint를 이번 감사에서 tensor 로드하거나 다시 해시한 것은 아니다.

이미 [선택2팔 readback](/home/uranus/tinyLM/test_result/evidence/p078_route_training_v1_s1337_cleanv3/selected_readback_uniform_r2/report.json)도 `SELECTED_TWO_OF_FOUR_RAW_RECOUNTED_NO_ADOPTION`, `selected_complete=2`, `original_total=4`, `original_four_arm_study_complete=False`, router 실행False로 닫혀 있었다. SHA는 `CBC2FB7D2A9979E3379C7BDB2D12867194DDFE2174D6812E59DBCB32E3BBD7F6`다. 이 부분 검산을 네 팔 readback이나 품질 채택으로 확대하지 않는다.

### 21.2 목적·초기화·노출의 조건 서명

원 Stage2W의 질문은 **같은 학습자료·평균 방문 예산에서 방문 순서/횟수 정책을 학습 때부터 바꾸면 무엇이 달라지는가**다. uniform_r2는 매번 순차 R2, fixed_shuffle_r2는 고정 원자 그룹 셔플 R2, update_shuffle_r2는 update별 셔플 R2, balanced_count는4update당 R1/R2/R2/R3의 순열이다. 이번 완료 두 팔은 **모두 순차 방문**이므로 횟수 분포 묶음만 관측했고, 순서 셔플 질문은 아직 미실행이다. 학습형 prefix router는 이 두 본체 학습 안에 들어 있지 않다. Stage2 모듈의 learned-router placeholder와 별도 Stage3 구현 존재/실행 여부도 구분한다.

두 팔을 **본 점수를 보기 전에** 고른 주체는 사용자가 아니라 총괄의 실행 우선순위 결정이다. [원 선택 descriptor](/home/uranus/tinyLM/handoff/audit/WIP_20261022_P078_SELECTED_ADMISSION.json)는 created `2026-10-22T07:48:34+09:00`, SHA `C4CD5928CF0462DC5F4D65A6A57DE066F25C02507AACF47A4E539ABF4E61C72A`이며 selected/deferred/이유/source가 원형 그대로다. uniform 학습 시작은 같은 날10:09 KST 이후여서 descriptor는 실제 두 본 결과보다 앞선다. 다만 이미 네 비용 표본/부모/자료 감사는 본 뒤였으므로 모든 선행 관측에서 완전 맹검 선택이었다고 쓰지 않는다.

| 비교 축 | 두 팔의 확인값 | 허용 해석/남는 한계 |
|---|---|---|
| 원 input signature | 전체 dict 동일, SHA `8CA5AE1BD08524C518EFAE6D88DE987D755991B566F27D4C9F39E661BFEE43BD` | 새595M/Broad/ALM 자료의 결과가 아님 |
| 부모·초기 가중치 | P090B chat32 dense14 부모 SHA `12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950`; 실제 initial core 둘 다 `E854AB4EC2E505DDC581CE08C94F9C8B4A8081E456AFBA193DF28A877E34A193` | 비용32 가중치를 이어 학습하지 않고 같은 부모에서 각각 출발 |
| 데이터/토크나이저 | frozen cleanbilingual V3 report SHA `7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20`; chat32 tokenizer `9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E` | 같은 **동결 noisy-control**이며 정제/정답성 전수검수 완료 자료가 아님 |
| actual pool·draw | TRAIN22,528행/고유 x5,405,444/assistant552,609; 정확4pass | 매 epoch22,528행/5,405,444 x/552,609 targets를 raw 합계로 확인 |
| 최종 노출·예산 | 각90,112행·x21,621,776·assistant2,210,436·704update; dummy0 | 704×8×16×1024=92,274,688은 padded 계산 slot이지 실제 학습 x token 수가 아님 |
| 순서·샘플링 | 고정 manifest 순서에서 `batches`가 epoch마다 `Random(1337+epoch)` 순열, 모든 행1회; replacement 없음 | 두 팔704개 update의 epoch/행수/x/target 수가 모두 대응. 실행 raw에는 개별 행 ID 목록이 없어 행별 동일성 재증명은 동결 manifest·같은 source/seed에 의존 |
| 모델/최적화 | 14층=2+10+2, dim768; m8×a16, width1024, checkpoint ON, eager/compile OFF, teacher/MTP OFF; Adam5e−5/Muon2e−4 | 상수 절대 LR/4pass704 지평. 원300M WSD 또는 P101A compile recipe의 단독 효과 비교가 아님 |
| 정밀도 | 학습 BF16 autocast, 실제 VAL/첫답 FP32 MATH/TF32 OFF/cache OFF | 보고된 VAL FP32를 학습 전 과정 FP32 실행이라고 부르지 않음 |
| 변경축 | cfg 차이는 train_repeat cap2→3뿐; 실제 uniform704×R2, balanced R1 176/R2 352/R3 176 | 평균 R2이지만 상한/gradient 경로·주평가 정책도 다름 |
| VAL/첫답 | 같은 VAL512/2,977 target, 같은8 question/prompt IDs·greedy 첫 시도1회·max160 | primary는 각 자기 정책; 같은 weights에서도 before CE가 달라질 수 있음 |
| 주장 등급 | primary 정책 묶음 비교는 `PARTIAL_CONFOUNDED`(train/eval route 동시 변경);8답 질 판독은 `DESCRIPTIVE_ONLY` | 훈련 횟수 랜덤화 **하나만**의 효과·learned routing·일반지능/실제 추론 능력 인과 분해 불가 |

source [batches](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:81)·[actual update](/home/uranus/tinyLM/scripts/p078_route_training.py:169)·[훈련/평가 controller](/home/uranus/tinyLM/scripts/diag_p078_route_training.py:364)를 직접 대조했다. 원 V3의 PUBLIC192/198 두 첫답 감독 주석 누락은 [P078 계획](/home/uranus/tinyLM/test_plan/P078_재귀는-reasoning인가-방문의-선택성.md:220)의 제한대로 유지한다. 456개는 제외 대상 첫답 전체 target 분모이지 전부 거짓 token 수가 아니다. 같은 오염을 공유한다고 정답 신호가 복구되는 것은 아니며, 그 두 행만으로 모든 실패 원인을 설명할 수도 없다. 새 정제본으로 바꿔 남은 두 팔을 같은 가족인 것처럼 잇는 것도 조건 변경이다.

**평균 방문량의 작은 함정도 실제로 계산했다.** 두 팔 모두 padded layer-visit slots2,214,592,512이고 train 방문수의 update 평균은 정확24다. 그러나 actual x에 방문수를 곱한 합은 uniform518,922,624 대 balanced519,074,744(+0.0293%), assistant target에 방문수를 곱한 합은53,050,464 대52,869,824(−0.3405%)다. 즉 원 token 노출은 같되 **내용/지도 token으로 가중한 방문 노출까지 정확히 같지는 않다**. balanced의 input-weighted 평균 방문은24.0070, target-weighted는23.9183이다. 이는 사전 random-count 설계 안에서 생긴 배정 차이이며 임의 보정하지 않는다. 평균 padded 예산 일치를 exact FLOPs·유효 token별 연산·시간 동일성으로 확대하지 않는다.

### 21.3 epoch별 CE와 고정704 최종의 실제 음성

TRAIN CE는 raw update CE×그 update의 실제 assistant targets를 가중 합산했다. VAL은 다른 고정512행/2,977 target의 FP32 자기 정책 CE다. 다음 전 숫자는 report 또는 raw 독립 재계산과 일치했다.

| 시점 | updates | uniform TRAIN CE | balanced TRAIN CE | uniform 주 VAL CE | balanced 주 VAL CE |
|---|---:|---:|---:|---:|---:|
| 학습 전 | 0 | — | — | 6.440286413 | 6.600031111 |
| epoch1 | 176 | 2.921506351 | 3.002745371 | **2.210306647** | **2.291023069** |
| epoch2 | 352 | 2.335013206 | 2.406173050 | 2.400894480 | 2.407769537 |
| epoch3 | 528 | 2.032838266 | 2.122820061 | 2.638945885 | 2.496060611 |
| epoch4/최종 | 704 | 1.780019668 | 1.894805785 | 2.667774655 | 2.650580304 |
| 704 update 전체 가중 TRAIN 평균 | 704 | **2.267344373** | **2.356636067** | — | — |

두 팔 모두 TRAIN CE는 계속 내려갔지만 관측한 VAL 네 시점 중 **epoch1이 최소**, 이후 최종은 각각+0.457468008/+0.359557235 악화했다. 이는 과적합/감독 잡음·분포 일반화 한계를 의심할 실제 패턴이며 원인 단일 확정은 아니다. 사전704/마지막 CP 계약은 그대로 유지하고 사후 epoch1을 새 주 결과로 바꾸지 않는다. 전체 평균 train_ce와 최종 VAL은 같은 checkpoint/같은 정밀도/같은 행의 손실이 아니므로 둘의 차를 곧 schedule 계측 오류라고 단정하거나 과거 pretraining의 `val−train_ce` 자를 그대로 적용하지 않는다.

자기 정책 최종 balanced−uniform은 **−0.017194351 CE**다. 같은 초기 weight인데 before가+0.159744698 다른 이유는 balanced VAL도 batch별 R1/R2/R2/R3로 평가했기 때문이다. 따라서 before→after 개선량 차이를 순수 학습효과 추가분이라고 빼지 않는다. 공통 순차R2 **secondary**에서는 uniform2.667774655 / balanced2.618869947, 차 **−0.048904709**다. 이 공통 inference 대조는 주평가와 다른 질문에 대한 유용한 진단이지만 원 source가 `COMMON_UNIFORM_MISMATCH_SECONDARY`로 지정한 값을 사후 주지표로 승격하지 않는다. 이 한 seed/VAL에 맞는 반복 학습 σ·판정자는 이번 증거에 없고 `_rulers.py`에도 이 새 SFT 가족의 정당화된 자를 찾지 못했다. 과거0.024/0.07 또는 다른 benchmark 자를 복사하지 않는다.

### 21.4 최종8답씩 — 종료·문체 변화와 정답성은 분리

두 report의 실제16개 최종 answer 문자열을 **전부 읽었다**. 다음은 짧은 원문/반복 특징이며, 생략표시는 여기 표의 축약일 뿐 원 JSON은 그대로다. prompt/질문은 두 팔 동일했고 전후 각 팔의 prompt IDs도 같았다. uniform은 모든 사례R2, balanced의 사례별 R은 아래와 같다. 사후 정성 판독이지 정식8문항 benchmark/채택 게이트는 아니다. 모든 원 `semantic_score`는 계속null이다.

| 고정 질문 목적 | uniform 실제 답·판독 | balanced 실제 답·판독 | balanced R |
|---|---|---|---:|
| KO 2+3, 숫자만 | `1` — 숫자 형식이지만 값 오답 | `1` — 동일 오답 | 3 |
| EN 7−4, 한 자리 | `7 minus 4 is the 6th largest...` 뒤 largest/important 반복 — 값·형식 실패 | `7 minus 4 = 6` 뒤4.5/6.5 반복 — 값·형식 실패 | 2 |
| KO 과일2개, 쉼표만 | `1. 쉼표로 구분하여 쓰세요.` — 지시 되풀이, 과일 없음 | `{"answer": "great"}` — 다른 형식/내용으로 대상 혼동 | 2 |
| EN result=5인 JSON만 | `Sure, here's a key difference between key_square and key_square:` 뒤 Define 반복/MAX160 | `Single key result and integer value 5.` — 짧아졌지만 JSON 아님 | 1 |
| KO 물이 얼면 | `물리적인 위치는 물과 물, 물, 성분이...` 뒤 위치 반복 — 질문 답 없음 | `가운데이션` — 질문 답 아님 | 2 |
| EN 인간이 사는 행성, 한 단어 | `The planet Earth is a planet in the solar system, with its moons and moons.` 반복/MAX160 | `The planet Earth is a small planet with a diameter of about 5,000 kilometers (3,3,3,...` /MAX160 | 3 |
| KO 문맥의 비밀단어 재기입 | `별빛` — 요구 충족 | `별빛` — 요구 충족 | 2 |
| EN 모든 빨간 상자는 무겁다, 이 상자는 빨갛다, yes/no | `Yes` — 이 사례의 요구 충족 | `Sure, here's a clear and simple way to get the red boxes to run:` 뒤 lightweight/black box 목록8회 — 무관/주어진 조건과 충돌 | 1 |

행성 두 답은 **Earth를 언급했다는 부분 내용**과 한 단어 요구 위반·반복을 함께 적는다. balanced는 새 수치 단언까지 만들었으나 이번 감사는 외부 사실 벤치가 아니므로 그 문장을 맞는 지식으로 승인하지 않는다. `별빛` 재기입 한 사례는 단기 문맥 복사가 된 관측이지 보편 기억·새 지식 추론을 확보했다는 뜻이 아니다. uniform의 logic 한 성공도 balanced R1 실패와 함께 그대로 보존하며, 그 차이는 훈련 weights와 해당 추론 R이 모두 달라 순수 R 증가/감소 인과 효과로 분해하지 않는다.

실제 종료는 uniform STOP_SEQUENCE6/MAX_NEW2, balanced STOP_SEQUENCE7/MAX_NEW1이다. **더 잘 멈추고 더 짧게 답했다는 관측을 답변 품질 PASS로 올리지 않는다.** 균형 팔의 JSON/과일/수학/물 질문은 짧게 종료해도 실패한다. 학습 전에는 위키형 각주/분류·무관 언어·반복이 많았고 SFT 뒤 문장/형식의 표면 변화는 보이지만 현재16답에서 반복·대상 혼동·기본 계산 실패가 남았다. 두 팔 완료/CE 감소/낮은 memory peak는 일반지능·원 P078 reasoning 가설·온라인 진위검사 또는 자료 채택의 증거가 아니다.

### 21.5 balanced gradient 최대는 원 update2/R3 — finite·clip과 안정성 구분

[실제 update source](/home/uranus/tinyLM/scripts/p078_route_training.py:199)는16micro backward 뒤 **clip 전** gradient의 원소 절댓값 최대를 기록하고, 이어 global `clip_grad_norm_(…,1.)`의 반환 **clip 전 norm**을 기록한다. 유한성 검사 뒤에만 optimizer.step이 이어진다. 따라서 report grad_max31.1666을 clipping 이후 남은 최대 gradient로 오해하지 않는다.

| 팔/실제 update | epoch/R/방문 | clip 전 최대 원소 | clip 전 global norm | 당시 TRAIN CE·분모 |
|---|---|---:|---:|---|
| uniform 최대 update2 | 1 /R2 /24 | 5.894256592 | 10.490004539 | CE4.195007409; assistant3222/x31939 |
| balanced 최대 update2 | 1 /R3 /34 | **31.166595459** | **62.580734253** | CE5.426917514; assistant3222/x31939 |

두 최대가 같은 자료 노출 수의 update2에서 발생했고, 이미 앞 update1의 R2/R1로 weights 궤적이 갈라졌으므로 원 update2의 차이를 고립된 R3 한 번의 효과로 부르지는 않는다. balanced의 grad_max>10인 update는 **2/8/9/15/20** 다섯 개뿐이고 **전부 epoch1·R3/34방문**이다. 그 값은 순서대로31.166595/19.738831/17.973404/12.189798/11.333496다. 이후 epoch2~4 최대는3.344162/3.106682/2.732841이며 uniform 전체에는>10이 없었다.

두 raw704개 모두 기록 CE/시간/gradient_max/norm은 유한·양수였고 source의 nonfinite loss/gradient/norm 실패 없이 완료됐다. 이는 **clip을 거쳐 유한한 실제 학습이 끝난 운영 관측**이다. balanced 최대에서 norm1로 줄이는 명목 scale은 약0.0159794지만 실제 post-clip tensor별 최대/norm이나 optimizer state 전량을 raw로 독립 측정한 것은 아니다. 큰 초반 gradient를 안정성 PASS로 숨기거나 반대로 clipping 전31.17만으로 NaN 발산/학습 실패라고 재명명하지 않는다. 현재의 정확한 문구는 **“초반 R3 큰 gradient 관측, finite/clip 경로로704 완료; 장기/다중 seed 안정성·품질 채택은 미입증”**이다.

### 21.6 이전 예측·실제 update 시간·worker 경과시간의 세 층

원 네 비용32 report도 같은 input signature/`COST32_COMPLETE`임을 읽고 원 `cost_forecast` 식을 표준라이브러리로 다시 계산했다. **완료 팔의 실제 시간은 과거 예측을 지우지 않고 별도로 기록한다.**

| 시간 종류 | uniform_r2 | balanced_count | 의미 |
|---|---:|---:|---|
| 비용32에서 본704 훈련 보수 예측 | 6714.666601s | 8155.608097s | 첫 회+최대 warm×703×1.35+600, 실제 완료시간 아님 |
| 과거 별도 평가/첫답 예측 | 411.309223s | 519.804770s | 별도 예약이며 위/아래와 혼합 금지 |
| **실제704 update seconds 합** | **3510.492578s /58.5082분** | **3492.276526s /58.2046분** | raw 합계, model load/VAL/첫답/저장 등 제외 |
| 실제 update 평균/중앙 | 4.986495/4.966651s | 4.960620/4.943034s | 인쇄 누적 ms/step를 그대로 인용한 값 아님 |
| activity `seconds`(perf_counter) | 3701.610890s /61.6935분 | 3680.210499s /61.3368분 | 시작/평가/저장 포함 worker의 해당 clock 관측 |
| activity `utc_seconds` | **4046.553322s /67.4426분** | **4037.419464s /67.2903분** | 기록된 실제 UTC 종료−시작 |

**새 시간 주의:** activity의 UTC 경과가 perf_counter보다 uniform344.942432s, balanced357.208965s 길다. uniform 시작/종료는 KST10-22 **10:09:19.888614→11:16:46.441936**, balanced **11:16:49.329596→12:24:06.749060**다. 원 activity 자체가 두 clock의 다른 경과를 저장했고 이번 감사는 그 원인을 조사하거나 한쪽으로 덮지 않았다. 이를 곧 GPU kernel 지연·모델 가속·clock 결함의 특정 원인으로 단정하지 않는다. 사용자가 기다린 달력상 구간을 설명할 때는 UTC 시각 차를 함께 보이고 perf/update 합만으로 “총약1시간”이라 축소하지 않는다. `budget/actual_spent`는 source상 activity의 perf `seconds`를 더하므로 새 만료/whole cap 확인에는 **현재 aware UTC와 이 clock 불일치**도 별도 주의가 필요하다.

기존4팔 전체31,028.581375s=8.619050h 예측 및 선택2팔 약4.5~4.9h 예약은 당시 보수 비용 계획이다. 실제 두 update 합은7002.769104s이며 둘의 worker perf 합7381.821389s/UTC 구간 합8083.972786s와 구분한다. source/설정 변화 없이 상한형 예측보다 짧았다는 것을 새 알고리즘2배 가속의 증거로 쓰지 않는다. 다른 순서 정책의 실제 미래 시간을 이 두 평균으로 대체하지 않는다.

### 21.7 남은 두 셔플 — 기존 런처 재사용 조건과 새2026-10-23 authority

한 번의 지정 경로 존재 조회에서 `train_fixed_shuffle_r2/report.json`, `train_update_shuffle_r2/report.json`은 없었다. **원4팔 중2팔만 완료**이며, 새 결과/실패를 만들기 위한 실행이나 대기 loop는 하지 않았다. [남은 두 팔 SH](/home/uranus/tinyLM/run_P078_Stage2We_remaining_shuffle_pair.sh)의 source SHA는 `E9EAEA1BA713ED32CF33EFE3E6E8C8B29F1152AA33478B12BF1696BB180515EA`, [JSON 검산 adapter](/home/uranus/tinyLM/scripts/diag_p078_route_protocol.py)의 SHA는 `9C43170866E73E4B9B45DA0E54796B4B251C2238B56C5567916BB3872680CF77`다. 이 SH는 이미 완료한 uniform/balanced의 closure·CP SHA를 선결로 검산하고 **fixed/update 두 팔만** 학습한 뒤 원4팔 readback을 부른다. 완료 두 팔을 다시 학습하는 흐름이 아니다.

현재 사용자10/23 수행 허가는 **만료된 파일의 날짜를 자동 연장하지 않는다**. 기존 두 학습의 authorization SHA `BF0081F631C53D0DD6B57B14D87A70BA0DB9BE17F31AC2537B729BF46B5394DD`는 expires **10-22 16:30 KST**다. 역사 closure는 당시 만료 안에 끝났으면 보존되지만 오늘 새 worker의 입장권은 아니다. 남은 실행자가 닫아야 할 최소 경계는 다음과 같다.

1. **새 별도 descriptor/bytes SHA**: schema `P078_TRAIN_EXECUTION_AUTHORIZATION_V1`, 원 tag/input signature `8CA5…43BD`, `allow_gpu_training=True`, 현 사용자 승인 reference·새 aware 만료·family cap144000초·실제 worker cap을 명시한다. 원 두 report/activity/authorization/선택 descriptor는 덮지 않는다. 과거 selected-stage wrapper는 `HARD_STOP=2026-10-22 17:00 KST`가 source에 박혀 있으므로 오늘 새 선택 descriptor만 넣어 완료 두 팔을 재호출하는 경로가 아니다.
2. **같은 원형 source/자료/부모/optimizer와 runtime provenance**: 원 driver/helper의 PINS 및44개 source/corpus/tokenizer가 같은지 검사하고 원4비용과 두 완료 결과를 그대로 소비한다. 다른 V4 코퍼스·parent·LR·마스크로 바꾸면 새 비교이며 원4팔을 완성한 것이 아니다. SH는 `tinylm_python`을 쓰되 `TINYLM_PYTHON` override가 가능하므로 실제 해석된 Python 절대 경로·버전/패키지 metadata·GPU/backend·기동 명령/새 auth SHA를 새 원로그에 고정해야 한다. 과거 source SHA만으로 실행환경까지 같다고 입증되지는 않는다. 평가 전용 Core6 venv 설치 권한과 학습 runtime 변경 권한도 섞지 않는다.
3. **원 cost 재사용·fresh budget 검산**: cost32를 재수행하라는 뜻이 아니다. 현재 같은-source closure/원 raw·전체 family activity를 다시 읽고 이미 완료한 두 팔 forecast를0으로 만든 **남은** 예측을 현재 UTC에 대조한다. 원 식 기준 fixed6549.815180+평가442.682413, update6057.658215+평가377.036875, reserve1800으로 합 **15,227.192683s=4.2298h**다. 이는 지금 새 admission을 실행한 결과가 아니라 보존된 cost 식의 파생값이다. 미완료/실패 activity가 있으면 숨기거나 삭제하지 않는다. 선택 readback 시점 actual_spent8231.681779s는 당시 누계이지 오늘의 fresh 누계라고 복사하지 않는다.
4. **전체 worker cap도 남은 승인시간에 들어가야 함**: 기존 SH는 각 train14400초, readback1800초를 요청한다. 새 authority의 max_worker가 옛10800이면 즉시 불충족이다. 예측이 약4.23h에 맞더라도 다음 worker의 **4h cap 전량**이 현재 남은 UTC보다 크면 시작 gate에서 HOLD다. cap 변경이 필요하면 총괄이 사용자 승인 범위 안에서 명시된 별도 실행 계약/launcher provenance로 정해야 하며 이 담당은 기존 SH/guard를 수정하거나 우회하지 않았다.

원 `closed`는 역사 실행의 당시 만료/입력/원답을 검증하고, `authority`는 **새 실행의 현재 UTC**를 검증한다. 역사 권한이 만료됐다고 성공한 두 학습을 무효/미실행으로 바꾸지도, 성공한 역사 학습이 있다고 새 권한을 생략하지도 않는다. 당일 source/date 변경을 위해 PINS·만료·ARMS·미완료 보존을 느슨하게 만드는 복구는 범위 밖이다.

### 21.8 prefix router — 본체 선결은 생겼지만 GPU router는 아직0

이번 한 번의 지정 조회에서 [Stage3 prepare](/home/uranus/tinyLM/test_result/evidence/p078_prefix_router_bootstrap_v3_s1337/prepare/report.json)는 있었고 cost/labels/fit/evaluate/readback report는 **없었다**. prepare SHA `54169072026E5C01FA8D0989173F63DA1BA3D39684E37E772B17B1BE8A676C0A`, status `ROUTER_SPLIT_PREPARED_BODY_NOT_LOADED`, source drift0다. 원 holdout metadata SHA는 `C6B42D5A56E9608AF953A9E7614E28A74E16038A1CF6EAEDA303937E8639D6AC`, DEV256/TEST256 각각 KO128/EN128, 공식 **TRAIN** annotation을 쓰고 `official_eval_gold_inputs=0`, fully_pipeline_blindFalse다. body 원 VAL512는 변경하지 않는 별도 holdout이다. 이번 감사는 holdout 원문을 학습/교사/Luna에 전달하지 않았고 의미/오염 전수검사를 새로 한 것도 아니다.

그 prepare authority는 **10-21 23시 만료/allow_gpu_training=False/body_checkpoint_sha256=null**인 CPU 준비 전용이다. 반면 오늘 사용할 과학 본체의 선결인 balanced_count704는 이미 존재한다. report에 고정된 CP SHA **`A9CA3B99EABCC08C3E8BD58FDBFEC90AB999A637F820DAA25E1F7470F2037196`**, final core **`8C3957569BE189BC07BDA84548981D91BB6B38D19CE8153269D63FC1D5A68025`**가 새 router authorization의 본체 대상이다. 본체를 다시 학습하거나 uniform/더 좋은 새 모델로 고르는 승인이 아니다. 선택2팔 원형 검산 뒤 그 사전 지정 balanced를 동결하여 router 비용부터 본다는 10/22 계획의 제한적 순서 변경과, 원4팔 전체가 아직 미완이라는 사실을 함께 유지한다.

이미 [Stage3 SH](/home/uranus/tinyLM/run_P078_Stage3Wc_prefix_router_full.sh)와 [독립 driver](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py)는 구현돼 있다. SHA는 SH `85217653A7D20AD3AC458FA5EC6F423D9D4203FA683E2EB0D7AE96069327F4EE`, driver `8A27979E6DE4B1DDD367843803E06A61F2CABA737DF8B09414E9407738F76199`다. Stage2의 `--mode router` placeholder를 실행하는 경로가 아니다. body frozen/gradient0·전후 fingerprint·CP SHA, TRAIN22528만 R1/R2/R3 상대 CE labels, prefix-only feature, 작은 CPU head5epoch, DEV1/3/5선택, TEST learned/random_quota/untrained/constant_train_mean 네 정책의 별도 흐름이다. 상대 CE 최소 예측은 gold 정답성 판단기나 문항별 online oracle가 아니다.

**실행자에게 필요한 별도 새 권한/원형 증거:** schema `P078_PREFIX_ROUTER_EXECUTION_AUTHORIZATION_V1`, tag `p078_prefix_router_bootstrap_v3_s1337`, 현재 exact source/corpus/holdout/body-source 전체 signature, 위 balanced CP SHA, `resource_only_r1=False`, allow_gpu_trainingTrue, 새 aware expiry/worker cap/family144000초 및 descriptor bytes SHA가 필요하다. 과거 CPU prepare는 역사 source/입력/closure가 같으면 재사용 대상이지 GPU 허가로 승격되는 것은 아니다. 실행 때 실제 CP bytes·full-row standalone prefix/target boundary/그룹 분리를 검산하는 선결은 유지한다. source가 바뀌면 과거 prepare/cost를 같은 서명으로 조용히 수리하지 않는다. R1 parent의 resource-only 우회는 labels/head/TEST 과학 경로를 승인하지 않는다.

**비용·날짜의 함정:** 기존 SH는 `cost→budget→labels→fit→evaluate→readback` 순서다. 비용8이 아직 없으므로 **1.5h는 미측정 임시치**이고 학습704의58분을 router 비용으로 대체할 수 없다. actual cost8/별도 feature·생성·head 시간 뒤 모든 미실행분을 예약하는 gate가 실제 입장을 결정한다. 또한 기존 fixed caps는 cost/budget/readback1200초, labels21600초, fit7200초, evaluate14400초다. 만약 총괄이 새 authority도16:30 KST 만료로 잡으면 **labels는10:30 이후, evaluate는12:30 이후, fit은14:30 이후** 시작에서 whole-cap 입장 조건을 충족하지 못한다. 단순히 forecast가 남은 창에 맞는다는 이유로 이 full cap guard를 통과한 것으로 볼 수 없다. 줄인 cap/단계별 호출이 필요하면 승인된 별도 실행 계약으로 명시해야 하며 이 감사는 그 변경을 구현/실행하지 않는다.

Stage2 family 시간은 원 학습 namespace의 activity, Stage3 `spent`는 router namespace activity를 읽으므로 두144000초가 자동으로 **하나의 공통 누계**인 것은 아니다. 오늘 전체 허용시간/다른 P106B 작업과 GPU 단독 사용의 합산·단계 우선순위는 총괄이 별도 현재 UTC 원장으로 관리해야 한다. 기존 SH의 “Current body704 is NOT_RUN” 콘솔 안내와 P078 계획/결과066의 옛 미실행 문구는 역사 snapshot에서 낡은 부분이며 현재의 두 닫힌 report보다 우선하지 않는다. 이것을 근거로 완료 두 학습을 다시 실행하지 않는다.

### 21.9 최종 판정

**완료 관측:** 같은 초기화/동결 V3/실제 row·x·target 노출의 두704 학습, 각 CP1개, 원 raw/closure와8답씩 판독. **음성/한계:** 초반 balanced R3 큰 gradient, epoch1 이후 VAL CE 악화, 짧게 멈춰도 남는 계산/형식/대상 혼동, 원4팔 중2팔만 완료, 단일 seed/잡음 자료/정답성 null. **미실행:** 남은 두 셔플 본학습·원4팔 최종 readback·router cost/labels/head/TEST/효과, 이번 담당의 모든 모델/GPU/테스트 실행.

판정은 **`P078_TWO_OF_FOUR_COMPLETED_RAW_AND_ANSWERS_AUDITED / NO_QUALITY_ADOPTION / REMAINING_AUTHORITY_SOURCE_REVIEW_ONLY`**다. 이 감사는 완료된 두 학습을 다시 수행하라고 제안하지 않는다. 새10/23 권한이 필요한 경우는 **기존에 안 한 남은 두 팔 또는 별도 prefix-router 단계**이며, 역사 원형/두 실패형 답변 묶음/gradient·clock 차이를 그대로 보존한다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 22. BabyLM2026 BLiMP 선택 AST·실제 full-logits 접합의 반 검토

### 22.1 결론·소유권·현재 source snapshot

**고정 공식 causal 함수 본문을 선택 로딩하고 기존 strict 모델의 실제 full logits를 넘기는 안은 타당한 최소 후보**다. SciPy를 가짜 모듈로 대체하거나 원 source를 고치는 안과 다르다. 다만 함수의 원문 동일성만으로 tokenizer/모델 호출·padding·RNG·분모까지 같아지는 것은 아니다. 표기는 **“BabyLM2026 고정 공식 함수 재사용, 별도 native adapter, BLiMP main/supplement 부분 과제”**로 제한한다. 공식 package 정상 import/CLI 실행·leaderboard 제출·전체 BabyLM suite·대회 참가자격 또는 모델 학습예산 대조가 아니다.

총괄의 P078 남은 두 셔플 GPU 작업과 원형44개 source 잠금을 인지했다. `impact-analysis`의 파일 권한/호출 경로/선택지 원칙과 `exp-preflight`의 실제 실행·정적 검토 분리를 적용했다. 이번 담당은 자기 연구문서만 추가하고 **코드/원 source/데이터/모델/설치/환경/Git 수정0, 프로젝트 함수 compile/exec/import·torch/tokenizer/model import·모델/GPU/테스트 실행0, 하위 호출0**이다. 표준라이브러리로 원문 AST/byte/hash만 읽었다. 평가 문항/정답은 학습·교사·Luna에 전달하지 않았다. 스킬의 registry/check-only 호출도 실행하지 않았다.

읽은 문헌담당 문서는 [문헌 감사 §11~13](/home/uranus/tinyLM/docs/research/20261023_acceleration_distillation_literature.md:420)이며, 그 주장과 별도로 아래 고정 원 source·기존 Core6 adapter/loader·실제 새 helper를 직접 읽었다. 최초 좁은 파일 조회 때 새 helper가 없었으나 검토 중 총괄이 신설해 뒤에 실제227행 전부와13개 회귀 **source**를 읽었다. KST09:26 이후 이 절이 고정한 snapshot은 다음과 같다.

| 파일 | SHA256·현재 감사 수준 |
|---|---|
| [새 선택 loader/processor/rank helper](/home/uranus/tinyLM/scripts/p106b_babylm_causal.py) | `97BF41E2600D99E2636A55EBDF8296404987127EF8EF33878C2626A7D0C425C2`; 전227행 읽음, 실행0 |
| [새 합성 회귀 source](/home/uranus/tinyLM/scripts/test_p106b_babylm_causal.py) | `AF10CB06D3B4D85C9813A581132C9C88B5C62DC8F54ECDA79DB7C7B6485551F5`; 전167행/13개 test 정의 읽음, PASS 관측은 이 담당0 |
| [기존 Core6 numerical adapter](/home/uranus/tinyLM/scripts/p106b_official_lm_adapter.py) | `E9FA2B17B5E8E27453C39889B6A3C5F97444B87550DB850B3D3FBC38E570CBC5`; strict runtime·full logits·route/precision 경로 추적 |
| 기존 Falcon 실제 modeling source | `E90BF774524E9B66284AD1C5528C35339271A187F58F16BA2D45C97F4BC6B5BD`; Core6 실행 영수증의 구현 SHA와 같음, 모델 실행 아님 |

현재 새 helper에는 공식 함수 선택/processor/rank 감사가 있지만 **실물 모델 full-logits wrapper나 전량 실행 runner는 이 파일에 없다**. 따라서 아래 P1은 구현된 원형 helper의 열린 결함, 아직 새 접합에 필요한 선결, 회귀 미검증을 구분한다. 이 파일 밖 새 구현까지 검토 완료했다고 확대하지 않는다.

### 22.2 원문 동일성·폐쇄 — 무엇이 실제 공식 함수인가

고정 commit은 `6f825c291e2c4c78ad33b1935fd64d45f52642dc`, 로컬 root는 [선택 원천](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp/source/strict/evaluation_pipeline/sentence_zero_shot)다. 다음4파일의 실제 bytes/SHA256·manifest Git blob SHA1을 이번에 독립 재검산했다.

| 공식 파일 | SHA256 | 선택한 원 node·줄 범위 |
|---|---|---|
| `read_files.py` | `742386554D9C7F80E7ED15EF7DFA6D186B29A4ADF6C832C94BFD4254840B1A8F` | `decode_blimp`92–130 |
| `dataset.py` | `133DA1300DDB10D3D7D2B42859D662C25986F6CDCB457721C3DA693E8F00571A` | instance method `process_causal_sentences`55–107; outer factory `get_causal_collate_fn`420–453 |
| `compute_results.py` | `DDCE8DE7185E1C29F13B05A8F76AC2FAB04A386DA86CAE693C7B7F38B198FC83` | `update_subset_to_stats`51–57; `rank_and_evaluate`60–88; `compute_causal_results`90–144 |
| `run.py` | `1E4B11F53DD71A6203ED7936160774BB634220C54EEA605BAE70503B57432668` | `process_results`74–110 |

새 helper의 FILES 상수는 이4파일과7개 node를 정확히 고정한다. `selected_node`는 정확 owner의 instance method를 찾고 decorator/`__class__` capture를 거부한다. 실제 원 node에는 decorator/default가 없고 `super` 사용도 없다. 선택 AST에는 `from __future__ import annotations`가 추가되어 미사용 AutoProcessor/PIL/argparse 타입을 런타임 annotation 때문에 import하지 않는다. collate 내부 함수만 분리하지 않고 outer factory 전체를 선택하므로 **pad_idx의 실제 closure**도 유지한다.

공통 namespace에 실제 `torch`, `torch.nn.functional`, `Counter/defaultdict`, `pad_sequence`, 명시 DEVICE/길이정규화 task 집합을 넣어 helper 간 참조를 유지한다. BLiMP는 정규화 task 집합에 없고 temperature는1.0 하나다. 기본 progress는 원 tqdm가 아니라 **순서를 그대로 넘기는 identity callable**이며 proof에 그 대체를 더 구체적으로 기록할 필요는 있다. package init의 TokenizersBackend alias/AutoProcessor/SciPy/원 DEVICE 초기화는 실행하지 않는 **별도 로딩 계약**이다. 사용하지 않는 SciPy 의존을 충족했다고 주장하거나 설치 권한을 넓히는 경로가 아니다.

P2 source binding 보강점: 현 `load_official:66–69`는 file_sha를 계산한 뒤 파일을 다시 read_text한다. 보존 source에 동시 writer가 없다는 현재 조건에서는 실질적 충돌 관측이 없지만, 엄밀히 **검증한 bytes와 AST를 만든 bytes가 한 번의 동일 read로 묶이지는 않는다**. 원문 bytes를 한 번 읽어 hash/parse/node 증거에 사용하는 방식이나 동등한 전후 stat/hash 증거가 더 강하다. 파일 SHA와 node의 canonical AST SHA/원 줄 범위는 모두 남기고, AST 본문 재작성·가짜 dependency·별도 scalar LL을 logits로 꾸미는 우회는 제외한다. 이 담당은 source를 수정하지 않았다.

### 22.3 실제 helper에서 이미 닫힌 부분과 미완료를 분리

현재 source는 single-token flat list의 원 method 오인 분기를 **길이<2 명시 거부**로 먼저 차단한다. 추가 BOS/가짜 token을 넣지 않는다. `len(native_tokens)−1<=1024`, offsets의 원 문자 범위, empty text/비어 있는 shifted phrase target·모양 불일치도 거부한다. main/supp 모두 원 `decode_blimp`를 호출해 good/bad·label0·field/UID를 그대로 쓴다. 이 실패 정책은 원 CLI가 비정상값까지 계속 숫자화하는 동작과는 다르므로 **유효 입력에서의 공식 함수 재사용**이라고 밝힌다. 거부 행이 실제로0인지 전수 검사 전에는 full 평가 가능이라고 확정하지 않는다.

`RankAudit`는 원 compute의 globals에 감사 wrapper를 연결하고 **원 rank 함수 자체를 한 번 호출**한다. 이어 같은 CPU RNG 시작 상태에서 index·Counter/prediction을 독립 재생하고 원 rank 종료 RNG를 복원한다. 부동소수점 F32 값을 Python float로 옮기는 것은 exact F32 값 자체를 보존하며 epsilon tie를 새로 만들지 않는다. finite/CPU/F32/2후보·행수·default device CPU 검산, 원 macro와 별도 micro의 구분, label0/always-first100%의 누설 경고도 있다. 이것은 원 함수 본문은 보존하면서 **전역 binding에 관찰 계층을 추가한 구현**이지 아무 wrapper도 없는 공식 CLI와 같다는 뜻은 아니다.

검토 중 처음 본 중간본은 prediction defaultdict를 set 순회로 미리 만들고 Counter를 dict로 비교했으나, 위 고정 snapshot에서는 **`.get`+최초 UID 순서**로 관찰하고 **Counter 대 Counter**로 비교하도록 이미 바뀌었다. 후자는 공식 correct Counter에 명시0이 남는 경우를 Python3.10의 Counter 동등성(없는 key=0)으로 비교한다. 이전 dict 비교였다면 첫 UID 전부 오답에서 zero-key 차이로 가짜 실패가 생길 수 있었지만 **현재 열린 결함으로 중복 보고하지 않는다**. explicit all-wrong UID/batch 회귀는 추가 가치가 있다. 이 정정은 source 판독이지 해당 회귀 실행 PASS의 대행이 아니다.

### 22.4 P1 — full 입장 전에 닫아야 하는 실제 인터페이스·수치 선결

| P1 항목 | 직접 source 근거·실패 모양 | 필요한 계약/확인 |
|---|---|---|
| **원 scalar LL이 아닌 실제 full logits** | Core6 `LikelihoodCore.score_encoded`는 scalar/greedy를 반환. BabyLM 원 compute는 `input_ids/attention_mask`를 받고 tuple[0] 또는 dict['logits']의 **B×T×V**를 읽음 | strict runtime 재사용 뒤 별도 thin wrapper가 실제 head 출력을 전달. native tokens 인자, logits_last_onlyFalse/return_hiddenFalse, Falcon logits_to_keep0·use_cacheFalse. LL 숫자로 가짜 logits를 만들지 않음 |
| **Falcon HFLM 호출 경로** | 고정 HFLM `_model_call:1140–1145`는 attn_mask를 주면 labels도 요구하고 **Seq2Seq class를 assert**함. causal Falcon에 mask만 넣어 기존 메서드를 그대로 쓰면 실패 | HFLM의 이미 strict하게 연 실제 model에 공식 attention_mask를 넘기는 얇은 호출이 필요. 새 model loader/remote code/FP16 fallback을 만들지 않음 |
| **우회하면서 잃을 Core6 guards** | `lm.core.score_batch.forward`를 직접 쓰면 TorchLikelihood의 외부 no_grad/autocast OFF/route 활성/shape·finite 검사를 자동 계승하지 않음. 선택한 원 compute의 no_grad는 바깥 dispatcher에만 있었음 | caller의 eval/no_grad/FP32·MATH/TF32 OFF·route assert·정확 model/tokenizer/CP·전후 core/원본 보존을 별도 유지. source helper에 있던 guard를 재사용했다고 말만 하지 않음 |
| **text-only shape와 자동 잘라내기** | 원 compute:122–123은 길이 불일치 시 이미지 전제를 두고 마지막 T를 crop함 | 새 text-only wrapper가 **공식 함수에 돌려주기 전** exact `[B,T,V]`/FP32를 검증. 긴 위치축·last-only·잘못된 hidden을 원 crop이 숨기지 못하게 함 |
| **pad ID/mask·state reset** | native forward에는 attention_mask 인자가 없음. Falcon은 mask를 attention/recurrent 양쪽에 사용. pad를 실제 token으로 역추정하면 EOS와 pad가 같은 경우 원 token까지 지울 수 있음 | 원 collate의 right-pad mask 그대로 사용. native는 오른쪽0꼬리 외 left/interior mask를 거부하고 유효 prefix의 singleton/batch parity로 제한. past/cache/MTP0, 요청 순서 교환 뒤 같은 유효 logits/LL 확인 |
| **score 지원 범위/비정상 처리** | 원 gather×mask는0×NaN/−inf도 NaN이 될 수 있고 rank는 NaN→−inf 동점까지 숫자화. 새 RankAudit는 비유한 score를 거부 | masked/nonmasked 위치·nonfinite/빈 mask·overflow를 수치 무효로 보존. 행 삭제/분모 축소·0점/0.5점 대체로 full을 만들지 않음. 모든 모델에 실제 거부0이어야 full 분모 주장 |
| **RNG/입력 순서·한 번의 판정** | 원 rank는 global torch RNG·정확 tie. RankAudit는 이를 복원하지만 시작 상태/선행 난수 소비는 caller 소유 | 모델 생성·canary·DataLoader 생성/반복 뒤 full 평가 시작 상태를 명시 고정. main/supp/model별 새 stats/audit·원 pair/후보 순서 유지. rank를 추가 호출해 통계를 두 번 누적하거나 문항별 reseed하지 않음 |

**실제 Falcon pad 차이:** 기존 Core6 report에는 tokenizer pad=`<|end_of_text|>`/ID11, BOS=None, EOS11이 기록돼 있다. model config의 pad0/bos1과 구분해야 한다. 현재 tokenizer_config도 EOS만 지정한다. BabyLM 원 constructor는 tokenizer pad가 없으면 EOS를 pad로 쓰므로, model.config.pad_token_id0을 무조건 쓰는 것은 그 정책과 다르다. 실제 strict runtime의 tokenizer/pad/자동 special 처리 값을 새 영수증에 남기고, 본문 token ID11이 있다고 임의로 지우지 않는다.

**정확1024 경계:** 원 causal collate는 전체 L tokens를 받은 뒤 입력을 `[:-1]`로 만들어 **T=L−1**을 forward한다. 그러므로 입력 문맥1024의 경계는 L1025 허용/L1026 거부이며 현 TextProcessor도 이 식을 쓴다. full 문장 L을1024로 제한해 불필요하게 일부를 버리거나, 반대로 source의 자동 crop에 의존해 초과를 통과시키지 않는다.

### 22.5 P2 — 첫 token·순서·진단 기준·보존의 해석 함정

1. **문장 전체라고 모든 text token을 지도하는 것은 아니다.** BOS 없는 `[a,b,c]`의 원 점수는 `log p(b|a)+log p(c|a,b)`다. 첫 native token은 조건일 뿐 점수 밖이다. 실제 tokenizer가 BOS를 넣으면 첫 text token이 들어가지만 별도 newline/chat/BOS를 추가하면 다른 사건이다. 양 모델의 첫 token 분절/offset이 다르다는 사실까지 기록한다. 공정성의 명목으로 토크나이저 하나를 공동 사용하거나 첫 token을 사후 보정하지 않는다.
2. **RNG는 DataLoader도 소비한다.** 실제 설치 torch의 `torch/utils/data/dataloader.py:706–710`은 iterator 초기화에서 shuffleFalse/worker0이어도 base_seed를 global generator에서 뽑는다. 한 번의 `manual_seed`를 모델 생성 전 걸었다는 사실만으로 원 rank의 시작 RNG가 같아지지는 않는다. list iterator 대 DataLoader, iterator 생성 전후 seed, cost/canary tie가 full 난수열에 들어가는지를 기록한다. source에 seed 옵션이 없으므로 이 seed/순서 고정은 추가 재현 계약이다. 두 모델의 tie 위치/수가 다르면 같은 seed도 문항별 같은 tie 선택을 보장하지 않는다.
3. **원 filesystem 순서는 미정이다.** 원 `read_files`는 정렬 없는 iterdir다. 새 manifest 순서를 사전 고정해 네 모델에 공통 적용하는 것은 합리적이나 원 CLI의 그날 filesystem 순서를 재현했다고 쓰지 않는다. filename/line/UID/원문 hash·좋은/나쁜 후보 순서를 보존하고, 효율상 정렬 후 반드시 rank 이전 원 순서로 복원한다. UID별 prediction ID도 최초 등장 순서에 민감하다.
4. **길이 기준의 tie에는 label 누설이 있다.** 현 `shortest_correct/longest_correct`는 문자 길이 동점이면 첫 후보를 골라 good-first/label0의 정답을 자동 얻는다. 최소쌍은 같은 길이도 많을 수 있으므로 이 수치를 곧 내용 비사용 기준의 우위로 읽지 않는다. `equal_character_length_pairs`와 동점에서0.5를 배정한 **별도 진단 기대값**을 함께 기록하거나 최소한 첫 후보 tie 우선/100% 누설 기여를 명시해야 한다. 모델의 공식 exact-tie 무작위 score를0.5 credit로 바꾸자는 뜻은 아니다. helper의 always-first100% 경고는 타당하다.
5. **허용오차와 예측 일치는 별개다.** helper의 ATOL1e−5/RTOL1e−4는 현재 실물 parity를 입증하지 않는다. |LL|100이면 상대오차만 약0.01nat를 허용할 수 있어 작은 good−bad margin의 순위가 바뀔 수 있다. score 오차와 함께 margin·chosen index/exact tie 변화/불일치 수를 보존한다. “allclose면 accuracy도 같다” 또는 epsilon tie는 사용하지 않는다.
6. **무한 logits 저장/거대 최종 JSON을 피할 별도 저장 계약이 필요하다.** 원 compute는 raw scores를 직접 반환하지 않고 전체 prediction dict를 RAM에 모은다. 새 RankAudit sink는 scores/chosen/margin/원문을 관찰할 수 있지만20MB 초과 방지·write-once shard·manifest·원본 불변·실패 PARTIAL/종료 proof는 아직 호출자 책임이다. wrapper가 RNG를 재생한 뒤 원 종료 상태로 복원했는지와 예외 후 원 rank binding 복구도 남긴다. 점수 보고만을 위해 원 Torch/F를 fake proxy로 바꾸지 않는다.

### 22.6 합성 oracle와 실물 oracle — 현재 실행하지 않은 구체 선결

새13회귀 source는 decode, 3행 서로 다른 candidate 길이의 right-pad/shift, mask hole의 공식 causal 대 독립 Python-LSE, UID macro75 대 micro66.6667, tie RNG/복구, NaN 거부, mock native BOS/EOS offsets, single-token/overflow 거부와 원문 보존을 다룬다. 이것은 좋은 **source상 검사 범위**이며 이 담당은 실행하지 않았다. mock tokenizer·상수 logits fixture 성공만으로 실제 tokenizer나 full model 접합을 검증했다고 할 수 없다.

| 선결 | 합성 또는 실물에서 확인할 것 | 현재 판단 |
|---|---|---|
| AST·함수 폐쇄 | 파일/노드 canonical AST SHA/줄·보조 함수 binding·future annotation·pad closure·실제 globals 상수/장치; 상단 SciPy/package init 미실행 | 새 source에서 설계 확인, 이 담당 compile/exec/import0 |
| 독립 합우도 | 작은 full-vocab logits에서 각 `z_target−logsumexp(z_all)`를 별도 FP64/stdlib로 계산; first-token 제외/BOS/EOS/내부 mask hole/후보별 다른 T·B=3 | 기존 mask-hole fixture는 B1·고정 logits. 모델 wrapper가 **실제 전달된 input_ids/mask에 의존**하는 추가 fixture도 필요 |
| zero/실패 경계 | 한 UID 전부 오답, 여러 UID 최초 batch 모두 오답, 근접하지만 비동점, 양쪽 NaN/−inf/0×NaN, sink 예외 뒤 binding/RNG 보존 | 일부 NaN/tie source는 있음; 명시 all-wrong/연속 batch·근접 margin·예외 fixture 보강 여지 |
| 정확 길이 경계 | L1025가 T1024로 통과, L1026 거부; 빈/한 token 문장과 zero-scoreable mask를 BOS 없이 실패 보존 | overflow/single fixture 있음. 경계의 **허용 쪽** L1025 fixture는 현재13개 정의에 없음 |
| 실제 native tokenizer | 같은 사전 고정 문장에 실제 ID/offset/attention/phrase, first/last score target, 선두 공백/개행/구두점/비ASCII·special-like text; raw tokenizer 결과와 façade 일치 | mock만으로 미확인, 실제 CPU tokenizer oracle 별도 |
| 실제 full-logits wrapper | 각4모델의 strict runtime에서 모델 full-label CE 또는 독립 gather oracle와 같은 collated input/target/mask score 대조; exact full shape/FP32/무절단/무cache·route 유지 | 기존 Core6 synthetic PASS를 자동 이월하지 않음. 신규 실물 `NOT_RUN_BY_REVIEWER` |
| right-pad/state parity | 같은 pair singleton/다른 길이 동반 batch/앞뒤 순서 교환, good/bad forward 순서 교환 후 원 순서 복원; EOS=pad와 내부 special 포함 | native는 mask를 받지 않고 Falcon은 recurrent mask도 있어 실제 관측 필요. LL 근접성과 판정 일치 함께 기록 |
| 분모/UID/순서 | main67 UID/59,875 pair와 supp5 UID/5,218 pair의 원 파일·행·SHA 일치, 모든 모델 같은 pair 집합·거부0, 정확 UID별 correct/total·prediction ID·raw SHA | §14의 고정 snapshot 수량 유지. 새 tokenizer 전수지원/실행 분모는 아직 미관측 |

독립 수치 oracle에 동일 `F.log_softmax/gather/sum`을 한 번 더 호출하는 것만으로 충분하다고 하지 않는다. 실제 checkpoint를 다시 학습하는 검증도 아니다. 합성 검산은 모델 없는 구조·숫자 증거, 실제 4모델의 고정 소수 oracle는 해당 backend 접합 증거, 전량 완주는 정확 두 과제 분모의 결과이며 서로 승격하지 않는다.

### 22.7 주지표·자격·비용과 세 경로의 최종 분리

main의 주점수는 **67 UID 정확도의 동일 가중 percent macro**, supplement는 **5 UID의 별도 percent macro**다. 59,875/5,218 pair micro는 진단이며 두 과제를72 UID로 합친 점수나 Core6 fraction(0~1)과 혼동하지 않는다. main/보충을 task='blimp'로 부르는 것은 공식 shell과 같지만 두 독립 집계/상태를 유지한다. 원 filtered 분모65,093pair=130,186문장/모델이며 이 문장 수가 실제 forward 호출 수와 같다는 뜻도 아니다.

원 개발환경/정상 CLI로 가장 가깝게 가는 A, 이번 원 causal full-logits 접합 B, 문헌§13의 기존 encoded scalar LL 접합 C는 서로 다른 경로다.

| 경로 | 실제 실행하는 점수 함수·장점 | 한계·영향·비용 |
|---|---|---|
| A 정상 공식 package/CLI | 원 import/AutoProcessor/모델/compute를 모두 사용 | 현 무승인 SciPy/넓은 의존·remote-code 경계. 설치 확대는 별도 허가이고 이 감사는0 |
| **B 선택 AST + 실제 full logits** | 원 process/collate/causal LL/rank/집계까지 실제 호출; 이번 목표에 가장 직접적 | 얇은 native/HF wrapper와 위 oracle/P1 필요. full B×T×V 메모리/새 저장·RNG 계약. 공식 CLI가 아닌 부분 task adapter |
| C 선택 함수 + 기존 encoded LL | loader/scalar likelihood 재사용량이 큼 | 원 causal likelihood loop를 대체하며 mask 연속성/첫 token/수치·attention 접합의 별도 parity 필요. 같은 공식 causal 함수 실행이라고는 못 함 |

무설치/원형 보존 목표 안의 **조건부 권장 방향은 B**다. 원 source의 Strict README도 순수 PyTorch 적응 경로를 허용하지만 그것이 모든 새 adapter의 수치 동등성을 자동 승인하는 것은 아니다. TinyLM600M token draw/한국어 노출·다회 SFT와 Falcon 사전학습은 strict-small100M/strict1B **누적 words**의 참가예산과 같은 단위가 아니다. 네 체크포인트가 해당 track의 적격자/동일 학습예산이라고 비교하지 않는다. 이 두 과제는 영어 문법 최소쌍 진단이며 한국어·대화·reasoning·진위검사·전체 BabyLM 성과를 대신하지 않는다.

비용은 실제 full-logits 경로에서 새로 관측해야 한다. V32768/B8/T1024의 FP32 tensor 하나만 **1GiB**이며 원 `logits/temp`와 full log_softmax도 추가 큰 tensor를 만든다. 원 기본 batch64 또는 Core6의 continuation-row-only softmax 메모리/시간을 복사하지 않는다. B8도 실측 안전이 확정된 값은 아니다. 사전 길이/UID 대표 비용과 실제 token 분포·원형 검산/기동/softmax/집계·저장/종료 비용을 나눠야 한다. P078 학습 worker와 모델을 겹쳐 열지 않고 그 작업 종료/idle·현재 수행 권한을 실행 소유자가 먼저 확인한다. 이번 담당은 비용 실행/새 권한 발급/모델 개방을 하지 않았다.

상태는 **`BLIMP_AST_HELPER_SOURCE_REVIEWED / FULL_LOGITS_BRIDGE_P1_AND_REAL_ORACLES_PENDING / NO_INSTALL_NO_MODEL_NO_EVAL_BY_REVIEWER`**다. 현재 source만으로 새 full BLiMP 점수나 원 CLI 재현 PASS를 만들지 않는다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 23. ALM V6 UTF-8 probe 연결의 GPU 전 독립 source 감사

### 23.1 범위·동결 식별·증거 수준

총괄의 요청에 따라 V6 수집기1440행/회귀817행, 확률 helper343행/회귀400행을 전부 읽었다. 정식 [Stage7b0We/Wh/Wi 계획](/home/uranus/tinyLM/test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md:7728), [문헌 §14~16](/home/uranus/tinyLM/docs/research/20261023_acceleration_distillation_literature.md:718), 기존 native TF parser·세션·종료·GGUF header parser의 해당 호출 구간과 대조했다. `impact-analysis`와 `exp-preflight`를 읽기 전용의 비교·실패 경계 검토에 적용했다. 공유 WIP/계획/실행 원장은 총괄 소유이므로 수정하지 않는다.

| 읽은 파일 | SHA256 | 정적 확인 |
|---|---|---|
| `scripts/diag_p106b_alm_cache.py` | `49D8DB4B7A3242956F9D5E5F9DD3131FE428DC378715B5517486300608EC3B81` | V6 전용 BASE, 함수/실제 caller 연결 |
| `scripts/test_p106b_alm_cache.py` | `7EA27E5F998BC854DF4998A8D703ACE23AF20428953E93B756F89BBEF344C696` | AST상 test 함수61개 |
| `scripts/p106b_alm_utf8_probability.py` | `5707ED0B8BC8FD67E33204FF03AC7B186DE04FA29CAC0404D4EABDC1F9AC7EB7` | 부분 질량은 관측 전용으로 바뀜 |
| `scripts/test_p106b_alm_utf8_probability.py` | `71C66352F9D52C4A25BD24A7E9B2AB0454A9AB0A69484E70BEA9AF66B66BA71E` | AST상 test 함수28개, 질량1/미세 초과 수용 회귀 |

함수 수/해시는 stdlib AST·바이트 읽기로만 확인했다. **이 담당의 project import/compile/exec·회귀·모델·GPU·HTTP 요청·설치·Git·추가 agent는0**이다. 공식 고정 웹 소스는 읽기만 했으며 로컬 반입0이다. 실제 QA/정답/평가 문항·선택 shard·V5 실패 raw는 열지 않았다. 총괄의 CPU218 통과와 V5 source/helper 원판 txt 보존은 **총괄 회신**이며, 이 담당이 그 실행·감사 txt 전부를 새로 검증한 것은 아니다. V6 실물은 요청 당시 **NOT_RUN**이다.

요약 판단: **probe를 원 target으로 바꾸지 않는 수치 전달, 고정17행, bounded K 및 과거 실패 보존은 source상 연결됐다. 다만 현재 함수가 자동 수용하는 응답 범위와 계획의 엄격한 실물 판정 사이에는 아래 P1 두 가지가 남는다.** 이는 GPU 안전사고가 관측됐다는 뜻이 아니라, 예정 canary의 완료 상태를 원 확률 보존 입장권으로 읽기 전에 닫아야 할 검증 차이다. 코드 변경·실행 선택은 총괄 소유다.

### 23.2 source상 닫힌 연결과 부분 질량 정정

1. **같은 원 선택·추가 실패행:** `SCHEMA`/`root_order`는 V1을 유지하고 BASE만 `p106b_alm_context_v6_s1337`로 분리한다. `canary_rows:572`는 `rows[:16]+[rows[34]]`의17개 서로 다른 prepared SHA를 요구한다. `validate_prepared_rows`는1024개 원 순서/서로 다른 root/ko-en 교대를 검사한다. 따라서 계획의 canary는 **한영8+8에 원 index34의 ko1행을 더한 ko9/en8**이며, 대칭16행만의 평균과 같은 분모가 아니다. V5의 완료32행을 V6으로 읽는 경로가 아니다.
2. **실제 native no-thinking·body-only:** nested `enable_thinking=False`를 실제 `/apply-template`에 보내고, 비어 있는 `<think>…</think>`가 닫힌 assistant prefix인지 확인한다. 원 assistant 본문은 renderer에 넣지 않고 그대로 append한다. 학생 원형/CE EOT는 유지하고 두 template의 assistant body byte 구간만 정렬한다. teacher 전체 IDs/pieces는 별도 두 tokenize 응답의 ID 일치·전체 UTF-8 재구성·1024 이내를 거친다. header/think/EOT를 KD에 넣지 않는 기존 조건을 바꾸지 않았다.
3. **fragment만 별도 조회:** `force_target:795`는 실제 native piece bytes의 strict UTF-8 완결 여부로 분기한다. 불완결이면 cold가 아니거나 probe registry가 없을 때 중단한다. `probe_target`는 원 정답의 native prefix를 그대로 사용하고, 선택 probe만 bias로 바꾼다. 결과의 `target_id/raw_logprob`는 원 top-K의 정수 reference ID에서 오며 실제 `chosen_probe`와 별도다. 다음 target prefix는 동결 `ids[:raw_index]`에서 만들므로 probe A/B를 정답 이력에 append하지 않는다.
4. **사전 상한·누락:** K는64→512→2048, bias는100/200만 허용한다. 정상 probe가 실제 선택됐는데 target이 없으면 같은 K에서 bias를 바꿔 target을 만들지 않고 다음 K로 간다. 최종 누락은0확률·probe logp 대입이 아니라 실패다. reference target/top2 비교도 실제 선택 ID가 서로 달라도 원 target ID/logp와 원 top2만 비교하도록 분리됐다.
5. **probe registry의 증거 수준:** header의 embedding/output shape 일치와 두 번째 축으로 vocab 크기를 얻고, A/B 각각 parse_special OFF/ON에서 단일 동일 ID·정확 ASCII bytes인지 확인한다. ID 두 개도 달라야 한다. 이 registry는 full GGUF vocabulary/token-type 전수가 아니라는 경고를 이미 기록한다. helper의 `special_token_ids`도 관측 marker 집합이지 완전한 special registry라고 승격하지 않는다.
6. **질량 정정 확인:** helper:312 부근은 원 top-K exp 합과 top-K 밖 chosen probe를 중복 없이 더한 known mass, 정확1/초과 flag를 남길 뿐 이것으로 거부·보정하지 않는다. 원 target/top2/logp를 나누거나 clamp하지 않는다. 새 회귀도 합1/미세 초과를 원값 그대로 관찰하는 계약이다. 잘못된 actual flag/ID/길이/순위/양수·비유한·sentinel·조회 누락에 대한 별도 검사는 유지됐다.

부분 질량 정정은 타당하다. 고정 upstream의 `get_token_probabilities`는 전체 원소에 FP32 softmax를 적용하며 K별 partial sort가 합산 순서를 바꾼다. 정확한 실수 부분합의 성질을 JSON logp의 재exp 합에 그대로 강제할 수 없다. 다만 질량 관찰 전용화 자체가 raw 확률의 보증도 아니다. [고정 공식 softmax 소스](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-common.cpp#L1444)

### 23.3 P1-A — 완결 piece의 직접 강제 경로는 실제 응답 계약을 충분히 검사하지 않는다

새 probe helper는 actual `truncated=False`, 생성1, evaluated prefix 길이, 종료 유형, raw/backend flag·K/seed/중립 설정·chosen ID/bytes를 검사한다. 반면 **실제 완결 token의 `force_target:807–824`는 `timings.cache_n==0`, legacy 확률 parser, chosen ID 일치와 chosen logp 비양수만 확인**한다. legacy `probability_entry`는 completion 객체1개/top 최소2개/일부 유한성만 검사한다. `probe_controls`의 직접 쪽도 actual flags 일부만 추가했을 뿐 동일한 전체 envelope 검사는 아니다.

구체 실패 시나리오는 다음과 같다. 정상 control을 먼저 통과한 뒤 한 complete-piece 응답이 **`truncated=True` 또는 `tokens_evaluated!=len(prefix)`**인데 chosen ID/logp/top2와 cache_n0은 그럴듯하게 반환한다. 동일한 잘못된 조건에서 두 번 답하면 `compare_reference_scores`까지 통과하며 그 값이 cached chunk 합에 들어갈 수 있다. 실제 이 현상이 발생했다는 관측은 없지만, **source의 수용 조건상 차단되지 않는다.** `n_predict=1`을 요청했다는 사실과 응답 객체가1개라는 사실은 실제 입력 무절단/정확 생성1을 대신하지 못한다. 공식 final은 이 필드들을 별개로 직렬화한다. [고정 공식 final 응답](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-task.cpp#L323)

원 response를 먼저 저장한 뒤 **complete target과 probe 양 경로의 공통 actual 계약**을 대조하는 검사가 필요하다. complete target은 한글/공백 등도 가능하므로 ASCII 전용 helper를 그대로 억지 적용하거나 문자열 replacement로 target을 바꾸지는 않는다. actual 생성수·평가 prefix·무절단·종료·native ID·raw/backend·MTP OFF·설정의 검사와 source/response provenance를 맞추는 것이 목표다. 과거 TF parser source 자체를 바꿔 Stage7a의 동결 증거를 무효화하기보다는 현 controller 경계에 국소 검사를 두는 안이 영향이 작다. 이 담당은 수정하지 않았다.

추가로 legacy parser는 top entry의 작은 양수 `<=1e-6`을 허용하며 `force_target`의 엄격 비양수 검사는 **chosen target만** 닫는다. 실제 top 전체의 비양수/순위·길이 계약까지 검사됐다고 쓰면 과장이다. 학습에 들어가는 chosen target의 양수 거부는 이전 §17.8의 정정대로 유지돼 있으므로 그 닫힌 결함을 다시 열린 것으로 보고하지 않는다.

### 23.4 P1-B — 정상4 controls는 네 쌍 내부 비교이지100/200·A/B 전체의 동일성 검산은 아니다

`probe_controls:901–926`은 A100/A200/B100/B200 각각에 대해 **그 probe·그 bias와 같은 K의 직접 target forcing**을 새로 받고 쌍 안에서 target logp/top2를 비교한다. K2 직접 쪽과 K64 probe 쪽을 섞던 함정은 닫혔다. 그러나 네 결과 사이 비교는 없고 각 control의 성공 K도 독립이다.

따라서 동일 prefix에서 **bias100일 때 direct/probe 모두 target logp=-2, bias200일 때 둘 다=-3**을 반환하는 잘못된 공통 변형은 각 쌍이 같아4개 모두 passed가 될 수 있다. A와 B의 호출 시점마다 공통 수치가 달라지는 경우도 쌍별로만 같으면 통과한다. 이 숫자는 실제 교사 관측이 아닌 source의 판정 공백을 설명하는 합성 예다. 원 top2도 각 쌍 안에서만 같도록 만들면 현재 검사는 이 반례를 배제하지 않는다. 기존 Stage7a의 독립2문구 검산은 유지되지만 이번 prefix에서 네 조건 전체가 bias-invariant라는 새 실물 증명으로 대체할 수 없다.

**판정 문구를 “동일 bias/K의 direct↔probe4쌍 parity”로 제한할지, 아니면 네 조건 전체의 원 target/top2 불변성을 별도로 요구할지 먼저 구분해야 한다.** 후자가 계획 의도라면 가능한 한 같은 K에서 이미 받은 네 결과를 교차 대조하는 것이 최소 보강이며 새 교사 호출을 반드시 늘리는 일은 아니다. K가 달라졌다면 차이를 bias 때문이라고 단정하거나 tolerance를 사후 완화하지 않는다. 기존 abs1e-5와 top2 ID 규칙은 임의 변경하지 않는다.

`closed_batch:1211`도4개와 각 passed만 확인하므로 같은4개 전체 비교를 대신하지 않는다. 저장 control의 `(probe_id,bias)`가 정확2×2이고 양쪽 K/prefix가 같은지 독립 closure에서도 대조하면 보고서의 네 개라는 개수와 실제 비교 계약을 더 직접적으로 묶을 수 있다. 현 함수가4개를 생성하는 정상 loop 자체에는 개수 오류를 찾지 못했다.

### 23.5 P2 — 실패 분류·원 실패 사건·반복 범위·고정 K의 한계

| 항목 | 현재 source와 구체 경계 | 해석·후속 확인 |
|---|---|---|
| 선택 실패와 schema 실패의 분리 | `probe_target:846`은 tokens가 `[probe_id]`와 다르면 parser 전에 `PROBE_NOT_FORCED`로 넘김. tokens 누락/타입 오류/잘못된 stop·flags가 함께 있어도 같은 분기 | 잘못된 ID1개로 정상 생성한 **실제 forcing 실패**만100→200 회복해야 한다는 주석보다 넓다. 예: tokens=[]와 raw flag 오류가 함께 나온 첫 응답 뒤 두 번째가 정상일 때 첫 계약 실패가 자동 중단되지 않음. raw는 보존되므로 삭제는 아니지만 실패 분류와 retry 허용 범위를 나눠야 함 |
| 누락과 강제 실패의 원인 | 최종 ValueError 문구가 target missing와 probe not forced를 합침. controls는 `"absent from bounded"` 문자열로 잡아 다음 K로 감 | missing은 K 증가의 근거, forcing 실패는 bias 문제다. 최종 실패를 “target이 top2048 밖”이라고 단정하지 말고 원 attempt별 상태를 유지. 예외 문자열 하나로 두 원인을 같은 coverage 판정으로 읽지 않음 |
| 원행34 포함 대 실패 token 회수 | canary17행/동일 SHA 검사는 있으나 완료 조건이 원 V5 실패 target36054/piece `[236,155]`의 **실제 FOUND 경로**를 명시 요구하지는 않음 | 고정 같은 native 입력이면 재등장할 것으로 예상되지만 source 판독만으로 실제 회수를 확인하지 않음. 원행34의 예상 prefix/target/bytes와 `probability_origin`·선택 probe가 대응했는지 실물 metadata로 확인. 행 포함만으로 UTF-8 누락 복구 PASS를 선언하지 않음 |
| canary/full 반복 범위 | canary는 전 selected target을 cold1pass 뒤 cold2pass. `--cache`에서는 `verify_all_cache=False`이므로 **행 첫 target만**2회, 나머지는 cold1회 | 보고 scope는 이미 이를 구분함. full1024의 모든 target을2번 검산했다고 쓰면 틀림. 계획의 “모든 대상 두 번”을 canary 범위로 명확히 하거나 다른 계약은 새로 동결. warm key는 두 번째 cold라는 주석 유지 |
| cold 반복의 실제 K | repeat는 성공 bias를 시작점으로 다시 K64부터 탐색하며 첫 pass의 성공 K를 강제하지 않음 | 경계 rank/순위 변동이면 서로 다른 K에 도달할 수 있음. target ID/logp/top2가 우연히 abs1e-5 안이면 source 비교는 통과하므로 K 차이도 기록해 같은-K 반복과 구분. 미세 차이를 cache 오염·bias 왜곡으로 자동 인과 해석하지 않음 |
| 첫 정상 target control의 coverage | 첫 행의 첫 strict-UTF8 완결 target 하나를4controls에 사용. 그 원 target이 top2048 밖이거나 bias100으로 직접 forcing 안 되면 canary 중단 | 제한된 API 회수 경로의 HOLD이며 문항 의미/교사 품질 실패가 아님. control을 쉬운 문항·높은 확률 token으로 사후 바꾸거나 원행34를 빼서 성공시키지 않음 |

본 절의 반례들은 actual V6 failure 로그가 아니라 **읽은 source에서 도출한 미차단/미검증 시나리오**다. 실제 데이터의 어떤 행이 해당하는지는 조사하지 않았다.

### 23.6 종료·원형 보존과 비용의 실제 주장 범위

`execute`는 준비본 source SHA와1024행 해시/순서, Stage7a 성공 및 원 raw manifest를 먼저 요구한다. 새 cache는 정확 현재 코드·준비본·원 input·교사 자산/런타임 SHA에 묶이며, canary closure 없이 full 새 batch를 열지 않는다. `new_directory`/`xb`는 기존 partial·원 V1~5를 대체하지 않는다. report/code/input/asset 전후 MATCH, 모든 원 행 완료, telemetry/raw 오류 없음, owned thread 종료 및 raw/cache manifest 검증을 성공의 선결로 둔다. end hash를 못 하면 **NOT_VERIFIED_AFTER_PARTIAL_FAILURE**이지 원형 유지 PASS가 아니다. 성공 전에 assets의 full hash를 교사 teardown 뒤 다시 검사하는 경로도 확인했다.

다만 이는 **시작/끝의 관측 identity**이지 실행 도중 변경됐다가 복원되는 모든 경우의 불변 증명은 아니다. 보고서 자체를 해시 검증한 원본이라고 재귀적으로 주장하지도 않는다. 현재 P078 실행 소스44개 보존 감사/동시 모델 금지는 총괄 실행 게이트의 별도 책임이며 이 담당은 해당 파일을 수정·전수 재해시하거나 GPU 상태를 조회하지 않았다.

시간에는 source/prepared/선결 읽기, 원 input 재해시,8.77GB 교사 전후 hash, startup·등록·row tokenize·scoring·저장·shutdown을 모두 포함시킨다. 요청마다30초 reserve와 남은 HTTP timeout을 계산하며, 마지막 worker/owned PID 미종료·오류·wall 초과는 negative status다. `wall_seconds`는 최종 report 쓰기 **직전**의 값이고 writer close/마지막 report write는 wall_limit 블록 밖이다. 따라서 이전 정정대로 외부630초와16:30 실제 모델 정지 여유가 필요하며, **모든 최종 JSON의 flush까지 정확600초 보장**은 아니다. 초과/외부 kill 시 부분 증거를 보존하고 새 성공으로 합치지 않는다.

비용 단위도 구분해야 한다. normal4controls는 모두 K64에서 성공하면 **최소8 completion**이며, 각 쌍이3개 K를 시도하면 최대24 completion이다. fragment lookup은 K가 모두 missing이면 통상3회, 실제 forcing 실패가 섞이면 사전2bias×3K의 최대6회다. canary는 원 target별2 cold pass에 이 비용이 붙고, 학생64 target 상한이 teacher target64를 보장하지 않는다. 같은 본문의 재요청/K상향/control은 새 자료·새 고유 target이 아니다. raw attempt의 K/bias/성패·prefix 길이·응답 bytes와 unique target/완료 행을 나눠 실제 비용을 회수해야 한다.

기존 `_http_json`은 응답 body를2,000,000B까지만 읽고, shard는19,999,999B의 별도 한도다. 후자는 HTTP가 임의 크기 응답을 모두 보존한다는 뜻이 아니다. K2048 안에서도 실제 response 크기를 확인하고 overflow/JSON 실패는 PARTIAL로 남긴다. 이 한도를 이유로 K=V·다중 token·stream/서버 교체로 자동 확장하지 않는다. 최초17행은 원 첫16+추가 ko 실패행이고 controls/hash/startup 고정비도 있으므로 `17행 wall×1024/17`만으로 full 비용을 정하지 않는다. 실제 teacher target 수·prefix 길이·fragment/K 분포·batch별 기동/검산 비용과 남은16:30창을 함께 봐야 한다.

### 23.7 회귀 범위·최소 회수 순서·세 선택지

현재61개 controller 회귀 source에는 원 선택/VAL 단위, UTF-8/shift/EOT, 원 template/질문 edge trim, cold 검산/누락, logging/flush/seal/thread·오류/파일20MB, 부분 보존/closure, deadline, fragment ID lookup/K상향·bias subset·17행 선택이 있다. helper28개에는 actual envelope/설정·ID/bytes/K·원 top 순위/양수·비유한/sentinel·무변이와 **질량 관찰 정정**이 있다. 그러나 V6 `native_ascii_registry`의 GGUF shape↔두 native probe 연결, `probe_controls`의4쌍 생성/교차차이, **native cache_row가 실제 fragment helper를 지나가고17행 closure/execute까지 이어지는 전체 mock 연결**은 현61개에서 직접 호출·실패 주입으로 검산하지 않는다. 원 non-native/warm 회귀의 다수가 통과해도 이 새 연결을 전부 검증했다는 뜻은 아니다.

비용이 작은 회수 순서는 **P1의 응답 guard·4controls 판정 계약 확인 → 그 경계를 합성 실패 주입으로 검산 → 고정17행 실물에서 target36054의 ID/bytes/prefix/조회 origin과 같은-K raw parity·전 target cold 반복·시간/종료/identity 회수 → 남은 창 안에서만 full 비용 판단**이다. 이 순서는 새 GPU/학생 학습을 승인하는 명령이 아니다. full1024 closure가 없으면 CE/ALM 학생 비교용 완성 cache가 아니며 GradMag/hidden/outcome OFF와 정답성 미심사도 그대로다.

| 선택지 | 범위·장점 | 비용·한계 |
|---|---|---|
| **A. V6 controller 국소 guard/검증 계약을 닫은 뒤 고정17행** | 원 binary/모델/학생·자료와 helper의 원값 보존. 이번 새 질문에 가장 직접적 | 총괄의 source 재동결/회귀·준비 identity 갱신 필요. 실제 target coverage/비용은 아직 미확인 |
| B. 현 source를 수정 없이 관측 진단으로만 사용 | 추가 구현 비용 없이 실패/응답 raw를 모을 수 있음 | 위 자동 수용 공백 때문에 `ALM_CANARY_COMPLETE`만으로 엄격 원 확률 입장권이라고 못 부름. full/KD 자동 진입을 분리해야 함 |
| C. 이번 창의 ALM cache 후속을 보류하고 증거 보존 | 미완료·과거 실패를 정직하게 남기고 새 모델/환경 변경 없음 | 신규 binary KL 대조의 효과는 여전히 NOT_RUN. 별도 scorer/서버 개선은 새 권한·새 설계가 필요 |

권고는 **A를 CPU/source 단계에서 먼저 닫는 것**이다. 기존 완료 실험 재학습·V5 재수행·새 자료 선택·K/오차의 사후 완화는 권고하지 않는다. 현재 결론은 **`V6_SOURCE_REVIEWED / P1_RESPONSE_AND_CROSS_CONTROL_CONTRACT_GAPS / REAL_CANARY_FULL_AND_KD_NOT_RUN_BY_REVIEWER`**다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 24. 승인된 V7 국소 수리 — 착수·원형 보존·합성 검증

### 24.1 최초 수정 전 범위와 영향도

총괄이 §23의 A를 선택하고 controller/helper4개와 본 문서, 정확 snapshot4개의 쓰기를 승인했다. `impact-analysis`·`exp-preflight`·`wip-ledger`를 다시 읽었다. shared WIP/정식 계획·런처·준비본의 소유자는 총괄이며 이번 명시 allowlist에 새 WIP 쓰기는 없으므로 원장 작업을 우회하거나 독립 WIP를 가장하지 않는다. 이 절에는 담당 착수·재개·완료 증거만 남기고 원장 연쇄는 총괄이 관리한다.

| 파일·경로 | 예정 작업 | 현재 승인 근거·제외 |
|---|---|---|
| `scripts/diag_p106b_alm_cache.py`, `scripts/test_p106b_alm_cache.py` | V7 namespace, 공통 응답 검사 연결·정상4controls/closure·고정 실패 사건 회수, 작은 합성 오류 주입 | 총괄의 이번 명시 구현 승인. prepare/실물/E2E/GPU0 |
| `scripts/p106b_alm_utf8_probability.py`, `scripts/test_p106b_alm_utf8_probability.py` | complete/probe 공통 actual 계약과 정상 forcing 실패 분리·회귀 | 동일 승인. 순수 stdlib helper 유지 |
| `handoff/audit/source_snapshots/20261023_alm_cache_v6.py.txt`, `20261023_alm_cache_v6_test.py.txt`, `20261023_utf8_probability_v2.py.txt`, `20261023_utf8_probability_v2_test.py.txt` | 최초 수정 전에 원 네 파일의 정확 bytes 보존 | apply_patch로 신설 후 원본/사본 SHA256 각각 일치 확인. 이후 변경하지 않음 |
| 본 연구 문서 §24 | 영향·시험·변경·잔여 한계 기록 | 기존 실패/§23 보존. 공유 계획/결과/원장/기준표는 수정하지 않음 |

snapshot의 SHA는 순서대로 §23.1의 `49D8…3B81`, `7EA2…C696`, `5707…7EB7`, `71C6…A71E`와 정확히 같다. bytes는83,441/44,951/17,473/20,871이다. 보존 전 source가 §23 snapshot과 같은 것도 확인했다. legacy `diag_p106b_teacher_tf.py` 및 P078·자료/모델·기존 V6 준비본은 변경·실행하지 않는다.

| 영향 축 | 착수 판단 |
|---|---|
| 코드·의존·중복 | 기존 TF payload와 순수 helper의 검증을 재사용하되 legacy parser 자체는 동결. 새로운 공통 actual parser를 complete/probe caller에 함께 연결. 외부 package 추가0 |
| 데이터·호환 | SCHEMA/root order/1024행·first16+34/학생CE·원 abs1e-5/K 순서 불변. BASE와 teacher contract만 V7로 분리해 V6 준비/실패 증거를 그대로 보존 |
| 테스트 | 합성 source/transport만. 공통 envelope 오류·진짜 forcing 실패만 retry·같은-K4조합 교차 변화·closure 오염·fragment caller를 오류 주입. 전체 모델 E2E mock은 만들지 않음 |
| 정본·기술부채 | 소유 문서에서 준비 구현/합성 결과만 기록. 실제 준비/source pin·Stage7b 실행·등록부/결과 연쇄는 총괄 후속. native API 고정 전용성은 계속 한계 |
| GPU·동시 소유권 | 실행은 승인 CPU 회귀만. 모델/GPU/서버·실제 원문/패킷·P078 원형44파일·설치·Git·서브호출0 |
| 비교·증거 | raw 확률 취득 계약의 국소 수리이지 ALM recipe/정답 품질/학습 효과 아님. 질량은 관찰 전용·원값 무변이 유지 |

재개 지점: 공통 actual parser/순수 회귀의 수정 전 실패 확인 → V7 controller/4controls/closure/실패 사건 연결 → 승인 tlm_torch 합성 회귀 → snapshot/소유 범위·한국어 문서 확인. 실제 자료/모델을 열어 source 부족을 메우지 않는다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 24.2 V7 담당 구현 동결 — 네 파일과 실제 변경

**담당 구현·합성 검증은 완료하고 아래 네 source 파일을 동결했다. 총괄이 이 뒤 source를 직접 회수·정적 검산하고 V7 실제 CPU 준비를 별도 수행할 수 있다. 이 담당의 실제 준비/모델/교사 요청은0이다.** BASE는 `HF/sft_ready/p106b_alm_context_v7_s1337`, 새 teacher contract는 `NATIVE_TEMPLATE_THINKING_FALSE_EDGE_COLD_UTF8_PROBE_STRICT_ACTUAL_V4`다. 기존 V6 디렉터리는 열거나 바꾸지 않았다.

| 동결 파일 | SHA256 | 규모 |
|---|---|---|
| `scripts/diag_p106b_alm_cache.py` | `0B53379EC83A79F578960B652B4EDF9FC16C456FA1988D1876CD6DEBCE0A4B6B` | 1,651행/97,779B |
| `scripts/test_p106b_alm_cache.py` | `F4546B9DAC70346B7C7F81D1CA2DE8B1C409DEAFF0854FA2067EDA57CB0BAC7A` | 1,183행/67,727B/test82개 |
| `scripts/p106b_alm_utf8_probability.py` | `1B2DBEFC4C108F0C72A5DE9367A04D4C1B063F739417BAB14099D7FA04A46CB5` | 431행/22,218B |
| `scripts/test_p106b_alm_utf8_probability.py` | `32A4A976D6407FDC7753E838D7E720619A13A0F32FB68305B9CAC3556979B79C` | 454행/24,170B/test31개 |

- [공통 actual parser](/home/uranus/tinyLM/scripts/p106b_alm_utf8_probability.py:240)는 complete/probe 모두에서 실제 무절단·prefix 길이·생성1/limit 종료·ID/bytes/content·cache_n·raw/backend/MTP OFF·중립 설정·bias/seed/K·top 전체의 비양수/유한성·중복/순위·선택 ID의 동일 logp/bytes를 확인한다. 현재 고정 응답의 `speculative.types="none,none"`, 빈 stop/grammar/LoRA도 명시 검사한다. `build_direct_payload`가 legacy TF source를 변경하지 않고 반환 ID와 중립 설정을 명시한다.
- `NativeNotForcedError`는 **다른 actual 계약까지 모두 정상인 실제 다른 선택**만 나타낸다. complete/probe controller는 이것만 사전100→200으로 제한 재시도한다. missing tokens·잘못된 flag/생성수/bytes 등의 schema 오류는 재시도하지 않는다. reference top-K 누락은 별도 `TargetMissingFromBoundedTopK`이며, 이것만 K64→512→2048로 넘어간다. 두 bias 모두 probe를 선택하지 못하면 K를 올려 감추지 않고 중단한다. reference의 원 bytes도 실제 top-K의 같은 ID bytes와 대조한다.
- [정상 controls](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:1006)는 K를 바깥 loop로 둬 **네 쌍 모두 같은 K·같은 native prefix**에서 비교한다. K가 부족하면 행/target/probe/bias를 바꾸지 않고 전체2×2 matrix를 다음 사전 K에서 다시 받는다. 각 쌍 parity뿐 아니라 이미 관측한 direct/probe의 target/top2를 같은 K의 첫 reference와 즉시 대조하므로 교차 불일치가 뒤의 누락/K 상향으로 가려지지 않는다. 성공 matrix는 정확 A/B×100/200의4조합·단일 K/원 prefix·선택 probe/원 target 분리와 원 target/top2 전체 동일성을 담는다.
- [closure의 순수 검사](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:948)는 stored passed4개를 믿는 대신 정확 조합·K/ID/bytes/rank/bias/prefix와 쌍별·교차 수치를 재검산하고 보고서 matrix와 대조한다. canary closure는17행·ko9/en8을 요구한다. 반복 cold의 probe K도 첫 성공 K에 고정해 두 관측을 같은-K로 비교한다. full에서 행 첫 target만 반복하는 기존 정책은 바꾸지 않았다.
- [원 실패 사건 회수 검사](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:1269)는 원 index34/ID36054/bytes `ec9b`/prefix SHA `5661E32015CBC28C7FC8D38BC1243052D37319CF7CB36BEA9D78A3D6858AA6F6`를 정확 요구한다. prefix SHA는 실제 캐시의 teacher IDs로 다시 계산한다. 같은 사건의 saved score와 독립 cold 두 관측에 실제 `FOUND`·원 top-K origin·별도 선택 probe·원 target bytes/logp·같은 K가 있어야 한다. `execute` 성공 전과 `closed_batch` 회수 때 모두 재검산한다. **17행에 원행34가 포함됐다는 사실만으로 복구 PASS가 되지 않는다.** metadata가 없거나 다르면 partial로 보존하며 쉬운 target으로 교체하지 않는다.

### 24.3 수행한 합성 회귀와 수정 전 반례

실행 인터프리터는 `/home/uranus/miniforge3/envs/tlm_torch/bin/python`, Python3.10.19다. 명령별 `CUDA_VISIBLE_DEVICES=''`, `-B -X utf8`을 사용했다. 최종185개 실행에는 `torch/tokenizers/transformers/lm_eval`의 import를 차단하는 별도 process-local guard를 걸었고 실행 전후 해당 module이 없음을 검사했다. 설치·전역 환경·startup 파일을 바꾼 것이 아니다.

| 수행 | 실제 결과 | 범위·주의 |
|---|---|---|
| source 수정 전 `StrictV7ActualContract.test_complete_target_cannot_accept_truncated_actual_response` | **1개 FAIL/exit1**, `ValueError not raised` | 기존 V6가 `truncated=True`+그럴듯한 확률을 받는다는 재현. 실제 모델/원문 없이 작은 transport fixture |
| 공통 helper 수정 뒤 helper 회귀 | 31/31 PASS/exit0 | 기존28+새3. complete/probe 공통 actual·유효 forcing 실패·누락 metadata 검사 |
| controller/helper 최종 두 모듈 | 113/113 PASS/exit0 | cache82+helper31. V6의61+28에서 총24개 추가. 중간 오류 주입/구현 반례를 최종 결과로 덮지 않음 |
| bytes/template/cache/probability4모듈 최종 합성 실행 | **185/185 PASS/exit0**, 최종 인쇄0.505초 | bytes41+template31+cache82+probability31. 위 import 차단/실행 전후 module 부재 검사도 통과 |
| 같은 tlm_torch의 실제 `diag_p106b_alm_cache.py --check-only` 진입 | SOURCE_ONLY/exit0 | 동결 SHA·V7 BASE·계획1024/17행·실패 사건 기대 metadata 반환, asset/data/tokenizer/model/GPU0. prepare/execute가 아님 |
| 원 snapshot 재해시·AST 불변성 | 원 네 snapshot SHA는 §23.1/§24.1과 동일 | 아래 함수·수치의 AST 대조이지 실제1024행을 읽어 재준비한 증거가 아님 |

추가 controller 회귀는 complete의 truncated/prefix/생성수/raw/MTP/bytes/양수 top/순위 오류에서 **요청1회 뒤 중단**, 실제 다른 probe 선택에서만100→200, 선택 실패로 K를 올리지 않음, K 부족 때 동일 matrix 전체 재시도, bias 의존·A/B 호출 순서 drift가 쌍 내부에서 같아도 교차 거부, duplicate/K/prefix/값 오염 closure, header/probe registry 연결, 실제 fragment caller의 원 prefix·동일 K cold 반복/합우도/EOT를 다룬다. 회수 metadata 검사는 원 사건 포함만으로 통과하지 않으며 ID/bytes/prefix/선택 probe/origin/반복/K/대입 logp 오류를 주입했다.

원 실패 prefix 원문/ID열은 열지 않았으므로 그 metadata predicate의 **양성 합성 fixture만 object_sha를 명시 mock**했다. 별도 음성 fixture는 mock 없이 toy IDs에서 실제 SHA를 다시 계산해 거부되는지 확인한다. 이를 원 prefix의 실물 회수 검증이라고 주장하지 않는다. closure 회귀도 recovery predicate를 격리 mock하고 exact controls 재검산을 따로 검사한다. 전체 모델/서버 E2E mock은 만들지 않았다.

중간 새 fragment caller 회귀에서 “한국어 한 문자는 한 chunk”로 잘못 기대해1개가 실패했다. 실제 byte 경계상 두 chunk였고 각각 원 logp를 올바르게 담고 있었다. **구현/정렬 함수를 바꾸지 않고 회귀의 검산을 전체 chunk 합으로 정정**했으며 최종185개에서 통과했다. 실패 원인과 정정을 원 실제 데이터 결과로 해석하지 않는다.

### 24.4 불변 범위·미실행·다음 소유 경계

원 snapshot과 최종 source를 AST로 대조하여 `root_order/choose_rows`, char/byte span·마스크, `pack_student/rebuild_student`, source inputs/prepare/1024 검증/load, teacher stream, `canary_rows`, native no-thinking renderer가 **내용 불변**임을 확인했다. Budget/Recorder/로그 seal/thread/세션 종료 함수도 그대로다. SCHEMA/seed/512-per-language/16×64/학생·교사1024/CE64/abs1e-5/19,999,999B/30초 reserve/16:30 hard stop/CODE 목록과 helper의 K64/512/2048·bias100/200·raw origin/중립 값은 AST가 같다. 이는 source 의미를 보존한 검산이며 원 선택1024행 SHA 동일성은 총괄의 새 V7 실제 준비가 회수한다.

저장소의 영구 쓰기는 **승인된4 Python 파일+본 연구 문서+최초4 snapshot**뿐이다. CPU 회귀의 임시 fixture는 test framework의 전용 임시 디렉터리 안에서만 사용했다. legacy `diag_p106b_teacher_tf.py`는 쓰지 않았고 현재 SHA는 `25E29E89A36BDC19FC5FFAAA52BBDCB2459E2C3C0AD5B64FF073DB79CBC47609`다. bytes/template helper·P078·런처·공유 계획/원장·설치 환경을 수정하지 않았다. 보호 데이터/실제 원문/실제 패킷/준비본/모델 자산은 읽지 않았다. snapshot은 삭제·갱신하지 않는다.

새 GPU 실행·실제 교사/학생·서버·실제 TF 요청·V7 prepare·자료 수리·설치·다운로드·Git·추가 agent는0이다. 원 CPU218 전체 suite의 `alm_core`에는 toy model 생성이 있어 이번 **모델 생성 금지** 범위에서 실행하지 않았다. 다른 학습 runner 회귀·전역 static/registry/smoke도 이 담당의 실행 범위가 아니며 총괄이 별도 회수한다. 최종185 합성 PASS를 이전218 전체 재실행이나 GPU/확률 품질 PASS로 바꾸지 않는다.

남는 한계는 quantized native API의 원 softmax·정밀도·실제 top-K coverage/응답 크기·cold 재현성·비용/종료의 실물 미확인이다. flag/부분 질량/합성 수치만으로 원 logits 동등성이나 의미 정답성을 보증하지 않는다. 질량은 계속 **관찰 전용**, 원값/clamp/재정규화0이며 abs1e-5·원 top2 ID 규칙을 사후 완화하지 않는다. 통과하더라도17행 canary는1024 완성 cache/학생 binary KL 효과/ALM full recipe가 아니다.

총괄의 다음 지점은 **이 동결 source 회수·독립 static/합성 확인 → 새 V7 실제 CPU 준비의 동일1024/17행 hash 검산 → P078 종료/idle·기존 시간·권한 게이트 아래에서만 실물17행**이다. 이 담당은 그 단계를 실행하지 않고 현재 구현 업무를 마친다. 상태는 **`V7_SOURCE_FROZEN / SYNTHETIC185_PASS / SOURCE_ONLY_ENTRY_PASS / PREPARE_TEACHER_GPU_AND_KD_NOT_RUN`**다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 25. 공식 평가 source에 대한 정적 검사기의 자료형·캐시 경계 재검토

### 25.1 착수 영향도·원 검사기 보존

총괄은 전수 static76의64PASS/6ERROR/6NOT_RUN 중 두 검사기 오탐 가능성을 확인하고, **평가 source/준비 identity를 변경하지 않는 검사기 수정과 작은 합성 CPU 회귀만** 허용했다. `impact-analysis`와 `wip-ledger`를 읽었다. 공유 WIP와 정본 연쇄는 총괄 소유이며 이번 allowlist에 없는 원장을 만들거나 바꾸지 않는다. 착수·잔여 판단은 이 절에만 기록한다.

| 파일·경로 | 작업 | 승인·제외 |
|---|---|---|
| `scripts/check_attrs.py` | 정확한 YAML loader import/단일 mapping binding이 지배하는 속성 접근만 TMTConfig와 구별 | 명시 검사기 수정 승인. get/update 전역 허용·파일명 면제 금지 |
| `scripts/check_hf_redirect.py` | 먼저 읽기 판별. source상 실제 cache 선설정이 증명될 때만 한정 정밀화 검토 | 명시 승인이나 **오프라인 설정을 cache redirect로 간주하지 않음**. 증명 불가한 실제 두 경고는 지우지 않음 |
| `scripts/test_p106b_official_eval_static_guards.py` | 새 합성 AST/임시 source 회귀 | 실제 HF/Torch/모델/평가 import·실제 자료/환경 변경0 |
| `handoff/audit/source_snapshots/20261023_check_attrs_before_official_eval.py.txt`, `20261023_check_hf_redirect_before_official_eval.py.txt` | 최초 검사기 수정 전 exact bytes snapshot | apply_patch로 먼저 신설, 원본/사본 SHA 일치. 각각4,851B/5,970B |
| 본 문서 §25 | 관측·수정·합성·미확인 기록 | 평가/ALM4파일/P07844/런처/설치/정본/Git 수정0 |

보존한 원 SHA는 attrs `31F315165C10C8646D3D99C822AC69FFB5338796FAE3A44929CB9AC862B95650`, HF `87B06AE9559F0D7FC867E32738E6B86217E630F95F07CF7105B9A4D4F8B7F67C`다. source 읽기는 이름이 지정된 Python 파일과 필요한 helper 구간뿐이며 실제 평가/학습 행은 열지 않았다.

| 영향 축 | 판단 |
|---|---|
| 코드·중복 | 기존 AST 검사 유지. 자료형 이름 추정의 오탐만 좁은 import/대입/순서 증거로 구별. exact factory가 아닌 일반 객체는 기존 TMTConfig 검사 유지 |
| 자료·identity | evaluator/prepare/source/YAML/data/준비본 변경0. 검사기 수정으로 원 모델/평가 source pin을 다시 쓰지 않음 |
| 시험 | YAML loader 위장/재바인딩/범위 누설·진짜 TMTConfig 오타·HF 선행 import/잘못된 경로 반례를 합성 source로 검증 |
| 정본·기술부채 | bounded AST 분석이며 범용 Python 타입·호출 그래프 증명이 아님. 불명확한 source를 성공으로 면제하지 않고 경고 유지 |
| 권한·동시·증거 | 합성 CPU만. 모델/GPU/평가 data·원문/패킷·기존 ALM/P078/설치/외부 상태0. 전체 static76 통과나 평가 결과로 승격하지 않음 |

### 25.2 읽기 판별 — 두 가설의 결론은 다르다

**attrs 오인은 확인됐다.** `p106b_official_tasks.load_tasks`는 local scope에서 `from lm_eval.tasks._yaml_loader import load_yaml` 뒤 `config=load_yaml(...)`를 받고 `.get/.update`를 호출한다. 고정 upstream Python loader는 `isinstance(cfg,dict)`가 아니면 예외를 내고, include merge도 dict를 반환한다. 읽은 loader의 SHA는 `3EA637C454937DF677EA662325A9F7CB08869FDE29EDFC26B44FF41BE6127034`다. 이 file/code만 읽었으며 실제 YAML 문항·dataset·lm_eval import는0이다. 기존 check_attrs는 변수명 cfg/config만 보고 이 mapping을 TMTConfig로 오인한다.

**현재 두 HF 경고는 같은 의미의 오탐으로 확인되지 않았다.** `prepare_p106b_official_eval.prepare`는 HF_HUB_OFFLINE/HF_DATASETS_OFFLINE만 설정하고 명시 `cache_dir`의 local parquet loader를 사용한다. `official_core6.execute`의 OFFLINE에도 HF_HOME/HF_HUB_CACHE/HF_DATASETS_CACHE 경로 설정은 없다. `prepare_harness`도 source/runtime identity를 검증하고 lm_eval을 import하지만 cache 환경을 설정하지 않는다. shell의 공통 Python 선택기와 runlog도 해당 경로를 설정하는 것으로 확인되지 않았다. **local_files_only/cache_dir/offline은 전역 cache 환경이 import 전에 고정됐다는 증거와 다르다.** source만으로 이전 실행의 모든 cache 경로를 위반했다고 확정할 수 없지만, 반대로 경고를 삭제할 source 근거도 없다.

추가로 기존 HF checker는 순서가 아니라 `tinylm` import의 **존재**만 확인한다. 따라서 HF를 먼저 import하고 tinylm을 나중에 import한 반례를 놓치는 한계가 있다. 이 한계를 평가 파일의 무조건 면제로 해결하지 않는다. source상 직접 증명되는 경계와 외부 실행 환경의 증거는 분리한다.

| 경로 | 장점 | 비용·현재 권한 |
|---|---|---|
| A. attrs의 정확 mapping만 구별하고 HF 불명확 경고 유지 | 평가 source/준비 identity를 보존하고 확인된 오인만 닫음 | 경고 전체0을 약속하지 않음. 현재 권한 안 |
| B. 평가 진입점에 실제 cache 선설정/검증을 신설 | HF import 선행 경로를 source 자체로 닫을 수 있음 | 평가 source·준비 pin 변경이며 이번 금지 범위. 별도 승인/새 identity 필요 |
| C. 현재 실행 wrapper·환경 영수증을 별도 계약으로 검증 | 이미 실행한 조건을 source 수정 없이 설명할 수 있음 | source-only 검사와 다른 증거. 외부 환경이 바뀔 수 있어 고정 파일명 면제로 대체 불가 |

현재 권고는 **A**다. HF checker 자체를 정밀화하더라도 설정되지 않은 cache 변수를 설정된 것으로 가정하지 않으며, 검증 불가 경계는 그대로 보고한다. 재개 지점은 두 검사기의 최소 AST 회귀와 attrs 오탐 수리이며 최종 수행/미수행은 다음 절에 별도 기록한다.

### 25.3 총괄의 후속 중단 지시 회수 — 공용 검사기 변경0

위 착수 판별 뒤 총괄은 HF 경고가 단순 오탐이라는 가설을 철회하고, **평가 진입점에서 기존 tinylm.paths를 명시 재사용하고 source snapshot/새 BabyLM v3 준비를 분리**하는 수리를 직접 소유하기로 했다. YAML 지역명도 `task_config`로 명확히 하므로 공용 attrs/HF 검사기의 새 의미 변경을 중단하라는 후속 지시를 받았다. 이는 §25.2 작성 당시의 A 권고/담당 재개 지점을 대체한다. 총괄의 source 수리·새 준비는 이 담당이 수행하거나 통과 판정한 것이 아니다.

**중단 시점의 실제 담당 변경:** `check_attrs.py` 수정0, `check_hf_redirect.py` 수정0, 새 회귀 파일 신설0, 합성/검사기 실행0이다. `scripts/test_p106b_official_eval_static_guards.py`는 존재하지 않는다. 두 검사기 원 SHA는 §25.1과 그대로 일치하며 보존 snapshot도 각각 바이트 SHA가 같다. 이미 만든 파일이나 문서를 되돌리거나 삭제하지 않았다.

남긴 새 파일은 `handoff/audit/source_snapshots/20261023_check_attrs_before_official_eval.py.txt`와 `handoff/audit/source_snapshots/20261023_check_hf_redirect_before_official_eval.py.txt`의 **정확 보존 사본2개**뿐이며, 본 연구 문서에는 §25의 읽기 판별·중단 기록이 추가됐다. 기존 ALM4파일/P07844소스·평가/준비 source·런처·원형/자료·설치·Git은 이 추가 작업에서 변경/실행0이다. 상태는 **`READ_ONLY_FINDINGS_RETURNED / SHARED_CHECKERS_UNCHANGED / TWO_EXACT_SNAPSHOTS_PRESERVED / IMPLEMENTATION_STOPPED_BY_PARENT`**이며 추가 지시 전까지 멈춘다.

## 26. 제어문자 진단의 재전파 — 표시 수리와 원본 증거 분류를 분리

### 26.1 이번 읽기 범위·영향도·직접 관측

총괄의 추가 지시는 **읽기 검토와 본 문서 갱신만** 허용한다. `impact-analysis`의 방법 비교를 적용하며 검사 완화·source 수정·시험 실행·원문/후보/원본 로그 변경은 하지 않는다. 공유 WIP·정식 결과/계획·정본 연쇄는 총괄 소유이고 이번 허용목록 밖이다.

| 경로 | 이번 수행 | 권한·제외 |
|---|---|---|
| `scripts/check_control_chars.py`, `scripts/test_control_chars.py` | 전체 source 읽기 | 명시 검토 대상. import·검사기/회귀 실행·수정0 |
| `scripts/check_static_all.py`, `scripts/runlog.py` | 직접 caller의 설명문·출력/저장 구간만 읽기 | 진단이 stdout/저장 로그로 연결되는 원인 확인. 전체 전수 검사·Git 경로·모델 진입0 |
| `test_result/101_log_20261023_P106B_Stage9aW_scoped_static_audit.txt` | header·관련 진단과 실제 C0의 행/byte offset/개수·SHA만 읽기 | 원본 파일은 보존. 점검 출력에서는 C0를 가시 이스케이프하고 원문 문맥은 재인쇄하지 않음 |
| 검수문서2개·원 후보/학습·평가자료 | 직접 열람/검색/해시0 | 기존 진단의 지명 경로만 확인. 원천 유래라는 설명은 총괄 제공 맥락이며, 이번 검토로 원천 전문과 대조했다고 주장하지 않음 |
| 본 연구 문서 §26 | 새 읽기 판별·대안 기록 | 유일한 쓰기. source/로그/스냅샷 신설·원장 변경0 |

코드 영향은 **발견 규칙이 아니라 표시 경계**이며, 자료 영향은 원본 로그를 다시 쓰면 증거 identity가 바뀐다는 점이다. 시험 영향은 기존3개 그룹이 탐지만 확인하고 stdout을 검사하지 않는 공백이다. GPU/학습/모델·보호자료·설치·다운로드·Git·서브호출0이며, 학습/평가 조건과 점수에는 변경이 없다. 정본/기술부채는 총괄의 별도 수리 승인·새 source/출력 hash 회수에 한정한다. 본 절은 재전파 문제의 검토이지 전체 정적 검사의 PASS 갱신이 아니다.

열람 시점의 SHA256은 checker `6993A9AE40D37BBEB0704EF57EE4FF00C1C2DDE523124193E10B7BC71FE1F74F`, test `0FE81191EC77780EE670150B367B924687F2E6B7865147F9ED6DCC304BE6FC24`, suite `93690C7B573359FAEFCB56E51B07D909DFC9C1E663271CFD779B7B84372D9BF5`다. 원본 저장 진단 로그는 **32,444B/285 LF행**, SHA `311FC8EF42DB7D5F2A49047BF7CFB96D501F79F0A59AC4C1C7F3273C7D8A2CE3`다. header는 2026-10-23 10:27:48, `P106B_Stage9aW_scoped_static_audit`, `check_static_all.py --profile codex-safe --quiet` 실행의 저장 기록임을 보여 준다. 과거 기록의 header를 이번 재실행 증거로 쓰지 않는다.

**실제 로그에는 U+0002만 있는 것이 아니다.** 다음은 저장 파일을 읽어 센 금지 C0 네 byte의 위치다. offset은 파일 시작0, 행은 LF 기준1이다. ANSI CSI의 ESC는 이 네 건에 포함되지 않는다.

| 행 | offset0 | 실제 byte | 관측한 위치·해석 |
|---|---:|---|---|
| 190 | 14317 | U+0002 | 직전189행이 `review_request/20261023_sft_000117_A5DADA1A2F57_review.md:422  0x02`를 지명. checker의 문맥 인쇄 위치 |
| 192 | 14454 | U+0002 | 직전191행이 `review_request/20261023_sft_000137_B53568435447_review.md:653  0x02`를 지명. 같은 문맥 인쇄 위치 |
| 271 | 30037 | U+0008 | suite의 `check_control_chars` 요약 설명문 안. 검수문서 인용과 별개 |
| 271 | 30042 | U+000B | 같은 요약 설명문 안. 검수문서 인용과 별개 |

### 26.2 source가 실제로 증명하는 두 전파 경로

**경로1: 발견한 원문 byte를 진단 문맥에 그대로 재삽입한다.** `check_control_chars.py:55`의 `first_bad_control`은 raw bytes에서 금지 집합의 첫 위치를 찾고 완결 ANSI CSI만 허용한다. `:102`는 해당 위치 앞뒤24byte를 UTF-8 `replace`로 decode하고 `:103`에서는 LF만 문자 두 개의 `\\n`으로 바꾼다. U+0002/BS/VT/ESC 등 다른 C0는 그대로 남는다. `:114`가 이 문맥을 stdout에 내보내므로 검수문서의 C0가 저장 진단에도 전파된다. 이는 **탐지가 잘못됐다는 증거가 아니라 출력 경계가 원문 제어문자를 다시 방출한다는 결함**이다.

**경로2: suite의 설명 문자열 자체가 출력 시 C0를 만든다.** `check_static_all.py:269`의 일반 Python 문자열에는 백슬래시 하나의 `\b`와 `\v`가 있다. source 파일에서는 인쇄 가능한 두 byte씩이지만 Python 문자열 값에서는 각각 BS와 VT가 된다. `:425`가 이를 요약문에 그대로 인쇄하며, 실제 로그271행의 U+0008/U+000B 두 개와 맞는다. 따라서 **checker의 ctx 표시만 수리하면 U+0002 재전파는 막을 수 있어도 이 별도 두 byte까지 없어지는 것은 아니다.** 이 설명 문자열을 문자 그대로의 백슬래시 표기로 고치거나, suite 설명 필드의 표시를 별도로 안전하게 만드는 수리가 필요하다. 현재는 제안만이며 suite도 수정하지 않았다.

suite `:403–417`은 자식 stdout/stderr를 받아 인쇄하고 원 출력 hash를 계산한다. `runlog.py:631–640`은 받은 텍스트를 콘솔과 저장 파일에 기록한다. **원본 기록기에서 조용히 치환하는 것은 최소 수리안이 아니다.** 원문 출력과 저장 증거를 변형하고 기존 output/file SHA의 뜻을 바꾸기 때문이다. 또한 runlog는 `text=True`, UTF-8 `errors=replace`와 줄끝 정규화를 쓰는 텍스트 기록기다. 이 파일을 “실행 당시 저장된 원본 진단 로그”로 보존할 수는 있지만, native stdout의 무변환 byte-for-byte packet이라고 부르지는 않는다.

현재 checker는 파일별 첫 발견만 보고 `len(hits)`를 **문제 파일 수**로 출력한다. 이 값을 전체 제어문자 수로 바꾸어 읽으면 안 된다. 로그의 실제 C0 네 개는 이번 별도 읽기 계수이고, 과거 gate의 “2파일”과 분모가 다르다. 현 ANSI 허용 regex는 파일의 원본 로그 역할을 증명하지 않고 내용의 완결 CSI만 본다. 이 기존 예외를 U+0002나 로그 전체 면제로 확대하지 않는다.

### 26.3 진단 표시만 바꾸는 최소 수정안 — 아직 미구현

**raw 탐지·대상·허용 집합·ANSI 규칙·첫 위치·exit0/1을 그대로 두고, 마지막 표시용 문자열만 가시 이스케이프하는 안**이 타당하다. stdlib `json.dumps(text, ensure_ascii=False)`처럼 C0와 백슬래시/따옴표를 일관되게 인용하는 작은 표시 함수를 사용할 수 있다. 한국어는 보존하며 실제 제어문자는 `\u0002` 등 인쇄 가능한 표현이 된다. 정규 LF/CR/TAB도 문맥 안에서는 가시화하고, 진단 레코드 사이 개행만 실제 LF로 출력한다. literal `\u0002`라는 원문과 실제 U+0002가 같은 모양으로 보이지 않도록 원래 백슬래시도 인용해야 한다.

적용 대상은 `ctx`와 원문에서 유래할 수 있는 **상대경로 문자열**이다. ctx에만 적용하면 제어문자가 든 파일명의 진단은 여전히 터미널 제어를 방출할 수 있다. 기존 `ctx.replace(chr(10), ...)`와 이중으로 합성하지 말고 하나의 표시 단계로 대체한다. 허용 ANSI가 금지 byte 근처 문맥에 함께 있어도 표시에서는 ESC를 가시화해 터미널에서 실행하지 않는다. 원 raw를 정리한 뒤 탐지하거나 `first_bad_control`에 escaped bytes를 넣어 PASS로 바꾸어서는 안 된다. UTF-8 chunk 끝의 기존 replacement 문자는 표시의 기존 손실이며 원 offset/byte 판정과 혼동하지 않는다.

**원인 단정·수리 지시 문구도 분리해야 한다.** checker `:115–118`의 “백슬래시 사고다/파이썬 패치나 heredoc이 만들었다/그 파일을 다시 쓴다”는 발견된 byte만으로 증명되지 않는다. 검수용 인용·기존 원문·모델 응답·저장 진단에서도 같은 byte가 나올 수 있다. 예를 들어 “금지 제어문자가 있는 N파일을 발견했다. 원인은 작성 경로와 원문/증거 역할별 확인이 필요하다. 원본 로그·후보는 임의 재작성하지 않는다”처럼 **관측과 원인·후속 조치를 분리**하는 문구를 권고한다. 발견의 비영 종료코드와 금지 byte 판정은 유지한다. suite 설명문도 모든 발견을 source 오류로 단정하지 않도록 맞춰야 한다.

### 26.4 원본 저장 로그는 어떻게 보고할 것인가 — 분류와 면제는 다르다

**지금 계약에서는 실제 C0가 남은 원본 로그도 별도 미해결 발견으로 보고하는 것이 맞다.** 새 표시가 안전해져도 과거 로그의 네 byte는 소급해서 없어지지 않는다. `test_result/*.txt`가 현재 검사 대상인 한 원본 로그를 다시 만나면 비영 결과가 생길 수 있다. 원본을 보존한 채 “source 표시 수리/합성 검증 완료”와 “원본 진단 로그에 보존된 실제 C0 발견은 남음”을 함께 보고해야 한다. 해당 로그를 이름·확장자·경로로 면제하거나 이미 보존했다는 말만으로 gate 전체0/PASS를 선언해서는 안 된다.

동시에 **증거 기반 ‘원본 저장 진단 로그’ 역할 분류는 적절하다.** 이는 원인·소유권·후속 조치를 설명하는 보고 분류이지 탐지 삭제나 허용 판정이 아니다. 이 파일은 정확 경로/SHA/크기·header 명령/시점·네 offset·지명된 원문 위치·위 두 producer 경계를 묶어 분류할 근거가 있다. `RAW_DIAGNOSTIC_EVIDENCE_PRESERVED / FORBIDDEN_C0_FINDING_REMAINS`와 같이 보존과 미해결을 동시에 명시할 수 있다. 경로에 `log`가 있거나 `test_result`에 있다는 사실만으로 분류하지 않는다. 지명된 검수문서의 C0가 정확 어떤 원천에서 왔는지는 전문 대조를 하지 않았으므로 이번 독립 검토에서는 미확인으로 남긴다.

사람이 읽을 새 이스케이프 view가 필요하면 **별도 승인 뒤** 원본 SHA·변환 규약/version·파생본 SHA를 명시해 원본과 구분할 수 있다. 이 view는 원본 대체나 native 원문이 아니고, 현재 원본의 비영 검사를 소급 PASS로 만드는 자료도 아니다. 원문/후보/원본 로그를 삭제·이동·개명·치환하는 제안은 하지 않는다.

| 선택지 | 장점 | 비용·한계 |
|---|---|---|
| A. 표시 수리 제안만 채택하고 모든 C0 발견을 하나의 미해결 목록으로 유지 | 가장 작고 현재 금지 집합/exit 계약과 완전히 동일 | 원문 보존물과 새 source 결함의 소유/조치가 한 목록에 섞임. 원본 로그가 남아 전체0은 불가 |
| **B. 표시 수리 + 증거 역할을 별도 보고하되 탐지/비영 결과는 유지** | 원문 보존과 실제 source 수리를 구별하고 원인 단정을 막음. 현재 발견을 숨기지 않음 | provenance 행과 필요한 별도 가시 view의 추가 관리. 원본 C0 미해결을 계속 명시해야 함 |
| C. 향후 exact manifest를 가진 증거 보존 정책을 정식 설계 | 보존 원문과 새 작성 텍스트의 규약·검증·보고 상태를 기계적으로 구별할 여지 | 별도 정책/사용자 승인·schema/음성 회귀·aggregate 의미 변경 검토 필요. 현재 권한으로 구현/면제하지 않으며 이번 로그에 소급 적용 불가 |

권고는 **B**다. 지금은 그 보고만 하고, 실제 source 수리는 총괄의 별도 승인 범위에서 수행한다. “별도 미해결”과 “원본 로그라는 증거 분류”는 양자택일이 아니다. **같은 네 byte를 발견 목록에 남기면서 보존 이유를 근거와 함께 설명**하면 된다. C를 B라는 이름으로 몰래 도입하지 않는다.

### 26.5 필요한 최소 회귀와 이번 미실행 경계

기존 `test_control_chars.py:8–19`는 plain/완결 CSI 허용, 고립·미완결 ESC 거부, 백스페이스 거부의3개 그룹만 검사한다. `main`의 실제 stdout/exit/원본 불변성과 suite의 설명 문자열은 검증하지 않는다. 이후 수리 승인이 있으면 작은 합성 입력으로 다음을 확인해야 한다. **아래는 제안이며 이번에는 시험/fixture 신설·실행0이다.**

- 실제 U+0002·BS·VT·고립 ESC를 넣은 toy raw는 기존 byte offset·검출·exit1을 그대로 유지하고, 캡처한 진단 stdout에는 실제 금지 C0가 없어야 한다. literal 백슬래시 표기는 별개로 보여야 한다.
- 문맥의 CR/LF/TAB·한글·완결 ANSI가 섞인 경우와 상대경로의 제어문자도 가시화해야 한다. 원본 raw bytes/SHA는 출력 전후 같아야 한다. 정상 텍스트/완결 CSI의 기존 허용과 고립·미완결 ESC/BS 음성 회귀는 삭제하지 않는다.
- C0가2개 이상이어도 현 파일별 첫 발견과 문제 파일 분모/비영 종료는 바뀌지 않아야 한다. 본래 C0가 없는 파일을 표시 함수 때문에 실패시키거나, 반대로 escaped view를 원본 판정에 사용해 통과시키면 안 된다.
- checker의 문맥 출력을 고친 뒤에도 suite `why`가 BS/VT를 만들면 실패하는 좁은 요약 출력 회귀가 필요하다. 전체76검사나 실제자료/모델을 실행해 이 작은 경계를 검증할 필요는 없다. 원본 로그의 C0가 보존돼 있다는 사실은 새 출력 회귀 PASS와 별도다.

이번 실제 변경은 **본 문서 §26만**이며 checker/test/suite/runlog와 원본 진단 로그는 읽기 전후 SHA가 같았다. 검수문서·후보·원자료는 직접 읽거나 바꾸지 않았다. 코드/시험/전수 static/모델/GPU/설치/Git/원본 수리0이다. 상태는 **`READ_ONLY_OUTPUT_PROPAGATION_REVIEW / FOUR_C0_BYTES_IN_PRESERVED_LOG / DISPLAY_AND_PROVENANCE_PROPOSALS_ONLY / NO_EXEMPTION_OR_TEST_EXECUTION`**다.

## 27. 총괄의 표시 수리 뒤 source 재검토 — 새 발견만

총괄은 §26 권고B 중 표시 수리만 구현하고 기존3그룹을 보존한7그룹 PASS, 전수68PASS/2ERROR/6NOT_RUN, 원 Stage9aW 로그의 C0 네 byte 보존과 새 저장 진단의 C0 부재를 보고했다. **이는 총괄의 실행 보고이며 본 담당의 재실행/독립 로그 재검산이 아니다.** 이번에는 checker127행/test60행과 suite의 관련 설명문·순수 import 경계만 읽었고 코드·검사기·회귀·스모크를 실행하지 않았다. 원본 로그/자료/사본0444도 다시 열거나 바꾸지 않았다. 유일한 쓰기는 본 절이다.

읽은 source SHA256은 checker `F70A623DDE00A0A15F74AB9E0FB565B23F073DD54EBBCE65F4F71DB9767A5F32`, test `6B0505EF29B53019AA1D3A044858BAE975F1BB882920F4FB66F82DF50A54F9B3`, suite `BD51DF30FEF3CC897371B687AC7E5C77A90CEC29CD32D956070E22AAE8AF0BE8`다. `display_text`가 원문 대신 표시 문자열만 JSON 인용하는 경계를 대조했다.

### 27.1 새 P2 — 실제 파일명에 C0를 넣는 회귀의 Windows 제약

`test_control_chars.py:40–43`은 임시 디렉터리의 **실제 파일명**을 `fixture`+U+0002+`.txt`로 만들어 `write_bytes`한다. 현재 Linux/WSL 파일 시스템에서는 가능한 경계 검사지만 Windows의 일반 파일명 규칙에서는 U+0002 같은 C0가 허용되지 않는다. Windows에서 이 회귀를 그대로 호출하면 checker의 기대 exit/표시 검산에 도달하기 전에 파일 생성이 실패할 수 있다. 이것은 원문 C0 탐지를 완화해야 할 이유가 아니라 **새 fixture가 이전보다 플랫폼을 좁힌 문제**다.

현재 승인된 WSL 실행의7그룹 결과를 뒤집거나 현 표시 수리의 blocker로 보지는 않는다. 다만 이 source를 Windows `.bat` 스모크/정적 게이트에도 재사용할 때에는 추가 검증 또는 fixture 분리가 필요하다. 실제 파일 입출력 회귀는 정상 파일명으로 두고, C0가 든 상대경로의 표시 경계는 실제 파일 생성 없이 mock Path/반환값으로 별도 확인할 수 있다. 이 담당은 변경/Windows 실행을 하지 않았다. 현재의7그룹을 교차 플랫폼 PASS라고 확대하지 않는다.

### 27.2 새 P2 — “진단 stdout에 실제 C0가 없다”와 현재 assertion의 차이

새 test의 `:30/:37/:47/:53`은 표시/설명 문자열을 **탐지기 자신의 `first_bad_control`**에 넣어 `None`인지 확인한다. 이 함수는 완결 ANSI CSI의 ESC를 허용한다. 따라서 이 assertion의 정확한 의미는 “허용 ANSI 밖의 금지 C0가 없다”이며, “실제 금지 C0 byte가 전혀 없다/진단에 ANSI도 실행되지 않는다”까지 증명하지 않는다. 예를 들어 표시 단계에 실제 `ESC[31m`이 다시 들어오는 후속 회귀가 생겨도 이 조건만으로는 잡히지 않는다. 기존 ESC 단독 회귀와 새 BAD 전수 그룹은 좋은 보강이지만, 완결 CSI를 표시에서 그대로 내보내는 특수 경로까지 반증하지는 않는다.

현재 `json.dumps(..., ensure_ascii=False)` 구현은 C0와 백슬래시를 이스케이프하므로 **지금 실제 ESC가 누출된다는 source 결함을 발견한 것은 아니다.** 다만 출력 보안 회귀는 탐지기의 ANSI 예외를 재사용하지 않는 독립 byte 조건도 있어야 주장 범위와 맞는다. 향후 작은 합성 stdout 검산에서, 진단 레코드 구분 LF 등 의도된 공백과 문맥 안의 표시만 구분하여 원 BAD 집합의 실제 byte/ESC가 없는지 직접 확인하면 이 공백을 닫을 수 있다. 원문 탐지의 완결 CSI 허용 규칙과 기존3그룹은 그대로 유지해야 한다. suite 설명문 검사도 같은 의미 제한이 있다. 실제 새 저장 진단에 C0가 없었다는 총괄의 별도 관측을 이 회귀 공백 때문에 무효라고 하지는 않는다.

### 27.3 현재 결론·실행 경계

이번 읽기 범위에서 **탐지 완화·원본 치환·원인 재단정·새 C0 생성의 P1은 추가로 찾지 못했다.** 위 두 P2는 새 회귀의 플랫폼/독립 판정 한계다. 총괄의 source 수리·기존7그룹/전수 실행을 이 담당이 다시 했다고 주장하지 않으며, C0를 보존한 기존 로그의 미해결 발견은 §26.4와 같이 남는다. source/시험/원본/새 저장 진단/평가자료/보호경로/설치/Git/모델/GPU/스모크 실행·변경0이다. 상태는 **`SOURCE_REVIEW_ONLY / TWO_NEW_P2_TEST_LIMITS / NO_NEW_P1_IDENTIFIED / NO_EXECUTION_OR_SOURCE_CHANGE`**다.

## 28. P078 원4팔 완료 합류 — update 셔플의 낮은 CE와 실제 답변의 한계

### 28.1 이번 독립 판독의 범위와 완료 상태

총괄은 남은 fixed/update 셔플704와 원4팔 readback 종료0을 알렸다. 이번에는 지정된 [원4팔 readback](/home/uranus/tinyLM/test_result/evidence/p078_route_training_v1_s1337_cleanv3/readback_uniform_r2/report.json)과 [update 셔플 train report](/home/uranus/tinyLM/test_result/evidence/p078_route_training_v1_s1337_cleanv3/train_update_shuffle_r2/report.json)를 **먼저 최상위/필요 하위 키·형만 확인하고, 선택 필드만 출력해** 읽었다. `log-to-result`의 JSON 정본·조건 통제·수치/해석 분리를 적용한다. 이것은 기존 연구문서에 대한 독립 검토이므로 정식 결과 생성기·원장·계획·기준표의 쓰기/검사까지 확대하지 않는다.

readback은548,024B, SHA256 `D92C65AA02824FC15934554F175DC933EF47DB1EC5FA03A23CCE5BAC23A12C32`; update report는362,698B, SHA `0572500BF740EA030C3A0D90EB3C0B02C8FE3062EF72E99772DE167AED28B092`다. 지명 JSON의 metadata/요약/답변과 작은 배열의 합계만 읽어 계산했다. 거대 `route`/`atomic_trace`/`prompt_ids`/`generated_ids` 배열을 stdout에 덤프하지 않았다. JSON 선택 도구가 없어 설치하지 않고 기존 Perl의 JSON 해독기로 읽었다. 프로젝트 모듈/import·검사기·모델·시험·스모크를 실행한 것은 아니다.

readback의 결과 key는 **uniform_r2/fixed_shuffle_r2/update_shuffle_r2/balanced_count 네 개 모두**이며 status는 `RAW_RECOUNTED_NO_AUTOMATIC_ADOPTION`, `model_loads=0`이다. 즉 이 파일은 이름이 `readback_uniform_r2`라도 uniform만의 결과가 아니고, 저장된 네 학습 결과의 재검산 묶음이다. readback에서 새 답변을 생성한 것도 아니다. update report는 `ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED`, updates704, CP write1, model construction1, optimizer factory1/resetFalse다. **§21에서 “원4팔 중2팔/셔플 미실행”이라고 적은 것은 당시 관측으로 보존하고, 현재 원4팔 완료는 본 절로 합류한다.** 완료가 품질 채택이라는 뜻은 아니다.

새 readback의 `input`과 update report의 `input`은 전체 dict가 같고, compact canonical SHA는 §21의 `8CA5AE1BD08524C518EFAE6D88DE987D755991B566F27D4C9F39E661BFEE43BD`와 같다. 읽은 policy/driver source SHA도 그 input의 해당 pin과 일치했다: `p078_route_training.py`는 `934C065C9B11CFA208F9DA1C47C8CD4B49B1860612CCC9FDEF349C691FF57FFC`, driver는 `1794CF5E446E1F931D70038C229E0758319CF63E11B69892186D5050961EFC45`다. 이번 독립 검토가 원44파일·원704 JSONL·CP bytes를 다시 전수 검산한 것은 아니다. 그 closure를 수행하는 driver `readback:429–479`의 source와 저장 결과를 대조했고, 원문 자료/가중치는 열지 않았다.

### 28.2 같은 초기화·입력·방문량이 뜻하는 것과 뜻하지 않는 것

| 축 | 이번 report/필요 source의 확인 | 해석 한계 |
|---|---|---|
| 초기화 | 네 결과의 initial core 모두 `E854AB4EC2E505DDC581CE08C94F9C8B4A8081E456AFBA193DF28A877E34A193` | 한 부모/한 seed의 조건부 대조. 다중 seed 안정성·다른 본체 전이는 미검증 |
| 자료·노출 | 네 팔 각각 actual x21,621,776, assistant target2,210,436, padded layer-visit slots2,214,592,512. update는90,112 real rows/dummy0/padded token slots92,274,688/704update | padded slots는 실제 학습 token 수가 아니다. 동결 V3는 계속 `PSEUDO_UNVERIFIED_NOT_FORMAL_TRAIN_READY`이며 같은 잡음을 공유한다고 정답 감독이 보증되지는 않음 |
| 행 순서/학습 | 같은4epoch, m8×a16, width1024, checkpoint ON, eager, teacher/MTP OFF, 절대 Adam5e−5/Muon2e−4. source batches는 `Random(1337+epoch)`의 무복원 전체 순열 | 이번 report에는 모든 개별 행 ID 목록이 없어 행별 동일성을 source/동결 manifest 계약에 의존. 기존 훈련을 재수행해 증명하지 않음 |
| 방문 정책 | uniform/fixed/update는 매update R2/24방문. balanced는 평균R2지만 R1/R2/R2/R3 배분. fixed는 seed0 고정 비순차, update는 phase/index별 결정적 셔플 | 같은 평균/padded 방문량은 같은 유효 token별 연산·동일 FLOPs/시간·같은 중간 함수가 아님. balanced의 target/x 가중 방문 차이는 §21.2에 보존 |
| VAL 분모/정밀도 | 전 팔 primary/secondary 모두512행/2,977targets/64batch/FP32_MATH, padded visit slots12,582,912/총 방문1,536 | 동일 분모·총예산이어도 primary의 경로는 서로 다르다. 정책-경로 교호작용을 무시해 CE 차이를 훈련 하나의 효과로 분해하지 않음 |
| 실제 첫답 입력 | 네 팔의8개 id/question/prompt/prompt_ids가 대응 위치별로 정확히 같음. attempts1/temperature0/top_k1/TF32·cache·MTP OFF | 답변은 각 자기 primary 정책의 첫 시도다. 공통 순차R2에서 다시 생성한8답이 아니며, 하나의 사례별 route 배정은 분포 평균이 아님 |

`Policy.plan:71–85`는 fixed에 seed0, update에 `[schema,seed,phase,index,'order']` 기반 seed를 쓴다. primary는 **학습과 같은 정책 계열**이지 평가 batch가 실제 학습의 동일 route였다는 뜻이 아니다. 평가 batch 순서/phase는 route 배정을 함께 정한다. 실제 update primary의64 VAL batch에는 route SHA47개, fixed/uniform에는 각각1개였다. 새로운 route seed/배치 순서에 대한 오차범위를 측정했다고 주장하지 않는다.

같은 총 방문 수의 작은 차이도 확인했다. primary에서 assistant target×방문 합은 uniform/fixed/update가71,448인데 balanced는71,428, target가중 평균방문23.993282다. balanced의 VAL R분포는 R1×16/R2×32/R3×16이다. secondary는 모두R2×64/가중 방문71,448이다. 이 차이를 보정해 점수를 재작성하지 않으며 “총 방문 예산 같음”을 “감독 token별 방문까지 완전히 같음”으로 확대하지 않는다.

### 28.3 주평가와 공통R2 보조평가 — 서열 차이를 숨기지 않음

다음 값은 같은 VAL512/2,977targets의 최종704 CE다. 차이는 각 열의 uniform 대비이며 낮을수록 이 고정 감독 분포의 NLL이 작다.

| 팔 | 자기 정책 primary CE | primary−uniform | 공통 순차R2 secondary CE | secondary−uniform |
|---|---:|---:|---:|---:|
| uniform_r2 | 2.667774655 | 0 | 2.667774655 | 0 |
| balanced_count | 2.650580304 | −0.017194351 | 2.618869947 | −0.048904709 |
| fixed_shuffle_r2 | 2.497328543 | −0.170446112 | 3.333177469 | **+0.665402813** |
| update_shuffle_r2 | **2.130360002** | **−0.537414653** | **2.068331409** | **−0.599443247** |

**관측:** update가 두 열 모두 가장 낮다. fixed는 자기 정책에서 uniform보다 낮지만, 공통 순차R2에서는 네 팔 중 가장 높고 자기 정책보다+0.835848925 CE 악화한다. update는 반대로 secondary가 primary보다−0.062028593 낮다. fixed의 순서 의존/불일치 대가와 update의 이 공통 경로 전이는 유용한 관측이다. 이것을 곧 일반 강건성·이유추론·실제 정답성 또는 learned routing의 성공으로 부르지는 않는다.

**질문의 차이:** primary는 “각 정책으로 학습하고 그 정책으로 쓸 때”의 묶음 대조다. 순수 훈련정책 효과에 대해서는 train/eval route를 함께 바꾼 `PARTIAL_CONFOUNDED` 해석을 유지한다. secondary는 inference를 동일 순차R2로 고정해 훈련정책 차이를 더 직접 비교하지만, fixed가 학습한 고정 순서를 제거하는 **명시 불일치 진단**이다. 원 서명이 `COMMON_UNIFORM_R2_MISMATCH_DIAGNOSTIC_ONLY`로 정한 보조지표를 좋은 결과 때문에 사후 primary로 승격하지 않는다. 두 열을 선택적으로 인용하거나 최고 점수의 경로/CP를 채택하는 절차를 새로 만들지 않는다.

숫자 차이가 크다는 것과 이 새 SFT 가족의 통계적 유의성/재현성을 검증했다는 것은 다르다. 한 seed·하나의 noisy VAL512이며 본 조건의 다중 seed σ가 없다. 과거 다른 가족의0.024/0.07 등 문턱을 가져오거나 일반 benchmark 점수와 절대 비교하지 않는다. before도 자기 경로이므로 update7.726576001과 §21 uniform6.440286413의 차이를 초기 weight 실패로 읽거나, 전후 개선량을 빼 순수 학습이득이라고 부르지 않는다.

### 28.4 실제8답씩 — 새 두 셔플의 내용과 기존 두 팔 대조

readback의 **실제32답을 전부 읽었다.** semantic_score는 모두null이다. 기존 uniform/balanced16답의 문제는 §21.4와 같은 관측이며, 여기서는 새 fixed/update16답을 각각8사례로 요약한다. 아래 짧은 원문과 생략은 연구문서의 설명일 뿐 원 JSON을 바꾼 것이 아니다.

| 질문 목적 | fixed_shuffle_r2 실제 답·판독 | update_shuffle_r2 실제 답·판독 |
|---|---|---|
| KO 2+3, 값만 | `1` — 형식은 짧지만 값 오답 | `1, 2, 3, 4, 6, …10, 10, …`/MAX160 — 정답5 없이 열거·반복, 형식/값 실패 |
| EN 7−4, 한 자리 | `7 minus 4.` — 문제 되풀이, 값3 아님 | `7 minus 4` — 같은 문제 되풀이 |
| KO 과일2개/쉼표만 | `1. 말고리는 …치소리가…` — 과일/쉼표 요구를 충족하지 않음 | 실제 문자열은 **U+200B 네 개/12 UTF-8 byte**, content token8 뒤STOP. 빈 문자열도 정상 과일 답도 아님 |
| EN result=5 JSON만 | `DJAON is a key component…performance…` — 무관, JSON 아님 | `Sure, here's a list of key results…Define key outputs…` 반복/MAX160 — JSON/내용 실패 |
| KO 물이 얼면 | `물이 얼면 아래쪽은 얼어붉은 얼음이…` 반복/MAX160 — 얼음 단어가 있어도 정상 한 문장 답변 아님 | `물이 얼면 무엇이 되나요.` — 질문 재서술, 얼음이라는 답 없음 |
| EN 인간이 사는 행성/한 단어 | `The planet is a planet-sized planet…diameter…5,000 years…warm…` 반복/MAX160 — 단위/대상 혼동·형식 실패. 뒤의 Earth 단어만 골라 정답으로 승인하지 않음 | `The planet humans…great…British…Greek word…` 반복/MAX160 — 답 대상·한 단어 요구 실패 |
| KO 비밀단어 재기입 | `날이 되면,…아침날은…` 반복/MAX160 — 다른 세 팔의 `별빛`과 달리 이 사례도 실패 | `별빛` — 이 한 사례의 요구 충족 |
| EN 빨간 상자→무겁다/yes-no | `Yes, it is not…common ground-based box…` 뒤 부정/긍정·반복 — yes/no 요구를 벗어나 모순적 내용 | `Yes, red boxes are heavy.` — 주어진 관계의 내용은 맞지만 “yes or no”만 쓰라는 좁은 형식은 초과 |

update의 마지막 답은 내용 성공과 형식 초과를 함께 기록하고 실패 하나로 뭉개거나 완전 형식 PASS로 올리지 않는다. fixed의 첫 `Yes`·얼음·Earth 역시 실제 문장 전체의 모순/반복을 지워 정답 처리하지 않는다. U+200B 사례는 C0가 아니며, 이 문자열을 C0 로그 오류와 혼동하거나 공백 제거로 정상 답을 만들어 내지 않는다.

종료는 uniform STOP6/MAX2, balanced STOP7/MAX1, **fixed STOP5/MAX3, update STOP5/MAX3**다. 가장 낮은 CE의 update에도 MAX160 세 답이 있고, STOP 답 중 문제 재서술·가시 내용 없는 U+200B가 있다. 따라서 CE 개선/종료코드0/정상 stop을 생성 품질 개선과 동일시하지 않는다. 같은8개는 이미 알려진 소형 진단이고 source/형식/언어·의미의 대표 표본이나 독립 정식 benchmark가 아니다. 사후 정성 판독의 주장 등급은 `DESCRIPTIVE_ONLY`이며, 여기서 새 자동 정답률·채택 문턱을 만들지 않는다.

### 28.5 update의 epoch·gradient·시간과 최종 판단

update primary의 epoch1→4 CE는 **2.047433860 → 2.010020857 → 2.091470438 → 2.130360002**다. 네 관측 중 최소는 epoch2이고 최종은+0.120339145 악화했다. 사전 고정704/마지막 CP 결과는 그대로이며, 사후 epoch2를 최종 주결과로 대체하지 않는다. report의 train_ce **2.668423506은704 update 전체의 target가중 평균**이지 마지막 CP의 결정적 TRAIN CE가 아니다. 이를 최종 FP32 VAL CE와 같은 눈금으로 빼 계측 오류나 일반화 gap을 단정하지 않는다.

grad_max는 **18.719238281**이다. 읽은 update source `p078_route_training.py:199–204`는 유한성을 확인한 뒤 **clip 전** 원소 최대/norm을 기록하고 global norm1 clipping을 거쳐 optimizer.step한다. 따라서 “큰 clip 전 gradient가 있으나704 완료”와 “안정성 PASS”를 분리한다. 이번에는 원 raw의 최대 update 위치·post-clip tensor·optimizer state를 새로 검사하지 않았으므로 그 값을 추정하지 않는다.

실제 update_seconds704개 합은 **4,058.085788s/67.634763분**이다. 시작·VAL·첫답·저장/종료를 포함한 worker 전체시간이나 이전 보수 forecast가 아니며, §21의 옛 두 팔 update 합과도 구분한다. fixed의 학습시간/gradient는 이번 지명 두 JSON의 선택 필드에 없으므로 별도 파일을 임의로 열거나 수치를 추정하지 않았다. 새 스모크11:38 실행에도 관여하지 않았다.

**현재 결론:** 원4팔 SFT704와 원4팔 readback은 닫혔고, 같은 초기화/노출·평균 padded 방문 예산에서 update 셔플은 고정 VAL의 두 CE 경로 모두 가장 낮았다. 그러나 fixed의 경로 불일치 대가와 실제 답변의 계산/형식/반복 실패가 남아 **정답 품질·추론·배포 채택의 성공으로 승격할 근거는 없다.** learned_router는 이 Stage2 보고서에서 계속 `NOT_IMPLEMENTED`이며 별도 Stage3 실행 상태는 이번에 조회하지 않았다. 이전 두 팔의 재수행·새 자료/조건·epoch/경로 선택을 제안하지 않는다.

이번 쓰기는 본 문서 §28뿐이다. 원 report/자료/로그/CP·원 P07844소스·공유 계획/결과/기준표/원장·검사기·설치를 바꾸지 않았고, 프로젝트 코드/모델/GPU/스모크/추가 agent/Git 실행0이다. 공용 C0 검사기의 두 P2 수리/7시험 PASS와 원 진단 로그의 C0 미해결 보존은 총괄 보고로 접수하되 이번 P078 감사에서 재검증하지 않았다. 상태는 **`FOUR_ARM_REPORT_READBACK_REVIEWED / PRIMARY_SECONDARY_SEPARATED / ALL32_FIRST_ANSWERS_READ / NO_AUTOMATIC_ADOPTION_OR_NEW_EXECUTION`**다.

## 29. ALM float 기술 진단과 기존 삼진 경로의 범위 차이 — 새 분기 착수 전 감사

### 29.0 범위·읽은 정본·현재 권한

총괄은 문헌담당 §19의 지적을 회수하고 아래 다섯 항목의 **읽기 검토와 본 문서 쓰기만** 요청했다. `impact-analysis` → `exp-preflight`/`exp-plan`을 읽어 조건·기존 구현·다안/비용/한계를 검토한다. 공유 계획·WIP·기준표·런처를 갱신하거나 실험 입장권을 발급하지 않는다. `check_run_registry`/CPU 회귀·prepare/torch import·GPU는 실행하지 않았으므로 완전 preflight PASS도 아니다. 원 첨부1071행 전체를 읽되 문헌 요약/이전 포괄 실행 문구를 이번 담당의 권한으로 확대하지 않았다.

읽기는 [첨부 §0.3/§3.3–3.5/§6.3](/home/uranus/tinyLM/ai_dev_tool/temp_20261023_작업지시서_참고용.md:205), [P106B Stage7c–7e 계획](/home/uranus/tinyLM/test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md:7536), 학생 제어기/관련 회귀, 기존 weight route/strict loader, 모델의 실제 embedding/head/STE 소비 경계, 기준표 관련 조건과 문헌 §19다. parent manifest는 `native595-f/q`의 지명 entry/header/CP descriptor **metadata만** 골라 읽었으며 CP bytes/tensor와 TRAIN/DEV/공식평가 원문·V7 수집 중 packet/cache/report는 열지 않았다.

| 영향 축 | 이번 판별·권한 |
|---|---|
| 코드/중복 | 손실/삼진/loader/업데이터는 이미 있음. 새 부모·route·study identity 연결이 필요한지 판별만 수행 |
| 데이터/호환 | 같은 V7 teacher cache를 재사용할 조건을 기술. 동결1024·정답·정렬·허용오차·teacher source 변경0 |
| 시험 | 기존 합성 검사의 범위와 새 QAT 연결의 필요한 음성/oracle를 제안만 함. 실행0 |
| 정본/기술부채 | float 계획의 정당한 좁은 질문을 보존하되 원 삼진 요청의 미완료를 공개. 이후 분기/등록/결과 연쇄는 총괄·사용자 소유 |
| GPU/동시/증거 | 현재 V7 cache 수집을 방해하지 않음. 새 source/부모/gradient/cost/학습/평가 실행0. 자료·기존 소스·원형·설치·Git·서브호출0 |

학생 source SHA256은 `6F3F8439A7FE89E4C23BC84740191D6B459C11470BA37BE770D3E6B75EFC945A`, test는 `5B5E46E82521466BD758EDE4EA05267B0A8B7E0417E507A227FF667197B327E5`, weight route는 `C2E77B6E8B3CD3338F853B0E5364BD41C9E3650091A11F652479494C55616187`, V7 cache source는 §24의 `0B53379EC83A79F578960B652B4EDF9FC16C456FA1988D1876CD6DEBCE0A4B6B`다. 본 절의 상태는 source-only이며 cache 진행/완결 여부를 재조회하지 않았다.

### 29.1 (1) 왜 float인가 — source에 있는 근거와 없는 근거

**float는 우발적인 loader fallback이 아니라 사전에 좁힌 기술 진단이다.** 계획 Stage7c의 “왜”는 native 확률/byte 사건을 실제 학생 학습으로 연결할 수 있는지 묻고 대상을 **Native595-F의 같은 초기화**, 재귀/MTP/tokenizer/부모 변경 없이 고정한다. Stage7e도 같은 native595-f 원4543 완료 CP의 strict header/route/core를 검산한다고 명시했다. 선택한 TRAIN-only λ 교정도 ALM binary-KL 연결의 크기/방향을 한 번 관측하는 최소 진단이며 논문 GradMag는 아니다. 따라서 현재 계획의 질문과 float 구현은 일치한다.

구현에서도 [study_identity:143](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:143)가 parent_name을 native595-f로 제한하고, `_prepare:511`이 그 entry를 선택하며, [runtime:607/615/629](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:607)의 세 context와 두 `load_routed_state`가 모두 `float`다. weight route의 float는 latent FP32 master를 weight에 대한 identity view로 사용하고 STE 창을 우회한다. 입력 gradient는 해당 실수 선형 연산의 통상 미분이며 수치가 항등행렬이라는 뜻은 아니다. `set_anneal(1.)`와 평가 `freeze_quant()`를 호출해도 이 context에서는 hard 삼진으로 바뀌지 않는다.

**그러나 이를 원 첨부의 삼진 결합 완료라고 할 근거는 없다.** 첨부 §3.3은 CE/SFT-only와 **ALM+현재 삼진 학습 경로**를 기준으로 요청하며 §0.3/§6.3도 float는 개발/진단용이고 삼진 주비교를 대신하지 않는다고 구분한다. 읽은 계획에는 float로 그 연결 질문을 좁힌 기록은 있으나, 사용자가 원 삼진 요청 자체를 철회했다는 근거는 없다. 따라서 이유의 정확한 범위는 **“ALM 신호 연결의 혼입을 줄이기 위해 F 부모/identity backward로 고정한 별도 기술 진단”**이다. 삼진이 원리적으로 ALM에 불가능하거나 먼저 float에서 정상 답변을 얻어야 한다는 근거는 없고 그런 선결을 새로 만들지 않는다.

### 29.2 (2) native595-q의 별도 CE/ALM 두 팔에 필요한 정확한 계약

현재 metadata의 F/Q는 다음과 같다. 이는 manifest 선언을 읽은 것이며 이번 CP 자체 재해시/로드는 아니다.

| 항목 | native595-f | native595-q |
|---|---|---|
| 부모 CP | `runs/ckpt/m100s10_ko-en_p106b_native595_v1_s1337_float_native.pt` | `runs/ckpt/m100s10_ko-en_p106b_native595_v1_s1337_ternary_native.pt` |
| CP SHA256 | `7DF60C47605B654520C510E2758D559213AABCB7ED1090424BDC0D50BC9413BA` | `C0610452ABF357868DA1CCDF16D98482D408F2D9D076C634444292023108BDF5` |
| core SHA256 | `E21E7023D5F289E2EBA2C65127491CB8016232A538E0619E63068BA095D4E3DD` | `C8F2A68232D95C8D4A8EDC455A5D389211806609C2F58E780C6EFF66E497F2DB` |
| forward/backward | `LATENT_IDENTITY_VIEW` / `IDENTITY` | `ORIGINAL_ANNEALED_TERNARY` / `ORIGINAL_STE_WINDOW` |
| 공통 기본 구성 | 4543step·373,134,277B·chat32/V32768/r256·2+10+2 | 왼쪽과 같음 |

양 부모는 선언상4543step·373,134,277B·chat32/V32768/r256·2+10+2이며 gradient checkpoint ON, MTP OFF, `micro_group=128`, `twn_thr_ratio=.7`, `ste_clip=2.5`, `quant_anneal=1`, wq/KV FP32다. 숫자/shape가 같아도 core는 다르다.

아래는 **향후 별도 승인 시 필요한 변경 목록**이지 이번 수정 내역이 아니다.

| 계약/파일·메타 | 필요한 차이·불변 경계 |
|---|---|
| 새 학생 driver/test·새 namespace | 현재 `diag_p106b_alm_train.py`/test와 TAG/BASE/EVIDENCE/CP를 보존하고 학생 전용 별도 분기와 회귀를 만든다. 예시 `diag_p106b_alm_train_ternary.py`/전용 test·Q 전용 tag는 후보 이름일 뿐, 충돌 검산/승인 완료 이름이 아님. 기존 전역 TAG/BASE를 런 중 monkeypatch하지 않음 |
| 준비/identity | `study_identity`의 F 제한, `_prepare`의 F 선택, 부모 entry/CP/header/core/입력 pin, SCHEMA/phase identity/calibration pin을 새 Q 가족으로 분리. 명시 `weight_route=ternary`, route metadata, anneal1 및 범위/예외를 identity·보고서에 결합 |
| CPU/실제 load·reload | runtime의 최초 CPU load/child CPU reload/실제 GPU context 세 곳과 strict `load_routed_state` 두 곳을 **같은 ternary 계약**으로 잇는다. F checkpoint의 route를 Q라고 retag하거나 `validate_route_metadata`를 우회하지 않음. 새 child header/experiment/CP계보도 Q 부모와 실제 route에 맞아야 함 |
| TRAIN cache/data | 현재 V7 원1024/64batch 전체가 닫힌 뒤 같은 selection/row/record SHA·tokenizer·ChatML·teacher contract·raw logp/정렬 chunk·CE/KD 분모를 읽기 재사용. Q/F 부모의 학생 tokenizer는 같은 pin이므로 **학생 weight 경로만 바꾼 이유로 teacher 재채점은 필요 없음**. 부분 cache를 완성으로 간주하거나 reference를 새 답변으로 교체하지 않음 |
| DEV/평가 입력 | 같은 DEV512, 고정64 질문/주석·8 사용자질문·native32 및 prompt/admission hash를 고정. **SCHEMA만 새 문자열로 바꾸면 `_prepare:524`의 `sha([SCHEMA,1337,"FIXED_DEV",root])` 선택도 달라진다.** 따라서 새 identity schema와 기존 평가 selection seed/schema를 분리하거나 기존64 IDs/SHA를 명시 이관해야 F/Q 비교의 입력이 유지됨 |
| Q 전용 TRAIN gradient 교정 | 같은 언어별 첫64/총128, whole-update CE N/KD K, 실제 마지막 block 고유 parameters에서 새 CE/KD norm/cosine/None·core/RNG불변을 회수. `λQ=.25*||gCE,Q||/||gKD,Q||`를 한번 고정. **F λ/교정 영수증 재사용 금지**. zero/nonfinite/graph 단절은 HOLD이며 임의 λ 상향으로 닫지 않음 |
| cost/train/종료 | Q 부모에서 CE/ALM 각각 fresh RNG/core/empty optimizer로2cost → 동일 부모에서각32학습. 원4epoch/행순서·m8a16/1024/checkpoint/BF16 eager/TF32 OFF/기존 optimizer·LR/WD0/clip1, head chunk64, τ100/GradMag·hidden·outcome OFF 유지. QAT라고 새 anneal warmup/GSQ/optimizer를 함께 넣지 않음 |
| CP/평가/readback | Q 전용 ce/alm weight-only CP1씩·정확 `quantization_route=ternary`, 새로운 study/phase/parent/교정/source SHA, 동일32step 노출을 저장. 부모Q+CE-Q+ALM-Q 세 종점은 같은 실제 ternary path/anneal1로 평가·재로드. 기존 수동6종 inference-only manifest는 부모의 출처이지 학습 권한/새 child 등록부가 아님 |
| 새 권한/문서·source map | 새 Q 가족의 허용 parent/route/tag/입력·전용 source/test/caps/종료/부분보존을 총괄이 명시하고 계획·등록·결과 연쇄를 소유. 새 파일은 source map에 포함하되 활성 teacher cache의 CODE/기존 source·준비 identity는 변경하지 않음 |

기존 controller의 순수/부모독립 함수와 ALMCore는 재사용 후보지만, prepare/study_identity/checkpoint_path/do_train/evaluate/execute에는 고정 TAG/SCHEMA/BASE/EVIDENCE가 섞여 있다. **flag 하나만 추가하면 끝난다는 범위는 아니다.** 상수의 암묵 전역 변경 없이 새 독립 adapter/명시 context로 provenance를 닫아야 하고, 이 구조 선택/구현은 별도 승인 대상이다.

### 29.3 (3) 부모 변경인가 QAT 교락인가 — 비교 단위를 분리

**F 가족 대 Q 가족의 직접 차이는 단순 부모 변경이 아니다.** native595-f/q는 원 pretraining부터 identity 대 삼진/STE로 다른 궤적을 거친 core이고, 후속 SFT에서도 forward와 backward가 함께 달라진다. Q의 `_TernarySTE`는 group별 threshold/mask·mean-abs scale로 `{-alpha,0,+alpha}`를 만들고 backward는 `1/(1+(|w|/(clip*alpha))^4)`의 surrogate window를 곱한다. anneal1에서 이를 업데이트하는 것은 latent FP32 master를 가진 기존 **QAT/STE fine-tuning**이며 고정 code를 한 번 저장해 상수로 미분하는 PTQ도, Gumbel/GSQ 학습도 아니다. float의 anneal1 호출과 동일하지 않다.

- **Q-CE 대 Q-ALM 내부:** 같은 Q 부모/route/초기화·자료·노출·optimizer에서 추가 binary-KL 신호의 기여를 묻는 통제 대조가 가능하다. 원 float 결과를 선결로 요구하지 않는다. 같은 원신호를 다시 쓴 새 Q 경로 진단이지 기존 학습의 무의미한 재실행은 아니다.
- **F-ALM 대 Q-ALM 또는 두 가족의 이득 차이:** 부모의 사전학습 이력·실제 weights·forward·STE backward와 route별 λ 교정값이 달라질 수 있다. 이를 순수 “삼진 비용”이나 ALM×양자화 단일 상호작용의 크기로 인과 분해하지 않는다. 자연 배포 경로 두 묶음의 조건부 비교다.
- **같은 F 부모에서 ternary로 전환:** 초기 master weights는 같게 할 수 있지만 새 QAT 전환 개입이다. F header를 `load_routed_state(...,"ternary")`에 바로 넣으면 현 strict loader가 올바르게 거부한다. 필요하면 원 F 로드 검증과 새 target route의 bridge 계약/새 child metadata를 따로 설계해야 하며 native595-q에서 이어 학습한 것으로 부르지 않는다.

**삼진 범위에 두 번째 미완료가 있다.** route metadata는 두 모드 모두 `scope=TLINEAR_WEIGHTS_ONLY`다. 실제 transformer는 `emb=nn.Embedding`, `emb_up=nn.Linear`, `_emb_w/_emb_up_w`와 tied `_head_logits`를 사용한다. `cfg.quantize_embedding=True` 선언이 있어도 현재 학습에서는 FP32 master table/projection이며 weight_route가 이 두 nn 모듈을 삼진화하지 않는다. 따라서 B안이 완료돼도 정확한 명칭은 **“기존 TLinear 삼진/STE 경로+FP32 tied embedding/head의 ALM core 대조”**다. 첨부의 본체와 큰 embedding/head 전체 고정 삼진·packing·40MB 목표까지 완료된 것은 아니며, 이번 누락을 메운다는 이유로 head 양자화까지 동시에 새 구현하지 않는다.

### 29.4 (4) 최소 세 안과 추가 구현·CPU/GPU 비용의 한계

| 안 | 질문·장점 | 추가 구현/CPU | 추가 GPU·한계 |
|---|---|---|---|
| A. 기존 float 기술 진단만 보존 | F에서 고정 byte 신호가 학습에 연결되는지 가장 좁게 확인. 현재 구현/출처를 유지 | 이 삼진 누락을 메우기 위한 구현0. 기존 CPU/prepare 선결은 그대로 | Q 추가 GPU0이지만 **원 삼진 결합은 NOT_RUN**으로 남음. float 성공을 삼진 완료로 보고하지 않음 |
| **B. native595-q/ternary의 독립 CE·ALM 두 팔** | 원 “현재 삼진 경로”에 가장 직접적. 같은 teacher cache/원 손실·자료를 재사용하고 Q 내부에서 신호 기여를 분리 | 중간 수준의 controller identity/runtime/CP·readback 연결 및 전용 CPU 음성/oracle. 새 loss·삼진 primitive·teacher 구현은 불필요 | Q 전용 교정1+각2cost+각32train+세 종점 평가. 수렴/시간/VRAM 미실측. F/Q 가족 간에는 부모/QAT 교락을 공개 |
| C. 같은 F master에서 명시 QAT bridge 후 CE·ALM 두 팔 | F와 같은 출발 weights에서 삼진/STE 전환을 연구하는 더 좁은 초기화 통제 | B의 provenance/회귀 외 **cross-route bridge/새 초기 effective codes/scales·header 계약** 추가. F source/CP는 보존 | 적어도 B와 같은 두 팔과 새 bridge 검증/초기 종점 필요. native595-q continuation의 답은 아니며 전환 효과와 pretrained-Q 효과를 대신하지 않음 |

**권고는 B의 학생 전용 준비 설계를 별도 승인·동결하는 것**이다. 이는 오늘 실행 결정이나 GPU 사용 승인이 아니다. F 기술 진단이 타당하다는 사실을 유지하면서 원 현재 삼진 경로 질문을 직접 닫고, C의 별도 변환 개입을 피할 수 있다. 충분한 구현/CPU/실물 시간 창이 없으면 A 상태를 정직하게 남긴다. 목표 embedding/head 전체 삼진이나 GSQ까지 덧붙여 B라고 부르지 않는다.

**비용은 단계 수와 미측정 시간을 분리한다.** B에는 원1024 teacher scoring의 추가 반복0을 기대할 수 있지만, 원 공통 teacher 시간은 총 time-to-quality에서 사라지지 않는다. 같은 cache를 썼다고 별개1024 원천/새 교사 생성 건수를 추가 가산하지 않는다. source/manifest/hash·정렬 준비/CP header 검증은 CPU이고 기존600초 prepare cap은 예상 소요시간의 실측이 아니다. Q λ 교정은 optimizer0이어도 **실제 학생 GPU forward/autograd**이며 CPU-only라고 쓰면 안 된다.

Q cost는 총4optimizer update, 본학습은 총64update다. 원32×8×16×1024=4,194,304 padded slots/팔이며 1024 고유행을4회 쓰는 SFT다. 현 계획의 actual x1,025,068/CE23,588은 준비 단계에서 다시 닫아야 할 **예정 노출값**이지 이번 진행 중 cache를 읽어 새로 검산한 값이 아니다. pretraining의 pool≥2× 조건을4epoch SFT가 충족했다고 쓰지 않는다. 세 평가 종점은 각각 DEV512 TF+64고정답+8사용자관측+native32이며 parent/child 로드·hash·저장/정리 비용도 별도다.

현재 입장식 `32*(2update training_seconds/2)*1.5`를 두 팔 합산하고 cost의 관측 비update overhead 및 세 평가 reserve900초를 더하는 것은 **보수 외삽 규칙**이다. 이를 Q 실측 없이 분/VRAM 숫자로 환산할 근거는 없다. reserve300초/종점·초기2시간 상한은 운영 가정이지 실제 완료 보증이 아니다. QAT는 master/optimizer가 FP32이고 effective quant cache/STE/activation/재계산이 있으므로 “삼진이라 학습 RAM이2bit/시간은 F와 동일”이라고 추정하지 않는다. 먼저 Q 양 cost/실제 초기화·gradient·평가 비용을 회수해야 현재16:30 모델종료·phase cap/정리 여유에 맞는지 판단할 수 있다. 현재 캐시 worker와 동시 실행해 얻은 속도를 단독 cost로 쓰지 않는다.

### 29.5 (5) 이미 있는 구현과 실제 net-new·필요 회귀

좁은 검색은 `scripts`/`tinylm`의 Python source만 대상으로 했다. `ALMCore/chunk_kl/P106B_ALM_REFERENCE`의 학습 연결은 현재 학생 driver/core/test에서만 확인했다. **별도 Q 부모 CE/ALM 두 팔이 이미 완성돼 있다는 source는 이 범위에서 찾지 못했다.** 저장소 전체/보호자료를 뒤져 부재를 증명하거나 완료 결과를 재실행한 것은 아니다.

| 기존 구현 | 재사용 범위·재사용할 수 없는 주장 |
|---|---|
| `p106b_weight_route.py` ternary/context/strict load, `test_p106b_weight_route.py:143` | 기존 TLinear 삼진 forward/STE·캐시 수명·strict metadata/alias 검증이 있음. 새 양자화 primitive를 만들 필요 없음. 기존 회귀는 .4 anneal의 원경로 parity도 다루지만 Q-ALM의 hard1 실제 연결 완료는 아님 |
| native595/native595_broad/broad4의 Q/F 학습·route CP | Q 부모→해당 ternary route의 로드/SFT/eval 재사용 사례가 있음. **다른 자료·704/CE**를 새1024/32 ALM 대조의 완료로 옮기지는 않음 |
| `tinylm/train/alm.py`, 학생 `ALMCore`, 기존 padding updater/optimizer factory | per-position 원 tied head NLL·binary KL·CE/KD 전체 update 분모·fresh optimizer·source/입력 봉인·새CP·기본평가를 재사용. net-new는 Q 부모/route를 처음 결합하는 identity/runtime/교정/비용/재로드 연결 |
| `p093b_native_repair.py`의 `GSQProjection/GSQAdapter/gsq_shared` | **Gumbel mask/sign·group scale의 실제 로컬 진단 구현은 이미 존재**한다. 다만 MLP/LoRA 함수 재구성의 normalized squared error이며 외부 teacher reference CE/ALM·whole-model/tied-head GSQ 학습이 아님. 새 GSQ를 처음부터 없었다고 보고하거나 이 진단을 ALM+GSQ 완료로 재분류하지 않음 |

새 CPU 회귀의 핵심은 pure ALM 수식을 다시 많이 만드는 것이 아니라 **새 조합의 음성 경계**다. F/Q 부모·route/header 교차 거부, 새/옛 tag·교정/child receipt 혼입 거부, λ0의 KD-backward0, 같은 row/hash/shift/EOT/분모, 새 SCHEMA가 고정64평가를 바꾸지 않음, 실제 ternary refresh+anneal1의 유효 `{-alpha,0,+alpha}`와 원 STE-window surrogate gradient, activation-checkpoint 재계산/optimizer 뒤 cache refresh·context 수명, CP strict 재로드/route복원을 작은 합성 oracle로 닫아야 한다. hard quantizer의 수치 미분과 surrogate STE가 같아야 한다는 잘못된 oracle는 만들지 않는다. 현재 ALM 회귀의 parent fixture는 F이고 header route도 문자열 dummy로 검산하는 구간이 있어, 그 PASS만으로 실제 QAT runtime의 합동 검증을 대체하지 않는다.

**최종 상태:** F-only 기술 진단의 계획/구현은 일관되지만 원 삼진 결합과는 별도다. 기존 삼진/ALM primitive를 재사용한 Q-CE/Q-ALM 독립 가족이 가장 직접적인 누락 보완 후보이며, cache 수집 중 공용 source를 바꾸거나 float 결과를 retag할 필요는 없다. 이번 수정은 본 문서 새 §29뿐이고 source/공유 계획/원장/CP/원자료/V7출력/실행 환경은 그대로다. 구현·CPU 회귀/prepare·교정·cost·학습·평가·모델/GPU·설치·다운로드·Git0이다. 상태는 **`FLOAT_DIAGNOSTIC_SCOPE_CONFIRMED / TERNARY_PAIR_CONTRACT_DESIGNED_ONLY / EXISTING_PRIMITIVES_REUSABLE / NO_COMMON_SOURCE_CHANGE_OR_EXECUTION`**다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 30. 미게시 KO24965 v2와 비SFT 명시 교정9건의 우선 판독

### 30.1 분모·권한·원문과 후보의 식별

총괄은 KO24965의 지명 v2/원 packet과 비SFT 첫8 packet의 후보 중 **명시 교정9건부터 먼저 마감**하도록 요청했다. 이번 정밀 대조 분모는 **비SFT9/64원천**이며 원 영어9개/총24,799문자와 번역·재표현 본문을 모두 읽었다. 3118은 HOLD/두 본문 공백이므로 실제 번역·재표현은8쌍/16본문이다. 첫8 packet이 각8원천이라는 metadata는 확인했으나 **나머지55원천의 v1 정밀 대조는 미완료**다. 첫64 전체 또는 혼합 캐시1.44M 전체의 품질 검사·학습원천 승인으로 보고하지 않는다.

원문 경로는 `/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/non_sft_translation_packets/non_sft_translation_00000N.json`, 후보는 같은 작업 폴더의 `scratch/non_sft_translation_v1/non_sft_translation_00000N/ID_vV.json`이다. 아래 표의 packet/version을 결합한 **정확 파일만** 최종 판독 대상으로 삼았다. 원문 string UTF-8 SHA는9개 모두 packet의 선언과 대조했다. 후보8개는 strict JSON 해독 뒤 id/source_sha256을 대조했고, 3750은 아래 구문 실패를 남긴 채 raw text의 명시 id/hash와 본문을 읽었다. 버전이 낮은 파일로 자동 fallback하지 않았다.

| source_id / 후보 | packet | 원문 SHA256 | 후보 파일 SHA256 |
|---|---:|---|---|
| 678681_v2 | 1 | `C91DA45D498513E19EF0517E79D5CEA5CF9AB014952F4D6809B246413E9B58E0` | `47D278FA8B8CA48399D33ECF3E9A1F4236B340C386BC86BBED96C2519DDE4195` |
| 1120379_v2 | 2 | `85F2B96E0A1E23B3B576FA558915819AB2485840AAB35B1ED1360117A062CCB4` | `852DE2520ABF9EE517D04C07ECF496519C5B61D64D1A737494206E940FF9B054` |
| 1267384_v2 | 2 | `D7BBF23D653BF164843D75E2D8B9511CE71D02DAD7605AB668B870ECCB9B5561` | `878B704C28A35F466F7B30341CEBC3698DC6F48BF46603ED5DAC4F19D4744B9F` |
| 1296532_v2 | 2 | `C8B5ECFB931140B0B0CB58C382D7C86E21D08E112A20487449233C770C18F547` | `62320B22DC530CF371F676FC59A11F2317FE158B3948CDDAB7208E84BC4C4E5C` |
| 303_v2 | 3 | `D251A8EFE77187A172E83416181F08897CB6CFC25EAD0A902B01B702732ED685` | `C0A5C2702224D8C3247D2D32D0571227C6666DA1D1BE1E07FBDADE3BA327E75C` |
| 468_v2 | 3 | `D9E2662549931AF2E352AE70815B07FF1F10D0A069989CE652F7CB3CF6EF929A` | `EF245719B5BD8A518F6BADF4AEB82B7478AFF990ACB4860A7C0D744DC7764323` |
| 2728_v3 | 6 | `367953B395A7377F45F129721B99BE7AC8A43BDFA714A80CEE2BC3417CDBD220` | `2FA5E8A471A56FB7E1FCDC2993013C435999423715B296E7D058D502A08DBE52` |
| 3118_v2 | 6 | `02DC1DCFA363F323B765D7CE1CB146EC3C43977B52A51E5A582533E253008B3D` | `527C9525C6DAA9465032C9AF4D105D65F24183DF05265CA9DB7FA549F541E40A` |
| 3750_v2 | 7 | `4CE8582A2881931BE3D26B1647C1D5995AEC2676ED235C02868132018B8659F1` | `9DB8DBCF06102646D7FE8B635DB44D7B0B90A5FD4A76CB1A66EA72BED573C4AE` |

이 판독은 **번역의 원문 충실성과 제한된 구조 검산**이지, 원천의 생물학/의학/교통·입법/통계가 실제로 맞다는 사실 인증이 아니다. 인터넷·모델/API·GPU·설치·추가 agent·teacher cache·공유 계획/원장·Git에 접근/실행하지 않았다. 새 결과 JSON이나 수정 후보도 만들지 않았다. 본 연구 문서만 추가한다.

### 30.2 KO24965 v2 — 내용은 지정 삭제와 같지만 LF도 하나 삭제됨

지명 [미게시 v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/author_scratch/luna_ko_20261023/native_full_ko_000041_24965_v2.json) SHA는 `C78E700F0EA33F71C91A58C0DE44CF8E3F70FEEDB411C4C9038432B06F610909`이고 [원 packet](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/packets/native_full_ko_000041.json) 파일 SHA는 `773B716840A4D3BC4C5E581F5168294F01D7A85A091F75453C803AD2F438DB64`다. packet에서 id/eos_segment_index24965인 유일한 문서를 골랐고755 LF행의 원문 string SHA `2D4FD75700DE0C9A0C11B31EB0C1AFA2D07BD5E6EA981DBBB31C4EEFB7F215C6`를 실제 재계산해 맞췄다.

승인된 CPU stdlib 범위에서 **기존 `apply_positioned_edits`를 실제 호출**했다. 모델/프로젝트 전체 import를 피하기 위해 원 source의 `lf_lines`/`apply_positioned_edits`, 기존 `p106b_source_cleanup.sha`의 AST 함수 node를 내용 변경 없이 선별 compile/call했다. 입력은 정확한 원문/후보1개이며 source/tool 파일을 고치지 않았다. helper source SHA는 `4163FADA22DA728DBB015F7786C56EEECBD9DB39A33F57A4088E23AB5572AB42`다.

- 후보는 changes1개, `source_lines=[10,10]`, `action=MOVE_TO_PROSE`다. 함수가 지명10행 `[735,1304)`의 Unicode codepoint 범위를 정확히 해석했고 boundary acknowledgment 보정은False였다.
- 지정 구절 **`통산 출루율(427개), `**는 원문10행에 정확히1회 있다. 후보 replacement는 **그 구절만 뺀 원문10행에서 맨 끝 LF를 제외한 문자열과 완전히 같다.** 따라서 문구 내용/선수·지도자 서술/나머지 통산 수치가 추가로 재작성된 것은 발견하지 못했고, 원10행 밖의 모든 문자도 함수 결과에서 그대로다.
- 그러나 원10행은 LF로 끝나고 replacement는 LF가 없다. 실제 전체 결과는 지정 구절 삭제에 **LF1개 삭제가 추가**된다. 그러므로 “원문에서 오직 지정 구절만 제거, 나머지 문자 그대로”라는 엄격 조건의 결과는 **실패**다. 결과를 공백 정규화해 PASS로 바꾸지 않았다.

실제 함수 결과 SHA는 `E39558ED11A6AD822797FAA22DA81D34C24C3B262325F19DE1F483A16BD03943`, 정확한 구절1개만 삭제하고 LF를 보존한 기대 결과 SHA는 `B82FE6FA1AC8CFA232EF6C1A237E1E2A1B5C0F17A5434BF11ED5C6B3B7AD71D2`다. 반복되는 `통산 출루율` 때문에 일반 diff의 정렬은 다른 삭제 조각처럼 보일 수 있어, 단순 opcode의 삭제 문자열이 아니라 **명시 기대 문자열과의 전체 equality**로 판정했다. 별도 승인이 있으면 replacement 말미 LF 보존만 제안할 수 있다. 이번에는 v2/v1/게시본·원 packet/적용 결과를 수정·저장·재게시하지 않았다. 이 검산은 원 야구 기록의 현실 사실성까지 판정한 것이 아니다.

### 30.3 비SFT 교정9건 — 확실한 차이와 추정 위험

아래에서 **확실**은 이 원문/후보 사이의 직접 차이를 뜻하고, 그 세계 지식이 옳다는 뜻은 아니다. **추정/미확인**은 외부 검증/실행 없이 확정하지 않은 위험이다. 관측하지 못한 오류를 “없다/품질 PASS”로 바꾸지 않는다.

| ID·문제 위치 | 직접 판독·판정 | 제안만 남기는 후속 |
|---|---|---|
| [678681_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000001/678681_v2.json), 두 본문/날짜·기관명 | 이번 대조에서 추가 핵심 의미/수치 오류를 찾지 못했다. 3,000h,7발전소/10–100kW,810million yuan→8억1천만 위안,97.59million USD→9,759만 달러,300마을/70,000·200,000명/135,000톤/2003-08-28을 보존한다. **현재 국가발전개혁위원회로 알려짐**은 원 영어에도 `now known as`가 있어 후보가 외부 지식으로 새 현행화를 한 사례로 보지 않는다. 두언스허 등 한글 인명의 표준 표기는 외부 확인하지 않았다 | 당시 보도/인용이라는 metadata 유지. 현재 태양광 현황·정확한 표준 인명/기관명 인증으로 승격하지 않음 |
| [1120379_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000002/1120379_v2.json), 태그/처리 순서 | pragma 전체-template 범위·reparse/variable 예외, 세 매크로 우선순위, `<!--[tagname]-->` 대 `<!-- [tagname] -->`의 공백 차이, PREFIX 비재귀, `$Tag->tagname()` 제한과[bounce]/이미지경로를 두 본문에서 보존했다. 추가 의미 오류를 찾지 못했다. 재표현의 “원문은 그 항목으로…”는 출처를 가리키는 편집 목소리이나 조건 변경의 증거는 아니다 | 버전 미상인 과거 문서 동작으로 한정. 실제 Interchange 실행/현행 동작 PASS 아님 |
| [1267384_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000002/1267384_v2.json), 코드1행/장 참조 | Response/Trace·Page 속성·운영서버 debug 노출·선택적인 page trace·Chapter10·Message.Label.Text/Response.Write 조건은 보존했다. **위험은 원문 유래 코드 자체**다. `Sub Page_Load( ) 'Example code will go here End Sub`가 실제로 한 LF행에 있고 두 후보도 그대로다. VB 주석 때문에 End Sub 경계가 손상됐을 가능성이 있으며 **코드 실행 가능성을 확인하지 않았다**. 새 번역 오류라고 단정하지 않음 | 역사 기술 설명의 충실성과 실행 가능한 완결 코드 채택을 분리. 추측한 줄바꿈/새 코드로 복구하지 말고 원형·코드 품질 미확인을 공개 |
| [1296532_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000002/1296532_v2.json), 재표현 마지막 문장 | **확실: 원문 밖 편집자 주석이 본문에 추가**됐다. “이 날짜와 수치는 … 현재 상황을 나타내는 것으로 일반화하지 않습니다”는 영어 원문에는 없고 별도 temporal_scope_note에도 있는 검수 설명이다. 반면1790/22회/10년/2010→2020/2012-01-01·312,780,963/17초는 유지하며 현재 수치로 갱신하지 않았다 | 편집/시점 한계는 metadata와 본문 생성 규약을 구분해 처리할 것을 제안. 원 날짜/당시 예측 자체를 최신 정보로 고치거나 삭제하지 않음 |
| [303_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000003/303_v2.json), 재표현 PBFD/권고 | **확실: 재표현에서 한정이 일부 약화/누락**된다. `most important viral disease`→“주요 바이러스 질환”, `often results in an AIDS-like condition`→“AIDS와 비슷한 상태를 일으키고”로 often이 빠지며, OEH의 `only feeding method`도 “권고한다고 소개된 방법”이 된다. 충실 번역은 해당 최상급/흔히/유일을 남긴다. 학명/질병명·수개월~수년 무증상 가능성/2011-04-15는 보존. Loriinae의 한국어 아과명과 원 괄호 `lories and lorikeets`의 범위는 별도 용어 확인이 필요한 **추정 위험** | 조건/빈도/배타성은 단순 축약으로 지우지 않도록 제안. 과거 조류 질병/급식 주장을 현재 수의학 지침으로 승인하지 않음 |
| [468_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000003/468_v2.json), 재표현 연구자/마지막 결론 | **확실: 공동 측정자 `graduate student Naveen Pawar`가 재표현에서는 빠지고 “연구진”만 남는다.** 번역은 나빈 파와르를 보존한다. `likely ... both ... correct`도 재표현 “두 주장이 모두 맞을 가능성이 있다”로 확신 강도가 약해진다. 다섯주·75/65/55mph, 낮은 트럭속도의 제동/조향 개선이라는 caveat, 속도차/사고위험의 양면은 보존 | 고유명 보존 요구와 결론의 likely 강도를 재표현에도 유지할 것을 제안. 주간 고속도로는 interstate 의미이며 낮 시간대라는 새 조건이 아님. 현재 정책/일반 안전법칙으로 일반화하지 않음 |
| [2728_v3](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000006/2728_v3.json), ROR2 두 본문/좌표·잔여 참조 | 적어도12변이·열성2사본/우성1사본·loss/gain-of-function 차이·지속활성의 추정/기전 미상·9q22·94,484,877–94,712,443을 보존한다. **확실: 번역에 “아래에 열거된 다른 이름”과 “다음 자료”가 있지만 이 원문 발췌/후보에 그 실제 목록이 없다.** 원문에도 같은 결손이 있고 reason이 이를 공개한다. 재표현은 긴(q)팔/22위치의 풀이를 생략하고9q22/좌표만 남겨 설명 밀도가 줄었다. source 자체 RTK 명칭/의학·좌표의 현행 정합성은 미확인 | 고아 목록/링크 안내를 독립 교육 본문으로 채택할지 별도 판단. 원 의료상담 면책문은 영어에도 있으므로 **새 편집자 주석으로 오인해 제거하지 않음**. 기준 조립체가 없다고 좌표를 최신 값으로 추측 교체하지 않음 |
| [3118_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000006/3118_v2.json), HOLD | HOLD이며 번역/재표현 모두 빈 문자열·NOT_ADMITTED다. 2004–2008/2008–2013 주기, 연도 없는 October 제안 마감·참여 촉구, 주민 의견/기관 계획과 lionfish/ciguatera 식용 안전 주장이 함께 있는 원문이므로 **이 제한된 발췌에서 보류한 이유는 원문에 근거한다.** 이를 생물학 주장 검증이나 원천이 반드시 무가치하다는 결론으로 확대하지 않음 | 더 쉬운 원천으로 대체하거나 HOLD를 번역완료로 세지 않음. 외부 검증 없이 식용 안전 조언을 새 본문으로 생성하지 않음 |
| [3750_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000007/3750_v2.json), JSON16행/재표현 Hall·단체 규모 | **확실한 구문 차단:** strict JSON 실패. 내용도 두 가지 직접 차이가 있다. `co-wrote a report for the wildlife federation`이 재표현에서 “전국야생동물연맹과 공동 작성”으로 바뀌어 **보고서의 의뢰/수혜 대상 for를 공동작성 주체 with로 바꾼다.** 원문 `more than 5 million`/`more than $125 million`은 재표현에서500만/1억2,500만 “이상”이 되어 엄격한 초과 경계를 약화한다. 영어에 없는 최신 입법 연도/상태를 추가한 것은 찾지 못했고8개주 전원승인·2005/2006/82–5·December/January는 보존 | raw 후보 보존/구문 실패를 먼저 공개하고, 별도 승인 시 새 버전의 구문 및 for/초과 관계만 수정 제안. 현재 법률 상태나 IPCC의 원문 명칭을 외부 지식으로 몰래 교체하지 않음 |

### 30.4 3750 v2의 strict JSON 실패는 의미 판독과 별도

3750 v2는10,074B다. Python stdlib strict JSON 해독에서 `Invalid control character at`, **16행137열/Unicode offset1102/U+000A**로 실패했다. `ko_translation`의 열려 있는 JSON 문자열 안에 escape되지 않은 실제 LF가 있고 재표현 본문도 여러 실제 행에 걸쳐 있다. raw UTF-8 본문을 읽어 위 의미 대조를 했으나 **정상 해독/import 가능 후보로 분류하지 않았고**, strict=False/자동 escape/수정 parser로 통과시키거나 v1로 대체하지 않았다. 이 구문 문제는 고유명·수치·의미가 맞는지와 다른 차단 항목이다. candidate가 스스로 DRAFT_TRANSLATED라 해도 구조 PASS/게시 가능을 뜻하지 않는다.

### 30.5 9건 우선 마감·제한

확정한 우선 결과는 **KO24965의 LF1 추가 삭제**, **3750의 JSON 구문 실패/for→with 및 초과 경계 변화**, **468의 공동 연구자 생략**, **303의 빈도/배타성/최상급 누락**, **1296532의 본문 편집 주석 혼입**이다. 1267384/2728의 불완전 코드·고아 참조는 원문 유래 위험으로 따로 분류했고, 678681/1120379는 이번 범위에서 추가 핵심 차이를 발견하지 못했다. 이것은9건 일괄 PASS 또는8개 번역의 정답성 전수 인증이 아니다. 모든 후보는 그대로 NOT_ADMITTED이며3118은 HOLD다.

의미 대조만으로 라이선스/원천 적법성·사실성·표준 용어·현재 상태·코드 실행·의학/수의학 안전을 인증하지 않는다. **나머지55/64 정밀 판독은 아직 하지 않았다.** 원755행 KO의 의미를 모두 새로 검수한 것도 아니며 그 전체의 문자 보존과 지명10행의 변화만 함수/해시로 검산했다. 지명 원문/후보와 필요한 함수 source를 읽었고 모두 수정/재게시하지 않았다. v1/게시본 본문·새 원장/공유 계획·teacher cache에는 접근/변경하지 않았다. 허용 CPU는 위 함수 호출/stdlib JSON·문자·hash 검산뿐이며 모델/API/GPU/설치/Git0이다. 상태는 **`PRIORITY_NINE_OF64_REVIEWED / KO_LITERAL_CONTENT_PRESERVED_EXCEPT_EXTRA_LF_DELETE / 3750_STRICT_JSON_FAILURE / ALL_CANDIDATES_NOT_ADMITTED / OTHER55_NOT_REVIEWED`**다.

## 31. ALM 학생 Fv2/Qv1 최종 동결본의 좁은 실행 전 반 검토

### 31.1 결론·증거 범위

**이번 변경부의 소스 검토에서 새 P1 차단 결함을 발견하지 못했다. 실제 학생 적재·교정·비용·CE/ALM 학습·자식 평가는 모두 NOT_RUN이며, 이 결론은 실행 허가나 실제 성공 판정이 아니다.** 총괄이 전달한 학생58+경로28=86 CPU 회귀 PASS는 총괄/구현 담당자의 실행 보고다. 반 담당자는 시험을 재실행하거나 torch/프로젝트 모듈을 import하지 않았다. 원본 대비 diff, 변경 함수·호출 경계·추가 합성 시험을 읽었으며 stdlib AST·해시 검산만 했다.

| 고정 대상 | 반 담당자의 실제 바이트 검산 |
|---|---|
| [학생 controller](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py) | `C8EFF2B4F84AE31EA66DD55F8EC3F22771E1CCE89FD9EFB992D18F34F103E51E` 일치 |
| [학생 시험](/home/uranus/tinyLM/scripts/test_p106b_alm_train.py) | `582F2B91BA1AED6E108304D817A1E24E640B7A551FD827ABB8C5C47102A4F51C` 일치 |
| controller의 리터럴 SOURCE_NAMES를 읽어 정렬 JSON으로 재계산한 묶음 | 75개/중복0, `4D29E546347A22FC0F0D66548F79BDC7924E27C4006C4A4A26D6C8D93B3834FD` 일치 |
| [수정 전 controller 사본](/home/uranus/tinyLM/handoff/audit/source_snapshots/20261023_pre_alm_study_profiles_diag_p106b_alm_train.py.txt) | `6F3F8439A7FE89E4C23BC84740191D6B459C11470BA37BE770D3E6B75EFC945A` |
| [수정 전 시험 사본](/home/uranus/tinyLM/handoff/audit/source_snapshots/20261023_pre_alm_study_profiles_test_p106b_alm_train.py.txt) | `5B5E46E82521466BD758EDE4EA05267B0A8B7E0417E507A227FF667197B327E5` |

동시에 읽은 경로 helper SHA는 `C2E77B6E8B3CD3338F853B0E5364BD41C9E3650091A11F652479494C55616187`, teacher cache controller SHA는 `0B53379EC83A79F578960B652B4EDF9FC16C456FA1988D1876CD6DEBCE0A4B6B`다. teacher/cache 원자료·실제 패킷·체크포인트 바이트에는 접근하지 않았다. 기존 두 source snapshot은 그대로 보존했다.

### 31.2 고위험 경계별 소스 판독

1. **부모/경로 일관성:** `StudyProfile`/`StudyContext`는 frozen dataclass이며 새 Fv2는 native595-f/float, Qv1은 native595-q/ternary로 묶인다. `validate_prepared_profile`은 부모명·정책·프로필 해시·route mode/scope/master와 준비본 route/header의 일치를 요구한다. `_prepare`와 `runtime`은 resolve된 spec.arm도 같은 mode인지 확인한다. `runtime`의 부모 CPU 적재, 자식 CPU 재적재, CUDA 전송 후 활성 문맥 세 곳 모두 **같은 mode 변수**를 전달한다. 원 payload의 route를 전용 validator로 확인하고 strict core fingerprint를 CPU/실제 장치 진입에서 확인한다. Q 문맥에 F 부모를 조용히 적재하거나 Q 자식만 float로 평가하는 새 분기는 찾지 못했다.

2. **구 전역 경로 혼입:** 새 준비/결과/교정/비용/학습/평가/체크포인트 경로는 context에서 파생된다. `execute`는 CLI study와 주어진 context가 다르면 거부한다. 새 context의 base/evidence를 다른 프로필로 치환하면 `resolve_context`가 거부한다. 남아 있는 TAG/SCHEMA/BASE/EVIDENCE의 직접 참조는 구 float_v1 정의·호환 생성 분기다. `_prepare`의 `cache.BASE`는 학생 결과 경로가 아니라 **공통으로 동결된 V7 교사 입력**이므로 F/Q 사이에 공유하는 것이 의도된 계약이다. 신규 F/Q context를 만들려고 전역 TAG 등을 변경할 필요가 없다.

3. **다른 부모의 lambda/자식 차단:** `calibration_pin`과 `phase_identity`는 프로필/그 해시, 전체 study identity, 부모 core, route 해시를 결합한다. 닫힌 비용/학습 report도 같은 preparation/source/phase와 일치해야 한다. `do_train`은 업데이트 전에 자신의 교정 report·pin·부모·weight·phase 해시를 다시 확인한다. 자식은 자기 namespace의 학습 report/정확 CP SHA를 읽고, `child_header`에서 schema/tag/부모 descriptor/route/profile/전체 experiment를 확인하며 strict loader가 route를 다시 검증한다. F 교정값을 Q에, F 자식을 Q 평가에 재사용하는 것은 현재 정상 진입 경로에서 거부된다. 새 교정은 각 부모별로 해야 하며 F와 Q의 lambda가 수치상 같아도 핀을 공유하면 안 된다.

4. **평가 64행 불변:** namespace schema와 별개인 `EVAL_SELECTION_SCHEMA="P106B_ALM_REFERENCE_TRAIN_V1"`를 추가해 이전 `sha([SCHEMA,1337,"FIXED_DEV",semantic_root_id])`의 실제 문자열을 고정했다. 한영 각각32행의 선택/순서는 새 프로필명으로 바뀌지 않는다. 준비된 평가행·길이 admission은 해시로 묶이고 runtime/evaluate에서 재검산한다. 추가 시험은 뒤집은 합성 입력에서도 구 리터럴 선택과 같은지 검사한다. **실제 새 준비본끼리 같은64행 SHA인지는 아직 실물 준비 후 확인할 항목**이며 합성 시험이 그 확인을 대신하지 않는다.

5. **원 업데이트·원 STE 보존:** 원본 snapshot과 AST를 대조한 `policy`, `authority`, `frozen_record`, `records_for`, `ALMCore`, `calibrate`, `gradient_stats`, `last_block_parameters`, `optimizers`, `optimizer_receipt`, `evaluation_admission`, `child_payload`는 모두 내용이 같다. 학습은 기존 P101A의 batches 및 `one_update`를 그대로 호출하며 fixed1024/8×16/4epoch/32update, compile OFF, BF16 eager/TF32 OFF, 원 Adam+RMS Muon 소유권·학습률 정책을 유지한다. Q의 `_ternary_refresh`는 원 `TLinear.refresh_quant`를 호출하고 anneal1을 사용한다. STE 미분창을 새로운 양자화식이나 float identity backward로 대체한 코드는 없다. 추가 합성 시험은 hard forward/원 surrogate 창, checkpoint 재계산, 업데이트 후 refresh, strict reload를 구분해서 검사하도록 작성됐다. 이는 작은 CPU oracle 설계 확인이며 실제 전체 학생 STE 동작의 관측은 아니다.

6. **봉인·같은 초기화:** 준비본은 현75개 source map·1024행/한영512·닫힌 V7 64batch·원 토큰/마스크·원 부모 descriptor를 요구한다. 재실행은 같은 preparation/source와 입력/준비 shard/교정/비용/자식 CP 핀을 전후 검산한다. CP는 `xb`로 새 파일에만 쓰고 child load는 같은 열린 핸들의 SHA→CPU tensor load→inode/크기/mtime 검사를 보존한다. 각 phase는 같은1337 seed로 원 부모부터 새로 열며 교정은 core/RNG/grad를 변경하지 않았는지 확인한다. 두 비용 팔의 initial RNG/optimizer group가 같아야 하고 실제 train도 이 receipt와 비교한다. 원칙상 같은 부모의 CE/ALM 대비이며 cost2update의 가중치나 optimizer state를 본학습에 이어 쓰지 않는다.

### 31.3 남은 P2·후속 관측 경계

- **P2/실행 선택 실수:** CLI 기본은 여전히 float_v1이다. 새 Fv2/Qv1을 선택하지 않은 명령을 자동 추정해서 새 namespace로 보내지 않는다. 따라서 총괄 소유 launcher/CPU 준비 단계는 명시 `--study float_v2` 또는 `--study ternary_v1`, 결과의 tag/parent_name/route와 각 source map을 확인해야 한다. 이것은 새 controller 결함을 발견했다는 뜻이 아니라 구 API를 보존하면서 남는 운영 경계다. 본 검토는 launcher를 수정하거나 새 준비를 실행하지 않았다.
- **P2/합성 시험의 범위:** 새 runtime 시험은 Mini와 패치된 CUDA admission/부모 loader를 사용한다. 실제 F/Q 부모의 manifest/header, 토크나이저·EOT·64평가 SHA, GPU peak/time, Q STE의 전체망 유한 gradient 및 CP 재적재는 아직 관측되지 않았다. 같은 root 밖의 합성 StudyContext 시험도 공통 V7 cache의 별도 root 이전을 보장하는 시험이 아니다. 실제 저장소 root의 공통 teacher 입력을 그대로 쓰는 현재 경로와 분리해 해석한다.
- **P2/비교의 의미:** Q의 CE 대 ALM은 같은 Q 부모/원 삼진 경로에서의 신호 기여를 묻는다. F 대 Q의 차이는 다른 사전학습 부모·전방 양자화·STE·각 부모별 교정값이 함께 바뀌므로 순수 양자화 효과가 아니다. Fv2만 닫혀도 원 삼진 요청의 완료가 아니며, Qv1이 실행되더라도 binary KL+one-off TRAIN norm 교정일 뿐 논문 전체 GradMag/hidden/outcome recipe 재현은 아니다.

별도 새 P1 수정 제안은 없다. 좁은 정적 감사 상태는 **`SOURCE_ONLY_NO_NEW_P1_FOUND / F_AND_Q_PROFILE_PATHS_SEPARATED / REPORTED_CPU86_NOT_RERUN / ACTUAL_STUDENT_NOT_RUN`**다. 이 절 외 파일·teacher/cache/tinylm·공유 계획/원장·설치/Git/모델/API/GPU는 변경·실행하지 않았다.

## 32. Luna KO30377 중복 게시 이력과 KO24965 v3의 독립 문자 감사

### 32.1 결론·범위

**30377은 성공 게시 당시 보존된 입력, 중복 시도 당시 보존된 입력, 현재 scratch, 현재 게시본 네 파일이 모두 같은304B다. SHA/내용 변경은 확인되지 않았다. 다만 scratch의 mtime/ctime은 두 시도 사이에 바뀌었으므로 “scratch에 어떤 재기록도 없었다”라고 말하면 안 된다.** 성공 게시본의 현재 inode/크기/mtime/ctime은 첫 성공 영수증의 관측과 같다. 두 번째 시도는 exit8/미게시이며 새 성공1건으로 집계하면 안 된다.

**24965 v3는 원문 전체에 기존 `apply_positioned_edits`를 실제 적용한 결과가 원문에서 `통산 출루율(427개), ` 한 번만 삭제한 본문과 문자 그대로 일치한다. LF754개/755행도 보존된다.** v2의 추가 LF 삭제는 v3에서 해소됐지만, 현재 게시본은 여전히 v1과 동일하다. 이 검토에서 원본/v1/v2/v3·게시본·코드 수정과 게시 함수 실행은 모두0이다. 문자 계약의 통과와 게시·통합·학습 채택·의미 품질 통과는 다르다.

### 32.2 30377: 영수증·원천 봉인·현재 파일 대조

지명 경로는 [scratch30377](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/author_scratch/luna_ko_20261023/native_full_ko_000050_30377_v1.json), [현재 게시본](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/published/native_full_ko_000050/30377.json), [원천 packet50](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/packets/native_full_ko_000050.json)다. 게시 함수 source의 실제 계약은 영수증과 `input.raw.json`, 원천 packet의 SHA 주소 사본을 함께 보존하며 O_EXCL 생성이 실패하면 exit8로 끝내는 방식이다. 이 판독에서 게시 함수는 실행하지 않았다.

| 실제 영수증 | 첫 성공 | 중복 시도 |
|---|---|---|
| [260d1864e6f9453e99e2c2dcb0da84a5](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/publish_receipts/260d1864e6f9453e99e2c2dcb0da84a5/receipt.json) / [75cb43f89ae340c0bac178b6423636be](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/publish_receipts/75cb43f89ae340c0bac178b6423636be/receipt.json) | `PUBLISHED_COPY_ONLY_DRAFT`, exit0, published_by_this_attempt=true | `ALREADY_EXISTS_NOT_A_COMPLETION_PROOF`, exit8, published_by_this_attempt=false |
| 시작/종료 KST | 13:21:32.642755–13:21:32.672311 | 13:21:57.804631–13:21:57.823890 |
| receipt 파일 SHA | `FB7A37758A83532E47CED43BA1350A1297775685EB1DF059AA82057D16DABFBE` | `66B8ED41915AC2A68E7AA4339C8A8271274078544F5025E5DEE5DE25564D6A46` |
| input.raw.json / input_before / input_after | 모두304B, 아래 공통 SHA | 모두304B, 아래 공통 SHA |
| final_observation | 같은 게시 경로·304B·공통 SHA | 첫 성공과 같은 게시 inode/size/mtime/ctime·공통 SHA |
| 원천 proof | id/eos_segment_index30377, HOLD, 변경범위0, authored_variant_count0 | 같은 proof이며 source_before=source_after |
| 언어/정답성/학습 채택 | NOT_VERIFIED/NOT_VERIFIED/NOT_ADMITTED | 같은 제한 |

공통 입력/게시 SHA는 **`08EAFAF5808FDDC7F2D3631480F27B1CED8162DCFD7CF2C3F365BB2B66DBD4A6`**다. 두 `input.raw.json`을 포함한 네 파일의 **바이트 동등성**을 직접 검사했다. 내용은 id30377, decision HOLD, changes[]이며, reason에는 원문의 전투 날짜/사상자 서술 충돌 때문에 하나를 임의 확정하지 않겠다는 설명이 같다. 이를 역사적 사실의 외부 검증이나 원문 정정 완료로 해석하지 않는다.

두 영수증이 가리키는 원천 packet과 [SHA 주소 보존본](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/publish_receipts/source_packets/C5BC07BC4D70679BE5AB63226471DED5071E1D6D4B335C1B16D527D16B69AC9F.json)은 실제 바이트가 같다. 둘 다433,540B/SHA `C5BC07BC4D70679BE5AB63226471DED5071E1D6D4B335C1B16D527D16B69AC9F`다. 선택된30377 객체의 정렬 JSON SHA는 `700F8A76B39316C147AD74EDC3E25483289633200A94D071314183983C871491`, 본문 SHA는 `CF1FDB355F886554EFF9196E37C2E8C72954A91E5F4497B745458D7678713387`이며 영수증과 일치한다. HOLD+빈 changes이므로 복원 본문 SHA도 같은 값이다. 두 영수증의 code_before/code_after와 source_before/source_after도 각각 같다.

**시각 변경은 별도로 남긴다.** scratch는 같은 dev2096/inode356178/304B인데 첫 성공의 mtime/ctime은 `1792729289766461105ns`(KST13:21:29.766461), 두 번째 시도와 현재 값은 `1792729311612816527ns`(13:21:51.612817)다. 반면 게시본은 dev2096/inode356139/304B/mtime=ctime=`1792729292662696172ns`가 첫 성공·중복 영수증·현재 모두 같다. 따라서 **동일 내용의 재기록 또는 metadata 갱신과 합치하는 관측**이지 내용 변조의 증거는 아니다. 제공된 “중복 AddFile”의 실제 편집 도구 호출·행위자·일시적인 중간 바이트 상태까지 이 영수증으로 확정할 수는 없다. 또한 동일 시점 SHA/파일 stamp의 일치만으로 모든 역사적 중간 변경이 불가능했다고 증명하지 않는다.

별도 `imported/native_full_ko_000050*` 경로는 이번 지명 prefix 조회에서 없었다. 이 사실로 다른 namespace의 전역 import/원장까지 부재라고 확대하지 않는다. 여기서 독립 대조한 manifest 수준의 소유 증거는 **두 게시 영수증과 봉인된 원천 packet 객체/사본**이며, canonical/학습 cache 전수 검산·전체 게시 집계는 수행하지 않았다.

### 32.3 24965: v1/v2/v3와 현재 게시본의 문자·LF 계약

원천은 [packet41](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/packets/native_full_ko_000041.json)의 유일한 id/eos_segment_index24965다. packet은566,787B/SHA `773B716840A4D3BC4C5E581F5168294F01D7A85A091F75453C803AD2F438DB64`, 원문 본문은77,295 Unicode 문자/SHA `2D4FD75700DE0C9A0C11B31EB0C1AFA2D07BD5E6EA981DBBB31C4EEFB7F215C6`다. 본문 안 지명 문구는 한 번만 나타나며, CR0/LF754개/755행이고10행 끝에 LF가 있다.

기존 [helper](/home/uranus/tinyLM/scripts/p106b_text_batches.py)의 `lf_lines`/`apply_positioned_edits`와 [문자 SHA helper](/home/uranus/tinyLM/scripts/p106b_source_cleanup.py)의 `sha` 노드를 **내용 변경 없이 AST로 선별 호출**했다. 모듈 import·게시 함수·파일 쓰기는 실행하지 않았다. 두 source SHA는 각각 `4163FADA22DA728DBB015F7786C56EEECBD9DB39A33F57A4088E23AB5572AB42`/`3A0F6F1FD394E6F9A02DB6D1E67C50F3C4FBCB3A8136A61CCB061CE019EB7A84`다. 모든 버전의 지명 범위는10행/Unicode `[735,1304)`이며 원천 span SHA `FA50EC21876E94BF73B40F1DC2C748E26F4AB1EE77518FF452EC09D9D627364B`가 같다.

| 후보/게시본 | 후보 JSON 파일 SHA | 실제 helper 결과 |
|---|---|---|
| [v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/author_scratch/luna_ko_20261023/native_full_ko_000041_24965_v1.json),666B | `C34EE77F73E63D0C5FB1B9E5465618DF99BBFD14D3FA692BB9F9A720ACE40B29` | 10행569문자 전체 삭제, LF753개/754행. 지정 문구만 삭제한 결과가 아님 |
| [v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/author_scratch/luna_ko_20261023/native_full_ko_000041_24965_v2.json),1,790B | `C78E700F0EA33F71C91A58C0DE44CF8E3F70FEEDB411C4C9038432B06F610909` | 지정 문구14문자 외 원래 LF1개도 추가 삭제. LF753개/754행. §30의 실패 판정을 유지 |
| [v3](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/author_scratch/luna_ko_20261023/native_full_ko_000041_24965_v3.json),1,792B | `A804DBF051EC91F4A6A0467D42E32ED5486069CE873B83000E1222234AB6A4B4` | 지정 문구14문자만 삭제.77,281문자/LF754개/755행이며 원래 LF 보존. `replacement == original_line10.replace(needle,"",1)` 및 전체 결과 동등성 모두 참 |
| [현재 게시본](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/published/native_full_ko_000041/24965.json),666B | v1과 같은 `C34EE77F73E63D0C5FB1B9E5465618DF99BBFD14D3FA692BB9F9A720ACE40B29` | v1과 바이트 동일, v2/v3와 다름. v3로 교체되지 않음 |

v3의 replacement는 v2 replacement 뒤에 원래 `\n` 하나를 돌려놓은 것과 같다. v3 복원 전체 본문 SHA는 **`B82FE6FA1AC8CFA232EF6C1A237E1E2A1B5C0F17A5434BF11ED5C6B3B7AD71D2`**로, 지정 문구만 한 번 제거한 예상 본문 SHA와 같다. 참고로 v2는 `E39558ED11A6AD822797FAA22DA81D34C24C3B262325F19DE1F483A16BD03943`, v1은 `170EADC5325C2C2809D0A866149851304C30D815817D57C40716396AD07ED7AC`다. 완성 본문 전체가 예상값과 같으므로 선수·지도자/그 밖의 통산 기록을 포함한 **나머지 모든 문자의 보존**을 이 문자 계약 범위에서 확인했다. 이는77,295문자의 의미·사실성 전수 심사나 삭제된 표현이 야구 기록상 오류라는 새 외부 판정은 아니다.

### 32.4 정정 필요점·미확인·원형 보존

1. 30377은 **성공1건+보존된 중복 실패1건**으로 보고해야 한다. exit8을 성공 회수·두 번째 게시 완료·원 게시본 덮어쓰기라고 기록하면 정정이 필요하다. 동시에 scratch metadata 변경을 숨기고 “성공 이후 scratch 파일 상태가 완전히 불변”이라고 적어서도 안 된다. 현재 네 사본의 SHA/내용 동일성과 중간 행위 미확인을 함께 남긴다.
2. 24965의 “지명 절만 삭제+원 LF 보존”은 **미게시 v3의 문자 계약**에만 적용된다. 현재 게시 v1에 이 판정을 소급하지 않는다. v1 reason이 좁은 오기 제거를 주장하더라도 실제 action은 행 전체 REMOVE다. 기존 v1/v2의 부정 증거는 지우지 않으며, v3가 게시·통합·채택된 것으로 원장에 승격하면 정정이 필요하다. 새 버전 반입/게시/기존본 대체는 총괄·사용자 소유 결정이고 이번 감사는 그 행위를 승인·실행하지 않는다.
3. 두 지명 대상만 검토했으며 다른 Luna KO 전체, 비SFT64건,1.44M 전체, 전역 manifest/학습 cache·의미 정답성은 검토하지 않았다. 읽기 검산 시작/종료의 지명 파일 SHA·inode/size/mtime/ctime은 모두 같았다. 이 문서 외 원본/후보/게시본/영수증/helper/공유 계획·원장 수정0, 재게시0, 모델/API/GPU/설치/Git0이다.

상태: **`30377_SUCCESS_COPY_PRESERVED / DUPLICATE_EXIT8_NOT_NEW_COMPLETION / SCRATCH_CONTENT_SAME_METADATA_CHANGED / 24965_V3_EXACT_PHRASE_DELETE_AND_LF_PRESERVED / CURRENT_PUBLISHED_24965_IS_V1 / NO_PUBLICATION_OR_TRAIN_ADMISSION`**.

## 33. Q 가족의 실제 부모·CE·ALM 답216개의 독립 판독

### 33.1 닫힌 세 팔 확인 후에만 판독한 범위

**Q 부모/CE/ALM의 같은64 QA+사용자8개를 모두 읽었다. 단문 정답을 안정적으로 내고 멈추는 개선은 이번 실제 답에서 확인하지 못했다.** 다만 이는 의미 정답률0이라는 새 판정이 아니다. 원 annotation exact는 세 팔 모두0/64지만, 정답에 해당하는 내용이 문장에 나타난 사례와 질문/지시문만 반복하는 사례가 섞여 있다. ALM에만 필요한 정보가 더 나온 사례와 CE에 있던 정보를 ALM이 잃은 사례를 함께 아래에 보존한다. 특정 사례로 전체 우열·채택 문턱을 새로 만들지 않는다.

처음 조회에서는 ALM report가 없어 판독하지 않고 대기했다. 이후 세 report가 모두 `ALM_EVALUATION_COMPLETE`/returncode0, sources_unchanged/inputs_unchanged/parent_checkpoint_unchanged=true, answer_manifest.lineage.complete=true인 것을 확인한 뒤 세 원답 shard를 읽었다. 각 shard의 실제 바이트 수/SHA/72행 및 concat SHA를 manifest와 대조했다. **각72행의 순서·kind·실제 question 전체·원 source_row/annotation·길이 admission과 실제 generation의 prompt SHA/token 수가 세 팔에서 같았다.** 사용자8행은 index가0부터 다시 시작하므로 QA64행의 분모와 섞지 않았다.

| 팔·정본 | report SHA | 원답72행 SHA/크기 |
|---|---|---|
| [Q 부모 report](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_parent/report.json) / [원답](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_parent/answers_000000.jsonl) | `6A344507A3AC2DC398A53052325448D43387DDA6B4DD70A9559D286014EE4C92` | `38A6AE787C87F0990A949089C80E57836251B3887FDCEFF1DD25F41F37428EF0` /422,772B |
| [Q CE report](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_ce/report.json) / [원답](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_ce/answers_000000.jsonl) | `AEAB335DAFF99CEEBDA34805FF9AE66EA97B1A70574AD7EB74BB4FA23144BD34` | `D90082A37F04465FE90DE633310D1E604BC9B0CE5EFED326BC641A2137165AFC` /422,553B |
| [Q ALM report](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_alm/report.json) / [원답](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_alm/answers_000000.jsonl) | `4205F82430A7D50C47ABC90107A1BE96AB1C469467D06D8DC5295B28FF38CF18` | `56F147137205B6B7F922E63DE0FD4BDA5E6C140AEEB018DCCD4514FB95CA52D0` /422,671B |

공통 부모는 native595-q/원 삼진 TLINEAR 경로/FP32 master이며 부모 core SHA는 `C8F2A68232D95C8D4A8EDC455A5D389211806609C2F58E780C6EFF66E497F2DB`다. tokenizer SHA `9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E`, preparation SHA `1489D9A708FB221319EFAD33FAD96F94D63023B5F420B639581CDD40A299B31A`, 공통 평가행 SHA `17C780899DC9708B87F13BFE3B4AA3A72E60F98D2B87ABA4C267DAC6FD34D2AF`가 세 report에서 같다. CE와 ALM은 같은 부모의 별도 자식이다. 본 절은 실제 **원답** 비교이며 학습 노출·gradient·λ 보정의 새로운 재감사나 F 대 Q 비교가 아니다.

### 33.2 원 annotation exact와 의미·종료의 분리

기존 report의 `exact_original`/`strict_whitespace_exact`/`whitespace_normalized_exact`는 세 팔 모두 **각0/64**다. 같은 원답64개에서 문자열 전체 동등성 및 공백 정규화 동등성을 독립 재계산해 같은 결과를 확인했다. 사용자8개에는 원 annotation이 없고 기존 보고에서도 `USER_OBSERVATION_NOT_SCORED`이므로0/72 또는 새8문항 점수로 바꾸지 않았다. 부분 문자열 포함·질문 복사·정답 단어 주변의 틀린 주체/날짜를 자동 정답으로 세지 않았다.

모든 실제 generation metadata는 max_new64/temp0/top_k1/MTP OFF/FP32_MATH/TF32 OFF/use_cache=true/actual_history=false, EOS 사용 가능·stop_at_eos 요청/유효 true, stop_token_sequences[[4]]다. 모델별로 설정을 달리해 길이를 유리하게 준 것은 아니다. 부모는72답 중 MAX_NEW70/EOS2이며, CE·ALM은 각각72답 모두 MAX_NEW다. 이는 새 품질 점수가 아니라 **실제 종료 상태의 기술**이다. 부모 EOS2개는 QA index17(김연경 기사 외 수단)과21(생도의 교양과목)로, 각각 엉뚱한 스포츠/군사학 분류 문구이며 정답을 내고 잘 끝낸 사례가 아니다. EOS terminal_ids는[2]로 기록됐다. CE/ALM에서 이 두 문장이 더 길어졌다고 의미 정답 개선이라고 부를 수도 없다.

MAX_NEW는64토큰 예산까지 생성했다는 뜻이지 이후에도 절대 답하지 못한다는 증명이 아니다. 반대로 짧은 정답이 요구된 문항에서 이미 같은 구절을 반복한 실제 답을 “예산만 늘리면 해결”이라고 가정할 근거도 없다. 이번 감사는 예산/문항/평가조건을 수정하거나 추가 생성을 하지 않았다.

### 33.3 최소 대비 사례: 실제 질문·세 답·기대답·한계

아래 QA index는 원답 파일의0-based index다. 질문은 source_row.meta.question_original 그대로이며 **실제 모델 입력에는 동일한 래퍼와 원 문맥이 함께 있었다.** 발췌의 `…`는 검토문서의 생략 표시이고 원답의 일부가 아니다. 원답 전체는 위의 각 shard에서 index+1행에 보존되어 있다. LF는 필요한 곳에서 `\n`으로 가시화했다. 모든 사례가 MAX_NEW로 끝났다. 원 annotation은 원천 annotation일 뿐 외부 사실·현재 상태의 새 인증이 아니다.

| index·실제 질문 / 원 기대답 | 부모 원답 발췌 | CE 원답 발췌 | ALM 원답 발췌 | 독립 해석 |
|---|---|---|---|---|
| 2, `4세기에 활동한 법률가 이자 밀라노의 주교인 서방 교회의 4대 교부 중 한 사람은?` / `암브로시우스` | `각주` 뒤 `가톨릭 전례` 반복 | `암브로시우스(라틴어: Sanctus Ambrosius, 340년?~397년)는 로마 가톨릭교회의 주교이다.` 이후 반복 | `암브로시우스(라틴어: Sanctus Ambrosius, 340년?~397년 4월 4일) 또는 성 암브로스(Ambrose)는 4세기 후반부터 4세기 후반까지…` 이후 반복 | 두 자식 모두 부모보다 목표 인물을 회수했다. **ALM만의 개선이 아니며**, ALM의 이상한 기간 표현과 반복까지 포함한 완결 답의 품질은 별도 문제다. exact0을 의미 정보0으로 오인하면 안 됨 |
| 14, `<금강삼매경론>의 저자는?` / `원효` | `각주`/`불교 용어` 반복 | `<금강삼매경론>의 저자는?`만 반복 | `<금강삼매경론>의 저자는?\n원효는 자신의 저서 《금강삼매경론》의 저자는?` 반복 | ALM에 정답 이름이 새로 나타나지만 실제로는 **저자 답을 확정하는 대신 다시 질문**한다. 이름 포함만으로 성공 처리하지 않음 |
| 19, `헨리 구스타프의 뇌는 현재 어디에 위치해 있는가?` / `미국 샌디에이고` | `각주`/`뇌전증` 반복 | `1891년 출생\n2008년 사망\n미국의 뇌…` | `미국 샌디에이고의 뇌는 현재 뇌 기능과 기억 장애 환자 H.M.의 발달과…` 반복 | ALM에 장소는 회수됐으나 **인물의 뇌가 그곳에 있다는 관계를 명확히 답한 문장과 다르다.** 원문은 뇌의 위치를 그렇게 적고 있다. 부분 회수 관측만 남기며 전체 문장 의미 PASS 아님 |
| 28, `시애틀에서 부진을 겪은 추신수가 2006년 7월 27일 이적한 팀의 이름은?` / `클리블랜드 인디언스` | `프로 야구 선수로서…`와 다른 팀 경력 목록 | `2007년 7월 27일 클리블랜드 인디언스의 내야수 벤 브루사드…` 반복 | CE와 같은 답 | 두 자식의 목표 팀명 회수는 공통 개선 요소지만 **질문의2006년을2007년으로 바꿨다.** 세 답 중 단어만 검색해 자식 정답이라고 승격하지 않음 |
| 36, `What four topics are required in an Endangered Species Recovery Plan?` / `goals, tasks required, likely costs, and estimated timeline to recover endangered species` | `a comprehensive plan for the management of endangered species` 반복, 네 항목 없음 | `…goals, tasks required, likely costs, and estimated timeline to recover endangered species…` | CE와 같은 답 | 두 자식이 네 항목을 실제로 담았다. NMFS 중복·문장 절단은 남지만 **모든 의미가 틀렸다고 할 사례는 아니다.** ALM 고유 이득 또는 exact 기준을 몰래 바꿀 이유로 쓰지 않음 |
| 45, `How many people were buried under rubble in Mianyang City?` / `1,700` | `The school was destroyed by the earthquake.` 반복 | `Give a concise answer to the question using only the reference.` 반복 | `In Mianyang City, five schools collapsed, burying at least 1,700 people. At least 6,000 school children died due` | ALM이 목표 수1,700을 회수한 **국소 개선**이 있다. 그러나 원 문맥은 **seven schools**이고 이어지는6,000 사망도 이 문맥에 없다. 목표 숫자 포함과 **주변 정보 왜곡/미완결**을 분리한다 |
| 53, `What companies received the money?` / `China Unicom and China Mobile` | `The Chinese government had to pay the money…` 반복 | `The Chinese government received the money from China Unicom and China Mobile…` 반복 | `The Chinese government received the money for the earthquake…` 뒤 장소/헌혈 문구 | CE는 회사명이 있어도 **돈을 받은 주체/출처를 뒤집었다.** ALM은 그 회사명마저 잃었다. CE→ALM의 정보 손실과 CE 자체의 관계 오류를 함께 보존하며 “CE 정답→ALM 오답”이라는 이분법으로 단순화하지 않음 |
| 58, `From what language does Universitas come from?` / `Latin` | `The term "universitas" is used…` 반복, 언어 답 없음 | `The original Latin word "universitas" is used…` 뒤 질문 반복 | `Give a concise answer to the question using only the reference to the question using only the reference…` 반복 | 원 문맥 첫 문장은 실제로 Latin을 명시한다. CE에는 언어 정보가 있고 ALM은 지시문 루프로 바뀌어 이를 잃었다. **ALM의 국소 회귀**이며 CE의 질문 반복/잘못된 부연까지 정상 답으로 승인하는 것은 아님 |
| 61, `Modern Baptist churches trace their history to the English Separatist movement in the century after the rise of what?` / `original Protestant denominations` | `Modern Baptist churches trace their history to the English Separatist movement in the century after the rise of the original Protestant denominations.` 이후 같은 문장 반복 | 부모와 동일 | 부모와 동일 | 세 팔 모두 첫 문장에 필요한 관계를 정확히 담았고 같은 반복 답이다. **exact0≠의미0**, 그러나 이 사례는 학습/ALM의 개선 증거가 아니고 종료 문제도 그대로다 |

선택된 문맥도 직접 읽어 위 관계/숫자를 대조했다. 예를 들어45의 원문은 `In Mianyang City, seven schools collapsed, burying at least 1,700 people.`이고,53의 원문은 해당 회사가 설치한 계좌로 문자 기부가 이루어졌다고 적는다.58은 `The original Latin word "universitas"…`로 시작한다. 이 대조는 표본 문맥의 내부 충실성 검사이며 역사·법률·의학 등의 외부 사실 검증으로 확대하지 않는다.

### 33.4 사용자8개: 원 annotation이 없는 실제 질문 그대로의 판독

U0–U7은 각 원답 파일65–72행이다. 세 팔 모두 이8개에서 MAX_NEW이며 실제 원답 전체를 읽었다. 아래는 원답의 시작/반복 구간 발췌다. 기대는 질문 자체에서 사람이 읽은 요구이지 새 gold label이나 자동 채점 결과가 아니다.

| 실제 질문 / 질문이 요구하는 것 | 부모 | CE | ALM | 관측·한계 |
|---|---|---|---|---|
| U0 `1+1은?` / 결과2를 답함 | `2+2은?so\n2+3은?so\n2+4은?so…` | `2+1은?sosososo…` | CE와 동일 | 첫 글자가2라고 산술 답2가 완결됐다고 보지 않음. 세 팔 모두 식/문자 반복 |
| U1 `2+2는?` / 결과4를 답함 | `2+2는?so` 반복 | `3+2는?dy\n4+2는?dy\n5+2는?dy…` | `3+2+2는?so????????…` | 질문 재생산·다른 식 진행. ALM의 물음표 루프는 의미 개선 아님 |
| U2 `A는 사과고 B는 당근이다. B는?` / B=당근 | `A는?heim` 반복 | `A는?dy` 반복 | `A는 당근이다. B는?dy` 반복 | ALM은 당근을 생성하지만 **B가 아니라 A에 붙이고 질문을 되풀이**한다. 정답 단어 포함을 대상 관계의 정답으로 세면 오판 |
| U3 `문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 질문: 영희의 사과는 몇 개입니까? 답만 쓰세요.` / 영희5개 | `각주`/`대한민국의 요리사` 반복 | `문맥: 민수는 사과 3개, 영희는 사과 3개, 영희는 사과 3개…` | CE와 동일 | 두 자식은 질문 형식에 가까워졌지만 **영희5를3으로 변형**한다. 문맥 QA 학습 후 역할/수치 보존이 해결됐다는 증거 없음 |
| U4 `사과에 대해 알려줘` / 설명 | `사과` 반복 | `사속사속…` | `사과에 대해 알려줘◎\ndyed` 반복 | 단일 정답 문자열은 없는 열린 질문이다. 그럼에도 세 답에 설명이 없고, ALM은 요청 자체를 반복한다는 관측은 분명함 |
| U5 `농구란?` / 개념 설명 | `농구란?heim` 반복 | `농구란?dy` 반복 | CE와 동일 | 접미 조각 변경을 답변 개선이라고 할 수 없음 |
| U6 `What is 1+1?` / 결과2를 답함 | `2+2+2+3+3+4+5\n3+4+5+6…` | `2+2+2+3+3+4+5+6+6…` | CE와 동일 | 세 팔 모두 식이 이어진다. 시작 숫자2 포함은 안정적인 산술 답/종료가 아님 |
| U7 `Explain what an apple is.` / 정의·설명 | `Explain what an apple is.ever` 반복 | `Impact of apple on the apple` 반복 | `Impact of apple on the environment` 반복 | ALM은 반복 제목의 대상이 바뀌었을 뿐 사과가 무엇인지 설명하지 않음 |

### 33.5 허용되는 결론과 남은 경계

이 표본의 관측은 **문맥에서 이름/항목/숫자를 더 회수하는 국소 변화가 있어도 질문 대상·관계·날짜를 틀리거나 지시문을 반복하며 멈추지 않는 문제가 남는다**는 것이다. ALM의 국소 개선(45 등)만 골라 전체 향상으로 부를 수 없고, 회귀(58 등)만으로 모든 KD 효과가 항상 음수라고 일반화할 수도 없다. 학습 전 부모도 이미 심한 분류/각주/문장 반복을 보였으므로 새 반복 전체를 ALM 하나의 탓으로 돌릴 근거도 없다.

이것은 기존 내부 DEV64(한영32씩)+사용자8의 실제 답 감사다. 원 source_original_split은 train인 원천을 포함하며 프로젝트 내부 DEV 분리/원 annotation 문자 검산에 의존한다. fresh 공식 test, Core6/BabyLM 점수, 전체 일반 대화·산술·한국어 능력 평가가 아니다.64 QA의 문맥 전체 의미/원천 사실을 모두 전수 검증한 것도 아니다. **읽은 분모는 실제 질문72개×세 답=216답 전부이고, 문맥 정밀 대조·문서화한 최소 대비 사례는 위9개**다. 문항/조건/학습 자료·평가 기준을 점수에 맞춰 바꾸지 않았다. F는 이 절에서 읽거나 비교하지 않았으며 이후 별도 증거가 필요하다.

`log-to-result`의 JSON 정본 우선·같은 조건 검산·부정 사례 보존 원칙을 이 제한된 감사에 적용했다. 정식 결과문서/계획/원장 연쇄 갱신은 총괄 소유이므로 새 번호 문서/채택 문턱·공유 원장 변경은 하지 않았다. 원답/평가 자료를 학습·교사·Luna에 전달하지 않았고, 모델/코드/시험/설치/API/GPU/Git 실행0이다. 소유 문서만 갱신했다.

상태: **`Q_THREE_CLOSED_ARMS_AND_MANIFESTS_VERIFIED / SAME72_INPUTS_216_ACTUAL_ANSWERS_READ / EXISTING_EXACT0_OF64_EACH_CONFIRMED / LOCAL_GAINS_AND_REGRESSIONS_RETAINED / NO_NEW_SEMANTIC_SCORE_OR_ADOPTION_THRESHOLD / F_NOT_REVIEWED`**.

## 34. Fv2 실제 세 팔216답의 별도 감사: 공통 회수와 새 오류·종료를 분리

### 34.1 F 원답의 독립 회수·봉인 확인

**F 부모/CE/ALM의 원답216개를 Q 문서에서 전용하지 않고 새로 모두 읽었다.** 이번 F 표본에도 같은 이름/주제/질문 반복과 역할·수치 왜곡이 남아 있다. 한 문항에서 두 자식이 부모보다 맞는 관계를 회수했지만, 이를 ALM만의 이득이라고 분해할 수 없다. ALM에서 문구가 덜 이상해지거나 EOS로 끝난 사례도 목표 답을 회수한 것과 달랐다. 아래 대표5개는 국소 관측을 보존하기 위한 것이며 새 전체 의미 점수·채택 문턱이 아니다.

첫 조회에서 F ALM report가 없었으므로 비교를 대기했다. 이후 `p106b_alm_train_float_v2_s1337`의 세 evaluate report가 모두 `ALM_EVALUATION_COMPLETE`/returncode0·전후 source/input/parent 보존=true이고 answer_manifest.lineage.complete=true임을 확인하고 읽었다. 세 manifest 각각의 실제 shard 크기/행 수/SHA/concat SHA를 검산했다.64 QA+사용자8의 입력 순서·kind·실제 question 전체·source_row/원 annotation·길이 admission·실제 prompt SHA/token 수와 생성 설정이 **F 세 팔끼리** 같았다.

| F 정본 | 실제 report SHA | 실제 원답72행 SHA/크기 |
|---|---|---|
| [부모 report](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_float_v2_s1337/evaluate_parent/report.json) / [원답](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_float_v2_s1337/evaluate_parent/answers_000000.jsonl) | `E0629909F30C89132788C5150D8F23D5BBF999DADC970C8AE40B44A22839383A` | `E06F2C967F05949D3F7C1F1B07466157F5C9B9126AB7ED41E462578A676DA382` /422,457B |
| [CE report](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_float_v2_s1337/evaluate_ce/report.json) / [원답](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_float_v2_s1337/evaluate_ce/answers_000000.jsonl) | `9C090548CFD39F0B4A44B07A771545C8631B5346808B485093B07F3FCAB509F7` | `5CC88202D3705C50AD7A123B4035076332BCE9A439A2D63205FF35D168C35C7D` /423,316B |
| [ALM report](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_float_v2_s1337/evaluate_alm/report.json) / [원답](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_float_v2_s1337/evaluate_alm/answers_000000.jsonl) | `47807406258B1DD61135DB00DDBAFF29CB03E2E577B882137E7F07AE4194026B` | `69BFD53AF4AFBB9D5EA953771E03D247DC0F167B5A7C29687572FE49F88A9E21` /423,218B |

F의 실제 study_identity는 native595-f/float_v2, TLINEAR LATENT_IDENTITY_VIEW/IDENTITY backward, FP32 master/공유 embedding·head 정책이다. 부모 core SHA는 `E21E7023D5F289E2EBA2C65127491CB8016232A538E0619E63068BA095D4E3DD`, preparation SHA는 `3D041047B11DB664E93BD2A19BC88FFC79769EAE0AC8BA30B9AF0D824487D565`다. 같은 F 내 tokenizer SHA는 `9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E`, 평가행 SHA는 `17C780899DC9708B87F13BFE3B4AA3A72E60F98D2B87ABA4C267DAC6FD34D2AF`다. 두 자식의 평가 report가 가리키는 공통 F 교정값은13.131641128023277이며 교정 report SHA는 `1E627B2690A145E2C56A721B5F48EE1E06A79C310EF4A86D9B86311E327E4568`다. CE가 이 λ를 손실에 가산했다는 뜻은 아니다.

각 평가 report의 core_before/core_after는 같고, CE 평가 core는 `234041504FB1CAA57FEB9A0A664DDB8CEA6DE2B228758EB575AEDC9B7325D717`, ALM은 `A170E1B746FE9C4E3CE0A68BBC796368B38DB80454B62F09EA33710941824B5F`로 다르다. **여러 greedy 원답이 같다는 관측만으로 같은 체크포인트를 중복 평가했다거나 ALM 학습 신호가 전혀 없었다고 추론하지 않는다.** 이 값은 닫힌 report의 관측이며 반 담당자가 모델/체크포인트를 새로 적재해 산출한 것이 아니다.

### 34.2 문자열 지표와 실제 종료

F의 기존 exact_original/strict_whitespace_exact/whitespace_normalized_exact는 모두 **각0/64**다. F 원답64개를 원 annotation과 전체 문자열/공백 정규화로 다시 대조해 확인했다. 사용자8개는 여전히 원 gold 없는 미채점 관찰이며0/72로 분모를 바꾸지 않는다. 아래61의 실제 첫 문장은 의미 정보를 회수했으므로 exact0을 의미0이라고 부르면 잘못이다.

실제 generation 설정은 세 팔에서 모두 max_new64/temp0/top_k1/actual_history=false/MTP OFF/FP32_MATH/TF32 OFF/use_cache=true, EOS 사용 가능·stop_at_eos 요청/유효 true, stop_token_sequences[[4]]다. 종료 상태는 부모 MAX_NEW69/EOS3, CE MAX_NEW70/EOS2, ALM MAX_NEW69/EOS3이다. QA64만 보면 각각 MAX_NEW61/EOS3,62/EOS2,61/EOS3이며 **사용자8은 세 팔 모두 MAX_NEW**다.

부모의 EOS는 QA index0/13/22, CE는0/22, ALM은0/22/29다.0은 정릉 위치 대신 행정구역 분류 문구,22는 접착제 이름 대신 `접착제`/각주 목록이다. 부모13도 형사소송법/법 분류 문구다. 따라서 단순 EOS 개수로 답 품질 순위를 정할 수 없다. ALM에만 새로 EOS인29는 아래처럼 목표 답을 내지 않았다. EOS terminal_ids는[2]이고, MAX_NEW는 예산 소진이지 EOS 비활성의 증거가 아니다. 예산을 늘린 새 생성은 하지 않았다.

### 34.3 F 내부 대표5개: 개선·부연 오류·겉모양 변화

질문은 F source_row.meta.question_original이며 실제 입력은 같은 래퍼/문맥을 포함한다. index는 QA0-based/각 원답 shard의 index+1행이다. 세 원답을 모두 읽고 아래5개 문맥을 별도로 직접 대조했다. 표는 **발췌**이며 `…`는 검토문서의 생략이고 실제 원답의 문자가 아니다.

| index·실제 질문 / 원 기대답 | F 부모 원답 | F CE 원답 | F ALM 원답 | 범위를 한정한 해석 |
|---|---|---|---|---|
| 61, `Modern Baptist churches trace their history to the English Separatist movement in the century after the rise of what?` / `original Protestant denominations` | `…in the century after the rise of the Church of England.` | `…in the century after the rise of the original Protestant denominations.` | CE와 같은 답 | **두 자식의 공통 관계 회수 개선**이다. 원 문맥 첫 문장도 original Protestant denominations다. 이후 문장/질문 형식 반복과 MAX_NEW는 남았으므로 단문/종료 성공은 아니며 ALM 고유 효과라고 할 수 없음 |
| 2, `4세기에 활동한 법률가 이자 밀라노의 주교인 서방 교회의 4대 교부 중 한 사람은?` / `암브로시우스` | `암브로시우스(라틴어: Sanctus Ambrosius, 340년?~397년 4월 4일) 또는 성 암브로시우스…` 반복 | `…4세기 중반에 활동한 로마 가톨릭의 수도원장이다. 로마 가톨릭교회의 수도원장이자 수도원장이다.` | CE와 같은 답 | 부모부터 목표 이름을 회수했다. 두 자식은 문장처럼 이어지지만 원 문맥의 **법률가/밀라노 주교를 수도원장으로 바꾼 근거 없는 부연**이 생겼다. 이름 포함의 개선 사례로 세면 안 되며, 새 부연 오류를 보존하되 이름 정답 자체도 지우지 않음 |
| 28, `시애틀에서 부진을 겪은 추신수가 2006년 7월 27일 이적한 팀의 이름은?` / `클리블랜드 인디언스` | `2006년 시즌 종료 후, 시애틀 매리너스 산하 마이너 리그 팀에서 타자로 뛰었다.` 반복 | `…팀의 이름을 '마이너리그'로 바꾸고…` 반복 | `…팀의 이름을 알렸다. 마이너리그에서 좋은 성적을 거두며 팀의 이름을 알렸다.` 반복 | ALM은 CE의 이상한 팀 개명 주장 대신 더 자연스러운 문구로 바뀌었다. **그러나 세 답 모두 목적 팀명을 내지 않았다.** 어색한 표현 감소와 목표 QA 정답 개선은 다름 |
| 29, `1682년 후쿠야만 번은 어디에 편입되었는가?` / `막부직할령` | `이타쿠라 가문은 메이지 유신기까지 이어지고…` 반복/MAX_NEW | `이타쿠라 가문에서 이타쿠라 가문은 메이지 유신기까지 이어지고…` 반복/MAX_NEW | `1682년 3월 15일, 후쿠야마 번에서 이타쿠라 시게히로가 사망.` 뒤 각주/인물 분류, EOS | ALM은 content50+EOS1토큰으로 종료했다. 하지만 **원문에 없는 사망일을 만들고 기대 답은 놓쳤다.** 원문 자체에 후쿠시마/후쿠야마 지명 혼재가 있으므로 그 사실성도 별도 한계다. 종료 변화만 품질 개선으로 승인하지 않음 |
| 45, `How many people were buried under rubble in Mianyang City?` / `1,700` | `What is the difference between a school and a community?`라는 다른 질문 뒤 반복 | `The following is a list of the most important facts about the city of Mianyang City.` 뒤 도시 위치 반복 | `The first school in the province was the Mianyang City School. The school was closed in the year 2000.` 뒤 다른 질문 반복 | 세 답 모두 목표1,700을 회수하지 못했다. ALM의 **새 학교명/2000년 폐교 주장은 제공 문맥에 없다.** CE도 이미 무관한 답이므로 “CE 정답→ALM 오답”이라고 꾸미지 않지만, 더 구체적인 무근거 주장이 생긴 사실은 남김 |

이5개에서 확인되는 것은 공통 회수 개선1개, 이름은 유지하면서 틀린 부연이 추가된 사례, ALM에서 문구/종료만 달라진 사례, 다른 질문·새 주장을 만든 실패다. **F의 ALM만 명확히 목표 정답을 개선했다는 대비나, 올바른 CE 답을 ALM이 확실히 오답으로 바꿨다는 최소쌍은 이 대표 사례에서 확정하지 않았다.** 필요한 정보가 없는데도 개선/회귀 사례의 수를 맞추려고 그런 라벨을 만들지 않는다. 이 표의5는 판독·제시 분모이지 새로운 품질 지표가 아니다.

### 34.4 사용자8: 실제 내용·종료를 별도 기록

각 원답 파일65–72행의 실제 세 답을 모두 읽었다. **F CE와 F ALM은 이8개 각각에서 answer 문자열과 generated_ids가 전부 같았음도 독립 검산했다.** 아래에서 CE=ALM이라고 적는 것은 실제 동일 원답을 확인했기 때문이며 Q 결과를 대입한 것이 아니다. 모든 팔/사용자 질문이 MAX_NEW로 끝났다. 기대는 질문 자체의 요구를 읽은 설명이지 새 annotation·자동 채점표가 아니다.

| 실제 질문 / 요구 | F 부모 발췌 | F CE 발췌 | F ALM 발췌 | 관측 |
|---|---|---|---|---|
| U0 `1+1은?` / 결과2 | `1+1은?ᇰ\n≠≠≠…` | 부모와 동일 | CE와 동일 | 산술 결과 대신 질문·기호 반복. 끝의 대체문자도 원답 그대로이며 검토문서 인코딩 사고라고 바꾸지 않음 |
| U1 `2+2는?` / 결과4 | `2+2는?ᇰ` 반복 | 부모와 동일 | CE와 동일 | 질문 반복이며 결과4를 답한 것이 아님 |
| U2 `A는 사과고 B는 당근이다. B는?` / B=당근 | `A는 사과고 B는?ᇰ` 뒤 다른 문자·질문 반복 | `A는 사과고 B는?ᇰᇰᇰ…` | CE와 동일 | 객체 대응을 답하지 않음. 제어문자가 아닌 실제 Unicode 조각이 반복되는 관측 |
| U3 `문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 질문: 영희의 사과는 몇 개입니까? 답만 쓰세요.` / 영희5개 | `문맥: 민수는 사과 6개를 가지고 있습니다. 질문: 민수의 사과는 몇 개입니까? 답만 쓰세요.` 반복 | `문맥: 민수는 사과 6개, 영희는 사과 7개…` 뒤 다음 문맥7개/8개 | CE와 동일 | 부모는 질문 대상을 민수로 바꾸고, 두 자식은 영희를 언급하지만 **원3/5를6/7·7/8로 변형**한다. 문맥 복사 형태가 답5개보다 좋아졌다고 보지 않음 |
| U4 `사과에 대해 알려줘` / 설명 | `각주`/`외부 링크`/`대한민국의 음악 그룹` 등 반복 | `각주`/음악 그룹 분류 반복 | CE와 동일 | 열린 질문이라 하나의 정답 문구는 없지만 실제 사과 설명은 없음. F 자식의 설명 능력이 해결됐다는 근거 아님 |
| U5 `농구란?` / 개념 설명 | `각주`/`외부 링크`/`대한민국의 기업`/`브랜드` 반복 | 부모와 동일 | CE와 동일 | 주제에 대한 설명 대신 분류 문구 반복 |
| U6 `What is 1+1?` / 결과2 | `♦♦♦…` | `1+1:1` 반복 | CE와 동일 | 기호 반복이 산술형 문자열로 바뀌었지만 **1+1을1로 쓴다.** 출력이 더 읽힌다고 산술 개선 성공이라고 하지 않음 |
| U7 `Explain what an apple is.` / 정의·설명 | `Explain how to make a apple.` 반복 | 부모와 동일 | CE와 동일 | 정의 요청을 만드는 방법이라는 다른 요청으로 바꾸며 반복. 답변/종료 개선 아님 |

### 34.5 해석 한계·종결

F에서 읽은 것은 **동일72질문×3팔=216실제 답 전부**, 문맥까지 직접 대조해 대표로 기록한 것은5개다. 일부 자식의 원문 관계 회수(61)와 새 부연 오류(2), 근거 없는 숫자·사건(29/45), 역할/수량 변형(사용자U3), 반복/미종료를 함께 남겼다. 원 annotation exact0만으로 이 의미적 차이를 지울 수 없으며, 대표 사례를 사후 선택한 자동 정답 점수나 전체능력의 인과 효과로 일반화할 수도 없다.

F는 native595-f/identity 경로를 초기화로 쓰고 Q는 native595-q/원 삼진·STE 경로를 쓴다. tokenizer/고정 평가행이 같아도 **부모 가중치·전방 경로·backward·부모별 λ가 함께 다르므로 F/Q 차이는 quantization-only 효과가 아니다.** 이 절의 대비 단위는 F 부모/자식 및 F CE 대 ALM이다. 기존 내부 DEV64/사용자8은 fresh 공식 test나 Core6/BabyLM 점수가 아니고, 문맥 사실성/전체 의미 정답률·산술/대화 능력 전수 인증도 아니다. 입력·조건·답·학습 자료를 사후 점수에 맞춰 바꾸지 않았고 추가 실행을 제안/수행하지 않았다.

`log-to-result`의 같은 조건·JSON 정본·부정 사례 보존 원칙만 승인 범위에 적용했다. 공유 결과/계획/원장·기준표는 총괄 소유로 유지했으며 소유 문서 외 수정0이다. 이번 실제 평가를 실행한 주체는 총괄이며, 반 담당자의 모델/시험/코드/API/GPU/설치/Git 실행은0이다. 평가 질문/원답을 학습·교사·Luna로 전달하지 않았다.

상태: **`F_THREE_CLOSED_ARMS_VERIFIED / F_216_ACTUAL_ANSWERS_INDEPENDENTLY_READ / FIVE_CONTEXT_PAIRED_CASES_RETAINED / USER8_CE_ALM_IDENTICAL_AND_ALL_MAX_NEW / NO_NEW_SCORE_OR_ADOPTION_THRESHOLD / F_Q_NOT_QUANTIZATION_ONLY`**.

## 35. 옵트인 어휘 타일 per-target NLL: fused CE 미완의 최소 설계 반 검토

### 35.1 우선 결론·권한·기존 구현과의 차이

**별도 내부 streaming prototype의 최소 구현 방향은 타당하지만, scalar CE의 backward를 재사용하는 것만으로 ALM 호환·현재 BF16 경로 동등성·가속을 주장하면 안 된다.** 핵심 P1은 (a) 임의의 위치별 상류 gradient를 받는 VJP, (b) FP32 공유 embedding/projection의 입력+출력 총 gradient, (c) 실제 BF16 matmul/cast 경계 보존, (d)157개 전체 파라미터의 **한 번 optimizer update 후** 검산이다. 아래는 소스/기존 결과를 읽은 설계 권고이며 새 구현·실행·허용차 확정이 아니다.

현재 [p102a_contract.py](/home/uranus/tinyLM/tinylm/train/p102a_contract.py)의 `factorized_ce_loss_first`는 **위치 chunk마다 전체 어휘 logits를 재생성하는 FP32 scalar sum CE**다. backward는 chunk scalar CE gradient에 하나의 grad_output을 곱한다. 어휘 타일도 per-target 벡터도 아니며 autocast를 명시 OFF한다. 기존 작은 SGD 모델 gate는 전체 부모의 Muon/Adam157개 업데이트/BF16 검산을 대체하지 않는다.

[alm.target_nll](/home/uranus/tinyLM/tinylm/train/alm.py:19)은 이미 ignore=-100을 **head 전에 gather**하고, 위치 chunk64/원 `_head_logits`/checkpoint로 미분 가능한 `[B,T]` NLL을 돌려준다. [mtp_sft.components](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:117)도 유효 위치 gather와 위치 chunk/checkpoint를 갖췄다. 따라서 net-new는 gather가 아니라 **그 안의 어휘축 logits/LSE 저장·역전파 방식**이다. 원본이 이미 가진 이득을 새 fused 효과로 다시 계산하지 않는다.

| 소유 경로 | 이번 동작·권한 | 제외 |
|---|---|---|
| p102a_contract/alm/mtp_sft/transformer와 관련 진단 source | 읽기·해시·호출 계약 검토만 | 코드·설정·기본 경로 변경0/import0 |
| 지명 PAD JSON report | 닫힌 수치·원 실패·허용차 읽기만 | 원형 수정·재실행0 |
| 본 연구문서 §35 | 총괄 요청에 따른 새 절 추가 | 공유 계획/원장/기준표 변경0 |
| CCE/Liger·새 kernel·패키지 | 구현·설치 승인으로 해석하지 않음 | 설치/등록/다운로드/제품 채택0 |

영향도 스킬의 `.agents/project.json` 축으로 보면 코드의 수치/미분 계약·회귀·메모리 계측에 영향이 크고, 데이터 schema/교사 확률/토큰 마스크는 변경 대상이 아니다. GPU·부모/원자료 소유권·같은 초기화/recipe·증거 수준·문서 연쇄를 분리한다. 특히 `alm.py`/`mtp_sft.py`는 닫힌 F/Q 학생 source map에, mtp_sft는 V7 teacher CODE에도 들어간다. **기본 동작을 유지하더라도 이 파일 바이트를 고치면 과거 preparation/source 핀이 달라진다.** 후속 구현 권한이 생긴다면 별도 신규 원형/새 source map으로 격리하는 쪽이 낫다. 이번 검토는 그 파일들을 수정하지 않는다.

### 35.2 실질적인 세 경로와 권장 최소 범위

| 안 | 범위 | 장점·부담 | 현재 주장 한계 |
|---|---|---|---|
| A. 기존 위치 chunk를 그대로 기준선으로 보존 | 원 `_head_logits`+CE none+유효 위치 gather/checkpoint | 기존 ALM/마스크·수치 경로를 가장 직접 보존, 추가 구현 낮음 | 어휘 타일/fused 미완 자체는 줄이지 못함 |
| B. 별도 옵트인 streaming NLL 원형 | 첫 단계 FP32 factorized head/per-target first-order VJP, 후속에만 원 BF16 경계 시도 | 기존 gather와 별개인 실제 신규 부분을 고립. 구현/회귀 중간~높음, Python tile/GEMM 재계산 비용 큼 | 내부 원형일 뿐 CCE/Liger 구현·fused kernel·속도 개선이 아님 |
| C. 공식 CCE/Liger 도입을 별도 과제로 준비 | 정확 source/API/버전·설치 권한·factorized/tied/per-target 지원부터 조사 | 검증된 kernel의 활용 여지가 있으나 의존성/어댑터/라이선스·수치 검산 부담 높음 | 현재 설치/도입 승인 없음. 기존 승인6종 패키지를 확대 해석하지 않음 |

**권장: A를 oracle로 보존하면서 B를 독립 FP32 원형부터 제한적으로 설계.** 처음부터 BF16 학습의 대체품이나 속도 후보로 채택하지 않는다. B에서 kernel 수가 늘고 로그확률/gradient 재계산을 하므로 메모리 한 성분이 줄어도 wall이 늘 수 있다. C는 독립 승인·검증 대상이다. 현재 요청은 이 권고를 문서화하는 것까지다.

최소 지원은 ordinary FP32 master의 공유 factorized head, ignore=-100/이미 shifted targets, 단일 장치 eager·compile OFF·MTP OFF·dropout0·고정1024를 명시한다. packed/LUT/quantized embedding·새 QAT·padding crop·teacher 재점수·optimizer/clip/LR 변경은 함께 넣지 않는다. F/Q 모두에 일반화하려면 각 부모/경로에서 별도 검산해야 하며, F 통과를 Q STE 통과로 승계하지 않는다. 지원하지 않는 dtype/형상/두 번째 미분 등은 조용한 fallback 대신 명시 거부하거나 NOT_SUPPORTED로 남긴다.

### 35.3 P1: per-target VJP와 공유 가중치의 정확한 계약

유효 위치 hidden을 `H[N,D]`, 공유 projection을 `U[D,E]`, embedding을 `W[V,E]`라 놓으면 `P=H U`, `Z=P W^T`, `nll_i=logsumexp_v Z_iv−Z_i,y_i`다. 새 출력은 scalar CE가 아니라 유효 위치에 대응하는 **원 순서의 NLL 벡터**여야 한다. 임의 상류 `g_i=dL/dnll_i`에 대해 로그잇 VJP는 `G_iv=g_i(softmax(Z_i)_v−1[v=y_i])`이고, 출력 경로는 `dP=G W`, `dW_head=G^T P`, `dU_head=H^T dP`, `dH=dP U^T`다. 이는 실수 산술의 식이지 BF16 연산 순서의 동등성 증명은 아니다.

- **임의 g:** ALM의 binary KL은 행/byte chunk마다 다른 계수를 만들고 부호도 바뀔 수 있다. all-ones/scalar grad_output에 대한 CE 합만 맞추거나 forward에서 scalar용 gradient를 미리 계산해 두는 것은 충분하지 않다. signed/0/비균일 g, 한 위치만 활성인 g와 실제 `CE/N + λ KL/K`를 모두 oracle에 포함한다. g에 CE 분모를 두 번 적용하거나 KL의 K를 CE의 N으로 바꾸지 않는다.
- **공유 총 gradient:** transformer 입력은 `embedding(tokens,W)` 후 같은 U로 올리고, 출력은 같은 U를 내려서 같은 W로 logits를 낸다. custom Function의 입력으로 **원 graph에 연결된 H/U/W**를 전달하고 dH/dU_head/dW_head를 반환해야 입력 경로 gradient와 autograd가 합산한다. `.grad`를 직접 할당/덮어쓰거나 detached 복제 Parameter·별도 head optimizer를 만들면 안 된다. 동일 leaf가 optimizer에 두 번 들어가도 안 된다. 입력에서만 쓰인 token도 attention/공유 head 때문에 gradient가 있을 수 있으므로 “비감독 token embedding은 항상0”이라는 잘못된 검사를 만들지 않는다.
- **ignore/빈 micro:** 기존 위치·EOT CE/KD 마스크·shift를 그대로 쓴다. 유효 target은 `[0,V)`이고 -100 이외의 잘못된 음수/어휘 초과는 거부한다. 한 micro가 전부 ignore이면 head를 실행하지 않고 기존 zero graph/None-vs-zero gradient 의미를 보존한다. 전체 update N=0은 기존처럼 거부한다. None을 임의 zero tensor로 바꾸면 momentum/WD/optimizer state 생성이 달라질 수 있다.
- **전체 어휘:** 각 tile마다 softmax를 정규화하거나 label에 나온 클래스만 남기면 다른 손실이다. global LSE와 target logit은 **동일 forward 타일에서** 얻고, 각 유효 target이 정확히 한 tile에 속하는지 검사한다. target만 별도 dot/GEMV로 계산하면 BF16 반올림 경로가 바뀔 수 있다. V가 tile 크기의 배수가 아닌 끝 타일·첫/마지막/경계 ID도 포함한다.
- **수치 안정·메모리:** stable max/sumexp 또는 LSE 결합을 쓰되, 큰 공통 logit offset에서 `LSE−target_logit`의 소거 오차도 확인한다. `(global_max−target_logit)+log(sumexp_shifted)`처럼 큰 절대값끼리의 뺄셈을 피하는 표현을 oracle와 대조할 수 있다. backward의 확률도 저장된 정규화 통계/같은 dtype·tile 계약으로 재계산한다. clamp/renormalize로 ALM의 rounded student q=1 사건을 숨기지 않는다.
- **진짜 제한 메모리:** 순수 Python tile loop에 autograd graph를 모두 남기면 모든 tile 중간값이 살아 있어 저장이 줄지 않을 수 있다. forward 통계만 저장하고 backward를 tile별 재계산하는 수명 설계가 필요하다. full `[N,V]`는 피하더라도 W 자체와 `dW[V,E]`는 남는다. V32768/E256의 FP32 dW만32MiB이며 입력 embedding gradient와 임시 버퍼가 동시에 살아 있을 수 있다. 위치64×V32768의 FP32 logits8MiB를 줄인 것을 전체 모델 peak·상주 메모리8배 절감이라고 표현하지 않는다.

현 target_nll의 `hidden[...,0]*0`도 nonfinite hidden이면 NaN을 지우지 못한다. gather가 PAD/backbone의 비유한 문제를 고쳤다고 주장하거나 `nan_to_num`/clamp로 baseline 실패를 조용히 숨겨서는 안 된다. zero-g/전체 ignore/gradient 불필요 입력을 건너뛰는 최적화도 reference의 None 의미와 optimizer 갱신을 바꾸지 않는지 확인해야 한다.

### 35.4 P1: FP32 LSE와 BF16 matmul의 경계를 혼동하지 않기

FP32 master가 있다는 것은 head matmul까지 FP32라는 뜻이 아니다. 현재 `_head_logits`는 두 `F.linear`를 호출하고 ALM은 **그 결과를 `.float()`한 뒤** cross_entropy none을 계산한다. BF16 autocast에서는 projected activation·logits 및 그 역방향 cast/GEMM이 AMP 규약을 따른다. 따라서 기존 p102a loss-first처럼 autocast를 끄고 hidden/U/W를 FP32로 계산하면 **더 높은 정밀도의 별도 head 경로**이지 현재 BF16 경로의 동일 구현이라고 할 수 없다.

첫 단계 FP32-only 원형은 이 한계를 이름/receipt에 명시하면 유효하다. 후속 BF16 시도에서는 forward의 projected/logits dtype, backward의 `g*(p−onehot)`가 원 logits dtype으로 cast되는 시점, dP·dU·dW의 matmul과 tile 합산 순서, FP32 leaf로 돌아오는 cast를 따로 확인해야 한다. **g를 곱한 뒤 반올림하는 것과 반올림된 scalar CE gradient에 g를 나중에 곱하는 것은 일반적으로 다르다.** FP32 probability로 dP를 전부 FP32에 합산한 뒤 한 번 BF16으로 내리는 방식도 기존 전체 어휘 BF16 GEMM과 같다고 가정할 수 없다.

custom backward가 호출될 때 바깥 autocast는 이미 꺼져 있을 수 있다. forward의 AMP 상태/dtype을 저장·복원하거나 그 상태와 동등한 명시 계산을 해야 한다. 단순히 현재 `is_autocast_enabled()`만 보고 backward dtype을 정하면 틀릴 수 있다. PyTorch는 custom autograd의 autocast 계약과 forward에 선택된 dtype의 backward를 별도로 설명하며, tensor slice/GEMM 분할이 수학적으로 같아도 bitwise 동일성은 보장하지 않는다. 이는 **오차를 무조건 허용하라는 근거가 아니라 실물 오차를 측정하고 다른 경로로 표기해야 한다는 근거**다. [PyTorch AMP custom functions](https://docs.pytorch.org/docs/2.14/notes/amp_examples.html#autocast-and-custom-autograd-functions), [PyTorch numerical accuracy](https://docs.pytorch.org/docs/2.14/notes/numerical_accuracy.html#batched-computations-or-slice-computations)

### 35.5 기존 PAD 실패가 주는 실제 중단 기준

참고할 실패는 예전 느슨한 무업데이트 probe와 구별해야 한다. [PAD workspace_v2 correctness](/home/uranus/tinyLM/test_result/evidence/p101a_padding_gpu_v1_s1337_workspace_v2/correctness/report.json), SHA `11D45F4A75A7ACB728761642FBD12A1DB1E335C7CC89D53AA8F650F34FF2B918`는 `NUMERICAL_DIAGNOSTIC_NEGATIVE`/returncode9다.

| 기존 실제 관측 | 결과 |
|---|---|
| 같은 첫128행·N2350, FP32 MATH/TF32 OFF, fresh 부모/RNG·각1update | scalar loss 차 `3.8958610559802764e-08`, 허용차 이내 |
| 전체157 gradient tensor | 모두 close, 최대 절대차 `2.1457672119140625e-06` |
| optimizer state301 tensor | 모두 close |
| 업데이트 후157 파라미터 | **85 tensor/11,181원소가 허용차 초과**, 최대 절대차 `2.1696090698242188e-05` |
| 공유 emb.weight/emb_up.weight | gradient 모두 close였지만 **emb_up의 업데이트는45원소/최대차 `1.8402934074401855e-05`로 실패** |

단순 max_abs와 atol만 비교하지 않고 원소별 `abs(candidate−reference) <= atol + rtol*abs(reference)`를 쓴 결과다. 같은 gradient/상태의 작은 허용 오차가 실제 optimizer 한 번 뒤 파라미터 동등성을 보증하지 않았다. 이 감사는 어느 optimizer 내부 연산이 차이를 증폭했는지 새로 분해하지 않았다. **손실 일치→gradient 일치→업데이트 일치라는 추론은 금지**하고 각각 실제로 확인해야 한다.

[같은 namespace의 BF16 timing](/home/uranus/tinyLM/test_result/evidence/p101a_padding_gpu_v1_s1337_workspace_v2/timing/report.json), SHA `F7CFE9D88F4C0E76D461EF33495CF03DAA3337C6BDC199F6093B6649185BC2FE`는 `TIMING_ABBA_COMPLETE`/0이나 자체에도 numerical equivalence/adoption과 분리한다고 적었다. 반면 이전 v1 두 report의 실패는 **앞 GPU tensor 미해제로 다음 팔을 못 연 실행/수명 오류**였다. 이를 v2의 수치 실패와 합치거나, 오래된 `p106b_padding_probe`의 무업데이트 FP32 근접/속도 관측으로 이번 실패를 덮으면 안 된다.

### 35.6 사전 oracle·허용차·STOP 제안: 지금 승인/실행한 기준은 아님

최소 검산의 순서는 (1) 작은 순수 head/vector-VJP, (2) 실제 공유 입력 경로를 포함한 합성 tied 모델+비선형 KL, (3) **별도 승인 후에만** 같은 실제 부모/고정1024/8×16/동일 row 순서의157개 gradient·실제 optimizer1update, (4) 수치 선결을 통과한 동일 경로의 비용 관측이다. 앞 단계의 tiny/FP32 PASS는 뒤 단계/BF16/속도를 승인하지 않는다. 이 요청에서 어느 단계도 실행하지 않았다.

| 항목 | 사전 권고·출처 | STOP/해석 |
|---|---|---|
| 구조·target·mask·V·위치·분모·alias/None·RNG·초기화 | 정확 일치. valid gather/scatter 순서·EOT CE/KD·단일 shift·전체V·CE N/KL K를 고정 | 하나라도 다르면 수치/속도 비교 전에 중단 |
| FP32 per-target NLL/비균일 g VJP/비선형 CE+KL | 기존 ALM tied-head oracle의 `atol=2e-6, rtol=1e-5`를 신규 벡터에도 적용하는 안을 **사전에** 제안. 순수 scalar P102A의 더 작은 예제 규칙을 벡터 증거로 대체하지 않음 | 모든 위치/반환 dH,dU,dW 및 전체망 비교. 평균 loss만 맞추거나 g=1만 시험하면 불충분 |
| 전체157 gradient/한 번 update 후157 파라미터/optimizer state | 기존 PAD의 `atol=2e-6,rtol=1e-5`와 원소별 판정식을 그대로 시작 기준으로 제안. loss/preclip norm은 기존 PAD `1e-5,1e-4`. 각 팔 fresh 빈 optimizer/None .grad·동일 clipping/그룹/LR·same seed | **한 tensor/원소라도 실패하면 해당 동등성 FAIL/HOLD**, 이후 실제 학습 채택0. CP0·재초기화 없이 두 팔을 연속 update하면 무효 |
| BF16 실제 경로 | dtype/cast/AMP·GEMM 계약부터 고정하고 별도 관측. 위 FP32 규칙 통과를 BF16 PASS로 자동 승계하지 않음 | 미보정 BF16 허용차를 결과에 맞춰 크게 만들지 않음. 엄격 동등성이 실패하면 **별도 수치 경로**로 보존하며 production/현재 recipe 대체0 |
| 경계·실패 주입 | V/tile 비배수·y0/V−1/경계 ID·비연속 H·반복 ID·mixed ignore·전부 ignore·빈 micro·unequal CE/KD 분모·큰 공통 logit offset·signed/zero g·teacher q=1/student rounded q=1 | 잘못된 label/nonfinite/누락/변경 source·입력/중간 model 수명 실패를 별도 사유로 보존. sentinel/clamp/쉬운 표본 대체 금지 |
| 비용/메모리 | 기존row chunk64/같은 dtype·전체 recipe·target 수·행 순서·checkpoint를 맞춘 독립 관측. forward/backward 재계산/head/clip/optimizer·whole wall·peak를 분리 | Python tile 수 증가/속도 회귀/OOM/기한 초과는 음성 또는 PARTIAL. head만 빠르거나 buffer만 작아진 것을 전체 학습 speedup/VRAM 채택으로 확대하지 않음 |

허용차는 이 검토가 새 정책을 확정한 것이 아니라 **기존 source의 좁은 규칙을 출발점으로 제안한 것**이다. 사용자/총괄이 새 수치 경로의 별도 판정 범위를 사전에 정해야 한다. 조건별 품질 σ를 소유하는 `_rulers.py`는 Muon/KD의 이 head 변경에 대한 수치 gradient 허용차를 제공하지 않으므로 오래된 품질 σ로 업데이트 차이를 면제하지 않는다. source/부모/optimizer/입력의 원형을 먼저 고정하고, 결과가 불리하다고 허용차·tile·정밀도·대상 token을 사후 선택하지 않는다.

### 35.7 이번 감사의 실제 수행·제한

읽은 주요 source SHA는 p102a_contract `1EC66273DFB3B043C9A8AE79B34BCC9381A52AE79B767788A8A7A1EFFF2521ED`, alm `59466D0810237477E4AB06BB2545138887508D168AAAC257D5096E925A7EBAFA`, mtp_sft `EF508EC83AA16FE37674516A77A3E5B43D69545C05E52E8C6AC34765255BC657`, transformer `BB8D88D8C1BA3475777AA65126AEB6A25C0259CC66D9A3BB5FF3CB3B3A37DA1A`다. 구현 중복·기존 테스트·PAD 실제 JSON·기준표의 관련 표준/레지스트리/비교 규칙과 `_rulers.py`, 공식 PyTorch 문서만 대조했다. registry/검사기/torch·프로젝트 import/모델·GPU·교사·테스트 실행·설치·Git은0이며 원자료/평가 원답을 새 학습/교사에게 전달하지 않았다. 전체 실행 preflight/태그 등록·새 계획서·공유 정본 갱신은 총괄 소유로 남겼다.

상태: **`DESIGN_REVIEW_ONLY / VECTOR_VJP_TIED_TOTAL_GRAD_AND_BF16_ROUNDING_ARE_SEPARATE_GATES / PAD_UPDATE_NEGATIVE_PRESERVED / NO_KERNEL_INSTALL_OR_SPEED_CLAIM / NO_IMPLEMENTATION_OR_MODEL_RUN`**.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 36. KO051 혼입 음성 보존과 지명 게시6표본의 원천·관계 대조

### 36.1 결론과 실제 판독 분모

**35018 v1의 잘못된27행은 같은 packet의 다른 인물35000(민영환)의27행과 경계 문구가 정확히 일치했다.**35018(민승호) 자기27행은 양모 항목이다. 즉 단순 철자/offset 착오가 아니라 **서로 다른 인물 문서가 섞인 후보**라는 근거를 독립 확인했다. 실패는 exit9/미게시로 보존해야 하며, 이후 HOLD가 게시됐다는 사실로 실패한 REWRITE를 성공으로 바꾸면 안 된다.

총괄이 지명한 현재 게시 REWRITE **34378/34472/34756/34966/35000/35048의6개·24수정 범위**를 같은 packet/ID별 raw와 대조했다. **이6개 수정에서35018과 같은 다른 문서 혼입은 추가로 발견하지 못했다.** 그러나34378의 계획→구현 서술 강화,34966/35000의 실제 LF 삭제·인접 항목 결합은 별개 문제다. 따라서 “6표본 정상/전량 품질 PASS”라는 요약은 부적절하다. 이6개는 무작위 추출이 아니라 지명 표본이고, 현재 packet128문서 전체 또는 원1.44M 전체를 검수한 것이 아니다. 모두 NOT_ADMITTED를 유지한다.

원문 전체 stdout 출력 없이, 지명 수정 구간·필요한 인접 항목·직업/가족/경력 관계만 읽었다. 허용한 stdlib JSON/문자열 범위 재구성·작은 SHA 검산만 했으며 프로젝트 검사기/게시 helper는 실행하지 않았다. 원문·게시본·실패 후보·코드·공유 원장 수정0이다.

### 36.2 packet/raw/게시 JSON의 실제 identity

[packet051](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/packets/native_full_ko_000051.json)은1,640,388B/128문서/SHA **`B5E8250A4DA30D0926FBFD3FAD0927F9B5F619328AD4023A71CD9B28458DAAA1`**다. 지명6개와35018의 ID는 각각 정확히1번 나타나고 eos_segment_index와 같다.6개 raw는 `packets/native_full_ko_000051_raw/{ID}.txt`이며 각각 packet의 자기 본문 UTF-8 바이트와 같다. 아래 source SHA는 이 raw/본문의 공통 값이다.

| 현재 게시본 | source/raw SHA | 게시 JSON SHA |
|---|---|---|
| [34378](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/published/native_full_ko_000051/34378.json) | `17C81DAAA808D579D5E12A40F086FB638ACD58E5319B8E287AF21B7AD530A20E` | `2265FC5025CDB309DE85DD5B81FA6E811102509C48605B256C8CF8ACD3CEBB88` |
| [34472](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/published/native_full_ko_000051/34472.json) | `E174F648AF64D74F74ABDCE1BD14324B26369D2471EF5BF2BBD9EC4925274B71` | `DD1B3BC02ACE739934205E91FD2DE8B2D5AEC5BE6FDB93307571AC4FF7A557C4` |
| [34756](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/published/native_full_ko_000051/34756.json) | `ADA6527C535D25D7B5E7F6CFC1598333356704218E0722325D302B6A45C8D911` | `6984AA2180743EF7CFEAE8A0E629202097AD3A2EE876CA24A495F44E7310841D` |
| [34966](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/published/native_full_ko_000051/34966.json) | `3CACEABB3D4C1B6AF06DF061549D79FA1742242FEBC423C31F2A50475C38A2D9` | `BD7B226AB9E9AC14B1DF5AE3AB501E937DB68FE8924DC6968245A753F2A68D07` |
| [35000](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/published/native_full_ko_000051/35000.json) | `1B7341771F2EA3A1402D3219A16A00CE3992B99233D8F6C6313134334A787999` | `4EAC135BF2085A0FF819140375EA274F554B87A2FDC67889C02EBD61C76EF159` |
| [35048](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/published/native_full_ko_000051/35048.json) | `41E8374254CD44EDBF2B85F9FF764F48CBAC7846626B5C3ED1E216CF5EA7C1DE` | `F9861BADEA753D7DD1548EF816B5F347CC6471A267BCEE4D12CE62AE71A6D046` |

6개 게시 JSON은 strict JSON으로 읽혔고 각 id/decision=REWRITE가 지명과 같았다.24범위의 LF행 좌표/원 시작·끝 문구가 자기 원문에 맞고 겹치지 않음을 확인했다. 재구성은 선언한 범위만 바꾸고 범위 밖 문자를 그대로 두는 읽기 전용 문자열 연산이다. 이것은 문구/관계 판독의 위치 근거이지 프로젝트 게시 검사기를 새로 통과시켰다는 보고나6개의 과거 성공 영수증 전수 감사가 아니다.

### 36.3 35018 원 실패: 혼입 출처까지 확인한 범위

[미게시35018 v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/author_scratch/luna_ko_20261023/native_full_ko_000051_35018_v1.json)은3,659B/SHA `D73C6B5A6D6BAB6D56F3F86144903C491A22F5ED90FAA97A9C51B212F873CDB8`다. [실패 영수증9e60108ce91242e18037abf38cafbc30](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/publish_receipts/9e60108ce91242e18037abf38cafbc30/receipt.json), SHA `8AB64FFE90B3DB9A34BA224326BCFDBF724E903D7428B3799CEBD61E81B6D105`는 INCOMPLETE/exit9/published_by_this_attempt=false이고 source_before/성공 final proof가 없다. 입력 전후 SHA는 현재 실패 후보와 같고 packet 전후도 같았다.

실제35018 source와 [raw35018](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/packets/native_full_ko_000051_raw/35018.txt)은 SHA **`C4320D000DAA78243111BF2701E5844E7E1CC264172ED672265B35C7AF357914`**로 같다. **77개의 LF 기준 행/실제 LF 구분자76개**이며 metadata.line_count도77이다. 총괄의 “77LF” 표현은 행 수와 구분자 수를 나누어 적는 편이 정확하다. 자기27행은 `양모 : 감고당…한산 이씨…`다. 실패 후보가27행에 선언한 `1904년, 한성부 감옥에 수감 중인 이승만…`부터 `…50주기 추념사…`까지의 경계는35018에는 없고, 이번에 함께 허용된 **35000 원문27행**에 정확히 맞았다.35000의 주어는 민영환,35018의 주어는 민승호다.

후보의 세 번째 수정91행도35018의77행 범위를 벗어난다. 따라서27행만 임의 이동하거나 fuzzy 경계로 구제할 사안이 아니다. reason이 “이승만 소개장/추념사/혈죽 보존”이라고 말하는 것도35018 자기 source의 근거가 될 수 없다. 정확 경계 검사가 이 오귀속 후보의 게시를 막았다는 음성을 유지한다. **이후 changes=[] HOLD v2의 exit0 게시·담당자 오판 인정은 총괄 전달 사실**이며, 이번 허용 목록 밖의 v2/새 성공 영수증을 추가 조회해 검산한 것으로 표기하지 않는다. HOLD는 오류 정정·정답성 PASS나 문제없음 인증도 아니다.

### 36.4 지명6표본의 실제 수정·귀속 판독

아래 “혼입 미발견”은 **읽은 수정/인접 문맥에서 추가 다른 문서의 주체·사건을 발견하지 못했다**는 뜻이다. 실제 세계의 사실성·최신성·역사적 정당성까지 인증하는 말이 아니다.

| ID/원 범위 | source→현재 수정 대조 | 귀속·관계 판단과 남는 문제 |
|---|---|---|
| 34378 락박스,1/3/107행 | DAP/GPL/Archos/2001년 후반, PDA·애플리케이션·게임/비디오/음성 안내는 자기 source에 있다.107행 빈 각주 제목 제거 | 다른 OS/인물 문서 혼입은 못 찾았다. 다만3행 `…기능을 추가할 수 있도록 심사숙고 하였다`→`…추가할 수 있도록 했다`는 **검토/구상에서 구현·지원 완료로 서술을 강화**한다. 어색한 원문을 자연스럽게 만들었다는 이유만으로 동등한 사실 강도라고 할 수 없다.1/3행 terminal LF도 빠졌지만 바로 다음이 빈 행이라 다른 텍스트가 즉시 붙지는 않음 |
| 34472 프라하 성,1/3/13/45/47행 | 체코/프라하/블타바강·왕/황제/대통령 관저, 기네스북의 최상급/약570×130미터/연약180만명, 오타카르2세의 요새화·궁전 건축이 자기 source와 대응 | 인물/시대/건축물 혼입이나 새 수치 대입은 못 찾았다. 현재 대통령 관저라는 표현은 **원문의 현재 서술 보존**이지2026년 현행 실사 아님.3개 replacement의 LF가 빠져 문단 간 빈 줄은 줄지만 다음 빈 행은 남음. 사진/각주 제목 REMOVE와 내용 추가를 구분 |
| 34756 김민성,1행 | 1969-09-19/대한민국 성우/문화방송 성우극회/1997년 MBC14기 관계를 그대로 연결 | 다른 성우의 생일/기수 혼입 증거를 못 찾았다. 작품/배역 목록은 수정 범위 밖 문자 그대로이므로 **새 사실을 보충한 것으로 보지 않음**.1행 LF는 빠져 다음 빈 줄 하나를 소모함. 원 경력의 외부 정확성은 미검증 |
| 34966 마사리크,1/31/60/96/98행 | 호도닌1850-03-07/라니1937-10-14, 초대 대통령·직업·얀 후스·400여년 서술, Jan Hus 저작의 Praha1896/1908, 샬럿과1923년 사별은 자기 source에 있다 | 다른 대통령 문맥의 추가 혼입은 못 찾았다. **60행의 LF가 빠져 원61행1937년 사망 항목과 같은 행으로 붙는다.** 원저작/사별 관계는 보존됐지만 “띄어쓰기만 교정”으로 설명하기에는 실제 행 경계가 달라졌다. 딸의 불완전 연도 등 범위 밖 정보는 추측 교체되지 않음 |
| 35000 민영환,66/91행 | 원66행의 민원식=7촌조카, 민영철=민영환의6촌형제/민원식의 부친·3남, 김규식 보좌역=민원식, 송병준=민영환 식객을 문장으로 분리 | **이 정보는35000 자기 문서에 실제 있으며35018에 옮겨 써도 되는 정보는 아니다.** 현재 replacement 자체는 명시 관계를 뒤집지 않았다. 하지만 LF 삭제로 다음67행 명성황후의13촌/고종형수 항목이 같은 행에 이어진다. 이 결합은 새 다른 인물의 친족관계로 오독될 잠재 위험이며, 실제 관계가 바뀌었다고 전수 확정한 것은 아님 |
| 35048 페케르만,1/9–19/21–22/24–26/28–56행 | 원10개 감독·디렉터 경력의 팀/연도/유소년·성인 구분,2006년 페케르만 아래 선수였던 스칼로니/메시와2022년 스칼로니 감독 관계, FIFA/다른 외부 링크 제목·출전 분류가 자기 source에 대응 | 다른 감독/선수 문서에서 새 경력을 가져온 증거를 못 찾았다. **페케르만이2022년 우승 감독이었다고 주어를 바꾸지는 않았다.** 목록→산문은 단순 오타보다 큰 변환이며 `살아있는 사람` 분류/현직 표현까지 문자 그대로 전부 보존된 것은 아니다.2021년부터 베네수엘라 감독이라는 source의 열린 시기 서술을 최신2026 경력으로 인증하지 않음. 수정 문단 끝 LF는 유지됨 |

35048의 감독 목록에서는 CD 레가네스2003을 **Director of Football/풋볼 디렉터**로 남겼고 전부 감독 경력으로 합치지 않았다. 차카리타1982, 아르헨티노스1982–1992, 콜로-콜로1992–1994의 유소년 구분과 아르헨티나 유소년1994–2001, 성인대표2004–2006, 톨루카2007–2008, UANL2009, 콜롬비아2012–2018, 베네수엘라2021–의 대응을 확인했다. 분류를 문장화한 해외 선수/감독·팀·출전의 귀속도 해당 자기 목록에서 읽힌다. 이는 source의 외부 사실성 검증이나 실제 링크 URL의 보존·접속 가능성 검증이 아니다.

34378에서 확정한 것은 `심사숙고 하였다`를 `했다`로 바꾼 문자 차이다. 원문이 어색하므로 검토/의도보다 구현 완료로 강하게 읽힐 위험을 남긴 것이며, 실제 락박스 기능이 구현되지 않았었다는 외부 사실을 새로 판정한 것은 아니다. 이 문제를 다른 문서 혼입이 확인된35018과 같은 종류의 확정 실패로 합치지 않는다.

### 36.5 확정 LF 경계 변화와 재구성 해시

반 담당자의 범위 재구성에서 원 LF 수→수정 후 LF 수는34378 **118→115**,34472 **53→48**,34756 **78→77**,34966 **119→114**,35000 **111→109**,35048 **55→14**다. 마지막 큰 감소는 명시한 다행 목록의 산문 변환에 주로 따른 것이므로 그것 자체를 자동 오류로 판정하지 않는다. REMOVE로 지명 제목을 없앤 것과 MOVE_TO_PROSE replacement에서 행 끝 LF를 누락한 것도 구분한다.

특히 직접 결합된 결과는34966의 `1923년 – 부인 샬럿과 사별 1937년 – 라니(Lány)에서 사망` 및35000의 `…송병준은 민영환의 식객이었다. 13촌 아주머니 겸 고종형수 : 명성황후 민씨`다. **행 경계 삭제는 확정**이고, 이로 인한 downstream 의미/학습 영향은 미측정이다. 새 승인·새 버전이 생긴다면 원래 LF를 보존하는 좁은 교정 검토를 제안할 수 있으나 현재 게시본을 덮어쓰거나 재게시하지 않는다.

재구성 본문 SHA는34378 `FEF249083725DEF96495CD08204EB5ECC3EEF10B558BD53A27DB75DD623326FC`,34472 `70585B1412EBD930084EC85161B07215C8FD9667898C6CB9513B7F78AAA9A9E6`,34756 `0C259A60D6D33F5F07453E8851D6640609F0A8C1EF944D1FDBA503EBD146B2AD`,34966 `707A83EB704043D5FDF4CF04D44CF73BA04A10128541388A077A0056C2B1F7B8`,35000 `39DC03F1B3CD3CCA20C0285DEF2750E88F0A87B06CA9A02769B66D592FE92D71`,35048 `8CFB77907E9CF3B21AB50AF890221A4405B28406B96CF313087D00D38352F285`다. **메모리 안의 읽기 전용 비교 결과**이며 새 후보/학습 corpus/게시물로 저장하지 않았다.

### 36.6 정정 필요점·미확인·원형 보존

35018의 source 혼입을 “내용상 옳을 수도 있으니 경계만 맞추면 됨”이라고 구제하지 않는다. 반대로 그 실패를 근거로 나머지 지명6개도 모두 혼입됐다고 단정하지 않는다. 이번6개에는 추가 교차 문서 혼입을 찾지 못했으나, **34378의 서술 강화와34966/35000의 항목 결합**을 숨기고6개 일괄 PASS로 쓰면 정정이 필요하다. 구조 검사/게시 exit0는 원 사실·귀속·언어 품질·학습 효용의 PASS가 아니다.

6개의 나머지 원문 의미를 처음부터 끝까지 전수 심사한 것은 아니며, source/raw 바이트 일치와24개의 실제 수정 구간 및 필요한 인접 문맥·목록/관계를 확인했다. 허용되지 않은35018 v2/다른 실패 후보·별도 source·다른 receipts·전체 raw/보호 데이터·teacher cache에는 접근하지 않았다. **모든 대상은 NOT_ADMITTED 유지**, 원형/게시본·코드 수정/게시/검사기/GPU/모델/API/설치/Git 실행0이다. 총괄 소유 계획/원장 대신 본 절만 추가했다.

상태: **`35018_V1_CROSS_DOCUMENT_SOURCE35000_CONFIRMED_AND_EXIT9_PRESERVED / SIX_NAMED_REWRITES_24_RANGES_REVIEWED / NO_ADDITIONAL_CROSS_DOCUMENT_MIX_FOUND_IN_THOSE_RANGES / 34378_STRENGTHENING_AND_LF_JOINS_RETAINED / NOT_FULL_QUALITY_PASS / ALL_NOT_ADMITTED`**.

## 37. Supported production8h v3의 닫힌 첫217후보: 등간격16개 실제 입력·질문·교사 답 판독

### 37.1 결론: 입력 가시성은 확인했지만 의미 적합·정답성 완료는 아님

2026-10-23 15시대, 총괄이 지정한 **닫힌 batch_000000의217후보 중 내용 확인 전에 고정한 등간격16개**를 읽었다. 각 표본의 질문·학생에게 실제 주어지는 참고자료 전체·교사 최종 답을 함께 판독했다. **16개 모두 원래 source의 user/assistant 본문이 학생의 현재 user 메시지 안에 빠짐없이 인용되어 있었다.** 그러나 이것은 원문의 사실성·질문의 완결성·답의 의미 적합이나 학습 효용을 보증하지 않는다.

가장 분명한 근거 범위 문제는 **후보101행/원천10806의 공용어 질문**이다. 본문에 도시 이름은 있지만 각 도시의 공용어와 유럽 소재 여부를 설명한 문장은 없다. 따라서 답 `로마입니다.`가 일반 상식으로 그럴듯한가와 별개로, **필요한 판단 전제가 모두 보이는 본문에 있다는 주장은 성립하지 않는다.** 후보130행의 이름 없는 `이 회사`,145행의 실물이 없는 `이러한 통계들`도 지시 대상/증거 범위를 약하게 만든다. 다만130행의 장소와145행의 결론 문장은 각각 본문에서 회수할 수 있으므로, 이 둘을101행과 같은 확정 근거 부재나 정답 오류로 합치지 않는다.

수치·고유명·주체를 교사가 보이는 원문과 반대로 새로 바꾼 확정 사례는 **이번16개에서 발견하지 못했다.** 이는16개 정답성 PASS가 아니다. 원문의 숫자·전문용어·관계 서술이 이미 손상되었거나 서로 어긋나는 경우가 있고, 교사가 그 원문을 잘 따라 답하는 것만으로는 이를 고칠 수 없다. 아래에서는 **문자 차이/근거 부재가 확인된 사실**과 **원어·외부 사실 대조가 필요한 의심**을 구분한다. 새 자동 정답 점수·문자열 불량목록·온라인 수락 게이트는 만들지 않았다.

본 절은 §36의 KO051 게시6개/24수정 범위 감사와 **다른 자료·다른 목적**이다. KO051 표본 수나 혼입 음성의 판정을 이217후보에 합산하지 않는다.

### 37.2 닫힌 원천과 실제 상태·manifest 검산

대상은 [batch_000000 report](/home/uranus/tinyLM/HF/sft_ready/p106b_supported_production8h_v3_s1337/batch_000000/report.json), [candidate manifest](/home/uranus/tinyLM/HF/sft_ready/p106b_supported_production8h_v3_s1337/batch_000000/candidates_shards_manifest.json), [raw manifest](/home/uranus/tinyLM/HF/sft_ready/p106b_supported_production8h_v3_s1337/batch_000000/raw_shards_manifest.json)와 두 manifest가 명시한 **그 batch의 두 shard만**이다. 열린 batch_000001는 열기·열거·검색·해시하지 않았다.

| 닫힌 파일 | 실제 크기/행수 | SHA256 |
|---|---|---|
| report.json | 보고서 | `3B536E5FF935054C4E3ACBF541C2584EFEEA70F114FCB0C10767510E84C3026C` |
| candidates_shards_manifest.json | manifest | `0F71A60A34F894CAEB0C6AF32C152891556EB8327EA7A6C1D90E5C9A04059984` |
| candidates_000000.jsonl | 905,590B/217행 | `94628A36FD24DFE358D749669BA1E23E72680C7E45836E0765CF55D24B66E98E` |
| raw_shards_manifest.json | manifest | `F22B3C67F7C690C8C25BFBEE4D526E60CBD38419A910AAD7C6853E21FF7543EF` |
| raw_000000.jsonl | 3,581,052B/223행 | `43DE089B66B992F22A49FDDD8291B45587A8333EB19D35B6D5211A0DFEC23D04` |

**두 manifest 모두** report 안의 각각 `candidate_manifest`/`raw_manifest`와 내용이 같고, shard의 실제 바이트·행 수·SHA 및 연결 SHA가 선언과 일치했다. 각 shard는20,000,000B 제한보다 작다. raw223행과 candidate217행의 차이를 단순히 “6개 의미 오답”으로 세지 않는다. 이번에는 표본의 대응 raw만 판독했으며 모든 시도/재시도 원인을 분류하지 않았다.

보고서의 실제 상태는 **`PRODUCTION_PAUSED`, returncode=8, `ProductionBudgetPause`**, 사유는 `explicit stop file while source filtering; incremental batch retained`다. 닫힌 증거가 남았다는 뜻이지 생산 목표 완료/전체 파이프라인 성공이라는 뜻이 아니다. `accepted_groups=217`, `scanned_source_rows=218`이고 `formal_train_ready=false`, `token_target_ready=false`, `semantic_quality=NOT_REVIEWED`, `semantic_truth=PSEUDO_UNVERIFIED`, `student_training=NOT_RUN`을 그대로 유지한다. report의 `rows` 필드에 있는 큰 수치를 이 batch의 후보 행 수로 대체하지 않았다.

report 입력 계약은 `visible_source_contract=GEMMA_SUPPORTED_SOURCE_8H_V3`, `student_support=complete quoted original public messages, no truncation`, task 계약은 `GEMMA_GROUNDED_TASK_LITERAL_V3`다. MTP ON/draft-mtp n_max2, context8192/max_output3072/thinking1024 및 temperature1/top_p0.95/top_k64는 **기록된 생성 조건**이지 이번에 재실행하거나 검증한 성능 조건이 아니다. `teacher_profiles=[PUBLIC_BASE_ONLY, ON_NEW_VISIBLE_SOURCE]`, `ancestor_candidate_rows_admitted=0`도 report 관측으로만 남긴다. 학생이 인용문을 토크나이즈해 최종 학습 context에서 끝까지 보게 되는지와 학생 학습 자체는 이번 미실행 범위다.

### 37.3 내용 확인 전에 동결한 표본 선택과 재현 위치

선택식은 candidate shard의0-based 행 순서에 대해 **`floor(i*(217-1)/15), i=0..15`**다. 첫/마지막을 포함한16개이며, 출력 전 내용에 따라 표본을 바꾸지 않았다.0-based 인덱스는 `0,14,28,43,57,72,86,100,115,129,144,158,172,187,201,216`; 사람이 읽는1-based 행은 **`1,15,29,44,58,73,87,101,116,130,145,159,173,188,202,217`**이다. 아래 source ID는 모두 `train-00000-of-00002.parquet:` 뒤의 행 suffix이며, raw 대응은 candidate의 `teacher_reasoning_refs.raw_row_1based`로 찾아 서로 다른 재시도 offset을 보존했다.

| 후보1-based 행 | source ID suffix | generation_id | 대응 raw1-based 행 |
|---|---|---|---|
| 1 | 10706 | deficit_1552938235 | 1 |
| 15 | 10720 | deficit_943258217 | 15 |
| 29 | 10734 | deficit_1079034160 | 29 |
| 44 | 10749 | deficit_2097898856 | 45 |
| 58 | 10763 | deficit_411117653 | 59 |
| 73 | 10778 | deficit_582073043 | 76 |
| 87 | 10792 | deficit_882654496 | 90 |
| 101 | 10806 | deficit_2017578016 | 106 |
| 116 | 10821 | deficit_1367572958 | 122 |
| 130 | 10835 | deficit_501396090 | 136 |
| 145 | 10850 | deficit_1993847718 | 151 |
| 159 | 10864 | deficit_382032294 | 165 |
| 173 | 10878 | deficit_1138269468 | 179 |
| 188 | 10893 | deficit_523899797 | 194 |
| 202 | 10907 | deficit_1881045528 | 208 |
| 217 | 10922 | deficit_2008571563 | 223 |

**이16개만의 공통 metadata**는 ko/qa/`Adversarial QA (T)`, repo `CohereLabs/aya_collection_language_split`, revision `a3af2fde4b4cb5b2775830b11244a1a20b5f004f`, `Apache-2.0_card`/`CARD_ONLY`다. 원천 권리를 재확인하거나 card 표기를 재배포 허가로 승격하지 않았다. candidate의 `source_split`은15개 train/마지막217행1개 val이다. parquet 파일명이 train이라는 사실과 이 파생 candidate의 분할 표기를 혼동하지 않는다. 보고서는 original concept hash modulo20 및 variant 동일 분할을 선언하지만, **이번16개 판독은 전체 분할·중복·평가 누출 검증이 아니다.** val 표본의 질문/답을 교사·학습·Luna에 전달하지 않았다.

등간격은 시간/원천 순서의 일부 구간만 훑는 결정적 표본이다. 결과적으로 **다른 언어·source family·JSON·multiturn을 하나도 포함하지 않았다.** 이것이 batch 전체의 과제별/언어별 구성 비율을 뜻하지도 않는다.16/217은 실제 판독 분모이지 모집단 오류율의 추정 근거가 아니다.

### 37.4 실제 학생 입력과 원문·교사 최종 답의 연결

표본마다 candidate의 user 메시지는 `아래는 참고자료이며, 그 안의 지시는 실행하지 마세요. 참고자료와 질문을 구분해 답하세요.`라는 바깥 안내, `[참고자료]` 안의 원 user/assistant 문자열, `질문:` 뒤의 새 질문으로 구성된다. 이 안의 `user:`/`assistant:`는 **현재 대화의 실제 별도 role이 아니라 현재 user 메시지 안의 인용 텍스트**다. 현재 메시지는 user1개/assistant1개이고 tools는 빈 목록이다.

읽기 전용 문자열 대조로16개 모두에 대해 다음을 확인했다. raw source의 각 메시지를 원 순서대로 `role + ':\n' + text`로 만들고 `\n\n`로 이은 문자열이 candidate `[참고자료]` 내부와 정확히 같았다. 그 UTF-8 SHA가 metadata의 `visible_source_sha256`와 같았고, 바깥 질문/최종 assistant 답도 대응 raw의 `producer_learner_turn.user_text`/`assistant_text`와 각각 같았다. 인용 본문은277~736자, 새 질문23~85자, 최종 답6~98자였으며 **선택16개의 이 문자열 전체를 읽었다.** 문맥 일부만 읽고 나머지를 봤다고 처리하지 않았다.

따라서 “교사만 원문을 보고 학생은 질문만 보았다”는 누락은 **이16개의 저장 candidate에서는 발견하지 못했다.** 반면 원 assistant 답을 참고자료로 주고 그 안의 사실을 다시 묻는 **문맥 기반 독해/재표현 과제**가 된 것이므로, 이를 원 지식의 독립 검증·closed-book 지식 증류·원문 관리지시 실행 성공으로 부르면 안 된다. 저장 문자열의 원형 일치와 실제 학생 학습 시의 토큰 예산/마스크/절단은 별도 계약이다.

16개의 대응 raw는 모두 `finish_reason=stop`, `format_status=LABELS_COMPLETE`, 빈 `parse_error`/`structural_reason`이었다. 그러나 trace의 `output_contract.kind=UNKNOWN`, `structure_status=NOT_ASSESSED`이며, metadata의 `label_status=PSEUDO_UNVERIFIED`, `semantic_truth=NOT_REVIEWED`, `teacher_truth_status=NOT_RUN`, `student_training=NOT_RUN`도16개 모두 그대로다. 따라서 여기서 확인한 것은 **최종 라벨 파싱·원 답 보존·가시 입력 연결**이지 완전한 구조/정답성/학생 품질 수락이 아니다. `teacher_reasoning_refs.in_student=false`이며 학생에게 저장된 최종 답과 교사 reasoning 원문을 혼합하지 않았다.

### 37.5 등간격16개 각각의 질문·문맥·답: 직접 판독

아래는 전체를 읽은 뒤의 **발췌/요약**이다. 짧은 인용은 해당 candidate/raw의 실제 문구이며, 장문의 원문 전체를 새 학습 산출물로 복제하지 않는다. “회수 가능”은 보이는 문맥에 답을 뒷받침하는 표현이 있다는 뜻이지 외부 사실성 인증이 아니다.

| 후보행/source suffix | 실제 새 질문의 대상과 학생 문맥 | 교사 최종 답의 핵심 | 독립 판독 |
|---|---|---|---|
| 1/10706 | “기원전60년에서30년 사이…Bibliotheca historica…작성한 인물”을 묻는다. 인용 assistant 첫 문장에 디오도루스 시킬루스/같은 연대/저작명이 함께 있다 | “디오도루스 시킬루스입니다.”를 포함한 한 문장 | 인물·연대 연결을 본문에서 회수할 수 있다. 인용 user의 “문맥을 적으십시오”를 새 질문으로 복사한 것은 아니다. 원문 다른 인물 연대의 `<unk>` 손상까지 정정되었다는 뜻은 아님 |
| 15/10720 | “북서부 소말리랜드…몇 개의 정부 운영 라디오 방송국”인가. 본문은 북동부의 약6개 민간 방송국과 북서부의 정부 방송국 하나를 구분한다 | “정부 운영 라디오 방송국이 하나 있습니다.” | 지역/소유형태/숫자 구분을 보존했다.6을 정부 방송국 수로 혼동하지 않았다. 현재2026 실제 방송국 현황을 조사한 답은 아님 |
| 29/10734 | 모리셔스 기술 대학 주요 캠퍼스 위치. 본문은 “포인트 오크스 세블(Pointe aux Sables)의 라 투어 코엔지”라고 쓴다 | 같은 두 지명/포함관계를 답함 | 장소는 직접 회수 가능. 원 인용 user는 “라 투르 로니그”라고 써 원문 안의 음역이 서로 다르다. 교사가 새 지명을 발명한 것으로 단정하지 않고 원어 대조 필요를 남김 |
| 44/10749 | 위기 국가의 개혁을 막을 것이라는 견해가 무엇과 관련되는가. 인용 assistant가 추가 재정 지원/높은 적자·채무 허용과의 조건을 설명한다 | “훨씬 더 많은 재정 지원…더 높은 예산 적자 또는 채무 수준을 허용하는 것” | 본문 조건의 재표현으로 읽힌다. 인용 user의 무관한 “싫어하는 것의 반대”를 따르지 않음. 경제정책 견해를 실제 인과의 입증으로 바꾸어 해석하지 않음 |
| 58/10763 | 200~500년 바빌로니아 유대인 인구가 약 몇 명으로 늘었는가. 본문 해당 절은 약200만 명 | “약200만 명으로 증가했습니다.” | 질문 대상 연대/수치는 본문과 같다. 다만 같은 인용 후반에는 “인구가4명에서8억10만명으로 두 배 이상 증가”라는 크게 손상된 수치 표현이 남는다. 답이 이 후반 수치를 쓰지 않았다고 문맥 전체가 깨끗해지는 것은 아님 |
| 73/10778 | 사하라 북부 건조함을 강화하는 것. 본문은 알제리·모로코·튀니지의 아틀라스 산맥/비 그림자 장벽을 설명 | 아틀라스 산맥이 “비 그림자 효과”로 건조함 강화 | 산맥/세 국가/효과 관계를 본문에서 회수 가능. 원문의 “상층층 침몰” 같은 어색한 번역까지 과학적으로 검증된 것은 아님 |
| 87/10792 | 빛에서 자라는 식물의 주요 피토크롬. 본문에 phyB/주요 피토크롬이 이어짐 | “주요 피토크롬은 phyB입니다.” | 답의 직접 단서는 있다. 그러나 같은 문맥이 cry 계열을 “암호크롬/암호화 염색/암호염색체”, 시계를 “생계 시계”라고 부르고 phyA 분해/Cry1 생성도 연결한다. 전문용어·관계의 원어 검수가 필요하며 phyB 단답만으로 문맥 적합을 승인하지 않음 |
| 101/10806 | “언급된 유럽 도시 중 영어가 공용어가 아닌 도시”를 묻는다. 본문에는 런던/베이징/시카고/더블린/예루살렘/로마 등의 센터명만 있음 | **“로마입니다.”** | **도시 목록은 보이나 공용어/유럽 분류 전제가 없다.** 원 user의 실질 질문을 거의 유지했지만 관리지시 꼬리를 새 질문에 복사한 것은 아니다. 답의 외부 사실성은 별도이며 순수 본문 근거만의 과제로는 전제 누락이 확인됨 |
| 116/10821 | 1947년에 설립된 USAF가 무엇인지. 본문 첫머리에 United States Air Force/미국 공군과1947년 독립 서술 | “USAF는 미국 공군(United States Air Force)입니다.” | 명칭의 회수는 가능. 문맥은 동시에 현재형 “미국 육군의 공중전 서비스 지부”와 “초기에는…육군의 일부였으나…별도의 분파”를 쓴다. 현재/초기 소속의 번역·시제 관계가 정리되지 않은 source이며, 단답의 명칭 일치를 조직 관계 정확성까지 확대하지 않음 |
| 130/10835 | “이 회사는 인도 남부의 어느 지역에 최초의 공장”을 세웠는가. 본문은 이름 없이 이 회사/코로만델 해안/마치리파트넘을 말함 | 코로만델 해안의 마치리파트넘 마을 | 위치는 회수되지만 **어느 회사인지는 새 질문·보이는 본문 어디에도 명시되지 않는다.** 한 문단의 유일 회사라는 국소 참조는 가능하므로 장소 답을 즉시 오답으로 만들지는 않음. 원문의 `<unk>갈 만`/“정서”도 원어 검수 전 임의 보정하지 않음 |
| 145/10850 | “이러한 통계들”이 건강·영양 지식 부족의 복잡성/사회 구조에 대해 무엇을 보이는가. 본문은 통계의 수치·표·표본 없이 결론을 서술함 | 지식 부족이 사회 구조에 내재되고 다른 문제와 상호 연관됨 | 결론 문장을 재표현할 수는 있다. 그러나 **통계 자체는 학생에게 제공되지 않았으므로 통계 근거를 이해·분석한 성공으로 채점하면 과장**이다. 지시어의 원 선행 대상을 확인해야 함 |
| 159/10864 | 바르비에 반응과 마그네슘 그리그나드 반응 대비 장점. 본문은 아연 대응/물에서도 반응한다는 절을 포함 | 아연과 동등한 반응/물 존재하에서도 가능 | 두 핵심 절을 본문에서 회수 가능. 주변에는 “오르가노진/유기 아진”, “덜 핵애성” 등 전문용어와 여러 반응식·조건이 섞여 있다. 이 수용 여부는 유기화학 원어/조건 대조가 필요하며 물에서의 가능성을 모든 반응물/조건에 보편화하면 안 됨 |
| 173/10878 | 양자화 정수가8비트일 때 간격 수. 본문은8비트256/16비트65,536을 구분함 | **“256개의 간격”** | 질문 비트폭과 답 수치를 맞춰 회수했다.16비트 수를 대입하지 않았다. 본문의 `<unk>` 손상은 다음16비트 절에 남지만 질문에 필요한8비트 절은 보임 |
| 188/10893 | 문장에 묘사된 supporters/motto. 본문 마지막에 “바다 사자(어류 꼬리를 가진 사자)”와 DEO DUCENTE NIL NOCET가 있음 | “두 마리의 바다 사자…DEO DUCENTE NIL NOCET” | 개수/표어는 본문과 같다. 다만 문장의 표장은 신화적 어류 꼬리 사자라는 괄호 설명이 답에서 생략돼 보통 동물로 읽힐 여지가 있다. 질문과 문맥을 함께 보면 회수 가능하며, 생략을 곧바로 새 사실 오류로 단정하지 않음. 문장학 문맥의 다른 색/분할 표현은 심하게 깨져 있음 |
| 202/10907 | “항공 산업에서 파트너십을 구축한다”는 의미. 본문은 항공사/국제 항공사/정부·군부·NGO/언어·지역·문화 능숙함을 함께 서술함 | 항공사들이 국제 항공사 등과 상호 이익·안전을 위한 관계 개발·지도·유지 | 교사 답은 보이는 첫 문장을 따른다. 그러나 상업 항공사 설명과 군부/정부 협력 어휘가 섞인 문맥이어서 **원어의 행위자가 실제 항공사인지 별도 검수 필요**. “항공사”를 다른 주체로 임의 고치거나 현재 답의 오류를 원어 미확인 상태에서 확정하지 않음 |
| 217/10922 | 아시타가 누구를 방문해 시드다르타 미래를 예언했는가. 본문은 “어린 왕자의 아버지인 수드도난” | 어린 가우타마의 아버지인 수드도난 | 방문자/방문 대상/부자 관계를 본문대로 회수했다. 원 인용 user의 불교 창시자 첫 이름 질문을 새 질문으로 복사하지 않음. 이 행은 candidate val이며 학습으로 옮기지 않음 |

### 37.6 관리지시 복사·명확한 오류·의심을 구분하는 예시

**관리지시의 존재와 실제 새 질문의 오염은 다르다.**16개 원 user에는 “앞의 질문을 생각해 보면…그 대답을 담은 문맥을 적으십시오.1~20개의 문장…”에 해당하는 문맥 작성 지시가 들어 있고, 원형 인용 계약 때문에 그 문자열은 학생 입력의 `[참고자료]` 안에 그대로 보인다. 하지만 이번 새 질문16개는 모두 본문 사실/설명에 대한 별도 질문이며 이 문맥 작성 명령 자체를 수행하라고 요구하지 않는다. 따라서 인용 안의 관리지시가 존재한다는 사실만으로16개 전부를 instruction-copy 불량으로 세지 않는다. 반대로 인용 경계/바깥 주의문이 있다는 이유만으로 실제 학생이 이를 항상 따를 것이라고 보장하지도 않는다. 학생 모델의 실제 응답은 미관측이다.

**문맥에 있는 답을 회수한 것과 좋은 source를 제공한 것은 다르다.**58행의 약200만 명/173행의256은 같은 문맥에서 바로 확인되므로 새 답의 숫자 교체 사례가 아니다. 그러나58행 문맥의 다른 수치 `4명에서8억10만명`을 “정확한 역사 인구”로 승인할 근거도 없다. 그 숫자가 손상되어 보인다는 판독과 올바른 원 수치가 무엇인지는 별도다. 외부 원문을 보지 않고 “4백만/8백만/1천만” 등의 기억 값으로 고쳐 쓰지 않았다.

87/159/188/202행에서 확정한 것은 **위 표의 전문용어·수식·주체 표현이 실제 학생 입력에 그렇게 저장되어 있다는 사실**이다. 암호화 염색/유기 아진 등의 번역 손상, 표장의 색·분할 표현 파손, 항공사·군부 어휘 혼재는 후속 원어 검수의 구체 대상이다. 원 영어 문서/원천 주석을 열지 않았으므로 올바른 생물학·화학·문장학·군사 용어/범위를 이번에 인증한 것은 아니다. 특히 원문이 틀렸을 수 있다는 이유로 교사의 phyB/바르비에 답까지 모두 오답으로 소급하지 않는다.

116행의 경우 약어의 대응은 본문에서 분명하지만, source의 현재 소속과 과거 분리 설명이 동시에 남는다. 학생에게 온전한 공군 조직사 설명을 학습시켰다고 하기보다 **내부적으로 정리되지 않은 문맥에서 약어를 회수한 예**로 읽는 것이 타당하다. source의 현재 군복 서비스 수 등은2026 현행 검증을 하지 않았다.

**수락 라벨과 의미 적합도 다르다.**101행도 다른15개와 동일하게 raw `LABELS_COMPLETE`/`stop`/빈 parse error로 저장돼217후보에 들어 있다. 이 기술적 상태는 질문에 필요한 공용어 전제가 본문에 없다는 관측을 무효로 하지 않는다.145행도 형식상 정상 답이지만 실물 통계 없이 결론을 반복한 답이다. `accepted_groups`를 “모든 질문의 충분한 근거·정답성·의미 적합 전수 수락 수”라고 읽으면 안 된다.

### 37.7 후속 재검토 필요·이번 작업의 한계와 원형 보존

후속 사람이 검토할 우선 사례는 **101행의 외부 전제 의존**,130/145행의 선행 대상·증거 누락,87/116/159/188/202행의 원어·행위자·전문용어와 조건 범위다. 이는 해당 문자열을 포함하면 자동 탈락시키라는 목록이 아니라 **이 정확한 문맥/질문/답을 다시 함께 읽어야 하는 위치**다. 정정 또는 제외를 결정할 경우 원어/source 근거·버전·영향 범위와 새 승인이 먼저 필요하고, 이번 감사는 어떤 후보도 수정·삭제·재생성·게이트 변경하지 않았다.

다음에 별도 닫힌 증거의 검토를 승인한다면, 이번 등간격 표본이 전혀 다루지 못한 영어/다른 family/JSON/multiturn과 긴 입력·예산 경계는 별도 표본으로 읽어야 한다. 현재 열린 batch_000001를 지금 읽거나 그 결과를 추정하라는 제안이 아니다. 전수 평가·오염률·유효 토큰량·학생 품질·production 채택 판정은 이번16개 읽기로 산출할 수 없다.

이번 실제 수행은 닫힌5개 파일의 읽기/작은 SHA·JSON·문자열 동일성 대조와 선택16개·대응 raw16개의 실제 입력/최종 답 판독이다. 원 upstream parquet·보호 TinyDataset·교사 모델·현재 열린 batch·추가 자료는 열지 않았다. 교사 reasoning 전문/생성 패킷을 새 교사·학습·Luna에 보내지 않았고, 문자열 불량목록·온라인 자동 정답 게이트·새 점수/문턱을 만들지 않았다. GPU/모델/교사 API/학습/설치/Git/프로젝트 검사기·코드 실행0, 원문/생성 후보/보고서/manifest/공용문서 수정0이며 **본 소유 연구문서의 이 새 절만 추가**했다.

상태: **`CLOSED_BATCH000000_217_CANDIDATES_MANIFEST_VERIFIED / PRESELECTED_SYSTEMATIC16_FULL_VISIBLE_CONTEXT_QUESTION_ANSWER_READ / RAW_SOURCE_QUOTING_EXACT_IN16 / EXPLICIT_PREMISE_GAP_AT_CANDIDATE101 / SOURCE_LANGUAGE_AND_REFERENCE_AMBIGUITIES_RETAINED / NOT_SEMANTIC_PASS_OR_POPULATION_RATE / BATCH000001_UNTOUCHED / NO_MODEL_OR_DATA_CHANGE`**.

## 38. 완료·대체 런처 정리의 독립 반 검토: 실행 완료와 wrapper 폐기를 분리

### 38.1 결론·권한·실제 재고

2026-10-23 17시대의 **새 사용자 삭제/로컬커밋 승인 전달을 전제로 한 읽기 전용 제안**이다. 이전 인계의 “삭제/Git 승인 없음”은 당시 이력이며 새 승인보다 우선하지 않는다. 그러나 반 담당자에게 실제 삭제·코드/공용문서 변경·Git 쓰기·모델 실행은 허용되지 않았다. 이번에는 소유 연구문서만 추가했다. 원형44소스·체크포인트·원문·raw로그·캐시의 삭제 제안은 아니다.

권고를 요약하면 **(A) 기존 DONE11은 현재 원본/전문 사본/SHA/755 대조까지 완료, (B) 추가19개는 중복·대체된 wrapper로 보존 사본을 먼저 만든 뒤 정리 가능, (C) 현재 미래 작업2개는 보존, (D) 나머지163개는 이번 제한 검토만으로 일괄 삭제하지 않음**이다.19개 중 미실행 대체 경로는 DONE으로 위장하지 않고 `SUPERSEDED_NOT_RUN` 등 실제 이력을 보존해야 한다.

루트 바로 아래 `run_P*.sh/.bat`만 열거한 시점의 재고는 **195개/275,316B: done42·hold142·접미사 없는11**, BAT0개였다. 이는 루트 이외 런처나 전체 frontier 전수 재심사 수가 아니다. `experiments.tsv`의 탭9열 이상 역사/현재 행은553개였고, 주석 처리된 과거 행도 있으므로 TSV 행 수를 현재 실행 파일 수/현재 유효 큐로 읽지 않았다. 최신 [202610231602 인계](/home/uranus/tinyLM/handoff/202610231602_HANDOFF.md)의 이전 연결은202610220107이며 §7/§7.1/§6b.1을 직접 대조했다. 현재 §7은 XW교사 재개와 learned router 두 작업만 유지하고 C2/C3 전수 frontier 검증 미완을 명시한다.

### 38.2 삭제 가능성이 이미 닫힌 DONE11: 전문 복구 증거를 독립 확인

[DONE11 전문 보존 감사](/home/uranus/tinyLM/handoff/audit/WIP_20261023_DONE11_FULL_SOURCE_ARCHIVE.json), SHA `D9BD916A089181C1BD9AEB4271B6B9E32F432B68C36712223ECB8BA5401BE0A9`의11행 각각을 현재 파일과 [보존 폴더](/home/uranus/tinyLM/handoff/audit/launcher_archive_20261023)에서 다시 읽었다. **11개 모두 source 존재, source/archive 바이트 동일, archive SHA=manifest SHA, 원 source mode755**였다. [명령 보존 감사](/home/uranus/tinyLM/handoff/audit/WIP_20261023_DONE11_COMMAND_PRESERVATION.json)의 정확한 source명·결과문서 연결도 읽었다. 이번에는 실제 모델 로그/학습을 재실행하지 않았다.

정확한 후보는 다음11개다. 각 사본은 같은 파일명 뒤 `.txt`를 붙인 경로이며, 전문에는 변수·loop·선결·오류 처리도 남는다.

| 루트 파일 | 보존/해석 |
|---|---|
| run_P106B_Stage7c0Wb_alm_profiles_cpu_prepare-done.sh | ALM 두 명시 profile CPU 준비 완료 이력 |
| run_P106B_Stage7cWb_alm_profile_gradient-done.sh | profile별 gradient 진단 완료 이력 |
| run_P106B_Stage7dWb_alm_profile_cost_pair-done.sh | profile별 비용 완료 이력 |
| run_P106B_Stage7eWc_alm_profile_train_pair-done.sh | Fv2/Qv1 CE·ALM 학습 완료 이력 |
| run_P106B_Stage7eWd_alm_profile_actual_answers-done.sh | 실제 부모/CE/ALM 답 회수 완료 이력 |
| run_P106B_Stage9bW_recovery_full_smoke-done.sh | 해당 source 시점의 완료 스모크 이력 |
| run_P106B_Stage9cW_alm_full_smoke-done.sh | 해당 source 시점의 완료 스모크 이력 |
| run_P106B_Stage9dW_current_source_full_smoke-done.sh | 최신 종료 source 스모크 이력; 이후 코드 변경까지 검증한 것이 아님 |
| run_P106B_Stage4fsWp_supported_teacher_deadline_window-done.sh | 첫 증분창 폐쇄;75M/의미 검수 완료 아님 |
| run_P106B_Stage4fsWt_supported_teacher_deadline_resume-done.sh | 둘째 증분창 정상 budget pause/폐쇄; 전체 생산 완료 아님 |
| run_P102A_Stage2bW_streaming_head_parity-done.sh | 수치 음성까지 회수한 완료 진단; 동등성/가속 채택 성공 아님 |

**복구 준비가 된 삭제 후보**라는 결론이다. 실제 삭제 직전 source/archive의 SHA·정확 경로를 총괄이 다시 대조하고, 삭제 영수증/레지스트리 이관을 남기면 된다. 사본 보존은 재실행 승인이나 source 수치 PASS를 의미하지 않는다. 원 파일을 지워도 음성 보고서·정확 명령·source SHA·모드·원 로그를 지워서는 안 된다.

### 38.3 P078 Wc는 “wrapper 실행 완료”가 아니라 “과학적 목표 완료에 따른 obsolete”로 정리 가능

[Stage2Wc](/home/uranus/tinyLM/run_P078_Stage2Wc_verified_route_full.sh)는 `budget-preview → uniform_r2 → fixed_shuffle_r2 → update_shuffle_r2 → balanced_count → readback`을 묶고, fresh `TL_P078_AUTHORIZATION`/SHA 및 전체8.62h 예상/여유 입장을 요구한다. 현재 SHA는 **`DD0F4EBC5E0F42FA4B1AE33C48BC2078B10F12934EA57DB5943F4DBFFCDB5F77`**,2,571B다.

실제 완료는 [066 결과 §12~13](/home/uranus/tinyLM/test_result/066_20260831_P078-이득은-몰려있지만-어느-크롭인지는-재현되지-않는다.md:470)과 원 로그가 소유한다.22일 [Wd 로그](/home/uranus/tinyLM/test_result/066_log_20261022_P078_Stage2Wd_selected_count_pair_100916.txt)는 선택2팔 uniform/balanced와 readback을 종료0으로 마쳤고,23일 [We 로그](/home/uranus/tinyLM/test_result/066_log_20261023_P078_Stage2We_remaining_shuffle_pair_090858.txt)는 미완 두 셔플만 train한 뒤 원4팔 readback을 종료0으로 닫았다. 이 두 로그의 실제 run name/명령을 읽었다. `066_log_*.txt`에서 **Wc run name의 실행 로그는 찾지 못했다.** 이것만으로 저장소 전체 어디에도 실행 기록이 없다고 증명한 것은 아니며, 적어도 Wc 자체가 한 번 성공 실행됐다고 기록할 근거는 이번에 없다.

따라서 Wc를 `DONE_WRAPPER_EXECUTED`로 바꾸는 것은 부정확하다. **`OBSOLETE_SCIENTIFIC_ARMS_COMPLETED_VIA_WD_WE; WRAPPER_RUN_NOT_ESTABLISHED`**로 retire하는 것이 맞다. 미실행 전체 wrapper를 계속 실행 가능 재고로 남겨 원4팔을 다시 훈련할 이유는 없다. 과학적 학습/원4팔 재계수 완료와 낮은 실제 답 품질은 모두 보존한다. 이 삭제 제안은 중복 학습의 제안이 아니다.

`experiments.tsv`의 **id180(line58)**은 아직 “본 네팔 pending8.619h” 상태이고, **id182(line60)**의 Wd도 미완처럼 남는다. 반면 인계 §7.1은 이미 Wc를 완료 이관했다. 새 정리에서는 두 TSV 항목의 유효 큐 여부를 **최신 실제 완료/obsolete**로 명시적으로 이관해야 한다. 역사 원행/명령을 조용히 지워 과거 예상과 실측의 구분을 잃으면 안 된다.

P078 controller의 `PINS` 및 source 목록을 source로 확인했다. `diag_p078_route_protocol.source_identity()`는 원 Python2개와 protocol/test를 검산하고, 원 training의44개 `CODE` 및 router의 확장 `CODE`에 이 루트 SH들은 들어 있지 않다. 따라서 **루트 SH만** 정리하는 것은44개 Python/tinylm 원형의 변경과 다르다. 원44파일·CP·자료·권한 원형은 그대로 둬야 한다.

### 38.4 추가9개 접미사 없는 대체·중복 경로: 전문 사본이 생긴 뒤 정리 권고

다음9개는 현재20261023 전문 보존 폴더에 **각 파일명+.txt가 없다**. 아래 SHA는 현재 루트 source의 읽기 관측이며 복구 사본을 만들었다는 뜻이 아니다. 모두 일반 파일이고 symlink가 아니었다. 새 전문 사본+SHA/모드/결과·대체 경로 manifest를 먼저 만들어야 한다. `scripts/`/`tinylm/`에서 이19개(본9개+다음10개)의 정확 basename을 참조하는 호출은 찾지 못했지만, 문서/TSV의 역사 참조는 남는다.

| 추가 후보 | 현재 SHA256 | 분류/이유 |
|---|---|---|
| run_P078_Stage2Wc_verified_route_full.sh | `DD0F4EBC5E0F42FA4B1AE33C48BC2078B10F12934EA57DB5943F4DBFFCDB5F77` | 위 §38.3의 obsolete; wrapper 실행 성공을 꾸미지 않음 |
| run_P078_Stage2Wd_selected_count_pair.sh | `79B470F6F3F0090F129266AECE59A702E321F37EE23EEDBD3BB8A2BCA3C192EA` | 선택2팔/원 readback 완료 로그 있음; 같은 두704 재실행 불필요 |
| run_P106B_Stage4fsWb_supported_teacher8h.sh | `2A162DB8F7C4018A87172F00EB82E4998971B8841C30B3B10FB5D8F89C05E565` | 현재 인계 §7.1에서 XW로 대체. 옛 produce8h를 새 사용자창으로 재사용하지 않음 |
| run_P106B_Stage4fsWc_supported_teacher_resume8h.sh | `BC3F9EBDB49C12FFE773D5BD37535932BA473ECC1149DFA8D10EE3604D309ECF` | XW로 대체. 특히 주석의 “prior STOP을 이동”은 새 XW의 고유 STOP/원 STOP 보존 계약과 다름 |
| run_P106B_Stage7c0W_alm_student_cpu_prepare.sh | `E22A30C37CB4542D36F9B72250AB1535A76305C2E9AC014451D9009F5B098B0F` | legacy profile 준비 wrapper; 명시 Fv2/Qv1 준비 wrapper로 대체 |
| run_P106B_Stage7cW_alm_train_gradient_calibration.sh | `F719FC73FA0ADB019CE00629793ACD07EBC9EDB7EAF8F66243DF60A7B04899E2` | legacy calibration; 새 profile별 calibration과 별개 이력으로 retire |
| run_P106B_Stage7dW_alm_matched_cost_pair.sh | `D7D5F81BE6665061C27141DB2895700C7F7FF9C279991D6B46FE9A069AECC2BA` | legacy cost; 새 profile별 완료 비용이 소유하는 진단과 혼합 금지 |
| run_P106B_Stage7eWa_alm_matched_train_pair.sh | `9DC88BC674ED9D9F0C51CA9D2DB558A0D42F6A5CF1721AD0CE03C7854E7CBADA` | legacy train; 현재 미완 새 연구라는 이유로 자동 재훈련할 경로 아님 |
| run_P106B_Stage7eWb_alm_parent_child_answers.sh | `12C9C1280D77485B99076ABA8DB7FA7357ACF7AC91C47AB9F33DD097B219BBD1` | legacy parent/CE/ALM 답 회수; 현재 Fv2/Qv1 완료 원답과 namespace가 다름 |

ALM5개는 모두 `--study`가 없고, 실제 [현재 CLI source](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:1312)의 기본값은 **`float_v1`**이다. 이를 완료된 `float_v2`/`ternary_v1`로 자동 해석하면 안 된다. source hash도 기본 `sources()` 경로에서 얻으므로 오래된 준비 영수증과 충돌하거나 legacy namespace로 새 작업을 시도할 수 있다. 반대로 explicit profile wrapper는 `--study "$study"`를 전달한다. **새 profile 완료가 legacy runtime 실행까지 완료했다는 뜻은 아니지만, 현재 사용자 요청용 실행 경로로는 대체됐다**는 판단이다. id210~214를 현재 미완 실험으로 계속 나열하기보다 미실행/대체 이력을 남기는 편이 정확하다. 이5개를 지운다고 ALM의 음성·원삼진 요청의 범위 차이를 없애는 것은 아니다.

### 38.5 추가10개 hold wrapper: 대체 원인이 명시된 한정 정리 후보

아래10개도 현재20261023 전문 보존 폴더에는 사본이 없다. **NOT_RUN/HOLD 음성을 보존하는 전문 archive를 먼저 만들고** root 실행 경로에서 정리할 수 있는 후보로 판단했다. `-hold` 접미사만 보고 삭제한 것이 아니라 source의 버전/선결·대체 wrapper와 인계의 실제 현재 경로를 대조했다.

| 정확 파일 | 대체·보류 원인 | 기록에 남길 상태 |
|---|---|---|
| run_P078_Stage3Wa_prefix_router-hold.sh | 옛 VAL512 split 부족의 V1. 현재 full Wc는 새 holdout V2 계약 | `V1_SPLIT_SHORTAGE_HOLD; SUPERSEDED` |
| run_P078_Stage3Wb_prefix_router_v2-hold.sh | 같은 router driver로 임의 stage를 전달하는 수동 wrapper. 자기 주석도 Wc full 사용 명시 | `MANUAL_WRAPPER_SUPERSEDED; NOT_ROUTER_DONE` |
| run_P106B_Stage7bWe_native_teacher_cache1024-hold.sh | V4 canary가 닫히지 않아 본 cache NOT_RUN; V5→V7로 대체 | `V4_PREREQUISITE_HOLD; FULL_NOT_RUN` |
| run_P106B_Stage7bWh_utf8_probability_canary17-hold.sh | V6 미실행 source를 보존한 옛 wrapper. 현재 strict Stage7bWj(V7)로 대체 | `V6_NOT_RUN; SUPERSEDED` |
| run_P106B_Stage7bWi_utf8_probability_cache1024-hold.sh | V6 본 cache 조건부 미실행. 현재 Stage7bWk(V7)로 대체 | `V6_NOT_RUN; SUPERSEDED` |
| run_P106B_Stage8eW_official_core6_full-hold.sh | 원 v1 source 경로. 현재 versioned v2의 네 full 보고서가 완료 | `OLD_SOURCE_FULL_NOT_RUN; V2_REPLACEMENT_COMPLETE` |
| run_P106B_Stage8fW_babylm_causal_cost-hold.sh | v1 GPU 비용 미실행, v2 공통 idle로 대체 후 v3 pre-HF cache 정책으로 재대체 | `V1_NOT_RUN; SUPERSEDED` |
| run_P106B_Stage8fWb_babylm_causal_cost-hold.sh | v2 미실행, 현재 Stage8fWc cache-policy 비용으로 대체 | `V2_NOT_RUN; SUPERSEDED` |
| run_P106B_Stage8gW_babylm_causal_full-hold.sh | v1 full 미실행, v2→v3로 대체 | `V1_NOT_RUN; SUPERSEDED` |
| run_P106B_Stage8gWb_babylm_causal_full-hold.sh | v2 full 미실행, 현재 Stage8gWc로 대체 | `V2_NOT_RUN; SUPERSEDED` |

폐기된 source 버전의 SH를 현재 바뀐 `.py`에 그대로 연결해 실행하는 것은 과거 버전 재현이 아니다. 최신 버전이 이름만 같아 실행된다고 원V4/V6/v1/v2 선결을 통과했다고 쓸 수 없다. 특히 추가10개 중 BabyLM 비용/full4개를 정리하더라도 **Falcon 문법 full HOLD와 전체 BabyLM 미완 범위가 해소되는 것은 아니다.** 원인·원 보고서·source snapshot은 보존한다.

### 38.6 반드시 보존할 현재2개: 미완 선결이 실질적으로 다름

| 보존 파일 | 현재 목적/유효 선결 | 완료 작업과의 차이 |
|---|---|---|
| [run_P078_Stage3Wc_prefix_router_full.sh](/home/uranus/tinyLM/run_P078_Stage3Wc_prefix_router_full.sh) | source/부모/고정 corpus 및 **새 router authority+SHA/holdout report SHA**, 완료balanced704, 현재 cost8·전체 예산. cost→budget→labels→fit→evaluate→readback 순서 | body 네팔704 완료는 선결 하나를 충족한 것뿐. TRAIN label/head fit/DEV 선택/TEST는 별도 미실행이므로 Wc를 P078 완료와 함께 삭제하면 실제 후속 경로가 사라짐.1.5h는 미측정 |
| [run_P106B_Stage4fsXW_user_supported_resume8h.sh](/home/uranus/tinyLM/run_P106B_Stage4fsXW_user_supported_resume8h.sh) | **사용자가 별도로 고른 미래8h 창**, `TL_P106B_USER_8H=1`, idle GPU/같은 V3 pilot·source·닫힌 batch, 고유 STOP_USER/deadline8h+종료여유. 원 STOP/보고서 보존 | 기존 Wp/Wt 두 폐쇄창/674후보는75M 목표 완료가 아님. 이 파일의 보존은 새8h 실행 권고/자동 승인 아님. §37의 원천 품질 우려·미채택 상태를 먼저 읽어야 함 |

이2개가 현재 인계 큐에 있다는 사실도 지금 실행할 권한/선결 완료를 의미하지 않는다.17시 모델 허가가 끝난 뒤 새 모델을 띄우지 않았다. XW의 사용자용 미래 창은 Codex 권한 연장과 별개다.

### 38.7 그 외31done·132hold는 이번 근거로 일괄 삭제하지 않음

DONE42 중 전문 byte archive까지 이번에 독립 검산한 것은11개뿐이다. 나머지31개는 `-done` 실물/TSV의 결과 연결 또는 완료/음성 표기가 있어 **후속 삭제 검토 대상**일 수 있으나, 그 이름만으로 복구 사본·완료 원 로그·같은 단계 재실행 의도까지 전수 확인한 것은 아니다. 특히 tokenizer recovery/PAD 옛 wrapper/public source deck은 현재 TSV에 정확 대응 행이 없었고, 일부 완료 wrapper는 TSV에 아직 접미사 없는 active 행으로 남는다. 원래 사본이 다른 역사 감사에 있을 가능성과 **이번20261023 폴더에서 복구 준비가 확인됐다**는 주장을 구별한다.

그31개의 정확 재고는 다음과 같다. 이 목록은 추가 삭제 완료/승인 목록이 아니다.

```text
run_P067_Stage4Wb_tokenizer_recovery-done.sh
run_P078_Stage2We_remaining_shuffle_pair-done.sh
run_P101A_Stage3jW_clean_mtp_four_arm-done.sh
run_P101A_Stage3jWb_clean_parent_baseline-done.sh
run_P101A_Stage3kW_verified_reasoning_pair-done.sh
run_P101A_Stage3nW_padding_gpu_pair-done.sh
run_P101A_Stage3ncW_padding_workspace_pair-done.sh
run_P106B_Stage4fvW_existing_model_probes-done.sh
run_P106B_Stage4fwW_new_public768-done.sh
run_P106B_Stage4u1W_public_source_deck-done.sh
run_P106B_Stage7aW_teacher_tf_canary-done.sh
run_P106B_Stage7b0Wc_native_teacher_cpu-done.sh
run_P106B_Stage7b0Wd_native_edge_cpu-done.sh
run_P106B_Stage7b0We_utf8_probability_cpu-done.sh
run_P106B_Stage7b0Wf_strict_probability_cpu-done.sh
run_P106B_Stage7bWb_alm_cache_canary16-done.sh
run_P106B_Stage7bWd_native_teacher_canary16-done.sh
run_P106B_Stage7bWf_native_edge_canary16-done.sh
run_P106B_Stage7bWg_native_edge_cache1024-done.sh
run_P106B_Stage7bWj_strict_probability_canary17-done.sh
run_P106B_Stage7bWk_strict_probability_cache1024-done.sh
run_P106B_Stage8aW_official_assets_cpu-done.sh
run_P106B_Stage8cW_official_adapter_canary-done.sh
run_P106B_Stage8dW_official_core6_cost-done.sh
run_P106B_Stage8dWb_official_core6_versioned_cost-done.sh
run_P106B_Stage8eWb_official_core6_versioned_full-done.sh
run_P106B_Stage8f0W_babylm_causal_cpu-done.sh
run_P106B_Stage8f0Wb_babylm_causal_cpu-done.sh
run_P106B_Stage8f0Wc_babylm_cache_policy_cpu-done.sh
run_P106B_Stage8fWc_babylm_cache_policy_cost-done.sh
run_P106B_Stage8gWc_babylm_cache_policy_full-done.sh
```

**hold142개 중 이번의 명시 대체10개를 뺀132개**는 전수 의미 재심사를 하지 않았다. 오래된 [retained disposition](/home/uranus/tinyLM/handoff/audit/WIP_20261019b_RETAINED_LAUNCHERS_DISPOSITION.json)은 생성 start/resume와 finalize/wire/train/eval의 선결을 나누며, 예를 들어 `run_P106B_Stage4jWk_stream_mtp_fork_start-hold.sh`/`Stage4jWl...resume`의 문제는75M 미달이 아니라 **source-visible 생산계약 미채택**이라고 정정한다. 반면 `run_P106B_Stage4kWg_stream_completed_corpus-hold.sh`/`Stage4k0Wg...student_wire` 등은 **정확한 해당 버전75M·quota·학생 배선**이 실제 미완 선결이다. 다른 source 버전의 새 생산을 돌렸다고 이 전 버전 미완이 자동 소멸하지 않는다.

따라서132개를 모두 “날짜가 지났으니 불필요” 또는 “같은 P106B이니 중복”으로 삭제하면 실제 미완 연구 선택지를 사후 소거할 수 있다. 반대로 전부를 현재 권장 실행 큐로 보존하는 것도 부정확하다. 정확한 버전·대체/폐기 의도·역사복구 경로를 추가로 닫기 전까지는 **HOLD 재고 보존/즉시 실행0**이 안전하다. 최신 인계가 C2/C3 미완을 공개한 것과 맞는 제한이다.

### 38.8 정리3안과 영향도: 권고는 한정 정리 후 남은 의미감사 분리

| 안 | 내용 | 장점 | 단점/영향·비용 |
|---|---|---|---|
| A 최소 | 이미 byte archive가 검산된11개만 실제 정리 | 현재 복구 증거가 가장 명확; 적은 변경 | obsolete Wc/legacy5/옛8h가 active처럼 남음. 비용 낮음 |
| **B 권고** |11개와, 전문 복구 사본·SHA/모드·retire 사유를 새로 남긴 추가19개만 한정 정리. 현재2개/나머지163개는 보존 | 과학적 완료와 wrapper 이력을 섞지 않고 명확한 중복 경로를 줄임 | 추가19의 archive가 **현재 아직 없음**. 총괄의 보존/재검산·TSV/인계 연결 갱신 필요. 비용 낮음~중간 |
| C 전수 후 정리 | 나머지31done/132hold까지 source·실제 결과·동등 대체·복구를 전수 판정해 더 큰 정리 | 루트 재고와 현재 frontier를 가장 명료하게 만들 수 있음 | C2/C3 미완·비교 의도/부분 음성까지 다시 추적해야 해 범위·비용 큼. 완료되지 않은 감사 없이 일괄 삭제하는 안은 아님 |

impact-analysis의 축별로 보면, 코드 영향은 root wrapper 제거에 한정하고 실제 Python API/원형44·모델코드는 변경하지 않는다. 데이터 스키마/CP/원 로그 영향은0이어야 한다. 테스트/스모크의 완료 증거는 보존하되 이후 source까지 PASS로 확장하지 않는다. 문서 영향은 `experiments.tsv`/최신 인계의 명시 retirement·정확 archive 링크에 있고, 기존 결과·계획·기준표·방법론의 역사 증거를 덮어쓸 필요는 없다. 기술부채 측면에서는 A가 legacy active 착시를 남기고 C가 현재 의미감사 비용을 키우므로 B를 권고한다. GPU/학습 권한·비교조건·메모리/품질의 증거 수준은 정리로 변경되지 않는다.

총괄의 실제 삭제는 별도 사용자 승인에 따른 정확 경로/복구 검산 및 명시 목록 보고가 필요하다. 로컬커밋도 총괄 소유이며 이 반 검토는 staging/commit/push를 하지 않았다. 이번 재고/해시는 관측 시점 값이므로 총괄이 동시에 정리했다면 사라진 파일을 되살리거나 source를 다시 쓰지 말고 실제 삭제 영수증을 후속 증거로 연결해야 한다.

상태: **`READ_ONLY_LAUNCHER_REVIEW / ROOT195_SNAPSHOT / DONE11_BYTE_ARCHIVE_VERIFIED / ADDITIONAL19_RETIRE_CANDIDATES_REQUIRE_NEW_FULL_ARCHIVE / KEEP_ROUTER_WC_AND_USER_8H_XW / OTHER163_NOT_CLEARED_FOR_BLANKET_DELETION / WC_WRAPPER_RUN_NOT_ESTABLISHED_BUT_FOUR_SCIENTIFIC_ARMS_COMPLETE / NO_DELETE_CODE_GIT_MODEL_ACTION`**.
