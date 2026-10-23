# 2026-10-23 정 검토 — Gemma 복구, 기존 가속 경로와 재귀 근거

상태: `RESEARCH_REVIEW_AND_OPT_IN_SOURCE_PREPARED`. 처음 범위는 소스·설정·작은 JSON·공식 문헌 조회와 이 문서 신설이었다. 이후 총괄의 명시 할당으로 PAD 진단기·순수/mock 테스트 두 파일(§3.5), 공식 likelihood adapter·순수/mock 테스트 두 파일(§7)을 추가했다. 이 담당자의 모델·체크포인트 tensor·torch 로딩, GPU/학습, 설치, Git 변경, 원형 삭제·테스트 실행은 0회다. 총괄의 실제 실행은 별도 로그·결과 정본을 따른다.

근거의 소유자는 실제 코드, [결과053](../../test_result/053_20260822_P067-단계0a-두-최신-소형모델은-KV를-버리고-있다.md), [결과093](../../test_result/093_20260925_P102A-기능통과-T1-단일순서-속도관측.md), [결과066](../../test_result/066_20260831_P078-이득은-몰려있지만-어느-크롭인지는-재현되지-않는다.md), [결과091](../../test_result/091_20260923_P098-R2-초기임베딩-재주입은-3시드-실무-동급.md)과 아래 정확한 산출물이다. 본 문서는 표준 조건·정책을 새로 정의하는 계획서나 실험 결과 정본이 아니다. 첨부 작업지시서 전체와 Codex README/00/06, 정확 세션 WIP, 최신 유효 인계 및 기준표/COMPASS를 대조했다.

## 1. 총괄에게 먼저 전달한 판단

1. Gemma 학생의 학습 기록과 실제 CP는 **262,144행**이고, 실제 사용자 명령에 지정한 tokenizer JSON은 기본 BPE 262,144개에 **출력층 밖 이미지 전용 ID 한 개**를 더 갖는다. 총괄의 실제 재현에서 **262,144 대 262,145**가 확인됐다. 임의로 다른 tokenizer를 고른 오류나 가중치 부족으로 바로 결론낼 사안이 아니다.
2. 현재 assistant-turn MTP 경로에는 **유효 위치 gather, 출력층 checkpoint, 전체 optimizer update 기준 손실 분모**가 이미 있다. P102A loss-first/STE-update cache도 구현·작은 모델 동등성 검증 이력이 있다. CCE/Liger의 새 부분은 주로 **어휘 축 타일 계산·log-sum-exp 결합**이며, 기존 기능을 다시 구현한 성과로 세면 안 된다.
3. P078 고정 R2와 균형 방문 두 팔은 **704회 학습을 이미 완료한 보고서와 닫힌 activity**가 있다. 문서의 과거 NOT_RUN/진행 표시는 새 산출물보다 뒤처져 있다. 셔플 두 팔의 본학습과 별도 prefix router의 학습·효과는 이 완료에 포함되지 않는다.
4. 기존 공유 MLP, 반복 방문, attention 타잉, CLA, 첫 cycle KV 재사용, prefix 깊이 router는 서로 다른 축이다. 특히 기존 반복 방문은 같은 Layer 객체의 attention·MLP·norm·gate를 cycle 사이에 재사용한다. 이를 모두 “MLP만 반복” 또는 모두 “작은 Huginn core”라고 요약하면 실제 구조를 놓친다.

## 2. Gemma270M 학생의 어휘 오류

### 2.1 실제 사용자 호출과 오류 조건

총괄이 사용자에게서 확보한 명령은 다음과 같다. 이 담당자는 실행하지 않았다. 아래 로더 설명은 수정 전 오류 재현 시점의 소스를 대상으로 한다.

```bash
cd /home/uranus/tinyLM
./interactive_infer.sh --model m100R1c_ko-en_300M_G270Tfull.pt --tokenizer ./HF/models--google--gemma-3-1b-pt/snapshots/fcf18a2a879aab110ca39f8bffbccd5d49d8eb29/tokenizer.json --mode plain --device cuda --max-new 128
```

[셸 진입점](../../interactive_infer.sh)은 자신의 디렉터리로 이동하고 [공통 환경 선택기](../../scripts/shell/tinylm_env.sh)의 `tinylm_python`으로 실제 Python CLI에 인자를 그대로 전달한다. Python 선택 순서는 명시 `TINYLM_PYTHON`, 활성 `tlm_torch` conda 환경, 기존 로컬 `tlm_torch` 인터프리터다. `--tokenizer-hf`가 아니라 **`--tokenizer`로 정확한 JSON**을 받는다. 상대 tokenizer 경로도 셸이 이동한 저장소 루트 기준이다.

[실제 CLI](../../scripts/interactive_infer.py)의 `_load_runtime`은 선택 CP의 저장 cfg와 tokenizer SHA를 먼저 읽고, [dialogue.resolve_tokenizer](../../tinylm/infer/dialogue.py)로 명시 JSON을 고른다. 그 뒤 `resolve_mode`의 다음 검사에서 보고된 문구가 나온다.

```python
if tokenizer.get_vocab_size() != cfg["vocab_size"]:
    raise ValueError("체크포인트와 tokenizer 어휘 크기가 다릅니다.")
```

이 조건은 `--mode plain`에서도 먼저 적용되고 **`load_model`보다 앞**에 있다. 따라서 이 문구 자체는 strict state_dict 로딩의 shape mismatch가 아니다. 소스에서 같은 문구는 이 한 곳에서 발견됐다. 현재 기본 자동 후보인 `data_cache/tok-ko-en-262144.json`과 `...-chat32.json`은 없지만, 사용자가 정확한 HF JSON을 지정했으므로 그 부재가 이번 실제 호출의 직접 원인은 아니다.

### 2.2 학습 당시 학생·교사와 현재 JSON

[정확한 학습 JSON](../../runs/logs/m100R1c_ko-en_300M_G270Tfull.json)은 학생 tokenizer를 `gemma-3-1b-pt`의 아래 snapshot으로, 교사 모델만 `gemma-3-270m`으로 기록한다. 이는 파일명에서 추정한 내용이 아니라 실제 명령·로그의 구분이다. [결과053 §10](../../test_result/053_20260822_P067-단계0a-두-최신-소형모델은-KV를-버리고-있다.md)에도 같은 명령이 보존돼 있다.

| 항목 | 현재 직접 읽은 내용 | 증거 한계 |
|---|---|---|
| 학생 tokenizer | `HF/models--google--gemma-3-1b-pt/snapshots/fcf18a2a879aab110ca39f8bffbccd5d49d8eb29/tokenizer.json` | 실제 사용자 호출과 학습 JSON 일치 |
| 교사 | `HF/models--google--gemma-3-270m` | 교사 tokenizer라는 이유로 학생 tokenizer를 다시 고르지 않음 |
| 로그와 CP cfg vocabulary | 262,144 | 총괄의 CP metadata 실측 로그를 회수해 확인 |
| 학습 | 2,289회, micro2×accum64, seq1024, seed1337, skip0 | 300M draw 완료; 새 실행 아님 |
| 구조 | 20층, rank256, CLA2, attention group1, train_repeat1 | MLP g8 공유 프리셋; 재귀 R2로 학습한 CP가 아님 |
| 학습 wall | 33,181.9899초 | 교사 동시 학습 당시 값; 현재 추론 비용 아님 |

두 로컬 snapshot의 tokenizer JSON은 **같은 SHA256**이다.

`7d4046bf0505a327dd5a0abbb427ecd4fc82f99c2ceaa170bc61ecde12809b0c`

270M snapshot은 `9b0cfec892e2bc2afd938c98eabe4e4a7b1e0ca1`이다. 두 JSON과 `config.json`, `tokenizer_config.json`, `added_tokens.json`, `special_tokens_map.json`을 표준 JSON으로 읽었다. base vocabulary의 ID와 added-token ID 합집합을 직접 대조했다. 또한 [P067의 2026-08-29 실사 표](../../test_plan/P067_외부-토크나이저와-외부-교사.md)가 두 JSON의 MD5 앞12자리를 `379e7490d90f`로 기록하며, 현재 직접 계산한 두 MD5 `379e7490d90f6f801ccfd8dfc50f7ce4`가 이 역사 기록과 일치한다. CP에 저장된 tokenizer SHA가 있는 것과 동일한 강도의 인증은 아니지만, 경로명만 같은 것보다 직접적인 원형 연결이다.

| 비교 항목 | 값 | 의미 |
|---|---:|---|
| 두 외부 text 모델 config.vocab_size | 262,144 | next-token 출력 행 수의 config 근거 |
| JSON `model.vocab` 크기 | 262,144 | BPE 기본 ID 0..262143 |
| JSON `added_tokens` 항목 수 | 6,415 | 6,414개는 기존 기본 ID의 속성 선언 |
| 기본 범위 밖 추가 ID | 1개 | `<image_soft_token>` = 262144 |
| 기본·추가 ID 합집합 | 262,145 | ID 빈 구간 0개, 실제 max ID+1 = 262145 |
| `added_tokens.json` | 1항목 | 위 이미지 토큰 한 개만 존재 |
| BOS/EOS/PAD/UNK | 2 / 1 / 0 / 3 | normalizer·BPE ID 대응 보존 필요 |
| tokenizer 클래스 | `GemmaTokenizer` | tokenizer_config 메타데이터 값 |
| BOS/EOS 자동 추가 | BOS true / EOS false | JSON post-processor도 BOS2 삽입 |
| CP 입력 embedding 논리 행 수 | 262,144 | 총괄 실측 `emb.weight=[262144,256]` |
| CP 출력 head 논리 행 수 | 262,144 | 같은 tied table 사용; `emb_up.weight=[768,256]` |
| 실제 `tokenizer.get_vocab_size(False/True)` | 262,144 / 262,145 | 총괄이 실제 tokenizers API로 확인; JSON 산술과 일치 |
| `AutoTokenizer.vocab_size` / `len(tokenizer)` | 해당 고수준 API 미실행 | 실제 사용 `tokenizers.Tokenizer`에는 len API가 노출되지 않음 |

공백 normalizer는 공백을 `▁`로 바꾸고, BOS를 넣는 post-processor와 byte-fallback decoder를 가진다. `<image_soft_token>`은 현재 JSON에서 출력 행이 **없는** 추가 special ID다. 기본 범위 안의 `<unused...>` 예약 토큰들은 이 한 개와 다르므로 일괄 삭제하거나 행을 옮길 근거가 없다.

[hf_spec.load_hf_tokenizer](../../tinylm/hf_spec.py)는 원 JSON을 `Tokenizer.from_file`로 읽고 별도 토큰을 추가하지 않는다. [학습 trainer](../../tinylm/train/trainer.py)는 외부 어휘를 선택할 때 tokenizer의 added-token 총수 대신 `teacher_spec(kd_teacher_hf or tokenizer_hf).vocab_size`를 우선해 모델을 262144로 만든다. 평범한 text가 이미지 special ID를 쓰지 않으면 이 상태에서도 학습이 완료될 수 있다. 이는 학습 캐시의 모든 ID를 이번에 다시 읽었다는 뜻은 아니다.

### 2.3 최소 복구 선택지와 권장

| 안 | 내용 | 장점 | 위험·영향 | 수행비용 |
|---|---|---|---|---|
| A 권장 | 정확한 학습 tokenizer 정체성을 고정하고, 인증된 범위 밖 이미지 ID 한 개를 입력에서 거부하는 tokenizer view/검증 계약 | 원 JSON·가중치·0..262143 대응을 유지; 원인에 국소 대응 | 기본 ID mapping·normalizer·BOS/EOS의 일치와 실제 encoding 범위 검증 필요 | 낮음~중간; tokenizer·로더·입력 회귀 |
| B | 학습 당시 이미 존재한 별도 text-only tokenizer 산출물이 있으면 그 정확한 원본을 사용 | 원형 정체성이 남아 있으면 변환 불필요 | 그 산출물의 존재·hash는 아직 확인 안 됨; 새로 JSON을 재생성해 역사 원본이라고 부르면 안 됨 | 낮음~중간; 원형 탐색·동등성 확인 |
| C | CP resize 또는 토큰 행 삭제·재배열로 262145에 맞춤 | 단순 크기 검사만은 통과 가능 | 추가 행은 학습되지 않음; 가중치·ID 의미 변경, tied head 회귀와 원본 보존 부담 | 높음; 이번 원인에는 근거 부족 |

**A를 권장한다.** 무조건적인 크기 검사 삭제나 임의 tokenizer 허용이 아니라, 알려진 추가 special ID·정확한 매핑·허용 입력 대역을 확인하는 계약이어야 한다. BOS/EOS나 기본 reserved row를 임의로 옮기면 안 된다. 범위 밖 ID가 실제 prompt에서 발생하면 모델 호출 전에 명확히 거부한다. 출력은 이미 모델의 V행 안이지만 decode가 같은 ID 의미를 쓰는지도 확인한다.

수정 후 strict load의 missing/unexpected keys, 한영 인코딩·일반 생성·EOS 종료, 이미지 토큰 거부, 원본 CP SHA 보존은 총괄의 별도 실행 대상이다. 이후 회수한 실제 결과는 §2.5에 분리했다. **로딩 복구와 답변 품질은 서로 다른 판정**이다. 이 담당자는 원본 CP hash도 새로 계산하지 않았다.

### 2.4 총괄의 수정 전 실제 재현 회수

[정체성 실측 로그](../../test_result/053_log_20261023_P067_Stage4Wa_tokenizer_identity.txt)와 [오류 재현 로그](../../test_result/053_log_20261023_P067_Stage4Wa_tokenizer_mismatch_repro.txt)를 직접 읽었다. 이는 총괄의 실제 CP tensor/API 검사이며 이 담당자가 모델을 로드한 기록이 아니다. CP SHA256은 `0AC6D2E1F9378C1B10382EDD7205C0E82059B9649E124BA9F333056B40B144F0`, top-level key는 `model,opt,step,cfg`이며 저장 tokenizer SHA는 없다. 실제 CP cfg262144, embedding `[262144,256]`, projection `[768,256]`과 위 API 수가 확인됐다. base→full의 기존 ID 변경은0개이고 범위 밖은 special 이미지 ID 한 개뿐이다.

2026-10-23 05:45:49~05:45:55 KST에 같은 사용자 인자와 `--prompt '1+1은?'`로 실행해 **동일 문구·exit2**가 재현됐다. 이 호출은 CP cfg/tokenizer 확인 뒤 모델 구성 전에 멈췄다. CP metadata 검사는 model construction0/GPU0/CP쓰기0을 별도 기록했다. 원인은 이제 단순 추정이 아니라 **추론기의 총 tokenizer 수 검사와 실제 text 모델 출력 범위의 불일치**로 확인됐다. 이 재현 시점에는 수정 후 동작이 미실행이었고 이후 실행은 다음 절로 분리한다. CP에 역사 tokenizer SHA가 없다는 한계는 계속 유지한다.

### 2.5 총괄의 최소 수리 뒤 실제 답변 회수

[수정 후 원로그](../../test_result/053_log_20261023_P067_Stage4Wb_tokenizer_recovery_055539.txt) 전체와 [결과053 §13](../../test_result/053_20260822_P067-단계0a-두-최신-소형모델은-KV를-버리고-있다.md)을 직접 읽었다. 총괄은 기본 strict 검사를 유지하고 `--allow-extra-special-tokens`를 명시할 때만 범위 호환을 허용했다. 같은 원 CP·원 tokenizer, plain·greedy·FP32 MATH·cache ON·독립 첫답·max128·MTP 추론OFF에서 05:55:39~05:56:26 KST에 네 문장과 별도 이미지 토큰 거부를 순차 실행했다.

네 실제 답은 `1+1은?`에19 반복, 한국 수도에창원 관련 반복, France 수도에질문 자체 반복, `Two plus three equals`에12와 문장 반복이었다. 네 호출은 모두 생성128/MAX_NEW에 도달했고 요청한2/서울/Paris/5를 답하지 못했다. 이미지 ID 입력은 모델 sampling 전에 명시 오류·exit2로 거부됐다. 결과 정본은 실행 후 CP SHA 불변도 기록했다. **텍스트 로딩 계약은 복구됐으나 답변 품질은 복구되지 않았다.** 공개 네 문장의 직접 판독이며 blind benchmark나 전체 증류 불가능성의 증거는 아니다.

## 3. 현재 출력 손실·가속 경로

### 3.1 이미 있는 것과 남은 것

| 경로 | 직접 확인한 동작 | 새 개선으로 집계하면 안 되는 것 | 실제 남은 공백 |
|---|---|---|---|
| 일반 `trainer` / 기존 `train_sft_p090.loss_sum` | `model(x)`의 전체 logits를 만든 뒤 row CE 청킹 | CE 청크·FP32 임시 cast 제한 | full logits 자체의 상주·gradient 저장 |
| [mtp_sft.components](../../tinylm/train/mtp_sft.py) | assistant 유효 위치 hidden을 먼저 gather; NTP/MTP 각 head를 위치 청크로 계산; 기본 head checkpoint | 유효 위치 gather·head 재계산·assistant mask | 어휘 축 전체 GEMM/LSE·head 밖 Python/동기화 비용 |
| [P101A 엔진](../../scripts/diag_p101a_sft_mtp.py) | compiled backbone + 별도 base head, m8×a16, 고정 폭1024 | compile·trunk checkpoint·Muon RMS4 | 같은 update/micro membership의 PAD 폭 축소 등 |
| [P078 업데이트](../../scripts/p078_route_training.py) | 같은 `components` 재사용, head 보조 없음, eager, route를 16 micro와 backward 동안 고정 | 방문별 학습·유효 위치 CE·whole-update 분모 | 새 가속의 route·checkpoint 호환성 |
| [P102A loss-first](../../tinylm/train/p102a_contract.py) / trainer opt-in | factorized `h→r→V`를 row 청크로 계산하고 backward에서 재계산하는 custom autograd | loss-first가 완전 미구현이라는 주장 | chat32·BF16·compile·KD 등 현재 목표 조합의 통합/검증 |
| [Muon](../../tinylm/train/muon.py) | 2D 비embedding 행렬의 NS 직교화, momentum, RMS/Jordan 스케일 분리 | Muon 또는 RMS4를 새 NorMuon으로 재명명 | NorMuon/AdaMuon 고유 업데이트·state·group 규약 비교 |

정확 단어·API 검색에서 로컬 CCE/Liger 패키지를 호출하는 새 통합은 발견하지 못했다. P102A 모듈 표제의 “default trainer integration 없음”을 읽고 opt-in 구현까지 없다고 결론내리면 틀린다. `trainer.py`의 `loss_first` 분기와 CLI가 이미 존재한다. 다만 fresh dense FP32-head에 한정하며 compile/KD/chat32_tokenizer/ce_chunk/resume 조합 등을 거부한다. 그 플래그만 현재 chat32 실행에 붙일 수 없다.

[결과093 §2~3](../../test_result/093_20260925_P102A-기능통과-T1-단일순서-속도관측.md)의 소형 모델 loss/gradient/SGD update 동등성은 재사용할 증거다. CUDA BF16·최대 VRAM·전체 step 가속은 그 증거가 아니다. 같은 결과의 T1 eval/save 감소는 후속 ABBA에서 전체 wall 이득의 방향이 재현되지 않아 기본 채택이 보류됐다. 단일 순서의 1.9%를 새 가속 보장치로 쓰지 않는다.

### 3.2 보존해야 할 실제 손실 계약

`encode_record`는 이미 `x=ids[:-1]`, `y=labels[1:]`, `segments=owner[1:]`를 만든다. **추가 shift=1을 다시 적용하면 다음 토큰이 아니라 두 칸 뒤를 학습한다.** CCE의 자동 shift 예시를 그대로 복사하면 안 된다.

각 optimizer update의 분모는 128개 실제 record 전체에서 센 horizon별 유효 수 `D_h`다. 각 micro의 loss **sum**을 같은 `D_h`로 나눈 뒤 누적한다. micro마다 CE mean을 낸 뒤 16으로 나누면 짧은 답과 긴 답의 가중치가 바뀐다. 모든 assistant label이 무시되는 micro도 있을 수 있어 전체 update의 유효 수와 구분해야 한다.

`horizon_targets`는 y가 이미 shifted라는 전제에서 hidden[t]가 raw[t+h]를 예측하게 하며, 그 사이 모든 label이 유효하고 동일한 양의 assistant owner인 창만 허용한다. EOT는 유효 target이고 다음 역할/다음 assistant turn은 넘어가지 않는다. assistant owner와 CLA KV owner는 다른 ID 체계다.

입력 embedding과 출력 vocabulary table은 **같은 `emb.weight`**, 입력 up-projection과 주 head projection도 **같은 `emb_up.weight`**를 쓴다. 새 fused loss는 출력 경로 gradient만 반환해도 충분하다고 가정하지 말고 입력 경로 gradient와 autograd가 같은 parameter에 합치는지 확인해야 한다. auxiliary MTP projection은 별도이고 vocabulary table은 공유한다. `detach`, 새 classifier parameter 복제, 사후 gradient 대입은 tied gradient를 지울 수 있다.

현재 학습 head의 `_emb_w()`는 계산 dtype accessor이며, 배포 시 삼진 table/packed lookup을 쓰는 사실과 학습 때 FP32 latent table을 최적화하는 사실을 섞지 않는다. fused 통합의 국소 표현은 `z=F.linear(hidden_keep, model._emb_up_w().t())` 뒤에 같은 `model._emb_w()`를 classifier로 전달하고 이미 shifted target의 loss sum을 기존 분모로 나누는 것이다. 여기서 임의로 새 삼진 classifier를 만들면 fused만 바꾸는 대조가 아니다. `split_params`는 `nn.Embedding`을 Muon에서 제외하므로 `emb.weight`는 Adam, 2D `emb_up.weight`는 Muon 소유다. 기존 본체 quantization STE의 gradient와 한 번의 clip/step도 보존 대상이다.

### 3.3 가속 후보 세 가지

| 안 | 내용 | 장점 | 위험·영향 | 수행비용 |
|---|---|---|---|---|
| A | 같은 ordered128와 ordered16×8를 유지한 오른쪽 PAD 폭 축소 | 기존 helper 재사용; 실제 prefix·마스크를 보존할 국소 변화 | GEMM/SDPA 형상·compile graph·수치 차이; 최악 micro peak는 남을 수 있음 | 낮음~중간; 합성/실제 동등성 뒤 비용 측정 |
| B 권장하는 새 head 후보 | 기존 valid gather 뒤 factorized projection을 유지하고 CCE/Liger 계열을 마지막 `r→V`에 연결 | 전체 어휘 logits 저장과 CE 중간 비용 감소 여지; 248K 확장과도 연결 | tied gradient·BF16·version·KD 확률·per-token upstream·head checkpoint 중복 재계산 | 중간; 손실·전 gradient·한 update·독립 속도 비교 필요 |
| C | NorMuon/AdaMuon 또는 progressive context/MNTP 등 목적·최적화 규칙 변경 | 데이터 효율까지 개선할 가능성 | 기존 손실/구조 효과와 교락; optimizer state 또는 학습 objective 변경 | 높음; 별도 통제와 품질까지의 시간 비교 |

총괄은 먼저 기존 완료 작업을 닫고 **A의 기존 감사·helper와 B의 새 어휘 계산 부분을 별도 후보로** 다루는 것이 합리적이다. B는 사용자 최우선 fused output-head 요청에 맞는 새로운 비교이고, A는 병행 가능한 국소 시스템 후보다. 아직 순수 GPU 속도가 확인되지 않았으므로 어느 쪽도 자동 채택하지 않는다. C는 같은 초기화·자료·목적을 고정한 시스템 가속이 확인된 뒤 독립 비교가 명확하다.

[전일 PAD 감사](20261022_padding_efficiency_audit.md)는 고정1024 대비 32/64/128배수 폭의 slot 절감과 경계를 이미 정리했다. slot 비율을 실제 가속으로 재보고하지 않는다. `pad_records(fixed_width=None)`도 이미 존재한다. 이번 새 기능은 helper 복제가 아니라 폭 정책·실제 동등성·전체 비용을 확인하는 부분이다.

### 3.4 공식 fused CE의 적용 조건

[CCE 공식 README](https://github.com/apple-aiml-research/ml-cross-entropy)는 vocab 방향 GEMM과 log-sum-exp를 결합해 전체 logits를 보관하지 않는 경로를 설명한다. gradient filtering을 양쪽 모두 끄는 `cce_exact`도 제공한다. 첫 동등성 비교에는 이 명시 경로가 적합하며 기본 CCE의 필터링 이득과 분리한다. 자동 shift는 이 저장소의 이미 shifted label과 중복 적용하지 않는다. 이 내용은 공식 README 직접 확인이며 TinyLM 실행 증거는 아니다.

[Liger 공식 fused CE 소스](https://github.com/linkedin/Liger-Kernel/blob/main/src/liger_kernel/ops/fused_linear_cross_entropy.py)의 현재 main은 `reduction="none"`에서 per-token upstream gradient를 logits gradient에 곱한 뒤 weight gradient를 합치도록 backward 재계산을 분리한다. 축약된 dW에 토큰별 가중치를 뒤늦게 곱해서는 같은 결과를 만들 수 없기 때문이다. 같은 파일에 예전 “none 미지원” 주석도 남아 있어 버전·실제 코드를 고정해야 한다. scalar mean/sum 성능과 none 재계산 비용이 같다고 가정하지 않는다.

ALM/ACTD·adaptive masking에 필요한 per-token 확률·LSE·top-k·잔여 질량을 scalar CE 하나가 자동 제공하지 않는다. CE 경로와 KD 확률 경로를 분리하거나 필요한 충분통계만 구하는 명시 API가 필요하다. full-vocabulary KL을 CCE 도입의 자동 효과로 보고하지 않는다. 공식 대형 모델/다중 GPU의 메모리·속도 배수를 이 로컬 V32K·r256 학생에 그대로 적용하지 않는다.

### 3.5 추가 승인된 PAD 실물 진단기 준비

총괄의 [사전 결정](20261023_execution_decisions.md)과 [P101A Stage3n0W/3nW](../../test_plan/P101A_M0-U2-QK-MTP-기능계약.md)에 따라 신규 [진단기](../../scripts/diag_p101a_padding_gpu.py)와 [순수/mock 회귀](../../scripts/test_p101a_padding_gpu.py)만 작성한 뒤 동결해 전달했다. 기존 학습 함수·모델·CPU 회귀·원 V3·cache는 고치지 않았다. helper 재구현이 아니라 원 `engine.load_runtime(parent_ntp)`, `clean.encoded`, `pad_records`, sampler와 optimizer factory를 재사용하는 별도 관측 도구다.

정확성은 실제 부모·FP32 MATH·CLA2·checkpointON에서 같은 ordered128/16×8의 첫 update를 두 폭 정책으로 각각 한 번 실행하도록 설계했다. 원 CPU 초기 상태로 팔마다 새 모델/optimizer/RNG를 구성하고 GPU 모델 둘을 함께 두지 않는다. 모든 raw gradient·같은 clip/AdamW+Muon update·optimizer state를 CPU 정본으로 비교하며 tied `emb.weight`와 `emb_up.weight`의 입력+출력 합산 기울기를 포함한다. 기존 관련 회귀의 허용값을 AST로 읽어 미보정 GPU 진단에 적용하고 CPU FP64는 통계 계산에만 사용한다. 실패는 exit9/음성으로 남기며 허용치를 바꾸지 않는다.

시간 진단은 같은 원 V3(보고 SHA `7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20`)를 사용하되 알려진192/198첫턴·669둘째턴 결함을 **비채택 noisy control**로 표시한다. BF16 eager·MTPoff·compileoff, fixed1024/crop128/crop128/fixed1024 네 독립 초기화 블록에서 매번 같은 첫2 warmup와 다음4 measured update, 총24 임시 update다. 실제 입력/target/PAD·전체 update·단계 시간·peak를 따로 남긴다. 원문·target·전체-update 분모·업데이트 안의 micro 순서와 optimizer 규칙은 바꾸지 않는다.

실행은 명시 `--execute`, 소스 SHA, aware deadline(23일16:30 KST 이내), 최대1200초, 새 exact evidence 경로를 요구한다. 소스 전용 `--check-only`는 자산·torch·모델·GPU를 열지 않는다. 본 실행은 import부터 내부 wall bound와 매 micro 절대시각을 확인하고, write-once/20MB/부분 event 보존·끝의 소스/CP/tokenizer/corpus SHA 불변을 확인한다. 총괄의 OS outer timeout과 `-B` 실행이 별도 보호다. CP 저장·품질/compile 개선 주장은0이다.

총괄은 동결 전 두 파일 전체를 읽고 신규18 mock 회귀 PASS를 보고했다. 이 담당자가 실행한 것이 아니며, 그 뒤 마지막 안전 보강이 포함된 소스를 총괄이 다시 고정·검증해야 한다. 실제 부모 정확성/ABBA 결과는 이 문서에서 아직 읽거나 PASS로 서명하지 않았다. 완료 상태는 소스 준비와 총괄 인계이고, 모델·속도 검증 완료가 아니다.

## 4. 기존 공유·재귀 구조와 실제 결과

### 4.1 구조 구분

| 축 | 실제 코드/설정 | 이 코드가 뜻하는 것 | 뜻하지 않는 것 |
|---|---|---|---|
| MLP 층간 공유 | `mid_mlps`, `mlp_group_index`, `tie_mlp` | 여러 논리 층이 같은 MLP를 참조 | attention/norm/KV까지 모두 공유 |
| attention 층간 공유 | `attn_group>1`, `mid_attns` | 여러 논리 층의 attention module 공유 | CLA 또는 반복 cycle의 cache 공유와 동일 |
| 반복 방문 | `_repeat_schedule` / `visit_schedule` | 같은 middle Layer 객체를 여러 번 통과하므로 cycle 사이 해당 attention/MLP/norm/gate 재사용 | 새 2층 core를 학습한 Huginn와 동일한 고유 깊이·상태 설계 |
| CLA | `self.owner`와 owner-first 계산 | 인접 소비 층이 owner의 K/V 사용 | 반복 cycle의 K/V까지 하나로 합침 |
| 정확 반복 KV | 기본 `(owner, pass)` key | cycle별 갱신 표현으로 K/V를 별도 계산·저장 | 파라미터 공유만으로 KV가 공짜 |
| 기존 KV 재사용 | `repeat_kv_reuse=True` | 반복 시 첫 cycle K/V 재사용 | 새 terminal-state 근사와 같은 알고리즘 |
| 기존 mode router | `n_modes>1`의 token별 softmax | mode-conditioned 연산의 혼합 | R1/R2/R3 깊이를 고르는 prefix router |
| P078 prefix router | 별도 `p078_prefix_router.py` | 미래 정답 없는 frozen embedding 통계로 R1/2/3 상대 CE 예측 | 정답 검증기·완전한 관계 reasoning |

`m100R1c`는 [프리셋](../../tinylm/config.py)상 2+16+2, dim768/FFN2048, MLP g8 공유, rank256, CLA2, attention group1이다. 이번 Gemma 학습 로그는 train_repeat1이다. 같은 이름을 recurrent R2 학생으로 취급하지 않는다.

기존 R2+ 방문은 `Layer` 객체 전체를 cycle 사이 재사용하지만 논리 core 층 안에는 독립 attention/norm/gate가 남는다. 따라서 compact core2·R8과 같은 외부 후보의 파라미터 산술을 16층 middle 공유 MLP 모델에 대입할 수 없다. embedding 재주입의 현재 덧셈 구현과 concat+adapter, orthogonal injection, 학습 scalar mixing도 서로 다르다.

[P070B 원자 스케줄](../../scripts/p070b_cla_routes.py)은 **CLA owner→consumer 그룹 안 순서를 유지한 채** middle 그룹을 reverse/shuffle한다. 무작위 token 순서나 개별 층 무제약 셔플이 아니다. [P078](../../scripts/p078_route_training.py)은 route를 update/forward/backward 전체에서 고정하고 session/model/receipt와 cache를 묶는다. `learned_router()` stub만 읽고 prefix router 전체가 없다고 결론내리면 안 된다. 구현은 [별도 helper](../../scripts/p078_prefix_router.py)와 [driver](../../scripts/diag_p078_prefix_router.py)에 있다.

### 4.2 재사용할 기존 결과와 실패의 범위

| 기존 근거 | 실제 관측 | 재사용할 판단 | 확대하면 안 되는 결론 |
|---|---|---|---|
| 기준표 B.27 / 결과047 | 고정 상주에서는 재귀, 같은 방문 예산에서는 깊이가 유리한 조건 존재 | 상주·지연·품질 예산을 따로 고정 | 재귀 또는 깊이의 전 조건 보편 우열 |
| [결과062](../../test_result/062_20260830_P077-KV재사용은-재귀이득의-5.4배를-먹는다-기각.md) | 고정 CP의 첫-cycle KV 재사용으로 full-val CE +0.0591~+0.0928 | 이 기존 추론 근사의 큰 대가 보존 | 새 상태 설계·재학습 terminal KV 전부 불가능 |
| [결과065](../../test_result/065_20260831_P077-bf16-KV-는-정확히-절반이고-cla2-재귀가-32MiB-예산에-들어왔다.md) | KV dtype을 줄이면 저장 bytes 감소; logits는 bit동일 아님 | cache 엔트리 수와 엔트리 bytes 분리 | 생성 품질·현 WSL RSS·새 GPU 속도 보장 |
| P078 옛 crop 선택 | 몸통 간 이득 r²0.7%, 시드 쌍 약4.3/5.9%; 공유 기준·일부 ckpt 조건차 존재 | 그 계기·특징의 낮은 재현성과 기존 종결 유지 | 모든 미래 prefix 특징의 엄밀한 설명력 상한6% |
| [P098 결과091](../../test_result/091_20260923_P098-R2-초기임베딩-재주입은-3시드-실무-동급.md) | 단순 덧셈 재주입 off−on +0.0015/+0.0001/+0.0002, 모두 당시 재귀 자0.0018 안 | 단순 덧셈은 default-off; 3시드 결과 재사용 | injection 미구현 또는 모든 injection 변형 실패 |
| P070B 결과105 §9~10 | CPU reverse R2의 한 logit 문턱 음성; 같은 길이 cache flag만 바꾸면 bit동일, 길이만 바꿔도 차이 재현 | 원래 음성 보존; 해당 차이를 입력 길이/연산 형상으로 좁힘 | 전체 긴 문맥·모든 route·GPU cache PASS 또는 재귀 구조 실패 |

기준표 B.29.2의 “재주입·무작위 횟수 없음”은 역사 상태다. 현재 P098 재주입 구현·완료와 P078 균형 방문 구현·실행을 확인했으므로 이를 새 미구현 목록으로 복사하지 않는다. 옛 결과066의 낮은 재현성은 관측 근거이지만, 제한된 상관만으로 새 입력 특징의 수학적 상한까지 증명한 것으로 사용하지 않는다.

### 4.3 P078 본704 두 팔의 새 실물 상태

다음 정확한 두 보고서와 대응 activity JSON을 직접 읽었다. CP tensor를 열거나 CP hash를 새로 계산하지 않았다. 아래 CP SHA는 보고서가 소유하는 값이며 실제 바이트는 총괄 strict loader의 검사 대상이다.

| 항목 | uniform R2 | balanced count |
|---|---|---|
| [보고서](../../test_result/evidence/p078_route_training_v1_s1337_cleanv3/train_uniform_r2/report.json) / [보고서](../../test_result/evidence/p078_route_training_v1_s1337_cleanv3/train_balanced_count/report.json) 상태 | `ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED` | 같음 |
| [activity](../../test_result/evidence/p078_route_training_v1_s1337_cleanv3/activity_train_uniform_r2.json) / [activity](../../test_result/evidence/p078_route_training_v1_s1337_cleanv3/activity_train_balanced_count.json) | complete true / returncode0 | complete true / returncode0 |
| optimizer updates | 704 | 704 |
| 실제 입력 / 지도 target | 21,621,776 / 2,210,436 | 같음 |
| padded slots / layer-visit slots | 92,274,688 / 2,214,592,512 | 같음 |
| CP 쓰기 | 1개 | 1개 |
| 저장 CP SHA 앞부분 | `0E330A5FF1C22875…` | `A9CA3B99EABCC08C…` |
| activity perf / UTC 초 | 3701.611 / 4046.553 | 3680.210 / 4037.419 |
| peak allocated / reserved MiB | 2774.103 / 2922 | 2972.618 / 3126 |
| grad_max | 5.894257 | 31.166595 |
| matched-policy VAL512 CE | 2.667775 | 2.650580 |
| 같은 uniform route의 secondary CE | 2.667775 | 2.618870 |
| epoch1→epoch4 matched VAL CE | 2.210307→2.667775 | 2.291023→2.650580 |

공통 구조는 P090B 부모 14층(2+10+2) **dense MLP**, dim768/FFN2048/r256, attention group1, CLA2, chat32 V32768이다. R1/R2/R3은 각각 14/24/34층 방문이다. fixed R2와 균형 R1/2/2/3은 전체 방문 슬롯 평균을 맞췄지만 최대 R3 peak나 세부 FLOPs까지 동일하다고 뜻하지 않는다. 학습은 기존 eager·checkpoint-on·BF16, 평가는 FP32 MATH로 구분한다. 각 VAL은 512행/2977 assistant targets다.

stored `final_answers`의 8문항을 직접 읽으면 uniform은 **‘별빛’ 복사와 red-box ‘Yes’**만 요청 내용·형식에 부합하고, balanced는 **‘별빛’**만 부합한다. 산술 두 문항은 두 팔 모두 틀렸고, Earth가 포함된 장문은 one-word 요청을 충족하지 않는다. 이는 이 담당자가 명시된 8개 요청을 읽은 진단이며 공식 일반대화 점수가 아니다. 원 `semantic_score`는 모두 null로 남아 있다. 종료는 uniform6/8·balanced7/8로 좋아 보일 수 있으나 정답과 다르다.

VAL의 epoch1 이후 상승은 실제 보고서에 있는 관측이다. 학습률·early stopping·마스크 원인 중 무엇 때문인지는 이 읽기만으로 확정하지 않는다. 새 baseline 평가 경로와 개입 실험을 섞지 말고 이 원답과 학습 이력을 먼저 정본에 회수한다.

`fixed_shuffle_r2`와 `update_shuffle_r2`의 train 보고서는 같은 namespace에 없다. 두 완료 팔을 네 팔 전체 연구 완료로 승격하지 않는다. prefix router의 별도 실제 labels/head/TEST 완료도 아직 이 담당자가 확인하지 못했다. router source의 `relative_ce_mse`는 깊이 선택 head의 목적이며, ALM을 임의 log-prob MSE로 구현해도 된다는 근거가 아니다.

## 5. 문헌 담당 초안의 정 검토 연결

[문헌 담당 초안](20261023_acceleration_distillation_literature.md) 최초203행과 보강216행 전체, 이후 추가된 §5.5~5.6의 native-ID/ALM 계약을 읽고 로컬 코드·기존 결과와 대조했다. 이후 초안 보강은 해당 문서가 소유한다. 이 담당자가 독립적으로 연 범위는 CCE 공식 README, Liger fused CE main 소스, [ALM v4 §3·Appendix E/I](https://arxiv.org/html/2503.20083v4), [ACTD v1 §3.1~3.2](https://arxiv.org/html/2608.29662v1), [NorMuon v1 §3/Algorithm1](https://arxiv.org/html/2510.05491v1)과 [공식 update 소스](https://github.com/zichongli5/NorMuon/blob/main/normuon.py), [Part I v1 §2](https://arxiv.org/html/2610.23036v1)이다. 다른 문헌의 표·수치·공식 코드 전부를 독립 재검증했다고 주장하지 않는다.

### 5.1 정 관점의 조건부 타당성

| 후보 | 성립할 수 있는 이유 | 필요한 전제·최소 증거 | 자원·불확실성 |
|---|---|---|---|
| exact CCE / Liger | 현재 factorized tied head의 마지막 linear+CE만 대체 가능; 구조/교사/정답을 고정할 수 있음 | shift0, sum/전체-update 분모, 입력+출력 tied gradient, 비균일 token upstream 및 한 optimizer update 동등성 | 현 valid gather가 이미 있으므로 이득은 미측정; CCE tile과 Liger chunk 알고리즘을 구분. 로컬 설치/버전과 compile 포함 비용 확인 필요 |
| ALM 핵심형 | 다른 어휘를 유지하며 같은 byte 구간의 target 확률만으로 teacher 신호를 넣을 수 있음. hidden 없는 최소형은 원문에 근거 있음 | 동일 reference의 실제 teacher-forced logp, 한영 byte 경계·특수토큰 정렬, 미분 가능한 student per-token NLL, 안정적인 chunk 확률과 binarized divergence | teacher cache 생성 비용 포함. 긴 chunk 확률 소실·정렬 희소성·교사 오답을 감시. 일반 logp MSE로 바꾸면 ALM 재현이 아님 |
| ACTD | hidden 추출 없이 TF top-k teacher ID/logit, student anchor logit/LSE로 구성 가능 | first-subtoken 매핑의 자동 BOS/EOS 제외, 중복 anchor와 빈/부분byte decode 정의, student residual 질량·gradient의 toy 검산 | 공식 구현 부재가 원문 구현 불가능을 뜻하지 않지만 mapping/re-normalization의 별도 검증 부담. full KL 또는 teacher tail 보존으로 부르면 안 됨 |
| NorMuon | 기존 Muon의 NS 뒤 행별 통계를 추가하는 독립 변경으로 분리 가능 | 논문 RMS 규약과 공식 코드의 norm보존+Jordan 규약 중 재현 대상을 명시; 기존 RMS4 대조·parameter 그룹·None/zero gradient·state 재개 | 고유 행당 state 추가는 작을 수 있음. 실제 time-to-quality와 STE 안정성은 미측정; 단순 optimizer step 가속과 다름 |
| AdaMuon | 문헌 초안이 설명하는 sign/원소별 적응은 현재 Muon과 다른 검증 가능한 가설 | 최신 v3와 공식 코드 규약 고정, 동일한 초기화·목적·group·LR 의미를 명명하고 비교 | 추가 full-matrix state 비용. 이 담당자는 AdaMuon 원문을 독립 완독하지 않았으므로 세부식은 문헌 담당 초안의 확인 범위로 한정 |
| 새 input mixing / state 설계 | P098의 단순 덧셈 음성이 scalar/concat/orthogonal 변형의 음성은 아님 | 기존 반복·재주입 대조 보존, 주입 원천/위치·초기 state·반복 수를 하나씩 분리 | Part I의 주입 원천은 prelude 출력이며 P098의 token representation과 다름. 새 core 학습 비용·고정삼진 예외를 포함 |
| terminal KV / depth prior | 첫 cycle KV 고정과 다른 근사이므로 기존 실패 밖의 질문이 남음 | 정확 iteration별 KV 기준, 학습 depth prior와 fixed point 접근의 실제 상태, full/cached·TF/free-answer·R별 비용 비교 | cache 절감·prefill·RL 속도는 별개 실험. 현 고정 R2를 즉시 terminal KV로 바꿀 근거가 아님 |
| GSQ 계열 선택 최적화 | 문헌 담당이 확인한 mask/sign logit 최적화는 현재 latent-weight STE와 구분되는 가설 | 공식 soft train/hard extraction과 새 hard-forward QAT를 구분; 같은 원문/정답/초기 codes·scale에서 비교. 공유 weight의 호출·checkpoint별 난수 replay 계약 필요 | 원형 블록 PTQ와 full CE/KD는 다른 실험. FP32 보조 logits만8×P bytes이며 gradient/optimizer 별도. embedding/head 예외를 바꾸면 새 축 |

**우선 검토 가능하다는 정 의견은 성공 판정이 아니다.** 당장은 교사·구조를 바꾸지 않는 fused 정확성/비용 관측을 먼저 닫고, reference scoring이 확인되면 같은 teacher답 CE 대조와 ALM 핵심형을 연결할 근거가 있다. CCE가 느리면 그 사실을 남기고 기존 CE에서 증류를 이어갈 수 있으므로 fused 채택을 모든 증류의 필수 성공 조건으로 만들지 않는다.

### 5.2 초안에 전달한 구체 보강

1. ACTD mapping에서 `encode(...).ids[0]`를 무조건 쓰면 안 된다. 이번 Gemma JSON은 기본 BOS2를 넣으므로 기본 설정의 첫 ID는 lexical first-subtoken이 아닐 수 있다. `add_special_tokens=False` 또는 동등한 계약을 명시하고, 빈 decode·특수토큰·부분 UTF-8·동일 anchor 충돌을 원형과 함께 검사해야 한다. 이는 실제 새 mapping을 실행해 관측한 오류가 아니라 소스·tokenizer 계약에서 도출한 구현 위험이다.
2. ALM chunk 평균과 CE assistant-token 평균은 분모 단위가 다르다. 기존 `D_h`를 목적 변경에 그대로 복사하지 말고 chunk 분모·유효 mask·micro 누적의 정의를 별도 명시한다. loss 값의 크기가 비슷한 것과 각 목적의 gradient 기여가 비슷한 것도 다르다.
3. 현재 학습 classifier는 FP32 latent accessor다. 미래 hard-ternary/packed 또는 새 GSQ 경로를 fused-only 대조에 섞지 않는다. 입력 lookup·출력 readout의 공유 gradient를 확인하는 현재 대조가 먼저다.
4. NorMuon 공식 `normuon_update`는 전달 gradient를 in-place 수정한다. `SingleDeviceNorMuon`은 None gradient를 0으로 만들어 과거 momentum에 의한 이동이 남을 수 있지만, 현재 TinyLM Muon은 None이면 건너뛴다. 비활성 head/분기에 그대로 복사하면 동작이 바뀔 수 있어 None과 수치0을 구분하는 검증이 필요하다.
5. 최신 반복형 연구를 적용할 문제는 기존 실물에서 정한다. P098은 단순 덧셈, 결과062는 첫 cycle KV, P078 옛 결과는 crop 이득 예측기의 한계를 쟀다. 다른 주입·깊이 prior·terminal KV까지 배제한 것도, 최신 문헌만으로 새 compact 본체를 앞단보다 우선할 근거가 생긴 것도 아니다.
6. 추가 §5.6의 native ID·기존 CE serializer 유지와 읽기 전용 raw-byte 뷰는 현재 경로에 국소적인 방향이다. 문자 offset만으로 byte fragment를 복원하지 않고 원문 재결합·양쪽 완전 assistant chunk·미정렬 제외량을 확인한다. teacher/student template conditioning 차이도 유지한다. 제시된 binary-CE의 target-NLL 도함수는 수식상 맞으며, 확률이 같을 때 loss값까지0이어야 한다는 오판을 피한다. tokenkit의 새 BOS/special·normalizer 변경을 그대로 접합하는 것은 이 동등성 대조와 다른 축이다.

ALM 원문 §3의 upper-bound 표현과 Appendix E의 lower-bound 증명 충돌도 독립 확인했다. chunk event와 나머지를 합친 divergence를 전체 categorical divergence의 상계·동일 복원이라고 주장하지 않는 초안의 경계가 타당하다. ACTD의 top-k 재정규화와 non-anchor target0도 원문 정의에 부합하므로 이를 방법 자체의 오류로 지적하지 않는다. 다만 손실 정의의 mapping 충돌은 따로 남는다.

### 5.3 아직 독립 확인하지 않은 범위

문헌 담당은 이후 공식 LoopCD v1 본문을 확보해 coda 이전 hidden 대비와 coda 이후 logits 대비·Huginn burn-in reference·분석 FLOPs와 실제 wall 차이를 보강했다. GSQ v2와 공식 quantizer의 soft forward/별도 hard 추출·RNG replay도 직접 읽어 경계를 추가했다. 이 담당자는 그 새 원문을 독립 재열람하지 않았고 초안 대조로만 검토했으므로 전문·공식코드 재현으로 서명하지 않는다. 지정 LoopCD 공식 구현 귀속, STARS 미확보 Ouro modeling, DWA/DVLM 공식 실행 코드와 다른 반복형 연구 표의 확인/미확인은 문헌 담당 표시를 따른다.

ALM의 안정적인 log1mexp가 긴 chunk의 q 자체 underflow나 KD gradient 소실까지 해결한다는 뜻은 아니다. coverage 외에 길이·chunk logp·실제 student gradient 신호를 관측해야 한다. GSQ를 end-to-end 공유 weight에 접합할 때도 공식 한 연산의 replay가 여러 호출·checkpoint 사이의 동일 code 표본을 자동 보장하는지 별도 확인해야 한다. 이는 확인된 구현 결함이 아니라 새 접합의 검증 조건이다. 고정삼진 end-to-end 증류·RCO와 학생 QAT의 결합, 외부 teacher logp/API·학생 최소식·자원은 아직 실증이 필요하다.

## 6. 영향·권한과 남은 실증

| 축 | 이번 영향과 경계 |
|---|---|
| 파일 | 이 새 연구 문서와 추가 승인된 PAD 진단기/mock 테스트2개·공식 adapter/mock 테스트2개·ALM cache 진단기/mock 테스트2개만 작성. 기존 코드·모델·원로그·계획·결과·COMPASS·기준표·등록부 수정0 |
| 데이터/동시작업 | 보호 TinyDataset 접근0. 기존 tokenizer JSON과 정확한 학습·P078 metadata만 조회. 원형 보존 |
| 검증 | 읽기·JSON 구조/ID 산술·공식 소스 대조. 학습·GPU·loss/gradient 동등성·생성·전체 정적검사는 이 담당자 NOT_RUN |
| 비교 유효성 | tokenizer ID·shift·assistant owner·whole-update 분모·tied gradient·초기화·route·자원 경쟁을 별도 고정 |
| 문서 정본 | 총괄의 실제 실행·원답 readback이 완료되면 전용 스킬로 결과→계획/목록→기준표/COMPASS 연쇄가 필요. 이 연구 문서가 이를 대신하지 않음 |
| 부채/우선순위 | 기존 학습 소스 pin을 바꾸면 독립 namespace/검증 필요. 진행 중 팔에 가속·마스크·optimizer를 섞어 소급 적용하지 않음 |

`impact-analysis`는 중복 구현 구분, 3안 비교와 영향·권한 분리에 적용했다. `plan-doc`는 읽었으나 본 산출물은 plan 디렉터리 밖의 일반 연구 문서이므로 P/S 템플릿·번호·상태 이관을 적용하지 않았다.

## 7. 추가 승인된 Core6 공식 likelihood adapter 소스 준비

[P106B Stage8a0W/Stage8aW](../../test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md)의 사전 계약에 따라 [신규 adapter](../../scripts/p106b_official_lm_adapter.py)와 [신규 순수/mock 회귀](../../scripts/test_p106b_official_lm_adapter.py)를 작성했다. 공식 원문은 이미 반입된 `d6de81643928d653435c431bae19945d41d32520` source의 `api/model.py`, `models/huggingface.py`, `utils.py`, `__init__.py`, `pyproject.toml`을 읽었으며 패키지를 import하지 않았다. root의 별도 평가환경 설치 승인은 이 담당자의 설치·실행 승인으로 확대하지 않는다.

기존 `eval_bench_suite.seq_ce`는 prompt/continuation 별도 encode·빈 문맥 newline·길이초과 None/skip을 사용한다. 따라서 기존 MC 점수를 유지하되 공식 연결의 수치 계약으로 그대로 재사용하지 않는다. 실제 재사용 대상은 `interactive_research_infer.selected_runtime`의 strict Q/F loader와 기존 FP32 MATH wrapper다. 지원하는 연구6종 외의 새 CP loader나 HF/GGUF backend는 만들지 않았다. 이미 열린 다른 strict runtime을 주입하는 factory도 있지만, 객체/어휘 검사는 그 원 loader의 CP/header/core 검증을 대신하지 않는다.

공식 `TemplateLM._encode_pair`와 `loglikelihood`는 상속으로 재사용한다. trailing whitespace 이동·joint encode·빈 문맥 prefix와 이미 있는 BOS의 중복 방지를 원문대로 둔다. continuation 전체의 조건부 logprob **합**과 모든 target의 greedy 일치를 순서대로 반환하며 PMI·길이 정규화는 하지 않는다. 정규화는 공식 task의 몫이다. 양쪽 문자열 자체를 정리하거나 새 chat template를 붙이지 않는다.

입력 계획은 고정 HFLM의 `(context+continuation)[-(1024+1):][:-1]`과 같은 규약이다. 문맥만 왼쪽에서 줄이고 continuation은 전량 보존한다. 1024개 target은 prefix를 포함한1024개 model input으로 채점할 수 있다. continuation1025+는 요청 묶음의 어떤 forward보다 먼저 명시 오류로 처리하며, 후보 일부를 절단·skip하거나0점으로 바꾸지 않는다. rolling likelihood·자유 생성·chat template는 명시 미지원이다.

오른쪽 PAD의 label은−100이며 질문 문맥은 attention에 남는다. 기존 TinyLM causal attention 때문에 유효 prefix가 미래 PAD를 참조하지 않는 규약을 사용하고 assistant-loss mask를 attention mask로 넘기지 않는다. stdlib ID/label 계획·작은 logits oracle와 별도 full-label CE oracle를 마련했지만 실제 torch oracle/parity는 총괄 실행 전 미검증이다. 순수/mock 회귀의 작은 FP64 산술 비교는 GPU 판정 허용치를 정하는 행위가 아니다.

모듈 import는 stdlib만 사용한다. 명시 factory는 archive/manifest·metadata 버전과 import 전 검색 경로를 확인한 뒤 harness를 지연 import한다. 원 source와 normal-wheel 설치판의 경로는 다를 수 있으므로 `runtime_root`를 명시하면 그 아래 실제 package와 보존 원문의 핵심 source SHA를 대조한다. 경로 차이를 무조건 거부하지도, version 문자열만 같다고 허용하지도 않는다. archive와 핵심5파일 검증을 새 전체 source-tree 재검산으로 과장하지 않으며, 설치 provenance와 task/data YAML·revision의 최종 정합은 총괄 wrapper/자료 manifest가 별도로 소유한다. 공식 evaluator의 자동 Git hash도 TinyLM 작업환경과 harness commit으로 분리해야 한다.

현재 상태는 **소스 준비·총괄 전체 검토/실행 인계**다. 공식 `lm_eval` import·설치·등록, 순수/mock 회귀 실행, 실제 소형/모델 likelihood parity, Core6 전수 점수는 이 담당자가 수행하지 않았다. 파일 존재나 상속 설계가 공식 점수 획득의 증거는 아니다.

## 8. 추가 승인된 Stage7b ALM 선택 동결·교사 캐시 소스

[Stage7b 사전 계약](../../test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md)에 따라 [신규 캐시 진단기](../../scripts/diag_p106b_alm_cache.py)와 [신규 순수/mock 회귀](../../scripts/test_p106b_alm_cache.py)를 준비했다. 기존 `p106b_alm_bytes`의 전체 입력 재결합·최소 공통 chunk·원래 index→한 번 shift를 재사용하고 ALM 손실·새 학습기는 만들지 않았다. root가 승인한 다음 세부 계약을 구현했으며 이 담당자는 실제 코퍼스·토크나이저·교사·GPU·회귀를 실행하지 않았다.

### 8.1 선택과 원형

- 기존 V3 corpus report의 고정 SHA를 입장 조건으로 사용한다. 원 TRAIN의 `explicit_public_context_qa`, wrapper0, 두 턴 user/assistant, 원 TRAIN/명시 근거·annotation·semantic root 계보만 후보가 된다. 전체 원 VAL의 root/context ID/정확한 대화/정확한 첫 user prompt와 겹치는 후보를 제외한다.
- 기존 `stream_rows`와 `encode_record`로 학생 x≤1024·CE target≤64를 확인한다. 정답 점수·교사 점수는 읽지 않는다. 언어별 `SHA256([schema,1337,ROOT_ORDER,language,root])` 순으로512개씩 골라 ko/en을 교대로 놓는다. 앞16과 이후 모든16행 배치가 각각8/8이며 실패 행은 교체하지 않는다. 작은 합성 fixture의 표본 수는 실제1024행 조건을 바꾸지 않는다.
- 새 `HF/sft_ready/p106b_alm_context_v1_s1337/prepared/`에 원 row/metadata·질문/근거/답/annotation·실제 serializer text·학생 원 ID/offset/piece/label/turn·UTF-8 byte SHA를 함께 보존한다. encoder의 원 x/y/segment와 직접 대조하며 source/VAL/tokenizer 원본은 수정하지 않는다. 이 저장은 annotation이 의미적으로 전수 검수됐다는 증거가 아니다.

### 8.2 교사 원 확률과 보존

학생 `id_to_token`의 ByteLevel 역함수와 원 `loss_spans`를 사용한다. 같은 전체 UTF-8 text를 `/tokenize(add_special=false, parse_special=true)`의 IDs-only/with-pieces 두 경로에 보내 ID가 같아야 한다. literal ChatML special의 교사 native ID도 별도 probe로 확인한다. 양쪽 piece 전체가 같은 입력 byte를 정확히 복원해야 하고, 교사 전체1024 cap은 학생 cap과 별개로 검사한다. 근사 template 변환·잘린 문자 복구·후보 일부 절단은 하지 않는다.

기존 `diag_p106b_teacher_tf.session_for/command/payload/probability_entry`와 소유 QwenSession을 재사용한다. MTP는 명시 OFF다. 실제 reference prefix와 target ID를 bias100으로 요청하고 ID가 다를 때만 bias200으로 한 번 더 시도한다. 모든 시도를 보존하며 sentinel/비유한 logp와 끝까지 다른 ID는 도구·신호 실패이지 답의 오답 판정이 아니다. 수락 chunk의 교사 raw target logp만 합하며 EOT는 KD에서 제외하고 기존 CE target에 남긴다.

`--cache-prompt`는 기본 OFF다. 명시 ON이면 각 행 첫 선택 target에서 cold/warm의 실제 ID·raw chosen logp·top2를 atol1e-5로 대조한 뒤에만 해당 행 후속 prefix를 재사용한다. 불일치 시 cold로 조용히 전환하지 않는다. 고유 target 수와 검증·재시도 요청 수를 구분한다. 언어별 CE target/KD chunk/교사 target과 supervised target·byte 및 원 assistant 비특수 byte에 대한 수락률을 각각 기록한다.

기존 세션을 계측 래퍼로 감싸 health/props를 포함한 요청 전 실제 payload와 reply/HTTP 오류, 전체 서버 log, 200ms 표본 및 표본 누락을 20MB 미만 write-once shard에 보존한다. 긴 prefix는 먼저 남긴 행별 전체 교사 ID·prefix stop·canonical payload SHA와 나머지 실제 키로 정확히 재구성할 수 있다. 기존 키 가림/HTTP 오류 보존 함수를 사용하며 source text에 일반 정규식을 적용해 바이트를 바꾸지 않는다. 기존 서버 수명관리 함수는 수정하지 않는다.

### 8.3 배치 경계와 아직 없는 증거

canary는 고정 앞16만 처리한다. `--cache --batch-index 0..63`은 한 프로세스에서 지정16행만 처리하며 닫힌 report의 코드/준비본/행/교사 계보·정책 SHA와 shard를 검증한 경우에만 재사용한다. partial은 보존·거부한다. canary를 새 full-cache 배치로 자동 복사하거나, 기존8시간 생산 재개와 같은 실행으로 취급하지 않는다. 어느 한 배치가 끝나도1024행 전체 완료라고 보고하지 않는다.

입장/종료의 코드·원 입력·교사 자산 full SHA, 기동·채점·종료를 전체 비용에 포함하며 최대600초와2026-10-23 16:30KST hard stop을 적용한다. 마지막30초는 소유 서버 종료 여유로 명시한다. 시간/실패로 종료 hash를 못 했으면 `NOT_VERIFIED_AFTER_PARTIAL_FAILURE`이지 원형 불변 PASS가 아니다. 새 선택·캐시가 실제로 준비됐는지,16행이 시간 안에 끝나는지, coverage와 긴 chunk logp가 유효한지, 비용이 감당되는지는 총괄의 실제 실행 전 **NOT_RUN**이다. 이후 CE-only 대 CE+ALM Stage7c는 실제 비용·coverage 관측 뒤 별도 사전 결정이며 이 파일 준비로 승인·성공이 생기지 않는다.

## 9. Native595-F의 CE-only/CE+ALM 최소 연결점 — 읽기 전용 추적

총괄의 추가 요청은 **같은 Native595-F 초기화·고정1024 TRAIN·4epoch·micro8×accum16·checkpoint ON·같은 optimizer**다. 여기서는 소스와 작은 완료 metadata만 읽었다. 실제 CP tensor·tokenizer·학습 행 전문·모델·GPU·테스트를 열거나 실행하지 않았으며 기존 코드 수정도 없다. 아래는 후속 구현의 연결 후보이지 새 trainer 구현·Stage7c 실행 승인·정확성 PASS가 아니다. `impact-analysis`는 기존 구현 중복과 세 가지 연결 비용을 구분하는 데 사용했다.

### 9.1 이미 있는 실제 부모와 float 경로

| 소유 정본·함수 | 확인한 사실과 재사용 경계 |
|---|---|
| `handoff/audit/WIP_20261021_RESEARCH_INFER_MANIFEST.json`의 `entries.native595-f` 및 `test_result/evidence/p106b_native595_v1_s1337/train_float/report.json` | 원 CP는 `runs/ckpt/m100s10_ko-en_p106b_native595_v1_s1337_float_native.pt`, 완료4543 update, weight-only다. metadata의 CP SHA는 `7DF60C47605B654520C510E2758D559213AABCB7ED1090424BDC0D50BC9413BA`, core SHA는 `E21E7023D5F289E2EBA2C65127491CB8016232A538E0619E63068BA095D4E3DD`다. 이 담당자가 CP 파일을 해시/로드한 값은 아니다. optimizer 저장은 false이므로 과거 optimizer resume가 아니라 양 팔 fresh reset이 필요하다. |
| [`diag_p106b_native595.loaded_runtime`](../../scripts/diag_p106b_native595.py#L516) | 검증한 완료 report와 원 Runtime을 받아 scratch 규격 생성→엄격한 CPU state/header 검사→CUDA→활성 `weight_route('float')` 안에서 실제 native595 core를 복원하고 `(torch,model,route)`를 반환한다. 기존 학습 가능한 부모 loader다. `model.cfg`가 cfg이며 tokenizer는 별도 고정 SHA로 읽는 bridge가 필요하다. |
| [`diag_p106b_native595_broad.parent_snapshot/parent_runtime`](../../scripts/diag_p106b_native595_broad.py#L501) | 위 3tuple에 cfg/tokenizer와 원 부모 descriptor를 묶는 기존 사례다. 다만 이 wrapper의 old Broad 자료·704update·기한을 이번 실험에 호출하는 것은 별개다. `parent_snapshot`의 전체 `read_training`은 기존 native bin/event까지 검산하므로 이번 새 실행의 최소 입장 비용과 구분해야 한다. |
| [`p106b_weight_route.weight_route/load_routed_state`](../../scripts/p106b_weight_route.py#L231) | instance-local float는 latent FP32 master의 identity view/gradient다. anneal0은 STE backward가 남으므로 float의 대체가 아니다. 활성 route를 forward·head checkpoint 재계산·backward·optimizer step·VAL 동안 유지해야 한다. `load_routed_state`는 keys/shape/dtype/layout/공유 Parameter alias까지 검사하지만 파일 SHA·recipe·tokenizer 검증은 caller 책임이다. |
| [`interactive_research_infer.read_selected_payload/validate_cfg`](../../scripts/interactive_research_infer.py#L356) | 같은 읽기 전용 파일 handle에서 SHA→CPU weights-only load→inode/mtime/header SHA를 검산하는 재사용 가능한 낮은 층이다. 기존 manifest/header/core 증거를 새 훈련 입장 영수증에 연결할 때 이용할 수 있다. 단, inference-only manifest 자체를 훈련 권한으로 해석하지 않는다. |
| [`interactive_research_infer.selected_runtime`](../../scripts/interactive_research_infer.py#L392) | **전체 context는 학습에 부적합하다.** eval/freeze를 설치하고 종료 시 본체 불변을 강제하므로 optimizer가 정상 변경한 본체도 오류로 본다. 이 조건을 끄는 것이 아니라 기존 학습 loader 또는 위 낮은 층을 새 권한/종료 계약 안에서 사용해야 한다. |

Native595의 cfg metadata는 dense14, dim768/FFN2048/embedding rank256, chat32 V32768, CLA2·attention group1, repeat1, MTP OFF, max1024·checkpoint ON이다. 같은 초기화의 기준은 과거 scratch028C46이 아니라 **각 팔 입장 후 E21E70… native595 학습 core**다. 원 `diag_p101a_sft_mtp.load_runtime('parent_ntp')`를 그대로 부르면 P090B의 다른 학습 가중치가 들어가므로 이 대체는 금지한다. 기존 native595 loader가 `scratch_ntp`를 사용하는 것은 규격 생성 뒤 native595 전체 state를 엄격히 덮어쓰는 절차이며 scratch 학습을 뜻하지 않는다.

### 9.2 업데이트 본체 재사용 세 안

| 안 | 정확한 연결점 | 장점 | 필수 차이·비용 |
|---|---|---|---|
| A. 기존 SFT 전체 controller 연결 | [`diag_p101a_sft_mtp.train_arm`](../../scripts/diag_p101a_sft_mtp.py#L189)의 micro 손실 블록 | 기존4epoch/128행/정적1024·분모/평가/저장 흐름이 있음 | 원 함수는 local import된 `mtp_sft.components/normalized_loss`를 직접 호출하며 objective callback이 없다. 원 parent/corpus schema·태그·compile·저장 header도 P101A에 묶여 있다. 이 원본을 바꾸거나 shared module 함수를 monkeypatch하는 것은 현재의 동결 소스를 훼손한다. 사전 승인된 좁은 callback 분리 없이는 완성된 drop-in seam이 아니다. 비용 중간 이상. |
| B. 기존 한-update primitive에 목적 객체 주입 | [`diag_p101a_padding_gpu.one_update`](../../scripts/diag_p101a_padding_gpu.py#L435)의 **`core` 인자** | 원 코드·전역 변경 없이 pad/forward/16micro backward/finite 검사/clip/optimizer.step/GPU events·peak·whole-update 분모를 통째로 재사용할 수 있음 | `policy='fixed1024'`, `precision='bf16_eager'`, `capture=False`가 전제다. 모델에 고정 PAD ID를 지정하고 guard/journal/update plan 및 NLL 목적 facade를 제공해야 한다. compile-forward 인자는 없으며 진단용 계측 비용을 포함한다. 새 파일은32회 호출/계보/VAL/저장만 소유하면 되어 반복 trainer 중복이 가장 작다. |
| C. Broad given-model core 연결 | [`diag_p106b_broad_curriculum.train_updates`](../../scripts/diag_p106b_broad_curriculum.py#L606) | model/forward/optimizer/probe를 이미 인자로 받고 외부 parent loader 사례도 있음 | 원352update·22528행 schedule·2816 native windows와 **추가 native8192 backward**가 고정이다. 단순히 objective만 바꾸면 QA-only 비교가 아니며, 전부 풀려면 A/B보다 훨씬 넓은 변경이 필요하다. 비용 높음·이번 최소 연결로 비권장. |

**정 의견: eager를 양 팔 공통으로 선택한다면 B가 가장 작은 실제 주입 seam이다.** 이는 PAD crop의 수치 음성을 채택하는 것이 아니다. 진단 `execute`·ABBA·crop128·FP32 비교 문턱·원 P090B CP 로딩을 호출하지 않고 이미 있는 **fixed1024 update 함수만** 사용한다. compile가 필수라면 B를 compile 측정이라고 부를 수 없으며 A의 명시적인 forward/objective seam을 새 승인 범위에서 분리해야 한다. 지금 이 담당자는 어느 코드도 변경하지 않았다.

### 9.3 기존 NLL core와 facade가 해야 할 최소 일

[`tinylm/train/alm.py`](../../tinylm/train/alm.py)는 이미 다음 세 함수를 제공한다.

1. `target_nll(model,hidden,already_shifted_targets,chunk=64,checkpoint_head=True)`는 기존 `_head_logits`를 통해 미분 가능한 **전체 `[B,T]` 위치의 NLL**을 돌려준다. valid gather 뒤 위치를 scatter해 원 위치를 복원하며 ignored 위치는0이다. 새 head/embedding/어휘를 만들지 않는다.
2. `chunk_kl(nll,supervised,chunks,temperature=...)`는 `{row,positions,teacher_logprob}`로 명시한 원 shifted 위치를 합한다. teacher 값은 detach되고 겹침·무감독 위치·sentinel·비정상 확률을 거부한다. `binary_kl_logq`와 안정 `log1mexp`도 이미 있다.
3. `normalized_loss(ce_sum,D_CE,kl_sum,D_KD,weight=...)`는 CE target과 KD chunk의 **서로 다른 전체 update 분모**를 사용한다. micro 평균의 평균이나 추가 `/16`은 필요하지 않다. 전체 D_KD=0에 비영 weight면 실패하며, 어떤 micro만 chunk0인 것은 전체 D_KD>0이면 허용된다.

B의 `core` facade는 `pad_records`를 원 `mtp_sft.pad_records`에 위임하고, `components`에서 위 NLL을 **한 번만** 계산해 CE 합과 KL 합을 함께 만든다. `sums[1]`과 `counts[1]`은 반드시 기존 의미의 **순수 CE 합/CE target 수**로 둔다. KL을 `sums[1]`에 섞으면 기존 primitive의 `loss=nll/observed` 로그가 CE인 척하는 결합 목적이 된다. 별도 KL 합/수락 chunk 수를 전달하고 facade의 `normalized_loss`가 미리 고정한 D_KD와 λ를 사용하도록 한다. 실제 결합 목적·KL·유효 chunk·언어별 수락량은 별도 사건/요약으로 남겨야 한다.

양 팔은 `target_nll`의 head chunk/AMP/checkpoint 경로까지 같게 두고 CE-only에서는 λ=0으로 KD 계산만 생략하는 것이 인과 비교에 적합하다. 원 `mtp_sft.components`의 chunk2048 대 ALM의 chunk64를 서로 다른 팔에 쓰면 목적 외 head 수치·실행 형태도 달라진다. 이 차이를 순수 목적 효과로 부르면 안 된다. PAD에서 작은 gradient 차이가 Muon update 차이로 커진 음성도 있으므로 기존 CPU toy의 CE/gradient 회귀만으로 실제 native595-F BF16 한 update 동등성이 이미 증명됐다고 쓰지 않는다. 기존 [`test_p106b_alm_core.py`](../../scripts/test_p106b_alm_core.py)에 full CE·tied gradient·비선형 KL·불균등 micro/zero-KD 검산이 있는 것은 확인했지만 이 담당자가 실행하지 않았다.

### 9.4 자료·순서·분모·optimizer의 정확한 연결

- 학생 Record는 동결 선택의 `ids[:-1]`, `labels[1:]`, `turn_ids[1:]` 또는 같은 원 `encode_record`로 만든 값을 원형과 대조한다. EOT는 CE에 남긴다. [`diag_p101a_sft_mtp.batches(records,epoch)`](../../scripts/diag_p101a_sft_mtp.py#L81)는 `Random(1337+epoch)`의 같은 순서로128행을16×8로 나눈다. shuffled Record와 cache 행을 원 source/prepared row SHA·row ID의 병렬 맵으로 묶어야 하며, 파일 순서나 token ID hash 하나만으로 캐시를 찾지 않는다. 서로 다른 root가 같은 token열을 가질 수 있다.
- facade의 한 update 시작에서128행의 D_CE와 수락 chunk의 D_KD를 CPU 정수로 동결한다. 각 micro의 local row번호와 학생 `student_shifted_indices`를 재배치하고 실제 `y[row,p] == cached_ids[p+1]`, 같은 assistant owner/turn·원 byte SHA를 확인한다. 이미 cache가 준 i−1를 다시 shift하거나 valid-gather의 compact 위치로 바꾸지 않는다. head checkpoint 재계산 때 순서 cursor가 다시 진행하지 않도록 changing tensor는 원 helper처럼 명시 인자로 유지한다.
- 고정1024행이면 epoch당8 update,4epoch에 **각 팔32 update·4096행 노출**이다. raw x/assistant target 수는 실제 Record 합이고 PAD slot 수와 다르다. 원래22528행·704update·native replay 노출을 이번 총량에 섞지 않는다. full-cache64배치가 다 닫히지 않았거나 어느 동결 행이 실패했다면 행을 교체하거나 표본을 줄여 동일1024 비교를 선언하지 않는다.
- [`diag_p101a_sft_mtp.optimizers`](../../scripts/diag_p101a_sft_mtp.py#L132)는 AdamW lr1e-4/Muon4e-4이며 embedding 쪽 WD.1이 남을 수 있다. [`diag_p106b_native_weight_route.make_optimizers(model,'sft')`](../../scripts/diag_p106b_native_weight_route.py#L618)는 이를 .5배·전 group WD0으로 바꾸고 전체 Parameter가 정확히 한 group에 속함을 검사한다. [`diag_p106b_relation_bind.make_optimizers`](../../scripts/diag_p106b_relation_bind.py#L319)도 같은 SFT lr5e-5/2e-4·WD0의 기존3tuple factory다. Native595의 과거 native 최대 lr.001/.004·embedding WD.1과 혼동하지 않는다. **어느 기존 factory/LR을 새 두 팔에 고정할지는 총괄의 사전 선택 사항**이며, 이 문서는 optimizer 숫자를 새로 채택하지 않는다.
- 두 팔은 같은 완료 native595-F core에서 각각 fresh optimizer·같은 RNG/순서로 시작하고4epoch 중간에 optimizer를 reset하지 않는다. Muon RMS 규약·NS5·clip1·FP32 master를 양 팔 같게 유지한다. 모델 두 개 동시 상주가 필요하지 않으며 팔별 별도 프로세스는 이전 cuBLAS workspace 잔류와 입장 증거를 분리하기 쉽다.

### 9.5 원 VAL context-QA와 첫 답의 재사용

원 V3 **report metadata**는 VAL512행(ko256/en256), assistant targets2977을 기록한다. 이번에 실제 VAL 행을 읽지 않았다. 이 VAL은 별도 새 TEST가 아니며 훈련 검증에 이미 쓰인 원 DEV다.

| 재사용 함수 | 바로 쓸 수 있는 부분 | 바꿔 호출하면 안 되는 부분 |
|---|---|---|
| [`diag_p101a_clean_bilingual.masked_record/encoded`](../../scripts/diag_p101a_clean_bilingual.py#L38) 및 원 `stream_rows` | 기존 VAL row→같은 serializer/assistant owner Record. `encoded`는 TRAIN도 함께 읽으므로 VAL만 원 manifest로 streaming하는 쪽이 이번 좁은 소비 경계에 맞는다. | 기존 모든22528 TRAIN을 이번1024 selection으로 착각하지 않는다. |
| [`diag_p101a_sft_mtp.evaluate(base,records,pad)`](../../scripts/diag_p101a_sft_mtp.py#L143) | MTP OFF에서 원 VAL CE/target 수를 합산한다. fixed1024·micro8, EOT 포함·같은 분모를 양 팔에 재사용할 수 있다. | 이 함수는 **BF16 autocast TF CE**다. `PrecisionForward('fp32_math')`를 base 대신 주입해도 바깥 head CE가 함수 내부 BF16 context에 남으므로 전체 FP32 TF CE가 됐다고 부를 수 없다. |
| [`diag_p106b_broad_curriculum.dev_probe`](../../scripts/diag_p106b_broad_curriculum.py#L576) | 주입한 Record 목록의 raw/content/EOT CE를 별도 집계하는 기존 함수다. | Broad 기록의 scope/제외16 dialogue 문구를 원 VAL512 결과에 그대로 복사하지 않는다. CPU/device 옵션이 있다고 실제 정밀도 계약까지 같아지는 것은 아니다. |
| [`diag_p101a_clean_eval.prompt_messages/score/readable_case`](../../scripts/diag_p101a_clean_eval.py#L21) | 마지막 assistant를 빼고 첫 실제 답을 수집·원 질문/기준 답/종료와 함께 기록한다. `score`는 annotation strip exact이며 의미 진실 판정이 아니다. | `execute/prerequisites`는 원 P101A tag와 **generic `load_model`**에 묶여 있다. 현재 `generate.load_model`은 route metadata를 복원하지 않고 `set_anneal(1)/freeze_quant`를 하므로 native595-F를 그 경로로 재로딩하면 안 된다. |
| [`p106b_night_learning.qa_scores`](../../scripts/p106b_night_learning.py#L142) | 원 aliases를 보존하면 KO 공백 무시 문자 F1/EN 단어 F1·raw exact를 부지표로 계산할 수 있다. | 로컬 지표이지 공식 SQuAD/KorQuAD scorer가 아니다. `p106b_night_evaluation.recount_natural` 전체는 모든 root의 wrapper0/1/2를 요구하므로 wrapper2만 있는 원 VAL512에 그대로 호출할 수 없다. |
| [`interactive_research_infer.answer_from_tokens`](../../scripts/interactive_research_infer.py#L517) 및 기존 `CaptureTokens/PrecisionForward`·`generate.sample` | 이미 활성인 float 모델에서 동일 FP32 MATH greedy·MTP1·EOT/EOS/생성 ID 영수증을 사용해 첫 답을 추출하는 낮은 층을 재사용할 수 있다. | 추론용 `selected_runtime` 전체와 `emit`의 고정6종/manifest 계약을 새 훈련 context의 권한·loader로 사용하지 않는다. prompt/full-context 예산·max-new·잘린 답·원답을 양 팔 동일하게 남긴다. |

VAL/첫 답 평가를 활성 float route 안에서 수행한 뒤 학습을 계속한다면 **`clear_quant(); train()`**가 필수다. `freeze_quant`는 추론 cache를 고정하는 표시이며 특히 no-grad 안에서 만든 cache를 학습으로 복귀할 때 남겨둘 수 없다. float route는 frozen 상태의 training 사용도 명시 거부한다. 양 팔의 같은 초기/epoch별/최종 VAL 경로와 model core 전후·source/VAL 불변을 구분해 기록한다. KL 감소·annotation EM/F1·종료 성공·현재 Core6 공식 점수는 서로 다른 관측이며 대체하지 않는다.

### 9.6 남은 사전 선택·검증 경계

이번 소스 추적만으로 정해지지 않은 항목은 **λ·temperature(함수 기본100을 자동 채택하지 않음)·head chunk·기존 optimizer factory/LR/WD·eager/compile·첫 답 max-new/평가시점·새 child CP/loader 계보**다. 위 B 연결의 조건은 eager이며 다른 선택이면 최소 범위도 달라진다. 새 child는 native595 원 tag/4543step/header/기존6종 inference manifest를 재사용해 덮어쓰지 않는다. 새 source/cache/parent SHA, 실제32update·objective 식/분모·τ/λ·route/tokenizer를 별도 영수증과 새 checkpoint metadata에 묶는 책임이 새 controller에 남는다. formal Stage7c 계획·preflight·실물 parity·자원·품질은 총괄의 후속 승인/실행 항목이며 이 담당자의 수행은 문서 기록까지다.


## 10. 텍스트 생산 진척 재집계 — 고정 시각의 게시본과 수입 선언을 분리

### 10.1 범위·시각·식별자

이 절은 총괄이 허용한 **텍스트·메타데이터 읽기 집계**다. 기준 경로는 data_cache/p106b_text_work_20261022이며, published/native_full_en_*, published/native_full_ko_*, published/sft_*의 JSON과 imported/*/report.json·manifest를 읽었다. 추가 승인된 봉인 packets/*.json 및 publish_receipts/source_packets/*.json에서는 ID·선언 원문 SHA만 추출하고, 게시 영수증에서는 성공 상태·ID·원문 SHA·게시 파일 SHA·패킷 SHA만 대조했다. 원천의 의미 검수·새 전처리·게시·수입·모델/토크나이저/GPU·테스트 실행은 하지 않았다. 도구 출력 범위 실수는 §10.7에 숨기지 않고 별도 기록한다.

- 고정 기준 시각: **2026-10-23 07:59:04.377053 KST**, 나노초 값 1792709944377053410. 최초 집계는 07:59:04.862246 KST에 끝났으며, 그 짧은 순회 중 기준 뒤 새 게시 파일은 관측되지 않았다.
- 같은 기준으로 **08:02:58 KST에 재집계**해 아래 핵심 수치가 같음을 확인했다. 이때 기준 뒤 EN10개·SFT32개가 이미 더 보였으나 이번 수치에는 넣지 않았다. KO의 기준 뒤 추가 파일은 그 재집계에서0개였다. 따라서 아래는 현재 시각의 실시간 총량이나 원자적인 파일시스템 스냅샷이 아니다.
- 각 파일을 읽기 전후 크기·mtime을 대조했다. 재집계가 읽은 기준 시각 이내 입력 **4,302파일**의 (기준 경로 상대파일명, 실제 파일 SHA256) 정렬 목록 해시는 E120D3C5B2EA62AE023128461BEE5989B9CB5ADF95ED30CC65CA5D7FEFA17A14다. 이는 아래 재현 명령의 입력 목록 해시이며 **원문 SHA나 데이터셋 전체 내용 해시가 아니다.** 앞으로 추가 게시·과거 mtime을 보존한 복사·기존 파일 변경이 있으면 재현 입력 목록은 달라질 수 있다.

고유 원천 키는 native의 (언어 구획, 문서 id, 선언 원문 text SHA256), SFT의 (sft, source_id, 선언 source_line_sha256)다. SFT의 source_index는 패킷 위치 표시에만 사용했다. 원문 SHA는 봉인 패킷과 성공 게시 영수증의 선언값 일치를 확인한 것이며, 원문을 따로 열어 의미 판독하거나 텍스트를 새로 해시한 결과가 아니다. **패킷 파일 SHA를 원문 SHA로 대체하지 않았다.** 같은 원문 SHA라도 source ID가 다르면 이 집계에서 서로 다른 원천이다.

게시본 각각에 성공 영수증과 원문 SHA 연결이 있었으며, 같은 키의 중복 게시 원천은 EN0·KO0·SFT0이었다. 최근 구간 보고 숫자나 ID 최솟값~최댓값의 차이를 합산하지 않고 이 집합으로 집계했다. imported 여부는 같은 패킷 SHA·같은 게시 파일명·같은 실제 파일 SHA가 닫힌 report의 response_files와 일치하고 manifest 계보·행수/바이트 선언이 일관된 경우만 센다. JSONL shard 본문·실제 shard 바이트는 읽지 않았으므로 이 일관성은 **수입 메타데이터 수준**이지 수입 산출물 전수 검산이나 의미 품질 PASS가 아니다.

### 10.2 고정 시각에 실제 있는 게시본

| 게시 구획 | 고유 원천 | KEEP | REWRITE | HOLD | 같은 게시 파일 SHA의 수입 선언 | 아직 같은 파일 SHA 수입 선언 없음 |
|---|---:|---:|---:|---:|---:|---:|
| EN native_full | 532 | 90 | 162 | 280 | 264 | 268 |
| KO native_full | 383 | 11 | 274 | 98 | 240 | 143 |

이 판정 표의 분모는 **현재 남아 있는 해당 게시 JSON**이다. 아래 과거 수입 전용 원천의 KEEP/REWRITE까지 뜻하지 않는다. EN 마지막 게시 mtime은07:59:02.798681 KST, KO는07:56:10.555800 KST다.

| SFT 게시본의 상태 | 고유 원천 | 실제 variant 객체가3개인 원천 | variant0개인 분류 전용 원천 | 고유 (원천 키, kind) variant |
|---|---:|---:|---:|---:|
| 게시본 전체 | 912 | 590 | 322 | 1,770 |
| 같은 게시 파일 SHA의 수입 선언 있음 | 448 | 334 | 114 | 1,002 |
| 같은 게시 파일 SHA의 수입 선언 없음 | 464 | 256 | 208 | 768 |

세 변형의 실제 kind는 ko_translation·ko_rephrase·en_rephrase가 각590개였다. 요청된 변형 수3을 원천912개 모두에 곱하지 않았다. 영변형322개는 새 학습 variant0개이며, 이 고정 게시본에서 세 변형 원천과 영변형 원천의 교집합도0이다. 여기서 “실제3변형”은 **세 종류 객체가 파일에 존재한다는 구조적 관측**이지 번역·재표현·응답의 의미 적합성이나 채택 판정이 아니다. variant 고유성은 문자열 의미 중복 제거가 아니라 위 원천 키와 종류의 고유성이다. SFT 마지막 게시 mtime은07:56:56.533532 KST다.

### 10.3 과거 수입 선언과 게시본의 중복 제거

| 구획 | 닫힌 report 수 | 보고/봉인 메타데이터로 복원한 수입 선언 고유 원천 | 위 게시본과 교집합 | 수입 선언만 있고 위 게시본에 없는 원천 | 두 증거의 고유 원천 합집합 |
|---|---:|---:|---:|---:|---:|
| EN native_full | 22 | 528 | 264 | 264 | 796 |
| KO native_full | 17 | 408 | 240 | 168 | 551 |
| SFT | 61 | 964 | 448 | 516 | 1,428 |

위 report들은 선언 원천 수와 ID·원문 SHA로 복원한 집합의 수가 일치했고, report끼리 동일 원천 키를 중복 선언한 수는0이었다. 구간 채팅 보고가 겹치지 않았다는 뜻은 아니다. 채팅 보고를 집계 입력으로 쓰지 않았고, 특히 **SFT의 게시912와 수입 선언964를 그대로 더하지 않고 공통448을 뺐다.**

SFT 과거 수입 선언964원천은 세 변형 원천850·영변형114로 나뉘며, manifest의 authoring 출력 행 선언은2,550이었다. 그중 현재 게시본 밖516원천은 모두 세 변형을 선언한 과거분이다. 따라서 합집합1,428원천은 **세 변형 원천1,106·영변형322**, variant는 **3,318개**로 연결된다. 단, 3,318 중 현재 게시 파일에서 직접 세 종류 객체를 확인한 것은1,770이고, 나머지1,548은 과거 report/manifest의 출력 선언이다. JSONL을 열지 않은 이번 작업에서 이 둘을 모두 “새로 직접 확인한 실제 variant”로 바꾸어 부르지 않는다.

과거 수입 전용 native EN264/KO168의 KEEP 대 REWRITE는 허용된 현재 게시 파일만으로 완전히 복원되지 않는다. held_source_ids에 EN141/KO122개가 선언돼 있지만, 나머지 EN123/KO46개를 임의로 KEEP이나 REWRITE에 넣지 않는다. 따라서 **native_full 누적 합집합 전체의 완전한 KEEP/REWRITE/HOLD 삼분표는 미복원**이며 §10.2의 게시본 판정표와 구분한다.

별도 레거시 native_en_* 5report/120원천 및 native_ko_* 6report/133원천도 메타데이터에 존재한다. 이는 이번 native_full_* 집계와 다른 이름의 구획이므로 조용히 더하지 않았다. 합집합796/551도 저장소의 모든 시대·모든 경로를 합한 전체 native 완료량이라는 주장은 아니다.

### 10.4 패킷 경계·미수입·누락

native ID는 선택된 원천의 식별자여서 구간 안에서 연속적이지 않다. 아래 ID 범위는 그 시각에 관측한 게시본의 최소~최대일 뿐 그 사이 모든 원천을 끝냈다는 뜻이 아니다.

| 구획·패킷 | 기준 시각 게시 원천 | 같은 파일 SHA 수입 선언 | 경계 |
|---|---:|---:|---|
| EN17 | 1 | 0 | id4174만 현재 게시 경로에 있음. 봉인24개 대비23개는 이 게시 경로에서 미확인 |
| EN18~27 및29 | 264 | 264 | 각24개 |
| EN28 | 23 | 0 | 8121~8339, **8150 미게시** |
| EN30~38 | 216 | 0 | 각24개 |
| EN39 | 23 | 0 | 11970~12406, 봉인 원천12420 미게시 |
| EN40 | 5 | 0 | 12425~12494까지만 관측, 봉인24개 대비19개 미게시 |
| KO15~24 | 240 | 240 | 각24개 |
| KO25~28 | 96 | 0 | 각24개 |
| KO29 | 23 | 0 | 13812~17316, 봉인 원천17294 미게시 |
| KO30 | 24 | 0 | 17455~17849 |
| SFT37~64 | 448 | 448 | 각16원천, source_index740~1195 |
| SFT65~93 | 464 | 0 | 각16원천, source_index1196~1666 |

따라서 게시돼 있으나 같은 파일 SHA로 아직 수입되지 않은 분량은 **EN268·KO143·SFT464원천**이다. SFT464에는 세 변형256원천/768variant와 영변형208원천이 따로 포함된다. native HOLD의 미수입도 이 원천 집계에는 남기지만 그것을 바로 학습에 들어갈 텍스트로 계산하지 않는다. 패킷17 같은 과거 경계의 “현재 게시 경로 미확인”은 다른 과거 증거까지 부재한다는 결론과 다르다.

사용자가 알려 준 **EN8150은 미게시 경계오류로 누락에 남긴다.** 새 판정·완료 원천으로 가산하지 않았으며, 나머지 미게시 ID의 원인도 이 메타데이터 집계만으로 경계오류라고 추정하지 않는다.

SFT1273은 published/sft_000069/1273.json에 세 종류가 있으므로 위590원천/1,770variant 안에서 **한 번만** 센다. 사용자 고지의 v1 literal-LF 문제는 **미채택 품질 경고**로 보존한다. 이전/재보고를 새3변형으로 한 번 더 가산하지 않았고, 이 파일 SHA의 수입 선언도 기준 시각에는 없었다. 이번 읽기 작업은 해당 문장이나 줄바꿈의 의미 재검수를 수행한 것이 아니다.

새 검수 요청 경로의 정본은 총괄 지시대로 WSL의 /home/uranus/tinyLM/review_request/다. 과거 Windows 경로나 구간 채팅을 새 검수 요청의 정본으로 대체하지 않는다. 이 절을 작성하기 위해 그 경로를 열거나 검수·게시한 것은 아니다.

### 10.5 재현 명령과 결과 해석

다음은 **파일을 만들지 않는 일회성 Python3 표준 라이브러리 읽기**다. 고정 mtime 기준, 게시 파일/영수증/봉인 ID·원문 SHA, 닫힌 수입 선언·manifest의 연결을 재현하며 원문·messages를 출력하지 않는다. imported의 JSONL, 원천 원본 전문 경로, 모델·토크나이저 라이브러리에는 접근하지 않는다. 위 고정 시각 이후 파일 수는 계속 달라질 수 있으나 같은 기준 시각 게시본이 변경되지 않았다면 핵심 수치는 유지된다. 출력의 “수입 선언”과 “미수입”은 §10.1의 메타데이터 정의를 따른다.

~~~bash
python3 -B - <<'PY'
import json, hashlib, re
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

base=Path('/home/uranus/tinyLM/data_cache/p106b_text_work_20261022')
cut=1792709944377053410
seen={}
def read(p):
    first=p.stat()
    if first.st_mtime_ns>cut:
        return None
    raw=p.read_bytes()
    last=p.stat()
    assert (first.st_size,first.st_mtime_ns)==(last.st_size,last.st_mtime_ns),str(p)
    digest=hashlib.sha256(raw).hexdigest().upper()
    seen[str(p.relative_to(base))]=digest
    return json.loads(raw),digest
def digest_value(value):
    value=str(value).upper()
    assert re.fullmatch('[0-9A-F]{64}',value),value
    return value
def lane_name(name):
    for part,lane in (('native_full_en_','en'),('native_full_ko_','ko'),
                      ('native_en_','legacy_en'),('native_ko_','legacy_ko'),
                      ('sft_','sft')):
        if part in name:
            return lane
    return None
packets={}
for p in sorted((base/'packets').glob('*.json'))+sorted((base/'publish_receipts'/'source_packets').glob('*.json')):
    item=read(p)
    if item is None:
        continue
    obj,sha=item
    rows={}
    if 'sources' in obj:
        for row in obj['sources']:
            index=int(row['source_index'])
            rows[index]=(str(row['source_id']),digest_value(row['source_line_sha256']))
    elif 'documents' in obj:
        for row in obj['documents']:
            index=int(row['id'])
            rows[index]=(str(index),digest_value(row['sha256']))
    if rows:
        assert sha not in packets or packets[sha]==rows
        packets[sha]=rows

receipts=defaultdict(list)
for p in sorted((base/'publish_receipts').glob('*/receipt.json')):
    item=read(p)
    if item is None:
        continue
    obj,_=item
    if obj.get('exit_code')!=0 or obj.get('published_by_this_attempt') is not True:
        continue
    final=Path(obj['final'])
    final=final if final.is_absolute() else base.parents[1]/final
    src=obj['source_before']
    receipts[final].append((int(src['id']),
        digest_value(src.get('declared_source_line_sha256',src.get('original_text_sha256'))),
        digest_value(obj['packet_before']['sha256']),
        digest_value(obj['final_observation']['sha256'])))

imported=defaultdict(set)
held=defaultdict(set)
authored=set()
triage=set()
report_count=Counter()
exact=defaultdict(set)
variant_rows=0
for p in sorted((base/'imported').glob('*/report.json')):
    item=read(p)
    if item is None:
        continue
    obj,_=item
    lane=lane_name(p.parent.name)
    if lane is None:
        continue
    sha=digest_value(obj['packet_sha256'])
    rows=packets[sha]
    files=obj.get('response_files')
    indices=[int(Path(name).stem) for name in files] if files else list(rows)
    assert len(indices)==obj['source_rows'],str(p)
    manifests=[]
    for mp in sorted(p.parent.glob('*manifest*.json')):
        mi=read(mp)
        assert mi is not None,str(mp)
        manifest,_=mi
        lineage=manifest['lineage']
        for field in ('packet_sha256','response_sha256','kind','training_admission'):
            assert lineage[field]==obj[field],(str(mp),field)
        if files:
            assert lineage['response_files']==files,str(mp)
        assert sum(x['rows'] for x in manifest['shards'])==manifest['rows'],str(mp)
        assert sum(x['bytes'] for x in manifest['shards'])==manifest['bytes'],str(mp)
        manifests.append((mp.name,manifest['rows']))
    output_name='authoring' if lane=='sft' else 'review'
    assert sum(n for name,n in manifests if name.startswith(output_name))==obj['output_rows'],str(p)
    report_count[lane]+=1
    keys={index:(lane,)+rows[index] for index in indices}
    imported[lane].update(keys.values())
    held[lane].update(keys[int(index)] for index in obj.get('held_source_ids',[]))
    if lane=='sft':
        zero={int(index) for index in obj.get('triage_only_source_ids',[])}
        assert len(zero)==obj.get('triage_only_source_rows',0),str(p)
        assert obj['output_rows']==3*(len(indices)-len(zero)),str(p)
        authored.update(key for index,key in keys.items() if index not in zero)
        triage.update(keys[index] for index in zero)
        variant_rows+=obj['output_rows']
    for name,file_sha in (files or {}).items():
        exact[lane].add((sha,name,digest_value(file_sha)))

published={}
for lane,pattern in (('en','native_full_en_*'),('ko','native_full_ko_*'),('sft','sft_*')):
    keys=set()
    matched=set()
    decisions={}
    threes=set()
    zeros=set()
    variants=set()
    packet_ids=defaultdict(set)
    nfiles=0
    newest=0
    new_files=0
    for p in sorted((base/'published').glob(pattern+'/*.json')):
        item=read(p)
        if item is None:
            new_files+=1
            continue
        obj,file_sha=item
        index=int(obj['source_index'] if lane=='sft' else obj['id'])
        valid=[r for r in receipts[p] if r[0]==index and r[3]==file_sha]
        assert valid,str(p)
        bound={(r[2],packets[r[2]][index]) for r in valid}
        assert len(bound)==1,str(p)
        packet_sha,source=next(iter(bound))
        assert all(r[1]==source[1] for r in valid),str(p)
        key=(lane,)+source
        assert key not in keys,str(p)
        keys.add(key)
        packet_ids[p.parent.name].add(index)
        nfiles+=1
        newest=max(newest,p.stat().st_mtime_ns)
        if (packet_sha,p.name,file_sha) in exact[lane]:
            matched.add(key)
        if lane=='sft':
            entries=obj['variants']
            kinds={entry['kind'] for entry in entries}
            assert len(entries) in (0,3) and len(entries)==len(kinds),str(p)
            if entries:
                assert kinds=={'ko_translation','ko_rephrase','en_rephrase'},str(p)
                threes.add(key)
                variants.update((key,kind) for kind in kinds)
            else:
                zeros.add(key)
        else:
            assert obj['decision'] in ('KEEP','REWRITE','HOLD'),str(p)
            decisions[key]=obj['decision']
    published[lane]=keys
    print(json.dumps({'구분':lane,'게시파일':nfiles,'고유원천':len(keys),
        '판정':dict(Counter(decisions.values())),'세변형원천':len(threes),
        '영변형분류원천':len(zeros),'고유변형':len(variants),
        '수입선언과세변형교집합':len(matched&threes),
        '수입선언과영변형교집합':len(matched&zeros),
        '같은파일해시수입':len(matched),'미수입':len(keys-matched),
        '패킷':len(packet_ids),'마지막수정한국시각':datetime.fromtimestamp(newest/1e9,timezone(timedelta(hours=9))).isoformat(),
        '기준시각뒤추가파일':new_files},ensure_ascii=False,sort_keys=True))
for lane in ('en','ko','sft','legacy_en','legacy_ko'):
    old=imported[lane]-published.get(lane,set())
    print(json.dumps({'보고구분':lane,'보고수':report_count[lane],
        '수입선언고유원천':len(imported[lane]),'게시와교집합':len(imported[lane]&published.get(lane,set())),
        '수입선언만존재':len(old),
        **({'과거분보류선언':len(old&held[lane])} if lane!='sft' else {}),
        '게시와수입선언합집합':len(imported[lane]|published.get(lane,set()))},ensure_ascii=False,sort_keys=True))
print(json.dumps({'수입선언세변형원천':len(authored),'수입선언영변형원천':len(triage),
    '수입선언변형행':variant_rows,'선언분류교집합':len(authored&triage),
    '읽은파일수':len(seen),'입력목록해시':hashlib.sha256(json.dumps(sorted(seen.items()),separators=(',',':')).encode()).hexdigest().upper(),
    '재집계한국시각':datetime.now(timezone(timedelta(hours=9))).isoformat()},ensure_ascii=False,sort_keys=True))
PY
~~~

### 10.6 주장하지 않는 것

확인한 수입 report의 training_admission=NOT_ADMITTED, semantic_review=PENDING 경계는 유지한다. 게시 성공·파일 수·세 종류 객체·수입 선언의 일관성은 원문 의미 전수검수, 실제 학습 투입, 번역 품질, 새 코퍼스 완성이나 모델 성능의 증거가 아니다. 실제 shard 전체 해시, tokenizer별 토큰량, 언어 자동 판별, 원천 문장 품질은 이번 집계의 미실행 범위다. 기준 시각 이후의 증가나 위 경계 누락을 임의로 채우지 않았다. 새 분석 코드 파일·원본/게시/수입 변경·Git·설치·GPU/모델 실행도 없다.

### 10.7 이번 작업의 정정 기록

1. 상위 에이전트에게 보낸 범위 질의에서 **한국어가 아닌 단어가 섞인 표현**을 사용했다. 잘못을 즉시 한국어로 정정했으며 그 표현은 이 문서에 재인용하지 않는다. 이후 자연어 보고는 한국어로 제한한다.
2. 영수증 구조를 살피던 중 **source_before 사전 전체를 도구 출력한 실수**가 있었다. 그 안의 resolved_ranges.normalized_boundary_ack에 원문 일부가 포함돼 ID·원문 SHA만 출력한다는 승인 경계를 넘었다. 원문 전문을 출력한 것은 아니지만 부분 내용도 허용 출력이 아니었으므로 이를 정상적인 메타데이터 출력이라고 축소하지 않는다. 원천 파일 변경은 없었고 해당 내용을 문서에 복사하지 않았다. 이후는 ID·명시 SHA·판정 등 허용된 스칼라 필드만 명시 추출하며, 위 재현 명령 역시 원문·메시지·범위 확인 문구를 출력하지 않는다.

## 11. Stage7c0W/7cW/7dW/7eW 설계 검토 — ALM 연결·부호·같은 출발점

검토 대상은 [P106B 사전 설계](/home/uranus/tinyLM/test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md:7434)다. **기존 한-update 엔진과 ALM core의 연결점은 실제로 존재한다. TRAIN 한 묶음의 분리 gradient로 고정 λ를 정한다는 선택A도 명확한 제한 실험으로 해석할 수 있다.** 다만 마지막 블록의 MLP 참조, optimizer factory의 기준 배율/WD, 음수 gold-NLL 계수와 확률 경계, 교정·cost 이후 초기화, 공백을 보존한 채점은 구현에서 별도로 닫아야 한다. 아래는 소스·설계 검토이며 실제 gradient·시간·품질의 예측이나 입장 PASS가 아니다.

exp-preflight로 현재 기준표 §1/§2/§3/§7과 새 조건을 대조하고, impact-analysis로 기존 중복·영향·세 대안을 확인했다. 선택A의 유지가 검토 의견이며, B의 임의 λ나 C의 온라인 GradMag를 새로 채택하지 않았다. 레지스트리 조회 프로그램·회귀·모델·CP·토크나이저·자료 행 로딩은 실행하지 않았다. 계획서가 보고한 태그/유사 검색 결과는 총괄의 관측으로만 읽었다.

| 경로·소유 | 이번 동작 | 제외 |
|---|---|---|
| P106B 계획·기존 ALM/엔진/optimizer/모델·평가 소스 | 읽기 전용 추적 | 코드·계수·문턱 수정0 |
| 이 연구 문서 | 이번 §11 추가 | 다른 계획/결과/기준표/원장 수정0 |
| 실제 cache·TRAIN/DEV·부모/학생·GPU | 접근·실행하지 않음 | full64 완료·실물 시작 상태·수치·비용·품질은 미검증 |

### 11.1 실제 seam과 새 facade가 소유할 최소 부분

[one_update](/home/uranus/tinyLM/scripts/diag_p101a_padding_gpu.py:435)는 원16×8의 순서/분모를 앞뒤 대조하고, 고정 padding→한 본체 forward→components→normalized_loss→backward를16번 수행한 다음 clip1과 AdamW/Muon step을 각각 한 번 실행한다. 따라서 새 facade의 pad_records/components/normalized_loss가 **기존 호출 규약**을 받으면 본체·학습 loop를 다시 만들 필요가 없다. policy=fixed1024, precision=bf16_eager, horizons=(), capture=False를 명시하는 연결이다. PAD 진단 execute·ABBA·crop 정책·원 P090B 부모 loader·원 diagnostic 경로를 통째로 호출하는 안은 아니다.

| 기존 구현 | 이미 있는 일 | facade/controller에 남는 일 |
|---|---|---|
| [alm.target_nll](/home/uranus/tinyLM/tinylm/train/alm.py:19) | 원 main tied head의 valid gather·head checkpoint·FP32 CE·원 위치 scatter | 두 팔 같은 head chunk/AMP/checkpoint를 고정하고 이 NLL을 CE/KD에 한 번만 사용 |
| [alm.chunk_kl](/home/uranus/tinyLM/tinylm/train/alm.py:108) | 명시 위치·무감독/겹침/비연속·teacher sentinel 거부, chunk 합·binary KL | 캐시의 student_shifted_indices→현재 micro의 행 재배치, 같은 원천/턴/byte/target 검산 |
| [alm.normalized_loss](/home/uranus/tinyLM/tinylm/train/alm.py:143) | CE/N + λ·KL/K, 전체 update 분모 | 매128행의 N과 K를 업데이트 전에 별도로 동결하고 helper에 전달 |
| [update_plan](/home/uranus/tinyLM/scripts/diag_p101a_padding_gpu.py:336) | 정확16micro×8·원 x/y/owner·CE target·padding slot의 봉인 | cache 행/채택 chunk 순서·K·λ/τ는 원 plan에 없으므로 별도 봉인 |
| [closed_batch](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:935) | 닫힌 report/원시·cache shard/행 SHA·언어별16행 계약 검산 | 서로 다른64배치와1024 고유 row의 전체 연결, 실제 cache 행 소비 |

one_update가 넘기는 분모 사전은 CE의 {1:N}뿐이다. 새 normalized_loss가 이를 K로 오해하거나 normalized_loss의 세 번째 빈 weights 사전에서 λ를 찾으면 안 된다. K·고정 λ는 새 facade의 **현재 update 계약**에 있어야 한다. sums[1]/counts[1]은 순수 CE 합/CE target 수로 유지한다. 원 엔진의 result.loss는 이 값으로 만든 CE이며 결합 목적이 아니다. KL 합/K·λ·실제 목적·언어별 CE/KD 분모와 coverage는 새 사건/요약에 별도로 남겨야 한다.

원 Record에는 cache row ID가 없다. 동일 토큰열을 갖는 서로 다른 원천도 있으므로 x/y hash만으로 cache를 선택하지 않는다. controller가 동결 row ID·원문/준비/cache 행 SHA와 Record의 병렬 맵을 만들고 shuffle에 함께 적용해야 한다. components가 micro cursor를 사용한다면 실제16회 소비와 종료를 검산한다. head checkpoint의 재계산은 components/cursor를 다시 진행하지 않고 고정 NLL 인자를 다시 계산해야 한다.

[encode_record](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:26)는 이미 raw i→shifted i−1를 적용했다. cache의 student_shifted_indices를 또1 빼지 않는다. padded y의 해당 ID·양의 segments·원 assistant turn·byte 사건을 모두 확인한다. ALM helper는 supervised 여부는 확인하지만 **같은 turn인지·EOT가 아닌지·캐시가 같은 원문인지까지 대신 확인하지 않는다.** EOT의 CE 보존/모든 special의 KD 제외는 facade 입장 계약이다.

micro의 chunk0은 전체 K>0이면 허용한다. 전체 K0인 update에 λ>0이면 원 core대로 실패하며 행 교체·micro 생략·λ0 대체를 하지 않는다. CE-only의 λ0은 KL을 역전파하지 않을 뿐 아니라 **불필요한 KL 계산도 건너뛰는 분기**가 적합하다. 먼저 무한/비정상 KL을 만든 뒤0을 곱하면 CE-only까지 NaN·경계 오류에 끌려갈 수 있다. cache/원천 계보 검산은 두 팔 공통이다.

### 11.2 한 loss 안의 부호 — “정답 CE를 항상 더 강화”하는 목적이 아니다

현재 core를 식으로 쓰면 다음과 같다. N은 EOT를 포함한128행 전체 CE target 수, K는 수락한 chunk 수다. ℓ_i는 원 shifted target의 NLL이며 chunk끼리 target 위치는 겹치지 않는다.

~~~text
S_j = Σ(i∈chunk j) ℓ_i
s_j = −S_j/τ,    t_j = 교사 raw chunk logp 합/τ
qS_j = exp(s_j), qT_j = exp(t_j)
L = (Σ_i ℓ_i)/N + (λ/K) Σ_j KL(Bernoulli(qT_j) || Bernoulli(qS_j))

0 < qS_j < 1일 때:
∂KL_j/∂S_j = (qT_j−qS_j) / [τ·(1−qS_j)]

수락 chunk의 각 gold NLL에 걸리는 결합계수:
c_j = 1/N + (λ/K)·(qT_j−qS_j)/[τ·(1−qS_j)]
KD 밖 target 및 EOT의 계수 = 1/N
~~~

이는 소스 식을 미분한 **해석**이지 실물 gradient 관측이 아니다. qT>qS면 해당 gold NLL을 더 줄이는 방향이고, qT<qS면 CE를 약하게 하거나 상쇄할 수 있다. 더 나아가 λN(qS−qT)>Kτ(1−qS)이면 c_j<0여서 그 target의 NLL을 늘리는 방향까지 허용한다. 이는 그 자체로 구현 버그나 “교사 오답 판정”이 아니라 교사의 낮은 reference 확신도를 전달하는 현 binary 목적의 성질이다. c_j의 최소/최대·음수/영 근처/양수 chunk와 학생 target·byte 질량을 언어별로 관측하고, 분모 N/K·원 logq·길이와 함께 보존하는 것이 계획의 “음수/상쇄 공개”를 구현하는 최소 증거다. 값을 양수로 잘라 버리거나 negative chunk를 제외하면 다른 목적이 된다.

τ=100은 **chunk log 확률을100으로 나누는 것**이다. 전체 vocab logits를 temperature100으로 softmax하는 KD와 같지 않다. token 수로 chunk 합을 평균하거나 τ²를 곱하는 것도 원 사전식에 없다. 현재 loss의 FP64는 작은 chunk logp/KL 벡터에 한정되고 본체·원 tied head가 FP64가 된다는 뜻이 아니다.

[binary_kl_logq](/home/uranus/tinyLM/tinylm/train/alm.py:74)의 경계는 유지해야 한다.

- qS=1, qT<1은 StudentProbabilityBoundary로 실패한다. NLL이 FP32에서0으로 반올림된 경우도 포함하며 임의 epsilon clip·CE-only 자동전환으로 숨기지 않는다.
- 교사 logq=0, 즉 qT=1은 별도 −s 분기가 있다. 위 일반식을 그대로0/0 계산하지 않는다. 교사가 고정된 이 분기에서 student logq에 대한 미분은 −1이며, 값0이라는 이유로 gradient도0이라고 대체하지 않는다.
- 양수 logp·비유한 값·native sentinel·K0은 각기 다른 오류다. 아주 음수인 유한 logq가 exp에서0으로 보이는 현상은 원 logq와 구분해 기록한다. q의 표시값만 남기면 포화/underflow와 실제 확신도 차이를 가릴 수 있다.
- 이론적인 KL 비음수, 부동소수점 상쇄로 생길 수 있는 아주 작은 음수 값, 위 c_j 음수는 서로 다른 문제다. 절댓값·0 clamp·유리한 허용치 재조정으로 합치지 않는다.

기존 [ALM 회귀 소스](/home/uranus/tinyLM/scripts/test_p106b_alm_core.py:27)에 scalar oracle/finite difference·교사 detach/qT1·동일분포0·원 tied head 전체 gradient·비선형 KL·불균등 micro/0KD·qS1 분류가 있다. 이것을 새 구현으로 중복할 이유는 없지만, 새 facade의 c_j 부호·EOT/turn·row 맵·분모/λ 연결은 별도 회귀 대상이다. 이 담당자는 해당 시험을 실행하지 않았다.

### 11.3 TRAIN-only ρ=.25 교정의 의미와 가장 중요한 블록 선택 함정

**마지막 블록을 단순히 layers[-1].parameters()로 잡으면 그 블록이 실제 사용하는 MLP가 빠진다.** [Layer](/home/uranus/tinyLM/tinylm/model/modules.py:211)는 MLP를 self.mlp=[mlp]라는 일반 리스트로 보관해 모듈 등록을 피한다. 실제 MLP는 [Transformer 초기화](/home/uranus/tinyLM/tinylm/model/transformer.py:92)의 coda_mlps 등에 따로 등록돼 있다. 따라서 layers.13. 접두사만 고르는 방법도 같은 누락을 만든다. 공유 attention은 _attn_ref 리스트를 쓸 수 있다.

계획의 “마지막 실제 블록”을 그대로 구현하려면 실제 visit schedule의 마지막 index와 owner를 기록한 뒤, **블록 자체의 등록 파라미터 ∪ block.mlp[0] ∪ block.attn_mod의 trainable Parameter를 객체 ID로 중복 제거**하고 model.named_parameters의 정본 이름에 매핑해야 한다. 정본 이름·shape·dtype·소유/참조·parameter 수/원소 수와 그 SHA를 남긴다. 마지막 모듈 밖의 head/공유 embedding·norm_f와 앞선 CLA owner의 K/V는 이 proxy에 자동 포함되지 않는다. 이를 누락 오류와 혼동하지 말고 proxy 범위로 명시한다. last block MLP를 제외한 좁은 부분집합으로 측정해 놓고 같은 실험명으로 “마지막 실제 block 교정”이라 부르면 안 된다.

gCE=∇_P(CE 합/N), gKD=∇_P(KL 합/K)에서 P가 위 고정 proxy다. λ=.25·||gCE||/||gKD||는 **λ를 곱하기 전 KD gradient**로 계산해 일반 고정 수치로 저장한다. λ 계산 그래프를 학습 loss 안에 남기거나 epoch마다 다시 맞추지 않는다. CPU FP64 norm 통계를 쓰더라도 gradient 피연산자는 실제 BF16 eager forward/FP32 master 경로에서 얻은 것이며 CPU toy 허용치를 실물 BF16 오차 보증으로 사용하지 않는다.

64KO+64EN의 분리 결과는 **같은128행 N/K**를 써야 합산 global gradient를 복원할 수 있다. 언어별 N언어/K언어로 따로 평균한 벡터를 평균하면 원 목적과 달라진다. global norm은 언어별 norm의 합이 아니라 두 gradient 벡터 합의 norm이고, global cosine도 두 cosine의 평균이 아니다. 언어별 자체 평균의 부진단을 추가한다면 이와 다른 단위임을 표시한다.

정확 산술과 같은 P/배치에서 교정이 성립하면 ||λgKD||/||gCE||=.25이며, 결합 raw gradient의 norm은 CE의.75~1.25배, gCE와의 내적은 최소.75||gCE||²다. **이 조건부 수학 관계는 개별 c_j 양수, 전체 모델의 같은 비율, 다음 update의 비율, clip 후 크기, AdamW/Muon update가25%라는 보장이 아니다.** 특히 Muon은 BF16 Newton–Schulz의 방향/형상 정규화를 적용하므로 raw gradient norm 비를 최종 가중치 이동 비로 읽을 수 없다. 실제 달성 비율·cosine과 언어별 차이를 그대로 남긴다.

None 정책은 소스 기반의 사전 명단으로 닫아야 한다. 실제0 tensor와 미연결 None을 같은 학습 상태로 바꾸지 않는다. 통계 벡터의 공통 좌표에서 None을0으로 표시할지와 오류로 볼지, 양쪽/한쪽 None을 각각 기록하며 임의 누락하지 않는다. 전체 CE/KD norm0·비유한·필요 graph 단절은 계획대로 HOLD다. 어떤 micro의 KD0은 global K>0일 때 허용되는0 기여이지 전체 graph 실패가 아니다. 교정용 .grad를 정리하면서 None↔0 tensor를 바꾸어 본학습 optimizer의 첫 상태에 남기지 않는 것도 회귀 대상이다.

### 11.4 optimizer 배율·WD와 교정/cost 뒤 같은 시작 상태

“기존 SFT factory의0.1배”는 **정확한 함수**를 적지 않으면 두 배 차이를 만들 수 있다.

| 재사용 후보 | 원 반환 LR | 추가0.1배의 결과 | WD/검증 주의 |
|---|---|---|---|
| [diag_p101a_sft_mtp.optimizers](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:132) | Adam1e-4/Muon4e-4 | 계획의1e-5/4e-5 | Adam embedding 그룹의 원 WD.1이 남으므로 **양 optimizer의 모든 group WD0을 명시**해야 함 |
| [native_weight_route.make_optimizers('sft')](/home/uranus/tinyLM/scripts/diag_p106b_native_weight_route.py:618) | 원 factory에 이미.5배: Adam5e-5/Muon2e-4 | 5e-6/2e-5로 계획의 절반 | 이미 전 group WD0이나 기존 endpoint validator는 원.5배 규약에 묶임 |

최소 연결은 첫 factory에서 fresh optimizer를 만들고 계획의0.1배·전 group WD0을 새 controller가 명시 검산하는 방식이다. 원 factory/validator 자체는 수정하지 않는다. [matrix_decay_groups](/home/uranus/tinyLM/tinylm/train/optimizer_audit.py:43)의 matrix WD0은 비행렬 WD0을 뜻하지 않는다는 점이 핵심이다. group별 정본 이름/소유 SHA·LR·WD·Adam betas/eps·Muon rms/ns_steps/momentum/nesterov를 두 팔에 기록하고 모든 trainable Parameter가 정확히 한 group에 속함을 확인한다. [split_params](/home/uranus/tinyLM/tinylm/train/muon.py:144)는 공유 embedding을 Adam 쪽에 두고 중복 제거한다.

양팔 초기화 기준은 원 Native595-F의 strict CP/header/float route/core다. [native595.loaded_runtime](/home/uranus/tinyLM/scripts/diag_p106b_native595.py:516) 같은 학습 가능한 loader를 사용하되, 원 수동 selected_runtime의 freeze·종료 불변 계약을 완화해 가져오는 것은 금지한다. 원 CP가 weight-only이므로 둘 다 fresh optimizer라는 해석은 맞다. 원4543 optimizer 상태를 resume하거나 원 P090B parent_ntp의 가중치를 대신 쓰면 비교가 아니다.

교정은 optimizer step0·clip0이며 같은 본체/정밀도/checkpoint/route 아래 분리 gradient만 측정한다. 가중치뿐 아니라 CPU/CUDA RNG·학습 mode·requires_grad·cfg flags·활성 route·남은 .grad와 optimizer state를 전후 검산한다. forward가 만드는 일시 cache는 정리하고 새 학습 입장에 남기지 않는다. 가장 명확한 격리는 교정 종료 뒤 부모에서 양팔을 새로 로드하는 것이며, same-process라면 같은 상태 증거가 필요하다.

7d의 각2update는 **측정용 학습**이지만 새 자식 CP0이고 본32회에는 산입하지 않는다. 7e를 그 가중치/모멘텀에서 이어가면 실제34update가 되어 계획을 위반한다. 각 cost팔 및 각 본팔은 원 부모에서 다시 시작하고 같은 첫 데이터 순서/RNG/optimizer 상태를 맞춰야 한다. 본32회 사이에는 optimizer를 epoch마다 reset하지 않는다. 낮은 LR·고정 λ라도 뒤의 gradient/norm/cosine이 유지된다고 미리 주장하지 않는다.

양팔 모두 같은 alm.target_nll·chunk 크기·checkpoint·BF16 eager·TF32 OFF·fixed1024이므로 독립변수를 고정 λ의 binary KL 추가로 좁힐 수 있다. 원 mtp_sft.components와 ALM CE를 서로 다른 팔에 쓰거나 한 팔만 compile/다른 padding을 쓰지 않는다. λ0 facade와 같은 CE 경로의 직접 loss/gradient·한 update를 대조하는 회귀, tied embedding의 입력/출력 및 emb_up 기여를 모두 포함한 검산이 최소 연결 증거다. 과거 PAD의 수치 음성을 통과로 바꾸거나 그 허용치를 완화하는 검토가 아니다.

새 weight-only CP에는 parent4543 계보와 **이번 curriculum의 실제32update**·λ/ρ/τ·route/tokenizer·1024선택/64cache/코드/optimizer 정책 SHA를 구분해 넣는다. 새 자식을 원 native595의4543 완료 header·수동 추론 manifest로 위장하거나 덮어쓰지 않는다. 새 child descriptor/strict loader가 별도 책임이며 weight-only CP만으로 optimizer 연속 재개를 주장할 수 없다.

### 11.5 학습량·평가·비용·허용 주장

128행/update이므로1024행은 epoch당8update,4epoch은 **각 팔32update/4096행 노출**이다. padded slot은 각 팔32×8×16×1024=4,194,304다. 계획의 실제 x1,025,068·CE23,588은 고유 x256,267·CE5,897의4배와 산술상 맞는다. 이 담당자가 실제 준비 행을 재로딩해 검산한 값은 아니다. 양팔 합계64 본update와 별도4 costupdate·교정0update를 섞지 않는다. 표준 CPT의 풀≥2배 조건을 반복 SFT1024에 억지로 적용하거나75M×4 달성으로 환산하지 않는 계획 해석은 타당하다.

| 평가 | 재사용·필수 경계 | 주장할 수 없는 것 |
|---|---|---|
| 전체 DEV512 TF | 부모/두 자식 같은 원 DEV·CE target/EOT·head/정밀도·분모 | 새 독립 test, 문장 의미 정답률 |
| DEV 고정64첫답, KO/EN각32 | source/root/행/별도 prompt SHA·순서·aliases와 채점 규칙을 첫 평가 전에 고정, greedy·max64·재시도0 | 64개만 보고 전체 DEV/일반 대화 성공·통계적 우위 |
| 고정 사용자8 | 같은 원문·단일/이력·prompt/생성 옵션·원답·종료를 별도 보존 | 맹검 미사용 test나 대규모 능력 점수 |
| native32 손실 | [native_probe](/home/uranus/tinyLM/scripts/diag_p106b_native_weight_route.py:660)의 같은 SHA·첫32×1024·32,768 targets·FP32 MATH를 활성 float route 안에서 재사용 가능 | 전체 native VAL, KO/EN 각각의 보존 보증 |

**공백 보존 채점에는 기존 clean_eval.score를 그대로 쓰면 안 된다.** [현 함수](/home/uranus/tinyLM/scripts/diag_p101a_clean_eval.py:21)는 answer.strip()==expected.strip()다. 계획의 strict whitespace-exact는 인증된 마지막 EOS/EOT만 제거한 raw 답과 원 주석의 공백까지 비교해야 한다. strip/정규화/aliases 일치를 보조로 남기더라도 서로 다른 이름의 지표로 둔다. [answer_from_tokens](/home/uranus/tinyLM/scripts/interactive_research_infer.py:517)는 인증된 마지막 종료만 제거하고 skip_special_tokens=False로 본문을 보존하는 낮은 층이다. 역할 표식·줄바꿈·실패 답을 임의 정리하지 않는다.

원 [engine.evaluate](/home/uranus/tinyLM/scripts/diag_p101a_sft_mtp.py:143)는 BF16 TF CE다. 이를 쓰면서 FP32 평가라고 쓰지 않는다. DEV TF의 정밀도·head chunk와 첫답 FP32 MATH·native32 FP32 MATH는 서로 구분해 세 종점에 동일하게 고정한다. 추론의 eval/freeze 뒤 학습으로 돌아간다면 clear_quant 및 원 train mode 복원이 필요하다. 모델 상주 없이 이 문서를 쓰는 현재는 선택64/사용자8의 실제 prompt와 독립성·첫답 실행을 확인한 것이 아니다.

7c의 마지막 block gradient 계측도 본체 forward와 head 계산·checkpoint 재계산을 요구한다. 교정 proxy만 작다고 공짜 CPU 계산이 되지는 않는다. 분리 CE/KD 역전파의 graph 유지 또는 재계산·CPU 복사/FP64 통계 시간, source/cache/부모 SHA 검산·기동·종료를 별도 기록해야 한다. 7d 두 update는 cold/두 번째 비용을 보는 작은 측정이지 정상상태 분산·compile 이득 증거가 아니다. 최종 입장에는 느린 팔의 관측 update wall과 실제 남은 학습/세 종점 평가·해시/저장/정리 여유를 모두 넣는다. 기존 PAD나704회 다른 trainer 시간을 이번 head/KL 비용으로 대체하지 않는다.

원 padding 진단의 wall_limit/validate_execution은60~1200초와 옛 diagnostic mode/namespace에 고정돼 있다. 새2시간 운영 상한을 그 validator의 문턱 상향으로 구현하지 않는다. 새 controller가 자신의 사전 phase cap·aware deadline·외부 watchdog·20MB 미만 shard/partial 보존을 소유하고, 기존 one_update의 guard.check를 이용하는 연결이다. 학생 입장은64cache 전량의 닫힌 계보·교사 종료 확인 뒤다. 한 팔만 완료하거나 마지막 update 뒤 종료 검산/CP가 미완이면 불완전 대조를 그대로 남긴다.

### 11.6 읽기 전용 preflight 결론

| 항목 | 정 검토 상태 | 남은 최소 증거 |
|---|---|---|
| 독립변수·기존 중복 | 설계상 명확 | 같은 Native595-F/원1024 CE에 고정 binary KL만 추가; engine/core 중복 구현0 |
| 학습량·epoch·분모 | 산술 일치, 실물 미조회 | 실제32개 ordered update/언어별 N·K·target·같은 shuffle 검산 |
| 마지막 block 교정 | **참조 MLP를 포함한 범위 명시 필요** | canonical parameter 집합/공유 ID 제거·None 정책·실물 norm/cosine·고정 λ |
| optimizer·시작 상태 | **정확 factory/WD/배율 및 reset 검산 필요** | 두 팔 group 계약·fresh state·교정/비용 이후 같은 core/RNG/grad 초기값 |
| loss 부호·확률 경계 | 원 core 식으로 확인 | c_j/경계별 합성 oracle와 실제 언어별 부호 질량·logq 보존; clipping/자동구제0 |
| 자료·cache·loader | 설계 계약만 검토 | v3 정확 SHA·64 닫힌 배치·실제1024/parent/float route 입장 증거 |
| 평가 | 제한 진단으로 타당 | strict whitespace-exact와 strip 보조 분리·같은64/8/32·정밀도/원답 |
| 태그·회귀·시간/VRAM | 담당자 재실행 없음 | 총괄의 등록/회귀·실제7c/7d 및 남은 절대시간 판정 |

권고는 **선택A의 제한된 목적/고정계수를 유지하고 위 누락 가능한 계약만 명시적으로 검산**하는 것이다. 선택B는 단순하지만 분모·τ에 따른 실효 신호가 미정이고, 선택C는 매-step 조절기·논문 GradMag라는 별도 최적화 문제와 더 큰 검증 비용을 추가하므로 이번 좁은 연결 검증과 구분하는 계획의 세 대안 비교에 동의한다. 이번 읽기에서 어떤 방법이 실제로 더 좋은 답을 만들지, λ가 얼마가 될지, 시간/메모리 상한을 통과할지는 예측하지 않는다. native595-F의 단일 seed·32update 결과는 이 작은 reference 확신도 신호의 조건부 대조이지 ALM 전체·별도어휘 full-vocab KL·일반 thinking·원600M 자료 인과성의 판정이 아니다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 12. v4 답 본문 범위 정렬 helper — 별도 template 계약

총괄의 직접 전달 관측은 v3 canary의 cold/warm chosen logp −27.07450676 대 −27.11883163 및 top2 ID 변화, reference 숫자 앞의 교사 top1 사고 시작 표식이다. 이 담당자가 서버/원시 로그를 다시 실행·검산한 값은 아니다. v3의 동일 전체 template 계약과 실패 원형은 보존하며, 이를 확률 정합 PASS로 승격하지 않는다. 이번 새 권한은 서로 다른 native template에서 **원 답 본문 byte가 같은 지정 범위만** 정렬하는 독립 helper와 합성 CPU 회귀다. 교사 native apply-template·enable_thinking=false·cold repeat의 실제 입장/확률은 총괄이 따로 검증한다.

### 12.1 착수 전 영향·권한

impact-analysis로 소유권과 중복을 대조했다. 기존 p106b_alm_bytes의 stream 검산·raw→shift·불변 dataclass를 재사용하고 전체 template 비교 함수의 계약은 바꾸지 않는다.

| 경로 | 승인된 동작 | 제외 |
|---|---|---|
| scripts/p106b_alm_template_alignment.py | 새 pure helper 작성 | I/O·모델·토크나이저·다운로드0 |
| scripts/test_p106b_alm_template_alignment.py | 합성/mock CPU 회귀 작성·직접 실행 | 실제 자료·교사·GPU0 |
| 이 연구 문서 | 설계/회귀 증거 기록 | 다른 계획/원장/결과 수정0 |
| 기존 bytes/core/model/cache 및 원형 산출물 | 읽기·재사용만 | 수정·삭제·Git·설치0 |

코드 영향은 새 opt-in API뿐이고 기존 caller는0이다. 자료 원형/schema migration과 정규화는 없고 기존 helper의 전체 입력 일치 요구도 그대로다. 새 반환형은 answer-relative 구간과 양쪽 full-stream 절대 구간을 따로 보존해 구계약으로 오인하지 않게 한다. 회귀는 prefix 차이·한글 byte 분절·범위 경계 token 교차·special/EOT·mask/turn·raw/shift·불일치 본문과 불변성을 다룬다. 후속 cache 연결/실제 확률/학습은 총괄의 별도 권한이며 이 helper의 PASS와 섞지 않는다.

### 12.2 연결 API

align_answer_contents(student_stream, teacher_stream, student_span, teacher_span)의 각 span은 **자체 full native stream에서 원 답 본문만 가리키는 [byte 시작, byte 끝)**이다. tuple/list의 정수2개를 받고 범위 밖·빈 범위·bool 좌표를 거부한다. 본문 byte의 완전 일치만 요구하며 prefix/template 자체를 맞추거나 바꾸지 않는다.

총괄의 연결 제안에 맞춰 반환값은 **result.alignment에 기존 AlignmentResult**, **result.metadata에 JSON 가능한 사전**을 제공한다. alignment의 byte_start/end와 input_byte_count는 이 새 API에서는 **답 내부 상대 좌표/본문 길이**다. 원 full stream의 raw index와 raw−1 shifted index는 바꾸지 않는다. alignment만 단독 저장하지 않고 metadata의 coordinate_system=ANSWER_RELATIVE_BYTE_OFFSETS, alignment_scope=ANSWER_CONTENT_BYTES_ONLY와 함께 기록해야 한다. full_template_equality_claim은 false다.

metadata의 student_span/teacher_span, student_input_byte_count/teacher_input_byte_count, answer_byte_count/covered_byte_count/uncovered_byte_count/boundary_uncovered_byte_count, student_uncovered_ranges/teacher_uncovered_ranges, 양쪽 boundary_crossing_indices/special_indices/supervised_byte_count, common_answer_boundaries 및 accepted_ranges/rejected_ranges에 각 full stream 절대 구간과 제외 이유를 보존한다. 사전은 호출마다 새로 만들어 외부 수정이 원 결과를 바꾸지 않는다.

기존 AlignedChunk/RejectedChunk의 불변 상속형을 사용하며, chunk 자체에도 student_byte_start/end·teacher_byte_start/end가 있다. 본문 가장자리가 token 안이면 원 token을 부분 절단하지 않고 해당 후보를 거부한다. 범위 안 zero-byte special이 공통 경계 내부면 enclosing chunk를 제외하고, 정확한 후보 경계면 이웃은 유지하되 길이0의 special 제외 기록을 별도로 남긴다. uncovered는 양의 길이의 거부 구간만 합산해 중복 계산하지 않는다.

숫자에 관한 총괄의 후속 정정은 첫 실제 reference가6억원이며 native id21은6, 다음173905는억원이라는 것이다. 이 담당자는 실제 reply를 재열람하지 않았으며 새 helper에는 특정 실제 ID·단어·정답을 하드코딩하지 않았다. 원시 ID/bytes/지정 구간만 사용한다.

### 12.3 실제 순수 회귀와 동결 인계

현재 새 helper는287줄, 새 시험은378줄이다. 직접 승인된 합성/mock CPU 실행은 처음 새29회귀0.054초 PASS, wrapper 연결 보완 뒤에는 **기존41+새31=72회귀를0.062초에 PASS**했다. 새 회귀 안에서 ASCII 길이1~5의 모든 native 분절 조합341쌍도 대조했다. 새 helper import 시 torch/tokenizers/transformers/numpy/requests를 막고 외부 명령·자산 열람을 금지하는 mock을 포함한다. 실제 tokenization/교사 HTTP/자료/모델/GPU를 실행한 시험이 아니다.

~~~bash
python3 -B -m unittest scripts.test_p106b_alm_bytes scripts.test_p106b_alm_template_alignment -v
~~~

이 최종 실행 전후 아래4개 소스 SHA가 같았다. 기존 두 파일의 변경은 없다. root의 전체 소스/시험 재검토와 실제 native template·본문 span·확률/시간 검산 전에는 교사 실물 PASS·학습 입장·품질 성공으로 승격하지 않는다.

| 파일 | SHA256 |
|---|---|
| scripts/p106b_alm_bytes.py | DE95A294A3CDEFC38A2A57C669C545D3DA914823873DEECCCB9632098F1B876B |
| scripts/test_p106b_alm_bytes.py | 9693BB34274DF8BBA91BACDAD0017DEE118A891E8A9B20D50883036E88E1B2A3 |
| scripts/p106b_alm_template_alignment.py | 5F56CB6A2205945DF66B0EBA3084AFCA8D4AB4CCA71F78AE0964073308B28023 |
| scripts/test_p106b_alm_template_alignment.py | AB1F9A7BB070E51A207F00EC0F3FD2CCEF47FEC45F1DEB3F3AA3A8996F018DF1 |

실제 연결에는 metadata를 함께 보존하고, 교사 자체 full native stream·prefill/본문/SHA·disable-thinking 응답·teacher context1024와 학생 원 serialization/labels를 각각 검산해야 한다. 본문이 같다는 사실만으로 서로 다른 template의 조건부 logp가 동일하다거나 사고 비활성화가 실제 적용됐다고 주장하지 않는다. cold repeat의 수치 정합·reference 확률·전체1024 캐시 비용은 총괄의 별도 실물 증거다. 새2파일과 이 문서 외 수정·설치·Git·삭제는 수행하지 않았다.

## 13. 새 ALM 학습 controller 읽기 전용 검토

대상은 [diag_p106b_alm_train.py](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py) 624줄과 [test_p106b_alm_train.py](/home/uranus/tinyLM/scripts/test_p106b_alm_train.py) 157줄 전체다. 검토한 SHA256은 각각 **378AD2162DE8A8F8BA769F3D608B6F2543CAB6059C83FD2C910C9E3B381B3AF7**, **E58482147767AE70B2B6979B6C0E18A2967031FC045162656109020935017789**다. 두 파일 해시는 읽기 전후 같았다. 아래 지적은 이 판본에 한정하며 총괄의 동시 수리를 소급해 미수리라고 부르지 않는다.

**optimizer 소유권/WD·마지막 실제 블록의 MLP 포함·전체 N/K를 쓰는 global λ·기존 updater 재사용은 소스상 적절하게 연결됐다.** 새 중요 문제는 λ0 팔도 KL 계산 경계에 실패할 수 있는 분기, 교정/cost/새 CP 사이의 정확 준비본·계수 연결 검산 부족, 학습 입장/전체 시간 경계, 그리고 공백 지표 이름과 사전 신호 계측의 누락이다. 실제 발생·정확성·속도·품질을 실행해 확인한 것은 아니다. 코드/시험 수정·시험 실행·torch/모델·실제 자료·GPU·설치·Git·추가 에이전트는0이며 이 절만 추가했다.

### 13.1 우선 수리할 수 있는 결함

| 우선도·위치 | 소스에서 확인한 문제 | 최소 수리·필요 회귀 |
|---|---|---|
| P1 — [ALMCore.components](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:312), normalized_loss:323 | weight0이어도 chunk_kl을 먼저 계산한다. qS=1/qT<1이면 KL 함수가 예외를 내므로 수학적으로 유효한 **CE-only가 자체 목적과 무관한 ALM 경계로 중단**된다. 0을 곱하지 않는 normalized_loss 분기만으로는 막지 못한다. | weight0이면 KL 함수를 호출하지 않고 같은 target_nll의 CE만 사용한다. cache의 chunk 개수는 계보/노출 수로 유지하되 미계산 KL을 관측0으로 기록하지 않는다. do_train의 KL 요약도 미계산 상태를 허용한다. KL 호출을 예외 mock으로 막은 components→normalized_loss 회귀와 NLL0/qT<1의 CE 유한성 회귀가 필요하다. |
| P1 — [execute의 선결 report 읽기](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:553), [child runtime](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:243) | calibration/cost/train 선결은 status와 source_code_sha256만 비교한다. 현재 준비본 SHA·부모 초기 core·arm/mode·고정 weight/τ/ρ가 같은지는 연결하지 않는다. child payload도 schema/cfg/step/토크나이저와 core는 검사하지만 experiment의 arm/tag/부모/preparation/source/weight를 현재 요청·닫힌 report와 모두 비교하지 않는다. 따라서 **같은 코드의 다른 준비본/계수 report를 섞었을 때 거부한다는 계약이 닫히지 않는다.** | 현재 준비 report SHA와 부모 core를 공통 phase identity로 만들고 calibration의 정확 SHA/τ/ρ/weight·각 cost의 arm/업데이트2·초기 core·계수를 train 입장에 묶는다. 평가도 child experiment와 train receipt의 arm/tag/부모/준비본/코드/λ를 대조한다. raw 보고서는 덮지 않는다. 같은 코드지만 다른 preparation/weight/arm인 mock report를 거부하는 회귀가 필요하다. |
| P1 경계 — [execute](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:542), [runtime의 CUDA 입장](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:251) | authority(cap)는 load_prepared보다 먼저지만 source/원자료/cache 전체 검산은 begun/Guard/wall_limit보다 앞이다. 이후 CPU CP 읽기/구성 뒤 .cuda() 전에는 절대시각 guard가 없고 guard는 모델을 옮긴 **뒤** 확인한다. 준비/CPU load가 예상보다 지연되면 최초 입장 판정만으로16:30 이후 CUDA 입장을 막는다고 증명할 수 없고 그 준비 시간은 report.wall_seconds에서 빠진다. | 전체 phase의 시작/절대 deadline을 CPU 선결부터 잡고 .cuda() 직전에도 같은 guard를 확인한다. 외부 watchdog도 남은 절대시간을 포함해야 한다. 기존 updater의 문턱은 바꾸지 않는다. 느린 준비/CP mock으로 deadline을 넘겼을 때 CUDA 호출0인지, full wall이 선결 시간도 포함하는지 회귀한다. 외부 launcher가 이미 이를 보완했는지는 이번 소스만으로 미확인이다. |
| P2 — [evaluate 사건/집계](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:508) | exact_original은 raw answer의 alias 일치라 공백을 보존하지만, whitespace_exact는 split/join으로 공백을 접는다. 이름만 보면 계획의 **strict whitespace-exact와 반대 의미**다. | raw 지표를 strict_whitespace_exact 등으로 명확히 이름 붙이고 현재 split/join 지표는 whitespace_normalized_exact라는 별도 보조로 분리한다. 앞뒤 공백/반복 공백/줄바꿈 사례에서 둘이 다름을 검사한다. 원답/원주석은 바꾸지 않는다. |
| P2 — [ALMCore 사건](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:319), [calibrate 반환](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:410), [do_train 요약](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:457) | 현재 관측은 CE/KL 합·N/K·gradient norm/cosine다. 사전 설계의 qT/qS·chunk 길이와 §11.2의 **gold-NLL 결합계수 음수/상쇄 질량**은 기록하지 않는다. norm.25만으로 개별 token이 항상 강화된다고 오해할 여지가 남는다. | 이미 계산한 NLL과 cache LP에서 graph 밖 통계만 추가한다. 언어별 raw logq/길이·c_j 부호/최소최대·chunk/학생 target/byte 질량을 남기되 clipping/제외·λ 재조절은 하지 않는다. qT1/qS1 경계를 일반식0/0로 계산하지 않고 기존 core 분류를 보존한다. |

첫 P1은 원 ALM core의 확률 경계가 틀렸다는 지적이 아니라 **CE-only caller의 불필요한 KL 호출** 문제다. 두 번째는 다른 준비본이 실제 섞였다는 관측이 아니라 현재 선결 비교로는 그 혼합을 거부하지 못한다는 source-level 결함이다. 세 번째 역시 실제 기한을 넘겼다는 보고가 아니다.

### 13.2 총괄이 이미 알린 수리와 새 native-template 연결

teacher_cache 경로와 cold-only는 총괄이 수리 중이라고 사전 고지한 항목이다. 검토한 trainer:147~150은 이미 **cache.BASE/teacher_cache/batch_… 및 cache_prompt=False**였다. 이 두 항목을 새로 발견한 미수리 버그로 가산하지 않는다.

현재 cache 소스의 batch_identity는 TEACHER_CONTRACT·enable_thinking=false·ANSWER_CONTENT_BYTES_ONLY·cold replicate tolerance를 포함한다. closed_batch는 source/data/policy identity, 원시/cache shard,16행/8대8, 각 행 native_teacher_input/answer_projection의 scope·수정 없음·cache_prompt=False·cold/cold 검산을 요구한다. trainer.prepare가 이 기존 closed_batch를64번 거친 뒤 frozen_record로 연결하는 구조는 **레거시 raw ChatML 캐시를 무조건 수락하는 경로가 아니다.** 실제64개 캐시가 존재/완료했는지는 읽지 않았다.

frozen_record의 핵심 target map은 cache의 **전체 학생 raw i→i−1**를 유지한다. 새 정렬의 answer-relative byte_start/end를 학생 shifted target 위치로 오해해 쓰지 않으므로 template prefix 길이 차이 자체가 NLL 인덱스를 바꾸지는 않는다. ids/labels/turn·EOT2/4 제외·연속/겹침·같은 원 ID·교사 LP/개수 검산도 있다. 원 전체 학생 stream 재구성은 prepare가 먼저 cache.rebuild_student로 검산한다.

다만 train용 bound row에는 native_teacher_input/answer_projection 본문 자체를 복사하지 않고 cache_row_sha256와 닫힌 cache report 경로/SHA를 보존한다. 이는 원 캐시로 역추적하는 간접 계보다. 위 P1 phase identity와 함께 준비본에 정확 cache report·cache row SHA를 고정해 **다른 scope의 캐시를 동일 신호라고 합치지 않는 것**이 필요하다. 실제 teacher full prefix/본문/ID 및 확률의 정합은 helper의 합성 PASS로 대체되지 않는다.

### 13.3 적절한 optimizer·블록·분모·updater 연결

- optimizers:422는 원 diag_p101a_sft_mtp.optimizers를 부른 후 **.1 LR·모든 group WD0**을 적용한다. 표준 factory의 Adam1e-4/Muon4e-4가1e-5/4e-5가 되고, 모든 trainable Parameter의 집합과 전체 group ID를 비교해 누락·중복 소유를 거부한다. Muon rms도 확인한다. 다른.5배 SFT wrapper에.1을 중첩한 경로가 아니다.
- last_block_parameters:344는 실제 visit schedule의 마지막 layer와 **참조 MLP/실제 attention**을 합집합으로 모으고 객체 ID로 중복 제거한다. 정본 named_parameters에 모두 존재하는지도 검사한다. §11에서 찾은 리스트 참조 MLP 누락을 수리한 구현이다.
- calibrate:362는 원 언어별 앞64개를8행씩 묶어 정확128개를 선택하고, facade.configure의 **전체 N/K**로 CE와 KD를 각각 나눠 분리 gradient를 누산한다. global_grad는 언어별 벡터 합이고 그 norm 비로 λ를 정한다. scalar norm의 합/평균으로 λ를 만드는 오류는 없다.
- by_language는 그 global 분모의 언어별 기여를 N/N언어·K/K언어로 재척도한 **언어별 자체 평균 손실의 gradient**다. global λ에는 사용하지 않아 계산은 타당하다. 다만 반환 이름만으로 두 단위를 혼동하지 않도록 normalization 필드를 명시하거나 global 기여와 자체 평균 통계를 따로 표시하는 것이 적절하다.
- None은 통계 좌표0으로만 취급하고 횟수를 남기며 .grad에0을 대입하지 않는다. autograd.grad만 사용하고 optimizer를 만들거나 step하지 않는다. 전체 norm0/비유한 λ를 거부하고 core/RNG 전후를 검사한다. 실제 이 검산을 통과했는지는 NOT_RUN이다.
- do_train:441는 fresh optimizer를 한 번 만든 뒤 기존 batches(1337+epoch)와 **one_update를 그대로 호출**한다. fixed1024/BF16 eager/16×8·N·clip1·양 optimizer 순서가 원 엔진에 남아 있다. cost는2회에서 끝나 CP0, 본팔은 원 runtime에서 새로 시작해32회/4epoch이고 본팔 epoch 중 optimizer를 reset하지 않는다.
- sums[1]/counts[1]과 원 updater.loss는 순수 CE다. KL/K를 별도 kl로 요약하므로 결합 목적을 CE인 척 인쇄하는 오류는 없다. 단 실제 결합 L=CE+λKL도 별도 필드로 기록하면 수리 후 계수/분모 감사를 더 직접 수행할 수 있다.

현재 optimizer_groups 영수증은 kind/LR/WD만 남기고 group의 정본 parameter names SHA·개수·betas/eps·Muon NS/momentum/nesterov를 남기지 않는다. 실제 소유권 검사는 존재하므로 이를 “검사 없음”이라고 쓰지 않는다. 다만 소유권 검사의 재구성 가능한 영수증을 추가하는 것은 계획의 동일 optimizer 증거에 필요하다.

### 13.4 평가 길이와 원문 보존의 실제 소스 경계

원 VAL의 producer 연결은 clean_bilingual.rows_for의 natural DEV wrapper2이며, [night_qa_data._encoded_pair](/home/uranus/tinyLM/scripts/p106b_night_qa_data.py:180)는 각 view에 **prompt_tokens+MAX_NEW128≤1024**, supervised target≤128과 EOT를 요구한다. render_view는 user/assistant 두 메시지다. 같은 고정 자료/serializer/tokenizer라면 새 max_new64는 원128 예산보다 작으므로 **이 producer 계약 자체에는 길이 충돌이 없다.** 앞부분만 읽는 다중 대화 오류도 이 고정 two-message source에는 해당하지 않는다. ui.emit가 실제 prefix+64>1024이면 자동 절단하지 않고 거부하는 방어도 유지된다.

이것은 실제 선택64개를 이번에 토큰화해 다시 확인했다는 뜻은 아니다. prepare/runtime 입장에 선택64와 사용자8의 실제 prompt 길이·예산/원 prompt SHA를 봉인하면 upstream lineage에 의존한 해석을 실물 확인으로 닫을 수 있다. 원 producer의 target 상한은128이므로 **reference 본문이64생성 안에 모두 들어간다는 조건까지는 별도로 보장하지 않는다.** 실제 긴 정답이 있다면 sample을 바꾸거나 정답을 자르지 말고 원 target 길이·MAX_NEW/종료와 예산상 exact 불가 여부를 공개해야 한다. max64가 사전 선택인 사실과 정답성/모델 실패를 섞지 않는다.

evaluate는 같은 원512 DEV를 기존 BF16 TF 함수로 계산하고, 첫답은 ui.emit의 FP32 MATH/greedy·인증된 EOS/EOT만 제거하는 경로다. native32는 같은 원 native_probe를 재사용한다. 정밀도와 서로 다른 세 지표를 분리한 방향은 적절하다. 사용자8은 고정 source tuple이며 자동 정답 점수에 합치지 않는다. 아직 결과를 본 뒤 고른 DEV/새 test라고 주장한 소스는 없다.

### 13.5 회귀 소스의 현재 보호 범위와 빠진 최소 사례

시험은14개 정의를 읽었고 실행하지 않았다. 마지막 MLP 참조·attention 중복 제거·WD0/.1 LR, row identity/shift/EOT, 원 updater 호출 존재, write-once/20MB, 직접 normalized_loss의 CE-only gradient는 보호한다. 다만 **CE-only 시험은 components를 호출하지 않아 첫 P1을 놓친다.** last-block/calibration N/K 및 RNG/초기 상태의 실물 경로·새 v4 준비본/교사 계약·평가 길이/공백 채점·phase identity의 불일치 거부는 아직 이 새 시험 파일에서 직접 다루지 않는다.

또한 이름에 unequal micro가 있는 facade 시험은 두 행 모두 CE3/KD1인 균등 사례다. 기존 ALM core의 불균등/0KD 회귀가 존재하더라도 facade의 N/K 전달까지 검증하려면 서로 다른 target/chunk 수의 사례가 필요하다. AST에 one_update 호출이 있다는 것은 재구현 중복 방지 증거일 뿐 실제 호출 인자·분모·첫 update 동등성의 실행 증거가 아니다.

추가 확인 경계는 종료 때 source/부모만 다시 검산하는 execute:587~590이다. cache report·원 TRAIN/DEV/tokenizer·준비본은 입장에서 검산되지만 종료 후 전부 재검산하는 코드와 불변 영수증은 없다. 무조건 inputs_unchanged를 써서 채우지 말고, 계획이 요구하는 범위의 실제 전후 해시/전체 wall·정리 결과를 따로 남겨야 한다. cost의 training_seconds는 updater 합이며 CPU 준비·부모 로드·검산을 모두 포함한 full phase 비용과 다르다. 두 update 평균에 고정300초를 더한 estimate를 실제 세 종점 평가의 비용 측정으로 승격하지 않는다.

이번 검토로 새 학습·교사 신호·품질·시간/VRAM을 통과 처리하지 않는다. 최소 수리는 소유 controller/시험에서만 하고 기존 bytes/core/모델/updater·실패 캐시는 보존하는 방향이다.

## 14. §13 최소 수리 구현 — 소유권 재할당

총괄이 diag_p106b_alm_train.py·test_p106b_alm_train.py와 이 문서만 새 쓰기 대상으로 명시 승인했다. impact-analysis로 영향 범위를 다시 고정했다. 기존 core/모델/updater/cache/helper/런처·정본 문서는 읽기 전용이며 특히 총괄이 실행할 V5 cache는 수정하지 않는다. 원 λ=.25·norm 비/τ100·micro8×accum16·4epoch32·부모·자료/split은 그대로다.

수리 범위는 CE-only의 KL 호출 제거, 단계/준비본/부모/고정계수/정확 report SHA·CP identity, CPU 선결부터의 full wall과 CUDA 직전 절대시각 가드, 입력 전후 SHA, 공백 지표 이름, qT/qS·결합계수 부호/coverage 관측, optimizer 그룹 영수증, 실제 평가 길이 입장과 긴 reference 제한 공개다. objective·decoder·원문을 새로 만들거나 실제 모델/교사 실행을 하는 작업이 아니다. 합성 CPU 회귀만 직접 수행하고 실물 입장은 총괄의 전체 소스 재검토 뒤 판단한다.

### 14.1 쓰기 범위와 영향도

| 파일·경로 | 실제 동작 | 권한 근거 | 제외 |
|---|---|---|---|
| scripts/diag_p106b_alm_train.py | 기존 controller의 caller·영수증·입장 경계만 수정 | 총괄의 §13 P1 전부와 필요한 P2 최소 수리 명시 승인 | 실제 prepare·모델·자료·교사·GPU 실행 |
| scripts/test_p106b_alm_train.py | 합성·주입형 회귀 추가, 기존 잘못 이름 붙인 불균등 사례 수정 | 같은 승인과 합성 CPU 회귀 직접 실행 허용 | 실물 CP·실제 tokenizer·원자료 |
| 이 연구 문서 | §14에 변경·실행 범위·잔여 제한 추가 | 기존 소유 문서 쓰기 허용 | 계획서·기준표·결과 원장 변경 |

| 영향 축 | 판단 |
|---|---|
| 코드·중복 | 기존 one_update·batches·optimizer factory·target_nll·chunk_kl·generation을 그대로 재사용한다. 변경은 이 controller의 호출 조건, identity 및 관측이다. 공통 core/helper를 복제·수정하지 않았다. |
| 자료·스키마 | 원문·split·선택1024·기존 parent는 유지한다. 새 준비본/단계 보고서/새 weight-only CP의 연구 영수증 필드는 강화된다. 과거 파일을 변환·덮어쓰거나 source가 다른 과거 준비본을 수락하지 않는다. |
| 회귀 | 기존14개를 유지·보강하고 새31개를 추가해 총45개다. 실제 CKPT/동적 학습 통과와는 구분한다. |
| 정본 문서 | .agents/project.json의 연쇄 대상은 확인했지만, 이 수리는 실험 결과·기준·실행 승격이 아니며 쓰기 허용도 이 세 파일뿐이다. 다른 정본은 수정하지 않았다. |
| 기술부채·비용 | 명시한 모든 입력의 반복 전체 해시와 graph 밖 관측으로 CPU I/O·동기화 비용이 생긴다. 실제 full wall에 포함하며, 그 비용을 감추거나 검산을 생략하는 캐시를 추가하지 않았다. |
| GPU·소유권 | 합성 CPU 회귀만 직접 실행했다. 실제 CUDA·실물 모델/CP/교사/자료·설치·Git·삭제·추가 에이전트는 수행하지 않았다. 총괄 소유 V5 cache와 core/updater/helper는 읽기 전용으로 유지했다. |
| 비교·증거 | λ=.25·norm 비, τ100, 8×16, 4epoch32, fixed1024, 동일 parent·초기 RNG·fresh optimizer·WD0·낮은 LR는 고정한다. 새 정적/합성 증거를 속도·품질 결과로 승격하지 않는다. |

### 14.2 수리한 caller·계보·시간 경계

수리 판본은 [controller](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py) **1,158줄/66,999바이트, SHA256 `6F3F8439A7FE89E4C23BC84740191D6B459C11470BA37BE770D3E6B75EFC945A`**, [회귀](/home/uranus/tinyLM/scripts/test_p106b_alm_train.py) **655줄/43,214바이트, SHA256 `641E3D2AF4111F08C4B4E9E21B640C174F8A865042E0F90732DBB042BBE078FF`**다. 아래 위치는 이 판본에 대응한다. 2026-10-23 09:20 한국시간에 최종 수치·쓰기 범위를 정리했다.

- **CE-only의 KL 미호출**: [ALMCore](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:652)는 같은 단일 target_nll의 CE만 사용하고 weight0이면 chunk_kl을 호출하지 않는다. KL 값은0이 아니라 `None`/`NOT_COMPUTED_CE_ONLY`다. NLL0·qT<1도 CE 경로가 유한하게 미분된다. ALM의 qS1/qT<1은 기존 core가 계속 명시 실패하며 관측은 예외 전 sharded 기록에 넘긴다. clipping·KD 제외·λ 재조절은 없다.
- **공통 연구 identity와 정확 SHA**: [study_identity](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:143)와 단계 identity가 준비 보고서의 실제 byte SHA, native595-f parent의 checkpoint descriptor/core, tokenizer SHA, 고정 행·cache report 목록·평가 행/길이 SHA, 고정 policy와 코드 SHA를 연결한다. calibration의 정확 report 경로/SHA·weight/τ/ρ·phase SHA도 학생 단계 identity에 포함한다. cost는 각 arm의2update/CP0·동일 core·fresh 상태, train은32update/CP1·정확 arm/단계와 계수를 검산한다. 다른 preparation·parent·arm·calibration SHA의 같은 코드 보고서를 수락하지 않는다.
- **새 CP 연결**: [do_train](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:866)의 weight-only experiment에 공통 identity SHA, 정확 train phase 전체/그 SHA, 준비본 SHA, parent·코드·λ/τ/ρ·optimizer 영수증이 들어간다. 닫힌 train report에는 같은 experiment와 새 CP의 실제 SHA가 남는다. [child_payload](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:268)는 그 SHA와 같은 열린 file handle을 검산한 뒤에만 총괄 실행의 CPU tensor load로 넘어가며 inode/크기/mtime도 읽기 전후 비교한다. child header는 요청한 train report의 experiment 전체와 cfg/step/tokenizer/quantization route를 대조한다. cfg의 tuple/list JSON 표현 차이만 정규화 비교하고, 다른 구성·ID mapping을 완화하지 않는다.
- **같은 optimizer·시작상태**: [optimizer_receipt](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:850)는 각 group의 정본 names·names SHA·개수/원소 수와 `params`를 제외한 실제 모든 group 옵션을 JSON 정규형으로 남긴다. betas/eps 및 Muon momentum/nesterov/ns_steps/scale_mode도 빠지지 않는다. 두 cost arm의 최초 RNG와 optimizer 영수증이 정확히 같아야 train 입장이 가능하며, 새 train도 그 RNG/영수증과 대조한다. fresh parent core·모든 grad None·빈 optimizer state를 업데이트 전 확인하고, 그룹 영수증은 종료 때도 변하지 않아야 한다. 원 optimizer 소유권 집합 검사·WD0·.1 LR는 유지했다.
- **전체 시간·CUDA 직전 입장**: [prepare](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:461)와 [execute](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:1006)는 함수 입장에서 시간을 잡는다. 소스/준비본/선결 보고서와 입력 해시·CPU load/구성·정리까지 포함하며 최종 자기 보고서 쓰기 직전까지라는 범위를 명시한다. 기존 Guard의 `started`도 같은 최초 시각이다. [cuda_admission](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:249)은 idle 확인 전과 **바로 .cuda() 전**에 기존 절대 deadline/wall 가드를 각각 확인한다. PAD ID와 실제 평가 길이 검산도 CUDA 전이다. 새 CP 쓰기 직전에도 가드를 확인한다. 외부 OS watchdog은 여전히 총괄 실행 계약이며 이 작업에서 만들거나 실행하지 않았다.
- **입력 전후 불변**: 준비본에는 실제 읽는 원 TRAIN/DEV report·split manifest/전체 shard, tokenizer, native32, parent CP, cache 준비/선결/선택 shard,64개 닫힌 cache report와 raw/cache shard를 명시 SHA로 고정한다. 단계는 그 목록에 자기 준비 보고서·준비 shard/manifest와 정확 선결 단계 보고서/관측 shard, 필요시 child CP까지 더해 시작·종료 전체 SHA를 검산한다. `sources_unchanged`/`inputs_unchanged`/`parent_checkpoint_unchanged`는 성공 검산 뒤에만 true다. 중단/실패는 false/partial로 보존하며 기한 뒤 전체 해시 재시도를 강행하지 않는다. 교사 GGUF를 학습기가 다시 여는 경로가 아니라 닫힌 cache report의 교사 자산 계보를 사용하는 구조다.

### 14.3 신호·coverage·평가 길이의 관측 단위

[chunk_observation](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:293)은 이미 계산된 NLL의 detach 값과 고정 교사 raw LP에서 `logqS=-NLL/τ`, `logqT=LP/τ`, qS/qT·길이·학생/교사 target 수·byte 수를 남긴다. 전체 N/K에서 gold NLL의 결합 미분계수는 다음과 같다.

`c = 1/N + (λ/K) · (qT−qS) / (τ · (1−qS))`

qT1에서는 KD 미분을1/τ로 직접 분기하고, qS1/qT<1에서는 ALM 경계를 명시한다. CE-only 계수는 그 경계에서도1/N이다. exp underflow 여부와 raw logq를 같이 보존하고 expm1으로 차/분모를 계산하며 확률을 잘라 바꾸지 않는다. 실제 per-chunk 관측은20MB 미만 shard로, 언어별 양/음/0/경계의 chunk·학생 target·교사 target·byte 질량 및 계수/q 범위는 단계/업데이트/각 micro 요약으로 남는다. train 관측에는 update/epoch·arm·phase SHA가 붙는다. calibration의 weight1 probe와 최종 고정 λ로 재계산한 관측은 서로 다른 사건 이름으로 구분한다.

이 계수는 **정렬된 gold-NLL 좌표의 수식 계수**이지 최종 parameter gradient의 부호나 optimizer update 방향이 아니다. 관측은 CPU FP64 scalar 합으로 재구성하며 원 모델/손실 정밀도를 FP64로 바꾸지 않는다. 실제 GPU core의 FP64 reduction과 마지막 bit까지 같다는 증거도 아니다. 전체 gradient 교정 norm은 원 gradient 장치의 FP64 통계로 유지되고 언어별 자체 평균과 전체128의 N/K 단위를 분리했다.

[coverage_summary](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:348)는 CE target(원 EOT 포함), KD에 포함된 학생/교사 target, 전체 답 본문 byte, 포함/미포함 byte를 따로 합친다. `answer_content_byte_acceptance`는 전체 **본문 byte** 분모이고 `student_ce_target_acceptance`는 **EOT를 포함한 CE target** 분모다. cache의 non-special 분모 비율을 같은 이름으로 바꿔 쓰지 않으며 기존 cache coverage 필드도 bound row에 보존한다. KD 밖 CE target의 계수는1/N이며 정렬 chunk의 부호 질량에 중복 합산하지 않는다.

[evaluation_admission](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:376)은 prepare와 매 runtime의 CPU tokenizer 단계에서 동일 실제 serializer의 DEV64+사용자8 prompt SHA/ID SHA/토큰 수를 고정한다. **prompt+64≤실제 cfg.max_seq_len**을 만족하지 않으면 원문/후보 일부를 자르거나 교체하지 않고 명시 실패한다. 실제 생성 뒤에도 prompt byte SHA·토큰 수가 그 입장 영수증과 같아야 한다. 원 alias 전체의 native joint-encode 길이와64 초과 여부를 남기며 joint prefix가 안정적이지 않으면 길이를 unknown으로 기록한다. 긴 답도 점수 분모에서 빼거나 답을 자르지 않는다.

여기서 긴 reference는 **고정 native encode 기준의 길이 진단**이다. 같은 문자열을 decode하는 모든 가능한 ID 열의 최소 길이를 증명한 것이 아니므로, canonical reference가64 초과라는 사실만으로 수학적 exact 불가능·모델 오답을 단정하지 않는다. 실제 생성의 MAX_NEW/종료 영수증과 함께 해석해야 한다. 원 주석/생성 원답은 그대로이고 `strict_whitespace_exact`는 raw alias 일치, `whitespace_normalized_exact`는 split/join 공백 접기의 별도 보조 지표다. 이름이 반대였던 whitespace_exact는 사용하지 않는다.

### 14.4 직접 수행한 합성 CPU 회귀와 재현

최종 **45/45 PASS, unittest 본체 0.463초, exit0**다. 첫 보강39개0.229초, 추가 연결43개0.428초도 모두 통과했고 최종 판본에서 다시45개를 실행했다. 이 시간은 인터프리터 시작·Torch import를 포함한 학습 full wall 측정이 아니다.

주요 회귀는 CE components의 KL 호출을 예외 mock으로 막은 qS1 사례, ALM 경계 전 관측 보존, 양/음 결합계수의 기존 core autograd와의 CPU FP64 대조, 실제 불균등 CE7/KD3의 micro 누산 동등성, 준비본/부모/계수/report SHA/arm 불일치 거부, 같은 handle child SHA 선결, 느린 CPU 선결/idle 뒤 기존 절대시간 Guard의 CUDA0, 선결 실패까지 포함한 full wall, 공백 지표 분리, 길이 초과와 unknown/no-filter, 실제 생성 prompt 영수증, optimizer names/전체 옵션의 JSON 왕복이다.

별도 연결 mock은 **실제 one_update 대신 주입한 함수**로 기존 caller가 cost2/CP0 및4epoch32/합성 CP 영수증1을 끝까지 연결하는지만 확인했다. 1024개의 합성 Record와16×8·전체 N/K·기존 update_plan을 사용했지만 실제 forward/backward/optimizer step·실물 CP를 실행한 것은 아니다. .grad 오염·초기 RNG/optimizer 영수증 불일치는 첫 updater 호출 전에 거부한다. 이 mock을 첫 실물 update 동등성으로 부르지 않는다.

재현 명령은 아래와 같다. 설치 없이 기존 tlm_torch 환경을 썼고 CUDA 초기화와 실제 torch.load를 강제 차단했다. import/실행 전후 `torch.cuda.is_initialized()`는 모두 false였다. 합성 fixture 임시 파일 외 실제 corpus·tokenizer·CP·교사 자산은 열지 않았다.

```bash
CUDA_VISIBLE_DEVICES='' TORCH_DEVICE_BACKEND_AUTOLOAD=0 /home/uranus/miniforge3/envs/tlm_torch/bin/python -B - <<'PY'
import ast
from pathlib import Path
import torch
import unittest
from unittest.mock import patch
from scripts import test_p106b_alm_train as tests
for name in ('scripts/diag_p106b_alm_train.py','scripts/test_p106b_alm_train.py'):
    ast.parse(Path(name).read_text(encoding='utf-8'),filename=name)
assert not torch.cuda.is_initialized()
with patch.object(torch.cuda, '_lazy_init', side_effect=AssertionError('GPU 초기화 금지')), patch.object(torch, 'load', side_effect=AssertionError('실제 체크포인트 로딩 금지')):
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
assert not torch.cuda.is_initialized()
raise SystemExit(not result.wasSuccessful())
PY
```

기존 template helper/회귀 SHA는 각각 `5F56CB6A2205945DF66B0EBA3084AFCA8D4AB4CCA71F78AE0964073308B28023`/`AB1F9A7BB070E51A207F00EC0F3FD2CCEF47FEC45F1DEB3F3AA3A8996F018DF1`, 기존 bytes/helper 회귀는 `DE95A294A3CDEFC38A2A57C669C545D3DA914823873DEECCCB9632098F1B876B`/`9693BB34274DF8BBA91BACDAD0017DEE118A891E8A9B20D50883036E88E1B2A3`로 앞 절의 동결값과 같다. core/updater/cache는 이 패치에서 수정하지 않았다. 참고용 현재 code SHA는 core `59466D0810237477E4AB06BB2545138887508D168AAAC257D5096E925A7EBAFA`, updater `B3F5B020E5D579380D2511185AD9F94F0F8B430C3AA92FA0C0095D6480487F9A`, 총괄 소유 cache `7523F958042DB5AFFC760E48DC1444BFDA4033D362365C0D40B8177F6E126112`다. 이는 총괄의 별도 변경을 되돌렸거나 cache 실물 실행을 검증했다는 뜻이 아니다.

### 14.5 남은 제한과 총괄 재검토 지점

실물64개 cache의 완성·전체 source/준비본 해시 비용·실제 tokenizer의 DEV/alias 길이·parent/child header·GPU gradient norm/cosine·모든 실제 optimizer 영수증·처리량/VRAM·정답 효과는 **NOT_RUN**이다. 원시 실패 캐시와 과거 음성은 보존되며, 학생 실행은 총괄의 전체 소스 재검토·회귀 재실행 뒤 판단한다. 본 작업에서 새 학습/교사 요청/다운로드·설치·Git·공유 정본 변경은 없다.

cost의 `training_seconds`는 기존 updater 합이고 `wall_seconds`는 선결/전체 입력 해시와 정리까지 포함한다. train 입장 추정은 두 cost의 업데이트 평균에1.5를 곱한 두 팔32회 비용, 관측한 비-update overhead, **부모+두 팔의 세 평가를 위한 고정900초 예약**을 합친다. 이900초는 실측 평가 비용이 아니라 보수적 사전 예약이라고 보고서에 명시한다. 최종 보고서 자신의 쓰기 시간·프로세스 종료 시간은 자기 wall 필드에 포함할 수 없고 외부 OS wall이 소유한다. 반복 전체 해시/관측이 실제 남은 권한에 안 맞으면 HOLD이지 검산 생략·표본 축소·문턱 완화의 근거가 아니다.

source pin에는 이 시험 파일도 포함한다. 총괄이 추가 수정하면 새 source SHA에서 준비·교정·cost 계보를 다시 닫아야 하며, 기존 준비본/단계/CP를 같은 identity인 척 재사용하지 않는다. 새 write-once 디렉터리 또는 CP가 부분 생성된 뒤 실패하면 원형을 보존한다. 자동 삭제/덮어쓰기/부분 성공 승격·기한 뒤 재시도는 구현하지 않았다.

## 15. BabyLM causal 선택 helper 읽기 전용 검토

[p106b_babylm_causal.py](/home/uranus/tinyLM/scripts/p106b_babylm_causal.py) **227줄/13,559바이트, SHA256 `97BF41E2600D99E2636A55EBDF8296404987127EF8EF33878C2626A7D0C425C2`**, [회귀](/home/uranus/tinyLM/scripts/test_p106b_babylm_causal.py) **167줄/9,151바이트, SHA256 `AF10CB06D3B4D85C9813A581132C9C88B5C62DC8F54ECDA79DB7C7B6485551F5`** 전체를 읽었다. 고정 공식 소스의 선택 함수와 필요한 globals도 직접 대조했다. 이 절 외 수정·helper import·Torch import·시험 실행·실제 tokenizer/자료/모델·GPU·설치·Git·추가 에이전트 호출은 없다. 총괄이 전달한13합성 회귀 PASS는 **총괄 실행 증거**이며 정이 재실행한 결과가 아니다.

**동시 변경 경계:** 작성 도중 두 코드 SHA가 바뀌어 새242줄/199줄 판본도 전체를 다시 읽었다. §15.1~15.5의 위치와 지적은 위 최초 snapshot의 역사적 검토이며, **최종 잔여 항목과 총괄이 이미 수리한 항목은 §15.6으로 구분한다.** 수리된 항목을 현재 미수리로 가산하지 않는다.

**고정 원함수의 선택, full-sentence 단일 shift·원 sum LL, CPU exact-tie RNG 재생과 UID macro 계산에서는 현재 의도한 BLiMP/단일 온도/저장ON 계약의 산식 오류를 찾지 못했다.** 다만 native tokenizer의 숨은 truncation/padding을 거부하지 않는 조건부 P1과, 향후 driver 입장에서 닫아야 할 인자·prediction 수량 및 소스 byte identity 경계가 있다. 아래의 fixture는 정적 재현 설계이며 실행하지 않았다.

### 15.1 적절한 원함수 선택과 관측 범위

공식 경로는 `data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp/source/strict/evaluation_pipeline/sentence_zero_shot/`다. 실제 읽은4개 코드 파일의 SHA는 helper의 FILES 상수와 모두 같았다.

| 공식 파일 | 선택한 함수 | 직접 확인한 계약 |
|---|---|---|
| read_files.py | decode_blimp | good/bad 순서·label0·원 문장=원 completion, supplement의 UID는 파일 stem이다. syntax_semantics의 표기는 공식 decoder가 원래 표준화한다. |
| dataset.py | CompletionRankingDataset.process_causal_sentences, get_causal_collate_fn | 실제 instance method의 본문을 그대로 가져온다. 사용 self 필드는 image 없는 경로의 processor뿐이다. offset 기반 원 phrase mask, 후보별 right padding, inputs[:-1]/targets[1:]/mask[1:]를 그대로 사용한다. |
| compute_results.py | update_subset_to_stats, rank_and_evaluate, compute_causal_results | 원 F.log_softmax→target gather→phrase mask sum이다. BLiMP는 길이 평균을 하지 않는다. LENGTH_NORMALIZED_TASKS의 두 global_piqa 이름은 공식 상수와 같다. |
| run.py | process_results | UID별 accuracy의 macro가 기본 평균이며 pair micro와 다르다. helper의 독립 summary도 같은 UID macro를 검산한다. |

[selected_node](/home/uranus/tinyLM/scripts/p106b_babylm_causal.py:39)는 정확한 class/함수 이름·유일성·decorator 부재를 확인한다. 선택 method를 top-level로 옮겨도 현재 본문은 super/class closure에 의존하지 않고, 공식 파일에도 future annotations가 있어 주입한 future는 annotation의 실행을 새로 바꾸지 않는다. 공식 import 전체를 실행하지 않고 torch/F/Counter/defaultdict/pad_sequence/DEVICE/tqdm 등을 공통 globals로 공급하는 방식은 이 선택 집합의 실제 free-name 사용과 맞는다.

이는 공식 CLI/AutoProcessor/자료 loader 전체를 실행한 것이 아니다. DEVICE를 호출자가 지정하고 progress를 생략할 수 있으며 RankAudit 중에는 rank 이름이 관측 wrapper를 가리킨다. proof가 `official_cli=False`, `original_package_import=False`, `caller_no_grad_required=True`로 구분한 것은 적절하다. source AST가 같다는 사실만으로 TinyLM logits·attention adapter·모델 상태·실제 batch parity가 검증됐다고 부를 수 없다.

[RankAudit.call](/home/uranus/tinyLM/scripts/p106b_babylm_causal.py:161)은 유한 CPU FP32·후보2·온도1.0·행 수·CPU default device를 제한한다. 이 경계에서는 원 rank의 exact equality와 같은 순서의 CPU torch.randint를 재생하고, 재생 후 RNG가 원 rank 이후와 같은지 확인한 뒤 그 상태로 복원한다. Python float로 옮겨도 원 FP32 값의 동일성은 보존된다. near-tie를 epsilon tie로 바꾸지 않는다. Counter는 호출 전 전체 값을 복사하고 metadata별 독립 증분을 비교하므로 현재3개 metadata 키의 total/correct 수량을 검산한다. 같은 UID가 한 batch에 반복되어도 prediction offset은 before length+사용 횟수여서 정상 누적 순서와 맞는다.

### 15.2 조건부 P1 — native encode가 이미 수행한 절단·padding을 놓친다

위치는 [TextProcessor](/home/uranus/tinyLM/scripts/p106b_babylm_causal.py:93), 특히97~99줄이다. `.encode(add_special_tokens=True)` 자체는 원 tokenizer의 post-processor/BOS/EOS를 재작성하지 않는 선택이다. 그러나 **기존 tokenizer.truncation/padding 설정과 encoded.overflowing을 확인하지 않고, native encoded.attention_mask는 버리고 전부1로 새로 만든다.**

따라서 이미 설정된 native truncation이 긴 원문을 짧은 Encoding으로 돌려주면 출력 길이 검사만 통과한다. offset의 끝이 원문 길이 이하라는 조건도 tail 누락을 거부하지 않는다. left padding이 있다면 실제0 attention을1로 바꿔 원 padding을 정상 conditioning token으로 간주할 수 있다. 공식 method는 전달받은 attention을 그대로 사용하므로 이는 원함수 자체의 문제가 아니다. 이번에 **실제 고정 tokenizer에 그 설정이 있다는 관측은 하지 않았다.** 미래 strict driver가 이미 두 설정의 부재를 검산한다면 이 경로는 선결로 막히며, 그 입장 증거를 남겨야 한다.

실물 전에 필요한 최소 수리는 읽기 전용으로 native 설정을 확인해 truncation/padding 활성 상태를 거부하고, Encoding의 실제 attention_mask·overflow 부재를 검산하는 것이다. tokenizer를 disable/재설정하거나 다시 encode해 원 설정을 조용히 바꾸는 수리가 아니다. native 실제 attention이 모두1이라는 계약을 확인한 뒤 그 값을 보존하면 된다. 한 번의 원 encode·원 ID/offset/BOS/EOS는 유지한다.

다음 mock은 현재 wrapper가 조용히 수락할 수 있는 두 경로를 구체화한다. 첫 사례는 원문6자 중 앞4자만 Encoding에 남고, 두 번째는 원 attention0이1로 바뀐다. 실제 원 tokenizer/자료는 필요하지 않다.

```python
# 정적 재현 설계 — 실행하지 않음
from types import SimpleNamespace

class Truncated:
    truncation = {"max_length": 4}
    padding = None
    def encode(self, text, add_special_tokens):
        return SimpleNamespace(ids=[1,2,3,4], offsets=[(0,1),(1,2),(2,3),(3,4)],
            attention_mask=[1,1,1,1], overflowing=["EF"])

p = TextProcessor(Truncated(), native=True, vocab=8)
# 현재 출력4개를 수락할 수 있으나, 수리 뒤에는 기존 truncation 설정 때문에 명시 거부해야 한다.
value = p(text="abcdEF", return_offsets_mapping=True)

class LeftPadded:
    truncation = None
    padding = {"direction": "left"}
    def encode(self, text, add_special_tokens):
        return SimpleNamespace(ids=[0,1,2], offsets=[(0,0),(0,1),(1,2)],
            attention_mask=[0,1,1], overflowing=[])

# 현재 value["attention_mask"]는 [1,1,1]이 된다. 수리 뒤에는 padding 설정/실제0 mask를 거부한다.
value = TextProcessor(LeftPadded(), native=True, vocab=8)(text="ab", return_offsets_mapping=True)
```

길이 상한 자체의 `len(tokens)-1≤1024`는 원 causal shift 이후 입력 길이에 맞다. full native token 최대1025를 무조건 off-by-one이라고 수리하면 안 된다. max_tokens 영수증은 BOS/EOS를 포함한 full Encoding 길이이고 실제 입력 width와 단위가 다르다. 원 post-processor에 BOS가 없으면 첫 native token을 조건으로 나머지 token을 평가하는 공식 shift가 유지되며, helper가 임의 BOS를 추가하지 않는 것은 적절하다.

### 15.3 P2 — driver의 args 계약과 prediction 전체 수량을 닫을 필요

[RankAudit.call](/home/uranus/tinyLM/scripts/p106b_babylm_causal.py:163)은 score 형태는 제한하지만 **args.task="blimp"·images_path=None·save_predictions=True를 검산하지 않는다.** 실제 모델 driver는 아직 없으므로 이것을 실행된 잘못된 driver라고 부르지 않는다. 다만 같은 helper에 global_piqa task가 잘못 들어가면 원 compute가 후보별 length normalization을 적용하고 audit는 그 결과의 순위/Counter만 일치한다고 본다. sum−2/길이1인 good과 sum−3/길이3인 bad는 BLiMP sum에서는 good, 잘못 켠 평균에서는 bad가 된다. 원함수 선택만으로 task 인자까지 고정됐다고 주장할 수 없다.

또한 공식 CLI에서 save_predictions의 기본값은 false다. false를 그대로 전달하면 원 rank는 prediction을 쓰지 않지만 wrapper203줄은 무조건 새 entry를 읽어 IndexError를 낸다. 이때 original은 이미 Counter/RNG를 갱신했다. BLiMP 전용 caller라면 scoring 전에 task/images/단일 온도/저장ON을 명시 입장시키고, helper에서도 요구 계약을 선명하게 거부하는 최소 방어가 적절하다. 공식 rank를 바꾸거나 false를 조용히 true로 바꾸는 것은 필요하지 않다. 기존 정상 fixture의 args에서 save_predictions=False로 바꿔 **원 rank 호출 전 명시 거부·Counter/RNG 불변**을 요구하는 회귀가 최소다.

prediction 검산은 기대한 새 위치 각각을 비교하지만 **UID별 최종 길이·새로 생긴 UID·기존 prefix entry 불변은 비교하지 않는다.** 원 공식 rank가 실제 중복 저장한다는 관측은 아니다. 감시기의 검출 범위 문제다. 다음 오류주입 fixture에서는 정상 새 entry 뒤에 하나를 더 붙여도 wrapper가 읽는 offset0은 정상이라 summary까지 통과할 수 있다.

```python
# 기존 합성 시험의 ns/args와 1행 UID A fixture를 사용한다. 실행하지 않음.
original = ns["rank_and_evaluate"]
def duplicate_prediction(*values):
    original(*values)
    predictions = values[-1]
    predictions[1.0]["A"].append({"id": "A_1", "pred": "unexpected"})
ns["rank_and_evaluate"] = duplicate_prediction
# RankAudit(ns, torch)는 위 callable을 original로 포획한다.
# 1행 정상 점수/label0/UID A를 넣으면 실제 예측은2개지만 현재 기대 offset0 검사만으로는 잡지 못한다.
```

최소 수리는 호출 전 prediction의 UID 집합과 entry prefix를 복사하고, 호출 후 **expected_UID 집합 및 UID별 길이=before+이번 횟수, 기존 prefix 동일, 새 suffix 전체 동일**을 비교하는 것이다. Counter의 정상 증분·동점 RNG·원 후보 순서는 그대로 둔다. 추가/기존 UID에 여분 entry 삽입, 기존 entry 변경, prediction 교환, Counter correct+1의 오류주입을 따로 거부하는 회귀가 좋다. 앞2개는 현재13개 시험에서 직접 보호하지 않는다.

### 15.4 P2 — SHA를 확인한 byte와 실제 compile byte의 단일화

[load_official](/home/uranus/tinyLM/scripts/p106b_babylm_causal.py:64)는 file_sha로 한 번 연 뒤 별도 read_text로 다시 연다. 두 읽기 사이 교체가 있으면 **확인한 SHA의 원 byte와 parse/compile한 byte가 달라도** 기존 expected SHA를 proof에 기록할 수 있다. 원 공식 소스는 동결 읽기 전용이므로 실제 교체를 관측하거나 의심한 것은 아니다. strict source receipt를 만들 때 두 byte stream을 하나로 닫을 수 있는 좁은 수리 지점이다.

최소 수리는 비심볼릭 경로를 확인한 뒤 byte를 한 번 읽어 그 buffer의 SHA를 비교하고, 그 **같은 buffer를 UTF-8 decode→AST parse→compile**하는 것이다. AST node/선택 목록·공식 원문 파일은 바꾸지 않는다. 필요하면 읽기 전후 file stat도 추가하되 같은 byte buffer의 SHA 비교를 대신하지 않는다.

구체 fixture는 fake Path/읽기 mock이 첫 SHA 확인용 byte에는 정상 공식 본문, 두 번째 read_text에는 같은 함수 이름이지만 `decode_blimp`의 label 반환을1로 바꾼 본문을 주게 하는 것이다. 현재는 정상 expected file SHA와 변경 AST SHA가 함께 proof에 들어갈 수 있다. 수리 뒤에는 한 byte buffer만 사용해 이 이중 읽기 경로가 없어야 하며, 실제 compile buffer가 expected SHA와 다르면 exec 전에 거부해야 한다. 이는 실물 공식 파일을 덮어써 수행할 시험이 아니다.

### 15.5 시험·보조 지표와 다음 증거의 한계

현재13개 시험은 원 파일 SHA/선택 위치·공식 shift/right-pad·mask hole의 독립 scalar LSE·정상 Counter/UID macro·exact tie RNG·nonfinite 거부·native BOS/EOS offset·1token/overflow 거부·원문 sink 보존을 다룬다. 다만 source의 AST SHA를 proof에 넣는 것과 기대된 AST SHA를 별도로 대조하는 것은 다르며, 단일 5-vocab 합성 oracle가 실제 native-vocab logits/전 batch parity는 아니다. ATOL/RTOL 상수의 존재도 실제 학생 수치 경로 PASS 증거가 아니다.

shortest_correct/longest_correct는 현재 **문자 수 len(str)** 기준이다. native token 길이 통제가 아니다. 두 문장의 문자 길이가 같으면 min과 max가 모두 앞 후보0을 골라 good-first label의 이익을 받는다. 예를 들어 "aa"/"bb"는 양쪽 length 통계가 모두 정답1이므로 이를 비누설 모델 baseline으로 해석하면 안 된다. 실제 보고 시 길이 단위·동일 길이 횟수와 앞 후보 tie 정책을 공개하거나 동률을 별도 집계하는 것이 적절하다. 원 rank의 random exact-score tie는 이 보조 문자 길이 tie와 다른 사건이며 바꾸지 않는다.

이 검토는 선택 helper의 정적 계약에 한정한다. 실제 driver의 strict model/tokenizer/config SHA·원자료 전체/분모·입력 길이·causal/pad attention·FP32 logits·no_grad/eval·기기/시간 경계·batch/serial parity·공식 실제 결과는 여전히 NOT_RUN/미구현 경계다. 모델 driver를 이 helper가 이미 대신한다고 주장하지 않는다. 조건부 P1의 실제 native 설정 확인과 필요한 P2 입장/영수증 수리는 총괄 소유 작업이며 정은 두 코드 파일을 수정하지 않았다.

### 15.6 동시 수정 판본 재검토 — 해결과 잔여 분리

최종 다시 읽은 helper는 **242줄/14,694바이트, SHA256 `CFB08C580AE45D365F3423F480556791886071CC8E45BF0DBE893EC6AC6BBC0C`**, 회귀는 **199줄/11,232바이트, SHA256 `D89ECBB1B3823FF6366BA6FBD88851782F02077AE6B132ECA81F3F1ACCF9F1D6`**다. 정은 이 변경을 하지 않았고 읽기 전용으로 새 본문을 대조했다.

- **§15.4의 SHA/compile buffer 이중 읽기는 새 소스에서 수리됐다.** read_bytes 한 buffer의 SHA를 비교한 뒤 같은 buffer를 decode/parse/compile한다. hash-mismatch 회귀도 read_bytes 반환을 바꾸는 쪽으로 맞춰졌다. 이 P2를 현재 열린 결함으로 보고하지 않는다.
- 문자 길이 동률은 equal_character_length_pairs, 두 random-tie 기대 정답 수와 명시 length_tie_policy로 공개된다. shortest/longest의 원 good-first raw count를 보존하면서 동률 기대값을 별도 계수하므로 §15.5의 해석 경고도 소스상 보완됐다. 실제 score tie의 원 RNG 정책은 바꾸지 않았다.
- 회귀 정의는13개에서16개로 늘어났고, 정확한 full1025→입력1024 경계·전체 오답 UID의0 Counter·문자 길이 동률·sink 실패 뒤 함수/RNG 복원 사례를 추가한 것을 읽었다. **새16개를 정이 실행하거나 PASS라고 판정한 것은 아니다.** 기존13개에 대한 총괄 전달 결과와 구분한다.
- **남은 조건부 P1은 §15.2다.** native encode의 기존 truncation/padding/overflow 검산과 실제 attention_mask 보존은 새 판본에서도 같아서, 실제 driver가 그 부재를 입장시키거나 helper에서 명시 거부해야 한다. 실제 tokenizer 설정이 위험하다는 실물 관측은 여전히 없다.
- **남은 P2는 §15.3의 인자 계약과 prediction 전체 수량/기존 prefix 불변 검산이다.** 새 소스에서도 save_predictions=False는 원 rank 이후 prediction 인덱싱으로 넘어가며, args.task/global_piqa 오설정을 helper가 제한하지 않는다. 여분 prediction/새 UID/기존 entry의 변경에 대한 전체 상태 검산도 아직 없다. 현재 의도한 blimp/images없음/T1/저장ON과 정상 공식 rank의 경로가 실패했다는 뜻은 아니다.

마지막 판독 SHA 이후 총괄이 다시 수정한 경우에는 그 변경 소유 증거가 우선이다. 이 절의 닫힌 수리와 열린 조건을 해당 SHA 경계 밖으로 소급하지 않는다.

## 16. BabyLM 실제 full-logits driver 입장 전 읽기 전용 검토

총괄이 추가한 [driver](/home/uranus/tinyLM/scripts/diag_p106b_babylm_causal.py) **362줄/23,614바이트, SHA256 `C25DC08AEDF02152A412E0CA55D83A83BF0484B1C7E28DE13A68DF1B186D2DDF`**, [driver 회귀](/home/uranus/tinyLM/scripts/test_p106b_babylm_driver.py) **90줄/4,811바이트, SHA256 `E3F1A80F695A69FF4B490D7F3448DA3AC2C282BAFD6408CD5E7EB93D06A514B6`**, 수정 [helper](/home/uranus/tinyLM/scripts/p106b_babylm_causal.py) **268줄/16,814바이트, SHA256 `EA07960488A8F97E83564B6F4047B9D885034903C587EBBD9839B10C239964B9`** 전체를 읽었다. 실제 model_runtime/strict loader/adapter의 필요한 호출부도 코드로 연결했다. 이 절 외 코드 수정·import·실제 자료·모델·GPU·시험·설치·Git·추가 에이전트 호출은0이다. 총괄이 전달한29CPU 회귀·원자료 분모 준비 완료는 총괄의 실행 결과이고 이 검토의 재실행 결과가 아니다.

### 16.1 현재 snapshot에서 남은 P1 — Falcon의 외부 GPU 상주 거부 경계

[driver.execute의 model_runtime 입장](/home/uranus/tinyLM/scripts/diag_p106b_babylm_causal.py:285) 전에 공통 NVML idle 검산이 없다. native3종은 재사용한 research_adapter→[selected_runtime](/home/uranus/tinyLM/scripts/interactive_research_infer.py:426)이 CPU load 이후 require_idle_gpu를 호출하므로 기존 거부 경계를 유지한다. 그러나 [model_runtime의 Falcon 분기](/home/uranus/tinyLM/scripts/diag_p106b_official_core6.py:138)는 자산/CPU 상태 검산 후 [model.eval().to('cuda')](/home/uranus/tinyLM/scripts/diag_p106b_official_core6.py:160)로 바로 옮긴다. **그 이전에 다른 compute PID를 거부하는 기존 NVML 입장 호출이 없다.** HFLM은 그 CUDA 이동 뒤에 만들어지므로 HFLM 내부 진단을 그 이전 입장으로 간주할 수도 없다.

따라서 한 번의 with가 **자기 모델 한 개**만 연다는 것과 **다른 프로세스의 교사/모델이 없는 GPU에만 입장**한다는 것은 다르다. 현재 실제 GPU에 다른 PID가 있다는 조회는 하지 않았고, 이미 수행한 Core6/Falcon 평가가 중복 상주였다고 소급 주장하는 것도 아니다. 다만 새 driver만으로는 Falcon이 이전 교사 프로세스와 함께 CUDA에 올라가는 경로를 거부하지 않아, 실제 실행 전 필요한 자원·소유권 입장 P1이다.

가장 작은 수리는 새 driver의 기존 wall_limit 안에서 model_runtime 직전에 **기존 interactive_research_infer.require_idle_gpu를 공통 재사용하고 전후 check()**, 그 point-query 영수증을 새 보고서에 남기는 것이다. native loader의 기존 두 번째 검산은 유지한다. 외부 실행기가 이미 동일한 fail-closed NVML 검산을 실행 직전 수행·보존했다면 그 실행 입장 증거로 이 선결을 충족할 수 있으나, 단순히 “이번에는 비워 두겠다”는 가정이나 가용 VRAM 수치만으로 대체하지 않는다. point query는 계속 감시·경쟁 프로세스의 미래 생성까지 보장하는 lock이 아니라는 기존 scope도 유지한다.

필요한 최소 회귀 fixture는 **외부 PID4242가 있다는 기존 NVML mock 응답**, 전부 통과하는 자산/준비본 mock, 그리고 .to('cuda')를 실제 GPU 대신 호출 횟수만 기록하는 합성 Falcon model이다. 수리 뒤에는 기존 idle 함수가 거부해 **CUDA 이동0·model_runtime 입장0**, 부분/실패 증거 보존이어야 한다. idle 점조회가 지연돼 시간 가드를 넘는 경우도 이후 모델 입장0이어야 한다. 실제 모델·GPU·원문을 쓰지 않는 오류주입 설계이며 정은 실행하지 않았다.

### 16.2 이전 지적의 해소와 추가 P1 여부

수정 helper는 native truncation/padding 활성 상태를 거부하고, overflowing==[] 증거와 실제 encoded.attention_mask를 사용한다. args도 blimp/images없음/save_predictions=True로 제한하며, batch별 UID/전체 prediction 수량과 마지막 모든 prefix/suffix의 독립 hash를 검산한다. 공식 소스는 같은 byte buffer의 SHA→decode→AST 경로를 유지한다. **§15의 조건부 native P1과 prediction/args P2를 현재 미수리로 다시 세지 않는다.**

FullLogits는 실제 strict runtime의 native PrecisionForward 또는 Falcon 본체를 직접 호출하고 실제 FP32/유한/full[B,T,V]·no_grad/no-autocast/TF32off·오른쪽 pad·eval 상태를 확인한다. native는 causal future mask에 의해 뒤 pad가 이전 유효 위치에 보이지 않는 계약이고, 실제 세 합성 문항에서 batch/single/full-label CE/문항 역순·후보 호출 역순을 비교한다. 수치 tolerance를 통과해도 후보 선택 또는 exact-tie 여부가 바뀌면 거부한다. 이 canary가 모든 실제 문항의 serial parity를 증명한다는 해석은 하지 않는다.

공식 원 compute_causal_results와 원 collate/rank/process_results를 그대로 호출하며 main/supplement를 따로 유지한다. 고정 전체 파일·행 분모와 SHA·UID 수·출력 행 수를 검산하고 원문 일부만 제거하거나 reference를 재작성하지 않는다. source/data의 종료 SHA, write-once20MB shard/보고서, cost/full 분리·실측 cost 외삽, 최초 CPU 선결부터의 wall과 모델 구간 내부 alarm·절대 종료 여유를 읽었다. 기존 runtime의 본체/자산 사후 검산이 예외를 내면 driver도 complete가 아니라 partial로 닫는다.

**이 snapshot에서 위 Falcon GPU 입장 외에 새로 확정할 scoring/shift/마스크/공식 함수 선택의 P1은 찾지 못했다.** 이는 실제 GPU 실행 PASS·원 모델 정확성·full 수치 동등성·VRAM/완주 시간·공식 benchmark 결과가 아니다. 실제 source/model/input SHA·canary 결과·전체 결과의 증거는 총괄 실행 이후 판단한다. driver·시험·helper는 수정하지 않았으며 후속 총괄 변경이 있으면 해당 새 SHA의 근거가 우선이다.

## 17. BabyLM 공통 GPU 입장 P1 최소 수리 — v1 원판 선보존

총괄이 §16의 공통 NVML 입장만 구현하도록 소유를 재할당했다. impact-analysis로 쓰기/실행 경계와 직접 호출부를 확인했다. 원 scoring·공식 함수·원문/분모·모델 runtime은 그대로이며, 공통 require_idle_gpu와 전후 시간 검사·영수증 및 새 OUTPUT만 수정한다.

| 경로 | 승인된 동작 | 제외 |
|---|---|---|
| scripts/diag_p106b_babylm_causal.py | 공통 모델 입장 P1·OUTPUT v2 최소 수정 | 모델/scoring/source 함수 변경·실물 실행 |
| scripts/test_p106b_babylm_driver.py | 외부 PID/지연·model_runtime 입장0의 합성 CPU 회귀 추가 | 실제 GPU/NVML/평가·훈련 자료 |
| handoff/audit/source_snapshots/20261023_babylm_driver_v1.py.txt 및 20261023_babylm_driver_v1_test.py.txt | 명시한 v1 원판2개를 apply_patch로 새로 보존 | 덮어쓰기·삭제·재편집 |
| 이 문서 | 영향·원판 SHA·실제 시험/미실행 범위 기록 | 새 준비본·런처·정본 연결 |

| 영향 축 | 근거와 경계 |
|---|---|
| 코드·중복 | 이미 존재하는 interactive_research_infer.require_idle_gpu를 그대로 호출한다. new driver의 model_runtime 직전 공통 경로 한 곳만 바꾸므로 Falcon과 native에 같은 외부 입장이 적용된다. native runtime의 내부 재검산은 남는다. |
| 자료·증거 스키마 | 원 평가 자료/준비 증거를 열거나 수정하지 않는다. OUTPUT만 p106b_babylm_causal_v2_s1337로 분리하고 새 점조회 영수증을 보고서에 추가한다. v1 보고서/준비본은 보존한다. |
| 시험 | 기존10개 driver 회귀에 순수 주입형 입장 시험을 더한다. model_runtime/원자료/공식 source load/Torch는 mock이며 실제 점조회 subprocess도 합성 응답을 쓴다. |
| 정본·소유권 | .agents/project.json의 영향 축을 대조했다. 새 v2 준비와 계획/런처/정본 연결은 총괄 소유이므로 이 작업에서 수행하지 않는다. WIP·공통 helper/core6 원천도 수정하지 않는다. |
| 비용·증거 | 새 비용은 기존 NVML point query 한 번이다. 이전/이후 같은 시간 검사로 지연을 거부한다. 이는 lock·연속 감시나 실제 GPU PASS가 아니다. |

실제 두 코드의 첫 수정 전에 UTF-8/LF·마지막 개행을 확인하고 **apply_patch Add File로 원판2개를 먼저 작성**했다. 작성 직후 원 코드와 read_bytes 전체 일치를 확인했고 SHA는 각각 driver `C25DC08AEDF02152A412E0CA55D83A83BF0484B1C7E28DE13A68DF1B186D2DDF`/23,614바이트, 시험 `E3F1A80F695A69FF4B490D7F3448DA3AC2C282BAFD6408CD5E7EB93D06A514B6`/4,811바이트다. 새 원판 두 개만0444 읽기 전용으로 만들었다. 기존 v1 결과/원본 자료는 이 보존 과정에서 열지 않았다.

### 17.1 적용한 최소 diff와 원판 위치

- [v1 driver 원판](/home/uranus/tinyLM/handoff/audit/source_snapshots/20261023_babylm_driver_v1.py.txt)과 [v1 시험 원판](/home/uranus/tinyLM/handoff/audit/source_snapshots/20261023_babylm_driver_v1_test.py.txt)은 위 SHA 그대로다. 작성 뒤/회귀 때 해시 및0444를 재확인했다.
- [v2 driver](/home/uranus/tinyLM/scripts/diag_p106b_babylm_causal.py)는 **365줄/23,763바이트, SHA256 `13647CDB36DF573F7B6ADF9229B468571B238DC9E6C6FCA538AE82925B4428C8`**다. v1 대비 실제 diff는 OUTPUT의 v1→v2, 기존 require_idle_gpu의 지연 import1줄, model_runtime 직전 보고서의 gpu_point_query 대입1줄과 뒤 check1줄뿐이다. 기존 with 내부의 앞 check를 그대로 활용하므로 **시간검사→공통 NVML 점조회/영수증→시간검사→model_runtime** 순서다. 공식 scoring/source/모델 함수를 수정하지 않았다.
- [v2 회귀](/home/uranus/tinyLM/scripts/test_p106b_babylm_driver.py)는 **206줄/12,417바이트, SHA256 `AB8E72ACCB2945D7B552A72DBB37B4FC87F7504806CCCB58FC71C6BD7AA37D87`**다. v1의 execute 이외 모든 top-level 함수/class AST가 바뀌지 않았다는 회귀도 포함한다. 원 FullLogits/numerical_canary/분모·policy·prepare·source identity 함수는 그대로다.

공통 helper는 기존 require_idle_gpu의 실제 파서·fail-closed 동작을 재사용한다. native runtime의 내부 입장 점조회는 유지한다. `p106b_babylm_causal.py`는 이 작업 전후 `EA07960488A8F97E83564B6F4047B9D885034903C587EBBD9839B10C239964B9`이며, 기존 core6 runtime도 수정하지 않았다. 새 schema/scoring 정책이나 원 자료 변환을 추가하지 않는다.

### 17.2 실제 수행한 합성 회귀 — 15/15 PASS

기존 driver10개+새5개, **15/15 PASS·unittest 본체0.074초·exit0**를 tlm_torch Python에서 직접 관측했다. 새 시험은 실제 execute의 입장 순서를 호출하되 준비본/소스/분모·official loader·모델 runtime·Torch·내부 alarm을 합성으로 주입한다. NVML 함수 본문은 기존 함수를 사용하지만 subprocess.run 대신 합성 응답만 공급하므로 실제 NVML/GPU 조회도0이다.

| 새 시험 | 관측한 보호 범위 |
|---|---|
| 외부 PID4242 | native3종과 Falcon 전부에서 기존 NVML 함수가 거부한다. 실제 execute의 model_runtime 호출0, PARTIAL/rc9와 외부 PID 원인 기록을 확인했다. |
| 점조회 지연 | 상대 wall581초 또는 절대 deadline−19초를 주입하면 점조회 영수증은 남기되 뒤 check가 TimeoutError를 내어 model_runtime 호출0이다. |
| 점조회 전 만료 | 앞 check가 거부하므로 NVML mock 호출0·model_runtime 호출0이다. |
| 정상 idle | NVML 요청2회 뒤 정확히 한 번의 mock model_runtime 입장과 gpu_point_query 영수증을 확인했다. 그 mock은 입장 경계에서 의도적으로 중단하므로 실제 평가 PASS를 생성하지 않는다. |
| v1 원판/불변 AST | 원판2개 실제 byte SHA/읽기 전용 비트, OUTPUT v2, execute 이외 모든 함수/class AST의 동일성을 확인했다. |

시험 전체에 추가 import finder를 두어 실제 torch/transformers/tokenizers/tinylm/lm_eval import를 거부했고, ROOT 아래 HF/data_cache/runs/datasets의 Path.open도 차단했다. 실행 전후 실제 torch 모듈은 sys.modules에 없었다. fake Torch만 입장 분기의 형태를 재현했으며, 모델·원본 평가/훈련 자료·교사·GPU·원 공식 source 실행은 없었다. 시험이 쓰는 결과/심볼릭 링크 fixture는 자체 임시 디렉터리뿐이다. 원판은 이 재검산 중 수정하지 않았다.

간단 재현은 아래 driver 회귀 한 모듈이다. 실제 관측에서는 여기에 위 import/자료 열기 차단 guard를 추가했고 `-B`로 pycache 쓰기도 막았다.

```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -B -m unittest -v scripts.test_p106b_babylm_driver
```

### 17.3 남은 실행·연결 경계

이번 범위는 **v1 코드2개를 선보존한 뒤 공통 GPU 입장 P1을 수리하고 합성 CPU 회귀를 닫은 것**이다. 실제 GPU/NVML PASS·같은 기기 지속 독점·실물 모델/캐시/우도·수치 canary·품질/속도/VRAM·full 완주를 증명하지 않는다. 점조회 이후 새 외부 프로세스가 생기지 않는다는 지속 lock도 아니다. 기존 절대시각·wall·외부 watchdog 계약은 그대로다.

v1 준비/결과는 읽거나 바꾸지 않았으며 새 OUTPUT 아래 준비본도 만들지 않았다. 코드·시험 SHA가 바뀌었으므로 총괄이 새 v2 prepare/source identity를 만들고 계획·런처·정본을 연결해야 한다. 실물 실행과 통합 재회귀·승격은 그 뒤 총괄이 판단한다. 실제 수정 경로는 이 문서·driver·시험과 명시 승인된 새 원판2개, 총5개뿐이다.

## 18. P078 기존 prefix 라우터 — 구현과 미실행을 분리한 읽기 전용 비용 검토

### 18.1 범위·시점·기존 구현의 정확한 진입점

**2026-10-23 10:28:06 KST 시점의 텍스트/보고서 관측**이다. 총괄 요청대로 이 절만 작성했다. 모델·Torch import·체크포인트/토크나이저/코퍼스/holdout 자산 열기·회귀·학습·GPU 조회/실행·설치·Git·추가 에이전트는0이다. 결과 JSON의 명시 metadata와 scripts/tinylm 소스 바이트만 stdlib 읽기로 대조했으며 체크포인트 SHA는 **보고서의 기록값이지 이번에 자산을 재해시한 값이 아니다.** 실제 GPU 작업은 총괄의 기존 프로세스가 소유한다.

관련 정본은 [P078 계획](/home/uranus/tinyLM/test_plan/P078_재귀는-reasoning인가-방문의-선택성.md)의 Stage3/Stage2Wd/2We와 [결과066](/home/uranus/tinyLM/test_result/066_20260831_P078-이득은-몰려있지만-어느-크롭인지는-재현되지-않는다.md)의 §9~10/§12다. 계획의 옛 “본체704 NOT_RUN” 문구보다 닫힌 실제 보고서와 이후 선택 단계가 현재 상태의 근거다. 둘을 조용히 고치거나 옛 상태를 현재로 재사용하지 않았다.

| 실제 파일·함수 | 이미 있는 역할 | 이번 변경 |
|---|---|---|
| [diag_p078_prefix_router.py](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:30) | bootstrap_v3 독립 router namespace, prepare→cost→budget→labels→fit→evaluate→readback | 없음 |
| [p078_prefix_router.py](/home/uranus/tinyLM/scripts/p078_prefix_router.py:26) | prefix/feature/상대 CE/CPU head/온라인 quota/기존 원자 경로 호출 | 없음 |
| [diag_p078_route_training.py.loaded](/home/uranus/tinyLM/scripts/diag_p078_route_training.py:163) | 기존 전용 본체 loader·계보·strict state/형상·GPU idle 검사 | 원44개 소스 모두 보존 |
| [Stage3Wc full 런처](/home/uranus/tinyLM/run_P078_Stage3Wc_prefix_router_full.sh:17) | cost부터 readback까지 자동 연결, prepare는 재생성하지 않음 | 없음 |
| [Stage3Wb 단일 단계 wrapper](/home/uranus/tinyLM/run_P078_Stage3Wb_prefix_router_v2-hold.sh:14) | 전달된 한 단계만 실행하는 기존 수동 경로; 파일명 V2와 실제 bootstrap_v3 namespace를 구분 | 없음 |
| [Stage3Wa 옛 HOLD wrapper](/home/uranus/tinyLM/run_P078_Stage3Wa_prefix_router-hold.sh:14) | 같은 driver에 인자를 전달하나 옛 VAL512 분할 음성의 역사 표기를 보존 | 재활성화/수정 없음 |
| [Stage2Wd 선택기](/home/uranus/tinyLM/scripts/diag_p078_selected_stage.py:130), [Stage2We 런처](/home/uranus/tinyLM/run_P078_Stage2We_remaining_shuffle_pair.sh:24) | 완료 두 본체 재학습 없이 남은 셔플 팔과 원4팔 판독 연결 | 없음 |

기존 [p078_route_training.learned_router](/home/uranus/tinyLM/scripts/p078_route_training.py:105)와 [옛 driver의 mode=router](/home/uranus/tinyLM/scripts/diag_p078_route_training.py:521)는 의도적인 NOT_IMPLEMENTED/HOLD다. 이것을 보고 **“현재 라우터 전체가 미구현”으로 판정하면 틀린다.** 실제 별도 label/head/eval은 위 prefix_router 두 파일에 구현돼 있다. 새 라우터 구조나 본체 updater를 만들 필요가 없다.

이번 source snapshot은 driver SHA `8A27979E6DE4B1DDD367843803E06A61F2CABA737DF8B09414E9407738F76199`, helper `54C1BF6060B2EFEC427FD0A227CD4A3039B192C1BAD2D9A8B719C208C3C52240`, Stage3Wc SH `85217653A7D20AD3AC458FA5EC6F423D9D4203FA683E2EB0D7AE96069327F4EE`다. 기존 prepare의49개 source SHA와 uniform/balanced/fixed-shuffle 보고서의44개 source SHA를 각각 현재 파일과 대조해 **불일치0**을 관측했다. 기존 소스/SH/자료를 수리하거나 재태깅한 결과가 아니다.

### 18.2 완료한 것을 다시 제안하지 않는 현재 상태

| 단계 | 이 시점 상태·직접 근거 | 다음에 반복할 것인가 |
|---|---|---|
| 옛 크롭 이득 분포·seed 재현 | 결과066의 Stage0/1 완료. 동일 본체의 약한 크롭 상관 음성은 보존 | 아니오. 다른 prefix feature 전체의 보편 상한으로 확대하지 않음 |
| 원4팔 cost32·프로토콜/분할 CPU 검산 | 결과066 §9~10의 실제 비용4팔과 CPU 검산 완료 | 아니오. 새 router cost8과는 별개 |
| uniform_r2704 / balanced_count704 | 22일 실제 완료. 각 보고서 status=ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED, 업데이트704·CP1 | 아니오. 낮은 CE를 일반 대화 성공으로 승격하지 않음 |
| fixed_shuffle_r2704 | **23일 10:20:31 KST 실제 완료/활동 rc0**, [보고서](/home/uranus/tinyLM/test_result/evidence/p078_route_training_v1_s1337_cleanv3/train_fixed_shuffle_r2/report.json)·[활동표](/home/uranus/tinyLM/test_result/evidence/p078_route_training_v1_s1337_cleanv3/activity_train_fixed_shuffle_r2.json), seconds4291.363580 | 아니오. 현재는 본체3/4가 닫힘 |
| update_shuffle_r2 및 원4팔 readback | [현재 로그](/home/uranus/tinyLM/test_result/066_log_20261023_P078_Stage2We_remaining_shuffle_pair_090858.txt)의 10:20:33 시작·update50까지 관측. 닫힌 train 보고서/원4팔 readback은 아직 없음 | **진행 중이지 미착수 NOT_RUN이 아님.** 중복 실행/개입 금지 |
| bootstrap_v3 router prepare | [준비 보고서](/home/uranus/tinyLM/test_result/evidence/p078_prefix_router_bootstrap_v3_s1337/prepare/report.json)와 [활동표](/home/uranus/tinyLM/test_result/evidence/p078_prefix_router_bootstrap_v3_s1337/activity_prepare.json) 완료. TRAIN22528, DEV256/TEST256·각 한영128, 모델/CP tensor/tokenizer load0, feature_labels=NOT_RUN | 아니오. 새 단계 안의 기존 prepared() 재검산만 필요 |
| 실제 router cost8 / budget / labels / fit / evaluate / readback | 같은 evidence namespace에서 해당 여섯 report.json 모두 없음. 현재 **NOT_RUN** | 이 부분만 후속 후보 |

router prepare 보고서 SHA `54169072026E5C01FA8D0989173F63DA1BA3D39684E37E772B17B1BE8A676C0A`, 활동표 `7D5CECAEC30380DD3EA80C419F463908582534C695CAAA89E125C1E7849F0522`, 실제 prepare3.161524초다. 이는 별도 holdout 생산/검산 시간 전체가 아니다. 옛 V1의 TEST 영어 최소수 부족은 그대로 HOLD이며 새 준비 성공으로 지우지 않는다.

balanced 본체는 보고서 SHA `C6DF14CA7D2B37AC3B39C72A58F235441E4BBFB6FB80C62C7F0CBEF2B2B0C099`, 기록된 CP 경로 `/home/uranus/tinyLM/runs/ckpt/m100s10_ko-en_p078_route_training_v1_s1337_cleanv3_balanced_count.pt`, 기록 SHA `A9CA3B99EABCC08C3E8BD58FDBFEC90AB999A637F820DAA25E1F7470F2037196`다. router는 사전에 이 본체를 고정했으므로 다른 셔플 결과를 보고 본체를 바꾸거나 native595-F를 대신 넣는 계약이 아니다. Stage2Wd 이후 계획은 **완료된 선택2팔의 판독만으로 router cost를 먼저 허용**하므로 원4팔의 마지막 팔 완료 자체가 router의 새 과학적 선결은 아니다. 다만 현재 같은 GPU 사용 중이므로 실행은 순차적이어야 한다.

### 18.3 label/head/eval의 실제 계약과 비용 단위

1. [prefix/validate_prefix](/home/uranus/tinyLM/scripts/p078_prefix_router.py:147)는 최초 실제 감독 y 위치의 `x[:first+1]`만 사용한다. y의 한 칸 shift와 원 correction owner를 보존하고, 알려진 과거+assistant header를 독립 serialize/encode한 IDs와 모든 행에서 같아야 한다. 미래 답 토큰을 넣거나 경계 실패 행을 지우는 경로가 아니다. [features](/home/uranus/tinyLM/scripts/p078_prefix_router.py:229)는 **동결 embedding 행**의 평균·위치가중평균·마지막행+길이2값이다. E256에서770차원이며 transformer 선행 추론 특징이나 관계추론 전체가 아니다.
2. [labels](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:341)→[trial_labels/per_row_ce](/home/uranus/tinyLM/scripts/p078_prefix_router.py:265)는 TRAIN22528 전부를 micro8/fixed1024로 R1/R2/R3 세 번 평가한다. 감독 target만 head128씩 CE 합/행 target수로 계산하고 세 행 CE의 평균을 빼 상대 CE를 만든다. **2816개 microbatch×3=8448개 본체 batch forward, 67584개 경로-행 관측**, 같은 실제 x의 세 경로 노출16,216,332와 감독 관측1,657,827, 패딩 위치69,206,016이다. R1/R2/R3의 물리 방문14/24/34는 서로 다르다. FP32/MATH·TF32off·no_grad이며 body optimizer0; 정답성 판별 라벨이 아니다.
3. [fit](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:489)는 **770→64→3/tanh, 49,539개 파라미터의 CPU head**, Adam0.001·seed1337·5epoch·micro8×accum16이다. [head_update](/home/uranus/tinyLM/scripts/p078_prefix_router.py:296)는 한 update의 `행수×3` 분모로 MSE를 누적한다. 22528/128=176 update/epoch, 총880회다. TRAIN feature만으로 정규화하며 행 단위 MSE와 아래 target 가중 CE의 분모는 같지 않다. DEV는 epoch1/3/5에서 각256행 **선택된 경로 한 번만** 평가해 target 가중 CE로 head를 고른다. DEV768개 본체 single-row forward가 있어 **기존 fit 전체를 순수 CPU 작업이라고 부를 수 없다.** 본체는 동결 GPU에 남고 best head CP만1개 쓴다.
4. [selected_evaluation](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:393)/[evaluate](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:536)는 TEST256×learned/random_quota/untrained/constant_train_mean 네 정책이다. 현재 prefix의 세 예측값과 남은 `[1,2,2,3]` quota로 R을 선택하며 미래 prefix/gold를 선택에 쓰지 않는다. 선택 후 CE의 gold 사용은 평가용이다. **1024개 single-row CE와1024개 실제 첫답**, 답당 max128이므로 최대131072개 생성 token이다. FP32/MATH·greedy·MTPoff·KVcache OFF라 token마다 전체 prefix를 다시 계산한다. 고정 R을 한 답 생성 동안 유지하며 token별 동적 중단/라우팅이 아니다.
5. [summarize/readback](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:427)는 방문 quota·전체 raw·880 update/optimizer 동일성·DEV 선택·TEST4lane·원자 CLA owner/consumer route·ID/EOT·SHA를 검산한다. readback 자체의 모델/tokenizer/tensor load는0이지만 원 CP/새 head의 **바이트 해시를 읽는다.** 현재 선결 미실행이므로 지금 다시 CPU 검산을 돌릴 독립 결과는 없다. 생성의 원 input slot은 `n*prefix+n*(n-1)/2`로 기록하고 target CE와 분리한다.

head FP32 feature 행렬만17,346,560값/69,386,240바이트(66.171875MiB)다. 이는 Python 객체·prefix/경로 영수증·JSON·동결 본체·head/optimizer를 뺀 **숫자 배열 한 벌의 계산값**이며 전체 호스트/VRAM 추정이 아니다. labels는 각 행에770개 feature와 prefix·세 경로 영수증을 JSON shard로 저장한다. shard당20MB 미만과 **총 저장/재독해량20MB 미만**은 다르며, cost8은 이 전체 label 저장 I/O를 실제 생성하지 않는다. 실제 디스크/RSS/총 소요는 미측정이다.

네 정책은 평균 R2의 방문량을 맞추지만 **모두 고정R2인 TEST 대조군은 이 네 정책 안에 없다.** 원 Stage2 uniform_r2 본체의 다른 VAL 결과를 가져와 같은 본체·같은 fresh TEST의 고정R2 대조로 대체할 수 없다. 따라서 현재 계약의 결론은 우선 **동일 quota 안의 학습된 배분 대 세 통제**이며, 고정 R2 대비 우월·어떤 입력에서나 최적·전체 reasoning 개선은 별도다. 같은 평균 방문도 입력길이/생성길이·feature/head CPU 왕복·시간이 같다는 뜻은 아니다.

### 18.4 기존 cost8이 최소 새 진단인 이유와 시간 예산

[cost](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:270)는 이미 준비한 원형을 검산하고 frozen balanced 본체 한 개를 연 뒤 전체 TRAIN+holdout을 encode/경계 검산한다. **TRAIN 첫64행/8microbatch의 세 경로 CE+64개 feature**, 첫행 R1/R2/R3 single-row CE, full128이 들어가는 **가장 긴 TRAIN prefix2개의 R2 생성**, CPU head64행 임시 update1회와 예측1회를 잰다. 본체 optimizer0·label artifact0이며 이 임시 head update를 본 head880회 완료나 품질 관측으로 합산하지 않는다. 부모 R1 resource-only 비용은 과학적 body 비용을 대신할 수 없다.

[forecast](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:309)는 이 실제 측정 이후에만 가능하다. L=8개 trial batch 초의 최댓값, H=head64행 update초, E=전체 encode초, S=R1/R2/R3 single-row CE초의 최댓값+최대 feature초+head 예측초, G=두 R2 생성의 초/token 최댓값으로 두면 아직 전부 미실행인 현재 분모의 코드상 예측은 다음과 같다.

| 남은 단계 | 기존 코드의 초 단위 외삽 |
|---|---|
| labels | `4224*L + 2*E` |
| fit+DEV3회 | `2640*H + 1152*S + 2*E` |
| TEST4정책 CE+답 생성 | `1536*S + 196608*G + 2*E` |
| raw 판독·추가 여유 | `300 + 600` |
| cost 이후 총 미실행 예약 | `4224*L + 2640*H + 2688*S + 196608*G + 6*E + 900` |

이 외삽은1.5배 여유를 포함해 남은 현재 권한과 router 가족144000초를 동시에 확인한다. 실측 reserved 대비 GPU total 여유1GiB도 요구하되 OOM 보증은 아니다. **R2 생성 두 건은 R3/다른 답 길이의 시간 상한 증명이 아니고**, label JSON 전체 I/O·반복 raw 검산도 이 수식의 별도 전수 실측이 아니다. 완료 보증으로 쓰면 안 된다. 원4팔 BF16 학습의 약5~6초/update나09:08 Stage2We 예측15227.192683초(약4.23h)는 새 FP32 label/generation의 측정값이 아니다. SH의 임시 “1.5h”도 여전히 미측정이다.

10:28:06부터16:30까지 달력상21714초(6시간1분54초)가 남았으나 이는 **지금부터 GPU를 전부 사용할 수 있다는 뜻이 아니다.** 현재 update_shuffle 작업의 남은 시간·총괄 우선 작업·실제 cost/closure·전환 여유를 먼저 빼야 한다. 현재 GPU 상태를 독자 조회하거나 남은 본체를 끊지 않았다.

특히 기존 full SH는 labels cap21600초/fit7200초/evaluate14400초/기타1200초다. [worker](/home/uranus/tinyLM/scripts/diag_p078_prefix_router.py:635)는 **예상 소요가 아니라 요청 cap 전체가 남은 절대시각 안에 들어와야** 입장한다. 16:30 종료라면 **10:30 이후 labels의6시간 cap 입장은 불가능**하다. 지금 GPU가 다른 팔을 진행 중이고 cost/budget도 선행하므로, **원 full SH를 그대로 오늘 자동 완주시키는 선택은 현재 시간 계약에 맞지 않는다.** 시간 상한은 실행 보증이 아니며 임의로 SH/허용치/행수/분모를 줄이는 수리는 하지 않았다. 기존 full SH의 환경변수 누락 안내에 남은 “Current body704 is NOT_RUN” 역시 현재 본체 상태가 아니라 낡은 안내다.

### 18.5 총괄이 고를 수 있는 기존 단계 세 안과 최소 선결

| 안 | 구체 범위 | 이득·한계 | 추가 영향·비용 |
|---|---|---|---|
| A — 이번에는 새 router GPU0 | 기존 준비/완료 본체·이번 소스 판독만 유지 | 현재 진행 학습/우선 KD·평가 창을 더 쓰지 않음. 라우터 품질 질문은 NOT_RUN 유지 | 새 구조/자료/시험/출력 없음 |
| B — 기존 cost 한 단계만 | GPU가 빈 뒤 독립 current 권한으로 **기존 mode=cost** 1개만, 끝나면 중지 | 실제 label/feature/head/두 생성 비용을 얻음. labels/학습/TEST 품질 성공은 주장0 | 본체1개 상주·앞64행 세 경로+두 생성·전체 CPU encode. 기존1200초 cap을 쓴다면 최대20분 예약이지 실제20분 완료 보장은 아님 |
| C — 기존 전체 미실행 단계 | B의 닫힌 cost를 읽고 전체 식이 실제 남은 창에 들어갈 때만 labels→fit→evaluate→readback 검토 | 사전 고정 quota/네 정책 질문을 직접 관측. 시간·저장·부분 실패 부담 가장 큼 | 현재 원 full SH cap은 불맞음. 기존 단일-stage CLI에서 별도 현재 권한/cap을 명시하는 선택도 **총괄의 새 비용·권한 판단** 없이는 실행하지 않음 |

**권장: 현재 진행 GPU를 건드리지 않는 A를 기본으로 유지하고, 총괄이 다른 우선 작업 뒤에 실제 여유를 확인할 때만 B를 검토한다.** B가 오늘 허용된다면 이는 이미 구현된 가장 작은 새 GPU 진단이다. 작은 head라는 이유로 full labels/DEV/TEST가 싸다고 가정해 C를 자동 연결하지 않는다. 현재는 L/H/E/S/G가 없으므로 C의 완주 시간·효과를 예측하거나 바로 실행할 명령을 승인된 것으로 제시하지 않는다.

추가 실행 전 최소 선결은 다음이다.

- 원 `prepare`의 완료 영수증·입력 서명·49개 소스/기존44개 소스·V3 corpus report SHA `7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20`·bootstrap_v3 holdout SHA를 기존 함수로 다시 검산한다. 이번에는 원 자산을 열지 않았다. **새 분할/본체704 재생성은 선결이 아니다.** old prepare의 당시 만료는 과거 정상 종료 증거를 무효화하지 않으며, 새 모델 실행의 현재 권한을 대신하지도 않는다.
- `handoff/audit/` 아래 **router 전용** 현재 권한 descriptor/SHA·정확 입력 서명·allow_gpu_training=True·위 balanced CP SHA·절대 만료·worker cap/40h 가족을 총괄이 제공해야 한다. 현재 Stage2We 권한은 schema/tag/본체 계약이 달라 대용 불가다. 기존 prepare는 당시 allow_gpu_training=False/body pin=null였으므로 GPU 허가가 아니다.
- frozen_body→기존 loaded()의 strict 본체/전용 header·cfg dense14/d768/E256/seq1024·chat32 vocab32768 및 ID3/4/2·source/CP 바이트·동결 core 검산을 통과해야 한다. **GPU가 비기 전에 cost를 시험 호출하지 않는다.** 현재 worker는 실패/부분 활동도 보존하며 spent()가 불완전 활동의 조용한 재시도를 거부한다. 단순 실패 후 같은 namespace 재호출을 정상 재개로 가정하면 안 된다.
- 비용만 닫은 뒤 전체가 안 들어오면 멈춘다. require_budget()는 **labels/fit/TEST/판독 전부**가 들어와야 진행하며, 몇 행 라벨만 만들기·DEV/TEST 축소·정책 삭제·max_new 축소·gold prefix·R1 본체 fallback은 없다. head-only CPU 학습이나 TEST 이전 임의 품질 성공 같은 새 단축 계약도 추가하지 않았다.

V3는 알려진 PUBLIC192/198 첫답·669 둘째답 주석 결함을 보존한 noisy-control이며 의미 전수 검수/배포 채택 자료가 아니다. fresh DEV/TEST의 원 TRAIN/VAL 키 분리와 전체 사전학습 오염 통제는 다르다. 기존 원답의 오류·반복·epoch1 이후 VAL 악화도 보존하며, router CE가 낮아져도 정답성/reasoning 개선은 실제 답과 통제를 함께 읽어야 한다. 현 P078 SFT/Muon·상대 CE head 조건의 새 seed 분산자는 없으므로 옛 재귀 사전학습 자를 그대로 복사해 유의성을 확정하지 않는다.

이 절은 impact-analysis의 기존 세 안 비교와 exp-preflight의 계산·중복·비교/권한 경계를 읽기 전용으로 적용한 **STATIC_ONLY 검토**다. 정본 기준표 §1/2/3/7 및 현재 `_rulers.py`를 대조했으나, 사용자 금지 범위에 따라 registry 조회·회귀·모델/자산 검산·GPU 입장은 실행하지 않았다. 따라서 완전 preflight PASS나 새로운 실행 승인이 아니다. 이번 쓰기는 본인 연구 문서뿐이고 원 소스44개·router 구현·SH·계획·결과 정본은 수정하지 않았다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 19. 공식 평가 HF 캐시 정책 국소 수리 — 읽기 전용 추가 검토

### 19.1 범위·확인한 기본 경로

총괄이 수정한 [configure_hf_cache](/home/uranus/tinyLM/scripts/prepare_p106b_official_eval.py:38) 전체와 [순수/mock 회귀84줄](/home/uranus/tinyLM/scripts/test_p106b_eval_cache_policy.py), [공식 task loader94줄](/home/uranus/tinyLM/scripts/p106b_official_tasks.py), [Core6 model_runtime](/home/uranus/tinyLM/scripts/diag_p106b_official_core6.py:139)의 호출부·기존 [tinylm.paths79줄](/home/uranus/tinyLM/tinylm/paths.py)·[패키지 진입8줄](/home/uranus/tinyLM/tinylm/__init__.py)을 소스로 대조했다. 요청에 축약된 시험 경로는 실제로 `scripts/test_p106b_eval_cache_policy.py`다. 공식 원문/평가 자료·모델/CP·캐시 파일은 열지 않았고, import·도구/코드 변경·회귀·GPU·설치·Git·추가 에이전트도0이다. 이 문서만 수정했다.

10:58 KST 전후 snapshot의 SHA256은 prepare `6579EE28834F95D338E03B2A10A65EFD5745CD66A5DD696AD878C093F473A497`, tasks `D73463C87E20CBCF20378E1A224B93551F8A9DBBF7C3D67528C1CBCDDF7C632F`, core6 `1A6FBCE1ADFCDDBD20D46042E31B89C6FFC515A9CCCA90ACBA3AED70C66851B2`, 새 시험 `8795E02A495B7F4683DD7836DD053CAD60AA9CC8051A7E490CA9F763F70B57FB`다. 아래 판단은 이 소스 경계이며 총괄의 이후 변경을 완료로 소급하지 않는다.

**새 프로세스·기본 canonical 절대경로·외부 연결 없는 캐시라는 조건에서는 이번 source 판독으로 새 확정 P1은 찾지 못했다.** 호출 순서는 다음처럼 닫혀 있다.

- CPU prepare(execute=True)는 자산 metadata 검산 후 configure→offline 환경→`from datasets import load_dataset` 순서다. 단순 모듈 import/execute=False에서 tinylm/HF/model을 미리 import하지 않는다.
- load_tasks는 configure→prepare_harness→lm_eval/ConfigurableTask 순서다. Core6 execute는 이 load_tasks를 먼저 호출하고 나중 model_runtime에서 재호출하므로 `_HF_CACHE_CONFIGURED=True` 상태에서 HF가 이미 import돼 있어도 같은 환경이면 통과한다.
- model_runtime은 configure→기존 paths의 HF_DIR 대조→research_adapter 또는 Transformers/HFLM 순서다. BabyLM은 공식 원함수를 선택 AST로 로딩하므로 원 파일의 datasets/AutoProcessor import를 실행하지 않으며, 공통 model_runtime이 첫 HF import보다 앞선 정책 적용을 소유한다.
- 첫 설정에서 TINYLM_DIR/TINYLM_HF의 허용 위치와 이미 import된 datasets/transformers/huggingface_hub를 검사한다. 이 함수로 먼저 설정한 뒤에만 재호출을 허용하며, 이후 세 캐시 환경값/TRANSFORMERS_CACHE가 변하면 조용히 복구하지 않고 거부한다. 처음부터 올바른 환경으로 HF를 먼저 import한 경우도 거부하는 것은 [명시 회귀](/home/uranus/tinyLM/scripts/test_p106b_eval_cache_policy.py:48)의 **의도된 새 프로세스 입장 계약**이지 숨은 오류로 세지 않았다.

### 19.2 P2 — 동일한 허용 경로의 상대 표현은 첫 호출에서 잘못 거부될 수 있음

[사전 검사](/home/uranus/tinyLM/scripts/prepare_p106b_official_eval.py:47)는 TINYLM_DIR/TINYLM_HF를 resolve해 비교하지만, 실제 [paths의 환경 설정](/home/uranus/tinyLM/tinylm/paths.py:16)은 Path의 원 상대 표현을 보존하고, [뒤 검산](/home/uranus/tinyLM/scripts/prepare_p106b_official_eval.py:56)은 환경 문자열을 canonical 절대 문자열과 직접 비교한다. 그 결과 **허용 위치가 맞아 사전 검사를 통과한 입력이 사후 검사에서 거부**되는 경로가 있다.

구체 fixture는 새 프로세스/cwd=저장소 루트에서 `TINYLM_DIR='.'`·TINYLM_HF 미지정, 또는 canonical TINYLM_DIR와 `TINYLM_HF='HF'`다. resolve된 ROOT/HF_DIR는 정확히 승인 위치지만 paths는 HF_HOME='HF', HF_HUB_CACHE='HF/hub' 등을 써서 “did not take effect”가 된다. 기존 paths가 이미 캐시된 경우에는 단순 import 재시도로 설정이 다시 적용되지도 않는다. 현재 시험의 정상 fixture는 세 환경값을 **처음부터 절대 문자열로 채우고 tinylm을 fake로 주입**하므로 이 사례를 감시하지 않는다. 한편 초기 설정 뒤 TINYLM_HF만 같은 위치의 상대 표현으로 바꾸고 기존 세 절대 캐시값을 유지하면 사전 resolve 검사와 재호출은 통과하므로 첫 호출과의 표기 허용도 일관되지 않다.

이는 **조건부 정적 재현 경로**이고 실제 프로세스로 시험하지 않았다. 현재 총괄의 기본 절대경로 실행을 막는 관측 오류는 아니다. 최소 수리 방향은 허용 위치 검사를 완화하는 것이 아니라, 승인한 상대 표현도 지원할지 canonical 절대 표현만 허용할지 계약을 일치시키는 것이다. 지원한다면 **HF import 전에 같은 위치를 절대 표현으로 고정**하고 이미 로딩된 paths 및 [model_runtime의 str(HF_DIR) 비교](/home/uranus/tinyLM/scripts/diag_p106b_official_core6.py:144)까지 함께 대조해야 한다. 절대 표현만 허용한다면 import 전부터 그 이유로 거부하고 해당 경계를 명시하면 된다. 정상 canonical/두 상대 fixture/이미 로딩된 paths/초기 호출 후 재호출의 fixture가 최소 추가 감시다. 이 검토에서 그 정책 선택이나 코드 수리는 하지 않았다.

### 19.3 조건부 경로 누락 — HF 하위 cache가 외부 연결인 경우

현재 ROOT와 **HF_DIR 자체**는 resolve 검산하지만, expected의 HF_HUB_CACHE/HF_DATASETS_CACHE 경로 각각을 resolve하거나 부모 연결 여부를 검사하지 않는다. 따라서 `ROOT/HF`는 일반 디렉터리인데 **HF/hub 또는 HF/datasets가 저장소 밖으로 가는 연결 경로**이면 환경의 문자열은 모두 맞아 configure가 통과할 수 있다. “승인한 세 경로 문자열” 검산과 “실제 모든 cache 쓰기가 저장소 안” 보장은 다르다.

최소 fixture는 실제 저장소를 쓰지 않는 임시 project/HF와 별도 임시 outside를 만들고, hub/datasets 각각만 outside로 연결한 뒤 fake tinylm.paths·정상 expected 환경을 공급하는 것이다. 이 함수에는 하위 resolve 검사가 없어 반환을 막을 조건이 없다. 최소 보호는 기존 정책을 import해 디렉터리를 만들기 **전에** 세 예정 경로의 실제 위치/연결 부모가 승인 범위인지 검산하고, 재호출에서도 같은 범위를 유지하는 것이다. 실제 저장소 HF 아래 연결의 존재는 확인하지 않았으므로 **현재 외부 쓰기가 발생했다는 주장이나 확정 실행 장애는 아니다.** 만약 실제 외부 연결이 있다면 모델 입장 전 거부/별도 권한이 필요한 조건이다. 원 HF/cache/공통 paths를 임의 변경하지 않았다.

### 19.4 증거·호출 범위의 제한과 BabyLM v3 연결

새 cache_policy 영수증은 HF_HOME/HF_HUB_CACHE/HF_DATASETS_CACHE의 세 환경값에 대한 것이다. 모든 라이브러리의 추가 cache 변수/이미 동결된 상수·네트워크·미래 환경변조의 지속 감시까지 증명하지 않는다. `process_only=True`도 **환경파일을 수정하지 않는 프로세스 환경 정책**으로 읽어야 한다. 실제 paths import에는 HF/hub·data_cache·runs 하위 mkdir이 있으므로 전체 호출이 파일시스템 side effect0인 순수 함수라는 뜻은 아니다. 이번 검토는 그 import를 실행하지 않았다.

또한 [Core6 SOURCES](/home/uranus/tinyLM/scripts/diag_p106b_official_core6.py:35)→[BabyLM identity](/home/uranus/tinyLM/scripts/diag_p106b_babylm_causal.py:64)는 수정한 prepare/tasks/core6를 포함하지만 새 위임 원천인 tinylm/paths.py와 tinylm/__init__.py 자체는 포함하지 않는다. 이번에 읽은 paths SHA는 `FBC4FD995ACFEED9258945990C5FC67A19947BCEED80189DF3B7C95B2015D3C4`, init은 `3CBC5092E4ED4F903B6A88AC39D1A1EDAA32AB4D20FD2DB061ADD441A917DC62`다. 캐시 정책 원천까지 “실행 전후 소스 불변”이라고 주장하려면 두 원천 SHA를 새 v3 identity/영수증과 종료 검산에 포함하는 것이 작은 P2 보강이다. 현재 나열된 source 파일의 검산과 전체 전이 의존성 불변을 혼동하지 않는다.

별도 [research_adapter/prepare_harness API](/home/uranus/tinyLM/scripts/p106b_official_lm_adapter.py:450)와 옛 [adapter canary](/home/uranus/tinyLM/scripts/diag_p106b_official_adapter.py:47)는 이 새 configure를 자동 호출하는 범용 API로 바뀐 것이 아니다. 현재 task/model_runtime을 거치는 Core6/BabyLM 호출 순서는 위와 같지만, 임의의 다른 caller도 자동 보호된다고 확장하지 않는다. 이미 끝난 canary/공식 평가를 재실행하라는 제안이나 기존 점수의 소급 무효화가 아니다.

마지막 source 판독에서 총괄의 BabyLM OUTPUT은 이미 **p106b_babylm_causal_v3_s1337**로 분리돼 있었다. prepare/tasks/core6가 바뀌었으므로 v2 준비의 source_identity가 현재와 맞지 않아 거부되는 것은 **올바른 보호**다. v2 준비/부분 증거를 덮거나 옛 점수를 새 소스 실행으로 재기록하지 않고 새 v3 준비·현재 source identity가 필요하다. 이번 수리 경로는 공식 YAML의 process_docs/프롬프트/선택지/target/metric을 바꾸는 동작을 추가하지 않으며, 캐시 위치 수정만으로 점수가 동등하거나 좋아졌다는 실제 주장은 하지 않는다.

현재 시험은 합성8개 정의를 읽었을 뿐 실행하지 않았다. 위 상대경로/연결 경로/위임 source 영수증 범위는 **남은 정적 경계**, 기본 canonical fresh-process 흐름은 **소스상 순서 확인**이다. GPU 입장·실제 cache 위치·외부 쓰기0·공식 점수/프롬프트 등가·새 v3 준비/모델 평가 PASS는 총괄의 실행 증거 없이는 선언하지 않는다. 기존 코드/도구/자료/결과는 수정하지 않았다.

## 20. ALM V7 실물17 독립 판독과 전체1024·학생의 시간 예산

### 20.1 결론·승인 범위·원 증거

**원 실패34의 확률 조회와 같은 prefix의 direct/probe 통제는 실제로 회복됐다. 그러나 이것은17행 기술 canary 완료이며1024 캐시나 학생 효과 완료가 아니다.** 저장된 전체 준비본에서 계산한 교사 고유 target 예상은 약5333개, 전량의 행첫 cold 복제를 포함한 completion 예상은 약6357회다. 아래 입력길이 보정의 **전량 캐시 보수 예약은 약166~179분**, 학생은 아직 실측 비용이 없고 기존 운영 예약이 별도120분이다. 따라서 현재 근거로 **오늘 전량 캐시+양팔 학생+세 종점 평가의 보수적 동시 완주를 약속할 수 없다.** 실제 학생 비용이 낮게 측정되면 남은 창에서 가능할 수 있다는 것과 구분한다.

총괄이 지정한 [V7 canary 보고서](/home/uranus/tinyLM/HF/sft_ready/p106b_alm_context_v7_s1337/canary/batch_000000/report.json), 그 raw/cache JSONL 및 [준비 보고서](/home/uranus/tinyLM/HF/sft_ready/p106b_alm_context_v7_s1337/prepared/report.json)·기존 selection JSONL4개만 stdlib로 읽어 scalar/집계를 산출했다. 해석에 필요한 기존 controller/학생/런처/사전 계획은 소스로 읽었다. 실제 모델·Torch·토크나이저·교사·GPU·회귀·설치·Git·새 에이전트·원천 재생산은0이며 이 문서만 수정했다. 원문/응답 전문을 stdout에 출력하지 않았다.

canary 보고서 SHA `A5922CB25E243EAB977437E1542EE850FF3D18E9250CA05E6B8823D4CD5865F2`, 준비 보고서 `D455646EB13158272B95960776EBD85874EDFAAE5B3D0A7B6979293402805C37`다. 선택4shard 총67,199,434바이트의 파일별/연결 SHA·1024개 행 자체 SHA·순서와 보고서의 row SHA를 검산했다. 연결 SHA는 `049720E9F8C36D8C49F8F9608A25DDF93D7699C7E12AC4BA78924320787CCB85`다. canary raw7431행/5,537,802바이트 및 cache17행/2,740,052바이트의 manifest SHA·연결 SHA·개수, cache17개 행 SHA, completion208개의 prefix 참조→실제 payload 재구성 SHA도 독립 대조했다. 새 원천/토크나이저 파일이나 GGUF를 재로딩/재해시한 검사는 아니다.

해석 조건은 원 TRAIN의 동결 선택1024/한영512·seed1337, 학생 chat32 SHA `9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E`, 원 V3 report SHA `7D52695308B0D8122B3ABE42CC7E396BFF3F94E811E5F379FFA85F259ED4EB20`, native no-thinking/질문 경계 trim 공개·본문 byte만 정렬·cold·MTPoff·양자화 본교사의 pre-sampling raw logp다. canary17은 **고정 앞16+실패 선택34**로 KO9/EN8이며 임의의 대표 무작위17이 아니다. 전체 시간 외삽은 DESCRIPTIVE_ONLY 계산이고 실제 full/학생은 NOT_RUN이다.

### 20.2 실패34와 정상 토큰의 네 통제를 raw까지 연결

원 사건은 **selection_index34/alm_000034, teacher raw_index539(shifted538), ID36054, 원 piece bytes `[236,155]`=`ec9b`**다. 실제 teacher IDs의 `[:539]`를 해시한 값은 기대한 `5661E32015CBC28C7FC8D38BC1243052D37319CF7CB36BEA9D78A3D6858AA6F6`와 같다. 완결 UTF-8가 아닌 조각을 임의 문자로 치환하거나 재토큰화한 값이 아니다.

두 실제 HTTP reply의 native top64에서 **원 ID36054와 원 bytes를 직접 찾았고**, raw logp는 둘 다 **−0.0002300407795701176**이다. 실제 선택 ID는 ASCII probe32, bias는 `[32,100]`이며 원 reference ID와 다르다. 저장된 값은 probe 자체 확률이 아니라 반환 top-K의 원 target 확률이다. saved/cold/replicate 세 표기는 **독립 관측3회가 아니다. saved와 cold는 같은 첫 관측이고 두 번째 cold 요청이 한 번 더 있다.** 비교차이는0이고 clamp·누락0 대입·질량 재정규화가 없다.

정상 토큰 통제는 raw_index330/원 reference21, prefix SHA `1E67511B2BA76C64CE1DA933781E045F7095ECEBC0C5C0CEDD660BC232DBA8B9`, 같은 K64에서 정확히 다음 네 조합이다. 각 조합은 direct1회+probe1회이므로 총8 completion이다.

| probe ID | bias | direct 원 target logp | probe 조회 원 target logp | 같은 top2 |
|---|---:|---:|---:|---|
| 32 | 100 | −0.004205414559692144 | −0.004205414559692144 | ID21/248046 |
| 32 | 200 | −0.004205414559692144 | −0.004205414559692144 | ID21/248046 |
| 33 | 100 | −0.004205414559692144 | −0.004205414559692144 | ID21/248046 |
| 33 | 200 | −0.004205414559692144 | −0.004205414559692144 | ID21/248046 |

top2의 두 번째 raw logp도8 reply 모두 −7.415709972381592다. pair별 일치뿐 아니라 첫 direct 대비 모든 direct/probe의 원 target/top2 교차값도 같았다. 위 원 실패 사건과 정상 통제의 **이 prefix들에서의 기능 대조**이지 모든 어휘·모든 prefix의 probe 불변성 증명은 아니다. K512/2048 상승이나 실제 데이터의 bias200 복구는 이번에 필요하지 않았다. 보고서 bias200 요청4건은 위 통제의 direct/probe 두 조합분이다.

### 20.3 요청·원형·종료·coverage 판독

17행에는 고유 teacher target100개, 전 target의 독립 cold 복제100회, 통제8회가 있어 **completion208/208 성공**이다. 원본 검산에서100쌍의 reference logp 최대차0·top2 logp 최대차0·top2 ID 불일치0이었다. HTTP325시도/269성공의 차56건은 전부 **기동 중 /health**(URLError4/HTTPError52)이며 completion 실패56건으로 읽으면 틀린다.

208개 실제 payload는 모두 cache_prompt=False/post_sampling_probs=False/n_predict1이다. 실제 reply도 truncated=False/tokens_predicted1, **timings.cache_n=0**, prompt_n과 tokens_evaluated가 정확한 native prefix 길이와 같았다. **reply.tokens_cached는 prefix 길이와 같은 비영 값**이므로 이 필드를 과거 KV 재사용 수라고 읽어 cold 위반으로 판정하지 않는다. 실제 재사용 검산 필드는 원 helper가 검사하는 timings.cache_n이다. `cache_verifications[*].warm`이라는 레거시 key도 실제 warm cache 관측이 아니라 두 번째 cold 결과다.

cache17의 student/source_row는 해당 준비 행의 보존본과 같고 원형 변경 플래그가 모두 False다. full template 동일성 주장은 모두 False이며 원 답 본문 byte만 대응한다. 질문 경계 trim은 준비1024 중42행으로 별도 공개됐고 학생 원문 수정과 구분한다. 이17의 byte/target acceptance는 양 언어에서 모두1.0이었다.

| 언어 | 행 | CE target(EOT 포함) | 학생 본문 target | 교사 고유 target | KD chunk | 대응 본문 bytes |
|---|---:|---:|---:|---:|---:|---:|
| KO | 9 | 38 | 29 | 35 | 29 | 105 |
| EN | 8 | 73 | 65 | 65 | 54 | 227 |
| 합 | 17 | 111 | 94 | 100 | 83 | 332 |

같은 입력의 서로 다른 native 분절이므로94/100/83을 같은 분모로 합산하지 않는다. EOT는 CE에 남고 KD에는 없다. 위 coverage1.0은 전체1024의 coverage/권리/의미 정답 전수 검수가 아니다. formal_train_ready=False·quality_claim=False·semantic_exhaustive_review=False를 유지한다.

보고서의 inputs/source/teacher-assets 종료 검산은 모두 MATCH다. 현재24개 controller/helper 소스 SHA는 독립 재해시에서도 불일치0이었다. 다만 원 corpus/tokenizer/GGUF의 전후 전체해시는 **총괄 실행의 보고서 증거**이며 이 분석에서 원 자산을 다시 연 결과가 아니다. raw의 owned_session_exit는 PID350406/rc0/종료0.415188초이고 보고서 owned_teacher_exitcode0·owned_threads_closed=True, 계측/원 raw 보존 오류목록은 비어 있다. raw request는 I/O 전에 flush됐다는 계약이지 fsync/전원장애 내구성을 증명하지 않는다.

GPU 전체 표본 peak9698MiB·최소 free6364MiB, 교사 프로세스 RSS peak8768.746MiB·200ms 표본463개는 이 canary의 관측이다. 더 긴 full prefix의 OOM 안전이나 지속 독점을 보증하지 않는다. 학생 load/optimizer/CP write는0이다.

### 20.4 저장된1024의 실제 길이·target 분포

분위수는 저장 행의 scalar로 계산한 nearest-rank다. 전체 text는 의미 판독하지 않았고 새 encode/교사 tokenize는 하지 않았다.

| 범위 | 행 | 실제 x 합 | x 평균/p95/최대 | CE 합 | CE 평균/p95/최대 | EOT 제외 본문 target 합 |
|---|---:|---:|---|---:|---|---:|
| 전체 | 1024 | 256267 | 250.26 / 392 / 852 | 5897 | 5.759 / 13 / 37 | 4873 |
| KO | 512 | 145551 | 284.28 / 436 / 852 | 2353 | 4.596 / 8 / 17 | 1841 |
| EN | 512 | 110716 | 216.24 / 330 / 494 | 3544 | 6.922 / 18 / 37 | 3032 |
| 고정 앞16 | 16 | 3628 | 226.75 / 341 / 341 | 105 | 6.563 / 22 / 22 | 89 |
| canary17 | 17 | 4066 | 239.18 / 438 / 438 | 111 | 6.529 / 22 / 22 | 94 |

전체 x는 ≤256이637행,257~512가375행,513~768이9행,769~1024가3행이다. CE는 ≤4가477행,5~8이418행,9~16이97행,17~32가31행,33~64가1행으로 **실제 최대37≤64**다. 전체 답 본문18533bytes·최대159bytes이며 full의 평균 target은 canary보다 짧지만 **입력은 더 길고 긴 꼬리가 있다.** 짧은 target만으로 전체 cold prefill 비용이 싸다고 단정하지 않는다. 정정: canary17 통계행의 초안에 섞인 비한국어 표현1곳은 인계 전 제거했으며 x 평균/p95/최대는239.18/438/438이다. 원자료와 계산값은 바꾸지 않았다.

64개16행 batch의 실제 x 합은 min3398/p50 3981/p95 4447/max4783, CE 합은 min68/p50 89/p95 116/max127이다. 고 target batch43은 CE127/본문111, 최대 x 합 batch35는4783이다. 첫16의 최대 x341, canary17의 최대438과 달리 **batch1에는 전체 최대 x852가 이미 들어 있다.** 긴 사례를 다른 행으로 교체하자는 제안이 아니다.

canary teacher full IDs 최대545 대 full의 학생 x최대852다. **학생1024 입장과 교사1024 cap 입장은 별개이며 full teacher 길이는 아직 저장돼 있지 않다.** 관측 teacher/student prefix 비율도 KO 약1.059~1.310, EN0.944~1.077로 일정하지 않았다. 큰 비율을 일률 적용하는 스트레스에서는 긴 KO3행이 teacher1024를 넘을 수 있지만 이는 실제 native 길이 측정이나 실패 예측이 아니다. 반대로 전체가 들어간다고 보증할 근거도 없다. 원 순서의 첫 full batch0 다음 batch1에서 이 긴 꼬리와 실제 full-mode 비용을 조기에 확인할 수 있다.

### 20.5 64번 invocation의 비용 — 복제 범위와 고정 비용을 분리

실측 full wall176.800053초는 scoring100.320383초와 그 밖76.479670초다. 후자에는 자산 전체해시 전46.300290/후11.088744초, 서버 startup14.136344초, 준비본 재독해2.687666초, 입력 hash 전후0.770747초 및 종료/영수증 등이 포함된다. **64개의 독립 프로세스**이므로 이 고정 부분만 그대로 반복해도 **4894.699초=81.58분**이다. 자산 전체해시57.389034초×64=61.21분, startup만15.08분이다. GGUF8,771,311,680바이트의 전후 두 전체해시를64회 수행하면 본체만 약1.123TB의 **논리적 해시 읽기량**이다. 실제 물리 디스크 읽기량이나 항상 같은 cache 상태라는 뜻은 아니다. 첫/끝 hash 시간 차이의 원인도 이번 metadata만으로 확정하지 않는다.

canary는 **모든100 target을 두 번** 평가했지만 [full 코드](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:1510)는 **각16행의 첫 target만 한 번 더 복제**한다. 정상 direct/probe 통제8회도 full마다 반복하지 않는다. canary17은64개 full batch 어디에도 완성 batch로 대체되지 않으므로 원첫16과 추가34도 full에서 자기 원 batch의 구성원으로 다시 처리해야 한다.

대표 비용 환산에서는 의도적으로 추가한 실패34를 제외한 **원첫16**을 썼다. KO의 실제 teacher/student 본문비는30/24=1.25, EN은65/65=1.0이다. 전체의 원 본문 target에 언어별로 적용하면 `1841*1.25 + 3032*1 = 5333.25`로 **약5333개 교사 target**, 행첫 복제1024를 더해 **약6357개 completion**이다. 원34를 포함한 KO35/29로 민감도 계산하면 약5254target/6278completion이다. 어느 쪽도 아직 없는 full teacher IDs의 정확한 계수가 아니다. canary의208을 단순1024/17배 하거나 CE target5897을 교사 target로 그대로 쓰지 않는다.

원첫16에서 통제8회와 추가34를 제외한 completion 실시간은 KO31.801679초/60요청, EN51.404790초/130요청이다. `P_i=저장된 학생 본문 시작 raw index`, `b_i=EOT 제외 학생 본문 target`, 언어비 `r_KO=1.25,r_EN=1.0`으로 정의했다. 각 언어의 실측시간을 다음 작업량 비로 환산했다.

`V_p = Σ언어 A언어 * [Σ전체 (r언어*b_i+1)*P_i^p] / [Σ원첫16 2*실제teacher_target_i*P_i^p]`

p=0은 요청 수만, p=1/2는 전체 prefix의 선형/제곱 작업량 대리값이다. **실제 교사 native 길이나 정밀 FLOPs 모델이 아니며**, 서로 다른 토크나이저·혼합 attention/선형 경로·target 위치 증가를 완전히 설명하지 않는다. full 첫 요청의 초기 비용을 빠뜨리지 않도록 canary에서 가장 느린 completion2.470091초를64회 추가 예약했다. 이것도 실제 full 초기화 비용 측정이나 수학적 상한이 아니다.

| 환산 | 가변 점수화 예상 | 고정81.58분+첫요청 여유 포함 명목 | 가변만×1.5 예약 | 고정 I/O도×1.5 스트레스 |
|---|---:|---:|---:|---:|
| 요청 수(p0) | 48.21분 | 132.42분 | 156.52분 | 197.31분 |
| 선형 prefix(p1) | 54.31분 | 138.52분 | 165.68분 | 206.47분 |
| 제곱 prefix(p2) | 63.27분 | 147.49분 | 179.12분 | 219.91분 |

의사결정에는 긴 꼬리를 반영한 **p1~2의 보수 예약166~179분**, I/O 상태까지 나빠지는 경우 **206~220분**을 제시한다. 1.5는 공개한 시간변동 민감도 가정이지 통계적 신뢰상한/새 코드의 승인문턱이 아니다. full의 bounded K 상승/forcing 재시도·UTF8 조각 빈도·이례적 I/O·별도 canary 재검산 등의 실제 비용은 아직 없다. target 누락/top2048 밖/교사 길이 초과면 다른 행이나0확률로 진행하는 것이 아니라 원 batch가 부분 실패하므로 “시간 내 반드시1024 완성”은 보증할 수 없다.

[full SH](/home/uranus/tinyLM/run_P106B_Stage7bWk_strict_probability_cache1024.sh:11)는64개의 별도16행 invocation을 max600초/외부630초로 순차 실행하고 실패하면 뒤를 미실행으로 남긴다. 64×600초=10시간40분은 **각 작업 cap의 합**이지 현재 남은 창에 들어온다는 전체 예측이 아니다. 원600초 cap의 마지막 batch는16:20까지 시작해야16:30 절대 입장에 맞는다. 상한·샘플·K·tol을 줄이는 수정은 하지 않았다.

### 20.6 학생 비교를 포함한 현재 창의 판단

12:10 총괄 추가 상태는 **Tiny BabyLM full 두 팔 완료/셋째 진행**, Falcon full은 동일 cost의5013초 외삽이 기존1시간 상한을 넘어서 미실행이다. 네 BabyLM cost JSON은 이미11:52:26까지 전부 rc0으로 닫혀 있었고 wall 합65.11초다. 이 끝난 비용을11:54 이후 창에서 다시 빼지 않는다. 현재 추가 GPU 차감 대상은 진행 중 Tiny full의 남은 시간과 이후 실제 소유 전환이다. 이 상태는 총괄 전달과 닫힌 JSON의 증거이며 독자 GPU 조회가 아니다.

11:54→16:30의 원 창은276분, 12:10 기준 남은 창은260분이다. **full cache166~179분+기존 학생 전체120분 예약=286~299분**으로, BabyLM 잔여·추가 전환·분석 시간을 빼기 전부터 원 창을 넘는다. 명목138.5~147.5분+120분이면258.5~267.5분이라 원 창의 여유가8.5~17.5분뿐이다. 실제 학생이120분 걸린다는 뜻이 아니라, **미측정 학생을 즉시 충분히 짧다고 가정하지 않으면 동시 완료의 보수 입장이 닫히지 않는다**는 뜻이다.

[기존 학생 준비](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:469)는 원64개 full cache를 모두 검산·바인딩한 뒤만 성공한다. canary17이나 일부 cache만으로 학생 cost를 먼저 재는 우회는 없다. 현재 calibrate/양 cost/양 train/세 evaluate의 닫힌 보고서는 전부 없었다. 기존 경로는 새 trainer가 아니라 원 one_update/facade를 유지한다.

| 기존 학생 단계 | 소스/SH상 내용 | 요청 wall cap의 합 |
|---|---|---:|
| 7c0W CPU prepare | full1024/64보고서·source/parent/cache SHA, 평가 길이, 보존 레코드 바인딩 | 600초 |
| 7cW calibrate | TRAIN의 한영64씩128행, 마지막 실제 block의 분리 norm/cosine·고정λ; optimizer0 | 900초 |
| 7dW cost | 같은 native595-F 초기화에서 CE/ALM 각2 update·CP0 | 2×600초 |
| 7eWa train | 두 팔 각1024×4epoch/32update, fixed1024/m8a16/ckptON/같은 optimizer | 2×1200초 |
| 7eWb evaluate | 부모/두 학생 각각 전체DEV512 TF+고정64첫답+사용자8+native32 | 3×1200초 |

합8700초=145분은 **현 개별 cap들의 합**이며 실제 학생 시간 예상이 아니다. 계획의 전체2시간은 초기 운영 예약이고 측정값도, 반드시 소모해야 하는 최소시간도 아니다. 기존 BF16 다른 SFT나 교사의 NLL 처리시간을 새 ALM32의 실측값으로 대신하지 않았다. 4epoch/팔의 실제 x1,025,068·CE23,588과 padded4,194,304를 구분하며, 두 팔 합68 update(비용4+본64)에 calibration/evaluation이 별도다.

전체 캐시 이후 두 비용이 실제로 닫히면 기존 [학생 입장식](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:1063)을 다시 적용할 수 있다. 각 팔 `u=실제2update training_seconds/2`, `O=양 cost의 관측 wall−training 합`이면 남은 양32+세 평가 예약은 **`48*(u_CE+u_ALM)+O+900초`**다. CPU 준비·calibration·2cost 자체는 이 식 전에 이미 소비하는 비용이므로 전체 시작 예산에서 빼야 한다. 이후 남은 R초에서 허용될 합은 `(R−O−900)/48` 이하이고, 실제 u가 아직 없어 이를 PASS로 계산할 수 없다. 평가900초는 측정이 아닌 기존 여유다.

별도로 [authority](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:97)는 각 호출 cap+30초 전체가 남아야 입장한다. 원 evaluate1200초 cap이면 **마지막 평가를16:09:30까지 시작**해야 하므로 단순히 “종료까지20분쯤 남음”과도 다르다. 양팔 중 한 팔이나 부모/학생 평가 일부만 닫으면 전체 대조 완료가 아니다. source/상한/분모/λ/τ를 유리하게 바꾸는 수리는 제안하지 않았다.

### 20.7 총괄 선택을 위한 세 안과 남은 한계

| 안 | 실제 범위 | 이득·한계 | 비용/영향 |
|---|---|---|---|
| A | canary 기술 복구만 보존, 새 full/학생 보류 | 새 GPU0. 전량/학생 질문은 NOT_RUN | 기존 원형·품질 음성·성공 분리 유지 |
| B | GPU 소유 전환 후 기존 full batch0→1을 각각 닫고 실제 full-mode wall·긴 prefix/target를 읽은 뒤 다음 호출 결정 | 고정 앞16의 다른 복제 범위와 전체 최대x852를 조기에 관찰. 32행은1024 완료가 아님 | 새 구조/재선택0, 기존 두16행 invocation cap 합20분. 실행 승인은 총괄 소유 |
| C | 원64batch를 순서대로 전량 닫고 학생은 full prepare/gradient/두 cost 후 남은 절대시각으로 다시 판단 | 오늘 전량 캐시를 자산으로 남길 수 있음. 양팔 효과 완료는 미보장 | 캐시 보수166~179분/스트레스206~220분+학생 미측정. 자동 전체 성공 전제 없음 |

**권장: B로 실제 full 복제범위와 긴 꼬리를 먼저 확인한 뒤 C의 계속 여부를 총괄이 결정한다.** 총괄이 오늘 전량 캐시 자체를 우선하면 C를 선택할 수 있으나, 학생 두 팔·세 평가까지의 동시 완주를 사전 약속하지 않는다. 실제 비용이 충분히 낮아 마지막 cap 입장까지 맞으면 기존 고정 학생 실험을 진행할 수 있다. 시간 부족이면 준비/부분 캐시/완료 batch를 원형 보존하고 완료량을 정확히 보고한다. 실패 행을 바꾸거나1024를 축소하지 않는다. 날짜/소스 계약이 바뀐 후의 미완 batch 자동 승계까지 지금 승인된 재개로 간주하지 않는다.

이 절은 log-to-result의 JSON·원형·관측/계산 분리, exp-preflight의 자원·입장·중복 경계, impact-analysis의 기존 세 안 비교를 **연구 문서 범위만** 적용했다. 정본 결과101/계획/기준표/COMPASS 연쇄와 실행 결정은 총괄 소유여서 수정하지 않았다. 새 registry/조건검사·회귀·GPU 실행도 하지 않았으며,17행 확률 전달 성공을 정답성/ALM 효과/75M 생산 완료로 올리지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 21. 기존 ALM 제어기의 명시적 F/Q 가족 연결 — 구현 의도와 범위

### 21.1 권한·원형·접근법

총괄은 [반 감사 §29](/home/uranus/tinyLM/docs/research/20261023_antithesis_official_eval_and_methods.md:1660)를 적용해 기존 학생 제어기에 별도 F/Q 가족을 연결하도록 승인했다. 수정 허용은 [학생 제어기](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py), [그 합성 회귀](/home/uranus/tinyLM/scripts/test_p106b_alm_train.py)와 이 소유 문서뿐이다. 별도 제어기·스킬·WIP·정본 계획·레지스트리·런처·교사·캐시·공용 `tinylm` 파일은 수정하지 않는다. 총괄이 수정 전 두 원판을 `handoff/audit/source_snapshots/20261023_pre_alm_study_profiles_*.py.txt`에 동일 바이트·읽기 전용으로 보존한 뒤 구현을 시작했다. 해당 원판/기존 준비/증거는 덮어쓰지 않는다.

| 구현 대안 | 판단·영향·비용 |
|---|---|
| 기존 제어기 전체 복제 | 기존 손실·보존·입장·평가 수리가 두 곳으로 갈라져 중복과 검토 비용이 큼. 채택하지 않음 |
| 실행 중 전역 태그·경로 치환 | 가족별 교정·자식 CP의 암묵적 혼입과 재호출 오염 위험이 있어 채택하지 않음 |
| 불변 프로필/문맥을 기존 함수에 명시 전달 | 채택. 순수 손실·실제 업데이터·삼진 구현은 그대로 두고 provenance와 경로 선택만 연결. 기존 호출은 기본 legacy로 유지 |

`impact-analysis`의 영향 축은 다음과 같이 한정했다. 코드 영향은 준비·identity·runtime·CP·평가·실행 진입의 명시 문맥 전달이며 손실/optimizer 재구현이 아니다. 데이터 영향은 새 namespace와 source pin 때문에 **새 준비본이 필요**하다는 점뿐이고, 동결1024·원문·split·캐시를 바꾸지 않는다. 시험 영향은 새 조합의 교차 거부와 실제 소형 TLinear 합성 oracle다. 정본 계획·실행등록·공유 작업원장 연쇄는 총괄 소유다. 기술부채는 legacy 기본 API를 의도적으로 보존하는 범위이며, 시간창·실물 학습비용을 합성 시험으로 대체하지 않는다. GPU/모델/부모 CP/원자료/교사 요청·설치·다운로드·Git·추가 에이전트 실행은 이 구현의 범위 밖이다.

### 21.2 가족·경로·평가 선택 계약

| 명시 선택 | 부모·실제 route | 전용 태그 |
|---|---|---|
| 생략 또는 `float_v1` | 기존 `native595-f`·`float` | 기존 `p106b_alm_train_v1_s1337` 보존 |
| `float_v2` | `native595-f`·`float` | `p106b_alm_train_float_v2_s1337` |
| `ternary_v1` | `native595-q`·`ternary` | `p106b_alm_train_ternary_v1_s1337` |

불변 `StudyProfile`과 `StudyContext`는 제어기 내부의 작은 자료형이다. 새 프로필의 준비·증거·CE/ALM CP 경로는 태그에서 분리 도출하며 런 중 전역값을 바꾸지 않는다. source map은 새로 재사용한 소형 모형 fixture의 원본 시험 파일도 포함한다. 따라서 예전 준비본의 source pin을 새 source에 맞는 것으로 간주하거나 과거 결과를 새 가족으로 재표기하지 않는다.

source closure는 기존 package 초기화·엄격 loader/native probe·기존 간접 helper와 V7의 고정 CODE 목록까지 학생 영수증에 보수적으로 포함한다. 이 목록은 소스를 해시하는 입력일 뿐 해당 함수의 실행 허가나 교사 source 수정이 아니다. import 자체는 여전히 표준 라이브러리만 사용하며, source 조회만으로 모델/토크나이저/자료를 열지 않는다.

새 두 가족의 평가 선택은 identity schema와 독립인 `EVAL_SELECTION_SCHEMA="P106B_ALM_REFERENCE_TRAIN_V1"`로 고정했다. 언어별 기존 `sha([기존schema,1337,"FIXED_DEV",root])`의 앞32·총64 선택을 재사용한다. 이는 원래 64행의 선택 규칙 보존이며, 이번 담당이 실제 DEV 원문을 다시 열어 IDs를 실물 대조했다는 뜻은 아니다. 원 DEV512·사용자8·native32와 실제 prompt 길이 입장·긴 reference 한계 공개는 기존 경로를 유지한다.

### 21.3 로드·교정·CP 혼입 방지의 의도

CPU 최초 부모 로드, CPU 자식 재로드, 실제 GPU context는 모두 같은 명시 프로필의 route 하나를 받는다. 기존 `read_selected_payload`의 동일 파일핸들 SHA/header 검증과 `validate_cfg`·`load_routed_state`의 정확한 키·shape·dtype·공유 alias·route 검증, CPU/GPU core fingerprint는 그대로 둔다. 부모 header를 retag하거나 F를 Q로 우회 로드하지 않는다. 실제 GPU 입장 전후 시각/유휴 검사와16:30 종료 계약도 바꾸지 않는다.

새 준비·공통 identity·단계 identity·교정 pin·phase report·CP experiment에 프로필과 그 SHA, 부모 core·준비 SHA·source map·route 또는 route SHA를 연결한다. 서로 다른 가족의 교정/비용/학습 receipt·child를 거부한다. Q의 λ는 Q 부모의 기존 TRAIN128 gradient 교정에서 별도로 얻는 `ρ=.25`, `τ=100`의 고정값이다. F 교정값을 Q에 재사용하거나 런 중 크기를 재조정하지 않는다. 새 trainer loop·binary-KL·head·optimizer를 만들지 않고 기존 `one_update`와 CE-only의 KL 미호출을 보존한다.

Q의 metadata에는 `TLINEAR_WEIGHTS_ONLY`, FP32 master, **FP32 tied embedding/head 예외**를 명시한다. anneal1의 기존 hard 삼진 forward와 STE-window backward를 쓰는 QAT continuation이지 전체 embedding/head까지 삼진화한 새 모델이나 GSQ가 아니다. F/Q 부모 core와 사전학습 경로가 다르므로 가족 간 차이를 양자화만의 단독 효과로 해석하지 않는다. 각 가족 안의 같은 부모 CE 대 ALM만 통제 비교다.

### 21.4 합성 검증 범위와 실물 미실행 경계

새 시험은 부모/route/header 교차 거부, 새/옛 프로필의 교정·자식 혼입 거부, 현재 source와 다른 준비 거부, 기존64 선택 규칙 고정, 명시 CLI 선택·legacy 기본값, 두 새 가족의 동일2cost/32train 업데이터 호출을 다룬다. 실제 작은 TLinear에는 hard1의 group threshold/scale와 surrogate STE의 독립식을 대조하고, CPU optimizer 갱신 뒤 캐시 refresh·checkpoint 재계산·context 종료 무효화·strict in-memory reload를 확인한다. hard quantizer의 수치 미분을 STE oracle로 쓰지 않는다. 모형/교사/코퍼스 원문이 없는 합성 CPU 범위이며 GPU는 비활성 상태로 제한한다.

원 손실 수식·anneal1·m8a16·1024행·4epoch/32update·LR/WD·상한·고정 평가를 유지한다. 활성 교사 V7의 CODE에는 이번 학생 두 파일이 없으므로 학생 source 변경을 교사 원형 변경과 섞지 않는다. 같은 V7 cache1024를 재사용하되64개 닫힌 batch의 정확한 identity/행 해시가 모두 확인되기 전 실제 준비·교정·비용·학습·평가 완료를 주장하지 않는다. source/test 재검토와 실제 학생 실행 여부·비용 판정은 총괄 소유로 남긴다.

## 22. ALM V7 원1024·64묶음의 독립 읽기 전용 실측 집계

### 22.1 입력·대조 범위와 실제 완결

총괄이 전체64묶음 종료0을 알린 뒤 **2026-10-23 13:31:33 KST**에 독립 집계를 마쳤다. 입력은 [V7 교사 캐시](/home/uranus/tinyLM/HF/sft_ready/p106b_alm_context_v7_s1337/teacher_cache)의 정확한 `batch_000000`부터 `batch_000063`까지 각 `report.json`, `raw_shards_manifest.json`, `cache_shards_manifest.json`이다. 추가 승인에 따라 manifest가 지목한 raw에서 `invocation`/`invocation_final`의 시간·상태만 골라 읽고, raw/cache 파일 자체의 byte·행수·SHA를 검산했다. 원문/확률 payload는 출력·의미 판독하지 않았다. 실제 모델·토크나이저·원코퍼스·교사 binary를 다시 로드하거나 실행하지 않았다. 학생 소스 두 개는 §21의 동결 상태 그대로이며 이 절 외 파일은 수정하지 않았다.

64개 모두 `ALM_CACHE_BATCH_COMPLETE`, rc0, 계획/완료16행, 한영 각8행이다. 실제 cache 줄 수 합1024, 언어별512이며, 각 묶음의 prepared-row SHA가 [동결 준비 보고서](/home/uranus/tinyLM/HF/sft_ready/p106b_alm_context_v7_s1337/prepared/report.json)의 해당 연속16개와 일치했다. 순서 전체가 동일하고 prepared-row/cache-row SHA는 각각1024개 고유다. 이는 원행·저장 원형 대조이며 원문 의미의 전수 검수나 새로운 독립 자료1024개 생성이라는 판정은 아니다.

| 분모 | 한국어 | 영어 | 전체 |
|---|---:|---:|---:|
| 원행 | 512 | 512 | 1,024 |
| 학생 CE target, EOT 포함 | 2,353 | 3,544 | 5,897 |
| 학생 KD 본문 target, special 제외 | 1,841 | 3,032 | 4,873 |
| 고유 교사 본문 target | 2,306 | 2,816 | 5,122 |
| 정렬 KD chunk | 1,790 | 2,465 | 4,255 |
| 본문 정렬 byte | 6,980 | 11,553 | 18,533 |

모든 묶음·양 언어의 reference/student/teacher **본문 byte 및 적격 본문 target 수락률**은1.0이다. 이는 전체 template 일치나 CE target 전체의 KD 편입을 뜻하지 않는다. CE와 학생 KD의 차이1024는 행당 EOT 한 개의 **CE 유지/KD 제외**와 부합한다. 이번 재집계는 보고서의 언어별 수치와 저장 줄/해시를 대조했으며 cache JSON 본문을 전수 재해석해 정렬 수식을 다시 실행한 것은 아니다.

completion은 **고유5122 + 행별 첫 target cold 재관측1024 = 6146건**이고 시도/성공이 모두6146이다. bias200 추가 시도는0, 비고유/검증 요청은1024다. 전체 cache의 검증 범위는 `FIRST_TARGET_COLD_REPLICATE_PER_ROW`이므로 §20의17행 canary가 모든 target를 두 번 관측한 분모와 다르다. HTTP 전체 시도10367/성공9858은 completion과 다른 분모다. 그 차이509의 경로별 내역은 이번 제한 읽기로 재분해하지 않았고 completion 실패509건으로 해석하지 않는다.

### 22.2 시작·종료·합산 시간의 서로 다른 경계

| 시간 경계 | 실제 관측/집계 |
|---|---|
| 총괄이 제공한 외부 원로그 | 12:13:38 시작~13:24:07 마지막 묶음 종료 KST, 초 단위4229초 |
| 첫 raw `invocation` UTC | `2026-10-23T03:13:41.596721+00:00` =12:13:41.596721 KST |
| 마지막 raw `invocation_final` UTC | `2026-10-23T04:24:06.768006+00:00` =13:24:06.768006 KST |
| 위 raw 최초~최종 경과 | 4225.171285초, 70분25.171초 |
| 각 raw invocation~final의 합 | 3979.627334초 |
| 묶음 사이63개 raw 경계 간격 합 | 245.543951초 |
| 각 보고서 full wall 합 | **4134.780496초, 68분54.780초** |
| 묶음별 full wall | 최소49.538604/중앙62.862644/평균64.605945/최대82.157021초 |

파일 mtime을 시작·종료로 대체하지 않았다. raw 시작은 준비본 읽기 이후이고 raw final은 마지막 shard/manifest 검산·보고서 쓰기 이전이므로 외부 로그·raw 구간·full wall 합은 같은 수치가 될 필요가 없다. 각 묶음 raw UTC 구간과 같은 두 event의 monotonic 구간 차이는 −0.000026217~+0.000007493초였다. 이 범위는 이번 두 경계의 관측이며 다른 날짜의 시계 정합이나 지속 계측을 보증하지 않는다.

| 각 단계의 보고값 합 | 초 |
|---|---:|
| native tokenization·확률 채점 | 3101.177606 |
| 교사 자산 전체 해시, 입장 전/종료 후 | 323.014702 / 329.004212 |
| 준비 selection 읽기 | 150.510668 |
| 교사 startup | 129.310856 |
| 입력 해시, 전/후 | 2.365643 / 2.448115 |
| 소스 해시, 전/후 | 0.088752 / 0.102254 |
| TF 선결 보고서 검사 | 0.065411 |

full wall은 원래 코드의 해시·startup·shutdown·보존/검산을 포함한다. 위 개별 계측항의 합을 전체시간으로 대체하지 않으며, 나머지 호출·정리·보존 시간을 교사 채점으로 임의 배분하지 않았다. 가장 느린 묶음은1번82.157021초, 다음13번82.103357초, 7번79.830194초이며 모두600초 상한 아래다. 이것은 실제 캐시 비용이고 학생 교정/학습 비용의 관측은 아니다.

### 22.3 메모리·teardown·원형 상태

| 보고서 계측, MiB | 64묶음의 범위/최악값 |
|---|---|
| 입장 전 global GPU baseline | 1123~1166 |
| 표본 global GPU peak | 9584~9649, 전체 보고 최대9649 |
| baseline 대비 표본 GPU 증가 | 8441~8514 |
| 표본 최소 GPU free | 각묶음6413~6478, 전체 보고 최소6413 |
| 소유 교사 프로세스 peak RSS | 8768.238281~8768.527344 |

이는 **200ms 표본의 global GPU 및 소유 프로세스 RSS**다. 저장 용량·GPU parameter 크기·지속 peak·짧은 spike 미발생을 뜻하지 않는다. 직렬64프로세스의 RSS/peak를 더하지 않았다. memory 요약의 표본 합은13042, 종료 후 `successful_memory_samples` 합은13052다. 묶음 **1,6,7,28,35,37,44,47,49,63**에서 종료 후 수가 각각1개 많다. [현재 소스의 memory 요약](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:1525)은 session 내부에서, 최종 sample 수는 teardown 뒤에서 취합하므로 서로 다른 시점의 분모다. 집계기의 최초 동일성 가정이 이10건에서 거부되어 두 수치를 분리했다. 보고서를 고치거나 원형을 이상 없이 같았다고 바꾸지 않았다. 추가10표본의 peak를 이번 제한 읽기에서 재계산하지 않았으므로 위 메모리 수치는 기존 요약의13042표본 범위다.

64개 모두 source/input/teacher asset 전후 `MATCH`, owned exit0, 소유 background thread 닫힘, raw 보존오류0, telemetry 오류0이다. 소유 PID는64개 고유이며 학생 로드/체크포인트 쓰기는0이다. attention ubatch 실패·KV 공간 경고 합은 각각0이다. GDN AR/chunked 필드는64개 모두 null이므로 enabled/disabled를 새로 추정하지 않는다. cache prompt·의미 전수검수·품질 주장·8시간 생산 재개는 모두false다. `full_cache_complete`도 각 단일 invocation에서는 의도대로false이며, **이번 전체 완결 판단은 연속64개 모두의 실제 폐쇄·1024행 원형 대조**에서 나온다.

독립 재해시는 보관된 report/manifest/raw/cache 및 현재24개 소스에 한정했다. 교사 binary·런타임 라이브러리·원코퍼스를 다시 해시한 것이 아니라 각 실행의 종료 전후 해시 `MATCH` 영수증을 확인했다. 현재24개 source는 준비/각64개 identity의 동일 map과 모두 일치했다.

### 22.4 파일 SHA 영수증과 소형 재현식

| 입력·보존 대상 | 독립 대조값 |
|---|---|
| 준비 report SHA256 | `D455646EB13158272B95960776EBD85874EDFAAE5B3D0A7B6979293402805C37` |
| 공통24소스 map의 canonical SHA256 | `44CC41527D2BD8DEC9296959F8A7568E7657D1EFEDCA2F766D3A03139BAF1293` |
| 192개 report/manifest의 총 byte | 3,101,914 |
| 그 파일목록 canonical SHA256 | `AC47AEDD39FADEBB3DF47272427822A912911B7CC8586F50BFF2594A2694061B` |
| 실제 raw64개 | 232,005줄 / 240,683,506 byte |
| raw를 묶음·shard 순서로 연결한 SHA256 | `91C32D12058BE9E55942774A3B020B1DBCCD37A8E1C12B078766E70F81CE7283` |
| 실제 cache64개 | 1,024줄 / 155,154,603 byte |
| cache를 같은 순서로 연결한 SHA256 | `1FD3340DAE76ABC14B99160AD43AB796A796697CA609F4C93697D11C6D60F5EA` |

192개 목록의 한 항목은 `[저장소 상대경로,실제 파일SHA256,byte수]`이며 batch0→63마다 report→raw manifest→cache manifest 순서다. 모든 shard는 실제 byte/줄수/마지막 LF/SHA와 manifest의 concat SHA가 일치했고, 각파일이20MB 미만임을 확인했다. 데이터를 잇는 새 파일은 만들지 않았다.

다음은 같은 종료 원형의 핵심 분모·시간·해시를 다시 읽는 소형식이다. 표준 라이브러리와 기존 stdlib-only shard 검산만 사용하며 모델/HTTP/학생 실행은 없다. 출력은 집계·해시·최초/최종 시간뿐이다.

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B - <<'PY'
from pathlib import Path
from collections import Counter
import hashlib,json,math
from scripts.p106b_shards import verify
root=Path('/home/uranus/tinyLM')
base=root/'HF/sft_ready/p106b_alm_context_v7_s1337/teacher_cache'
enc=lambda v:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
sha=lambda b:hashlib.sha256(b).hexdigest().upper()
reports=[];inventory=[];bounds=[];languages={'ko':Counter(),'en':Counter()}
whole={k:hashlib.sha256() for k in ('raw','cache')}
for i in range(64):
    directory=base/f'batch_{i:06d}';path=directory/'report.json'
    raw=path.read_bytes();r=json.loads(raw);reports.append(r)
    assert r['returncode']==0 and r['status']=='ALM_CACHE_BATCH_COMPLETE'
    assert r['batch_index']==i and r['rows_completed']==16
    inventory.append([str(path.relative_to(root)),sha(raw),len(raw)])
    for language,values in r['language_totals'].items():
        languages[language].update({k:v for k,v in values.items() if type(v) is int})
    for stem in ('raw','cache'):
        path=directory/(stem+'_shards_manifest.json');raw=path.read_bytes();m=json.loads(raw)
        inventory.append([str(path.relative_to(root)),sha(raw),len(raw)])
        assert m==r[stem+'_manifest'];verify(directory,m)
        for spec in m['shards']:
            with (directory/spec['path']).open('rb') as stream:
                for line in stream:
                    whole[stem].update(line)
                    if stem=='raw' and any(x in line for x in
                        (b'"event":"invocation"',b'"event":"invocation_final"')):
                        event=json.loads(line)
                        bounds.append((event['event'],event['utc']))
print('totals',{k:sum(r[k] for r in reports) for k in
    ('rows_completed','unique_targets_completed','completion_attempted','completion_succeeded')})
print('languages',{k:dict(v) for k,v in languages.items()})
print('sum_full_wall_seconds',math.fsum(r['wall_seconds'] for r in reports))
print('first_last_utc',bounds[0],bounds[-1])
print('metadata_inventory_sha256',sha(enc(inventory)))
print('concat_sha256',{k:v.hexdigest().upper() for k,v in whole.items()})
PY
```

상태는 **원1024의 확률·정렬 캐시 저장/폐쇄 관측**이다. 파싱·checksum·수락·종료가 맞다는 사실을 정답성·교사 지능·ALM 학습 효과·새 학생 완성·정식 TRAIN_READY로 승격하지 않는다. `log-to-result`의 수치 JSON/원형 대조와 관측·계산 분리만 이 소유 문서에 적용했고, 공유 결과/계획/기준표/WIP/런처 연쇄는 총괄 소유로 유지했다.

## 23. 첨부 §2·§3.3 이후 요구의 구현·실행 범위 감사

### 23.1 조회 범위와 시각 정정

대상 정본은 [첨부 작업지시 §2·§3](/home/uranus/tinyLM/ai_dev_tool/temp_20261023_작업지시서_참고용.md:119)이며, 읽은 파일 SHA256은 `07ED9B5F105A859533DDD73E8B8844AFF0493D544F40C52CBE65A317EE7F39DF`다. 제품/실험 Python 소스는 `tinylm/`와 `scripts/`를 명시 범위로 검색하고, 연결 함수와 아래 결과 절·닫힌 JSON의 선택 지표를 읽었다. 설치 패키지 목록·외부 코드의 현재 공개 상태·다른 저장소 전체까지 부재를 증명한 것은 아니다. 새 모델/토크나이저/교사 로드·학습·GPU·시험·설치·코드 변경은 없다. 현재 생산 중인75M의 원문·진행 로그를 열어 이번 비교의 완료로 가산하지 않았다.

**정정:** 중간 전달에서 정 담당이 UTC→KST에 한 시간을 잘못 더해 쓴 **“14:50 조회”는 철회한다.** 최초 조회의 정확한 실행 시각은 기록하지 않았으므로 추정 시각으로 대체하지 않는다. 그때 F 학생 `evaluate_ce`·`evaluate_alm` 보고서가 없었던 관측과, 이후 실제 폐쇄를 구분한다. 총괄은 F 세 평가가13:50:20 KST까지 닫혔다고 회수했으며, 이것은 총괄이 제공한 종료 경계다. 정 담당의 **명시 시각을 남긴 선택 scalar 재조회는13:56:07.399397~13:56:07.403928 KST**이고, 이때 F/Q 각3개 모두 `ALM_EVALUATION_COMPLETE`/rc0를 확인했다. 파일 mtime을 실행 시각으로 쓰지 않았다. 따라서 앞 절/초기 문헌표의 당시 `NOT_RUN`을 현재 학생 두 가족의 미실행 판정으로 재사용하지 않는다.

이 절은 이미 완료한 작업을 다시 계획하는 문서가 아니라 **요구별 실제 도달 범위와 미완 사유의 대조**다. 아래 `NOT_RUN`은 해당 새 방법의 실제 대조·단기 학습이 없다는 뜻이며, 효과 없음·OOM·교사 능력 부족이라는 음성 결과가 아니다.

작성 중23.5 소제목에 한국어가 아닌 표현이 섞였던 잘못도 발견해 한국어로 바로 정정했다. 다른 언어의 표현을 사용하지 말라는 지시를 다시 어긴 사실을 숨기지 않으며, 잘못된 표현 자체는 재인용하지 않는다. 수정 후 이 절의 한국어 외 동아시아 문자 혼입0을 읽기 전용으로 확인했다.

### 23.2 §2 가속 — 재사용할 구현과 실제 미완

| 첨부 요구 | 확인한 기존 구현·정확한 접점 | 실제 실행 증거 | 아직 충족하지 않은 부분·미완 사유 |
|---|---|---|---|
| 유효 위치만 출력 head/CE 계산 | [mtp_sft.components](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:117)는 assistant 유효 위치 gather→위치 chunk→head checkpoint를 이미 사용한다. [alm.target_nll](/home/uranus/tinyLM/tinylm/train/alm.py:19)은 같은 유형의 per-target NLL을 제공하고 [ALMCore.components](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:848)가 chunk64로 쓴다. | 현재 F/Q의 CE·ALM 각32update가 이 경로로 실제 완료됐다(§23.4). | 기존 gather/chunk/checkpoint를 새 CCE/Liger 구현이나 새 가속 이득으로 가산하지 않는다. 현재 CE·ALM 비교는 출력 head 가속 대조가 아니다. |
| **§2.1 최우선 fused output-head/CE** | [p102a_contract._LossFirstCE](/home/uranus/tinyLM/tinylm/train/p102a_contract.py:26)는 **이미 구현된** FP32 scalar CE 합/행 chunk 재계산형이다. [trainer의 loss_first 분기](/home/uranus/tinyLM/tinylm/train/trainer.py:1069)도 있다. 반면 [입장 제한](/home/uranus/tinyLM/tinylm/train/trainer.py:212)은 chat32 tokenizer·KD·compile·다른 경로와의 결합을 거부한다. | [결과093 §1~3](/home/uranus/tinyLM/test_result/093_20260925_P102A-기능통과-T1-단일순서-속도관측.md:5): 작은 CPU FP32 loss/전 gradient/한 SGD update 통과. S1 최대차는 각각4.7683716e-7/1.4901161e-8/9.3132257e-10. CUDA BF16 peak·whole-step 가속의 증거가 아니다. | 범위 검색에서 CCE/Liger API 연결을 찾지 못했다. P102A는 어휘 타일 LSE형 CCE가 아니며, scalar 합만 반환해 현재 ALM의 위치별 비선형 upstream gradient 계약도 아직 연결되지 않았다. **현재 chat32/BF16의 tied 입력+출력 table/projection 전 gradient·같은 optimizer 한 update·메모리/시간 비교는 NOT_RUN.** 총괄도 이번 최우선 항목의 실제 미완을 누락으로 인정했다. 자원상 불가능했다고 소급하지 않는다. |
| CCE/Liger별 새 연산과 확률 제공 | [factorized tied head](/home/uranus/tinyLM/tinylm/model/transformer.py:440)는 `h→r→V`와 기존 공유 table 접근자를 소유한다. [문헌검토 §3](/home/uranus/tinyLM/docs/research/20261023_acceleration_distillation_literature.md:34)은 CCE의 어휘 타일/LSE와 Liger의 위치 chunk logits·CE/gradient 재사용을 구분한다. | 외부 API의 현재 로컬 adapter·동등성·처리량 실측은 찾지 못했다. | 재사용할 것은 기존 projection/table/shift/mask/전체-update 분모다. 새로 남은 것은 실제 backend 접합과 per-token 가중 손실·anchor logits/LSE 계약이다. CCE/Liger가 full KL까지 제공한다고 가정하지 않는다. 32K 실측과 향후248K 추정은 별개다. PyTorch 내부의 암묵적 kernel fusion 여부까지 부정한 것은 아니다. |
| §2.2 NorMuon | [Muon.step](/home/uranus/tinyLM/tinylm/train/muon.py:127)는 momentum `buf`+NS5, Jordan/RMS 두 배율을 이미 제공한다. [현재 ALM optimizers](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:993)는 기존 RMS4 Muon/AdamW 그룹을 재사용한다. | 기존 Muon은 실제 학습에 사용됐다. **NorMuon 대조는 NOT_RUN.** | bounded source 검색에서 NorMuon optimizer/선택지를 찾지 못했다. 기존 `scale_mode="rms"`에는 NorMuon의 NS 뒤 **행별 제2모멘트**가 없다. 논문 RMS 정규화와 공식 main의 norm보존+Jordan 규약 선택, None와0 gradient, 그룹·LR·추가 state/whole-wall/time-to-quality 검증이 남았다([문헌 §4](/home/uranus/tinyLM/docs/research/20261023_acceleration_distillation_literature.md:66)). |
| §2.2 AdaMuon | 기존 Muon·고유 parameter 분할/영수증은 재사용 가능하다. | **AdaMuon 대조는 NOT_RUN.** | 현재 source에는 sign(momentum)→NS 뒤 원소별 second moment/RMS 경로가 없다. 문헌의 distributed 구현을 단일 GPU drop-in으로 간주하지 않는다. 추가 원소별 state의 실제 메모리·step/전체시간·같은 품질 도달시간도 미측정이다. FP32 상태라면 추가4×행렬원소 bytes라는 산술과 실측 peak를 구분한다. |
| §2.3 점진 문맥128→256→512→1024 등 | [Loader](/home/uranus/tinyLM/tinylm/data/loader.py:10)는 생성 시 받은 고정 `seq`로 crop한다. 현재 학생 [do_train](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:1024)은 4epoch 내내 `fixed1024`를 기존 updater에 전달한다. | 현재32update는 **고정1024** 실행이다. 문맥 성장 schedule 대조는 **NOT_RUN**. | 단계별 길이·batch/accum·동일 token/원문 노출 예산·packing/문서경계·최종1024평가를 연결한 경로를 찾지 못했다. 모델의 `repeat_mode="progressive"`는 층 방문 깊이이며 문맥 길이 curriculum이 아니다. 아래 PAD 말미 축소도 실제 문맥 성장과 다르다. |
| §2.4 causal+MNTP | [기존 attention](/home/uranus/tinyLM/tinylm/model/modules.py:112)은 학습 SDPA의 causal visibility를 소유한다. [mtp_sft.horizon_targets](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:66)는 같은 assistant 구간의 미래 horizon 정답을 만드는 **MTP**다. | 현재 ALM은 causal·MTP OFF다. **MNTP 입력 손상/visibility 혼합 학습은 NOT_RUN.** | MTP·assistant loss mask를 MNTP로 세지 않는다. source 범위에서 MNTP corruption/shift·masked visibility·causal:masked 배치 비율의 통합을 찾지 못했다. causal KD와 masked CE의 분리, 최종 causal LL/생성 대조까지 남았다. loss 항 하나의 추가로 끝나는 상태가 아니다. |
| §2.4 adaptive 대 uniform masking | 기존 assistant 감독 mask와 [balanced_mtp_micro_mask](/home/uranus/tinyLM/tinylm/train/p102a_contract.py:98)는 각각 감독 범위·보조 MTP micro 선택이다. | P102A 선택 기대값의 합성 검산은 이미 있으나 **적응형 입력 token masking 대조는 NOT_RUN.** | uniform 통제군·mask-rate/통계 갱신·한국어/희귀 token/숫자 편향·원문 노출량을 다루는 학습 경로를 찾지 못했다. 기존 mask 이름이나 half-micro 선택을 adaptive token masking으로 바꾸어 세지 않는다. |
| 별도 가속 관측: PAD 말미 crop | [PAD 진단](/home/uranus/tinyLM/scripts/diag_p101a_padding_gpu.py)과 기존 updater는 이미 있다. | [결과092 §24](/home/uranus/tinyLM/test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md:1346): BF16 ABBA 측정8update씩28.381334419→17.498542566초,1.6219256배. 그러나 FP32 한 update 후157개 중85개 가중치가 기존 허용차를 넘어서 exit9. | timing0을 수치 채택으로 승격하지 않았다. gradients157/state301 통과와 update85개 실패를 함께 보존한다. Muon BF16 NS 증폭은 아직 원인 분리 전 가설이다. 현재 ALM은 fixed1024를 유지한다. 이 결과로 점진 문맥/CCE가 실행됐다고 하지 않는다. |
| §2.5 종합 채택 근거 | 학생/교사 보고서에 phase wall·warmup/cost·단계/peak 일부가 이미 있다. | cache·학생의 실제 wall/peak는 §22·§23.4에 구분했다. | 위 새 가속법의 같은 품질 도달시간, token budget 대 wall budget, 원문 bytes/s, optimizer-state 실측을 포괄한 비교는 **미완**이다. 단일 step 감소·PAD 속도·P102A eval/save cadence의 관측을 이 전체 요구의 완료로 합산하지 않는다. |

검색에서 나온 [trainer.py:719](/home/uranus/tinyLM/tinylm/train/trainer.py:719)의 `AdamW(...fused=True)`는 **optimizer update**이며, [ternary.py의 fused int8 linear](/home/uranus/tinyLM/tinylm/model/ternary.py:255)는 별도 양자화 linear다. 어느 것도 output-linear+CE 접합 증거가 아니다. 반대로 기존 P102A loss-first가 존재하므로 **“fused CE 관련 구현이 전혀 없다”도 잘못**이다. 정확한 미완은 **사용자가 우선 요구한 현재 chat32 경로의 CCE/Liger식 명시 접합·동등성·실제 가속 비교**다.

### 23.3 §3.3~3.6 증류 — 실제 도달과 미완

| 첨부 요구 | 재사용할 기존 코드·현재 신호 | 현재 실제 상태 | 미완 원인·주장 경계 |
|---|---|---|---|
| 같은 자료 CE/SFT-only 대조 | [ALMCore](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:809)는 weight0이면 KL 함수를 부르지 않으며 CE·ALM에 같은 원주석 reference/순서/전체-update CE 분모를 쓴다. [do_train](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:1024)은 기존 `one_update`·optimizer를 재사용한다. | **F/Q 각 CE-only32update 실행 완료.** 같은 자료/부모 안의 loss 대조가 존재한다. | 이번 reference는 원래 주석 답이며 교사는 그 답의 확률을 제공한다. 이것을 새 교사가 생성한 답으로 만든 SFT-only 자료라고 부르지 않는다. 별도 온라인 pseudo-SFT/75M 생산을 이 네 팔에 합치지 않는다. |
| ALM+현재 삼진 경로, 별도 실수 가족 | [alm.py](/home/uranus/tinyLM/tinylm/train/alm.py:74)의 chunk TF logp→Bernoulli KL, [template_alignment](/home/uranus/tinyLM/scripts/p106b_alm_template_alignment.py), V7 native teacher 본문 byte 정렬, 기존 updater facade가 연결돼 있다. EOT는 CE 유지/KD 제외다. | **원1024 cache 폐쇄 및 F/Q 각 CE·ALM32update/3팔 평가 완료.** 실제 수치는 §23.4. | `no-hidden/no-outcome-debias` ALM 핵심형이다. TRAIN128의 last-block norm비로 고정λ를 정했고 원문 전체 GradMag 구현은 아니다. Q는 native595-q의 TLinear STE, F는 native595-f의 float로 다른 부모/core다. F 대 Q 차이를 양자화 단독 효과로 부르지 않는다. **FP32 tied embedding/head 예외**가 있으므로 최종 전부 삼진/40MB 달성도 아니다. |
| ACTD 최소 구현·단기 학습 | V7의 reference TF 요청·byte/ID 계보·raw 보존은 재사용 가능하다. 별도로 [기존 kd_cache.py](/home/uranus/tinyLM/tinylm/train/kd_cache.py:27)에 **같은 ID 공간**의 top-k 저장/제한 KL이 이미 있다. | ACTD 목적함수/first-subtoken anchor/잔여질량의 제품·실험 연결을 못 찾았다. **최소 구현·단기 학습·로컬 비용 모두 NOT_RUN.** | V7 [직접 요청](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:800)의 기본은 n_probs2이며 UTF-8 fragment probe에서만64/512/2048을 늘릴 수 있다. 모든 위치의 top64 anchor cache가 아니다. mapping(BOS 자동 삽입 금지·중복/조각 처리), student anchor 확률+정확한 LSE/residual과 그 gradient가 추가로 필요하다. 기존 per-target NLL이나 같은-ID top-k KL만으로 ACTD가 되지 않는다. [문헌 §5.3](/home/uranus/tinyLM/docs/research/20261023_acceleration_distillation_literature.md:133)의 teacher top-k 재정규화/학생 residual 목표0은 ACTD 정의이며 full KL/tail 보존은 아니다. 공식 코드 공개 여부의 과거 조사만으로 구현 불가를 선언하지 않는다. |
| DSKDv2 최소 구현·단기 학습 | 현재 HF teacher wrapper·[일반 _kd_kl](/home/uranus/tinyLM/tinylm/train/trainer.py:40)은 기존 logits KD 자산이다. V7 GGUF 경로는 reference target 확률을 제공한다. | 새 양방향 projector/ETA·두 prediction head 미분 경로 연결을 못 찾았다. **NOT_RUN.** | 필요한 teacher hidden·head/projector 입력 VJP가 현재 GGUF target-logp 계약에 없다. frozen teacher라고 head 입력 미분까지 불필요해지는 것은 아니다. 기존 HFTeacher는 logits 인터페이스이며 tokenizer/vocab 대응과 hidden/head 미분 접합을 자동 제공하지 않는다. 실제 작은 모델 비용·메모리도 아직 없다([문헌 §5.4](/home/uranus/tinyLM/docs/research/20261023_acceleration_distillation_literature.md:141)). |
| DWA-KD 최소 구현·단기 학습 | TF 요청/학생 학습 seam은 재사용 가능하지만 DSKD형 양공간 신호가 먼저 필요하다. | entropy weighting·lexical/contextual Soft-DTW/attention 연결을 못 찾았다. **NOT_RUN.** | 단순 confidence 가중 loss는 전체 DWA-KD가 아니다. 필요한 hidden/embedding/정렬 연산이 현재 cache 신호에 없고 최소 구현·단기 학습을 아직 하지 않았다. 논문 다른 모델의29.92GB/step시간을 로컬 예상이나 실측으로 이식하지 않는다. |
| DVLM 최소 구현·단기 학습 | 현재 학생 native vocabulary·source identity·교사 세션 자산 검산은 재사용 가능하다. | PTS 입력 group/HPA·교사의 새 학생-vocab head 학습·후속 OPD를 찾지 못했다. **NOT_RUN.** | 현재 causal GGUF endpoint에 head 하나를 붙인다고 입력 token 불일치와 visibility가 해결되지 않는다. teacher 입력/attention 경로 수정과 별도 두 단계가 아직 없으며, 큰 비용 가능성과 실제 OOM/실행 실패는 구분한다. 문헌의 자원 수치는 이 로컬 실행값이 아니다. |
| **ALM+GSQ 이산 최적화** | [p093b_native_repair.GSQProjection](/home/uranus/tinyLM/scripts/p093b_native_repair.py:96)에 mask/sign Gumbel-Softmax·학습 scale·hard 배정이 **이미 있다**. `fit`은 기존 함수 재구성 목표다. | [결과103 §1~3](/home/uranus/tinyLM/test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md:9): 공유 MLP 배정250회 실행/과학적 음성8. NRMS0.996645→0.982631, 오류감소1.406%로 사전10% 문턱 미달, 보정4.891초. **외부 교사 CE+ALM의 GSQ 학습은 NOT_RUN.** | 현재 ALM route에 GSQ code/scale 수명·optimizer group·hard forward/평가·온도·붕괴/gradient/RNG/checkpoint·embedding/head 제약이 연결되지 않았다. 기존 함수 복원 음성을 GSQ 전체 기각으로 쓰거나, 정상 자유답변을 새 GSQ 시작의 선결로 만들지 않는다. 같은 CE/KD·초기 hard codes/scales·자료/노출의 STE 대조가 미완이다. 원형 GSQ의 soft-train/hard-extract와 이 hard QAT/KD 변형도 구분한다. |
| §3.5 reference 확률·캐시·총 비용 | V7 원1024의 입력/교사/template/shift/mask/byte/요청·응답 계보와64묶음 폐쇄는 **이미 실행**됐다(§22; [공유 결과101 §462](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:22221)). | rows1024·고유교사 target5122·completion6146, report full-wall 합4134.780496초. | 전체 template가 같은 것은 아니고 **assistant 본문 byte**만 대응한다. reference 확률 수집 성공은 정답성·hidden KD·full KL·매위치 top64 확보가 아니다. cache 재사용 뒤 학생 시간과 최초 cache 비용을 분리하며 64회 startup/해시 비용을 숨기지 않는다. |
| §3.6 새 KO100+EN100 final holdout·usable-response | [현재 evaluate](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:1112)는 고정 **OLD_DEV64+사용자8+native32**다. Core6/BabyLM은 별도 공식 평가 경로다. | 이번6개 평가의 문자열 exact는 모두0/64. TF CE와 원답 보존은 실제 관측이다. | **이번 학생 비교에서 새200문항 final holdout/출력안정·질문대응·정확성의 공동 usable-response rate는 NOT_RUN.** exact0만으로 의미 정답0이라고 단정하지 않고, TF CE/문법성/공식 후보선택을 정상 자유답변 확보로 승격하지 않는다. |
| 조건부 X-Token/BLD·후속 on-policy | 문헌 요구와 현재 경계를 정리했으나 이 감사 범위의 source에서 새 목적함수/단기 학습을 확인하지 못했다. | **NOT_RUN.** | 조건부 후속 후보이며 현재 구현/실행됐다고 세지 않는다. 기존의 약한 자유답변을 self-teacher로 쓰거나 on-policy-only를 지금 모든 방법의 필수 전제로 강제하지 않는다. |

기존 [top-k 제한 KL](/home/uranus/tinyLM/tinylm/train/kd_cache.py:93)은 교사 원확률의 선택 항만 합하며, 현재 cross-tokenizer ALM/ACTD 정렬이나 tail 합계가 없다. 또한 [HFTeacher](/home/uranus/tinyLM/tinylm/train/hf_teacher.py:48)의 기존 어휘 크기 검사는 임의 다른 ID mapping의 동등성 보증이 아니다. 이 자산들은 **이미 있는 일반 KD 구현**으로 재사용 경계를 표시하되 위 새 방법의 완성으로 합산하지 않는다.

### 23.4 현재 실제 학생 네 팔과 여섯 평가 — 문헌/계획과 분리

근거 디렉터리는 [F 실수 가족](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_float_v2_s1337)과 [Q 삼진 가족](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337)다. 각 가족의 `calibrate`·`cost_ce`·`cost_alm`·`train_ce`·`train_alm` 및 평가 보고서는 모두 닫힌 rc0다. 네 학습 팔은 각각32update·원1024행4회·실제 x1,025,068·CE target23,588·KD chunk17,020으로 같은 노출 분모이며, CE-only는 KD chunk 수를 계보/관측용으로 보존하되 KL을 계산하지 않는다. 고정 m8×a16·checkpoint ON·BF16 eager·MTP/compile OFF, AdamW LR1e-5/Muon RMS4 LR4e-5·WD0·clip1·seed1337이다. 동일 가족 안에서는 같은 parent/core에서 fresh optimizer/RNG 영수증으로 시작한다. F/Q 부모와 보정λ가 다르므로 이 표는 양자화 단독 대조가 아니다.

| 가족/학습 팔 | 고정λ | report full-wall, 초 | history 최대 allocated/reserved, MiB | update/CP 쓰기 |
|---|---:|---:|---:|---:|
| F CE | 0 | 115.055185 | 1957.626953 / 2040 | 32 / 1 |
| F ALM | 13.131641128023277 | 127.033616 | 1957.627441 / 2042 | 32 / 1 |
| Q CE | 0 | 128.368918 | 2605.899414 / 2760 | 32 / 1 |
| Q ALM | 36.32277684798984 | 138.486527 | 2605.899902 / 2760 | 32 / 1 |

위 peak는 PyTorch allocator 보고값이며 global GPU/RSS나 optimizer-state 단독 메모리가 아니다. full-wall은 각 phase 입장~최종 보고서 쓰기 전의 준비/로드/해시/정리를 포함하고, 사전 `cost`나 교정·교사 cache·다른 팔 평가까지 포함한 전체 연구시간은 아니다. F/Q 교정 full-wall은 각각9.376556/7.872191초이며 λ는 자기 부모의 TRAIN128 norm비에서 측정했다. 정상 종료와 유한 gradient는 학습 효과의 증거를 대신하지 않는다.

| 가족/평가 팔 | OLD_DEV64 TF CE, 2977 target | native32 CE, 32768 target | 원문 exact | 평가 full-wall, 초 |
|---|---:|---:|---:|---:|
| F parent | 6.135389354 | 3.203985751 | 0/64 | 81.055303 |
| F CE | 5.815453511 | 3.206979752 | 0/64 | 80.199171 |
| F ALM | 5.820518983 | 3.207073390 | 0/64 | 81.384076 |
| Q parent | 6.132168094 | 3.357963562 | 0/64 | 83.383450 |
| Q CE | 4.636132304 | 3.395286858 | 0/64 | 88.435917 |
| Q ALM | 4.769204152 | 3.395796478 | 0/64 | 82.461979 |

관측 범위에서는 두 가족 모두 OLD_DEV TF CE가 부모보다 내려갔지만 ALM이 같은 가족의 CE-only보다 낮지는 않다. 단일 seed/32update/기존 DEV의 관측이며 모든 ALM·GSQ·교사 지식 전달을 기각하는 결과는 아니다. 문자열 exact·엄격 공백 exact·공백 collapse exact는 여섯 팔 모두0이고, long/unknown reference length case도 모두0이다. 그래도 답의 의미 전수 판정을 이 scalar 감사로 수행한 것은 아니므로 `usable-response=0%`나 “정상답변 확보”로 바꾸지 않는다. native32는 고정 첫32개1024 crop이며 전체 VAL/두 언어 능력의 대표 점수가 아니다.

각 보고서에서 source/input/parent checkpoint 전후 불변은 모두true였다. 이를 실행 영수증으로 확인했으며 checkpoint tensor를 다시 로드/해시한 것은 아니다. 학생 제어기/시험의 현재 SHA는 각각 `C8EFF2B4F84AE31EA66DD55F8EC3F22771E1CCE89FD9EFB992D18F34F103E51E` / `582F2B91BA1AED6E108304D817A1E24E640B7A551FD827ABB8C5C47102A4F51C`로 동결돼 있다. 이 감사에서 source를 바꾸지 않았다.

| 닫힌 report, 위 F/Q 디렉터리 기준 | 실제 파일 SHA256 |
|---|---|
| F `train_ce/report.json` | `FF5D992A1294ADA114171739F453F2A3F1840E5B0FA5FE988009F3B4F3B14A2F` |
| F `train_alm/report.json` | `D5EAFF3653EA2A60324EF7B95CDAFEB876D84157F9AE2903D642F54868975BC3` |
| Q `train_ce/report.json` | `2B1B4EFF2B4F7BC64CEB63E35A1C32760A24B5980DD52F30B04DC4A346AB4C94` |
| Q `train_alm/report.json` | `766F2BF7B540CFBBA150456DB819918F7F18CFD12CFC5997CC83C7F7E1C9FB5D` |
| F `evaluate_parent/report.json` | `E0629909F30C89132788C5150D8F23D5BBF999DADC970C8AE40B44A22839383A` |
| F `evaluate_ce/report.json` | `9C090548CFD39F0B4A44B07A771545C8631B5346808B485093B07F3FCAB509F7` |
| F `evaluate_alm/report.json` | `47807406258B1DD61135DB00DDBAFF29CB03E2E577B882137E7F07AE4194026B` |
| Q `evaluate_parent/report.json` | `6A344507A3AC2DC398A53052325448D43387DDA6B4DD70A9559D286014EE4C92` |
| Q `evaluate_ce/report.json` | `AEAB335DAFF99CEEBDA34805FF9AE66EA97B1A70574AD7EB74BB4FA23144BD34` |
| Q `evaluate_alm/report.json` | `4205F82430A7D50C47ABC90107A1BE96AB1C469467D06D8DC5295B28FF38CF18` |

### 23.5 재현 범위·미완 종결 원칙

소스 검색은 다음의 **명시된 허용 두 디렉터리**로 한정했다. 첫 검색에서 나온 출력 중 `trainer.py:719`는 위 optimizer fused이며 `test_p106b_native_weight_route.py`의 `above_four_hours`는 정규식 문자열의 우연한 일치다. 이 결과에 설치 상태나 전 저장소 부재 증명을 더하지 않는다.

```bash
rg -n -i --glob '*.py' 'cut_cross_entropy|linear_cross_entropy|liger|fused.{0,30}(cross.?entropy|ce\b)|normuon|adamuon|\bactd\b|dskdv2|ds-kd|dwa.?kd|\bdvlm\b|\bmntp\b|adaptive.?mask|seq_len_schedule|context_schedule|length_schedule' tinylm scripts
```

정확한 결론은 **기존 head 절약/일반 Muon/MTP/KD/GSQ 함수 보정은 이미 있고, ALM 핵심형의 실수·기존 삼진 실제 대조는 이제 닫혔으나, 첨부 최우선 fused와 나머지 요청 방법들의 최소 구현·실행은 그대로 남았다**는 것이다. 연구 문헌, 준비된 계획, 순수 CPU 계약, 교사 확률 저장, 학생 학습, 정상답변/최종 holdout은 서로 대체하지 않는다. 이 절만 갱신했으며 공유 계획·결과·기준표·레지스트리·런처와 동결 source는 총괄 소유로 유지한다. 실제 미완을 권한·시간 부족이나 방법 실패로 소급 정당화하거나 전체 요구 완료로 마감하지 않는다.

## 24. 내부 어휘타일 NLL 원형의 실행 전 정 검토

### 24.1 권한·버전·실행 상태

총괄 요청으로 [streaming_head.py](/home/uranus/tinyLM/tinylm/train/streaming_head.py), [GPU 진단 제어기](/home/uranus/tinyLM/scripts/diag_p102a_streaming_head.py), [순수 CPU 시험](/home/uranus/tinyLM/scripts/test_p102a_streaming_head.py), [런처](/home/uranus/tinyLM/run_P102A_Stage2bW_streaming_head_parity.sh)를 처음부터 끝까지 읽고, 재사용하는 PAD updater·엔진/허용차·[P102A Stage2bW 사전 설계](/home/uranus/tinyLM/test_plan/P102A_T1-S1-S2-S3-학습시간-기능계약.md:129)와 대조했다. **네 파일의 수정·실행, 모델/토크나이저/실자료/교사/GPU 로딩·시험·설치·Git은 정 담당이 수행하지 않았다.** 이 절만 추가했다. 총괄은 교사 단독 생산이 아직 진행 중이고 이 GPU 진단은 `NOT_RUN`임을 알렸다.

`exp-preflight`의 비교 축/단위/판정 경계를 적용했지만 레지스트리 도구의 전 로그/체크포인트 조회는 이번 source-only 권한에 맞춰 실행하지 않았다. 기준표의 표준조건/비교 유효성/기존 결과와 코드의 새 namespace·덮어쓰기 거부를 읽었으며, 이를 별도 기계 태그 검사 완료라고 보고하지 않는다. `log-to-result`의 CPU/실물·원형/해석 분리만 적용하고 공용 결과/계획/기준표 연쇄는 총괄에게 남긴다.

최초 전달의 CPU13/0.590초·source-only100파일·SH199 계약은 **총괄의 그 당시 회수**다. 감사 중 총괄이 아래 수리를 수행해 소스가 바뀌었고, 최종 회신은 **CPU18 통과**다. 정 담당은 최신18개 시험 함수를 소스에서 확인했으나 시험/원본 CPU 로그를 다시 실행·검산하지 않았다. 최초13개의 이전 source 영수증으로 최신 파일을 인증하지 않으며, 실행자는 최신 source-only SHA로 다시 입장해야 한다.

### 24.2 발견한 결함과 총괄 수리의 읽기 전용 재확인

| 등급·초기 결함 | 구체 근거와 최소 수리 | 최신 소스의 확인 상태 |
|---|---|---|
| **P1: 마지막 optimizer group의 강한 참조** | 최초 제어기123~124행의 `for group in ...param_groups`가 `run` 지역변수에 마지막 dict를 남겨 GPU parameter를 계속 소유했다. `del opts,model`/gc/cuBLAS 정리로는 그 parameter를 지우지 못하므로 첫 reference 뒤 strict allocated0에서 막히는 경로였다. | [fresh_optimizers](/home/uranus/tinyLM/scripts/diag_p102a_streaming_head.py:50)로 반복문을 별도 함수 스코프로 옮겼다. [팔 종료 weakref 검사](/home/uranus/tinyLM/scripts/diag_p102a_streaming_head.py:155)는 model와 모든 parameter가 소멸한 뒤에만 workspace를 지운다. [CPU 참조수명 fixture](/home/uranus/tinyLM/scripts/test_p102a_streaming_head.py:115)도 추가됐다. 소스상 수리 확인, 실제 GPU 해제는 미실행이다. |
| **P1: GPU 외부 조회/CPU 준비 뒤 CUDA 직전 시각 미검사** | 최초 `guard.check` 뒤 외부 `gpu_admission`·CPU 생성/strict load/fingerprint가 지연되면 deadline이 지났어도 `model.cuda()`를 부를 수 있었다. 조회 직후와 CUDA 직전 재검사가 최소 수리다. | [조회 직후 검사](/home/uranus/tinyLM/scripts/diag_p102a_streaming_head.py:130)와 [checked_cuda](/home/uranus/tinyLM/scripts/diag_p102a_streaming_head.py:60)가 들어갔다. [만료 시 CUDA 호출0 fixture](/home/uranus/tinyLM/scripts/test_p102a_streaming_head.py:132)를 읽었다. 소스상 수리 확인이다. |
| 양팔 공통 gradient 누락이 동등성 PASS가 되는 빈틈 | 기존 `tensor_table`은 양쪽 `None`이면 close=true다. 전157개 gradient를 주장하려면 양쪽 공통 누락도 거부해야 한다. | [제어기149행](/home/uranus/tinyLM/scripts/diag_p102a_streaming_head.py:149)에서 parameter157/non-None157/빈 none-list/gradient key157/값None0을 강제한다. 기존 비교기·허용차는 바꾸지 않았다. |
| cleanup/source·asset 재조회 예외가 최종 보고를 건너뛰는 보존 빈틈 | 최초 `finally`의 workspace 정리나 재해시가 예외를 내면 뒤의 journal close/report 저장이 실행되지 않을 수 있었다. | [최신 finally](/home/uranus/tinyLM/scripts/diag_p102a_streaming_head.py:185)는 각 오류를 모아 `ERROR_CLEANUP_OR_FINAL_AUDIT`/9로 보존하고 마지막 보고로 진행한다. 최종 활성 할당도0이 아니면 오류다. OS 강제종료·디스크 쓰기 자체 실패까지 폐쇄를 보장한다는 뜻은 아니다. |

최신 네 파일에서 위와 별개의 **추가 P1은 발견하지 못했다.** 이는 제한 수치 진단의 소스 검토 결론이지 실제 GPU 입장·동등성·실행 성공을 선승인한 결과가 아니다. 총괄 수리가 반영된 최신 source pin과 CPU 회수 후에만 총괄이 실행 여부를 결정한다.

### 24.3 수식·마스크·tied gradient·updater 재사용의 타당 범위

| 계약 | 소스에서 확인한 내용 | 남은 한계 |
|---|---|---|
| 어휘타일 NLL | [forward](/home/uranus/tinyLM/tinylm/train/streaming_head.py:15)는 tile4096마다 logit을 계산하고 running max/partition을 합쳐 `(max−target)+log(partition)`을 돌려준다. 큰 공통 logit offset에서 절대 LSE와 target의 뺄셈 소거를 줄이는 형태다. | 타일 내부 logits/exp·FP32 table gradient·BF16 cast는 여전히 존재한다. 전체 `N_valid×V` logits 상주를 피하는 원형이지 무임시버퍼·최소 peak 보증은 아니다. 큰 offset 입력 VJP는 소거에 민감하며 최신 fixture도 table VJP만 비교한다. |
| 임의 부호의 상류 기울기 | [backward](/home/uranus/tinyLM/tinylm/train/streaming_head.py:57)는 `delta=(softmax−onehot)×outer`를 계산한다. outer를 양수로 잘라내거나 scalar 평균으로 고정하지 않는다. CPU signed/nonlinear fixture와 [실제 ALM binary-KL VJP fixture](/home/uranus/tinyLM/scripts/test_p102a_streaming_head.py:165)가 있다. | `once_differentiable`의 **1차 미분 전용**이다. ALM의 1차 chain rule과 양립하는 설계지만 고차 미분/모든 극단값의 수치 동등성은 보장하지 않는다. |
| shift·ignore·유효 위치 | [target_nll](/home/uranus/tinyLM/tinylm/train/streaming_head.py:88)는 이미 shift된 y를 재shift하지 않고 -100 이외 위치를 gather한다. 제외 위치는 loss/hidden gradient0이며 빈 mask도 graph 연결을 유지한다. native token/turn mask는 기존 encode/pad 경로 소유다. | 원행의 지도 의미/정답성을 이 함수가 고치는 것이 아니다. V3 결함은 알려진 수치 통제로만 남긴다. |
| factorized tied 입력/출력 합 | 기존 `_emb_up_w()`·`_emb_w()`를 직접 사용해 `h→r→V`를 보존한다. 공유 table/projection의 출력 VJP와 원 backbone/input lookup VJP는 autograd가 같은 parameter에 더한다. 별도 weight 복제/untie를 하지 않는다. | storage-quantized embedding을 명시 거부하며 현재 FP32 tied table 예외를 유지한다. 향후 hard embedding/head·GSQ effective weight의 검증이 아니다. |
| FP32/BF16 계산 | autocast operand dtype을 기록해 backward 재계산에 쓰고 logp/partition은 FP32(합성 FP64만 예외)로 계산한다. projected gradient의 어휘별 부분합은 FP32로 더한 뒤 한 번 cast한다. | BF16 matmul 출력/미분 반올림·타일 환원 순서가 원 full linear와 다를 수 있다. 특히 Muon NS5가 차이를 증폭할 가능성은 실제 한 update로 판단해야 한다. CPU BF16 fixture의.02 허용치를 GPU의 엄격 문턱으로 옮기지 않는다. |
| 순서·분모·optimizer 한 update | [HeadCore](/home/uranus/tinyLM/scripts/diag_p102a_streaming_head.py:29)는 기존 pad/normalization을 그대로 쓰며 기존 [one_update](/home/uranus/tinyLM/scripts/diag_p101a_padding_gpu.py:435)를 호출한다. 모델→유효 head NLL 합→전체128행의 assistant target 분모→16micro backward→clip1→원 AdamW/Muon 한 update다. 두 팔 같은 CPU 초기 state의 strict reload·fresh 빈 optimizer·seed/RNG·all157 gradient/갱신 weight/state 비교다. | 실제 선택은 **epoch0 seed1337 shuffle의 첫128행**이며 파일상 순서 첫128행이라고 단정하지 않는다. 1×8×16×1024=131072 padded slot/update, 네 팔 합524288이며 실제 x/assistant targets와 다르다. 수렴 학습이 아니므로 pool≥2× 규칙의 예외가 사전 계획에 명시돼 있다. |
| 참조 팔의 재사용 | [alm.target_nll](/home/uranus/tinyLM/tinylm/train/alm.py:19)의 유효64행 chunk/head checkpoint가 참조다. 두 팔 CLA2·R1·backbone ckpt ON·MTP OFF·fixed1024·동일 parent/V3·같은 optimizer LR를 쓴다. 후보는 어휘 타일 재계산형 custom backward다. | 참조의 head checkpoint와 후보의 자체 backward 재계산은 바로 비교할 구현 차이다. checkpoint가 같다는 말로 head 구현까지 동일하다고 쓰지 않는다. 일반 trainer/ALM 기본 경로를 변경·채택한 것은 아니다. |

재사용 범위는 적절하다. 실제 NLL/gradient/한 update의 질문을 위해 새 loader·optimizer·training loop·tolerance를 복제하지 않았고, 소유 모델은 직렬 한 개다. parent SHA·tokenizer SHA·V3 report/shards의 전후 대조, source pin, source-only 검사, exact namespace 존재 거부, write-once/20MB guard, micro별 절대시간·wall 제한과 외부 timeout도 기존 계약에 연결돼 있다. 단, 보고 full-wall은 최초 source manifest/첫 GPU 입장 조회/런처 CPU 시험 뒤에 시작하므로 그 밖의 시간까지 포함한 생산 총시간으로 부르지 않는다. 절대시간 검사는 입장/마이크로 경계 검사이며 진행 중 CUDA kernel의 즉시 선점 종료를 보장하는 것은 아니다.

### 24.4 결과가 나와도 허용되는 주장과 아직 미실행인 것

| 결과 상태 | 허용하는 해석 | 허용하지 않는 해석 |
|---|---|---|
| 최신 CPU18 통과, 총괄 회신 | 작은 FP32/FP64·CPU BF16/마스크/tied 경로·signed/nonlinear/ALM VJP·수명/만료 입장의 합성 계약 통과 | 실제157 parameter GPU PASS, 큰 offset 입력 VJP 완전 일치, 일반 모든 dtype/모델의 동등성 |
| 두 정밀도 실제 동등성 통과 시0 | 이 부모·고정128행·두 정밀도/현재 tolerance 안에서 loss/norm/157 gradient/한 optimizer update/state 동등성 | 학습 수렴/정상 답변·공식 CCE/Liger kernel 재현·현재 ALM 학습기 채택·full KL/ACTD·미래248K 어휘 효과 |
| 유효 수치 음성8 | 같은 통제에서 기존 문턱을 넘는 차이를 실제 관측, production 미채택 | 데이터 학습 불가·교사/ALM 능력 실패·문턱 사후 완화·시간이 빨랐다는 이유로 채택 |
| 입장/실행/폐쇄 오류9 | 부분 증거를 보존한 실행 계약 오류 | 과학적 수치 음성이나 후보 알고리즘의 본질적 실패 |
| 한 update 시간·allocator peak | CPU gradient 복사·journal을 포함한 한 update 및 backbone/head/backward/optimizer의 **단일 쌍 기술 관측** | warmup/ABBA 정상상태 속도, 같은 품질 도달시간, 전체 GPU/RSS, optimizer-state 단독 메모리, 본학습 가속 배수 |

GPU 제어기의 objective는 `NLL.sum()/whole_target_count`인 **CE 대조**다. 비선형 ALM VJP는 최신 CPU fixture에만 있으며 실제 GPU에서 λ/τ를 건 ALM 전체 update·학습은 별도로 `NOT_RUN`이다. 따라서 이 진단을 마쳐도 §23의 공식 CCE/Liger 통합과 나머지 방법·최종 holdout 미완은 자동 해소되지 않는다. 다만 **“현재 내부 어휘타일/per-target NLL 원형이 없다”는 상태는 총괄의 이번 구현으로 바뀌었다.** 설치 없이 작성한 PyTorch 원형과 공식 융합 kernel을 분리한다.

### 24.5 최신 읽기 원형의 해시

감사 중 총괄이 수리한 최신 네 파일을 **14:34:51.174494 KST**에 다시 읽었고, 아래 SHA는 최초 결함 버전이 아닌 **수리본**이다. 실행 시 source SHA는 새로 닫힌 영수증과 일치해야 하며, 정 담당은 이 파일들을 고치지 않았다.

| 읽은 파일 | SHA256 |
|---|---|
| `tinylm/train/streaming_head.py` | `F7BEB3386E40C3A0064F83B6C2A48FBF4AE98C85B60D8D0D2A39F604C87DADF8` |
| `scripts/diag_p102a_streaming_head.py` | `9D4A529C92AF535DFBF3120C354CE32FCE478E534A82753BBFA6E4E9D6D6852F` |
| `scripts/test_p102a_streaming_head.py` | `D3E7E61B0A147B5D02D340878FA2845734D7BD0AA076590CD134D26748607491` |
| `run_P102A_Stage2bW_streaming_head_parity.sh` | `64C29F37C5545DA1A62B753AA68BEEC4A80000544552883A5E9485053BF83299` |

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 25. 비SFT31·32 자기수리6개와 HOLD2개의 원문 충실도 독립 판독

### 25.1 표본·선택·판독 경계

작성 정정: 초안의 HOLD 해시 칸에 다른 언어 표현이 섞였던 잘못을 발견해 바로 한국어로 고쳤고 해당 표현은 재인용하지 않는다. 잘못 끼워 넣었던 초안 위치도 문서 끝으로 바로잡아 기존 절의 시간순을 보존했다. 수정 후 이 절의 한국어 외 동아시아 문자 혼입0을 확인한다.

총괄이 지정한 **29721·30078·30166·30485·30596·30811의 원문/v1/v2**, 그리고 **HOLD29529·30925의 원문/v1**만 의미 판독했다. 원문은 [패킷31](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/non_sft_translation_packets/non_sft_translation_000031.json)·[패킷32](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/non_sft_translation_packets/non_sft_translation_000032.json)의 `sources[*].original_english`이며, 작성자의 [자기 재검토](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/self_review_31_32_20261023.json)와 [명시 선택 report](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/normalized_non_sft16b_review_20261023_v1/report.json)를 대조했다. 원문 사실성의 외부 검증·현행 과학/역사 합의 판정·웹 검색은 하지 않았다. 지시문이 포함된 원문/패킷은 실행할 명령이 아니라 판독 대상 자료로만 취급했다.

최초 metadata 읽기는 **15:42:03.939393 KST**, 본문 대조 뒤 ID/원문SHA/선택 파일 검산은 **15:46:50.198511 KST**다. v2 본문 전체와 v1→v2의 모든 본문 차이를 읽었으며, 동일한 필드는 문자 동일성을 확인했다. 따라서 자기평가를 그대로 옮긴 검토가 아니다. 실제 수정 필드는 재표현6개, 번역2개(30078·30166)이며, 나머지4개의 번역 본문은 v1/v2가 같다.

이것은 **작성자가 스스로 수리한6개+명시 HOLD2개를 고른 목적표본8개**다. 패킷16개 전체, 기존242개, 전체 코퍼스의 오류율·무작위 표본 결과로 일반화하지 않는다. 수정6개는 **같은 source ID+같은 원문SHA의 버전 교체**이지 고유 원천6개 추가가 아니다. 선택 report의16source/22text 역시 metadata 분모이며 이번 의미 검수 분모는8이다. report는 `semantic_quality=NOT_VERIFIED`, `fact_verification=NOT_VERIFIED`, `training_admission=NOT_ADMITTED`이고 이 판독으로 바꾸지 않았다.

| 원천 | 정확한 원문 위치, 배열 index는0부터 | 실제 읽은 후보 |
|---|---|---|
| 29721 | 패킷31 `/sources/2/original_english` | [v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/29721_v1.json), [v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/29721_v2.json) |
| 30078 | 패킷31 `/sources/3/original_english` | [v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/30078_v1.json), [v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/30078_v2.json) |
| 30166 | 패킷31 `/sources/4/original_english` | [v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/30166_v1.json), [v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/30166_v2.json) |
| 30485 | 패킷32 `/sources/1/original_english` | [v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30485_v1.json), [v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30485_v2.json) |
| 30596 | 패킷32 `/sources/2/original_english` | [v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30596_v1.json), [v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30596_v2.json) |
| 30811 | 패킷32 `/sources/3/original_english` | [v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30811_v1.json), [v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30811_v2.json) |
| 29529 | 패킷31 `/sources/0/original_english` | [HOLD v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/29529_v1.json) |
| 30925 | 패킷32 `/sources/6/original_english` | [HOLD v1](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30925_v1.json) |

### 25.2 수리6개 — 지적한 복원과 남은 의미 변화

#### 25.2.1 29721 — 직책·서지는 복원, 날짜 상한의 확정화는 잔류

- **원문 핵심:** 법안의 처리 과정, 초안/수정 주체, 처벌 상한, Taft의 발언 및 서지를 설명한다. 1942년2월22일은 Bendetsen이 초안을 보낸 시점의 **상한**(`By February 22`)이다. Bryan의 Alien Division/Provost Marshal General실 직책과 참고문헌 판본·쪽수도 명시된다.
- **v2 복원 관측:** `/ko_rephrase`의 Bryan 직책과113–114쪽·1993년 판68쪽·출판 정보/Archives 경로가 v1의 일반화된 문장 대신 실제로 들어갔다. `/ko_translation`은 v1과 동일하다. 5,000달러/5년 초안 대 최대1년 수정, 발의/심의/서명 날짜·시간, Taft 발언의 인물 귀속/평시 조건은 유지됐다.
- **잔여:** `/ko_rephrase` 둘째 문단은 여전히 **“그는 2월 22일 … 초안을 보냈다”**라고 써 상한을 정확한 발송일로 좁힌다. 번역 본문은 “2월22일까지”라 원문의 한정을 보존한다. **재표현의 날짜 한정 수리 필요**이며 최소 방향은 “2월22일까지는 … 초안을 보냈다”다. 원문에 없는 더 정확한 날짜를 사실로 보충하지 않는다.

#### 25.2.2 30078 — 제목/잔털 은유는 개선, p53 기능상실 조건은 재표현에서 누락

- **원문 핵심:** 2002년 연구 보도이며, 종양유전자 활성화→ROS/DNA 손상과 p53의 반응·상쇄 가능성을 다룬다. 중요한 조건은 **추가 돌연변이가 p53을 무력화하는 경우** 종양이 생길 수 있다는 것이다. 실험의 ROS2~3배, DNA 손상 약80% 감소, 감마선 뒤 분열 세포10배와 인간 암 절반 초과를 각각 다른 설명에 붙인다.
- **v2 복원 관측:** `/ko_translation` 제목에서 v1의 “구조 신호 분자” 결합을 풀고, 마지막 은유를 v1의 “근거 없는 촉수”에서 노년의 엉뚱하게 자라는 잔털로 고쳤다. 재표현에도 제목과 마지막 희망의 은유가 추가됐다. 위 수치, Wahl의 추측/DePinho의 평가,2002년 시점은 유지된다. 제목의 “구조 분자”는 한국어에서 구조적 분자라는 뜻으로도 읽힐 수 있어 “세포를 구하는 분자”처럼 뜻을 분명히 할 여지는 있다.
- **중요 잔여:** `/ko_rephrase` 둘째 문단은 **“p53에 추가 돌연변이가 생기면 … 종양이 생길 수 있다”**고 쓰며 **p53 기능을 무력화한다는 필수 조건**을 생략한다. 모든 추가 돌연변이가 같은 조건인 듯 범위를 넓힌다. 번역 본문에는 무력화 조건이 남아 있으므로 **재표현의 조건 누락**이다. 최소 방향은 “추가 돌연변이가 p53을 무력화하면 …”이며, 의학적 사실의 외부 확인이 아니라 원문 조건의 복원이다.

#### 25.2.3 30166 — 토지 보상·복장 제공은 복원, 이주·정치적 태도 주체 오류2곳 잔류

- **원문 핵심:** Owens의 전기다. 토지 보상은 기록에 나오는 동명 인물이라는 유보가 있고, 결혼 상대는 **De León 식민지로 재이주한 McMullen-McGloin 개척자의 의붓딸 Elizabeth**다. 분리독립 반대표를 던진 주체는 **Owens 개인**, 남부연합에 봉사한 주체는 **부부**다.
- **v2 복원 관측:** 두 본문에서 토지 보상을 청구권으로 좁히지 않고 `land bounty`를 병기했다. 중대에 “무장·지원”했다는 v1 번역을 **옷으로 중대 전체의 복장을 마련했다**로 고쳤다. 복무1837.2~1839.1, 혼인1844.4.8, 일수입 최대40달러, 철도1857~1861/파괴1862~1863, 은퇴1884/사망1890.8.2 및 페이지2010/2019/2020 날짜는 보존된다.
- **중요 잔여1:** `/ko_translation` 첫 문단의 **“그녀는 De León 식민지로 이주했다”**, `/ko_rephrase` 첫 문단의 **“의붓딸이자 De León 식민지로 옮긴 Elizabeth”**는 원문의 개척자에게 붙은 관계절을 Elizabeth의 이동으로 바꾼다. 두 본문 모두 주체 수리가 필요하다. 최소 방향은 “De León 식민지로 재이주한 … 개척자의 의붓딸 Elizabeth”처럼 관계절의 선행사를 유지하는 것이다.
- **중요 잔여2:** `/ko_rephrase` 셋째 문단의 **“분리독립에 반대한 Owens 부부”**는 Owens 개인의 반대/투표를 아내에게도 부여한다. 번역 본문은 Owens만 반대표를 던졌다고 올바르게 구분한다. 최소 방향은 “Owens는 분리독립에 반대표를 던졌지만, 그와 아내는 남부연합을 위해 일했다”다. 원문에 없는 아내의 견해를 추론하지 않는다.

#### 25.2.4 30485 — 해수면의 공간적 한정 복원 확인

- **원문 핵심:** 2019.6.11 보도자료가1986년의 조건부 예측과 당시 농도/향후 위험을 구분한다. 해수면은 **최악의 경우2100년까지 최대1m**, 다만 지역 차이가 클 수 있다는 한정이 붙는다.
- **v2 복원 관측:** `/ko_rephrase` 셋째 문단에 v1에서 빠진 지역별 차이와 독일 기상학자의 폭염 전망 주체가 들어갔다. 번역 본문은 원래부터 해당 한정을 포함해 v1과 동일하다. 연소 제한의 조건·50~100년/500~600ppm·2019년 당시400ppm 초과/30년 전340/1900년경270·최소80만 년·2010년194개국/2°C·최악의 경우 조건이 유지된다.
- **판독 한계:** 이 대조에서 추가 주요 의미 변질은 발견하지 못했다. 2019년 기사의 수치/전망 충실도에 한정하며 현재 수치·실현 여부·기후과학의 외부 합의를 검증한 결론이 아니다. “완전 무오류”나 정식 채택으로 승격하지 않는다.

#### 25.2.5 30596 — 진행 중 상태는 재표현에서 복원, 현장학습 가능 표현은 약화

- **원문 핵심:** 원문 당시 **진행 중인** 프로그램이 매년 Craven County 학교 절반에 도달하도록 설계됐다는 설명이다. 교실 수업 후 현장학습을 **갈 수 있다**는 선택/가능 표현과,8학년·매시간/24시간·주7일 자료·시료 항목/잠재적 유해성이 있다.
- **v2 복원 관측:** `/ko_rephrase` 첫 문단의 v1 “계속 운영할 계획”이 **원문 작성 당시 진행 중인 프로그램**으로 바뀌어 상태가 복원됐다. 매년 학교 절반은 달성 실적이 아닌 설계 범위로 유지된다. 도구/측정·시료 항목 및 잠재적 위해도 보존됐다. 번역 본문은 v1과 같고 “지속 운영되게 설계”라 상태가 덜 명료하지만, 재표현처럼 미래 계획으로 새로 단정하지는 않는다.
- **잔여 주의:** `/ko_rephrase` 둘째 문단의 **“학생은 … 견학하고 … 탑승한다”**는 원문의 `can take a field trip`보다 가능/선택 한정이 약하다. 프로그램 일정의 일반 묘사로도 읽히므로 위30166/30078과 같은 수준의 명백한 주체/조건 역전으로 세지는 않는다. 다만 약속된 모든 학생의 필수 활동으로 읽힐 여지를 막으려면 “현장학습을 갈 수 있다”를 유지하는 편이 충실하다. 현재 운영 여부는 원문/별도 시점 주석 모두 확정하지 않는다.

#### 25.2.6 30811 — 노벨상 귀속의 원문 강도 복원 확인, 사실 인정과 구분

- **원문 핵심:** 2018.1.6 기사는 저차원 실험/4차원 물리의 효과·그림자 비유를 설명하고, 특정 계산이2016년 노벨 물리학상을 받았다는 강한 서술을 한다. 실제4차원 공간계를 갖고 있지 않음/직접 접근 불가와 가능·추측 표현도 함께 있다.
- **v2 복원 관측:** `/ko_rephrase` 셋째 문단의 v1 “노벨상과 연결된 계산”을 **기사가 상을 받은 계산이라고 말한다**는 형태로 바꾸어 원문의 귀속/강도를 복원했다. 번역 본문은 v1부터 해당 강도를 보존해 변경되지 않았다. 저차원 구조·미국/유럽 실험의 구분, 직접 접근 불가, 전망, 인용자와2018년 시점도 유지된다.
- **판독 한계:** 추가 주요 의미 변질은 발견하지 못했다. 이는 원문의 강한 주장을 **기사의 주장으로 충실하게 전했다**는 뜻이지 계산/노벨상 귀속이나4차원 존재를 독립 사실로 승인한 것이 아니다. 사실이 이상해 보인다는 이유로 번역에서 몰래 약화하거나 반대로 원문 밖의 사실로 확정하지 않는다.

### 25.3 HOLD2개 — 원문 근거와 빈 본문 일치

| 원천 | 실제 원문에서 확인한 근거 | 후보와 대조한 결과·한계 |
|---|---|---|
| 29529 | 냉방 원리 설명 뒤 특정 업체 기술자 소개, Southwest Florida 지역 고객 대상 전화·웹사이트와 연락 권유가 붙는다. | `decision=HOLD`, 번역/재표현 **각0문자**, preserved_terms 빈 배열이다. 광고 문맥을 숨긴 교육용 번역을 만들어 넣지 않았고 reason의 상업 홍보 근거가 실제 원문과 맞는다. 앞부분의 물리 설명이 모두 거짓이라는 판정이나 광고를 제거한 새 텍스트의 승인으로 확대하지 않는다. |
| 30925 | 지형 모형/영상 과제 자체는 있으나 특별 제안의 구체 내용·조건이 없고, 영상 제출 주소가 일반 자리표시자다. | `decision=HOLD`, 번역/재표현 **각0문자**, preserved_terms 빈 배열이다. 없는 혜택·실제 연락처를 발명하지 않았고 운영 안내의 결손이라는 reason은 이 원문 조각에 근거한다. 지질 교육 내용 전체가 불가능하거나 원기관 서비스가 현재 없다는 판정은 아니다. |

### 25.4 원형·선택 계보 검산

8개 모두 packet의 `source_sha256`이 실제 `original_english` UTF-8 SHA와 일치했고, report의 source object가 해당 packet source object와 같았다. 선택 후보의 ID/원문SHA·실제 파일SHA·본문 object가 report와 일치했다. 자기 재검토 ledger의 ID/원문SHA와도 같고, 모든 후보/선택은 `NOT_ADMITTED`다. 이 검산은 내용의 사실성이나 번역 무오류를 증명하지 않는다.

| 고정 입력 | 실제 SHA256 |
|---|---|
| 패킷31 | `0625400ED7DE66EBF719DEE4C02C703CF392D1701D7E3985B8E3DC1AC8D90F7B` |
| 패킷32 | `28FD9D2523FA2F975C934E2D1EBE9C4F8BCC259B8A0D20C43DE2DDCBA23A9364` |
| 자기 재검토 ledger | `B7EA9B76A9FEAB00FF1426A0D4600215114923FAFA893B07CC2F826E7BC580C1` |
| 명시 선택 report | `6114DB179516F877125E26543ABB8C9CC4CB0EA086C3DF999484F014CA00B5A9` |

| 원천 | 실제 읽은 v1 파일SHA256 | 실제 선택 v2 파일SHA256, HOLD는v1 |
|---|---|---|
| 29721 | `62D372020986ED16F0BB4006E2AD812D4D33A5CBD834B6E973074ED417D608D1` | `8884C8E34AAE4A5F52A7D8A7412CC0B8E2B7C0918543B7DB3CFF879137FBF810` |
| 30078 | `E3146D5093D9B825AB58BAA95B65F543228FA76E85338CC4016103926D63D06D` | `D099C315B53293558875F3B514D09071529FBD2B962244BDCB4B7BAC654ED1A8` |
| 30166 | `B9D53277A40A1A4289DA19CF036F0CC8337EB2518C57B4A8DE7F374B760E7A58` | `F641CE41BB89A88E03F584F2384FBA05D1A6C7D0801A1300EE94EB4129E24D79` |
| 30485 | `AF6EED363D1B9D266FBD6BBE67B53CDA14B005A2C4FF0C5BB38D45B2E3A3AF29` | `D3EE8F27E8BC4AEC8AFF9F441CA67DD4B7B99888E4CA022836F00851C07A52C7` |
| 30596 | `78FC9F58A4033D0C34766E5C75AAC4534B2207934176C9BD548A0FD0520E58B1` | `ABEAF227BB840A89D77F507C6971CCD30E128C17FE005C91F5AA45CDF5642203` |
| 30811 | `F4AF50E9CCEDDD4F0AD483D2939438812D43A8A5DD75614D8448440D7C3AD2E4` | `58FBB0EC7EEC8B06BDB39C8162B370568BFA2E57E845F17F1D1B494D6FD60310` |
| 29529 | `D9C36CF623F84F89503EAE1DF1EF10C512DE7A1E85701C1F4FA3410D955ADAE7` | 같은v1 |
| 30925 | `3D582386E57C1BAE9532639A44A11E4FE8ED61CEDCD93394352657FFD9D2697D` | 같은v1 |

### 25.5 v2 선택본 기준 총괄용 결론

**자기수리6개의 지적 대상 변경은 실제로 존재하지만, 그 사실만으로6개 모두 의미 보존 완료라고 마감할 수 없다.** 우선 남은 것은30166의 두 주체 오류와30078 재표현의 기능상실 조건 누락이다. 29721의 날짜 상한을 정확일로 바꾼 표현도 복원할 필요가 있고,30596의 현장학습 가능 표현은 수리 권고로 남긴다. 30485·30811에서는 지정된 원문/두 버전 대조 범위에서 추가 주요 변질을 발견하지 못했으며, HOLD2개는 원문 근거와 빈 본문이 일치했다.

이 결론은 source/candidate를 수정하거나 HOLD/채택 상태를 바꾼 것이 아니다. 총괄/작성자가 후속 버전을 만들 경우 지금 v1/v2 음성을 보존하고 ID+원문SHA를 그대로 연결해 변경 위치를 재대조해야 한다. 이번8개를 전체242개/전체 코퍼스 오류율이나 최종 품질로 환산하지 않으며, 수정6개를 새로운 고유 원천으로 더하지 않는다. 코드·모델·GPU·공용 자료·후보·게시/API는 모두 변경/실행0이다.

### 25.6 v3 후속 확인 — 두 원천의 지적 의미 범위만, 선택본 교체 아님

총괄의 추가 읽기 승인 뒤 **15:51:41.276772 KST**에 새 [30078_v3](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/30078_v3.json), [30166_v3](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/30166_v3.json)와 별도 [잔여 수리 장부](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/self_review_31_32_residual_corrections_20261023.json)를 읽었다. 위25.2/25.5의 **v2에서 실제 발견한 내용은 그대로 남긴다.** 이번 후속은 두 원천의 지적된 의미 범위만의 독립 대조이며 v3 전체·원래16개·242개의 의미 PASS가 아니다.

| 원천·범위 | 실제 v3에서 읽은 변화 | 좁은 후속 판독 |
|---|---|---|
| 30166, 이주 주체 | 번역/재표현 모두 De León으로 이주한 관계절을 McMullen-McGloin 개척자에게 붙이고 Elizabeth는 그 의붓딸로 둔다. v2의 별도 “그녀는 … 이주했다”가 없어졌다. | 지적한 **이주 주체 변질은 해당 범위에서 해소**됐다. |
| 30166, 반대표 대 복무 주체 | 재표현 셋째 문단은 Owens 개인이 반대표를 던졌다고 한 뒤, 그와 아내가 남부연합을 위해 일한 것으로 구분한다. | 지적한 **아내의 정치적 견해 추가는 해당 범위에서 해소**됐다. |
| 30078, p53 기능상실 조건 | 번역은 v2와 같고, 재표현 둘째 문단은 추가 돌연변이가 **p53을 무력화하면** 종양이 생길 수 있다고 고쳤다. 절반 초과는 이러한 p53 무력화가 인간 암에서 차지하는 범위로 따로 명시한다. | 지적한 **조건 누락·범위 혼동은 해당 범위에서 해소**됐다. 모든 돌연변이 일반으로 읽히던 v2보다 원문 조건이 명확하다. |

두 v3의 source ID/원문SHA는 각각 v2·원패킷과 같고 `DRAFT_TRANSLATED`/`NOT_ADMITTED`/`NOT_VERIFIED`다. 장부도 신규 원천0, 자기 재검토만 수행했다고 명시한다. **현재 고정 정규화16b report와 최초 자기검토 장부는 여전히 v2를 가리킨다.** v3가 존재한다고 선택본이 자동 갱신되거나 v2 음성이 사라지지 않으며, 정 담당은 후보·장부·정규화본 어느 것도 바꾸지 않았다. 29721의 날짜 한정과30596의 가능 표현 등 위 다른 범위도 이번 v3 후속으로 해결됐다고 하지 않는다.

| 후속 원형 | 실제 SHA256 |
|---|---|
| `30078_v3.json` | `1A30FCDE91EF4F71498131803287C181AA7CA17E5BFF615E10408E2E29E85A7E` |
| `30166_v3.json` | `FBAF70F9BA90A332DEC229B4CE0CB0A5AF6ECEC2548F6521F688B7844FE00292` |
| 잔여 수리 장부 | `D1A3EB23E05D396D389556B80E80892CFC8A16B9469FFA43BE1A78C57B1454CA` |

## 26. 29721·30596 v3의 두 한정 복원과 변경 범위 독립 확인

### 26.1 이번에 실제 읽은 범위

총괄의 파일 생성 통지를 받은 뒤 **16:42:26.913929~16:42:26.914753 KST**에 패킷31의 `/sources/2/original_english`(29721), 패킷32의 `/sources/2/original_english`(30596), 각 v2/v3를 직접 읽었다. 이어 **16:43:18.342665 KST**에 전체 JSON 필드 차이와 재표현의 변경 범위를 다시 대조했다. 작성자 회신을 그대로 통과로 옮기지 않았다. 이번 목적은 날짜 상한/현장학습 가능 표현의 복원과 비의도 변경 여부뿐이다. 원형 읽기·필드/해시 대조에만 Python 표준 라이브러리를 썼고, 원문 사실성·현재 운영·법률의 외부 검증·웹 탐색·프로젝트 프로그램/모델/GPU 실행은 하지 않았다.

정확한 입력은 [패킷31](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/non_sft_translation_packets/non_sft_translation_000031.json)·[29721_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/29721_v2.json)·[29721_v3](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000031/29721_v3.json), [패킷32](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/non_sft_translation_packets/non_sft_translation_000032.json)·[30596_v2](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30596_v2.json)·[30596_v3](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/scratch/non_sft_translation_v1/non_sft_translation_000032/30596_v3.json)다. 원문 UTF-8 SHA는 각 후보의 source ID/SHA와 같고, 패킷/기존v2 파일SHA도 §25의 원형과 일치했다.

### 26.2 두 한정의 판독과 다른 본문 변화

| 원천·정확 위치 | 원문·v2의 차이 | v3의 실제 변경과 독립 판독 |
|---|---|---|
| 29721 `/ko_rephrase` 둘째 문단 | 원문은 초안을 **2월22일까지** 보냈다고 하며 정확한 발송일을 확정하지 않는다. v2는 **2월22일**이라고 좁혔다. | v3는 “그는 2월22일까지 … 안을 보냈다”로 바뀌었다. 재표현 전체가 **해당 한 곳의 날짜 표현만 교체한 문자열과 정확히 같다.** 날짜 상한은 이 범위에서 복원됐고, 다른 재표현 문장/서지/수치는 변경되지 않았다. |
| 30596 `/ko_rephrase` 둘째 문단 첫 두 문장 | 원문은 수업 후 현장학습을 **할 수 있다**고 하며, 참여할 때의 시설 방문/연구선 이동을 설명한다. v2의 단정형 견학·탑승은 그 가능 한정이 약했다. | v3는 “현장 학습을 할 수 있다” 뒤 **“그 현장 학습에서는”**으로 연구선·상류 측정소 방문을 연결한다. 참여 가능성과 그 일정 안의 활동을 구분해 해당 한정을 복원했다. New Bern 시설의 원어 고유명과 Mills Branch 측정소의 CAAE 소유도 함께 명시됐으나 모두 원문에 있어 새 사실의 추가는 아니다. |

30596의 첫 문단/마지막 문단은 v2와 같고, 둘째 문단에서도 **“CAAE가 운영하는 …” 이후 측정소·자료·도구 설명은 문자 그대로 같다.** 현재 운영이나 모든 학생의 실제 참여로 확장한 변화는 위 변경 범위에서 발견하지 못했다. 두 원천의 `/ko_translation`은 v2/v3가 완전히 같으며, 원래 번역에 있던 날짜 상한/현장학습 가능 표현도 그대로다. **대조한 본문 차이에서 비의도 의미 변경은 발견하지 못했다**는 좁은 결론이지 각 글 전체의 무오류 인증은 아니다.

### 26.3 실제 변경 필드 — 본문만 바뀐 것과 전체 JSON을 구분

| 원천 | JSON 값이 실제 달라진 필드 전부 | 해석 |
|---|---|---|
| 29721 | `ko_rephrase`, `reason_ko` | 재표현의 날짜 한정 수정과 그 수정 이유의 기록이다. `temporal_scope_note`는 같다. |
| 30596 | `ko_rephrase`, `reason_ko`, `temporal_scope_note` | 재표현의 현장학습 가능 한정 수정, 이유, 실제 참여/현재 운영을 단정하지 않는 시점 주석의 보완이다. |

따라서 **“본문 수정은 ko_rephrase만”은 맞지만 “다른 JSON 필드까지 모두 불변”은 아니다.** 위 메타데이터 변화는 해당 수정의 설명으로 일치하며 source/결정/채택 상태를 바꾸지 않는다. 양쪽 모두 `schema`, `source_id`, `source_sha256`, `decision`, `preserved_terms`, `ko_translation`, `training_admission`, `fact_verification`이 같고 필드 집합도 같다. 두 v3는 계속 `DRAFT_TRANSLATED`/`NOT_ADMITTED`/`NOT_VERIFIED`다.

### 26.4 읽은 원형과 종결 범위

| 원천 | 원문 UTF-8 SHA256 | v2 파일SHA256 | v3 파일SHA256 |
|---|---|---|---|
| 29721 | `0417B81520E09197B9ADF78055A64D919CFAFD2759C6353CC584398BDE505F5E` | `8884C8E34AAE4A5F52A7D8A7412CC0B8E2B7C0918543B7DB3CFF879137FBF810` | `B67EEB347EB1E46B66C7EFAEC715F36EF15A68F289DBC1E92BD3636404FA66DF` |
| 30596 | `FB5F10753B55352E96F921A769BF35BB42ADC00BA86E9F852E7BD2B45B16118E` | `ABEAF227BB840A89D77F507C6971CCD30E128C17FE005C91F5AA45CDF5642203` | `FCD09494E0A3C9EC65181E26B391C791385F68CE280BEE7FB6CE7C24FEDF727F` |

**두 지적 한정은 새 v3의 해당 의미 범위에서 복원됐다.** §25의 당시 v2 음성/주의는 손대지 않고 이 후속 사실을 별도로 남긴다. 다른 원천·기존16개/242개 전체의 의미 PASS·최종 품질·사실성으로 일반화하지 않는다. 같은 ID+원문SHA의 버전이므로 **새 고유 원천은0**이다. 이번에는 선택/정규화본을 다시 읽거나 바꾸지 않았으므로 v3의 존재를 그 선택본의 자동 갱신으로 보고하지 않는다. 후보·코드·GPU·공용자료·기존 절은 변경0이며, 이번 소유 문서에는 §26만 추가했다.
