# 텍스트 보조 위임 명세

근거: 2026-10-26 사용자 goal 5절. 총괄 세션 `01a17740-f435-7243-874c-2b5d58181c4c`, [정제 작업 계약](../../../docs/research/20261026_전체입력풀_의미보존정제_작업계약.md). 동시 보조는 `gpt-6-luna`, `max` 최대 5개다. 모든 보조는 텍스트 판독·새 txt/md 정제본·판정 이유만 맡는다. 코드·시험·전처리 스크립트·모델·GPU·Git·작업규약·설정 수정/실행과 설치·다운로드·외부 발신은 금지한다. 원문/기존 초안은 읽기 전용이며 공유 worktree를 OS로 격리했다고 주장하지 않는다.

## legacy_review

- 입력: `data_cache/p106b_native_source_context_clean_v1_20261026/source_{01,02,03,04,06,07,08}_original.txt`, 동일 디렉터리의 `luna_revision_v5/source_{01,02,04,06}.txt`, `source_08_draft_scope_v4.txt`; 관련 소형 manifest의 정확 원문 ID/SHA·편집 근거.
- 출력: `data_cache/p106b_corpus_cleanup_v1_20261026_goalc/agents/legacy_review/` 아래 새 `source_XX.txt` 및 `review.md`만 생성. 기존 다섯 초안을 독립 대조하고 불명/복원 불능은 HOLD, 새 정제가 필요하면 원문 관계·용어·수치·조건을 보존한다.
- 반환: 문서별 KEEP/EDIT/HOLD, 정확 입력/출력·보존/제거 근거·사실검증 한계·실제 읽은 범위. 총괄 채택 전 자동 학습 편입 없음.

## historical_review

- 입력: `handoff/audit/oct26_research/source_context_review_v1/long_source_05/original.txt`와 그 디렉터리의 순서 있는 txt 분할본·manifest, 직전 원문맥락 판독 문서의 source_05 설명.
- 출력: `data_cache/p106b_corpus_cleanup_v1_20261026_goalc/agents/historical_review/` 아래 새 `source_05.txt`와 `review.md`만 생성.
- 역할: 역사 원고 전사·인용 주체·편집 기호·후대 주석/판본을 보호하며 실제 웹 푸터와 분리 가능성을 판독한다. 전량을 읽지 못하면 범위를 명시하고 HOLD한다. 누락 구간을 생성하지 않는다.
- 반환: 실제 읽은 구간/순서·판정·층위별 보존 근거와 정제안. 코드·시험·다른 텍스트 출력은 금지한다.

## 후속 위험군/무신호 독립 판독

전체 스캔이 만든 지정 원문 패킷을 이 명세에 추가한 뒤 남은 자리를 위임한다. 작은 패킷은 규칙·의미 검증 표본이며 전체 처리량 한도가 아니다. 보조 출력이 누락되거나 원형과 대응하지 않으면 총괄은 채택하지 않고 사유를 기록한다. 파일 범위 이탈은 즉시 중단·보고한다.

## legacy_review 후속 v2

총괄이 첫 실제 저장물/근거를 읽고 01/02의 원문 인용·불확실성 복원을 확인했다. 04의 학술 참고문헌은 보존하지만 연결을 잃은 외부 링크 제목 다섯 줄은 별도 보류 부록, 08의 마케팅/수요/경쟁사 찬사는 별도 광고 부록으로 분리한다. 추가 새 쓰기 허용은 같은 legacy_review 폴더의 `source_04_v2.txt`, `source_04_appendix_hold.md`, `source_08_v2.txt`, `source_08_advertising_hold.md`, `review_v2.md`다. 첫 저장물을 덮지 않는다.

## historical_review 후속 v2

첫 보조가 28조각 전체 판독과 원고 층위·취소 기호의 유효성을 보고했다. 총괄은 일반 HTML/반복 필터의 예외로 원고와 학술 apparatus를 보존하되 확정 사이트 UI만 분리한다. 같은 historical_review 폴더의 새 `source_05.txt`와 `review_v2.md` 쓰기를 허용한다. 지정 original.txt를 새 txt로 그대로 복사한 뒤 텍스트 패치로 마지막 `Return to homepage`와 `File last updated 2 July, 2012.`만 제거할 수 있다. 이는 일반 텍스트 저장이며 분석/전처리 스크립트 작성·실행은 금지한다. 사이트 서지 인용과 URL은 보존한다. 첫 review.md는 덮지 않는다.

## context_hangul / context_latin / context_controls

각 역할의 정확 입력은 새 파생 폴더 `assignments/<역할>.md`가 소유한다. 원문은 같은 파생 폴더 `packets_initial/`에서 그 목록에 적힌 txt만 읽는다. 이 44개는 시험 묶음이며 전체 정제 한도가 아니다. 각 역할은 같은 파생 폴더 `agents/<역할>/review.md`와 EDIT 판정 ID의 콜론을 밑줄로 바꾼 새 txt만 쓴다. 자동 판정 구현과 분리한 독립 문맥 판독이다. KEEP/EDIT/HOLD·실제 전체 읽기 여부·원문/수정 근거를 반환한다. 코드·스크립트·시험·모델/GPU·Git·규약 수정/실행은 금지한다. 다른 역할의 입력·출력은 접근하지 않는다.

## legacy_review 후속 v3 — 총괄의 원문/저장물 diff 반례

새 쓰기 허용은 같은 폴더의 `source_01_v2.txt`, `source_04_v3.txt`, `source_08_v3.txt`, `review_v3.md`다. 01의 수상 목록에 원래 정확했던 IBBY 영문을 도입부 오탈자와 일괄 통일한 새 오류를 원문대로 복원한다. 04의 링크 꼬리 중 제목·저자·매체·날짜가 있는 Jennifer A. Clack의 Scientific American 서지는 학술 참고자료로 보존하고, 목적지를 잃은 나머지 네 링크 표제는 보류한다. 08에는 새로 넣은 편집자 안내 문장을 없애고 중립 도감 본문으로 적는다. 객관적 정보·단위는 유지하고 광고 부록은 보존한다. 이전 산출물을 덮지 않는다.

## 다섯 역할의 전체 범위 문맥 검토 v2

첫 44개 후속으로, 160개 표본을 다섯 기존 역할에 32개씩 배정한다. 정확 읽기 목록은 `assignments/<역할>_coverage_v2.md`, 원문은 `packets_coverage_v2/`의 그 목록에 적힌 txt뿐이다. 각 역할의 쓰기는 `agents/<역할>/coverage_v2/review.md`와 EDIT ID의 콜론을 밑줄로 바꾼 새 txt만 허용한다. 기존 리뷰/원문/수정본은 덮지 않는다. 총괄은 실제 저장물과 원문 연결·변경·판정을 후행 대조한다. 코드·시험·스크립트·모델/GPU·Git·다른 역할 폴더·목록 외 자료는 금지한다. 초기 두 보조의 주변 행/외부 memory 검색 노출은 각 리뷰에 그대로 보존하며 후속은 지정 목록만 판독한다.

## 전량 스캔 완료 후 최종 추가 판독

전체 2,154,912구간 스캔 완료 뒤 같은 위험/문자 출현 선택 규칙을 다시 적용했다. 이미 읽은 원문 SHA를 제외한 추가분만 다섯 기존 역할에 배정한다. 정확 목록은 `assignments/<역할>_final.md`, 원문은 `packets_final/`의 그 목록에 적힌 txt다. 쓰기는 `agents/<역할>/final_context/review.md`와 EDIT ID 콜론을 밑줄로 바꾼 새 txt만 허용한다. 이전 원문·수정본·리뷰는 덮지 않고 같은 텍스트 전용 금지를 유지한다.

## 실제 정제 저장물 독립 대조

현재 52개 EDIT 후보를 작성자와 다른 기존 Luna 역할에 배정한다. 정확 원문·정제본 쌍은 `assignments/<역할>_counterreview.md`다. 지정 쌍만 읽고 각 역할의 `agents/<역할>/counterreview.md` 하나에 PASS/REVISE/HOLD·반례·실제 읽은 범위를 쓴다. 본문을 추가 편집하지 않는다. 긴 source_05는 끝40줄 문맥 판독과 총괄의 전체 바이트 불변 검산을 결합하며 이를 전량 재독으로 표현하지 않는다. 짧은 쌍은 전문 대조한다. 나머지 실행/보호 금지는 동일하다.

## 실제 대조 후 보완 저장

- legacy_review: 기존 지정 source01/02/04/08 원문과 현재 수정본·관련 counterreview를 읽어 같은 폴더에 `source_01_v3.txt`, `source_02_v2.txt`, `source_04_v4.txt`, `source_08_v4.txt`, `review_v4.md`만 새 작성한다. 01/02/04의 유효 고유 분류 관계는 주제가 드러나는 구조로 보존하고, 02의 유효 경력 반복을 원문대로 회복한다. 08은 원문 객관적 정보와 광고 분리를 유지하면서 불필요한 재서술을 줄인다. source01 서명 정정은 새 ISBN 근거로 유지한다.
- historical_review: `expanded_train:38390`의 기존 지정 원문과 수정본을 다시 읽어 `agents/historical_review/coverage_v2/expanded_train_38390_v2.txt`와 같은 폴더 `revision_v2.md`만 쓴다. 제목과 붙은 작성자 표식을 정확 분리하고 원문 밖 이름을 생성하지 않는다.
- context_hangul: `expanded_train:62127`의 기존 지정 원문/수정본과 정확 관련 counterreview를 읽어 `agents/context_hangul/coverage_v2/expanded_train_62127_v2.txt`, 같은 폴더 `revision_v2.md`만 쓴다. 내용 있는 Wildcat Haven 서평·수량·인용·개체 나이/기간은 원문대로 복원하고 판매/후원 CTA·탐색만 분리한다.

모든 이전본과 독립 부정 의견은 보존한다. 코드·시험·모델/GPU·Git·기타 범위는 추가 허용하지 않는다.

## DCD 본문 말미 장식 분리

context_controls는 이미 지정된 `expanded_train:155518` 원문/정제본을 다시 읽어 같은 coverage_v2 폴더에 `expanded_train_155518_v2.txt`와 `revision_v2.md`만 새 작성한다. 제목을 생성하지 않고 DCD 본문·논문 인용·쪽수·조건은 그대로 보존한다. 첫 소셜 UI·끝 추천 위젯 외에 그 바로 앞의 장식 행 `~~~~~~~~~~ 0 ~~~~~~~~~~`만 제거한다. 실제 코드펜스가 아닌 이 확정 장식 행은 총괄이 원문별 예외로 검산하며 전역 펜스 제거를 허용하지 않는다.

## 보완 저장물 독립 재대조

추가 읽기 목록은 `assignments/<역할>_counterreview_v2.md`의 일곱 원문/새 수정본 쌍이다. 각 역할은 같은 폴더의 `counterreview_v2.md` 하나만 쓴다. 정확 추가 읽기 허용은 `COUNTERREVIEW_RESOLUTION.md`와 `title_fact_check.json`이며, 근거 있는 서명 정정·주제 식별 가능성과 핵심 관계 소실을 구분한다. 다른 자료·실행 권한은 추가하지 않는다.

## 최종 좁은 표제·주체 보완

legacy_review의 새 쓰기는 같은 폴더 `source_01_v4.txt`, `source_02_v3.txt`, `source_04_v5.txt`, `source_08_v5.txt`, `review_v5.md`다. 01/02의 `원문 분류` 표제는 각각 인물 정보로, 04는 이크티오스테가의 분류로 바꾸어 편집자 관점을 본문에 넣지 않는다. 정보값은 그대로 유지한다. 08은 고립된 상위 도감 서명과 주체 없는 We’ve를 없애고 원문이 명시한 National Geographic·상위 도감·동서부 편제 관계를 한 중립 문장으로 연결하며 나머지 기능·수치·단위는 그대로 둔다.

context_latin은 source02 원문과 v2를 정확 다시 읽어 `counterreview_v3.md`만 쓴다. 총괄이 source02에는 한국전통가공식품협회/1999.01 경력이 없음을 확인했다. 다른 문서233567의 중복 경력을 source02에 혼동해 적용한 이전 의견을 실제 원문 근거로 정정하며 어떤 사실도 source02에 추가하지 않는다.
