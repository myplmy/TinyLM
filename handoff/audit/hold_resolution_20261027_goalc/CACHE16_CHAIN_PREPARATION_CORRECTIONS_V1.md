# cache16 연결 준비의 정정 이력

새 runner를 만들 때 기존 v5와 파일명을 중복 사용했다. 실제 git diff와 HEAD를 확인한 뒤
그 변경만 좁게 역패치하고 바이트 일치를 검증했다. 기존 v5 SHA는
`F9FD5851FCA4FA95FBE09CE6ACC3CED07E5818C85E449A3DD7C542128532FDFD`이며
수정 상태가 아니다. 새 연결은 이름 중복이 없는 v6만 사용한다. 이 오류가 있는 동안
캐시나 build/consumer worker를 시작하지 않았다.

새 adapter의 첫 CLI 검사에서는 frozen 파일 안의 문자열 상수까지 anchor로 센 검사가
실패했다. 실제 실행 행의 앞줄까지 정확히 일치하도록 수정하고 CLI 구문 검사를 통과했다.
이 CLI 검사는 실제 캐시 PASS가 아니다. 실제 설정·pin 검증과 build/consumer를 별도로 수행한다.

이미 pin한 F3/F4 문서는 원래 바이트를 보존하며 이 정정은 별도 파일로 남긴다.
