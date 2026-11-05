# TASK_010 source review (V4)

TASK_010의 다섯 지정 ID를 고정 V4 `pair` reader로 전 파트 판독했다. 초기 한 행 리뷰 `review_010.md`는 보존한다. 이 정제 검토는 최종 채택 판정이 아니다.

| ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거 |
|---|---|---|---|---|
| `expanded_train:289315` | `REVISE_TEXT` | V4 `pair` 1/1, `EXACT_IDENTICAL`, 원문·후보 전체와 EOF 확인. 양쪽 321자·667 bytes, SHA-256 `BD1FF618DC8856D1E348FEBAADED0C4A41D81307066763E750AF4AB43659603A`. | `expanded_train_289315_revised_task010_v1.txt` | 구스타프 미의 생년 괄호에서 빈 쉼표 필드만 제거했다. 연도·직업, 다른 뜻과 인명 목록, `ME`·`MI`를 보존했다. 상세: `hold_289315_task010_v1.md`. |
| `expanded_train:289530` | `REVISE_TEXT` | V4 `pair` 1/1, `EXACT_IDENTICAL`, 원문·후보 전체와 EOF 확인. 양쪽 1,640자·1,640 bytes, SHA-256 `A6458F9B6E91FF71C91EE8739FFA2F230FF6EC20CF758F00154515EE8797A490`. | `expanded_train_289530_revised_task010_v1.txt` | 기록·예상 분포값이 비고 참조 대상도 없는 문장 전체만 HOLD했다. 사진·보호 지정·생태 서술·인용 서지는 보존했다. 값 없는 `Image copyright information` 라벨은 별도 `NEEDS_ROOT`로 남겼다. 상세: `hold_289530_task010_v1.md`. |
| `expanded_train:289609` | `REVISE_TEXT` | V4 `pair` 1/1, `EXACT_IDENTICAL`, 원문·후보 전체와 EOF 확인. 양쪽 860자·1,672 bytes, SHA-256 `5F0C6F02CAB0EA86BABCB8A0256972471B2DFE6FA18F10639264CE258A44E5B7`. | `expanded_train_289609_revised_task010_v1.txt` | 비어 있거나 잘린 일본어 읽기 값에 종속된 문장만 HOLD했다. 독립된 라디오 소개, 발매·트랙·작사/작곡/편곡·주제가 관계 및 링크는 보존했다. 상세: `hold_289609_task010_v1.md`. |
| `expanded_train:289639` | `REVISE_TEXT` | V4 `pair` 1/1, `EXACT_IDENTICAL`, 원문·후보 전체와 EOF 확인. 양쪽 371자·617 bytes, SHA-256 `B888254DF9A6991B725543A49DAA669CA3310C36A9468029166074535B9A8F13`. | `expanded_train_289639_revised_task010_v1.txt` | 제목 뒤 빈 괄호만 제거했다. KOTOKO 싱글 설명, 곡 길이·크레딧·OVA 주제가 관계, 외부 링크와 연도를 보존했다. 상세: `hold_289639_task010_v1.md`. |
| `expanded_train:289707` | `REVISE_TEXT` | V4 `pair` 2/2, `EXACT_IDENTICAL`, `end_of_view=true`, `next_part=null`; 원문·후보 전체와 EOF 확인. 양쪽 3,920자·3,970 bytes, SHA-256 `2D141C63B4B6B656C4B2214C1FD07B0E10413164C397BB94122B71C1CD11D050`. | `expanded_train_289707_revised_task010_v1.txt` | 뒤따르는 코드가 없는 코드 소개 문장 두 곳만 제거했다. 프로젝트 설명·인용·링크와 명시된 Rule 1·2·3·5를 보존했으며 빠진 Rule 4나 코드를 만들지 않았다. 상세: `hold_289707_task010_v1.md`. |

다섯 ID 모두 V4 pair 전체, 새 본문 전문, 원문 대비 전체 diff 및 EOF를 확인했다. 새 본문 SHA·크기와 근거는 각 sidecar에 기록했다. 다음 커서는 TASK_011, `expanded_train:289900`이다.
