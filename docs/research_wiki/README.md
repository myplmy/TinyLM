# TinyLM 연구 위키

연구 계획, 검토, 계측 결과와 인계 기록을 원문 절까지 찾아가는 진입점이다.

- [P109 학습과 P077 문맥 연구](P109-P077.md)
- [방법론 적용 판정과 실제 실험 근거](방법론_적용_판정.md)
- [연구 작업폴더와 산출물 위치](작업폴더_안내.md)
- [실험 계획 목록](../../test_plan/실험계획목록.md)
- [결과 목록](../../test_result/실험목록.md)
- [판정·비교 기준](../EXPERIMENT_BASELINES.md)
- [연구 방향과 인계](../../handoff/COMPASS.md)
- [Codex 작업 절차](../../ai_dev_tool/Codex/README.md)

## 검색과 대조

저장소 루트의 WSL에서 Python 표준 라이브러리로 실행한다. 색인은 `runs/research_catalog/index.sqlite3`에 있다.

```bash
python3 -m scripts.research_catalog refresh
python3 -m scripts.research_catalog status
python3 -m scripts.research_catalog search 'p109c_early_course_share_chat32_v1_20261124' --kind result
python3 -m scripts.research_catalog search '한영대응 32,768쌍' --project P109
python3 -m scripts.research_catalog search --project P109 --claim DIRECT_PAIRED --dataset SAME_V11_VAL_AND_AUTHORED_16_SITUATIONS --tokenizer CHAT32_9716F40E
python3 -m scripts.research_catalog search --project P087 --origin '사용자 실행 보고' --preset 'P109C v3' --decision 미검토
python3 -m scripts.research_catalog search --preset 'P109C v3' --decision 적용
python3 -m scripts.research_catalog search '균등R2' --preset 'P109C v3' --decision 적용
python3 -m scripts.research_catalog related 'docs/research_wiki/P109-P077.md#p109-wiki-training'
python3 -m scripts.research_catalog show 'test_result/109_20261119004016_P109-기존G4-방문-세정책-실제갱신.md#p109c-raw-recovery-official-result-20261124' --lines 24
python3 -m scripts.research_catalog artifacts 'test_result/109_20261119004016_P109-기존G4-방문-세정책-실제갱신.md#p109c-integrated-v3-complete-20261124'
python3 -m scripts.research_catalog wiki P077
python3 -m scripts.research_catalog --json search '비겹침 표집 11.64%' --project P109
```

FTS5는 제목과 본문을 절 단위로 순위화한다. [등록한 별칭](ontology.json)과 접두어를 함께 찾아 한국어 조사와 띄어쓰기 차이를 보완한다. 정확한 경로나 문장 일부를 알고 있으면 `rg -F`도 곁들인다. 검색 결과에는 원문 경로와 앵커 또는 줄 번호가 표시된다. `갱신 필요`가 표시된 항목은 최신 원문을 먼저 확인하고 색인도 갱신한다.

`show`는 검색에서 찾은 `경로#앵커` 또는 `경로:줄번호`를 받아 현재 Markdown을 읽는다. 앵커의 줄이 이동해도 현재 파일에서 해당 절을 찾는다. 긴 절은 `--lines`로 읽을 분량을 조절하고 출력의 다음 줄 번호에서 이어 읽는다. `--json show`에는 원문 지문과 색인 최신 여부도 들어 있다.

`artifacts`는 같은 형식의 주소를 받아 해당 절이 직접 인용한 검산 JSON·원답·원로그의 로컬 경로와 인용한 줄, 파일 존재 여부를 보여 준다. 결과 증거, 인계 감사, 실행·스모크 로그의 텍스트 계열 링크를 대상 디렉터리 열거 없이 확인한다. 산출물 내용과 지문, 결과 판정은 해당 원문과 연결된 검산에서 확인한다.

`--claim`, `--dataset`, `--tokenizer`는 [기존 비교 조건 검증기](../../scripts/check_result_conditions.py)가 읽고 검증한 조건으로 조회를 제한한다. 평가셋과 토크나이저는 한 기록의 같은 비교군에 속해야 한다. 원래 비교에서 풀·초기화·채점 경로를 어떻게 통제했는지와 허용된 판정은 해당 원문 절에서 확인한다.

`--origin`, `--preset`, `--decision`은 한 절의 같은 판정 행에서 일치해야 한다. 이 필터와 함께 `--project`를 쓰면 그 방법론 절이 인용한 실험 번호도 찾는다. 예를 들어 P087을 조회하면 사용자 로그로 확인한 반복 노출과 P109C v3에서의 `미검토` 판정이 함께 나온다. `related 'docs/research_wiki/방법론_적용_판정.md#corpus-repeat-exposure'`로 계획·결과·원장 링크까지 따라갈 수 있다.

## 작성과 수정

1. 새 실험이나 결과를 쓸 때 계획·결과·작업원장 중 해당 사실을 소유한 문서를 먼저 갱신한다. 작업원장은 `scripts/wip.py`로 갱신한다.
2. 새 프리셋을 고르기 전에 같은 목적의 후보를 사용자 실행 기록과 GPT 주도 결과 양쪽에서 찾는다. 적용·유보·미검토 상태와 이유를 [방법론 적용 판정](방법론_적용_판정.md)에 적는다. 풀·초기화·학습량·채점 방식이 다르면 원문에서 조건과 한계를 확인하고 다음 판단에 필요한 검증을 남긴다.
3. 새 별칭은 같은 뜻을 가리키는지 확인한 뒤 [ontology.json](ontology.json)에 추가한다. 의미가 다른 판본이나 평가 경로는 각각의 이름을 쓴다.
4. 문서나 어휘를 갱신했으면 `refresh`를 실행하고 `search` 혹은 `related`로 찾을 수 있는지 확인한다.

색인의 원문 및 산출물 경로, 비교군과 판정 필터, 기존 색인 갱신과 실패 복구는 `python3 -m unittest scripts.test_research_catalog`로 검증할 수 있다.

## 색인의 책임 범위

| 항목 | 현재 동작 |
|---|---|
| 수집 범위 | 연구·방법·검토 문서, 계획과 결과 Markdown의 최상단, 공유 인계 문서, Codex 절차. |
| 관계 | 정본 경로·절, 파일명에 명시된 실험 번호, 검증기를 통과한 비교 조건, 방법론의 근거 출처·프리셋·판정, 색인 안 문서에 대한 인용 링크. |
| 갱신 | 원문 SHA-256을 함께 기록하고 SQLite 트랜잭션으로 새 스냅샷을 게시한다. |
| 저장 | 색인은 다시 만들 수 있는 파생 자료다. 데이터셋·체크포인트·원본 실험 로그는 수집 범위 밖이다. |
| 권한 | 도구가 새 사실을 추론하거나 원문에 대신 기록하지 않는다. 위키는 기존 저장소 검토 절차로 작성한다. |

반복되는 실제 질문에서 관계를 잇기 어렵거나 조건을 틀리게 섞는 사례가 남으면, 누락된 관계와 근거를 먼저 조사한다. 검증된 관계와 원문 검색을 결합한 차이로도 해결되지 않는 교차 문서 질문이 확인되면 온톨로지 고도화와 GraphRAG를 비교한다. 검토에는 독립 사례의 원문 인용 정확도, 한국어 조회, 갱신 비용을 함께 넣는다.
