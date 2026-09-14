# TinyDataset SFT 버전 색인

- 갱신일자: 2026-09-15

이 디렉터리는 SFT 데이터 패키지의 저장 위치를 버전별로 분리한다.

| 디렉터리 | 의미 | 현재 저장 상태 |
|---|---|---|
| `v1/` | SFT용 Fresh 코퍼스 v1 파일럿 | 패키지 전체 보존 |
| `v2/` | SFT용 Fresh 코퍼스 v2 실패 draft | 감사·평가·문서 보존, 대용량 train·source ledger 제외 |
| `v2_r1/` | v2의 독립 revision1 | 감사·평가·문서 보존, 대용량 train·source ledger 제외 |

`v2_r1`은 저장 디렉터리명만 평탄화한 것이다. 레코드와 매니페스트의
`dataset_version=v2`, `package_revision=revision1` 의미는 바꾸지 않는다.

## 대용량 파일 보존 경계

2026-09-15 사용자 승인에 따라 GitHub 100 MB 제한을 넘거나 대용량 경고를 일으킨 다음
네 파일은 로컬 `main` 이력과 작업트리에서 제거했다.

- `v2/train/sft_fresh_v2_train.canonical.jsonl`
- `v2/sources/sft_fresh_v2_train_source_ledger.jsonl`
- `v2_r1/train/sft_fresh_v2_r1_train.canonical.jsonl`
- `v2_r1/sources/sft_fresh_v2_r1_train_source_ledger.jsonl`

따라서 v2와 v2_r1의 기존 감사·매니페스트에 기록된 레코드 수와 해시는 생성 당시
산출물의 증거이며, 현재 작업트리에 파일이 존재한다는 뜻이 아니다. 감사 JSON 안의 기존
절대경로도 생성 당시 provenance로 보존하며 현재 경로 라우팅에 사용하지 않는다.
