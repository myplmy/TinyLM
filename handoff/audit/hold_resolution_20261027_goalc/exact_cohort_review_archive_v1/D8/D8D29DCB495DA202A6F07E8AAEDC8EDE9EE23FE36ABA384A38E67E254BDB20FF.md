# expanded_train:411002 source holds v2

## 식·변수 결손의 직접 종속 범위

- 원문 앵커: `TCP Friendly Bandwidth Share Estimations`의 평균 bandwidth share 식 도입 뒤 본 식이 없고, 이어지는 receiver estimate/packet size/loss rate/RTT 변수 정의와 loss-free 갱신식의 기호가 비어 있다.
- 처리: 식 도입, 변수 정의, 갱신 조건·식, 보고 주기별 평균 변수 문장을 최종 본문에서 분리했다. 앞의 연구 주제·분석모델 설명과 뒤의 독립적인 packet-loss/RTT 처리는 유지했다.
- 원문 앵커: `Interarrival Jitter Estimations`에서 RTP timestamp와 도착 시간 변수가 비어 있고, `D may be expressed as:`와 뒤의 delay-jitter 식도 내용이 없다.
- 처리: 지터 정의, 고립 수식 도입, 식 없는 jitter filter 문장을 최종 본문에서 분리했다. 이어지는 코드 구현 설명은 남겼다.

## 불완전 인용·링크 슬롯

- 원문 앵커: 전송 연구 주장의 뒤에 저자 인용 슬롯이 `, , and .`로 비어 있다. 슬롯만 제거하고 주장 자체는 보존했다.
- 원문 앵커: 손실률 filter 문장의 `presented in ,` 출처와 `The authors of ...`의 저자 주체/인용이 비어 있다. 불완전한 출처 문구를 분리하고, weighted average 설명은 일반적인 filter 설명으로 유지했다.
- 원문 앵커: RTT 설명의 `The algorithm above is described in` 뒤 출처가 비어 있다. 그 출처 구절은 제거하고, TRFC 사양의 송신자 RTT 추정 및 본 구현의 수신자 추정 비교를 유지했다.
- 원문 앵커: `You may find the original Evalvid-RA here` 및 ASSP 최신 소스 링크 안내는 링크 대상이 표시되지 않는다. 링크만 지시하는 두 문장을 최종 본문에서 분리했고 대상을 추정하지 않았다.
- 같은 Vicisiano/Rizzo/Crowcroft 문헌 문장이 반복되지만 추출 중복 증거가 없으므로 반복 서지는 유지했다. Figure 1 캡션도 본문에 남겼으며 그림 자체의 존재/내용은 별도로 추정하지 않았다.

## 판독·출력 근거

- 원형/후보 전체 EOF와 공통 SHA-256은 `review_004.md`의 최초 판독 기록을 재사용했고, 이번 정정에서 원형/후보를 재독하지 않았다. 원형/후보 SHA-256 `9EFC7FDA3FDDC516FD4CEE6629EAFBA911B7DF47377EAFD0F583D56ECAA2DB86`.
- 최종 v2 전문 1/4–4/4 및 exact changes 1/2–2/2를 고정 final-review로 실제 EOF까지 확인했다. 총 10개 변경이며 exact byte reconstruction을 확인했다.
- 최종: `expanded_train_411002_final_v2.txt`, 14794 bytes, SHA-256 `0BAA98FD74EC6D47861D6B8A045E6679F80A198A966420595A81C36C2D30CC24`.
