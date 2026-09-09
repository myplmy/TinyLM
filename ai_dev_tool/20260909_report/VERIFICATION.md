# 작성·검증 기록

작성일: **2026-09-09**  
결과: **파일 패키징 완료 / 코드 실행 미검증 / 연구 실험 미수행**

## 실제 수행한 작업

원본 코드와 보고서 본문을 읽고, 보고서 v2의 A01–A15별 수정안·교체본·신규 코드를 작성했다. 쓰기와 복사는 `Z:\TinyLM\ai_dev_tool\20260909_report\` 아래에서만 수행했다. 원본 프로젝트에 교체본을 적용하지 않았다.

PowerShell의 파일 읽기·목록·복사·SHA-256 대조로 다음을 확인했다. 패키지에 작성한 Python과 CHECK_PACKAGE.ps1은 실행하지 않았다.

| 확인 항목 | 실제 확인 결과 |
|---|---:|
| 조치별 폴더 | A01–A15, 15개 |
| 코드 포함 / 문서만 | 12개 / 3개 |
| 통합 적용본 고유 Python 파일 | 48개 |
| 기존 파일 교체 / 신규 파일 | 13개 / 35개 |
| 개별 조치 적용본 사본 | 119개 |
| 개별+통합 적용본 해시 대조 | 167/167 일치 |
| 개별+통합 원본 사본 해시 대조 | 33/33 일치 |
| 교체 대상 원본 코드 | 13/13 기준 해시 유지 |
| 원본의 신규 코드 경로 | 35/35 생성되지 않음 |
| 그대로 사용하는 핵심 의존 파일 | 28/28 기준 해시 유지 |
| 기존 v1/v2 보고서 | 2/2 기준 해시 유지 |
| report 폴더의 Python 파일 실수량 | 200개 = 적용본 167 + 원본 사본 33 |
| A07/A12/A14의 파일 | 각 README.md만 있음 |
| 파일 대조에서 발견한 불일치 | 0개 |

원본 사본은 원래 파일 바이트를 그대로 복사했다. 교체본과 개별 조치의 공통 파일도 바이트 단위로 같다. 수정 시작 때 읽은 기존 전체 파일 중 보존본을 사용한 8개는 작성 후 원본을 다시 읽어 본문이 유지됨을 확인했다. 그 밖의 보존 확인 범위는 manifest에 기록된 파일 집합이다.

[manifest.json](manifest.json)은 고유 파일별 적용 조치, 신규/교체 구분, 코드 내부 패키지 의존성, 원본/교체본 SHA와 크기를 제공한다. [CHECK_PACKAGE.ps1](CHECK_PACKAGE.ps1)은 이 목록을 현재 파일과 대조할 수 있도록 **작성한** 도구다. 이번 결과는 해당 스크립트를 실행해서 얻은 결과가 아니다.

## 수동으로 검토한 구현 연결

- 원본의 cfg, MLP 그룹 소속, optimizer 파라미터 분할, canonical 대화와 serializer를 재사용했다. 새 도구가 다른 preset을 임의로 재구성하도록 만들지 않았다.
- 전 target bpb의 입력/target 위치와 실제 byte 분모, ID join 및 family 비교, assistant label shift/padding/경계, 실제 optimizer update 시점의 계측을 본문으로 검토했다.
- 각 조치의 import 대상이 신규/교체 파일이면 동일 버전의 의존 파일도 같은 replacement 폴더에 포함했다. 원본에 그대로 있는 supporting module은 manifest의 별도 기준 해시로 남겼다.
- 본학습 trainer/CLI와 Transformer/generation의 교체본은 해당 원본 전체 파일을 기준으로 변경했다. 전체 head는 기본값으로 유지하고 마지막 위치 head는 추론 선택 옵션으로 두었다.
- 원본 코드와 batch 참조를 검색하여 common_bpb의 SQUAD/load_squad_contexts import 및 LRM의 --tag 진입점을 보존했다. 다만 명령/점수 규약을 고친 도구의 옛 batch 전체 호환을 보장하지는 않는다.
- A05의 실제 채점 metadata 불일치와 A08의 Muon optimizer state 누락을 문서에 별도로 기록했다. 옛 정상 학습 전체의 무효 사유로 확대하지 않았다.

이는 source 검토다. Python parser, import 검사기, 정적 gate, unit test를 실행한 증거가 아니다.

## 작성한 회귀 테스트와 남은 인수 검증

회귀 테스트는 11개 모듈, 44개 테스트 메서드이며 전부 미실행이다.

| 조치 | 테스트에서 확인하도록 작성한 항목 | 상태 |
|---|---|---|
| A01 | 등록 버전, 두 schema, gold/중복 선택지, 4,500건 cache와 tamper | 미실행 |
| A02 | 문서 꼬리/UTF-8 byte/전 target, hash n-gram, 실제 제외, 여러 tokenizer 제외 합집합, byte 가중 비교 | 미실행 |
| A03/A04 | ID/skip join, 중복/누락 provenance, token CE 제약, margin, McNemar, family bootstrap | 미실행 |
| A05 | prompt/종료 marker, 여러 턴, thinking, BPE 경계, 빈 답/길이 초과, padding, 손실 token 가중 gradient, 채점 규약 | 미실행 |
| A06 | 공유 storage, plain tensor, 구/신 cache, cached answer NLL, 선택적 마지막 위치 head | 미실행 |
| A08 | 행렬 WD의 대상, 파라미터 중복, embedding/LRM WD 보존 | 미실행 |
| A09 | WD=0, skip/checkpoint 경계, 누락 history | 미실행 |
| A10 | 전체/tail/union의 causal null, 미래 위치 mass | 미실행 |
| A11 | 같은/반대 방향 tensor, 선두 compile prefix, 불균등 정본 그룹 | 미실행 |
| A13 | 마지막 정본 답을 교사 입력에서 제외, eval split 거절 | 미실행 |
| A15 | 반올림/실제 byte 차이, dtype 차이, 부호가 다른 0 | 미실행 |

다음 항목은 실제 실행 검증이 남아 있다.

1. 기존 TinyLM Python 환경에서 import/CLI·회귀 테스트와 필요한 저장소 정적 검사를 실행하는 것.
2. 실제 held-out/cache/tokenizer/checkpoint를 연결한 최소 평가가 새 결과 schema·coverage를 만드는지 확인하는 것.
3. A05 학습의 유효 loss-token 합과 실제 optimizer update, A08의 선택하지 않은 기본 경로 및 Muon save/resume를 확인하는 것.
4. 같은 seed·입력·checkpoint에서 A15의 실제 gradient/update 비교 결과를 얻는 것.
5. A06의 실제 저장 경로·대표 context에서 메모리/속도·cache 생성 일치를 측정하는 것. 현재 도구가 관찰하지 못하는 내부 CPU workspace는 별도 실행기 계측/상한 근거가 필요하다.
6. B0/S1 및 같은 ID의 N_REF/T_VERIFIED가 실제로 능력을 개선하고 원래 한국어/영어 품질을 유지하는지 검증하는 것.

합성 테스트가 나중에 통과하더라도 위 실제 모델 검증을 대신하지 않는다. 보고서의 연구 조치 번호는 이 코드 묶음 작성만으로 CLOSED나 실험 성공으로 바꾸지 않았다.

## 보존한 원본 코드 SHA-256

아래 파일을 원본에서 읽어 비교용 사본으로 복사했다. 실제 적용 코드 해시는 manifest에 있다.

| 원본 경로 | SHA-256 |
|---|---|
| `scripts/check_lr_factor_sync.py` | `5d49650114e788ee0a11e47b28c3c296d6d7b60f1dcaee65d81a7488c19dbcff` |
| `scripts/common_bpb.py` | `630e2e8af2e3754d7c61677cab430ab5159722d76b92a22c17d5b153fa0c7675` |
| `scripts/diag_attention_sink.py` | `9a4ec119afbd050a68970eac5fb1271aca0502e17d894832322f0c3f6920728c` |
| `scripts/diag_dataset_tokens.py` | `50db9befecb6c6c6207e9f884f0aaa7f67bc0ef7e444c8effea757861600df87` |
| `scripts/diag_group_agg.py` | `3a2fec5935465dd66553be5e13932ff10215139f551a4948ea7923796a1aff6d` |
| `scripts/diag_lrm_values.py` | `eb0dddc915b8698a4578327428e9b5d0899ccc3aac3ab2710a7b6df9541ccf43` |
| `scripts/eval_bench_suite.py` | `e612d6ca995a5b3c456cf92d697f1455f6bc91dff4925db3dad5505e35761f8f` |
| `scripts/fetch_bench_data.py` | `079829b8a8a259dd44f50cf71b44bfb3f0b4c53f140a8f7b7cdb995cfa51545b` |
| `tinylm/chat/serialize.py` | `f67f8db7760be9c1bae9102692c819e2444c8780a2906179c4c468451926d4c8` |
| `tinylm/cli.py` | `dcb09241cbcbff0cf99535ce39a1265b623ac909a84ae71a6cca42160a8d63e3` |
| `tinylm/infer/generate.py` | `5f6e2e2be41ab2d28526f868734a54ec3ed9d97b144a4bf8bef9f3f78bc2bde1` |
| `tinylm/model/transformer.py` | `9c3c1d62c17870c7fb5b7b38834f39c1681b168bafaee14fa1826650afa77d0f` |
| `tinylm/train/trainer.py` | `2f40c4ee6f21221ce3b505fce3341fd1ef37e6b09416f869e7531a192689cf35` |

기존 보고서 해시:

- v1: `920ed2a16a6d59d6667f2129e78b48edb93fd558e44da940f94f7cbf0df992a3`
- v2: `c942b073b27700b0c46400a2c3f06a18b3fff1bde97876c1fcd030f397b46242`

이 기록은 원본 보존·사본 일치와 미실행 범위를 남기기 위한 문서다.
