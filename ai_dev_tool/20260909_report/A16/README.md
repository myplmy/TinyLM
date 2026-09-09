# A16 사용 안내 — 기존 경로 보존 + 참조 평가 경로

먼저 [분석보고서](분석보고서.md)를 읽는다. **코드와 아래 명령은 작성만 했으며 실행하지 않았다.** A16 자체의 테스트·import·모델 추론 통과 기록은 없다. 다른 A 패키지나 ALL에 합친 상태도 아니다.

## 1. 복사할 것

replacement/ 안의 **tinylm과 scripts 두 폴더를 Z:\TinyLM 아래 같은 이름의 폴더에 병합 복사**한다. 프로젝트의 tinylm 폴더 전체를 지우거나 빈 폴더로 바꾸는 방식이 아니다. 모두 새 경로이며 기존 eval_bench_suite.py / eval_korean_bench.py / fetch_bench_data.py는 교체하지 않는다.

~~~
A16/
  분석보고서.md
  README.md
  VERIFICATION.md
  manifest.json
  DATA_AUDIT.json
  CHECK_PACKAGE.ps1
  dependencies/
    requirements-reference.txt
  replacement/
    scripts/
      eval_reference_bench.py
      compare_reference_bench.py
      eval_reference_code.py
      eval_reference_korean.py
      serve_reference_bfcl.py
      eval_reference_bfcl.py
      tests/
        test_a16_reference_protocol.py
        test_a16_harness_contract.py
    tinylm/eval/reference_bench/
      __init__.py
      artifacts.py
      engine.py
      lm_adapter.py
      harness_run.py
      legacy_compare.py
      code_bench.py
      korean_bench.py
      bfcl_server.py
      bfcl_bridge.py
      legacy_sources/
        eval_bench_suite.py
        eval_korean_bench.py
~~~

legacy_sources의 두 원본 복사본은 해시로 잠근다. 새 helper는 그 복사본의 경로 상수만 **실행 중** 현재 프로젝트로 지정한다. 원본 파일 내용은 변경하지 않는다.

CHECK_PACKAGE.ps1은 파일 해시·기존 원본 기준 해시·새 설치 경로 충돌만 읽어 검사하는 **사용자용** 도구다. 이번 세션에서 실행하지 않았다. 검사에 성공해도 Python 구문·의존성·실행 결과 검증은 아니다.

## 2. 별도 환경과 의존성

기존 학습 환경의 torch를 일괄 업그레이드하지 않는다. 사용자가 선택한 별도 평가 환경에서 준비한다.

| 경로 | 외부 선행조건 |
|---|---|
| 일반 harness | Python 3.10 이상, 현재 TinyLM과 호환되는 torch/tokenizers/transformers, **lm_eval==0.4.13**, 각 task가 요구하는 extras/data |
| IFEval | harness IFEval task의 NLP 의존성과 필요한 언어 리소스. 미설치하면 해당 오류를 해결한 뒤 새 출력 폴더로 재시도 |
| HumanEval | **OpenAI 공식 human-eval 저장소의 로컬 checkout** 설치. 동명의 비공식 배포본으로 자동 대체하지 않음 |
| HumanEval+ | **evalplus==0.3.1**의 평가 의존성. 모델 backend는 TinyLM이 담당 |
| BFCL | **Gorilla v1.3 / BFCL v3**의 검토한 로컬 checkout과 해당 의존성. 최신 main으로 묵시 변경 금지 |
| KorQuAD | 공식 **evaluate-v1.0.py** 파일 및 그 SHA-256. 로컬 evaluate-2.0.py는 사용 불가 |

일반 harness와 EvalPlus만의 pin 파일은 dependencies/requirements-reference.txt다. HumanEval/BFCL은 사용자가 준비한 공식 checkout을 editable install하는 방식이다. BFCL의 전체 dependency 설치가 무겁거나 충돌하면 **모델 서버 환경과 BFCL 환경을 분리**할 수 있다.

설치 예시도 **사용자 실행용**이다.

~~~powershell
python -m pip install -r Z:\TinyLM\ai_dev_tool\20260909_report\A16\dependencies\requirements-reference.txt
python -m pip install -e C:\bench_sources\human-eval
python -m pip install -e C:\bench_sources\gorilla-v1.3\berkeley-function-call-leaderboard
~~~

위 C:\bench_sources 경로는 **예시이며 현재 존재를 확인한 경로가 아니다.** 공식 source 릴리스·commit·패키지 버전을 사용자 실행 결과에 함께 남긴다. v1.3 BFCL checkout에 대한 이 wrapper의 호환 실행은 미검증이다. API가 다른 경우 오류를 숨기지 않고 중단한다.

HF task 데이터는 기존 평탄화 JSONL만으로 모두 대체하지 않는다. few-shot dev/train, 수정 정답, 원래 task schema를 upstream이 선택하기 때문이다. 필요한 데이터를 준비한 뒤 아래처럼 offline을 선언하면 실행 중 부족한 캐시는 오류로 남는다. 이미 설치한 데이터의 현재 revision도 결과의 source/sample hashes와 함께 보존한다.

~~~powershell
$env:PYTHONIOENCODING = 'utf-8'
$env:HF_HUB_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:WANDB_MODE = 'disabled'
~~~

새 진입점은 tinylm import를 통해 기존 HF cache 규약을 적용한다. 일반 task 결과를 HF Hub/W&B에 자동 게시하지 않는다. BFCL endpoint는 127.0.0.1에만 바인딩한다.

## 3. 검사와 공통 변수

다음 checkpoint 파일의 존재는 이번에 파일 목록으로 확인했다. **가중치를 열거나 실행하지는 않았다.** best와 last는 다른 비교이므로 먼저 하나를 고정한다.

~~~powershell
Set-Location Z:\TinyLM
$Checkpoint = 'Z:\TinyLM\runs\ckpt\m100s8_ko-en_300M_d12_cla2_norecur.pt'
$Out = 'Z:\TinyLM\ai_dev_tool\20260909_report\A16\user_runs'
python scripts\tests\test_a16_reference_protocol.py
python scripts\tests\test_a16_harness_contract.py
~~~

첫 테스트는 알려진 확률의 CPU 모형으로 LL 합·EOS·길이 중단을 검사하고, macro F1/accuracy 차이·ID 대응·결과 덮어쓰기 방지를 확인한다. 두 번째는 upstream TemplateLM의 공백 경계, rolling token coverage, 미지원 옵션 거부를 확인한다. **통과했다고 가정하지 않는다.**

--device cpu / --dtype float32가 기본이다. 아래 CUDA BF16 예시는 사용자 장비에서 순차 실행할 때의 선택이다. 비교 모델 양쪽에 dtype을 일치시킨다. 기존 평가기는 CUDA에서 BF16 autocast를 쓰므로 legacy 대조에도 그 차이가 남는지 기록한다.

출력 폴더는 매 실행 새 이름이어야 한다. 기존 폴더가 있으면 덮어쓰지 않고 실패한다. --limit은 **하위 task마다 적용되는 smoke 전용**이며 생략하면 full split이다. 예를 들어 MMLU --limit 2는 전체 2문항이 아니라 각 과목 2문항이다.

## 4. 일반 벤치마크 R 경로

먼저 2문항 smoke를 통과시킨 후 별도 폴더로 전량 실행한다.

~~~powershell
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --tasks hellaswag --shots 0 --limit 2 --device cuda --dtype bfloat16 --output "$Out\R_hellaswag_smoke"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile core --shots 0 --device cuda --dtype bfloat16 --output "$Out\R_core_0shot"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile korean --shots 0 --device cuda --dtype bfloat16 --output "$Out\R_kobest_0shot"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --tasks mmlu mmlu_redux --shots 0 --device cuda --dtype bfloat16 --output "$Out\R_knowledge_0shot"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --tasks mmlu --shots 5 --device cuda --dtype bfloat16 --output "$Out\R_mmlu_5shot"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile lambada --shots 0 --device cuda --dtype bfloat16 --output "$Out\R_lambada"
~~~

core는 HellaSwag·PIQA·WinoGrande·ARC-Easy·ARC-Challenge·BoolQ다. korean은 KoBEST 두 과제다. 결과의 acc, acc_norm, f1 등 **원래 metric 이름을 그대로 읽고 서로 대체하지 않는다.** KoBEST F1은 utils의 macro reducer이며 단순 accuracy와 별도다.

LAMBADA는 lambada_openai이다. MMLU는 0-shot/5-shot을 분리한다. MuSR은 leaderboard_musr 그룹의 세 하위 과제이며 **논문 CoT 재현 경로라고 부르지 않는다**.

### 4.1 생성·장문 과제

아래 기본 task generation 설정이 모델 window보다 크면 오류가 나는 것이 정상이다. 무조건 budget을 줄여놓고 같은 benchmark라고 기록하지 않는다. --generation-budget은 **명시적인 프로토콜 변경**이며 output/invocation에도 남는다.

~~~powershell
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile gsm8k --limit 2 --device cuda --dtype bfloat16 --output "$Out\R_gsm8k_default_smoke"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile ifeval --limit 2 --device cuda --dtype bfloat16 --output "$Out\R_ifeval_default_smoke"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile musr --limit 2 --device cuda --dtype bfloat16 --output "$Out\R_musr_fullinput_smoke"
~~~

GSM8K task 기본은 5-shot이다. 1,024 window에 few-shot 입력을 못 담을 때의 **별도 0-shot/256-token/left-truncated 팔** 예시는 다음과 같다.

~~~powershell
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile gsm8k --shots 0 --generation-budget 256 --overflow left --device cuda --dtype bfloat16 --output "$Out\R_gsm8k_0shot_256_left"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile ifeval --generation-budget 256 --overflow left --device cuda --dtype bfloat16 --output "$Out\R_ifeval_256_left"
python scripts\eval_reference_bench.py --checkpoint $Checkpoint --profile musr --shots 0 --overflow left --device cuda --dtype bfloat16 --output "$Out\R_musr_0shot_left"
~~~

이 값은 **해당 제한을 명시한 점수**다. 원문 전부를 읽은 장문 모델의 점수와 동일 설정이라고 부를 수 없다. max-length는 checkpoint의 max_seq_len 이하만 허용한다. --kv-cache는 별도 수치 검증 후 사용하는 선택사항이다.

### 4.2 외부 HF 모델도 같은 R로 측정

--hf-model에는 다운로드된 **로컬 HF 모델 디렉터리**를 지정한다. 별도 프로세스로 실행한다.

~~~powershell
$HfModel = 'C:\bench_models\local-reference-model'
python scripts\eval_reference_bench.py --hf-model $HfModel --profile core --shots 0 --device cuda --dtype bfloat16 --output "$Out\R_external_core"
~~~

예시 $HfModel은 현재 존재를 확인하지 않았다. upstream HFLM을 쓰며 chat template은 자동 적용하지 않는다. HFLM의 context 처리와 TinyLM의 error/left 조건 차이를 확인한다. 동일한 raw 문항·task·few-shot에 각 모델 고유 tokenizer를 쓰는 것이 기본 비교다.

## 5. 기존 L과 R을 같은 문항으로 비교

기존 명령은 그대로 남아 있다. 아래 새 비교기는 **R에서 실제 사용한 문항**을 로컬 기존 캐시와 내용 hash로 대응시키고 frozen 기존 평가 함수를 실행한다.

~~~powershell
python scripts\compare_reference_bench.py --checkpoint $Checkpoint --reference-run "$Out\R_core_0shot" --reference-task hellaswag --task hellaswag --metric acc --device cuda --dtype bfloat16 --output "$Out\L_vs_R_hellaswag"
python scripts\compare_reference_bench.py --checkpoint $Checkpoint --reference-run "$Out\R_lambada" --reference-task lambada_openai --task lambada --metric acc --device cuda --dtype bfloat16 --output "$Out\L_vs_R_lambada"
~~~

MMLU/Redux/MuSR는 **results에 기록된 leaf task 이름**을 --reference-task로 지정한다. group 전체를 한 파일처럼 지정하지 않는다. MuSR 로컬에는 murder_mysteries만 있으므로 나머지 두 task는 기존 경로와 1:1 대조 대상이 아니다.

--metric 기본은 acc다. KoBEST에서 f1만 기록되는 task라면 --metric f1을 사용하며, 문항별 (gold,prediction) 쌍의 일치 여부로 paired correctness를 계산한다. **aggregate macro F1은 R results.json의 값을 읽는다.**

동일 내용 중복으로 매칭이 모호하면 중단한다. 필요한 경우 --id-map JSON을 제공한다. 형식은 {"reference_doc_id": 기존캐시의0기반행번호}이며 내용이 다른 문항을 강제로 연결할 수 없다. 정답을 join key에서 제외하므로 Redux 라벨 교정은 따로 기록된다.

주요 결과는 paired_items.jsonl과 comparison.json이다. legacy skip은 None으로 보존하고 **같은 문항의 유효 쌍만** 비교한다. 모든 skip을 제거한 분모와 full benchmark 분모를 섞지 않는다. L−R에는 prompt·정규화·tokenization 등의 차이가 함께 포함되며 PMI 단독 효과가 아니다.

### 5.1 GSM8K·IFEval 채점기만 비교하는 S 팔

~~~powershell
python scripts\compare_reference_bench.py --checkpoint $Checkpoint --reference-run "$Out\R_gsm8k_0shot_256_left" --reference-task gsm8k --task gsm8k --metric exact_match --filter strict-match --scoring-only --device cpu --output "$Out\S_gsm8k_strict_vs_old"
python scripts\compare_reference_bench.py --checkpoint $Checkpoint --reference-run "$Out\R_ifeval_256_left" --reference-task ifeval --task ifeval --scoring-only --device cpu --output "$Out\S_ifeval_official_vs_old"
~~~

filter 명칭은 실제 samples의 filter와 맞춘다. GSM8K는 flexible-extract도 별도 폴더로 비교할 수 있다. --scoring-only를 빼면 기존 생성까지 다시 실행하며 --legacy-max-new로 과거 실험값(128/192 등)을 명시한다. IFEval의 기존 부분 instruction accuracy는 공식 네 지표와 분모가 다르므로 Δaccuracy 하나로 합치지 않는다.

## 6. HumanEval·HumanEval+

### 6.1 생성만 수행

~~~powershell
python scripts\eval_reference_code.py generate --suite human-eval --checkpoint $Checkpoint --max-new 512 --device cuda --dtype bfloat16 --output "$Out\R_humaneval_gen"
python scripts\eval_reference_code.py generate --suite human-eval --checkpoint $Checkpoint --legacy-generation --max-new 192 --device cuda --dtype bfloat16 --output "$Out\C_humaneval_old_gen"
python scripts\eval_reference_code.py generate --suite evalplus --checkpoint $Checkpoint --max-new 512 --device cuda --dtype bfloat16 --output "$Out\R_humanevalplus_gen"
~~~

164문항 각각 1개 greedy completion을 생성한다. 구형 생성 경로도 공식 ID와 새 run 파일로 저장한다. 문법 진단은 generation.jsonl, 공식 입력은 samples.jsonl이다. 같은 출력의 syntax rate와 기능 pass@1을 비교할 수 있다.

### 6.2 사용자의 별도 기능 검사 단계

**이 단계는 생성한 Python 코드를 실제 실행한다.** 공식 도구가 요구하는 별도 Linux/WSL 평가 환경에서 실행한다. GPU는 필요 없다. 이 안내를 현재 세션에서 실행한 것으로 읽지 않는다.

~~~powershell
python scripts\eval_reference_code.py evaluate --run "$Out\R_humaneval_gen" --workers 2 --timeout 3 --execute-generated-code --output "$Out\R_humaneval_score"
python scripts\eval_reference_code.py evaluate --run "$Out\C_humaneval_old_gen" --workers 2 --timeout 3 --execute-generated-code --output "$Out\C_humaneval_old_score"
python scripts\eval_reference_code.py evaluate --run "$Out\R_humanevalplus_gen" --workers 2 --execute-generated-code --output "$Out\R_humanevalplus_score"
~~~

WSL에서는 위 경로·$Out을 그 환경에 맞는 절대 경로로 지정한다. --timeout은 OpenAI HumanEval용이고 EvalPlus는 공식 기본 timeout 정책을 사용한다. completion.json은 실행 완료 표식이다. HumanEval 점수는 scores.json, EvalPlus 집계 점수는 official_stdout.txt에 공식 도구가 출력한 그대로 보존한다. EvalPlus의 문항별 JSON 파일명·해시는 official_outputs.json에 기록한다. EvalPlus base 결과와 original HumanEval을 자동 동일시하지 않는다.

## 7. 한국어: metric 교체와 실제 QA 답 생성

### 7.1 KLUE: 예측기를 유지한 전량 채점

~~~powershell
python scripts\eval_reference_korean.py klue --task ynat --checkpoint $Checkpoint --device cuda --dtype bfloat16 --output "$Out\YNAT_full_legacy_predictor"
python scripts\eval_reference_korean.py klue --task nli --checkpoint $Checkpoint --device cuda --dtype bfloat16 --output "$Out\NLI_full_legacy_predictor"
~~~

기존 PMI 예측 함수를 그대로 쓰고 전량을 채점한다. YNAT은 macro F1이 primary, NLI는 기존과 같은 accuracy가 primary다. NLI 알고리즘이 잘못돼 새 분류기를 만들었다는 뜻이 아니다. 이 경로의 길이 처리는 **기존 legacy-seq-max** 계약이다. 초과 문항을 버린 뒤 full dev score를 내지 않는다.

외부 예측 파일이 이미 있으면 --checkpoint 대신 --predictions를 쓴다. JSONL 각 행은 guid와 prediction을 가지며 전체 dev ID가 정확히 일치해야 한다. YNAT prediction은 IT과학/경제/사회/생활문화/세계/스포츠/정치, NLI는 entailment/contradiction/neutral이다. 이를 사용하면 모델을 로드하지 않고 동일 예측의 F1/accuracy를 비교한다.

### 7.2 KorQuAD 1.0

~~~powershell
python scripts\eval_reference_korean.py korquad-generate --checkpoint $Checkpoint --max-new 64 --overflow left --device cuda --dtype bfloat16 --output "$Out\KorQuAD_v1_dev_left"
$Scorer = 'C:\bench_sources\korquad-v1\evaluate-v1.0.py'
$ScorerHash = (Get-FileHash -LiteralPath $Scorer -Algorithm SHA256).Hash
python scripts\eval_reference_korean.py korquad-score --run "$Out\KorQuAD_v1_dev_left" --scorer $Scorer --scorer-sha256 $ScorerHash --output "$Out\KorQuAD_v1_score"
~~~

$Scorer 경로는 예시다. **공식 배포 파일을 확보한 다음** 지정한다. 파일명이 같다는 사실이나 해시 계산만으로 공식 출처가 증명되지는 않는다. 로컬 2.0 scorer를 이름만 바꿔 사용하면 안 된다. left 팔은 문맥 절단을 명시한 dev 점수다. 원문 전부를 받는 조건은 --overflow를 생략해 길이 검사를 통과해야 한다.

## 8. BFCL v3: 공식 채점기·대화 루프 연결

BFCL은 upstream handler/CLI에 의존한다. **v1.3 checkout API에 대한 실제 호환 시험은 아직 안 했다.** 처음에는 simple 한 범주부터 검증하고, 그 뒤 선언한 전체 v3 범주로 확대한다. release/source가 달라지면 잠금 파일을 무시하지 말고 별도 실험으로 취급한다.

~~~powershell
$Bfcl = 'C:\bench_sources\gorilla-v1.3\berkeley-function-call-leaderboard'
python scripts\eval_reference_bfcl.py freeze --upstream $Bfcl --release-label 'Gorilla-v1.3-BFCL-v3-reviewed' --output "$Out\BFCL_lock"
$Lock = "$Out\BFCL_lock\source_lock.json"
~~~

freeze는 사용자 제공 release label과 파일 해시를 저장한다. 최신 main을 지정하면 그것을 자동 v3로 복구하는 기능이 아니다.

터미널 1: TinyLM 모델을 한 번만 로드하는 loopback 서버다. **자동 백그라운드 실행하지 않으며** 사용자가 종료할 때 Ctrl+C를 누른다.

~~~powershell
python scripts\serve_reference_bfcl.py --checkpoint $Checkpoint --device cuda --dtype bfloat16 --port 1053 --output "$Out\BFCL_server"
~~~

tokenizer/ 아래 config는 BFCL의 token count/context 확인용 metadata다. **HF 모델 가중치 변환물이 아니다.** wrapper는 반드시 skip-server-setup으로 연결하므로 vLLM이 이 디렉터리의 가중치를 로드하게 하지 않는다.

터미널 2: 공식 BFCL prompt 생성·평가. multi-turn 범주는 생성 중에도 공식 tool simulator가 수행될 수 있으므로 해당 옵션을 별도로 요구한다.

~~~powershell
python scripts\eval_reference_bfcl.py generate --upstream $Bfcl --lock $Lock --server-run "$Out\BFCL_server" --categories simple --execute-simulated-tools --output "$Out\BFCL_R_simple"
python scripts\eval_reference_bfcl.py evaluate --upstream $Bfcl --lock $Lock --run "$Out\BFCL_R_simple" --execute-official-evaluation --output "$Out\BFCL_R_simple_score"
~~~

--categories에는 그 checkout의 공식 범주/collection을 쓴다. 전체는 all이며 시간·context 검증 후 사용자 실행 대상이다. 단순 범주 점수를 전체 BFCL 점수라고 쓰지 않는다. transport 실패가 발생하거나 공식 ID가 빠지면 완료 처리하지 않는다.

기존 생성 방식의 C 팔:

~~~powershell
python scripts\eval_reference_bfcl.py legacy-export --upstream $Bfcl --lock $Lock --checkpoint $Checkpoint --cache Z:\TinyLM\datasets\bench\bfcl_v3.jsonl --categories simple --legacy-max-new 128 --device cuda --dtype bfloat16 --output "$Out\BFCL_C_simple"
python scripts\eval_reference_bfcl.py evaluate --upstream $Bfcl --lock $Lock --run "$Out\BFCL_C_simple" --execute-official-evaluation --output "$Out\BFCL_C_simple_score"
~~~

legacy-export는 원래 prompt 절단·greedy stop을 유지하면서 공식 ID/파일 schema만 복구한다. 공식 source와 캐시의 ID·question·function이 다르면 중단한다. 기존 parser 진단과 공식 scorer 점수를 같은 생성물에서 비교한다. multi-turn은 기존에 구현되지 않았으므로 이 팔에서 새 동작을 발명하지 않는다.

## 9. 읽어야 할 결과와 남은 검증

| 산출물 | 의미 |
|---|---|
| invocation.json / manifest.json / model.json | 실제 설정·모델·출처 |
| results.json 및 samples_*.jsonl | harness 집계와 문항별 입력·응답·metric |
| paired_items.jsonl / comparison.json | L/R 또는 S 대응 비교. 분모·skip 확인 |
| failure.json | 불완전 실행. 점수 0으로 전환 금지 |
| completion.json | 해당 단계의 정상 종료 표식. 생성 완료와 공식 채점 완료는 다름 |
| source_lock.json / coverage.json | BFCL 버전 bytes와 실제 공식 ID 누락 검사 |
| predictions.json / scores.json | 한국어 예측과 metric |

공식 dependency·task 자료를 준비하지 않은 채 Python 구문만 확인하는 것으로 끝내면 안 된다. **이번 패키지에는 실행 검증이 남아 있다.** 검사 결과를 받기 전에는 README의 명령 예시를 측정 완료 목록으로 옮기지 않는다.
