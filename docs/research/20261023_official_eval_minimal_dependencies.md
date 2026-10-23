# 2026-10-23 Core6 공식 평가 도구 고정 및 최소 의존성 감사

## 1. 결론과 수행 경계

Core6의 공식 도구는 **EleutherAI lm-evaluation-harness**로 고정했다. 공식 GitHub API에서 확인한 `main`의 정확 commit `d6de81643928d653435c431bae19945d41d32520`의 archive와 source만 반입했다. **설치·등록·패키지 import·모델/GPU·평가는 모두 `NOT_RUN`**이다. 의존성이 있다고 해서 설치 승인으로 간주하지 않았다.

실제 Core6 경로에서 새로 필요한 공통 패키지는 `sacrebleu`와 공식 CLI 출력용 `pytablewriter`이며, `lm_eval` 자체의 배포 metadata 등록도 빠져 있다. HF 백엔드를 선택하면 `accelerate`가 추가로 필요하다. 이들은 아직 설치하지 않았다. 반면 `evaluate`·`scikit-learn`·`rouge-score` 등은 harness 배포 설정에는 선언되지만, 이번 Core6의 내장 acc/acc_norm 경로와 캐시·PEFT OFF에서는 호출되지 않는다. **배포 metadata의 전체 요구 충족**과 **선택한 경로만의 runtime 요구**를 같은 말로 쓰지 않는다.

앞선 [공식 평가 반 감사](20261023_antithesis_official_eval_and_methods.md)의 최초 소스 감사 시점에 미고정이던 harness source commit은 이번 추가 승인으로 해소했다. 기존 MC768의 SUM_NLL 점수를 새 공식 평가 점수로 변환하거나 절대 비교하지 않는다. BabyLM2026Strict의 82개 자산과 트랙은 별도이며, Core6를 위해 BabyLM pipeline을 추가하지 않았다.

## 2. 대상·도구·source provenance

| Core6 공식 task ID | 고정 source의 dataset/config | 공식 채점 split | 이 task의 내장 지표 |
|---|---|---|---|
| `piqa` | `baber/piqa` / null | validation | acc, acc_norm |
| `arc_easy` | `allenai/ai2_arc` / ARC-Easy | test | acc, acc_norm |
| `arc_challenge` | 같은 dataset / ARC-Challenge | test | acc, acc_norm |
| `hellaswag` | `Rowan/hellaswag` / null | validation | acc, acc_norm |
| `winogrande` | `allenai/winogrande` / winogrande_xl | validation | acc |
| `boolq` | `aps/super_glue` / boolq | validation | acc |

이 표는 source YAML의 계약이다. 후속 별도 승인으로 **지명 평가 Parquet 6개와 정확 dataset revision의 실제 반입**을 마쳤으며, [반 문서 §12](20261023_antithesis_official_eval_and_methods.md#12-추가-승인-core6-평가-split의-고정실제-반입)와 [데이터 manifest](/home/uranus/tinyLM/data_cache/p106b_official_eval_assets/core6_d6de816_20261023/manifest.json)에 기록했다. 자료 확보와 실제 loader/평가 실행은 다르며 후자는 `NOT_RUN`이다. HellaSwag의 공식 전처리와 WinoGrande의 후보별 prefix/common suffix 우도를 유지하고 첫 글자 생성이나 후보 첫 token 확률만으로 대체하지 않는다.

| 항목 | 실제 확보값 |
|---|---|
| commit 확인 원천 | [공식 commits/main API](https://api.github.com/repos/EleutherAI/lm-evaluation-harness/commits/main), [정확 commit](https://github.com/EleutherAI/lm-evaluation-harness/commit/d6de81643928d653435c431bae19945d41d32520) |
| committer date | `2026-09-14T10:51:05Z` |
| source archive | [정확 commit의 공식 archive](https://codeload.github.com/EleutherAI/lm-evaluation-harness/tar.gz/d6de81643928d653435c431bae19945d41d32520) |
| 전용 보존 폴더 | `/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/` |
| archive 실제 크기·SHA256 | 3,640,478 B · `c60d18c7dcedb03fdd95d43cd2f0bc4a575862a64eb8c9b390e96f5129e442a4` |
| source 파일 | `source/` 아래 16,415개 · 13,907,399 B |
| source tree SHA256 | `798fa248b3c3a2342ca733fb89ccb507e938d955fd6d7b26f8405a89af43fc54` — 파일별 path/bytes/SHA256를 정렬한 compact canonical JSON의 SHA256 |
| 완료 시각 | `2026-10-22T21:19:05.310812+00:00` = KST 2026-10-23 06:19 |
| 배포 정보 | `lm_eval 0.4.14.dev0`, Python >=3.10, MIT. `LICENSE.md` 원본 포함 |
| 영수증 | [manifest.json](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/manifest.json) |

archive SHA는 공식 고정 URL로 받은 실제 바이트의 로컬 checksum이다. 별도 upstream 서명/공표 checksum을 검증했다는 뜻은 아니다. archive 안의 경로·링크·크기를 먼저 제한하고 정규 파일/디렉터리만 새 경로에 풀었다. 기존 파일 교체, Git clone/명령, pip·editable 설치, PYTHONPATH 등록, 환경 변경은 없었다. 소스의 MIT가 각 벤치마크 데이터의 재배포 라이선스를 대신하지 않는다.

## 3. 현 환경 metadata 검사 방법

기준 Python은 `/home/uranus/miniforge3/envs/tlm_torch/bin/python`의 3.10.19다. site 초기화를 끈 `-I -S -B`로 인터프리터 버전만 확인했고, 시스템 Python의 표준 `importlib.metadata`로 다음 dist-info/egg-info의 version 필드를 읽었다.

`/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages`

아래 “현재 metadata.version”은 그 metadata 필드값이다. 대상 패키지나 torch를 import하지 않았고, import 성공·ABI/커널 호환·모델 실행을 검증한 값이 아니다. `미설치`는 해당 위치에 distribution metadata가 없다는 의미다. 다른 Python 환경의 package 존재를 섞지 않았다.

## 4. 실제 공통 import 경로와 필요한 변경

| 패키지 | 필수 버전/선결 | 이유·직접 경로 | 현재 metadata.version | 추가 변경 필요 |
|---|---|---|---|---|
| `lm_eval` | **위 정확 commit**의 0.4.14.dev0 | `__init__.py:7`이 `metadata.version('lm_eval')`을 즉시 읽음 | 미설치; source만 있음 | **등록/설치 별도 승인 필요.** source 경로만 제공하면 metadata 부재로 막힘 |
| `datasets` | harness >=2.16.0 | `api/task.py`, task 데이터 로더; Hella 전처리도 직접 import | 5.0.0 | 현재 유지. 최신 하한 충족이 모든 YAML/data 호환을 보증하지 않음 |
| `numpy` | harness 하한 미명시 | evaluator/metrics/task 공통 | 2.2.6 | 유지 |
| `jinja2` | harness 하한 미명시 | `utils.py`의 template 환경 | 3.1.6 | 유지 |
| `PyYAML` | harness 직접 하한 미명시; 현재 datasets는 >=5.1 | `utils.py`, `_yaml_loader.py`, config | 6.0.3 | 유지 |
| `requests` | GGUF/API extra에도 하한 미명시 | `utils.py`가 공통 상단 import; `models/gguf.py` HTTP | 2.34.2 | 유지; api extra 전체 설치는 불필요 |
| `typing_extensions` | 하한 미명시; `deprecated` 등 symbol 필요 | task manager/result schema/models utils | 4.16.0 | 유지 |
| `tqdm` | >=4.59.0 | model/task 진행 표시 | 4.70.1 | 유지 |
| `dill` | harness 하한 미명시; 현재 datasets >=0.3.0,<0.4.2 | `caching/cache.py`가 상단 import. 캐시 OFF라도 모듈은 로드됨 | 0.4.1 | 유지 |
| `sacrebleu` | >=1.5.0 | **`api/metrics.py:10` 상단 import**, Core6가 BLEU를 안 써도 필요 | 미설치 | **공통 누락 필수 후보** |
| `pytablewriter` | harness 하한 미명시 | 공식 CLI가 완료 후 `utils.make_table()`로 출력 | 미설치 | **CLI 누락 필수 후보**. programmatic 결과 dict만 받는 대체 경로는 별도 명명 |
| `pandas` | 표준 CLI logger import상 필요, 하한 미명시 | `loggers/__init__` → `wandb_logger.py:7`, W&B OFF라도 import | 2.3.3 | 유지; W&B 업로드 권한과 별개 |
| `huggingface-hub` | 현재 datasets >=0.25.0,<2; transformers >=1.5.0,<2 | dataset/client·HF 모델·logger 경로 | 1.24.0 | 유지; 저장된 weights가 있어도 Hub metadata 접근 정책은 별도 |
| `packaging` | 현재 transformers >=20.0 | 모델/버전 처리 및 logger | 26.3 | 유지 |
| `setuptools` | build 시 >=64.0 | source 배포 metadata/설치 준비. 평가 계산 자체의 필수는 아님 | 84.0.0 | 현 환경 추가 갱신 불필요; build 실행은 미승인 |

핵심 소유 파일은 [배포 설정](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/pyproject.toml:1), [초기 metadata lookup](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/__init__.py:7), [공통 metrics import](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/api/metrics.py:10), [CLI table](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/utils.py:481)다. 새 설치가 2개뿐이라는 말은 **그 둘이 가져오는 전이 의존성까지 2개**라는 뜻이 아니다(§7).

기존 datasets의 주요 전이 패키지도 metadata상 존재한다: pyarrow 25.0.1(현재 datasets 요구 >=21), fsspec 2026.4.0(현재 요구 <=2026.4.0), multiprocess 0.70.19(<0.70.20), xxhash 4.0.1, filelock 3.32.3. 최소 설치라는 이유로 이들을 최신으로 일괄 갱신하지 않는다.

## 5. 백엔드별 필수/선택 구분

| 패키지·도구 | 필수 버전 | HF 백엔드 | GGUF 백엔드 | 현재 metadata.version | 추가 변경 필요 |
|---|---|---|---|---|---|
| `torch` | harness hf >=1.8; 현재 transformers torch extra >=2.4 | 직접 필수 | backend 자체는 요구하지 않음 | 2.10.0+cu130 | 현것 유지, 재설치/업그레이드 근거 없음 |
| `transformers` | harness hf >=4.1 | 직접 필수 | backend 자체는 요구하지 않음 | 5.14.1 | 유지; 하한만 충족했다고 내부 API 호환 PASS 아님 |
| `accelerate` | harness hf >=0.26.0; 현 transformers 관련 extra >=1.1.0도 고려 | **상단 import 필수**, 단일 GPU라도 필요 | 요구하지 않음 | 미설치 | **HF 선택 때만** 후보 1.15.0, GGUF만이면 보류 |
| `peft` | hf extra >=0.2.0; 4bit adapter 분기에는 별도 >=0.4 | `peft=` adapter를 실제 쓸 때 lazy import | 요구하지 않음 | 미설치 | 일반 BF16/FP32 weights 평가에는 보류. hf extra 일괄 설치로 끌어오지 않음 |
| `tokenizers` / `safetensors` | 현재 transformers 요구 >=0.22.0,<=0.23.0 / >=0.8.0 | 현재 fast tokenizer와 weights 경로 | 서버 자체 tokenizer/weights 사용 | 0.22.2 / 0.8.0 | 유지 |
| `sentencepiece` | 해당 extra >=0.1.98 | slow/SentencePiece 경로를 실제 선택할 때 | 서버 tokenizer이면 불필요 | 미설치 | 지정 모델의 tokenizer.json fast 경로를 먼저 확인; 자동 설치하지 않음 |
| llama-server/Prism | 지명 바이너리 SHA·model format·현대 OAI `logprobs.content` 응답 | 해당 없음 | 별도 서버가 필수 | Python package 아님 | 기존 엔진/정확 GGUF 호환 canary가 선결. pip llama-cpp-python 설치는 필요조건 아님 |
| `aiohttp` / `tenacity` / `tiktoken` | api extra에 하한 미명시 | 별도 API backend를 선택할 때 | `gguf.py`의 실제 요청에는 쓰지 않음 | 3.14.3 / 미설치 / 미설치 | native GGUF를 api extra 전체와 혼동하지 않음 |

[HF 실제 imports](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/models/huggingface.py:9)는 accelerate를 상단에서 가져오지만 PEFT는 `if peft:`에서만 가져온다. [GGUF 실제 imports](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/models/gguf.py:6)는 requests/tqdm/공통 LM이다. TinyLM 자체를 custom LM adapter로 붙이는 것과 `HFLM`을 쓰는 것은 다른 경로이므로 TinyLM adapter에 accelerate가 무조건 필요하다고 단정하지 않는다.

GGUF의 순수 backend import 요구가 적다고 해서 이 **기존 환경에서 공식 evaluator 실행 시 torch import가 0**이라는 뜻은 아니다. `set_torch_seed()`는 torch가 있으면 import하고, 환경정보 수집도 설치된 torch/transformers를 가져올 수 있다. 이번 감사는 그 코드를 실행하지 않았다.

## 6. 배포 설정상 선언됐지만 Core6 경로에서는 선택적인 항목

| 패키지 | 공식 pyproject 요구 | 실제 쓰이는 분기 | 현재 metadata.version | 이번 Core6 runtime-only 변경 |
|---|---|---|---|---|
| `evaluate` | >=0.4.0 | 등록된 내장 metric이 없거나 HF metric 강제 시 `get_metric()` fallback | 미설치 | 보류: Core6 acc/acc_norm은 내장 등록 |
| `scikit-learn` | >=0.24.1 | F1/Matthews 등 해당 aggregator | 미설치 | 보류: 이번 6과제는 acc/acc_norm. 이후 KoBEST macro-F1에는 재검토 |
| `rouge-score` | >=0.0.4 | TruthfulQA generation 등 별도 task utils | 미설치 | 보류 |
| `sqlitedict` | 하한 미명시 | `CachingLM` 응답 DB 캐시 선택 시 lazy import | 미설치 | `use_cache` OFF면 보류 |
| `word2number` | 하한 미명시 | 배포 기본 요구에 있으나 선택 Core6 import graph에 없음 | 미설치 | 보류 |
| `more_itertools` | 하한 미명시 | 현 source에서는 vLLM backends의 distribute | 미설치 | HF/GGUF Core6에서는 보류 |
| `scipy` / `joblib` / `threadpoolctl` | Core6 source에 직접 요구 없음; sklearn의 버전별 전이 요구 | sklearn 등 선택 시 | 모두 미설치 | Core6 acc만을 위해 선제 설치하지 않음 |
| `nltk` / `langdetect` / `immutabledict` | ifeval extra: nltk >=3.9.1, 나머지 하한 미명시 | IFEval checker | 모두 미설치 | 이번 Core6 설치 문의 밖. NLTK resource 자동 다운로드도 별도 |
| vLLM·GPTQ·ONNX·task/dev/all extras | 개별 optional 목록 | 해당 엔진/과제를 선택할 때만 | 이번 감사의 실행 대상 아님 | 전부 제외 |

이 표의 앞 여섯 패키지는 **pyproject 기본 dependencies**다. 따라서 정상적인 resolver로 `lm_eval` 자체를 설치하면 그중 미설치 항목도 들어올 수 있다. runtime-only 설치를 하려면 의도적인 dependency 자동해결 제한과 누락 상태의 공개가 필요하며, 그것을 “공식 배포 요구 전체를 만족한 환경”이라 부를 수 없다. 실행 경로의 불필요와 package metadata 요구의 부재를 혼동하지 않는다. [내장 metric/fallback 경계](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/api/registry.py:741), [응답 캐시 lazy import](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/api/model.py:283)

## 7. 최소 후보도 전이 의존성을 포함해 문의해야 한다

공식 PyPI metadata만 읽어 다음 **설치 후보 버전**을 확인했다. wheel/패키지 파일 다운로드·해시 검증·설치·실행은 하지 않았다. 이 버전들이 성능/호환 검증을 통과했다는 뜻은 아니다.

| 직접 후보 | upstream 요구와 현재 조건 | 확인한 후보 | 필요한 새 전이 패키지 |
|---|---|---|---|
| `sacrebleu` | >=1.5.0; 후보 Python >=3.9 | 2.6.0 | portalocker, tabulate, colorama, lxml. numpy/regex는 기존 것 유지 |
| `pytablewriter` | upstream 자체 하한 없음; 후보 Python >=3.9 | 1.2.1 | DataProperty, mbstrdecoder, pathvalidate, tabledata, tcolorpy, typepy[datetime]와 그 chardet |
| `accelerate` — HF 때만 | >=0.26.0; 현 transformers 관련 조건 >=1.1.0; 후보 Python >=3.10 | 1.15.0 | 후보의 기본 요구 numpy/packaging/psutil/PyYAML/torch/huggingface-hub/safetensors는 metadata상 이미 있음 |

공식 근거: [sacrebleu 2.6.0 metadata](https://pypi.org/pypi/sacrebleu/2.6.0/json), [pytablewriter 1.2.1 metadata](https://pypi.org/pypi/pytablewriter/1.2.1/json), [accelerate 1.15.0 metadata](https://pypi.org/pypi/accelerate/1.15.0/json).

| 새 전이 패키지 | 부모의 제약 | Python3.10용 확인 후보 | 현재 metadata.version |
|---|---|---|---|
| portalocker | sacrebleu, 버전 하한 없음 | 4.4.1 (Python >=3.10) | 미설치 |
| tabulate | >=0.8.9 | 0.10.0 (Python >=3.10) | 미설치 |
| colorama | 하한 없음 | 0.4.6 | 미설치 |
| lxml | 하한 없음 | 6.1.3 | 미설치 |
| DataProperty | >=1.1.0,<2 | 1.1.1 | 미설치 |
| mbstrdecoder | >=1.0.0,<2 | 1.1.5 | 미설치 |
| pathvalidate | >=2.3.0,<4 | 3.3.1 | 미설치 |
| tabledata | >=1.3.1,<2 | 1.3.5 | 미설치 |
| tcolorpy | >=0.0.5,<1 | 0.1.7 | 미설치 |
| typepy[datetime] | **pytablewriter >=1.3.2,<2** | **1.3.5**. 최신 2.0.0은 이 제약에 불일치 | 미설치 |
| chardet | mbstrdecoder >=3.0.4,<7 | **6.0.0**, 7계열 제외 | 미설치 |

typepy datetime의 나머지는 python-dateutil 2.9.0.post0(<3), pytz 2026.3.post1, packaging 26.3으로 이미 metadata상 존재한다. Python/OS marker도 적용해야 하므로 Windows 전용 항목을 Linux에 자동 추가하지 않는다. [typepy 1.3.5의 정확 metadata](https://pypi.org/pypi/typepy/1.3.5/json), [chardet 6.0.0의 정확 metadata](https://pypi.org/pypi/chardet/6.0.0/json)

따라서 공식 CLI runtime-only 후보는 **직접 두 패키지 + 새 전이 11개 = 13개 외부 배포 패키지**, 여기에 고정 source의 `lm_eval` metadata 등록이 더해진다. HF를 선택하면 accelerate 1개가 추가된다. programmatic 결과 dict만 쓰면 pytablewriter 계열을 줄일 수 있지만, 표준 CLI 실행과 구분해야 한다. lxml 등의 정확 플랫폼 wheel 존재/용량/해시까지 아직 고정한 설치 영수증이 아니므로, 이것을 즉시 실행할 설치 명령으로 안내하지 않는다.

## 8. 설치 문의의 선택지와 권장 경계

| 안 | 실제 범위 | 장점 | 비용·위험 | 이번 상태 |
|---|---|---|---|---|
| A. source-only 유지 | 고정 archive/source/표만 확보 | 현재 승인 그대로, 환경 변경 0 | 공식 실행은 아직 불가 | **실제 수행안** |
| B. 선택 Core6 runtime-only | 정확 source 등록 + §7 최소 closure; HF면 accelerate만 조건부 추가 | 과제/엔진과 무관한 설치 최소화 | 기본 배포 dependency 일부 미충족 상태를 공개해야 함. 선택 경로 import/채점 검사 전 NOT_RUN | 별도 승인 필요 |
| C. 선택 도구의 선언된 base 요구도 전부 충족 | B 외에 §6 앞 여섯 기본 요구와 필요한 전이만 추가; HF extra 전체는 하지 않음 | package metadata와 공식 지원 범위가 더 잘 맞음 | Core6가 안 쓰는 평가 패키지·SciPy 등이 늘어남. task/all/dev/IFEval/BabyLM은 여전히 제외 | 별도 확대 선택 필요 |

**권장:** 지금은 A를 유지한다. 실제 평가를 준비할 때 총괄이 **사용할 백엔드·CLI/programmatic·설치 대상 환경과 B/C 중 범위**를 먼저 확정하고, 그 선택에서 부족한 필수와 전이 항목만 사용자에게 문의한다. B를 택하면 metadata 미충족 사실을 숨기지 않으며, C를 선택해도 `[hf]`, `[api]`, `[tasks]`, `[all]`, `[dev]` 일괄 설치로 확장하지 않는다. 기존 torch·transformers·datasets를 바꿀 필요가 입증되지 않았으므로 교체/업그레이드는 문의 대상에 자동 포함하지 않는다.

## 9. 실행 전 남는 별도 선결

1. source-only가 곧 import 가능은 아니다. `lm_eval` package metadata와 실제 읽는 code path가 **같은 고정 commit**인지 확인해야 한다. 다른 설치본 version만 빌려 원 source가 실행됐다고 주장하지 않는다.
2. 공식 `simple_evaluate()`는 종료 시 `get_git_commit_hash()`를 호출하며, 현재 source는 `git describe --always`를 subprocess로 실행한다. 총괄의 경계 확인에 따르면 이 읽기 조회 자체가 금지된 것은 아니고 staging/commit/push 등 상태 쓰기가 금지다. 다만 프로젝트 아래 archive에서 실행하면 TinyLM repo의 hash를 official harness hash로 잘못 남길 수 있다. **원본 source는 보존**하고, 승인된 별도 adapter/wrapper가 `framework_source_commit`·`framework_archive_sha256`·manifest 경로를 명시하며 자동 `git_hash`는 프로젝트 작업환경 provenance로만 구분하는 안을 권고한다. 보호 경로를 훑는 전체 git status는 하지 않는다. [실제 helper](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/loggers/utils.py:87)
3. GGUF는 서버의 native/OAI target 확률 의미·ID·BOS·joint encoding·post-sampling 여부·문맥 제한 canary가 선결이다. 다운로드한 weight magic이나 패키지 설치가 그 검증을 대신하지 않는다.
4. HF는 현재 transformers/datasets의 metadata 하한만 맞춘 상태다. 실제 모델·tokenizer·private 내부 API 호환과 TinyLM adapter는 아직 검증하지 않았다. 기존 입력/head/정밀도·full 선택지 우도와 task별 공식 분모를 맞춘다.
5. 데이터 취득 승인과 코드 소스 반입·패키지 설치·모델 평가 승인은 서로 다르다. 이번에는 source 반입만 실행했고, 평가 질문·정답은 학습 교사·Luna에게 전달하지 않았다.

이 문서는 읽기 전용 소스/metadata 감사와 승인된 소스 반입 기록이다. 공식 full Core6 점수·BabyLM 완료·품질 향상·설치 호환 PASS가 아니다.
