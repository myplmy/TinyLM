# Stage 2~10 파일럿 폐기 초안 기록 — 2026-09-01

## 판정

아래 산출물은 Stage 2~10 tokenizer pilot의 **확정 corpus가 아니다**. 생성 도중 정본 작업지침서 §10~§11의 직접 작성·문형 다양성 규칙을 충족하지 못한 사실을 확인해 전부 재작성 대상으로 돌렸다. 이 기록은 실패한 초안을 완료본으로 오인하거나 다음 세션에서 재사용하지 않게 하기 위한 감사 로그다.

## 폐기 사유

1. Stage 2~4 초안은 `author` 계열 Python 도구가 concept·relations·text를 조합했다. Stage 3~4에는 `…가다`, `…가었고`, `판정 판정`, 의미 없는 `…판정에서` 삽입이 반복됐다.
2. Stage 8~10 초안은 `rewrite`·`diversify` 계열 Python 도구가 문장 문두, 추가 문장, relation 순서를 일괄 변환했다. 표면 문장은 비교적 자연스러웠으나 600/600이 primary concept로 시작하고 600/600이 한 문장인 Stage가 있어 구조적 template가 남았다.
3. Stage 5~7 최초 초안은 기계 감사에서는 통과했지만 독립 의미 감사에서 1,782/1,800(99.0%) primary-concept 문두, 1,800/1,800 단문, 강한 6행 relation 주기, 생산적 suffix, train–validation 골격 재사용이 확인됐다.
4. Stage 2와 Stage 8의 validation 표본은 같은 행 번호의 train 문장을 다른 도메인 명사로 바꾼 대응 골격이 남아 Guide §13의 단순 바꿔쓰기 금지에 미달했다.

## 금지·제거 대상 활성 도구

다음 유형의 도구는 최종 `tools/`에 남기지 않는다. 정확한 파일 존재 여부는 최종 통합 감사가 다시 검사한다.

- `stage2_highdensity_dataset/tools/_author_stage2_direct_psv.py`
- `stage3_highdensity_dataset/tools/_author_stage3_direct_psv.py`
- `stage8_highdensity_dataset/tools/rewrite_stage8_remaining_sources.py`
- `stage8_highdensity_dataset/tools/diversify_stage8_10_sources.py`
- `stage9_highdensity_dataset/tools/rewrite_stage9_direct_sources.py`
- `stage10_highdensity_dataset/tools/rewrite_stage10_direct_sources.py`
- 그 밖에 text·concept·relations를 조합·치환·다양화하는 `author`·`rewrite`·`diversify` 도구

builder의 ID·metadata 포장과 read-only auditor는 허용한다. 문장 의미를 만드는 코드는 허용하지 않는다.

## 재작성 승인 조건

- canonical source의 각 행을 직접 읽고 primary concept·relations·text를 독립 작성한다.
- 파일별 primary concept 문두 시작 90/150 이하, 2문장 이상 45/150 이상, lag-6 동일 relation-set 72/144 이하를 최소 구조 gate로 사용한다.
- Stage 6 long-context와 Stage 7 multiturn은 150/150 모두 3문장 이상으로 실제 장거리 참조·턴 상태를 담고, 정확히 3문장인 단일 골격을 막기 위해 파일마다 최소 30개는 4문장 이상의 독립 전개로 쓴다.
- validation은 train의 행별 대응 골격을 쓰지 않고 독립 작성하며, `unseen_relation: true`는 18/150로 재계산한다.
- JSON·schema·ID·13개 relations·5어절·4어절 도입부·TF-IDF·조사·보호 SHA-256과 별도 층화 의미 감사를 모두 통과해야 한다.

## 보호 범위

폐기 판정 시점까지 저밀도, held-out/evaluation, Stage 1 고밀도 train/validation, 중앙 예약 원장은 corpus source로 사용하거나 수정하지 않았다. 최종 무결성 수치는 재작성 종료 후 시작 기준선과 다시 비교한다.
