# A02 — 실제 오염 제외와 문서별 정확한 bpb

우선순위: **P0** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A02](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

기존 `--drop-contaminated`의 무동작과 floor chunk의 분모/꼬리 누락을 교정한다. 과거 348개 오염 문서의 ID 목록이 보존되어 있지 않으므로 숫자만으로 목록을 복원하지 않는다.

### 코드 수정안

- `build_bpb_exclusion.py`는 평가 문서의 모든 token n-gram을 명시한 train.bin 전체와 대조한다. 청크 경계도 읽고 hash 후보는 token tuple로 재확인한다.
- 제외 ID, 첫 일치 위치, 실제 train.bin/meta/tokenizer SHA, 전체 scan 범위를 새 manifest에 남긴다. 같은 corpus의 완성된 manifest만 평가기에 적용한다.
- `common_bpb.py`는 각 문서의 첫 target부터 마지막 target까지 정확히 한 번 채점한다. 미채점 prefix를 분리하고 실제 UTF-8 원문 byte 합을 분모로 쓴다.
- `analyze_paired_records.py --metric bpb`는 문서 평균의 차이가 아닌 합계 NLL/합계 byte의 차이를 문서 또는 family 단위로 bootstrap한다.

### 사용 예

```powershell
python scripts/build_bpb_exclusion.py --squad datasets/squad/train-v2.0.json --max-docs 4000 --train-bin data_cache/ko-en_600000000/train.bin --tokenizer "$AuditTokenizer" --ngram 13 --out runs/audit_20260909/A02_exclusion.json
python scripts/common_bpb.py --models candidate --checkpoint "candidate=$AuditCheckpoint" --tokenizer "candidate=$AuditTokenizer" --max-docs 4000 --drop-contaminated --contamination-manifest runs/audit_20260909/A02_exclusion.json --out-jsonl runs/audit_20260909/A02_candidate_bpb.jsonl
```

train.bin은 **비교 후보들이 실제 사용한 모든 학습 stream**으로 바꾼다. tokenizer가 다른 stream은 그 실제 tokenizer로 별도 scan해야 한다. 위 한 개 예시가 모든 기존 런을 포괄하는 것은 아니다. 같은 tokenizer로 학습한 여러 stream은 `--train-bin`에 함께 넣는다. 한국어 원문은 별도 id/text/language JSONL을 `--text-jsonl`로 지정한다.

서로 다른 tokenizer로 만든 manifest는 다음처럼 합친다.

```powershell
python scripts/merge_bpb_exclusions.py --manifests runs/audit_20260909/A02_native_exclusion.json runs/audit_20260909/A02_teacher_exclusion.json --max-docs 4000 --out runs/audit_20260909/A02_union_exclusion.json
```

모든 비교 모델에 **같은 합집합 manifest**를 적용한다. 이 도구는 corpus 순서/내용/건수와 scan 완료를 검증하고, 입력 manifest 전체와 파일 SHA를 보존한다. 단독 scan이나 합집합만으로 알려지지 않은 학습 stream을 무오염이라고 인증하지 않는다.

### 인수 기준과 해석

1. manifest와 평가 corpus의 hash/문서 수가 같고, 제외 전후 ID 차이가 실제 제외 목록과 일치해야 한다.
2. 짧은 문서와 마지막 불완전 청크도 target 수가 빠지지 않아야 한다. 합성 균등 모델에서 NLL이 token 수×ln(V), byte가 실제 UTF-8 길이와 일치하는 회귀 테스트를 제공했다.
3. tokenizer가 다르면 token CE 순위를 비교하지 않는다. 새 bpb도 고정 token 문맥창이 tokenizer별로 다른 원문 길이를 보므로 평가 규약을 명시한다.
4. 이 scanner는 **제공한 tokenizer와 stream에서의 어휘 중복**을 검사한다. 옛 cache가 생성 당시 tokenizer hash를 보존하지 않았다면 역사적 tokenizer 동일성은 로그/원장을 추가 확인해야 한다. 의미 중복·훈련에 쓰지 않은 다른 stream까지 무오염으로 인증하지 않는다.
5. 새 bpb는 기존 연결 스트림 bpb와 규약이 다르다. 옛 분해능 0.008이나 348/4,000을 자동 재사용하지 않는다. 최종 후보·KD 대조군의 동일 clean 평가부터 다시 수행한다.
6. `load_squad_contexts`/SQUAD import는 보존했다. 원본 dataset/cache를 수정하거나 새로 prepare하지 않는다.

### 포함 파일

- `scripts/analyze_paired_records.py`
- `scripts/build_bpb_exclusion.py`
- `scripts/common_bpb.py`
- `scripts/merge_bpb_exclusions.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a02_bpb.py`
- `tinylm/audit_io.py`
- `tinylm/eval/audit_io.py`
- `tinylm/eval/bpb_corpus.py`
- `tinylm/eval/model_adapter.py`
- `tinylm/eval/paired_records.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
