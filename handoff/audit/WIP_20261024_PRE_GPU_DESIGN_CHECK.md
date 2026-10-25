# 2026-10-24 야간 실행 전 설계 점검

현재 원장73번의 CPU/GPU 위임은10월24일09:00 KST까지다. 내부 새 실행 마감은08:40이며
사용자 지시 없는 설치·다운로드·Git·삭제·다른 세션 후보 편입은 하지 않는다.

## 실제 gradient/NS 원인분리

독립변수는 같은 초기 본체·첫128행·FP32 MATH에서 참조 헤드와 어휘 타일 헤드의 수치 경로다.
기존 Stage2bW와 달리 실제 postclip 입력·NS 입출력·초기 weight로 원 Muon을 재생한다.
합성2×2 민감도 재실행이나 head 채택을 위한 품질 실험이 아니다.

| 항목 | 사전 판정·근거 |
|---|---|
| 노출 | 각1×8×16×1024=131,072 padded slots; 실제 입력/assistant targets는 원 batch 계획으로 회수 |
| 원천 | 같은 동결22528/512 자료·부모·chat32 SHA. 알려진V3 결함을 기술 제어용으로만 사용 |
| 풀2배 | 수렴/일반품질 비교가 아닌 대응1update 수치 진단이므로 적용 대상 아님 |
| 중복 | registry --tag 두 태그 모두 충돌0. --plan의 P102A100M T0/T1은 본학습 cadence 연구로 이번과 다름 |
| 엄격 대조 | 같은 gradient 재생과 실제 step 재현 모두 완전일치가 필요. 실패하면 인과 해석 금지 |
| 허용차 | 기존2e-6/상대1e-5 유지. FP32 NS도 원 알고리즘의 진단 개입이지 제품 설정 변경 아님 |
| 자원 | 모델 한 개씩, 원GPU 입장검사·실제 CPU 캡처량8GiB 상한·시스템2GiB 여유·종료CUDA0 |
| 시간 | 최대1200초. 기존4update100초는 참고이며 새 회수/첫step 비용 때문에 가속률로 쓰지 않음 |
| 출력 | 새 namespace, 원로그/weight 불변, checkpoint 저장0, 파일별20MB 미만 |

## 외부 HF 공식 Core6

이번 독립변수는 실제 외부 Base/PT 모델이다. 사전학습량·tokenizer가 달라 동일 학습법의
인과 비교나 서로 다른 corpus loss 비교를 하지 않는다. 각 모델의 native tokenizer를 쓰되
공식 고정 과제·prompt·데이터·0shot·choice score/정규화·집계·전체 분모는 동일하다.

| 항목 | 사전 판정·근거 |
|---|---|
| 원형 | 기존 pinned lm_eval/tasks/data를 재사용, 새로운 benchmark 정답 학습0 |
| 수치 선결 | 합성6요청의 실제 batch1/2·전체 label CE·빈 prefix·native BOS·한국어·padding 검산 |
| 비용 | 각 과제32문항은 비용 진단만. 과제별 전체분모 외삽×1.3+실측기동+60초가 full 상한7200초 및08:40 안에 있어야 함 |
| 전체 | 19,965행/67,106 choice likelihood, 저장 원형으로 별도 재계수·공식 집계 대조 |
| 자산 | Qwen06/Gemma270/Gemma1B weight SHA 고정. local-only·remote code 금지·FP32 MATH/eager·TF32/KV off |
| 보류 | Qwen3508 nested loader 미검증. GGUF GPT2 및 나머지 외부 모델은 지원/설치가 미완이므로 통과로 계산하지 않음 |
| 출력 | 모델/phase별 write-once, 부분 실패 원형 보존, raw shard <20,000,000 bytes |

스킬 회귀에 이어 전수 정적을 수행한다. 새 파일의 오류는 GPU 전에 수리하며 보존 원로그의
기존0x02는 지우지 않고 별도 오류로 남긴다. check-only·CPU 통과는 실제GPU 통과가 아니다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
