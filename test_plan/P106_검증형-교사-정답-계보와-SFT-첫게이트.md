# P106 — 검증형 외부 교사 텍스트·계보 분리와 A-only SFT 첫 관문

> 제안 계기: 사용자 승인 [검증형 적응 증류 제안 §10.3](../proposal/20260925_검증형 적응 증류·잠재 추론·내장 의사결정 통합 제안-approved-on-going.md). P090B chat32 부모 사전학습은 완료됐지만 [결과096 §9](../test_result/096_20260925_P090B-공개원천-구조후보-SFT-보류.md)의 공개 SFT 원천 `TRAIN_READY=false`와 풀 편차가 남았다. 이 계획은 A0 선행계약이며 B 잠재추론·C 의사결정 통합 승인이 아니다.

## 1. 왜

외부 교사의 유창한 답을 곧바로 정답으로 삼거나 교사 자신의 만족도를 verifier로 사용하면 작은 학생에게 오류를 전파한다. 교사와 학생 tokenizer가 다르므로 token ID·로짓 KL이 아니라 검증된 **문자열 정답**과 기존 assistant-only SFT mask를 연결해야 한다. 공개 한국어 대화 100+1행의 사람 권리·품질 검수는 아직 대기 중이다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | REJECT/UNKNOWN이 학습 target으로 섞이지 않고 verifier 근거를 추적할 수 있나 | 자기오류 강화·분모 혼동 방지 |
| Q2 | 문제 가족·조상·원문 중복이 train/curriculum_probe/dev/sealed_test 사이에 새지 않나 | 적응 정책의 평가 누출 차단 |
| Q3 | 서로 다른 교사/학생 tokenizer에서 문자열 answer가 canonical assistant-only target과 출처를 보존하나 | token ID 동형 착각·질문 loss 누출 방지 |
| Q4 | 동일 검증 문제에서 Bonsai 후보의 한국어/영어 정답·완료율·accepted sample 비용은 얼마인가 | 교사 선정은 크기나 공급자 평균이 아니라 실측이어야 함 |

## 3. 예측

Q1~Q3의 합성 계약은 모델 없이 PASS 가능하지만 필드 진술만으로 verifier 독립성·정답의 참을 증명하지 못한다. Q4에서는 27B가 더 강할 가능성과 긴 thinking·출력 미완료·VRAM 비용의 대가가 함께 예상된다. 8B 두 계보는 같은 모델의 bit폭 대조가 아니므로 단순 크기 효과를 예측하지 않는다.

## 4. 단계 설계

### Stage0W — 무모델 데이터계약·음성 fixture 사용자 실행 완료(결과098), 교사 정답성 NOT_RUN

[독립 검사기](../scripts/diag_p106_verified_teacher_contract.py)와 사용자 `run_P106_Stage0W_verified_teacher_contract.sh`는 합성 ACCEPT/REJECT/UNKNOWN, teacher 자기판정 거부, split 조상 누출, token ID target 거부, canonical assistant-only 문자 span을 검증해 [결과098](../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)에 남겼다. 재현명령 보존 뒤 SH는 삭제 대상으로 이관됐다. 원문/교사모델/HF/GPU 접근0이며 이 PASS는 정답 검증 PASS가 아니다.

### G0a — 공급자/교사 자산과 소규모 개발 pilot

Bonsai 2 27B PTQ1_0/PQ2_0, 이전 Ternary Bonsai 8B, 1-bit Bonsai 8B의 정확 revision·LICENSE/NOTICE·PrismML fork·template/effort/출력상한을 사용자 승인 아래 고정한다. 동일 문제 가족의 공개 개발용 한국어/영어·논리/산술/문맥/형식 문제를 독립 verifier 가능한 20문항/가족 이내로 작성하되 sealed 문제/정답을 teacher prompt에 보이지 않는다. 한 후보당 GPU/CPU wall·KV/VRAM·출력토큰, 완료/거절/불확실/정답과 독립 verifier 불일치를 기록한다. 다운로드·모델 실행은 사용자 소유이며 현재 `NOT_RUN`.

### G0b — 기준 고정·sealed 교사 선택

G0a의 버그/예산을 본 뒤 **sealed 답을 보기 전에** 가족별 pass/완료율과 accepted sample당 총 출력토큰·wall·권리/안전 컷오프를 사용자와 고정한다. 세 후보를 같은 프롬프트·한도·verifier로 비교하고 단일 평균으로 선택하지 않는다. 정확 후보 revision·정답 출처와 사람 표본 검토가 없으면 `NO_TEACHER_SELECTED`.

### A0 — 정적 검증 텍스트 SFT pilot, 적격 원천 뒤

교사 출력 중 독립 검증된 answer 문자열만 기존 canonical assistant target으로 만들고, 불확실·오답은 학습에서 제외해 별도 원장에 둔다. 기존 P090B 공개 SFT의 license·사람 품질·오염·split/mask `TRAIN_READY`와 부모/tokenizer SHA가 선결이다. 학생 2M processed-token pilot는 기능·오염·비용 진단이지 지능 승격이 아니며 같은 원문/부모·토큰 예산의 no-teacher SFT 대조가 필요하다. 적응 출제 A1/A2와 B/C는 A0의 실제 전이 결과 뒤 별도 계획이다.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| UNKNOWN/REJECT에 supervised target이 생김, teacher-origin verifier를 독립으로 수락, 가족/조상 split 겹침 | Stage0W `FAIL`, 생성·학습 중단 |
| 합성 Stage0W PASS | 스키마·손실 출처 계약만 PASS; 진짜 정답·license·교사 품질 `NOT_RUN` |
| 모델/pack/template/fork/license·GPU budget 미고정 또는 sealed 정답 유출 | G0 중단·`NO_TEACHER_SELECTED` |
| G0a에서 교사 실패 또는 기준 미등록 | A0 열지 않음; 정확 음성과 비용 기록 |
| 공개 SFT 사람/오염/권리 미확인 또는 P090B 부모 계보 불일치 | `TRAIN_READY=false`, 정식 A0 학습 금지 |
| 2M pilot의 loss/문답 개선 | 기능·방향 후보만; 한국어/영어 지능 향상 판정 불가 |

## 6. 비용

| 단계 | 예상 | GPU |
|---|---:|---|
| Stage0W | ⚙0.1h | 없음 |
| G0a/G0b 세 교사 | 다운로드 GB·VRAM/KV·출력토큰 미고정이므로 **시간 상한 등록 전 비용 확정 불가** | 사용자 실행, 한 후보씩 순차 |
| A0 2M pilot | 선별 accepted sample당 비용과 지도토큰/epoch 확인 뒤 산정 | 사용자 모델/GPU |

## 7. 실행 파일

Stage0W의 무모델 계약만 실물로 만든다. G0a/G0b teacher launcher는 revision/license/fork·질문 가족·출력한도·예산을 사용자와 고정한 뒤, A0 학습 SH는 `TRAIN_READY`와 부모 계보가 맞고 `exp-preflight`가 통과한 뒤에만 쓴다. 파일이 없는 단계를 권장 큐 실물로 꾸미지 않는다.

## 8. 한계

메타데이터의 `verifier_origin=external` 표기만으로 실제 독립성·정답성을 증명하지 못한다. Stage0W는 캐시·체크포인트·원본 공개 SFT를 읽지 않고, 다국어 teacher의 지역·문화·의학/법률 답안은 사람 검토가 남는다. 27B·8B 모델 계보가 달라 크기/bit폭만의 인과 효과를 측정할 수 없다. 훈련·원격 추론·다운로드·보호 데이터 접근은 Codex가 수행하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-25: 사용자 §10.3 권장 순서 승인. Stage0W 검사기의 합성 ACCEPT/REJECT/UNKNOWN·teacher 자기판정 거부·split 조상 중복·문자열 target·assistant span fixture가 직접 PASS했고 SH 문법/entrypoint도 PASS다. 이는 **계약 구조만** 검증한다. G0 teacher 자산·실제 독립 정답성·A0 SFT는 권리·사람 품질과 별도 사용자 실행 전 `NOT_RUN`; [검수요청 §7](../review_request/20260925_공개-한국어-SFT-멀티턴-1차GPT-사용자-검수요청.md)을 A0 사람 선결로 둔다.
- 2026-09-25: 사용자 [Stage0W 원본](../test_result/098_log_20260925_P106_Stage0W_verified_teacher_contract.txt) exit0 회수. 합성 accepted/reject/unknown 각1, negative6·교차 split 누출1 거부로 Q1~Q3 구조 예측을 재확인했다([결과098](../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)). Q4 실제 교사 3후보의 라이선스·정답·비용과 A0 SFT는 `NOT_RUN`; 교사 선정 없음.

## 10. 2026-09-26 G0a 선결 — Bonsai 2 27B 자산 메타데이터 gate

사용자가 지목한 로컬 `Ternary-Bonsai-2-27B-PTQ1_0.gguf` 한 파일은 5,946,648,928B·GGUF v3 헤더다. CPU/CUDA 표기 폴더의 `llama-cli --version`은 모두 Prism fork build10735/commit `842b18804`이며, 이 조회는 모델 가중치 로딩이 아니다. 그러나 CUDA 표기 폴더에 `libggml-cuda.so*`가 0건이고 두 CLI의 빌드 ID가 같으므로 **GPU backend는 미검증**이다. 로컬 모델 폴더에 정확 revision의 LICENSE/NOTICE/README도 없다. 폴더명·모델크기·CLI 도움말을 라이선스나 실제 GPU 구동 PASS로 승격하지 않는다.

[Stage0bW 자산 SH](../run_P106_Stage0bW_bonsai27b_asset_preflight.sh)는 GGUF v3/파일크기, 두 CLI의 version/ELF, 정확 모델 폴더의 LICENSE·README 및 CUDA plugin을 메타데이터만으로 확인한다. self-test/check-only는 모델 미열람이다. 자산 부족은 사전등록 exit8 `HOLD`, 헤더/바이너리 결함은 exit2 `FAIL`로 나눈다. 5.9GB SHA 계산은 HOLD가 해소될 때까지 미실행이다. 이 게이트는 teacher answer/정확도·KV/VRAM·출력비용을 측정하지 않는다.

G0a 실제 teacher 소형 pilot의 선결은 (1) 정확 GGUF revision의 공식 LICENSE/NOTICE·model card/출력 재이용 조건을 사람이 확인, (2) GPU를 쓰려면 해당 Prism fork CUDA backend 파일/실제 인식 확인 또는 CPU pilot을 명시 선택, (3) chat template·reasoning effort·출력 상한·독립 verifier 가능한 공개 개발문항을 고정하는 것이다. 본 교사는 27B 한 후보일 뿐 8B 두 계보와 동일조건 3후보 비교는 아직 아니다. 권리/런타임 선결 전에는 모델 로딩 SH나 A0 학생 SFT SH를 READY로 쓰지 않는다.

이 게이트의 예상 시간은 약0.1h·GPU0·모델 생성0이다. 자산 조회가 통과해도 실제 교사 선택은 G0b 기준·독립 verifier와 사용자 E2E 후 별도 판정한다. 웹 공식 페이지 재검증은 도구 인증 오류로 `NOT_RUN`; 이전 제안서의 Apache 표기만 현재 정확 파일의 권리 근거로 삼지 않는다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.


## 11. 2026-09-27 Stage0bW 재판독과 Stage0cW 제한 구동 — 권리 출처·백엔드·예산 분리

§10의 Stage0bW `HOLD8`은 **그때 검사한 `b10735/842b188` 폴더**에 대한 유효한 이력이다. 당시 폴더에 CUDA plugin과 LICENSE/card가 없었다는 관측을 지우지 않는다. 그러나 그 이유를 현재 장치 전체의 CUDA 불가·교사 로컬 시험 불가로 일반화한 것은 과도했다. 사용자가 새 `/home/uranus/llama-prism-bin-ubuntu-x64-cuda133/llama-prism-b10743-adfffbe` 패키지와 이번 요청의 CPU+GPU 제한 시험을 승인했다. 새 패키지에는 `libggml-cuda.so`가 있고 `llama-cli`는 build10743/commit `adfffbe41`이다. PyTorch CUDA 가능과 Prism backend는 별개이며, 이 패키지의 실제 모델 오프로딩은 Stage0cW 로그로 판정한다.

정확한 로컬 `Ternary-Bonsai-2-27B-PTQ1_0.gguf` 5,946,648,928B의 SHA-256은 `53107F530AA52EB00912263AB1EE29BD199261C87CD7B4AD4CA1318C1FE33EE3`로 [공식 PTQ1_0 파일](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/Ternary-Bonsai-2-27B-PTQ1_0.gguf)의 공개값과 일치한다. 공식 [모델 카드](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf)는 Apache-2.0을 표시하고 [LICENSE](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/LICENSE)·[NOTICE](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/NOTICE.txt)를 제공한다. **로컬 파일에 사본이 없다는 이유만으로 로컬 기술 시험을 막지 않는다.** 배포·모델/파생물 재배포는 NOTICE 보존 등 별도 권리 검토 대상이며, 교사 출력의 정답성·훈련 데이터 재이용 적격성은 이 자산 확인만으로 증명하지 않는다.

Stage0cW의 독립변수는 **동일 파일·동일 새 CLI의 GPU 오프로딩 층 수 0→16**이다. 공개 산술 한 문장, ctx512·출력 최대64토큰·CPU 스레드8·temperature0·reasoning effort medium·budget16을 고정한다. `--ctx-size 0`은 모델의 262K 문맥을 잡을 수 있어 금지한다. 각 팔 wall 상한 180초, GPU 팔 전 `nvidia-smi` free≥8192MiB, 원본 HF/체크포인트 쓰기0, 외부 다운로드0, 사용자 작업 중인 학습 프로세스가 확인되면 중단한다. `llama-cli`의 실제 로딩·출력·오프로딩 층·CUDA 버퍼와 전후 VRAM을 기록하되 **64토큰 출력을 정답률이나 teacher 채택으로 쓰지 않는다**. 이번 지시에서만 Codex 제한 실행이 승인됐고 일반 운영 실행 소유권은 사용자다.

| 안 | 역할 | 예상 대가·판정 |
|---|---|---|
| A CPU `-ngl 0` | GPU 충돌 없는 기준선 | RAM 약6GB+버퍼, 느릴 수 있음; CPU 기능만 |
| B hybrid `-ngl 16` | 16GB 카드에서 학습 VRAM 여유를 남길 후보 | CPU↔GPU 전송·부분 오프로딩 지연 가능; 실제 VRAM/속도 확인 후 판단 |
| C full GPU `-ngl all` | 교사 단독 처리량 상한 | 5.95GB 가중치 외 KV/compute가 추가되어 TinyLM 학습 reserved 약8.64GiB와 동시 상주를 보장하지 않음; 이번 작은 시험은 실행하지 않음 |

이번 시험 PASS의 최소 조건은 정확 SHA·새 CLI/plugin·CPU 팔 exit0/출력>0과 hybrid 팔 exit0/실제 CUDA 층 오프로딩·출력>0이다. 하나라도 무너지면 해당 팔은 `FAIL` 또는 자원 `HOLD`로 분리한다. 현장 GPU 메모리 free 14,627MiB(사전 읽기)는 실행 시 바뀔 수 있으므로 런처가 다시 확인한다. Stage0cW가 통과해도 Q4의 교사 정확도, 한국어 SFT 데이터 권리/사람 검수, 8B 후보 대조와 A0 학습은 `NOT_RUN`이다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 12. 2026-09-27 실제 CPU/GPU 패널 — 동시 배치 추산과 남은 교사 품질 문턱

[결과098 §4~§5](../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)는 사용자 Stage0bW `HOLD8`을 **옛 패키지에 대한 역사 결과**로 보존하면서, 이번 요청의 제한된 Codex CPU/GPU 시험을 별도 Stage0cW/dW/eW/fW/gW/hW로 기록한다. §11의 “full GPU 미실행”은 실행 전 계획 문장이고 **이번 Stage0f/gW에서 단독 full GPU가 실제 실행됐다**. 로컬 SHA와 공식 파일 SHA 일치, 새 `b10743/adfffbe41` CUDA plugin 존재, CPU0·GPU16/40/48/56/all 각 프로세스 종료0·산술 출력4를 확인했다. 이는 기술 구동이지 독립 검증 교사 채택이 아니다.

동일 PTQ1_0·Prism·ctx512·합성 프롬프트/출력상한64의 단독 실행에서 0.2초 **전역 GPU 사용량 표본** 증가와 생성 tok/s는 GPU16 `1,817MiB/2.7`, GPU40 `3,795MiB/4.9`, GPU48 `4,479MiB/7.7`, GPU56 `5,145MiB/12.4`, full `5,874MiB/54.2`였다. 별도 CPU0는 약2.1tok/s였다. `16,376MiB 카드 − 팔별 시작 GPU 점유 − P076 학생 reserved 8,846MiB − 교사 증가표본`으로 계산한 **동시 상주 추정 잔여**는 순서대로 4,267/2,272/1,608/942/213MiB다. 실제 학생·교사를 같은 시각에 돌린 횟수는 **0회**이며, NVML 전역 표본은 좁은 peak·다른 프로세스·allocator 단편화를 놓칠 수 있다. 따라서 full은 단독 생성 전용, 최소2GiB 명목 여유의 CPU16층/GPU40을 **동시 실험 1순위**, GPU48은 약1.57GiB 여유의 조건부 후보, GPU56은 장기 동시 운영 보류다. GPU40의 생성4.9tok/s는 full54.2tok/s보다 약11배 느려 대량 교사 데이터라면 **교사 단독 full GPU 선생성→독립 검증→학생 단독 학습**이 우선이다.

부분 오프로딩 16/40/48/56 모두 첫 CPU 층 때문에 fused Gated Delta Net이 비활성화됐고, hybrid 종료 때 `CUDA_Host compute buffer` 23.99 대 기대9.44MiB 경고가 있었다. full에서는 전자가 없었다. 현재 짧은 CLI 내부 서버는 localhost 임시 포트에만 바인딩됐지만 CORS `*`·API key 없음 경고를 냈으므로 장시간 교사 서비스로 확대하기 전 접근제어가 별도 선결이다. 새로운 [VRAM sampler](../scripts/diag_p106_vram_sample.py)의 0.2초 표본과 [런처](../run_P106_Stage0hW_bonsai27b_concurrent_budget.sh)의 정적·동적 계약은 기능 범위로만 PASS이고, Q4 공개문항 가족별 정답성/완료율·accepted sample 비용, 8B 후보 대조, 실제 동시 학생 학습, A0 SFT는 모두 `NOT_RUN`이다.

Stage0cW 로그의 llama 로딩 스피너가 두 줄에 백스페이스를 남겨 정적 제어문자 검사에서 실패했다. 사용자 승인 아래 원본 SHA와 정제 후 SHA를 [결과098 §5](../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)에 기록하고 그 스피너 줄만 정규화했다. 이후 Stage0d/g/h는 `--simple-io`로 같은 사고 없이 수집됐다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 13. 2026-09-27 Stage0iW~0oW — GDN 배치 원인과 교사·학생 공존의 세 게이트

[결과098 §6~§7](../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)은 같은 GGUF/Prism/ctx512·64출력 상한에서 `--fit off`, `--op-offload` 유무, FFN tensor CPU override만 바꾼 제한 실험이다. 계획 §12의 GPU40 기본 생성4.9tok/s·GDN 비활성은 **고정 판정이 아니라 개선 대조군**이다. Stage0iW의 `--require-fusion`은 verbosity3에서 `enabled` 로그가 생략돼 exit8을 잘못 찍었다. **무효 계측**으로 남기고, Stage0lW verbosity4 복구를 정본으로 쓴다.

| 단계 | 한 축과 사전 질문 | 실제 관측·판정 |
|---|---|---|
| Stage0lW A/B/C | GPU40 기본 vs `--no-op-offload`, GPU48 확장. `--fit off` 고정, trace4에서 AR/chunked `enabled`를 명시 확인 | GPU40 기본 GDN 둘 다 disabled/5.1tok/s; no-op은 둘 다 enabled/6.7tok/s·VRAM3,791MiB. GPU48 no-op 둘 다 enabled/9.2tok/s·4,455MiB. 옵션이 **융합을 복구**하나 CPU층 병목은 남음 |
| Stage0jW/kW | `-ngl all`의 논리 GPU 층을 보존하고 첫32층 FFN gate/up/down 96 tensor만 CPU | FFN32 약4,084~4,087MiB·7.0~7.2tok/s, Stage0k trace4 GDN 둘 다 enabled. 정확 tensor 이름 확인; 원본 GGUF 변경0 |
| Stage0mW/nW/oW | FFN32 micro8 → FFN60 micro8 → FFN32 micro4. 교사 실제 생성과 P076 같은 모양의 합성 학생 Muon 1 step을 겹침 | 세 팔 모두 짧은 공존 exit0·OOM0. `nvidia-smi` 시작 free−증가표본은 126/1,019/4,679MiB. 앞 두 팔은 안전여유 부족; micro4는 별도 학습 recipe 후보일 뿐 |

동시 시험의 학생은 `m100R1c tied/ag2/cla2`, seq1024, Muon RMS4×4·AdamW, 합성 token과 무컴파일·난수 초기화, micro8 또는4, `accum=1`, **체크포인트·캐시·부모 읽기0**으로 제한했다. 이는 사용자 승인 1~3 step 안에서 실제 두 프로세스의 상주/동시 계산 peak를 확인한 것이다. 실제 P076 micro8×accum16/compile/부모/실데이터 300M 학습과 동일하지 않다. 변경된 micro4로 유효 배치를 유지하려면 `accum=32`지만 GPU wall·품질·장기 OOM은 **NOT_RUN**이므로 기본 팔을 조용히 변경하지 않는다. FFN60의 단독 VRAM 표본2,527MiB와 생성3.2tok/s는 메모리 확보와 CPU 처리량 손해를 분리한다.

현재 기술 권고는 **교사 단독 full GPU에서 후보 답안 생성→독립 verifier와 사람 검토→교사 해제→학생 학습**이다. 실시간 공존이 실질적으로 필요할 때에는 별도 계획·사용자 실행으로 `FFN32/no-op/fit-off + micro4×accum32`의 실제 학습 조건, peak/step wall·학습 품질을 미리 등록하고 판정한다. Stage0oW의 4,679MiB 표본 여유를 장시간 운영 안전 보증으로 사용하지 않는다. P106 Q4 교사 정답성·accepted sample 비용·세 계보 비교와 A0 SFT `TRAIN_READY`는 계속 `NOT_RUN`이다.
