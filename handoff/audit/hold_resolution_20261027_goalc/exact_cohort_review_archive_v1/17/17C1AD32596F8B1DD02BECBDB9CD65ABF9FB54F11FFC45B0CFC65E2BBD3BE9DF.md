# B안 지정 문맥 검토 — 묶음 4

- 역할: `l_partial_deletions`; 범위: 지정 10개 ID 전부
- 입력 scope SHA-256: `20A4400D2F8C0F9E6FF39663BA85073FEBB68DD53F0DD778CED682484F595D5E`
- 고정 판독기 출력에서 10건 모두 `original_full_read_is_prior_primary_author_claim=true`, `exact_final_reconstruction=true`, `unchanged_text_outside_delivered_changes_preserved=true`, `new_first_read_credit=0`, `root_or_cache_admission=false`를 확인했다. 원문 전문 근거와 동일본문 증명은 기존 primary review를 재사용했다.
- `flags`는 모든 ID에서 part 1/1, EOF이며 `NO_LOCAL_BLOCK_FLAGS`였다.
- 이 파일만 새로 작성했다. 입력 TXT 변경·ROOT/cache 채택 없음.

| ID | BODY_SHA256 | DECISION | ACTUAL_VIEWS_AND_EOF | SOURCE_MEANING_OR_REMAINING_ISSUE |
|---|---|---|---|---|
| expanded_train:153808 | `BB775C521011260060D61FA4337781A69F4366A86F32A1F27717AFF50404DC1E` | APPROVE_EXISTING_BODY | changes p1/1 `[0,2973)` EOF=yes; body p1/2 `[0,3499)` EOF=no, p2/2 `[3499,5715)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | 서지 끝의 빈 괄호와 내용 없는 `각주` 표제만 제거했다. 증거의 종류·입증책임·증거능력·디지털 증거 및 무인장비 사진에 관한 설명, 같이 보기 항목과 `형사소송법`·`법률 용어` 분류는 남아 있다. 법률 문구의 반복·오류는 후보가 고치지 않았다. |
| expanded_train:155939 | `A065BC7D3BBF4E358D85192FE26143F50A6B58BFF45559C6C429BD4C34A2BA61` | APPROVE_EXISTING_BODY | changes p1/2 `[0,3498)` EOF=no, p2/2 `[3498,6674)` EOF=yes; body p1/1 `[0,2568)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | 명칭의 빈 병기 슬롯과 그에 붙은 쉼표·공백만 정리해 `케플러 초신성(SN 1604)`를 보존했다. 빈 각주 표제는 제거하고 관측일·밝기·유럽 및 조선 기록·태그를 남겼다. 고유명·연도·수치의 독립 삭제는 없다. |
| expanded_train:157246 | `CC2D6358B1F5CAAD6300B05468782B46331A6506781F4ACF828AA2AAA6A384FE` | APPROVE_EXISTING_BODY | changes p1/2 `[0,3500)` EOF=no, p2/2 `[3500,6880)` EOF=yes; body p1/1 `[0,1815)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | 빈 `Start menu ()`를 정리했고 실제로 제공되지 않은 스크린샷을 가리키는 문구, 영상 자기소개와 편집 메모를 제거했다. 권한 상승·재시도 안내, `netstat` 명령, Ctrl+C, 로그 파일 열기와 결과 해석 등 실제 실행 설명은 그대로 남아 있다. |
| expanded_train:157634 | `CECD2154F0E556B21D88926CD1CB4792D61EEED8D20F043DC0721A027C1B9C2E` | BODY_NEEDS_REPAIR | changes p1/2 `[0,3500)` EOF=no, p2/2 `[3500,4077)` EOF=yes; body p1/1 `[0,349)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | 평탄화되어 절차 경계가 손실된 VBA 코드는 보류할 수 있다. 그러나 같은 삭제 범위에 코드 앞의 완결된 설명 두 문장(첫 단추가 조건을 검사해 행을 숨기고, 둘째 단추가 표시·색을 되돌린다는 설명)까지 함께 제거됐다. 이 문장은 코드 행·조건 구조를 복원하지 않고도 자체로 요약 정보를 제공하므로 원문 그대로 복구한다. 코드 본문과 뒤의 계산 동영상 포인터는 복원하지 않는다. |
| expanded_train:158709 | `842B071F3A8DB77BA64DEB015D35A177605BFEAE293606BFFB26B9325FAB7C0D` | APPROVE_EXISTING_BODY | changes p1/2 `[0,3500)` EOF=no, p2/2 `[3500,5192)` EOF=yes; body p1/1 `[0,963)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | 빈 병기 괄호, 내용 없는 소절 `형법`, 빈 서지 괄호와 각주 표제만 정리했다. 영미법상 승낙·불법행위·추정적 승낙 설명, 두 참고문헌과 말미의 실제 `형법` 분류는 남아 있다. 빈 소절 삭제가 말미 분류까지 지우지 않았다. |
| expanded_train:160174 | `8DB93A67DA7260E56754D2EBB969D59522FA6E03FDA11F582137D56673CBDF81` | APPROVE_EXISTING_BODY | changes p1/3 `[0,3500)` EOF=no, p2/3 `[3500,6999)` EOF=no, p3/3 `[6999,8544)` EOF=yes; body p1/1 `[0,3272)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | 기호·대상이 빠져 출력이 비어 있는 `충돌 저항성` 조건 및 약한·강한 정의를 보류했다. 남은 본문은 해시 충돌의 존재·자료구조 영향, 암호학적 용례와 공격 명칭, 실제 참조·외부 링크와 분류를 완결된 문장으로 설명한다. 누락 변수와 정의에 기대는 결론을 본문에 남겨 일반화하지 않았다. |
| expanded_train:160257 | `0C436320788656C136F37C761077039D7ECE05F03BCBB47742BED0D50E6661C7` | APPROVE_EXISTING_BODY | changes p1/3 `[0,3500)` EOF=no, p2/3 `[3500,6998)` EOF=no, p3/3 `[6998,8045)` EOF=yes; body p1/2 `[0,3500)` EOF=no, p2/2 `[3500,5198)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | 빈 `조문` 표제, 이미 없는 각주 표제, 서지 끝 빈 괄호와 마지막 LF만 다뤘다. 형법 제20조의 정의·요건·효과·유형·판례, 채워진 참고문헌, `법률 용어`·`형법` 분류는 남아 있고 조문 표제가 빠진 자리에 미제공 조문 내용을 만들지 않았다. |
| expanded_train:161535 | `0256804799200D2DC90CA77580CEE5C5956DFECFB05F9CBB782AFD48D112ED89` | APPROVE_EXISTING_BODY | changes p1/2 `[0,3500)` EOF=no, p2/2 `[3500,3752)` EOF=yes; body p1/2 `[0,3500)` EOF=no, p2/2 `[3500,3978)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | Dawkins·Hitchens 참고문헌의 빈 괄호와 내용 없는 `각주` 표제만 정리했다. 신의 존재 주장과 반박, 불가지론, 실제 서지 및 신학·철학 등 분류값은 유지됐으며 논증의 참·거짓을 외부 검증하지 않았다. |
| expanded_train:165468 | `9B6AAE2C27A3EEAA7F19437BE16FF4B356B3D2CA746F9301179B5B6E21CF44B1` | APPROVE_EXISTING_BODY | changes p1/2 `[0,3500)` EOF=no, p2/2 `[3500,5109)` EOF=yes; body p1/1 `[0,310)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | 빈 병기값, 값이 없는 정의표와 그 빈 함수값·치역·정의역을 직접 참조하는 설명 및 아크탄젠트 지시를 함께 보류했다. 일반 역함수 설명과 같이 보기·실제 분류값은 남아 있다. 특정 역삼각함수의 공식이나 interval을 추정하지 않았다. |
| expanded_train:167841 | `C47BF6DBF0B60650C0EA1A95D877A494219711487D12FF6BBFBC81FA6E54B133` | BODY_NEEDS_REPAIR | changes p1/4 `[0,3500)` EOF=no, p2/4 `[3500,7000)` EOF=no, p3/4 `[7000,10500)` EOF=no, p4/4 `[10500,12646)` EOF=yes; body p1/2 `[0,3500)` EOF=no, p2/2 `[3500,4589)` EOF=yes; flags p1/1 `[0,89)` EOF=yes | `Yin,p.` 꼬리, 열린 인용·출처 경계 뒤의 잘린 문장·혼입 발췌는 보류할 수 있다. 다만 change 1은 페이지 제목으로 보이는 `Analysis of case study methodology`가 문장 안에 끼어든 것 외에, 사회과학자가 이 방법을 동시대 사례에 적용해 아이디어·방법을 확장한다는 완결 주장을 함께 삭제했다. 제목 토큰을 분리하고 그 문장 내용은 원문 표현으로 복구한다. 별도 `This paper` 비영리 네트워크 사례 문단은 독립 완결문이지만 남은 일반 방법론 본문과의 출처 관계가 확인되지 않아 삭제 근거가 별도 확인 대상이다. 이 문단을 복구하거나 출처를 일반화하지 않는다. |

## 묶음 판정 요약

- `APPROVE_EXISTING_BODY`: 153808, 155939, 157246, 158709, 160174, 160257, 161535, 165468
- `BODY_NEEDS_REPAIR`: 157634의 VBA 예제 앞에 있던 두 문장짜리 독립 설명 복구 제안; 167841의 제목 토큰에 끼인 완결 설명 복구와 별도 `This paper` 문단의 출처 경계 확인 제안

좁은 구별은 코드 구조가 평탄화된 예시와 그 코드 자체를 가리키는 설명을 보류하되, 코드의 용도·효과를 자연어로 완결해 설명한 문장까지 자동으로 의존구간에 묶지는 않는 것이다. 이 경우 정확 두 문장만 원형으로 복구하고 코드를 재구성하지 않는다.
