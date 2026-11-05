# 동일 원문 역할의 guard5 판독 전환

현재 원문 권한·역할·출력 폴더·무손실 core3·TXT작성 원칙은 그대로다. 새 metadata guard5 `01642506DFC284C3097F9E591CA297924A24D5043BF675A7A474FF6B86515338`만 결합한다.

- C/L: `bash /home/uranus/tinyLM/tmp/hold-c-lossless-v5 SOURCE_ID pair PART` 또는 `hold-l-lossless-v5`.
- H/J/G: `bash /home/uranus/tinyLM/tmp/hold-h-lossless-v5 PAGE SOURCE_ID pair PART` 또는 해당 `hold-j-lossless-v5`/`hold-g-lossless-v5`.
- 지금 읽는 ID는 기존V4의 마지막 EOF까지 마치고 다음ID부터V5를 쓴다. 구V3/V4로이미완독한ID를 재독하지 않는다.
- 32895와74587 및원형/후보SHA·expanded/historical 부모alias는 metadata HOLD이며 raw·후보·packet·해시 추가 접근과새본문 작성이 금지된다. 과거에읽은일반기사전체를 민감으로 확정하는 규칙은 아니다.
- 일반JIT825214와이미해소한일반화학21396/37267/22078은새민감분류에포함하지않는다.
- 원형그대로는KEEP_SOURCE+절대경로, 후보그대로는ACCEPT_CANDIDATE+accept_output_absolute, 실제수정때만새TXT다. 정확출력셀에는TXT절대경로하나만, sidecar는사유칸에쓴다.
- 별도전환pilot파일·원문사본을만들필요없다. 첫V5완독ID/전체파트수는통상진행기록에쓴다.

실제고정별칭의정상metadata5건/새2행·기존267902·잘못된역할거절4건과25회귀가통과했다. 아직5역할의V5실사용완료를주장하지않는다. core3에서측정한긴문서50→26파트는보존되며전량판독속도배수는미측정이다.
