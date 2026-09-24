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

### Stage0W — 무모델 데이터계약·음성 fixture PASS, 교사 정답성 NOT_RUN

[독립 검사기](../scripts/diag_p106_verified_teacher_contract.py)와 [사용자 SH](../run_P106_Stage0W_verified_teacher_contract.sh)는 합성 ACCEPT/REJECT/UNKNOWN, teacher 자기판정 거부, split 조상 누출, token ID target 거부, canonical assistant-only 문자 span을 검증한다. 원문/교사모델/HF/GPU 접근0. 검사기가 출력할 수 있는 것은 레코드 수·해시 ID·오류 이유코드뿐이며 이 PASS는 정답 검증 PASS가 아니다.

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
