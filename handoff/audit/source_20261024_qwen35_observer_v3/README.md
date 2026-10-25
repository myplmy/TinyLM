# Qwen3.5 관찰 v3 실행 전 원형 보존

이 소스는 pre/resident/post 세 시점은 연결했지만, resident의 저장소 개수 상한이 실제 모델 규모보다 작은 차단을 CPU에서 재현해 GPU를 실행하지 않았다.

| 파일 | SHA-256 |
|---|---|
| diag_p106b_qwen35_numeric_observer.py.txt | 915BE3C20747C8CAFF7DB8586056221FBBBEE4A8523117267DB4A307C1995D3B |
| test_p106b_qwen35_numeric_observer.py.txt | 2EAD5D31C622FD1E5CC3CDF4CBF6425005E7ACCC0064E9A3FB1F3B002708C30E |

source48은 F8F3BDB6D1F301D61D6E60519B8F0E67C5AED1C33DE1D3D839E29F5652F5EBDE다. root133개 CPU는 2.232초, 독립133개는 1.251초에 통과했지만 실제 언어320키 규모를 반영한 저장소 회귀가 없었다. root 코드 검토에서128개 상한을 지적했고 저자와 독립 검토가129/320/322개 반례를 재현했다. 기본128을 넘으면 complete=false와 Hold로 막히며 clear는0회였다. 이 소스의 모델 실행은 NOT_RUN이다.

128 유지안은 정상 상주 관찰을 막는다. 상주 시점만 늘리는 안은 종료 후129개 이상의 실제 잔류 분석을 다시 막을 수 있다. 따라서 v4는 메타데이터 저장소 상한만1024로 늘리고1025부터 계속 중단한다. 값과 텐서를 복사하지 않으며 원 모델과 수치 허용차 및 cleanup false에 따른 exit9/veto는 변경하지 않는다. 새1024 상한은 모델 품질·수치 게이트의 완화가 아니다.
