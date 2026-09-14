# SFT용 Fresh 코퍼스 v2 revision1

> **현재 저장 경로:** `datasets/TinyDataset/SFT/v2_r1/`. 디렉터리만 평탄화했으며
> 레코드의 `dataset_version=v2`, `package_revision=revision1` 계약은 그대로다.
>
> **2026-09-15 저장 상태:** GitHub 대용량 제한 대응을 위해 사용자 승인 아래
> `train/sft_fresh_v2_r1_train.canonical.jsonl`과
> `sources/sft_fresh_v2_r1_train_source_ledger.jsonl`을 로컬 `main` 이력과 작업트리에서
> 제거했다. 아래 생성 수치와 매니페스트 해시는 생성 당시 증거이며, 현재 패키지를 곧바로
> 학습에 사용할 수 있다는 뜻이 아니다.

이 디렉터리는 `SFT/v2` 루트의 `SEMANTIC_SOURCE_FAMILY_AUDIT_FAIL` draft를 수정하거나
덮어쓰지 않고 새로 만드는 독립 revision이다.

핵심 추가 hard gate는 다음과 같다.

- 가공어 어간을 `<가공어>`로 치환한 train source의 정규화 고유 유형률 95% 이상
- 같은 정규화 source 유형의 train 최대 반복 2회 이하
- 정규화 source 유형의 train/eval 교집합 0
- 실제 의미로 정의한 `source_family`와 `situation_domain`의 train/eval 교집합 0
- source_family는 record ID를 포함하지 않고 `도메인×논리 원형×semantic task`로 구성

학습 문자열은 canonical record의 `messages`만 live `chatml` serializer로 직렬화한다.
GPU·모델 로드·학습·checkpoint·모델 평가는 이 패키지 작업 범위가 아니다.

## 현재 결과

- train: 23,760건, 실제 ChatML serialized token 10,025,284
- assistant body token: 3,846,663
- supervised-loss token: 4,012,983, 비율 40.0286%
- eval: 360건
- train 가공어 치환 후 정규화 source: 23,760/23,760 고유, 최대 반복 1
- train/eval 정규화 source·situation domain·source family·primary concept 교집합: 0
- held-out v2.8 및 ko-en 600M train pool exact 8-token 공유 유형: 각각 0
- 독립 정적 감사: `STATIC_AUDIT_PASS`, 위반 0

GPU·모델 로드·학습·checkpoint·모델 평가는 수행하지 않았다. 루트 평가기의 v2 T1
metadata choices 우도 채점 지원도 아직 확인되지 않아 `V2_T1_SCORER_PENDING`이다.
