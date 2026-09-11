# Manifest 준비 영역

이 폴더에는 다음 두 종류의 manifest만 승인 뒤 만든다.

- v1 read-only inventory: 원본 경로·record count·SHA-256만 기록하며 v1을 변경하지 않는다.
- v2 release manifest: 승인된 v2 source·corpus·audit 판정·SHA-256을 기록한다.

준비 단계에서 임의 hash, 완료 수치, PASS 판정을 미리 만들지 않는다.
