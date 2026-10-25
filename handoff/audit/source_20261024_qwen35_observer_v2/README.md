# Qwen3.5 관찰 v2 실행 전 원형 보존

이 폴더는 실행하지 않은 v2 두 소스의 정확 바이트 사본이다. 원 v1의 실제 exit9와 원 qwen35 v3의 실패 기록은 별도로 유지한다.

| 파일 | SHA-256 |
|---|---|
| diag_p106b_qwen35_numeric_observer.py.txt | 3227385ABBE376EDF64193C21BFE2CE89A052AD3A61E0C0BBFEC246A21E67F06 |
| test_p106b_qwen35_numeric_observer.py.txt | 4BFB1ADA25D34406894A87C638B36DE3DEE8A476D2820C9D9CC22CF20FDA1C4A |

원 source47은 5AED353F4F1B95F75DEE88CDF725F57B1CC185FB67E8A60AC9227C2B55E05CA1이다. 총괄 CPU129개는 2.543초, 독립 CPU129개는 1.751초에 통과했다. 독립 검토에서 runtime 종료 후 통계만 있고 입장 전과 상주 시점 통계가 빠졌음을 확인했다. 실제 GPU 실행 전에 보완하므로 이 소스의 모델 실행과 private workspace clear는 NOT_RUN이다.

공식 HFLM의 self.pretrained는 실제 사전 인스턴스 참조로 확인됐다. 초기 AttributeError 의심은 철회됐으며 재현 결함으로 세지 않는다. gc.get_objects는 전체 heap의 CPU 목록과 일시적 강참조를 만들므로 관찰기 자체의 메모리 생성이 없다고 주장하지 않는다. 500000은 순회 한도이지 목록 생성과 RSS 상한이 아니다.

후속은 동일 두 활성 파일의 별도 v3와 새 source로 구분한다. 원 runtime과 수치 문턱 및 cleanup false에 따른 exit9/veto는 변경하지 않는다.
