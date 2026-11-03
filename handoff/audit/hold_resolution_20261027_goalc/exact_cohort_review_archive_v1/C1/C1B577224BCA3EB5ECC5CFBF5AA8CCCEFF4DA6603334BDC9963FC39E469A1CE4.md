| ID | 판정 | 실제 판독 범위 | 출력 TXT | 구체 근거 |
|---|---|---|---|---|
| 478825 | ACCEPT_CANDIDATE | 지정 패킷 0001–0003의 원문·후보·전체 diff를 순서대로 각 논리 END/EOF까지 판독. | expanded_train_478825_candidate.txt | 리드 `1984년 7월 8일`과 분류 `1979년 출생`의 상충 생년은 후보에서 분리되고 `7월 8일`은 유지된다. 성우의 학교·출연작·광고·방송 경력은 보존. 두 생년은 `hold_478825_task163_birth_years_v1.md`. |
| 479143 | ACCEPT_CANDIDATE | 지정 패킷 0001의 원문·후보·전체 diff를 논리 END/EOF까지 판독. | expanded_train_479143_candidate.txt | 원문 리드 `1937년 3월 15일`과 분류 `1939년 출생`의 연도 충돌을 후보가 분리하고 `3월 15일`은 남긴다. 사망일·가족·작품·경력과 명명 분류는 유지. 근거는 `hold_479143_task163_birth_years_v1.md`. |
| 480213 | ACCEPT_CANDIDATE | 지정 패킷 0001의 원문·후보·전체 diff를 논리 END/EOF까지 판독. | expanded_train_480213_candidate.txt | 리드·본문·분류의 1920년 출생 및 2017년 사망이 일치한다. 후보는 빈 `각주` 표제만 정리하고 출처가 붙은 활동 서술·사망일·관계를 보존한다. |
| 480434 | ACCEPT_CANDIDATE | 지정 패킷 0001–0003의 원문·후보·전체 diff를 순서대로 각 논리 END/EOF까지 판독. | expanded_train_480434_candidate.txt | 리드와 본문에 있는 `1761년` 및 분류 `1781년 출생`이 상충하며 후보는 세 연도 출현을 분리하고 `1월 29일`을 보존한다. 1849년 사망 및 공직·학술 경력은 유지. 보류 원형은 `hold_480434_task163_birth_years_v1.md`. |
| 481028 | ACCEPT_CANDIDATE | 지정 패킷 0001의 원문·후보·전체 diff를 논리 END/EOF까지 판독. | expanded_train_481028_candidate.txt | 리드·본문·분류의 1925년 출생과 2006년 사망이 일치한다. 후보는 빈 `각주` 표제만 정리하고 이름·직업·외교 경력·가족 정보를 유지한다. |
