# A05 — Fresh SFT의 계측·mask·학습·생성 평가

우선순위: **P0** · 산출물 상태: **코드 작성/수동 검토용, 실행 미검증**

근거: [보고서 v2의 A05](../20260909_TinyLM_40MiB_연구타당성_및_실행조치_보고서_v2.md). 원본 코드·데이터·checkpoint 및 기존 보고서는 이 작업에서 수정하지 않았다.

### 적용 구조

`replacement/` **안의 내용**을 `Z:\TinyLM\`에 병합 복사한다. `scripts`, `tinylm`, `tests` 경로를 유지한다. `tinylm` 폴더 전체를 삭제·교체하는 뜻이 아니다. `original/`은 수정 전 원본 사본이며 적용 대상이 아니다. 상위 README와 manifest.json에 복사할 파일 및 원본/교체본 SHA가 있다.

아래 명령의 `$AuditCheckpoint`, `$AuditReferenceCheckpoint`, `$AuditTokenizer` 등 변수는 사용자가 실제 파일로 지정한다. 기본 native tokenizer의 현재 위치는 `data_cache\tok-ko-en-32768.json`이다. 명령은 적용 후 프로젝트 루트에서 사용자가 실행할 예시이며, 이번 작업에서 실행하지 않았다.

이미 준비된 Fresh train 1,000건/eval 300건을 실제 학습 가능한 경로에 연결한다. 기존 고밀도 원문 자료와 chat SFT를 같은 token 규모로 간주하지 않는다. 300 step/3% 같은 미검증 임계값을 성공 조건으로 강제하지 않는다.

### 코드 수정안

- 기존 `tinylm/chat/serialize.py`를 재사용하며 assistant 본문/종료 marker의 문자 span을 제공한다. thinking을 mask해도 입력 문자열은 유지한다.
- `supervision.py`가 계측과 학습의 공통 tokenizer/offset/shift/label mask를 만든다. prompt의 **직접 CE만 제외**한다. prompt 표현에 attention을 통한 gradient가 전달되는 것은 정상이다.
- role 경계를 가로지른 BPE token은 assistant-only 손실에서 제외하고 개수를 기록한다. 빈 assistant와 손실 token 0개는 실패다. 자동 특수토큰 추가를 끄고 serializer가 만든 문자열을 그대로 encode한다.
- 새 SFT는 packing을 사용하지 않는다. 오른쪽 padding의 label은 -100이며, 기본 길이 초과는 실패다. 명시적 truncate를 쓴 경우 잘린 수를 기록한다. packing 구현을 완료했다고 주장하지 않는다.
- 새 `train_sft.py`/`tinylm/train/sft.py`는 원본 pretraining trainer와 별도다. 가중치/cfg를 strict load하고 새 optimizer로 시작하며, 실제 loss token 합으로 accumulation을 정규화한다. 마지막 작은 batch도 같은 계약이다.
- `diag_dataset_tokens.py`의 미정의 tp를 수정하고 `--fields messages`/학습과 동일한 계측을 추가한다.
- `eval_sft.py`는 마지막 reference assistant를 prompt에서 제외한다. exact/명시적 요소/명시적 형식과 diagnostic-only를 분리하며, 잘림/skip을 저장한다.

### 가장 먼저 확인할 실제 자료 문제

원본 eval JSONL 11행(EVAL-000011)은 reference가 “미리내통이다.”인데 normalized_exact의 accepted_answers는 “미리내통”이다. NFKC/공백 정규화만으로 같아지지 않는다. 32행(EVAL-000032)은 “열 어절 이내 한 문장”을 요구하지만 format_constraints에는 sentence_count만 있다.

따라서 **원본 규칙으로 reference-only를 먼저 돌려 전체 불일치 목록을 얻는다.** 이 단계가 실패했다고 모델이 실패한 것은 아니다. 허용 답에 문장형을 추가할지, 정본 답을 짧은 형태로 바꿀지는 데이터 계약의 선택이다. 이 패키지는 원본 데이터나 허용 답을 몰래 완화하지 않는다.

검수한 수정은 별도 `--grading-overrides` JSON으로 적용할 수 있다. 각 ID에 `source_item_sha256`과 완전한 `grading` 사전을 넣는다. SHA는 I/O의 digest_json 규약으로 생성한 문항 SHA이며 reference-only 출력의 source_item_sha256을 그대로 쓴다. max_words/min_words도 지원한다. “이다/다 제거” 같은 전역 휴리스틱으로 원본 계약을 바꾸지 않는다.

### 수동 순서와 명령

```powershell
python scripts/diag_dataset_tokens.py --train datasets/TinyDataset/SFT/train/sft_fresh_v1_train_1000.canonical.jsonl --val datasets/TinyDataset/SFT/eval/sft_fresh_v1_eval_300.canonical.jsonl --tok "$AuditTokenizer" --fields messages --serializer chatml --seq 1024 --out-json runs/audit_20260909/A05_tokens.json
python scripts/eval_sft.py --eval datasets/TinyDataset/SFT/eval/sft_fresh_v1_eval_300.canonical.jsonl --reference-only --out-jsonl runs/audit_20260909/A05_reference_contract.jsonl
```

계측/채점 규약을 검수한 뒤 기존 B0를 동일 생성 평가로 기록한다. 다음은 **새 SFT 실행 예시**이며 이번 작업에서는 실행하지 않았다.

```powershell
python scripts/train_sft.py --checkpoint "$AuditCheckpoint" --train datasets/TinyDataset/SFT/train/sft_fresh_v1_train_1000.canonical.jsonl --tokenizer "$AuditTokenizer" --serializer chatml --seq 1024 --epochs 1 --micro-bs 1 --accum 4 --lr 0.00002 --optimizer adamw --ce-chunk 256 --out-dir runs/audit_20260909/A05_S1_seed1337
python scripts/eval_sft.py --eval datasets/TinyDataset/SFT/eval/sft_fresh_v1_eval_300.canonical.jsonl --checkpoint runs/audit_20260909/A05_S1_seed1337/model.pt --tokenizer "$AuditTokenizer" --serializer chatml --out-jsonl runs/audit_20260909/A05_S1_generation.jsonl
```

위 LR은 **시작용 제안값**이며 검증된 최적값이 아니다. 검수 override를 사용했다면 B0·reference·S1 모두 동일 파일과 hash를 써야 한다.

### 최소 비교와 적용 한계

| 팔 | 목적 |
|---|---|
| B0 | 같은 부모, 추가 학습 없음 |
| C0 | 필요할 때 같은 추가 노출/비용의 clean 원문 계속학습. `--format text --objective all` |
| S1/N_REF | Fresh 정본 assistant-only |
| S2 | 동일 accepted ID의 검증된 짧은 교사 답/이유. A13 |

첫 단계는 B0와 S1이며 C0는 계속학습 일반 효과를 주장할 때 필요하다. 사용자 방향과 다른 Bridge 팔을 필수로 만들지 않는다. 동일 step, 동일 loss token, 동일 총 시간은 서로 다른 비교이므로 별도 표에 기록한다. epochs를 늘리기 전 source family별 평가와 한국어/영어 유지 지표를 확인한다.

현재 구현은 native tokenizers JSON, 단일 장치, fresh optimizer, constant LR, no packing을 대상으로 한다. 재개·분산·기존 pretraining schedule 복원을 지원한다고 읽지 않는다. tokenizer ID 의미의 동일성은 vocab 크기 비교만으로 입증되지 않으므로 부모 tokenizer의 경로/해시를 확인한다.

1,000건은 메모리 내 토큰화한다. 큰 코퍼스로 확대할 때 RAM과 data loader 설계를 다시 확인한다. 13–14GB 가용 VRAM에서는 micro-bs=1부터 사용자가 probe하며, OOM을 이번 코드 작성으로 해결했다고 선언하지 않는다.

**인수 기준:** mask/shift/padding/경계/빈 답 테스트, 계측과 실제 update token 합 일치, reference grading 감사, 같은 기준의 B0/S1 생성·선택·clean bpb 결과. 모델 개선이나 40MiB 합격은 아직 미판정이다.

### 포함 파일

- `scripts/analyze_paired_records.py`
- `scripts/diag_dataset_tokens.py`
- `scripts/eval_sft.py`
- `scripts/train_sft.py`
- `tests/report_20260909/support_report.py`
- `tests/report_20260909/test_a05_supervision.py`
- `tinylm/audit_io.py`
- `tinylm/chat/serialize.py`
- `tinylm/chat/supervision.py`
- `tinylm/eval/audit_io.py`
- `tinylm/eval/model_adapter.py`
- `tinylm/eval/paired_records.py`
- `tinylm/eval/sft_grading.py`
- `tinylm/model/checkpoint_io.py`
- `tinylm/train/sft.py`

이 목록은 필요한 **새/교체 파일의 의존성까지 포함**한다. 다른 A 폴더와 겹치는 파일은 모두 ALL/replacement의 같은 버전이다. 원본 프로젝트의 나머지 모듈은 그대로 사용한다. 파일 생성·복사·해시 대조 외에 Python 실행, import, compile, 테스트, 학습, 평가를 수행하지 않았다. 테스트 파일의 존재는 PASS 증거가 아니다.
