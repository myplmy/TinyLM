# 작업 폴더의 추출 전 원문 탐색

사용자의 「직접 작업경로 내 폴더 탐색해보기 바람」 지시에 따라 읽기 전용으로 확인했다. 이 기록은 탐색 범위의 결과이며 저장소 전체에 원본이 없다는 단정이 아니다.

## 확인한 위치와 결과

| 위치 | 실제 관찰 | 복구에 사용할 원문 |
|---|---|---|
| `HF/datasets--wikimedia--wikipedia`, `HF/hub/datasets--wikimedia--wikipedia` | 각 5개 파일: README, refs/main, 빈 부재 표식 3개 | 본문 parquet/Arrow/XML/JSONL 없음 |
| `HF/datasets--HuggingFaceFW--fineweb-edu`, `HF/hub/datasets--HuggingFaceFW--fineweb-edu` | 각 5개 파일: README, refs/main, 빈 부재 표식 3개 | 본문 parquet/Arrow/XML/JSONL 없음 |
| `HF/datasets`의 해당 원천 이름 | 위키백과 20231101.ko와 FineWeb-edu sample-10BT의 lock 이름 확인 | 해당 원천의 Arrow 디렉터리는 확인하지 못함 |
| 허용된 native ko-en 캐시 | meta.json과 토큰화 train.bin/val.bin | 추출 전 위키텍스트·HTML·수식 원본은 확인하지 못함 |
| `article`, `util`, `proposal`, `review_request` | XML, parquet, Arrow, JSONL, HTML, WARC와 압축 원본 파일명 검색 결과 없음 | 위키 덤프 후보 없음 |

앞의 네 HF 위치는 링크를 외부로 따라가지 않는 재귀 메타데이터 조사로 총 20개 파일을 확인했다. 실제 파일별 관찰은 [LOCAL_SOURCE_LOCATION_SURVEY_V1.json](LOCAL_SOURCE_LOCATION_SURVEY_V1.json)에 기록했다. `article`의 TXT 후보 이름은 연구 자료와 코드 관련 파일이었으며 이를 위키 원문으로 간주하지 않았다. 평가 데이터의 사례 본문도 열지 않았다.

## 현재 준비 코드와의 대조

`tinylm/paths.py`는 기본 HF 위치를 프로젝트의 `HF/`, `HF/hub/`, `HF/datasets/`로 설정한다. `TINYLM_HF`로 달리 지정할 수도 있으므로 현재 기본 경로만으로 과거의 모든 저장 위치를 단정할 수 없다. 이 파일은 실행하지 않고 텍스트로 읽었다.

`tinylm/data/prepare.py`의 현재 ko-en 원천은 위키백과 20231101.ko와 FineWeb-edu sample-10BT이며, 관찰한 경로는 streaming 로드 → text의 토큰화 → train/val 배열 저장이다. 관찰한 배열 저장 지점에서는 추출 전 텍스트를 별도로 쓰지 않는다. 이는 현재 코드에 대한 관찰이며 과거 별도 덤프의 존재 여부를 증명하지 않는다.

따라서 이 범위에서는 이미 토큰화 과정 전에 빠진 수식·변수를 원본 대조로 복원할 파일을 찾지 못했다. 기존 native 토큰에서 원문을 다시 디코딩하는 것은 가능하지만, 그 토큰에 없는 수식까지 되살릴 수는 없다. 해당 직접 결손은 원형과 이유를 보존하고, 같은 자료의 완결된 설명·조건·서지는 계속 회수한다.

보호된 `datasets/TinyDataset/**`, 타 세션 전용 자료, 모델 가중치와 평가 사례는 탐색하지 않았다. 설치·다운로드·원본 변경·캐시 채택은 수행하지 않았다.
