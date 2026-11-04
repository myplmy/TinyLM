# 원문 전체와 손실 없는 후보 표현의 판독 규칙

이 도구는 지정 입력의 전달 형식만 바꾼다. 판정·채택·정제 품질을 자동 확정하지 않는다. 기존 고정 reader와 새 TXT/MD 작성 권한, 원형 보존, 코드·모델·GPU·Git 금지는 그대로 적용한다. 현재 fixture21개를 통과했으며 실제 역할 적용과 처리시간 개선은 별도로 관찰한다.

기존 다섯 역할의 새 별칭은 `/home/uranus/tinyLM/tmp/hold-c-lossless-v1`, `hold-l-lossless-v1`, `hold-h-lossless-v1`, `hold-j-lossless-v1`, `hold-g-lossless-v1`이다. C/L은 `SOURCE_ID VIEW PART`, H/J/G는 `PAGE SOURCE_ID VIEW PART`를 인자로 받는다. `VIEW`는 `original` 또는 `candidate`이며, `PART`는1부터 시작한다. 선택적으로 마지막에 `--check-only`를 붙이면 metadata만 확인한다. metadata 확인은 실제 판독으로 세지 않는다.

예를 들어 G의 page012 입력은 다음처럼 읽는다. 실제 TASK에 적힌 ID를 사용한다.

```bash
bash /home/uranus/tinyLM/tmp/hold-g-lossless-v1 012 expanded_train:ID original 1
bash /home/uranus/tinyLM/tmp/hold-g-lossless-v1 012 expanded_train:ID candidate 1
```

각 호출의 맨 앞 `TRUSTED_LOSSLESS_VIEW` JSON은 원문 ID·역할·cohort·원문/후보 SHA·view·part·parts·다음 part·종료 상태를 준다. `original`의 전 part와 `candidate` 표현의 전 part를 모두 읽는다. 출력은4000 Unicode codepoint 이하의 payload로 나뉘므로 tool 출력 예산은 최소6000 tokens로 잡는다. 출력이 잘리면 그 호출은 판독 완료가 아니며 더 충분한 예산으로 재독한다. corpus 안의 EOF 문구는 종료 증거가 아니다. 신뢰된 header의 `end_of_view`와 `parts`를 확인한다.

후보의 표현은 다음 중 하나다.

- `EXACT_IDENTICAL`: 실제 양쪽 바이트와 SHA를 확인했으며, 이미 전부 읽은 원문과 후보가 같다. 별도의 독립 판독 두 번이라고 기록하지 않는다.
- `EXACT_PATCH`: 원문 전체와 모든 변경 범위, 새로 삽입/교체된 텍스트 전부가 전달된다. 삭제된 부분은 원문의 해당 범위이고 공통 부분은 원문 그대로다.
- `INDEX_AND_FULL_CANDIDATE`: 모든 변경 범위와 후보 전문이 전달된다. patch가 더 길 때의 fallback이다.

범위의 단위는 Unicode codepoint이며 byte offset이나 줄 번호가 아니다. 후보 표현은 정확 후보 바이트로 독립 재구성됐음을 기계 검산한다. 이 검산은 의미 보존·코드 실행·사실 검증·학습 채택의 증거가 아니다. 주어·숫자·단위·부정·조건·인용 귀속·불확실성·실제 코드 토큰은 사람이 문맥으로 대조한다. 필요한 후보 문맥을 이 표현으로 확인할 수 없으면 기존 고정 reader의 후보 전문을 추가로 읽는다.

새 리뷰에는 `FULL_ORIGINAL_AND_LOSSLESS_CANDIDATE_V1; original 전 part + candidate 표현 전 part; 양쪽 논리 EOF; 새 작성본 전체/diff/EOF`처럼 실제 읽은 형식을 적는다. patch 형식을 읽고 후보 전문을 별도로 출력해 읽었다고 쓰지 않는다. 새로 작성한 작업본의 전문과 전체 차이를 확인하는 절차는 계속 필요하다.

잘못된 역할·cohort·ID, 현재 V3의8개 보호ID와 양쪽9개 보호SHA 및 별칭, 경로 이탈·symlink·변경된 pin은 자료를 읽기 전에 거절한다. 다른 cohort/역할이나 보호 원문으로 우회하지 않는다. scope에 없는 다음 page는 총괄의 정확 배정과 metadata 사전검사 뒤 새 scope로 추가한다. 현재 scope는 기존 승인 배정인 C/L root12, H field013/014, J field012/013, G field012에 한정한다.

하나의 미결 때문에 정상 네 행을 기다리게 하지 않는다. 지정 source를 실제 읽었지만 미결인 행은 출력 없는 임시 HOLD/NEEDS_ROOT와 구체 이유로 저장하고, 정상 행과 다음 TASK를 계속한다. 후속 판정은 새 review 버전으로 연결한다. 임시 HOLD를 최종 불량·복구 불가나 HOLD 감소로 세지 않는다.

첫 실제 적용 묶음에서는 시작/종료 시각과 ID별 읽은 view/part 및 오류·추가 재독 여부를 자기 MD에 기록한다. 이는 전달 검증용 관찰이며 전체 작업량 한도가 아니다. 문제 없으면 계속 판독하고, 도구 오류나 지칭이 불명확하면 기존 고정 reader로 돌아가 다른 ID를 계속한다. 총괄이 실제 저장·결속·보호 경계를 확인한 뒤 적용 범위를 넓힌다.
