# TASK_007 판독 및 출력 끝 확인

- `expanded_train:191639`: Identity V1이 정한 original frame 패킷 0001–0006을 순서대로 읽어 원문 END/EOF까지 확인했고, packet 0012에서 candidate 끝과 full_diff END/EOF를 확인했다. byte-identical 증명으로 candidate를 연결했다. 경계 질문과 원형 인용은 hold sidecar에 남겼으며 학습 TXT는 선택하지 않았다.
- `expanded_train:191952`: Identity V1의 original frame 패킷 0001–0002와 final full_diff 패킷 0004를 읽었다. 새 출력 말미는 `디즈니 애니메이션 영화`; 출력본에 종단 LF가 추가됐다.
- `expanded_train:192107`: 패킷 0001–0004로 original/candidate/full_diff를 끝까지 확인했다. 새 출력 말미는 `테니스의 기술`; 출력본에 종단 LF가 추가됐다.
- `expanded_train:192356`: 패킷 0001에서 original/candidate/full_diff의 논리 END와 실제 EOF를 확인했다. 새 출력 마지막 내용은 두 번째 펑청시의 현급시 설명이며 빈 줄로 끝난다.
- `expanded_train:192845`: 패킷 0001에서 original/candidate/full_diff의 논리 END와 실제 EOF를 확인했다. 새 출력 마지막 내용은 자무쓰시 샹양구의 시할구 설명이며 끝 바이트를 자르지 않았다.

수정 출력 네 개는 대응 draft와 비교해 차이가 없었고 마지막 항목을 확인했다. 출력 생성 과정에서 원형/초기사본을 덮거나 지우지 않았다.
